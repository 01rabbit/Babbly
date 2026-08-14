import io
import json

from babbly.adapters.azazel_edge_action import (
    ACTION_PROPOSAL_SCHEMA,
    AzazelEdgeActionExecutor,
    interpret_edge_decision,
    translate_action_request,
)
from babbly.adapters.factory import create_action_executor, parse_write_actions
from babbly.core.request import ActionRequest, RiskClass


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._buf = io.BytesIO(body)
        self._status = status

    def getcode(self):
        return self._status

    def read(self, n=-1):
        return self._buf.read(n)

    def close(self):
        pass


def _opener(body, status=200, capture=None):
    def opener(request, timeout=None):
        if capture is not None:
            capture["request"] = request
        return FakeResponse(body, status)
    return opener


def _request():
    return ActionRequest(action="isolate.target", parameters={"scope": "host"}, target_ref="target-A",
                         risk_class=RiskClass.HIGH, requested_by_modality="voice")


def test_translate_has_no_shell_string():
    env = translate_action_request(_request())
    assert env["schema_version"] == ACTION_PROPOSAL_SCHEMA
    assert env["action"] == "isolate.target"
    assert env["target"] == "target-A"
    assert "command" not in env and "shell" not in env


def test_interpret_decisions():
    assert interpret_edge_decision({"decision": "approved", "external_ref": "e1"}).ok is True
    rej = interpret_edge_decision({"decision": "rejected", "reason": "policy"})
    assert rej.ok is False and rej.rejected_by_executor is True
    unknown = interpret_edge_decision({"decision": "wat"})
    assert unknown.ok is False and unknown.rejected_by_executor is True
    empty = interpret_edge_decision({})
    assert empty.ok is False and empty.rejected_by_executor is False  # no decision -> fail closed, not a denial


def test_executor_posts_proposal_and_reads_approval():
    capture = {}
    body = json.dumps({"decision": "approved", "external_ref": "edge-9", "detail": "done"}).encode()
    ex = AzazelEdgeActionExecutor("http://127.0.0.1:8084", token="t0k", opener=_opener(body, capture=capture))
    result = ex.execute_action(_request())
    assert result.ok is True and result.external_ref == "edge-9"
    sent = capture["request"]
    assert sent.method == "POST"
    assert sent.full_url == "http://127.0.0.1:8084/api/action"
    assert sent.headers.get("X-azazel-token") == "t0k"
    assert json.loads(sent.data.decode())["action"] == "isolate.target"


def test_executor_http_error_is_not_an_authoritative_denial():
    ex = AzazelEdgeActionExecutor("http://127.0.0.1:8084", opener=_opener(b"", status=503))
    result = ex.execute_action(_request())
    assert result.ok is False and result.rejected_by_executor is False


def test_executor_invalid_json_fails_closed():
    ex = AzazelEdgeActionExecutor("http://127.0.0.1:8084", opener=_opener(b"{not json"))
    result = ex.execute_action(_request())
    assert result.ok is False and result.rejected_by_executor is False


def test_factory_disabled_by_default_and_requires_actions():
    assert create_action_executor({}) is None
    assert create_action_executor({"AZAZEL_EDGE_WRITE_ENABLED": True}) is None  # no actions
    executor = create_action_executor(
        {"AZAZEL_EDGE_WRITE_ENABLED": True, "AZAZEL_EDGE_WRITE_ACTIONS": ["isolate.target"],
         "AZAZEL_EDGE_URL": "http://127.0.0.1:8084"}
    )
    assert isinstance(executor, AzazelEdgeActionExecutor)


def test_parse_write_actions_forms():
    assert parse_write_actions({"AZAZEL_EDGE_WRITE_ACTIONS": ["a", "b"]}) == {"a": RiskClass.HIGH, "b": RiskClass.HIGH}
    assert parse_write_actions({"AZAZEL_EDGE_WRITE_ACTIONS": {"a": "low"}}) == {"a": RiskClass.LOW}
    assert parse_write_actions({}) == {}
