from babbly.wake.asr_backend import ASRWakeDetector
from babbly.wake.sherpa_onnx_backend import SherpaOnnxWakeDetector


def create_wake_detector(config, asr, aliases=None):
    backend = str(config.get("WAKE_BACKEND", "asr")).strip().lower()
    phrases = config.get("WAKEUP_PHRASES")
    if not isinstance(phrases, list) or not phrases:
        phrases = [str(config.get("WAKEUP_PHRASE") or "").strip()]

    if backend in {"asr", "legacy"}:
        return ASRWakeDetector(asr, phrases, aliases)

    if backend in {"sherpa-onnx", "sherpa", "kws"}:
        return SherpaOnnxWakeDetector(
            tokens=str(config.get("KWS_TOKENS") or ""),
            encoder=str(config.get("KWS_ENCODER") or ""),
            decoder=str(config.get("KWS_DECODER") or ""),
            joiner=str(config.get("KWS_JOINER") or ""),
            keywords_file=str(config.get("KWS_KEYWORDS_FILE") or ""),
            sample_rate=int(config.get("KWS_SAMPLE_RATE", 16000)),
            chunk_ms=int(config.get("KWS_CHUNK_MS", 100)),
            num_threads=int(config.get("KWS_NUM_THREADS", 2)),
            provider=str(config.get("KWS_PROVIDER") or "cpu"),
            device=config.get("KWS_INPUT_DEVICE"),
        )

    raise ValueError(f"Unsupported WAKE_BACKEND: {backend}")
