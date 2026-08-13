from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WakeResult:
    triggered: bool
    keyword: str = ""
    backend: str = "unknown"
    confidence: Optional[float] = None
