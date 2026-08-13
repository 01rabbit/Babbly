from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.situation import Observation, Recommendation, SituationSnapshot


class StaticSituationEngine:
    def __init__(self):
        self.snapshot = SituationSnapshot()
        self.snapshot.set_system_state("azazel-edge", "online")
        self.snapshot.add_observation(
            Observation(
                source="azazel-edge",
                category="network",
                summary="探索通信を検出",
                severity="warning",
                confidence=0.92,
            )
        )
        self.snapshot.add_recommendation(
            Recommendation(
                source="azazel-edge",
                action="Shield維持",
                reason="探索通信を継続観測するため",
                priority=1,
                confidence=0.92,
            )
        )

    def collect(self):
        return self.snapshot


def test_situation_report_uses_same_core_path_for_voice_and_web():
    runtime = OperatorIntentRuntime(StaticSituationEngine(), dry_run=True)

    voice = runtime.submit(OperatorIntent("situation.report", SourceModality.VOICE))
    web = runtime.submit(OperatorIntent("situation.report", SourceModality.WEB))

    assert voice.status == "ok"
    assert web.status == "ok"
    assert voice.payload == web.payload
    assert voice.payload["snapshot"]["status"] == "warning"


def test_registered_operation_has_same_semantics_from_voice_and_eud_under_dry_run():
    voice_intent = OperatorIntent(
        "operation.run",
        SourceModality.VOICE,
        parameters={"operation": "recon-alpha"},
        target_ref="192.0.2.10",
        context_ref="registered-sop",
    )
    eud_intent = OperatorIntent(
        "operation.run",
        SourceModality.EUD,
        parameters={"operation": "recon-alpha"},
        target_ref="192.0.2.10",
        context_ref="registered-sop",
    )

    assert voice_intent.semantic_payload() == eud_intent.semantic_payload()

    voice_runtime = OperatorIntentRuntime(dry_run=True)
    eud_runtime = OperatorIntentRuntime(dry_run=True)
    voice_runtime.submit(voice_intent)
    eud_runtime.submit(eud_intent)

    voice_result = voice_runtime.resolve_pending(True, SourceModality.VOICE)
    eud_result = eud_runtime.resolve_pending(True, SourceModality.EUD)

    assert voice_result.status == "dry_run"
    assert eud_result.status == "dry_run"
    assert voice_result.payload == eud_result.payload


def test_modality_switch_preserves_pending_confirmation_and_context():
    runtime = OperatorIntentRuntime(dry_run=True)
    request = OperatorIntent(
        "operation.run",
        SourceModality.VOICE,
        parameters={"operation": "recon-alpha"},
        target_ref="192.0.2.50",
        context_ref="task-17",
    )

    pending = runtime.submit(request)

    assert pending.status == "confirmation_required"
    assert runtime.context.pending_confirmation_id == pending.confirmation_id
    assert runtime.context.current_target == "192.0.2.50"
    assert runtime.context.current_context == "task-17"

    result = runtime.resolve_pending(True, SourceModality.WEB)

    assert result.status == "dry_run"
    assert result.correlation_id == request.correlation_id
    assert result.audit_id == request.audit_id
    assert result.confirmation_id == pending.confirmation_id
    assert result.payload["target_ref"] == "192.0.2.50"
    assert result.payload["context_ref"] == "task-17"
    assert runtime.context.pending_confirmation_id is None
    assert runtime.context.pending_intent is None


def test_profile_or_persona_is_not_part_of_authority_contract():
    intent = OperatorIntent(
        "situation.report",
        SourceModality.VOICE,
        parameters={"presentation_profile": "azazel-edge"},
    )

    assert "authority" not in intent.to_dict()
    assert "shell" not in intent.to_dict()
    assert intent.intent_id == "situation.report"
