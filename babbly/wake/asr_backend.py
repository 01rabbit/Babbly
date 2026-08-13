from babbly.nlu.japanese import normalize_japanese
from babbly.wake.base import WakeDetector
from babbly.wake.types import WakeResult


class ASRWakeDetector(WakeDetector):
    """Compatibility wake gate using the configured ASR backend.

    This preserves the existing behavior while allowing the main loop to stop
    depending on how wake detection is implemented.
    """

    def __init__(self, asr, phrase: str, aliases=None):
        self.asr = asr
        self.phrase = phrase
        self.aliases = aliases
        self.expected = normalize_japanese(phrase, aliases)

    def wait(self) -> WakeResult:
        while True:
            result = self.asr.listen()
            if result.is_empty:
                continue
            text = normalize_japanese(result.text, self.aliases)
            if self.expected and self.expected in text:
                return WakeResult(
                    triggered=True,
                    keyword=self.phrase,
                    backend=f"asr:{result.backend}",
                    confidence=result.confidence,
                )
