import pytest

from babbly.core.attention import (
    AttentionController,
    OperatorAttentionState,
    coerce_state,
    policy_for,
)
from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.render import (
    render_recommendation_for_attention,
    render_situation_for_attention,
)
from babbly.core.situation import Observation, Recommendation, SituationSnapshot


ALL_STATES = list(OperatorAttentionState)


def _rich_snapshot() -> SituationSnapshot:
    snapshot = SituationSnapshot()
    snapshot.set_system_state("azazel", "online")
    snapshot.set_system_state("kali", "error")
    snapshot.add_observation(Observation(source="azazel", category="state", summary="Edge稼働中", severity="info"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="探索通信を検出", severity="warning"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="再送を検出", severity="caution"))
    snapshot.add_recommendation(
        Recommendation(source="azazel", action="Shield維持", reason="探索通信を継続観測するため", priority=1, confidence=0.92)
    )
    return snapshot


def _operation_intent(modality=SourceModality.VOICE) -> OperatorIntent:
    return OperatorIntent(
        intent_id="operation.run",
        source_modality=modality,
        parameters={"operation": "recon-alpha"},
        target_ref="target-A",
        context_ref="ctx-1",
    )


# --- state machine -----------------------------------------------------------

def test_three_states_exist_and_are_distinct():
    assert {s.value for s in OperatorAttentionState} == {"normal", "heads_up", "critical"}


def test_controller_defaults_to_normal_with_empty_history():
    controller = AttentionController()
    assert controller.state is OperatorAttentionState.NORMAL
    assert controller.history == []


def test_every_transition_is_applied_and_recorded():
    # Covers all 9 (from, to) ordered pairs, including no-op self-transitions.
    for from_state in ALL_STATES:
        for to_state in ALL_STATES:
            controller = AttentionController(state=from_state)
            transition = controller.request_state(to_state, "test")
            assert controller.state is to_state
            assert transition.from_state is from_state
            assert transition.to_state is to_state
            assert transition.sequence == 1
            assert controller.history == [transition]


def test_history_sequence_increments_and_preserves_order():
    controller = AttentionController()
    controller.request_state("heads_up", "voice")
    controller.request_state("critical", "web", reason="hands busy")
    controller.request_state("normal", "eud")
    assert [t.sequence for t in controller.history] == [1, 2, 3]
    assert [t.to_state.value for t in controller.history] == ["heads_up", "critical", "normal"]
    assert controller.history[1].source_modality == "web"
    assert controller.history[1].reason == "hands busy"


def test_coerce_state_accepts_variants_and_rejects_unknown():
    assert coerce_state("heads_up") is OperatorAttentionState.HEADS_UP
    assert coerce_state("HEADS-UP") is OperatorAttentionState.HEADS_UP
    assert coerce_state("headsup") is OperatorAttentionState.HEADS_UP
    assert coerce_state(OperatorAttentionState.CRITICAL) is OperatorAttentionState.CRITICAL
    with pytest.raises(ValueError):
        coerce_state("panic")


def test_request_state_fails_closed_on_unknown_state():
    controller = AttentionController()
    with pytest.raises(ValueError):
        controller.request_state("panic", "voice")
    assert controller.state is OperatorAttentionState.NORMAL
    assert controller.history == []


# --- presentation policy / rendering ----------------------------------------

def test_same_snapshot_renders_with_decreasing_density():
    snapshot = _rich_snapshot()
    normal = render_situation_for_attention(snapshot, OperatorAttentionState.NORMAL)
    heads_up = render_situation_for_attention(snapshot, OperatorAttentionState.HEADS_UP)
    critical = render_situation_for_attention(snapshot, OperatorAttentionState.CRITICAL)

    assert normal != heads_up != critical
    assert len(normal) > len(heads_up) > len(critical)

    # NORMAL exposes adapter health and the recommendation reason.
    assert "接続系統" in normal
    assert "理由は" in normal
    # HEADS_UP / CRITICAL drop health and reasoning but keep the action.
    assert "接続系統" not in heads_up and "接続系統" not in critical
    assert "理由は" not in heads_up and "理由は" not in critical
    assert "Shield維持" in normal and "Shield維持" in heads_up and "Shield維持" in critical


def test_observation_count_matches_policy():
    snapshot = _rich_snapshot()
    for state in ALL_STATES:
        text = render_situation_for_attention(snapshot, state)
        policy = policy_for(state)
        # The most severe observation (warning) always survives truncation.
        assert "探索通信を検出" in text
        if policy.max_observations < 3:
            # the info-severity, lowest-priority observation is dropped
            assert "Edge稼働中" not in text


def test_recommendation_rendering_shrinks_with_attention():
    snapshot = _rich_snapshot()
    normal = render_recommendation_for_attention(snapshot, OperatorAttentionState.NORMAL)
    critical = render_recommendation_for_attention(snapshot, OperatorAttentionState.CRITICAL)
    assert "理由は" in normal and "92%" in normal
    assert "理由は" not in critical
    assert "Shield維持" in critical
    assert len(normal) > len(critical)


# --- canonical runtime integration ------------------------------------------

def test_attention_set_from_voice_and_web_reach_same_state():
    results = {}
    for modality in (SourceModality.VOICE, SourceModality.WEB):
        runtime = OperatorIntentRuntime()
        result = runtime.submit(
            OperatorIntent(intent_id="attention.set", source_modality=modality, parameters={"state": "critical"})
        )
        assert result.status == "ok"
        assert result.message_code == "attention.state_changed"
        assert result.payload["attention_state"] == "critical"
        assert result.payload["previous_state"] == "normal"
        results[modality] = runtime.attention.state
    assert results[SourceModality.VOICE] == results[SourceModality.WEB] == OperatorAttentionState.CRITICAL


def test_attention_set_invalid_state_fails_closed():
    runtime = OperatorIntentRuntime()
    result = runtime.submit(
        OperatorIntent(intent_id="attention.set", source_modality=SourceModality.WEB, parameters={"state": "panic"})
    )
    assert result.status == "invalid"
    assert result.message_code == "attention.invalid_state"
    # unchanged
    assert runtime.attention.state is OperatorAttentionState.NORMAL
    assert runtime.attention.history == []


def test_attention_status_is_read_only_reportable():
    runtime = OperatorIntentRuntime()
    runtime.attention.request_state("heads_up", "voice")
    result = runtime.submit(
        OperatorIntent(intent_id="attention.status", source_modality=SourceModality.TUI)
    )
    assert result.status == "ok"
    assert result.payload["attention"]["state"] == "heads_up"


# --- authority invariance across attention modes ----------------------------

def test_operation_authority_is_identical_in_every_attention_mode():
    """Attention mode changes presentation only, never execution/confirmation."""
    pending_signatures = set()
    confirmed_signatures = set()
    for state in ALL_STATES:
        runtime = OperatorIntentRuntime(dry_run=False)
        runtime.attention.request_state(state, "test")

        pending = runtime.submit(_operation_intent())
        pending_signatures.add((pending.status, pending.message_code))

        confirmed = runtime.resolve_pending(True, SourceModality.WEB)
        confirmed_signatures.add((confirmed.status, confirmed.message_code))

    assert pending_signatures == {("confirmation_required", "operation.confirmation_required")}
    assert confirmed_signatures == {("ready_for_registered_executor", "operation.ready")}


def test_dry_run_representation_is_identical_in_every_attention_mode():
    confirmed_signatures = set()
    for state in ALL_STATES:
        runtime = OperatorIntentRuntime(dry_run=True)
        runtime.attention.request_state(state, "test")
        runtime.submit(_operation_intent())
        confirmed = runtime.resolve_pending(True, SourceModality.WEB)
        confirmed_signatures.add((confirmed.status, confirmed.message_code))
    assert confirmed_signatures == {("dry_run", "operation.dry_run")}


def test_mode_change_preserves_pending_confirmation_and_context():
    runtime = OperatorIntentRuntime(dry_run=True)
    pending = runtime.submit(_operation_intent(SourceModality.VOICE))
    assert pending.status == "confirmation_required"
    confirmation_id = pending.confirmation_id
    correlation_id = pending.correlation_id

    # Operator drops to CRITICAL mid-request; this must not clear the pending op.
    switched = runtime.submit(
        OperatorIntent(intent_id="attention.set", source_modality=SourceModality.EUD, parameters={"state": "critical"})
    )
    assert switched.status == "ok"
    assert runtime.attention.state is OperatorAttentionState.CRITICAL
    assert runtime.context.pending_confirmation_id == confirmation_id
    assert runtime.context.pending_intent is not None

    # The confirmation still resolves from a different modality, context intact.
    confirmed = runtime.resolve_pending(True, SourceModality.WEB)
    assert confirmed.status == "dry_run"
    assert confirmed.correlation_id == correlation_id
    assert confirmed.payload["target_ref"] == "target-A"
    assert confirmed.payload["context_ref"] == "ctx-1"
