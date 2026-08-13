from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence


class VadEvent(str, Enum):
    """Frame-level voice-activity classification with utterance boundaries."""

    SILENCE = "silence"          # quiet, no active utterance
    SPEECH_START = "speech_start"  # first frame of a new utterance
    SPEECH = "speech"            # ongoing utterance (loud, or within hangover)
    SPEECH_END = "speech_end"    # hangover elapsed; utterance closed on this frame


@dataclass
class EnergyVad:
    """Low-cost energy voice-activity detector.

    This is the separable VAD stage of the speech-entry pipeline
    (VAD -> wake/KWS -> full ASR). It decides *whether there is speech*, never
    *what was said*, so it can gate expensive full-ASR inference while idle
    without any model asset. It has no action authority.

    A short hysteresis avoids chattering: ``start_frames`` consecutive loud
    frames open an utterance and ``hangover_frames`` consecutive quiet frames
    close it, so brief dips inside speech do not end the utterance.
    """

    rms_threshold: float = 0.012
    start_frames: int = 1
    hangover_frames: int = 8

    def __post_init__(self) -> None:
        self.rms_threshold = max(0.0, float(self.rms_threshold))
        self.start_frames = max(1, int(self.start_frames))
        self.hangover_frames = max(1, int(self.hangover_frames))
        self.reset()

    def reset(self) -> None:
        self._in_speech = False
        self._loud_run = 0
        self._quiet_run = 0

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    @staticmethod
    def rms(samples: Sequence[float]) -> float:
        """Root-mean-square level of a frame; 0.0 for an empty frame."""
        total = 0.0
        count = 0
        for value in samples:
            total += float(value) * float(value)
            count += 1
        if count == 0:
            return 0.0
        return math.sqrt(total / count)

    def observe_rms(self, rms: float) -> VadEvent:
        """Advance the state machine by one frame given its RMS level."""
        loud = float(rms) >= self.rms_threshold

        if not self._in_speech:
            if loud:
                self._loud_run += 1
                if self._loud_run >= self.start_frames:
                    self._in_speech = True
                    self._loud_run = 0
                    self._quiet_run = 0
                    return VadEvent.SPEECH_START
            else:
                self._loud_run = 0
            return VadEvent.SILENCE

        # in speech
        if loud:
            self._quiet_run = 0
            return VadEvent.SPEECH
        self._quiet_run += 1
        if self._quiet_run >= self.hangover_frames:
            self._in_speech = False
            self._quiet_run = 0
            self._loud_run = 0
            return VadEvent.SPEECH_END
        return VadEvent.SPEECH

    def observe_frame(self, samples: Sequence[float]) -> VadEvent:
        return self.observe_rms(self.rms(samples))

    def speech_present(self, frames: Iterable[Sequence[float]]) -> bool:
        """True if any utterance opens across a sequence of frames.

        Convenience for an idle gate: if this returns False for a window of
        captured frames, full ASR does not need to run.
        """
        for frame in frames:
            event = self.observe_frame(frame)
            if event in (VadEvent.SPEECH_START, VadEvent.SPEECH):
                return True
        return False
