from babbly.core.attention import OperatorAttentionState
from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.session import (
    PROTOCOL_VERSION,
    CoreSessionEndpoint,
    ReferenceEudClient,
    situation_is_stale,
)
from babbly.core.situation import Observation, SituationSnapshot


class FakeClock:
    def __init__(self, start=1000.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class _FakeEngine:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def collect(self):
        return self._snapshot


def _snapshot():
    snap = SituationSnapshot()
    snap.set_system_state("azazel", "online")
    snap.add_observation(Observation(source="azazel", category="alert", summary="探索通信を検出", severity="warning"))
    return snap


def _endpoint(**kw):
    kw.setdefault("runtime", OperatorIntentRuntime(situation_engine=_FakeEngine(_snapshot())))
    return CoreSessionEndpoint(**kw)


def test_connect_returns_welcome_with_versioned_situation():
    client = ReferenceEudClient(_endpoint())
    welcome = client.connect()
    assert welcome["type"] == "welcome"
    assert welcome["protocol_version"] == PROTOCOL_VERSION
    assert client.session_id
    env = welcome["situation"]
    assert "revision" in env and "generated_at" in env
    assert env["view"]["status"] == "warning"


def test_incompatible_protocol_version_is_rejected():
    ep = _endpoint()
    resp = ep.handle({"type": "hello", "protocol_version": "babbly.eud-session.v2"})
    assert resp["type"] == "error"
    assert resp["code"] == "incompatible_version"


def test_auth_token_is_enforced_when_configured():
    ep = _endpoint(expected_token="s3cret")
    assert ep.handle({"type": "hello", "protocol_version": PROTOCOL_VERSION})["code"] == "unauthorized"
    ok = ep.handle({"type": "hello", "protocol_version": PROTOCOL_VERSION, "auth_token": "s3cret"})
    assert ok["type"] == "welcome"


def test_unknown_session_fails_closed():
    ep = _endpoint()
    assert ep.handle({"type": "get_situation", "session_id": "nope"})["code"] == "unknown_session"
    assert ep.handle({"type": "resume", "session_id": "nope"})["code"] == "unknown_session"


def test_reference_client_submits_non_executing_intent():
    ep = _endpoint()
    client = ReferenceEudClient(ep)
    client.connect()
    resp = client.submit_intent("attention.set", {"state": "critical"})
    assert resp["type"] == "intent_result"
    assert resp["result"]["status"] == "ok"
    assert ep.runtime.attention.state is OperatorAttentionState.CRITICAL
    assert resp["situation"]["view"]["attention_state"] == "critical"


def test_write_intents_are_not_exposed_over_the_session():
    ep = _endpoint()
    client = ReferenceEudClient(ep)
    client.connect()
    resp = client.submit_intent("operation.run", {"operation": "recon-alpha"})
    assert resp["type"] == "error"
    assert resp["code"] == "intent_not_allowed"
    assert ep.runtime.context.pending_intent is None


def test_duplicate_submission_is_idempotent_and_not_replayed():
    ep = _endpoint()
    client = ReferenceEudClient(ep)
    client.connect()
    first = client.submit_intent("attention.set", {"state": "heads_up"}, client_msg_id="m1")
    assert first["deduplicated"] is False
    assert len(ep.runtime.attention.history) == 1

    second = client.submit_intent("attention.set", {"state": "heads_up"}, client_msg_id="m1")
    assert second["deduplicated"] is True
    # the transition was NOT applied a second time
    assert len(ep.runtime.attention.history) == 1


def test_reconnect_resyncs_and_preserves_pending_confirmation():
    ep = _endpoint()
    client = ReferenceEudClient(ep)
    client.connect()

    # A voice-initiated operation leaves a pending confirmation in the shared runtime.
    ep.runtime.submit(
        OperatorIntent(
            intent_id="operation.run",
            source_modality=SourceModality.VOICE,
            parameters={"operation": "recon-alpha"},
            target_ref="target-A",
        )
    )

    client.disconnect()
    resumed = client.reconnect()
    assert resumed["type"] == "resumed"
    pending = resumed["situation"]["view"]["pending_confirmation"]
    assert pending is not None
    assert pending["operation"] == "recon-alpha"
    assert pending["target_ref"] == "target-A"


def test_stale_situation_is_detectable():
    clock = FakeClock()
    ep = _endpoint(clock=clock)
    client = ReferenceEudClient(ep)
    client.connect()
    env = client.last_situation
    assert situation_is_stale(env, clock(), max_age_seconds=5.0) is False
    clock.advance(10.0)
    assert situation_is_stale(env, clock(), max_age_seconds=5.0) is True


def test_oversized_message_is_rejected():
    ep = _endpoint(max_message_bytes=200)
    resp = ep.handle({"type": "hello", "protocol_version": PROTOCOL_VERSION, "blob": "x" * 500})
    assert resp["type"] == "error"
    assert resp["code"] == "message_too_large"


def test_ping_pong_and_unknown_type():
    ep = _endpoint()
    assert ep.handle({"type": "ping"})["type"] == "pong"
    assert ep.handle({"type": "nonsense"})["code"] == "unknown_type"
