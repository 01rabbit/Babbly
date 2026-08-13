from abc import ABC, abstractmethod
from typing import Iterable

from babbly.core import Observation, Recommendation


class BabblyAdapter(ABC):
    """Read-only/advisory integration boundary for external systems.

    Adapters convert external system state into Babbly observations and
    recommendations. They do not receive arbitrary shell execution authority.
    """

    name = "base"

    @abstractmethod
    def observations(self) -> Iterable[Observation]:
        raise NotImplementedError

    def recommendations(self) -> Iterable[Recommendation]:
        return ()
