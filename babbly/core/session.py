from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.situation import SituationSnapshot
from babbly.core.surface import build_situation_view


PROTOCOL_VERSION = "babbly.eud-session.v1"
PROTOCOL_MAJOR = 1

# The EUD is a presentation/input client. It may read situation state and change
# presentation, but write-capable requests are NOT exposed over the session
# until the controlled request/approval path (#18) is wired in. This mirrors the
# web surface allowlist.
ALLOWED_SESSION_INTENTS = {
    "situation.report",
    "recommendation.explain",
    "attention.status",
    "attention.set",
}

DEFAULT_MAX_MESSAGE_BYTES = 64 * 1024


@dataclass
class _Session:
    session_id: str
    created_at: float
    last_seen_at: float
    # Idempotency: cache the response for each client message id so a resend
    # (e.g. after reconnect) returns the same result instead of re-applying it.
    seen_messages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    connected: bool = True


def _major(version: str) -> Optional[int]:
    tail = version.rsplit(".v", 1)
    if len(tail) == 2 and tail[1].isdigit():
        return int(tail[1])
    return None


class CoreSessionEndpoint:
    """Transport-neutral EUD <-> Core session contract (issue #19).

    `handle` is a pure function from a request message (dict) to a response
    message (dict), so it can be driven over any transport or directly in tests.
    All connected surfaces share ONE operator runtime, so switching between voice
    and a wearable EUD preserves target, attention state, and pending
    confirmation. The endpoint never exposes arbitrary shell execution.
    """

    def __init__(
        self,
        runtime: Optional[OperatorIntentRuntime] = None,
        *,
        clock: Optional[Callable[[], float]] = None,
        expected_token: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
    ) -> None:
        self.runtime = runtime or OperatorIntentRuntime()
        self._clock = clock or time.monotonic
        self._expected_token = expected_token
        self.capabilities = list(capabilities or ["situation", "attention", "intent", "resume"])
        self.max_message_bytes = int(max_message_bytes)
        self._sessions: Dict[str, _Session] = {}
        self._revision = 0  # bumped on each state-changing intent

    # -- public API -----------------------------------------------------------

    def handle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw = json.dumps(message)
        except (TypeError, ValueError):
            return self._error(None, "invalid_message", "message is not serializable")
        if len(raw.encode("utf-8")) > self.max_message_bytes:
            return self._error(message.get("session_id"), "message_too_large", "message exceeds size bound")

        mtype = message.get("type")
        handler = {
            "hello": self._hello,
            "get_situation": self._get_situation,
            "submit_intent": self._submit_intent,
            "resume": self._resume,
            "ping": self._ping,
        }.get(mtype)
        if handler is None:
            return self._error(message.get("session_id"), "unknown_type", f"unknown message type: {mtype!r}")
        return handler(message)

    # -- handlers -------------------------------------------------------------

    def _hello(self, message: Dict[str, Any]) -> Dict[str, Any]:
        auth = self._check_auth(message)
        if auth is not None:
            return auth
        client_version = str(message.get("protocol_version") or "")
        if _major(client_version) != PROTOCOL_MAJOR:
            return self._error(None, "incompatible_version", f"server requires {PROTOCOL_VERSION}")

        now = self._clock()
        session = _Session(session_id=str(uuid4()), created_at=now, last_seen_at=now)
        self._sessions[session.session_id] = session
        return {
            "type": "welcome",
            "protocol_version": PROTOCOL_VERSION,
            "session_id": session.session_id,
            "capabilities": list(self.capabilities),
            "situation": self._situation_envelope(),
        }

    def _get_situation(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session = self._touch(message.get("session_id"))
        if session is None:
            return self._error(message.get("session_id"), "unknown_session", "call hello or resume first")
        return {"type": "situation", "session_id": session.session_id, "situation": self._situation_envelope()}

    def _submit_intent(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session = self._touch(message.get("session_id"))
        if session is None:
            return self._error(message.get("session_id"), "unknown_session", "call hello or resume first")

        client_msg_id = message.get("client_msg_id")
        if client_msg_id is not None and client_msg_id in session.seen_messages:
            cached = dict(session.seen_messages[client_msg_id])
            cached["deduplicated"] = True
            return cached

        intent_id = message.get("intent_id")
        if intent_id not in ALLOWED_SESSION_INTENTS:
            response = self._error(
                session.session_id, "intent_not_allowed", f"{intent_id!r} is not exposed over the session"
            )
            self._remember(session, client_msg_id, response)
            return response

        parameters = message.get("parameters")
        intent = OperatorIntent(
            intent_id=intent_id,
            source_modality=SourceModality.EUD,
            parameters=parameters if isinstance(parameters, dict) else {},
            target_ref=message.get("target_ref"),
            context_ref=message.get("context_ref"),
        )
        result = self.runtime.submit(intent)
        if result.status == "ok":
            self._revision += 1
        response = {
            "type": "intent_result",
            "session_id": session.session_id,
            "result": result.to_dict(),
            "situation": self._situation_envelope(),
            "deduplicated": False,
        }
        self._remember(session, client_msg_id, response)
        return response

    def _resume(self, message: Dict[str, Any]) -> Dict[str, Any]:
        auth = self._check_auth(message)
        if auth is not None:
            return auth
        session_id = message.get("session_id")
        session = self._sessions.get(session_id) if session_id else None
        if session is None:
            # Fail closed: the client must re-hello. Reconnect never silently
            # replays state onto an unknown session.
            return self._error(session_id, "unknown_session", "session expired; send hello")
        session.connected = True
        session.last_seen_at = self._clock()
        return {
            "type": "resumed",
            "session_id": session.session_id,
            "situation": self._situation_envelope(),
        }

    def _ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": "pong", "session_id": message.get("session_id"), "at": self._clock()}

    # -- helpers --------------------------------------------------------------

    def _situation_envelope(self) -> Dict[str, Any]:
        result = self.runtime.submit(
            OperatorIntent(intent_id="situation.report", source_modality=SourceModality.EUD)
        )
        snapshot = SituationSnapshot.from_dict(result.payload.get("snapshot", {}))
        pending = self.runtime.context.pending_intent
        pending_view = None
        if pending is not None:
            pending_view = {
                "operation": pending.parameters.get("operation"),
                "confirmation_id": self.runtime.context.pending_confirmation_id,
                "target_ref": pending.target_ref,
            }
        view = build_situation_view(snapshot, self.runtime.attention.state, pending_confirmation=pending_view)
        return {
            "revision": self._revision,
            "generated_at": self._clock(),
            "view": view,
        }

    def _check_auth(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._expected_token is None:
            return None
        if message.get("auth_token") != self._expected_token:
            return self._error(None, "unauthorized", "invalid or missing auth token")
        return None

    def _touch(self, session_id: Optional[str]) -> Optional[_Session]:
        session = self._sessions.get(session_id) if session_id else None
        if session is not None:
            session.last_seen_at = self._clock()
        return session

    def _remember(self, session: _Session, client_msg_id: Optional[str], response: Dict[str, Any]) -> None:
        if client_msg_id is not None:
            session.seen_messages[client_msg_id] = dict(response)

    def _error(self, session_id: Optional[str], code: str, detail: str) -> Dict[str, Any]:
        return {"type": "error", "session_id": session_id, "code": code, "detail": detail}


def situation_is_stale(envelope: Dict[str, Any], now: float, max_age_seconds: float) -> bool:
    """Client-side staleness check: True if the last situation is too old.

    Stale data must be visibly distinguishable from current state; the client
    compares the envelope's ``generated_at`` against its own clock.
    """
    generated_at = envelope.get("generated_at")
    if generated_at is None:
        return True
    return (float(now) - float(generated_at)) > float(max_age_seconds)


class ReferenceEudClient:
    """In-process reference EUD client for the session contract.

    It can display a SituationSnapshot view and submit a non-executing canonical
    intent. It is transport-agnostic (talks to a CoreSessionEndpoint directly),
    which is what the contract tests exercise.
    """

    def __init__(self, endpoint: CoreSessionEndpoint, *, auth_token: Optional[str] = None) -> None:
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.session_id: Optional[str] = None
        self.last_situation: Optional[Dict[str, Any]] = None
        self.connected = False

    def connect(self) -> Dict[str, Any]:
        response = self.endpoint.handle(
            {"type": "hello", "protocol_version": PROTOCOL_VERSION, "auth_token": self.auth_token}
        )
        if response.get("type") == "welcome":
            self.session_id = response["session_id"]
            self.last_situation = response["situation"]
            self.connected = True
        return response

    def fetch_situation(self) -> Dict[str, Any]:
        response = self.endpoint.handle({"type": "get_situation", "session_id": self.session_id})
        if response.get("type") == "situation":
            self.last_situation = response["situation"]
        return response

    def submit_intent(self, intent_id: str, parameters=None, *, client_msg_id: Optional[str] = None) -> Dict[str, Any]:
        response = self.endpoint.handle(
            {
                "type": "submit_intent",
                "session_id": self.session_id,
                "intent_id": intent_id,
                "parameters": parameters or {},
                "client_msg_id": client_msg_id,
            }
        )
        if "situation" in response:
            self.last_situation = response["situation"]
        return response

    def disconnect(self) -> None:
        self.connected = False

    def reconnect(self) -> Dict[str, Any]:
        response = self.endpoint.handle(
            {"type": "resume", "session_id": self.session_id, "auth_token": self.auth_token}
        )
        if response.get("type") == "resumed":
            self.connected = True
            self.last_situation = response["situation"]
        return response
