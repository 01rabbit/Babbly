import json

import pytest

from babbly.adapters.azazel import AzazelAdapter
from babbly.adapters.azazel_edge_transport import (
    AzazelEdgeStatusProvider,
    AzazelEdgeTransportError,
    translate_edge_state,
)
from babbly.adapters.factory import create_situation_engine
from babbly.core.engine import SituationEngine


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.closed = False

    def getcode(self):
        return self.status

    def read(self, _limit=-1):
        return self.payload

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return FakeResponse(self.payload)


def status_payload():
    return {
        "ok": True,
        "status_view": {
            "schema_version": "1.0",
            "product": "edge",
            "generated_at": "2026-08-13T00:00:00Z",
            "trace_id": "trace-1",
            "mode": {"name": "shield", "since": "2026-08-13T00:00:00Z"},
            "posture": "degraded",
            "headline": "edge · shield · degraded",
            "reasons": ["repeated local probing"],
            "operator_wording": "Maintain observation while the probe remains active.",
            "current_action": {"kind": "throttle", "target": "client-a"},
            "next_actions": ["review evidence", "verify client identity"],
            "health": [
                {"key": "suricata", "label": "crit=1 warn=0", "status": "critical"},
                {"key": "uplink", "label": "CONNECTED", "status": "ok"},
            ],
            "evidence_ids": ["ev-1"],
            "product_view": {"edge_snapshot": {"user_state": "DEGRADED"}},
        },
    }


def test_translates_fabric_status_view_without_treating_current_action_as_request():
    translated = translate_edge_state(status_payload())

    assert translated["system"] == "azazel-edge"
    assert translated["state"] == "degraded"
    assert translated["headline"] == "edge · shield · degraded"
    assert any(item["category"] == "control.current_action" for item in translated["alerts"])
    assert translated["recommendations"][0]["action"] == "review evidence"
    assert translated["metadata"]["trace_id"] == "trace-1"


def test_provider_uses_canonical_token_header_and_short_ttl_cache():
    opener = FakeOpener(json.dumps(status_payload()).encode("utf-8"))
    provider = AzazelEdgeStatusProvider(
        "http://127.0.0.1:8084",
        token="secret-token",
        cache_ttl_sec=5.0,
        opener=opener,
    )

    first = provider()
    second = provider()

    assert first == second
    assert len(opener.calls) == 1
    request, timeout = opener.calls[0]
    assert request.full_url == "http://127.0.0.1:8084/api/state"
    assert dict(request.header_items())["X-azazel-token"] == "secret-token"
    assert timeout == 2.0


def test_status_view_flows_into_situation_engine_as_read_only_advice():
    provider = lambda: translate_edge_state(status_payload())
    snapshot = SituationEngine([AzazelAdapter(provider)]).collect()

    assert snapshot.systems["azazel"] == "online"
    assert snapshot.status == "critical"
    assert snapshot.recommendations[0].action == "review evidence"
    assert snapshot.recommendations[0].advisory_only is True


def test_native_edge_state_is_supported_only_as_compatibility_fallback():
    translated = translate_edge_state(
        {"user_state": "NORMAL", "suricata_critical": 0, "suricata_warning": 0}
    )
    assert translated["state"] == "NORMAL"
    assert translated["metadata"]["status_view"] == "unavailable"
    assert translated["recommendations"] == []


def test_invalid_json_fails_closed():
    provider = AzazelEdgeStatusProvider(
        "http://127.0.0.1:8084",
        opener=FakeOpener(b"not-json"),
    )
    with pytest.raises(AzazelEdgeTransportError):
        provider()


def test_factory_is_disabled_by_default_and_reads_token_from_environment(monkeypatch):
    assert create_situation_engine({}).adapters == []

    monkeypatch.setenv("BABBLY_TEST_EDGE_TOKEN", "env-secret")
    engine = create_situation_engine(
        {
            "AZAZEL_EDGE_ENABLED": True,
            "AZAZEL_EDGE_URL": "http://127.0.0.1:8084",
            "AZAZEL_EDGE_TOKEN_ENV": "BABBLY_TEST_EDGE_TOKEN",
        }
    )
    assert len(engine.adapters) == 1
    assert engine.adapters[0].status_provider.token == "env-secret"
