from babbly.asr.types import ASRResult
from babbly.ja.vosk_asr_module import get_asr_result, initialize_vosk_asr


class VoskASR:
    def __init__(self, model_path: str):
        self._engine = initialize_vosk_asr(model_path)

    def listen(self) -> ASRResult:
        text = get_asr_result(self._engine) or ""
        return ASRResult(text=text, confidence=None, backend="vosk")
