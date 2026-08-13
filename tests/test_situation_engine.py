from babbly.adapters.base import BabblyAdapter
from babbly.core import Observation
from babbly.core.engine import SituationEngine


class HealthyAdapter(BabblyAdapter):
    name = "healthy"

    def observations(self):
        return [Observation("healthy", "status", "ok", severity="info")]


class FailingAdapter(BabblyAdapter):
    name = "failing"

    def observations(self):
        raise RuntimeError("boom")


def test_one_failed_adapter_does_not_drop_healthy_context():
    snapshot = SituationEngine([FailingAdapter(), HealthyAdapter()]).collect()
    assert snapshot.systems["failing"] == "error"
    assert snapshot.systems["healthy"] == "online"
    assert any(item.source == "healthy" for item in snapshot.observations)
