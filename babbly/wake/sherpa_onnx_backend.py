from pathlib import Path

from babbly.wake.base import WakeDetector
from babbly.wake.types import WakeResult


class SherpaOnnxWakeDetector(WakeDetector):
    """Always-on local KWS using an explicitly provisioned sherpa-onnx model.

    The model and keyword file are deployment inputs. Babbly does not download
    them at runtime and does not assume the public pretrained KWS models support
    Japanese. Detection only opens the command-listening gate; it has no action
    authority.
    """

    def __init__(
        self,
        *,
        tokens: str,
        encoder: str,
        decoder: str,
        joiner: str,
        keywords_file: str,
        sample_rate: int = 16000,
        chunk_ms: int = 100,
        num_threads: int = 2,
        provider: str = "cpu",
        device=None,
    ):
        try:
            import numpy as np
            import sherpa_onnx
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "sherpa-onnx wake backend requested but sherpa-onnx, numpy, or sounddevice is unavailable"
            ) from exc

        required = {
            "tokens": tokens,
            "encoder": encoder,
            "decoder": decoder,
            "joiner": joiner,
            "keywords_file": keywords_file,
        }
        missing = [name for name, value in required.items() if not value or not Path(value).expanduser().is_file()]
        if missing:
            raise ValueError("Missing sherpa-onnx KWS files: " + ", ".join(missing))

        self.np = np
        self.sd = sd
        self.sample_rate = max(8000, int(sample_rate))
        self.samples_per_read = max(1, int(self.sample_rate * max(20, int(chunk_ms)) / 1000))
        self.device = device
        self.kws = sherpa_onnx.KeywordSpotter(
            tokens=str(Path(tokens).expanduser()),
            encoder=str(Path(encoder).expanduser()),
            decoder=str(Path(decoder).expanduser()),
            joiner=str(Path(joiner).expanduser()),
            keywords_file=str(Path(keywords_file).expanduser()),
            num_threads=max(1, int(num_threads)),
            provider=str(provider or "cpu"),
        )

    def wait(self) -> WakeResult:
        stream = self.kws.create_stream()
        kwargs = {
            "channels": 1,
            "dtype": "float32",
            "samplerate": self.sample_rate,
        }
        if self.device is not None:
            kwargs["device"] = self.device

        with self.sd.InputStream(**kwargs) as audio:
            while True:
                samples, _overflowed = audio.read(self.samples_per_read)
                mono = self.np.asarray(samples, dtype=self.np.float32).reshape(-1)
                stream.accept_waveform(self.sample_rate, mono)
                while self.kws.is_ready(stream):
                    self.kws.decode_stream(stream)
                    result = self.kws.get_result(stream)
                    if result:
                        self.kws.reset_stream(stream)
                        return WakeResult(
                            triggered=True,
                            keyword=str(result),
                            backend="sherpa-onnx-kws",
                            confidence=None,
                        )
