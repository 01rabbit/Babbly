from __future__ import annotations

from collections.abc import Sequence

from babbly.nlu.japanese import normalize_japanese
from babbly.wake.base import WakeDetector
from babbly.wake.types import WakeResult


class ASRWakeDetector(WakeDetector):
    """Compatibility wake gate using the configured ASR backend.

    A profile may expose one or more wake phrases. Matching remains low-authority:
    a wake hit only opens command listening and never creates an executable intent.
    """

    def __init__(self, asr, phrases: str | Sequence[str], aliases=None):
        self.asr = asr
        self.aliases = aliases
        if isinstance(phrases, str):
            values = (phrases,)
        else:
            values = tuple(str(value) for value in phrases)
        self.phrases = tuple(value.strip() for value in values if value.strip())
        self.expected = tuple(
            (phrase, normalize_japanese(phrase, aliases)) for phrase in self.phrases
        )

    def wait(self) -> WakeResult:
        while True:
            result = self.asr.listen()
            if result.is_empty:
                continue
            text = normalize_japanese(result.text, self.aliases)
            for phrase, expected in self.expected:
                if expected and expected in text:
                    return WakeResult(
                        triggered=True,
                        keyword=phrase,
                        backend=f"asr:{result.backend}",
                        confidence=result.confidence,
                    )
