import math
import time
from typing import List

import numpy as np
import sounddevice as sd

from babbly.asr.types import ASRResult


class FasterWhisperASR:
    """Offline utterance ASR using faster-whisper.

    Audio capture is bounded by silence detection so the backend can be used as
    a drop-in replacement for the legacy one-utterance Vosk path.
    """

    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "ja",
        sample_rate: int = 16000,
        silence_seconds: float = 0.8,
        max_seconds: float = 12.0,
        rms_threshold: float = 0.012,
    ):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper backend requested but faster-whisper is not installed"
            ) from exc

        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self.language = language
        self.sample_rate = sample_rate
        self.silence_seconds = silence_seconds
        self.max_seconds = max_seconds
        self.rms_threshold = rms_threshold

    def _capture_utterance(self) -> np.ndarray:
        block_seconds = 0.1
        block_size = int(self.sample_rate * block_seconds)
        silent_blocks_required = max(1, int(self.silence_seconds / block_seconds))
        max_blocks = max(1, int(self.max_seconds / block_seconds))
        chunks: List[np.ndarray] = []
        speech_started = False
        silent_blocks = 0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
        ) as stream:
            for _ in range(max_blocks):
                data, _overflowed = stream.read(block_size)
                mono = np.asarray(data[:, 0], dtype=np.float32)
                rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0

                if rms >= self.rms_threshold:
                    speech_started = True
                    silent_blocks = 0
                    chunks.append(mono.copy())
                elif speech_started:
                    chunks.append(mono.copy())
                    silent_blocks += 1
                    if silent_blocks >= silent_blocks_required:
                        break
                else:
                    time.sleep(0.01)

        if not chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(chunks)

    @staticmethod
    def _segment_confidence(segments) -> float | None:
        scores = []
        for segment in segments:
            avg_logprob = getattr(segment, "avg_logprob", None)
            if avg_logprob is not None:
                scores.append(max(0.0, min(1.0, math.exp(float(avg_logprob)))))
        if not scores:
            return None
        return sum(scores) / len(scores)

    def listen(self) -> ASRResult:
        audio = self._capture_utterance()
        if audio.size == 0:
            return ASRResult(text="", confidence=None, backend="faster-whisper")

        segments_iter, _info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        segments = list(segments_iter)
        text = "".join(segment.text for segment in segments).strip()
        confidence = self._segment_confidence(segments)
        return ASRResult(text=text, confidence=confidence, backend="faster-whisper")
