from abc import ABC, abstractmethod

from babbly.wake.types import WakeResult


class WakeDetector(ABC):
    """Blocking low-authority gate that only decides whether Babbly should listen."""

    @abstractmethod
    def wait(self) -> WakeResult:
        raise NotImplementedError
