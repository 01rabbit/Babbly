from babbly.core.attention import OperatorAttentionState
from babbly.core.situation import Observation, Recommendation, SituationSnapshot
from babbly.core.surface import build_situation_view, render_tui


def _rich_snapshot() -> SituationSnapshot:
    snapshot = SituationSnapshot()
    snapshot.set_system_state("azazel", "online")
    snapshot.set_system_state("kali", "error")
    snapshot.add_observation(Observation(source="azazel", category="state", summary="Edge稼働中", severity="info"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="探索通信を検出", severity="warning"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="再送を検出", severity="caution"))
    snapshot.add_recommendation(
        Recommendation(source="azazel", action="Shield維持", reason="継続観測のため", priority=1, confidence=0.92)
    )
    return snapshot


def test_view_normal_exposes_full_density():
    view = build_situation_view(_rich_snapshot(), OperatorAttentionState.NORMAL)
    assert view["attention_state"] == "normal"
    assert view["status"] == "warning"
    assert view["status_label"] == "警戒"
    assert view["systems_summary"] == {"online": 1, "error": 1, "total": 2}
    assert view["systems"]  # adapter health exposed in NORMAL
    assert len(view["observations"]) == 3
    assert view["recommendation"]["reason"] == "継続観測のため"
    assert view["recommendation"]["confidence"] == 0.92
    assert view["degraded"] is True


def test_view_critical_is_compressed_but_same_snapshot():
    snapshot = _rich_snapshot()
    view = build_situation_view(snapshot, OperatorAttentionState.CRITICAL)
    assert view["systems"] == []  # health suppressed
    assert len(view["observations"]) == 1
    assert view["observations"][0]["summary"] == "探索通信を検出"  # most severe survives
    assert view["recommendation"]["action"] == "Shield維持"
    assert view["recommendation"]["reason"] is None  # reasoning suppressed
    # underlying snapshot is untouched
    assert len(snapshot.observations) == 3


def test_view_density_decreases_with_attention():
    snapshot = _rich_snapshot()
    counts = [
        len(build_situation_view(snapshot, state)["observations"])
        for state in (OperatorAttentionState.NORMAL, OperatorAttentionState.HEADS_UP, OperatorAttentionState.CRITICAL)
    ]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1]


def test_view_pending_confirmation_is_passed_through():
    pending = {"operation": "recon-alpha", "confirmation_id": "c1", "target_ref": "target-A"}
    view = build_situation_view(_rich_snapshot(), OperatorAttentionState.NORMAL, pending_confirmation=pending)
    assert view["pending_confirmation"] == pending


def test_render_tui_normal_vs_critical():
    snapshot = _rich_snapshot()
    normal = render_tui(build_situation_view(snapshot, OperatorAttentionState.NORMAL))
    critical = render_tui(build_situation_view(snapshot, OperatorAttentionState.CRITICAL))
    assert "警戒" in normal and "警戒" in critical
    assert "探索通信を検出" in normal and "探索通信を検出" in critical
    assert "azazel=online" in normal  # adapter detail only in NORMAL
    assert "azazel=online" not in critical
    assert "継続観測のため" in normal and "継続観測のため" not in critical
    assert len(normal) > len(critical)


def test_render_tui_handles_empty_snapshot():
    view = build_situation_view(SituationSnapshot(), OperatorAttentionState.NORMAL)
    text = render_tui(view)
    assert "観測: なし" in text
    assert view["degraded"] is False
