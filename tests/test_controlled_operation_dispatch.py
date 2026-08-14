from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.request import ActionRequest, ControlledRequestManager, ExecutionResult, RiskClass


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class RecordingExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute_action(self, request: ActionRequest) -> ExecutionResult:
        self.calls.append(request)
        return self.result


def _wired_runtime(executor, *, dry_run=False):
    return OperatorIntentRuntime(
        dry_run=dry_run,
        request_manager=ControlledRequestManager(clock=FakeClock()),
        action_executor=executor,
        write_actions={"isolate.target": RiskClass.HIGH},
    )


def _confirm_operation(runtime, operation, *, target="target-A", modality=SourceModality.VOICE):
    runtime.submit(
        OperatorIntent(intent_id="operation.run", source_modality=modality,
                       parameters={"operation": operation}, target_ref=target)
    )
    return runtime.resolve_pending(True, SourceModality.WEB)


def test_confirmed_write_action_dispatches_through_contract():
    executor = RecordingExecutor(ExecutionResult(ok=True, external_ref="edge-7", detail="isolated"))
    runtime = _wired_runtime(executor)
    result = _confirm_operation(runtime, "isolate.target")
    assert result.status == "completed"
    assert result.message_code == "operation.completed"
    assert result.payload["external_ref"] == "edge-7"
    assert [r.action for r in executor.calls] == ["isolate.target"]
    # the full lifecycle is auditable
    events = [e["event"] for e in runtime.request_manager.audit_log]
    assert events == ["submit", "approve", "dispatch"]


def test_executor_rejection_is_reported_and_authoritative():
    executor = RecordingExecutor(ExecutionResult(ok=False, rejected_by_executor=True, detail="edge policy denied"))
    runtime = _wired_runtime(executor)
    result = _confirm_operation(runtime, "isolate.target")
    assert result.status == "failed"
    assert result.message_code == "operation.executor_rejected"
    assert result.payload["detail"] == "edge policy denied"


def test_dry_run_does_not_call_executor():
    executor = RecordingExecutor(ExecutionResult(ok=True))
    runtime = _wired_runtime(executor, dry_run=True)
    result = _confirm_operation(runtime, "isolate.target")
    assert result.status == "dry_run"
    assert result.message_code == "operation.dry_run"
    assert executor.calls == []


def test_non_write_operation_stays_at_registered_boundary():
    executor = RecordingExecutor(ExecutionResult(ok=True))
    runtime = _wired_runtime(executor)
    result = _confirm_operation(runtime, "recon-alpha")  # not in write_actions
    assert result.status == "ready_for_registered_executor"
    assert result.message_code == "operation.ready"
    assert executor.calls == []


def test_without_manager_write_wiring_is_inactive():
    runtime = OperatorIntentRuntime(write_actions={"isolate.target": RiskClass.HIGH})  # no manager
    result = _confirm_operation(runtime, "isolate.target")
    assert result.status == "ready_for_registered_executor"


def test_confirmation_is_still_required_before_dispatch():
    executor = RecordingExecutor(ExecutionResult(ok=True))
    runtime = _wired_runtime(executor)
    pending = runtime.submit(
        OperatorIntent(intent_id="operation.run", source_modality=SourceModality.VOICE,
                       parameters={"operation": "isolate.target"}, target_ref="target-A")
    )
    assert pending.status == "confirmation_required"
    assert executor.calls == []  # nothing dispatched before approval
