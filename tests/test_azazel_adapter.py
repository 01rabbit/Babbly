from babbly.adapters.azazel import AzazelAdapter
from babbly.core.engine import SituationEngine


def test_azazel_adapter_translates_alerts_and_advisory():
    payload = {
        "system": "azazel-edge",
        "state": "shield",
        "alerts": [
            {
                "category": "network.scan",
                "summary": "repeated local probing",
                "severity": "warning",
                "confidence": 0.91,
            }
        ],
        "recommendations": [
            {
                "action": "maintain shield",
                "reason": "probing remains active",
                "priority": 10,
                "confidence": 0.88,
            }
        ],
    }
    adapter = AzazelAdapter(lambda: payload)
    snapshot = SituationEngine([adapter]).collect()

    assert snapshot.systems["azazel"] == "online"
    assert snapshot.status == "warning"
    assert any(item.category == "network.scan" for item in snapshot.observations)
    assert snapshot.recommendations[0].action == "maintain shield"
    assert snapshot.recommendations[0].advisory_only is True


def test_adapter_failure_does_not_break_situation_engine():
    def broken_provider():
        raise RuntimeError("offline")

    snapshot = SituationEngine([AzazelAdapter(broken_provider)]).collect()
    assert snapshot.systems["azazel"] == "error"
