from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Mapping, Optional
from uuid import uuid4


SCHEMA_VERSION = "babbly.operator-intent.v1"


class SourceModality(str, Enum):
    VOICE = "voice"
    TUI = "tui"
    WEB = "web"
    EUD = "eud"
    TEST = "test"


class ClarificationState(str, Enum):
    NONE = "none"
    REQUIRED = "required"
    CONFIRMED = "confirmed"
    DENIED = "denied"


@dataclass(frozen=True)
class OperatorIntent:
    """Presentation-neutral operator intent.

    The contract deliberately contains no shell command and no execution
    authority. Voice, TUI, Web and EUD surfaces may differ in presentation,
    but equivalent actions must converge on this representation.
    """

    intent_id: str
    source_modality: SourceModality
    parameters: Mapping[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    target_ref: Optional[str] = None
    context_ref: Optional[str] = None
    confidence: Optional[float] = None
    clarification_state: ClarificationState = ClarificationState.NONE
    confirmation_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    audit_id: str = field(default_factory=lambda: str(uuid4()))

    def semantic_payload(self) -> dict[str, Any]:
        """Return modality-independent semantics for equivalence checks."""
        return {
            "schema_version": SCHEMA_VERSION,
            "intent_id": self.intent_id,
            "version": self.version,
            "target_ref": self.target_ref,
            "context_ref": self.context_ref,
            "parameters": dict(self.parameters),
            "clarification_state": self.clarification_state.value,
            "confirmation_id": self.confirmation_id,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.semantic_payload()
        payload.update(
            {
                "source_modality": self.source_modality.value,
                "confidence": self.confidence,
                "correlation_id": self.correlation_id,
                "audit_id": self.audit_id,
            }
        )
        return payload

    def with_modality(self, modality: SourceModality) -> "OperatorIntent":
        return replace(self, source_modality=modality)


@dataclass(frozen=True)
class OperatorResult:
    intent_id: str
    status: str
    correlation_id: str
    audit_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    confirmation_id: Optional[str] = None
    message_code: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "intent_id": self.intent_id,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "audit_id": self.audit_id,
            "confirmation_id": self.confirmation_id,
            "message_code": self.message_code,
            "payload": dict(self.payload),
        }


@dataclass
class OperatorContext:
    current_target: Optional[str] = None
    current_context: Optional[str] = None
    pending_confirmation_id: Optional[str] = None
    pending_intent: Optional[OperatorIntent] = None
    last_correlation_id: Optional[str] = None

    def bind(self, intent: OperatorIntent) -> OperatorIntent:
        """Carry task context across modality changes without inventing it."""
        target = intent.target_ref or self.current_target
        context = intent.context_ref or self.current_context
        bound = replace(intent, target_ref=target, context_ref=context)
        if target:
            self.current_target = target
        if context:
            self.current_context = context
        self.last_correlation_id = intent.correlation_id
        return bound

    def set_pending(self, intent: OperatorIntent, confirmation_id: Optional[str] = None) -> OperatorIntent:
        identifier = confirmation_id or intent.confirmation_id or str(uuid4())
        pending = replace(
            intent,
            clarification_state=ClarificationState.REQUIRED,
            confirmation_id=identifier,
        )
        self.pending_confirmation_id = identifier
        self.pending_intent = pending
        return pending

    def resolve_pending(self, approved: bool, modality: SourceModality) -> Optional[OperatorIntent]:
        pending = self.pending_intent
        if pending is None:
            return None
        state = ClarificationState.CONFIRMED if approved else ClarificationState.DENIED
        resolved = replace(pending, source_modality=modality, clarification_state=state)
        self.pending_confirmation_id = None
        self.pending_intent = None
        self.last_correlation_id = resolved.correlation_id
        return resolved
