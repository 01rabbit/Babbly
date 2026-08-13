from babbly.core.render import render_recommendation_ja, render_situation_ja
from babbly.core.situation import Observation, Recommendation, SituationSnapshot
from babbly.nlu.japanese import IntentResolver


def test_situation_report_intent():
    resolver = IntentResolver()
    assert resolver.resolve("現在の状況を報告して").name == "situation.report"
    assert resolver.resolve("状況を教えて").name == "situation.report"


def test_recommendation_explain_intent():
    resolver = IntentResolver()
    assert resolver.resolve("推奨を説明して").name == "recommendation.explain"
    assert resolver.resolve("どうすればいい").name == "recommendation.explain"


def test_render_situation_prioritizes_warning_and_recommendation():
    snapshot = SituationSnapshot()
    snapshot.set_system_state("azazel", "online")
    snapshot.add_observation(Observation(source="azazel", category="state", summary="Edge is online", severity="info"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="探索通信を検出", severity="warning"))
    snapshot.add_recommendation(Recommendation(source="azazel", action="Shield維持", reason="探索通信を継続観測するため", priority=1))

    text = render_situation_ja(snapshot)
    assert "警戒" in text
    assert "探索通信を検出" in text
    assert "Shield維持" in text


def test_render_recommendation_is_explicitly_advisory():
    snapshot = SituationSnapshot()
    snapshot.add_recommendation(
        Recommendation(
            source="azazel",
            action="Shield維持",
            reason="探索通信を継続観測するため",
            priority=1,
            confidence=0.92,
            advisory_only=True,
        )
    )
    text = render_recommendation_ja(snapshot)
    assert "Shield維持" in text
    assert "92%" in text
    assert "自動実行はしません" in text


def test_empty_snapshot_has_safe_report():
    snapshot = SituationSnapshot()
    assert "報告可能な観測はありません" in render_situation_ja(snapshot)
    assert "提示できる推奨はありません" in render_recommendation_ja(snapshot)
