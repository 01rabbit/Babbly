from __future__ import annotations

from typing import Optional

from typing import Mapping as _Mapping

from babbly.core.attention import AttentionController, coerce_state
from babbly.core.engine import SituationEngine
from babbly.core.operator_intent import (
    ClarificationState,
    OperatorContext,
    OperatorIntent,
    OperatorResult,
    SourceModality,
)
from babbly.core.request import (
    ActionExecutor,
    ActionRequest,
    ControlledRequestManager,
    RiskClass,
)


class OperatorIntentRuntime:
    """Shared core path for Voice/TUI/Web/EUD operator intents.

    This runtime owns read-only intents and the presentation-neutral request
    state for registered local operations. It does not accept arbitrary shell
    strings and it does not replace the registered command/SOP executor.
    External-system write requests remain out of scope until #18.
    """

    READ_ONLY_INTENTS = {"situation.report", "recommendation.explain", "attention.status"}
    PRESENTATION_INTENTS = {"attention.set", "attention.status"}

    def __init__(
        self,
        situation_engine: Optional[SituationEngine] = None,
        *,
        dry_run: bool = False,
        context: Optional[OperatorContext] = None,
        attention: Optional[AttentionController] = None,
        request_manager: Optional[ControlledRequestManager] = None,
        action_executor: Optional[ActionExecutor] = None,
        write_actions: Optional[_Mapping[str, RiskClass]] = None,
    ) -> None:
        self.situation_engine = situation_engine or SituationEngine()
        self.dry_run = bool(dry_run)
        self.context = context or OperatorContext()
        self.attention = attention or AttentionController()
        # Controlled write path (#18). Absent by default so a registered
        # operation still stops at the registered-executor boundary. When both a
        # manager and executor are provided, an operation named in write_actions
        # is dispatched as a controlled external request after human approval.
        self.request_manager = request_manager
        self.action_executor = action_executor
        self.write_actions = self._normalize_write_actions(write_actions)

    @staticmethod
    def _normalize_write_actions(
        write_actions: Optional[_Mapping[str, RiskClass]]
    ) -> dict:
        if not write_actions:
            return {}
        normalized = {}
        for name, risk in write_actions.items():
            normalized[str(name)] = risk if isinstance(risk, RiskClass) else RiskClass(str(risk))
        return normalized

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

        if bound.intent_id == "attention.set":
            return self._set_attention(bound)

        if bound.intent_id == "attention.status":
            return OperatorResult(
                intent_id=bound.intent_id,
                status="ok",
                correlation_id=bound.correlation_id,
                audit_id=bound.audit_id,
                payload={"attention": self.attention.snapshot()},
                message_code="attention.status",
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

        # A confirmed operation that is a registered external write action is
        # dispatched through the controlled request/approval contract (#18). The
        # intent confirmation IS the human approval. Everything else stays at the
        # registered-executor boundary, unchanged.
        if operation in self.write_actions and self.request_manager is not None:
            return self._dispatch_external_action(intent, operation)

        status = "dry_run" if self.dry_run else "ready_for_registered_executor"
        code = "operation.dry_run" if self.dry_run else "operation.ready"
        return OperatorResult(
            intent_id=intent.intent_id,
            status=status,
            correlation_id=intent.correlation_id,
            audit_id=intent.audit_id,
            confirmation_id=intent.confirmation_id,
            payload={
                "operation": operation,
                "target_ref": intent.target_ref,
                "context_ref": intent.context_ref,
            },
            message_code=code,
        )

    def _dispatch_external_action(self, intent: OperatorIntent, operation: str) -> OperatorResult:
        """Run a confirmed write operation through the controlled request contract.

        The manager records submit/approve/dispatch in its audit trail. The
        external executor keeps final authority and may still reject an
        approved request; under DRY_RUN nothing is sent to the executor.
        """
        manager = self.request_manager
        manager.dry_run = self.dry_run  # honour the runtime's field-tuning switch
        parameters = {k: v for k, v in dict(intent.parameters).items() if k != "operation"}
        request = ActionRequest(
            action=operation,
            parameters=parameters,
            target_ref=intent.target_ref,
            context_ref=intent.context_ref,
            risk_class=self.write_actions[operation],
            requested_by_modality=intent.source_modality.value,
            correlation_id=intent.correlation_id,
            audit_id=intent.audit_id,
        )
        manager.submit(request)
        manager.approve(request.request_id, intent.source_modality.value)
        state = manager.dispatch(request.request_id, self.action_executor, modality=intent.source_modality.value)
        result = manager.result_of(request.request_id)

        payload = {
            "operation": operation,
            "target_ref": intent.target_ref,
            "context_ref": intent.context_ref,
            "request_id": request.request_id,
            "request_state": state.value,
            "external_ref": result.external_ref if result else None,
            "detail": result.detail if result else None,
        }
        if state.value == "completed" and self.dry_run:
            return self._operation_result(intent, "dry_run", "operation.dry_run", payload)
        if state.value == "completed":
            return self._operation_result(intent, "completed", "operation.completed", payload)
        code = "operation.executor_rejected" if (result and result.rejected_by_executor) else "operation.failed"
        return self._operation_result(intent, "failed", code, payload)

    def _operation_result(self, intent: OperatorIntent, status: str, code: str, payload: dict) -> OperatorResult:
        return OperatorResult(
            intent_id=intent.intent_id,
            status=status,
            correlation_id=intent.correlation_id,
            audit_id=intent.audit_id,
            confirmation_id=intent.confirmation_id,
            payload=payload,
            message_code=code,
        )

    def _set_attention(self, intent: OperatorIntent) -> OperatorResult:
        """Apply an operator attention-state change.

        Attention state is a presentation control: it is applied without
        confirmation and it never alters execution authority, confirmation
        policy, the pending operation, or the SituationSnapshot. An unknown
        state fails closed.
        """
        try:
            target = coerce_state(intent.parameters.get("state"))
        except ValueError:
            return OperatorResult(
                intent_id=intent.intent_id,
                status="invalid",
                correlation_id=intent.correlation_id,
                audit_id=intent.audit_id,
                payload={"requested": intent.parameters.get("state")},
                message_code="attention.invalid_state",
            )

        previous = self.attention.state
        transition = self.attention.request_state(
            target,
            intent.source_modality.value,
            reason=intent.parameters.get("reason"),
        )
        return OperatorResult(
            intent_id=intent.intent_id,
            status="ok",
            correlation_id=intent.correlation_id,
            audit_id=intent.audit_id,
            payload={
                "attention_state": self.attention.state.value,
                "previous_state": previous.value,
                "transition": transition.to_dict(),
            },
            message_code="attention.state_changed",
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
