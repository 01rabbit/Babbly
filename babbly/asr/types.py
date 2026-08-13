from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ASRResult:
    text: str
    confidence: Optional[float] = None
    backend: str = "unknown"

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()
