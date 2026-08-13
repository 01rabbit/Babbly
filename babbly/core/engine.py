from typing import Iterable

from babbly.adapters.base import BabblyAdapter
from babbly.core.situation import SituationSnapshot


class SituationEngine:
    """Aggregate read-only adapter output into one operator-facing snapshot."""

    def __init__(self, adapters: Iterable[BabblyAdapter] = ()):
        self.adapters = list(adapters)

    def collect(self) -> SituationSnapshot:
        snapshot = SituationSnapshot()
        for adapter in self.adapters:
            try:
                for observation in adapter.observations():
                    snapshot.add_observation(observation)
                for recommendation in adapter.recommendations():
                    snapshot.add_recommendation(recommendation)
                snapshot.set_system_state(adapter.name, "online")
            except Exception as exc:
                snapshot.set_system_state(adapter.name, "error")
                # Adapter failure is represented as state, not raised into the
                # operator loop. External integrations must remain optional.
                continue
        return snapshot
