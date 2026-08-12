from babbly.asr.faster_whisper_backend import FasterWhisperASR
from babbly.asr.vosk_backend import VoskASR


def create_asr(config):
    backend = str(config.get("ASR_BACKEND", "vosk")).strip().lower()

    if backend == "vosk":
        return VoskASR(config.get("MODEL_PATH"))

    if backend in {"faster-whisper", "whisper"}:
        return FasterWhisperASR(
            model_name=config.get("WHISPER_MODEL", "small"),
            device=config.get("WHISPER_DEVICE", "cpu"),
            compute_type=config.get("WHISPER_COMPUTE_TYPE", "int8"),
            language=config.get("ASR_LANGUAGE", "ja"),
            silence_seconds=float(config.get("ASR_SILENCE_SECONDS", 0.8)),
            max_seconds=float(config.get("ASR_MAX_SECONDS", 12.0)),
            rms_threshold=float(config.get("ASR_RMS_THRESHOLD", 0.012)),
        )

    raise ValueError(f"Unsupported ASR_BACKEND: {backend}")
