import json
import threading
import urllib.request

from babbly.core.attention import OperatorAttentionState
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.situation import Observation, Recommendation, SituationSnapshot
from babbly.web.server import SituationWebApp, make_server


class _FakeEngine:
    """Return a fixed snapshot so surface tests are deterministic."""

    def __init__(self, snapshot: SituationSnapshot) -> None:
        self._snapshot = snapshot

    def collect(self) -> SituationSnapshot:
        return self._snapshot


def _snapshot(*, degraded: bool = False) -> SituationSnapshot:
    snapshot = SituationSnapshot()
    snapshot.set_system_state("azazel", "online")
    if degraded:
        snapshot.set_system_state("kali", "error")
    snapshot.add_observation(Observation(source="azazel", category="state", summary="Edge稼働中", severity="info"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="探索通信を検出", severity="warning"))
    snapshot.add_observation(Observation(source="azazel", category="alert", summary="再送を検出", severity="caution"))
    snapshot.add_recommendation(Recommendation(source="azazel", action="Shield維持", reason="継続観測", priority=1))
    return snapshot


def _app(snapshot=None) -> SituationWebApp:
    runtime = OperatorIntentRuntime(situation_engine=_FakeEngine(snapshot or _snapshot()))
    return SituationWebApp(runtime)


def _json_body(body: bytes):
    return json.loads(body.decode("utf-8"))


def test_index_is_served_as_responsive_html():
    status, content_type, body = _app().handle("GET", "/")
    assert status == 200
    assert "text/html" in content_type
    text = body.decode("utf-8")
    assert "<title>Babbly Situation" in text
    assert "width=device-width" in text  # responsive viewport


def test_api_situation_matches_snapshot_via_canonical_intent():
    status, content_type, body = _app().handle("GET", "/api/situation")
    assert status == 200
    assert "application/json" in content_type
    view = _json_body(body)
    assert view["attention_state"] == "normal"
    assert view["status"] == "warning"
    assert [o["summary"] for o in view["observations"]] == ["探索通信を検出", "再送を検出", "Edge稼働中"]
    assert view["recommendation"]["action"] == "Shield維持"


def test_visual_action_reaches_canonical_intent_and_changes_density():
    app = _app()
    body = json.dumps({"intent_id": "attention.set", "parameters": {"state": "critical"}}).encode()
    status, _ct, resp = app.handle("POST", "/api/intent", body)
    assert status == 200
    data = _json_body(resp)
    assert data["result"]["status"] == "ok"
    assert data["result"]["message_code"] == "attention.state_changed"
    # the runtime's shared attention state changed...
    assert app.runtime.attention.state is OperatorAttentionState.CRITICAL
    # ...and the returned + subsequent view render at the new density.
    assert data["view"]["attention_state"] == "critical"
    assert len(data["view"]["observations"]) == 1
    follow = _json_body(app.handle("GET", "/api/situation")[2])
    assert follow["attention_state"] == "critical"


def test_web_surface_rejects_non_allowlisted_intents():
    app = _app()
    body = json.dumps({"intent_id": "operation.run", "parameters": {"operation": "recon-alpha"}}).encode()
    status, _ct, resp = app.handle("POST", "/api/intent", body)
    assert status == 400
    assert _json_body(resp)["error"] == "intent_not_allowed"
    # the rejected write never created a pending confirmation
    assert app.runtime.context.pending_intent is None


def test_web_surface_rejects_malformed_json():
    status, _ct, resp = _app().handle("POST", "/api/intent", b"{not json")
    assert status == 400
    assert _json_body(resp)["error"] == "invalid_json"


def test_unknown_route_is_404_not_a_crash():
    status, _ct, resp = _app().handle("GET", "/nope")
    assert status == 404
    assert _json_body(resp)["error"] == "not_found"


def test_degraded_adapter_is_represented():
    view = _json_body(_app(_snapshot(degraded=True)).handle("GET", "/api/situation")[2])
    assert view["degraded"] is True
    assert view["systems_summary"]["error"] == 1


def test_end_to_end_over_a_real_socket():
    server = make_server(_app(), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[0], server.server_address[1]
        with urllib.request.urlopen(f"http://{host}:{port}/api/situation", timeout=5) as resp:
            assert resp.status == 200
            view = json.loads(resp.read().decode("utf-8"))
            assert view["schema"] == "babbly.situation-view.v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
