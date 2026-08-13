from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, runtime_checkable
from uuid import uuid4


SCHEMA_VERSION = "babbly.action-request.v1"


class RiskClass(str, Enum):
    """Advisory risk/confirmation class. It never removes the human approval
    requirement; higher risk may only add friction in a surface, not authority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RequestState(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    COMPLETED = "completed"
    FAILED = "failed"


# Terminal states cannot transition further.
_TERMINAL = {
    RequestState.DENIED,
    RequestState.CANCELLED,
    RequestState.TIMED_OUT,
    RequestState.COMPLETED,
    RequestState.FAILED,
}


class RequestError(Exception):
    """Raised on an illegal controlled-request transition."""


@dataclass(frozen=True)
class ActionRequest:
    """The only contract by which Babbly asks an external executor to change state.

    It is deliberately distinct from the read-only SituationSnapshot/Recommendation
    model and carries no shell string, credentials, or authority grant. The action
    is an identifier; parameters are normalized values. Approval is always a
    separate, explicit human step (see ControlledRequestManager).
    """

    action: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    target_ref: Optional[str] = None
    context_ref: Optional[str] = None
    risk_class: RiskClass = RiskClass.MEDIUM
    requested_by_modality: str = "unknown"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    audit_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "action": self.action,
            "parameters": dict(self.parameters),
            "target_ref": self.target_ref,
            "context_ref": self.context_ref,
            "risk_class": self.risk_class.value,
            "requested_by_modality": self.requested_by_modality,
            "correlation_id": self.correlation_id,
            "audit_id": self.audit_id,
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome returned by an external executor after an approved dispatch."""

    ok: bool
    detail: str = ""
    external_ref: Optional[str] = None
    rejected_by_executor: bool = False


@runtime_checkable
class ActionExecutor(Protocol):
    """Write-capable external authority.

    A distinct method name (``execute_action``) keeps read-only situation
    adapters from accidentally satisfying the write contract. The executor
    retains final authority: it may reject an already human-approved request.
    """

    def execute_action(self, request: ActionRequest) -> ExecutionResult:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    request_id: str
    event: str
    from_state: Optional[str]
    to_state: str
    modality: str
    at: float
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "request_id": self.request_id,
            "event": self.event,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "modality": self.modality,
            "at": self.at,
            "detail": self.detail,
        }


@dataclass
class _Tracked:
    request: ActionRequest
    state: RequestState
    created_at: float
    deadline: Optional[float]
    result: Optional[ExecutionResult] = None


class ControlledRequestManager:
    """State machine and audit trail for controlled write requests.

    Read-only situation data never flows through here. The manager holds pending
    requests, enforces the approve/deny/cancel/timeout transitions, and dispatches
    only human-approved requests to an external executor. A clock is injected so
    timeout behaviour is deterministic under test.
    """

    def __init__(
        self,
        *,
        dry_run: bool = False,
        default_timeout_seconds: Optional[float] = 120.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.dry_run = bool(dry_run)
        self.default_timeout_seconds = default_timeout_seconds
        self._clock = clock or time.monotonic
        self._tracked: Dict[str, _Tracked] = {}
        self._audit: List[AuditEntry] = []

    # -- introspection --------------------------------------------------------

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in self._audit]

    def state_of(self, request_id: str) -> RequestState:
        return self._require(request_id).state

    def result_of(self, request_id: str) -> Optional[ExecutionResult]:
        return self._require(request_id).result

    def pending_ids(self) -> List[str]:
        self._expire_overdue()
        return [rid for rid, t in self._tracked.items() if t.state == RequestState.PENDING_APPROVAL]

    # -- transitions ----------------------------------------------------------

    def submit(self, request: ActionRequest, *, timeout_seconds: Optional[float] = "default") -> RequestState:
        if request.request_id in self._tracked:
            raise RequestError(f"duplicate request_id: {request.request_id}")
        now = self._clock()
        window = self.default_timeout_seconds if timeout_seconds == "default" else timeout_seconds
        deadline = None if window is None else now + float(window)
        self._tracked[request.request_id] = _Tracked(
            request=request,
            state=RequestState.PENDING_APPROVAL,
            created_at=now,
            deadline=deadline,
        )
        self._record(request.request_id, "submit", None, RequestState.PENDING_APPROVAL, request.requested_by_modality)
        return RequestState.PENDING_APPROVAL

    def approve(self, request_id: str, modality: str) -> RequestState:
        return self._decide(request_id, modality, approve=True)

    def deny(self, request_id: str, modality: str, *, detail: Optional[str] = None) -> RequestState:
        return self._decide(request_id, modality, approve=False, detail=detail)

    def _decide(self, request_id: str, modality: str, *, approve: bool, detail: Optional[str] = None) -> RequestState:
        tracked = self._require(request_id)
        self._expire_overdue()
        tracked = self._require(request_id)
        if tracked.state != RequestState.PENDING_APPROVAL:
            raise RequestError(
                f"cannot {'approve' if approve else 'deny'} request in state {tracked.state.value}"
            )
        target = RequestState.APPROVED if approve else RequestState.DENIED
        prev = tracked.state
        tracked.state = target
        self._record(request_id, "approve" if approve else "deny", prev, target, modality, detail)
        return target

    def cancel(self, request_id: str, modality: str, *, detail: Optional[str] = None) -> RequestState:
        tracked = self._require(request_id)
        if tracked.state in _TERMINAL:
            raise RequestError(f"cannot cancel request in terminal state {tracked.state.value}")
        # Cancellation is allowed while pending or after approval but before dispatch.
        prev = tracked.state
        tracked.state = RequestState.CANCELLED
        self._record(request_id, "cancel", prev, RequestState.CANCELLED, modality, detail)
        return RequestState.CANCELLED

    def dispatch(self, request_id: str, executor: Optional[ActionExecutor], *, modality: str = "system") -> RequestState:
        """Send an approved request to the external executor.

        Only APPROVED requests dispatch. Under dry_run the executor is not called.
        The executor may still reject an approved request; external systems keep
        final authority.
        """
        tracked = self._require(request_id)
        if tracked.state != RequestState.APPROVED:
            raise RequestError(f"cannot dispatch request in state {tracked.state.value}")

        if self.dry_run:
            result = ExecutionResult(ok=True, detail="dry_run")
            tracked.result = result
            tracked.state = RequestState.COMPLETED
            self._record(request_id, "dispatch_dry_run", RequestState.APPROVED, RequestState.COMPLETED, modality, "dry_run")
            return tracked.state

        if executor is None:
            raise RequestError("no executor supplied for a live dispatch")

        result = executor.execute_action(tracked.request)
        tracked.result = result
        if result.ok:
            tracked.state = RequestState.COMPLETED
            self._record(request_id, "dispatch", RequestState.APPROVED, RequestState.COMPLETED, modality, result.detail)
        else:
            tracked.state = RequestState.FAILED
            event = "executor_rejected" if result.rejected_by_executor else "dispatch_failed"
            self._record(request_id, event, RequestState.APPROVED, RequestState.FAILED, modality, result.detail)
        return tracked.state

    def poll_timeouts(self) -> List[str]:
        """Expire any pending request past its deadline; return the affected ids."""
        return self._expire_overdue()

    # -- internals ------------------------------------------------------------

    def _expire_overdue(self) -> List[str]:
        now = self._clock()
        expired: List[str] = []
        for rid, tracked in self._tracked.items():
            if (
                tracked.state == RequestState.PENDING_APPROVAL
                and tracked.deadline is not None
                and now >= tracked.deadline
            ):
                tracked.state = RequestState.TIMED_OUT
                self._record(rid, "timeout", RequestState.PENDING_APPROVAL, RequestState.TIMED_OUT, "system")
                expired.append(rid)
        return expired

    def _require(self, request_id: str) -> _Tracked:
        tracked = self._tracked.get(request_id)
        if tracked is None:
            raise RequestError(f"unknown request_id: {request_id}")
        return tracked

    def _record(
        self,
        request_id: str,
        event: str,
        from_state: Optional[RequestState],
        to_state: RequestState,
        modality: str,
        detail: Optional[str] = None,
    ) -> None:
        self._audit.append(
            AuditEntry(
                seq=len(self._audit) + 1,
                request_id=request_id,
                event=event,
                from_state=from_state.value if from_state else None,
                to_state=to_state.value,
                modality=str(modality),
                at=self._clock(),
                detail=detail,
            )
        )
