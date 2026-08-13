from __future__ import annotations

from typing import Optional

from babbly.core.engine import SituationEngine
from babbly.core.operator_intent import (
    ClarificationState,
    OperatorContext,
    OperatorIntent,
    OperatorResult,
    SourceModality,
)


class OperatorIntentRuntime:
    """Shared core path for Voice/TUI/Web/EUD operator intents.

    This initial runtime intentionally owns only read-only intents and DRY_RUN
    representation of registered operations. Write-capable execution remains
    outside this contract until the controlled request/approval work in #18.
    """

    READ_ONLY_INTENTS = {"situation.report", "recommendation.explain"}

    def __init__(
        self,
        situation_engine: Optional[SituationEngine] = None,
        *,
        dry_run: bool = False,
        context: Optional[OperatorContext] = None,
    ) -> None:
        self.situation_engine = situation_engine or SituationEngine()
        self.dry_run = bool(dry_run)
        self.context = context or OperatorContext()

    def submit(self, intent: OperatorIntent) -> OperatorResult:
        bound = self.context.bind(intent)

        if bound.intent_id == "situation.report":
            snapshot = self.situation_engine.collect()
            return OperatorResult(
                intent_id=bound.intent_id,
                status="ok",
                correlation_id=bound.correlation_id,
                audit_id=bound.audit_id,
                payload={"snapshot": snapshot.to_dict()},
                message_code="situation.snapshot",
            )

        if bound.intent_id == "recommendation.explain":
            snapshot = self.situation_engine.collect()
            top = snapshot.recommendations[0] if snapshot.recommendations else None
            payload = {
                "snapshot": snapshot.to_dict(),
                "recommendation": (
                    {
                        "source": top.source,
                        "action": top.action,
                        "reason": top.reason,
                        "priority": top.priority,
                        "confidence": top.confidence,
                        "advisory_only": top.advisory_only,
                    }
                    if top is not None
                    else None
                ),
            }
            return OperatorResult(
                intent_id=bound.intent_id,
                status="ok",
                correlation_id=bound.correlation_id,
                audit_id=bound.audit_id,
                payload=payload,
                message_code="recommendation.snapshot",
            )

        if bound.intent_id == "operation.run":
            return self._submit_operation(bound)

        return OperatorResult(
            intent_id=bound.intent_id,
            status="unsupported",
            correlation_id=bound.correlation_id,
            audit_id=bound.audit_id,
            message_code="intent.unsupported",
        )

    def _submit_operation(self, intent: OperatorIntent) -> OperatorResult:
        operation = str(intent.parameters.get("operation") or "").strip()
        if not operation:
            return OperatorResult(
                intent_id=intent.intent_id,
                status="invalid",
                correlation_id=intent.correlation_id,
                audit_id=intent.audit_id,
                message_code="operation.missing_name",
            )

        if intent.clarification_state == ClarificationState.DENIED:
            return OperatorResult(
                intent_id=intent.intent_id,
                status="denied",
                correlation_id=intent.correlation_id,
                audit_id=intent.audit_id,
                confirmation_id=intent.confirmation_id,
                payload={"operation": operation, "target_ref": intent.target_ref},
                message_code="operation.denied",
            )

        if intent.clarification_state != ClarificationState.CONFIRMED:
            pending = self.context.set_pending(intent)
            return OperatorResult(
                intent_id=pending.intent_id,
                status="confirmation_required",
                correlation_id=pending.correlation_id,
                audit_id=pending.audit_id,
                confirmation_id=pending.confirmation_id,
                payload={"operation": operation, "target_ref": pending.target_ref},
                message_code="operation.confirmation_required",
            )

        if not self.dry_run:
            return OperatorResult(
                intent_id=intent.intent_id,
                status="external_authority_required",
                correlation_id=intent.correlation_id,
                audit_id=intent.audit_id,
                confirmation_id=intent.confirmation_id,
                payload={"operation": operation, "target_ref": intent.target_ref},
                message_code="operation.write_contract_not_enabled",
            )

        return OperatorResult(
            intent_id=intent.intent_id,
            status="dry_run",
            correlation_id=intent.correlation_id,
            audit_id=intent.audit_id,
            confirmation_id=intent.confirmation_id,
            payload={
                "operation": operation,
                "target_ref": intent.target_ref,
                "context_ref": intent.context_ref,
            },
            message_code="operation.dry_run",
        )

    def resolve_pending(self, approved: bool, modality: SourceModality) -> OperatorResult:
        resolved = self.context.resolve_pending(approved, modality)
        if resolved is None:
            return OperatorResult(
                intent_id="confirmation.resolve",
                status="no_pending_confirmation",
                correlation_id="",
                audit_id="",
                message_code="confirmation.none",
            )
        return self.submit(resolved)
