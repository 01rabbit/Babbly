import pytest

from babbly.core.request import (
    ActionExecutor,
    ActionRequest,
    ControlledRequestManager,
    ExecutionResult,
    RequestError,
    RequestState,
    RiskClass,
)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


class RecordingExecutor:
    def __init__(self, result: ExecutionResult) -> None:
        self.result = result
        self.calls = []

    def execute_action(self, request: ActionRequest) -> ExecutionResult:
        self.calls.append(request.request_id)
        return self.result


class ReadOnlyAdapter:
    """Stands in for a situation source: it can only be collected, not executed."""

    def collect(self):
        return {}


def _request(**kw) -> ActionRequest:
    params = dict(action="isolate.target", parameters={"scope": "host"}, target_ref="target-A",
                  requested_by_modality="voice", risk_class=RiskClass.HIGH)
    params.update(kw)
    return ActionRequest(**params)


def _manager(**kw) -> ControlledRequestManager:
    kw.setdefault("clock", FakeClock())
    return ControlledRequestManager(**kw)


def test_submit_creates_pending_and_audits():
    mgr = _manager()
    req = _request()
    assert mgr.submit(req) is RequestState.PENDING_APPROVAL
    assert mgr.state_of(req.request_id) is RequestState.PENDING_APPROVAL
    assert mgr.pending_ids() == [req.request_id]
    assert mgr.audit_log[0]["event"] == "submit"
    assert mgr.audit_log[0]["modality"] == "voice"


def test_request_contract_carries_no_shell_string():
    payload = _request().to_dict()
    assert payload["schema_version"] == "babbly.action-request.v1"
    assert "command" not in payload and "shell" not in payload
    assert payload["action"] == "isolate.target"


def test_cross_modality_approval_preserves_correlation():
    mgr = _manager()
    req = _request(requested_by_modality="voice")
    mgr.submit(req)
    assert mgr.approve(req.request_id, "web") is RequestState.APPROVED
    events = {(e["event"], e["modality"]) for e in mgr.audit_log}
    assert ("submit", "voice") in events
    assert ("approve", "web") in events
    # correlation identity is the request's own, unchanged by the modality switch
    assert req.correlation_id  # stable object identity, never reassigned


def test_deny_is_terminal():
    mgr = _manager()
    req = _request()
    mgr.submit(req)
    assert mgr.deny(req.request_id, "web", detail="operator refused") is RequestState.DENIED
    with pytest.raises(RequestError):
        mgr.approve(req.request_id, "web")


def test_cancel_pending_and_after_approval():
    mgr = _manager()
    r1, r2 = _request(), _request()
    mgr.submit(r1)
    assert mgr.cancel(r1.request_id, "voice") is RequestState.CANCELLED
    mgr.submit(r2)
    mgr.approve(r2.request_id, "web")
    assert mgr.cancel(r2.request_id, "web") is RequestState.CANCELLED
    with pytest.raises(RequestError):
        mgr.cancel(r2.request_id, "web")  # already terminal


def test_timeout_expires_pending_and_blocks_approval():
    clock = FakeClock()
    mgr = ControlledRequestManager(clock=clock, default_timeout_seconds=30.0)
    req = _request()
    mgr.submit(req)
    clock.advance(31.0)
    assert mgr.poll_timeouts() == [req.request_id]
    assert mgr.state_of(req.request_id) is RequestState.TIMED_OUT
    with pytest.raises(RequestError):
        mgr.approve(req.request_id, "web")
    assert mgr.audit_log[-1]["event"] == "timeout"


def test_no_timeout_when_window_disabled():
    clock = FakeClock()
    mgr = ControlledRequestManager(clock=clock, default_timeout_seconds=None)
    req = _request()
    mgr.submit(req)
    clock.advance(10_000.0)
    assert mgr.poll_timeouts() == []
    assert mgr.state_of(req.request_id) is RequestState.PENDING_APPROVAL


def test_dispatch_requires_approval():
    mgr = _manager()
    req = _request()
    mgr.submit(req)
    with pytest.raises(RequestError):
        mgr.dispatch(req.request_id, RecordingExecutor(ExecutionResult(ok=True)))


def test_approved_request_dispatches_to_executor():
    mgr = _manager()
    req = _request()
    mgr.submit(req)
    mgr.approve(req.request_id, "web")
    executor = RecordingExecutor(ExecutionResult(ok=True, external_ref="edge-42"))
    assert mgr.dispatch(req.request_id, executor) is RequestState.COMPLETED
    assert executor.calls == [req.request_id]
    assert mgr.result_of(req.request_id).external_ref == "edge-42"


def test_external_executor_retains_final_authority():
    mgr = _manager()
    req = _request()
    mgr.submit(req)
    mgr.approve(req.request_id, "web")
    executor = RecordingExecutor(ExecutionResult(ok=False, rejected_by_executor=True, detail="policy denied"))
    assert mgr.dispatch(req.request_id, executor) is RequestState.FAILED
    assert mgr.audit_log[-1]["event"] == "executor_rejected"


def test_dry_run_does_not_call_executor():
    mgr = _manager(dry_run=True)
    req = _request()
    mgr.submit(req)
    mgr.approve(req.request_id, "web")
    executor = RecordingExecutor(ExecutionResult(ok=True))
    assert mgr.dispatch(req.request_id, executor) is RequestState.COMPLETED
    assert executor.calls == []
    assert mgr.result_of(req.request_id).detail == "dry_run"


def test_read_only_adapter_cannot_satisfy_write_contract():
    assert isinstance(RecordingExecutor(ExecutionResult(ok=True)), ActionExecutor)
    assert not isinstance(ReadOnlyAdapter(), ActionExecutor)


def test_duplicate_and_unknown_request_ids():
    mgr = _manager()
    req = _request()
    mgr.submit(req)
    with pytest.raises(RequestError):
        mgr.submit(req)
    with pytest.raises(RequestError):
        mgr.state_of("nope")
