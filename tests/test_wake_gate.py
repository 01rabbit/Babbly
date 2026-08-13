import pytest

from babbly.asr.types import ASRResult
from babbly.wake.asr_backend import ASRWakeDetector
from babbly.wake.factory import create_wake_detector


class FakeASR:
    def __init__(self, results):
        self.results = iter(results)

    def listen(self):
        return next(self.results)


def test_asr_wake_detector_ignores_non_wake_utterances():
    asr = FakeASR(
        [
            ASRResult("こんにちは", 0.9, "fake"),
            ASRResult("プログラム", 0.8, "fake"),
        ]
    )
    result = ASRWakeDetector(asr, "プログラム").wait()
    assert result.triggered is True
    assert result.keyword == "プログラム"
    assert result.backend == "asr:fake"
    assert result.confidence == 0.8


def test_asr_wake_detector_is_not_sensitive_to_whitespace():
    asr = FakeASR([ASRResult("プ ロ グ ラ ム", None, "fake")])
    assert ASRWakeDetector(asr, "プログラム").wait().triggered is True


def test_factory_defaults_to_legacy_compatible_asr_gate():
    detector = create_wake_detector(
        {"WAKEUP_PHRASE": "プログラム"},
        FakeASR([ASRResult("プログラム", None, "fake")]),
    )
    assert isinstance(detector, ASRWakeDetector)


def test_unknown_wake_backend_is_rejected():
    with pytest.raises(ValueError):
        create_wake_detector(
            {"WAKE_BACKEND": "magic", "WAKEUP_PHRASE": "プログラム"},
            FakeASR([]),
        )
