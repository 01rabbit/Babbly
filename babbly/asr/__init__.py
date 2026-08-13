from .types import ASRResult


def create_asr(config):
    """Create the configured ASR backend without importing ML/audio stacks at package import time."""
    from .factory import create_asr as _create_asr

    return _create_asr(config)


__all__ = ["ASRResult", "create_asr"]
