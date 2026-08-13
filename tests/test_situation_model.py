from babbly.core import Observation, Recommendation, SituationSnapshot


def test_snapshot_uses_highest_observation_severity():
    snapshot = SituationSnapshot()
    snapshot.add_observation(Observation("sensor", "network", "normal", severity="info"))
    snapshot.add_observation(Observation("sensor", "network", "suspicious", severity="warning"))
    assert snapshot.status == "warning"


def test_recommendations_are_sorted_by_priority():
    snapshot = SituationSnapshot()
    snapshot.add_recommendation(Recommendation("a", "observe", "later", priority=50))
    snapshot.add_recommendation(Recommendation("b", "review", "first", priority=10))
    assert [item.source for item in snapshot.recommendations] == ["b", "a"]


def test_recommendations_are_advisory_by_default():
    recommendation = Recommendation("azazel", "maintain shield", "suspicious scan")
    assert recommendation.advisory_only is True
