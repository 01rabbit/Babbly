"""Read-only Azazel-Edge transport for Babbly situation adapters.

The transport consumes the additive ``/api/state.status_view`` JSON contract
emitted by Azazel-Edge. Babbly intentionally does not import Azazel-Fabric: the
wire contract is sufficient and keeps Babbly usable outside the Azazel series.

Only HTTP GET is supported. There is no write/action path in this module.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class AzazelEdgeTransportError(RuntimeError):
    """Raised when the read-only Edge status surface cannot be consumed."""


def _status_severity(value: object) -> str:
    word = str(value or "unknown").strip().lower()
    if word in {"normal", "ok", "safe", "healthy", "quiet", "online"}:
        return "info"
    if word in {"degraded", "caution", "warn", "warning", "unknown"}:
        return "caution"
    if word in {"contain", "containment", "deception"}:
        return "warning"
    if word in {"critical", "lockdown", "offline", "danger"}:
        return "critical"
    return "caution"


def _health_severity(value: object) -> str:
    word = str(value or "unknown").strip().lower()
    if word == "ok":
        return "info"
    if word in {"warn", "warning", "unknown"}:
        return "caution"
    if word == "critical":
        return "critical"
    return "caution"


def _current_action_summary(value: object) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, Mapping):
        action = value.get("kind") or value.get("action") or value.get("name")
        target = value.get("target")
        if action and target:
            return f"current action: {action} ({target})"
        if action:
            return f"current action: {action}"
        return "current action is present"
    return f"current action: {value}"


def translate_edge_state(payload: Mapping[str, object]) -> Dict[str, object]:
    """Translate Edge ``/api/state`` into Babbly's generic adapter payload.

    ``status_view`` is authoritative for presentation when present. The native
    Edge snapshot is used only as a compatibility fallback for installations
    where the additive Fabric view has not been emitted yet.
    """
    view = payload.get("status_view")
    if isinstance(view, Mapping):
        product = str(view.get("product") or "edge")
        system = f"azazel-{product}"
        posture = str(view.get("posture") or "unknown")
        headline = str(view.get("headline") or f"{system} state is {posture}")
        state_severity = _status_severity(posture)
        alerts = []

        for reason in view.get("reasons", []) or []:
            if reason:
                alerts.append(
                    {
                        "category": "status.reason",
                        "summary": str(reason),
                        "severity": state_severity,
                    }
                )

        for row in view.get("health", []) or []:
            if not isinstance(row, Mapping):
                continue
            key = str(row.get("key") or "unknown")
            label = str(row.get("label") or key)
            detail = row.get("detail")
            summary = label if not detail else f"{label}: {detail}"
            alerts.append(
                {
                    "category": f"health.{key}",
                    "summary": summary,
                    "severity": _health_severity(row.get("status")),
                    "data": dict(row),
                }
            )

        current_action = view.get("current_action")
        action_summary = _current_action_summary(current_action)
        if action_summary:
            alerts.append(
                {
                    "category": "control.current_action",
                    "summary": action_summary,
                    "severity": "info",
                    "data": dict(current_action) if isinstance(current_action, Mapping) else {"value": current_action},
                }
            )

        operator_wording = view.get("operator_wording")
        recommendations = []
        for index, action in enumerate(view.get("next_actions", []) or []):
            if not action:
                continue
            recommendations.append(
                {
                    "action": str(action),
                    "reason": str(operator_wording or headline),
                    "priority": 10 + index * 10,
                }
            )
        # Current Edge emits its native snapshot recommendation as
        # StatusView.operator_wording and does not yet populate next_actions.
        # Preserve that information as spoken advice only; it is never wired to
        # an execution path.
        if not recommendations and operator_wording:
            recommendations.append(
                {
                    "action": str(operator_wording),
                    "reason": headline,
                    "priority": 50,
                }
            )

        return {
            "system": system,
            "state": posture,
            "state_severity": state_severity,
            "headline": headline,
            "alerts": alerts,
            "recommendations": recommendations,
            "metadata": {
                "schema_version": view.get("schema_version"),
                "generated_at": view.get("generated_at"),
                "trace_id": view.get("trace_id"),
                "mode": view.get("mode"),
                "operator_wording": operator_wording,
                "evidence_ids": list(view.get("evidence_ids", []) or []),
                "current_action": current_action,
            },
        }

    # Compatibility fallback: use only stable, read-only state indicators. Do
    # not synthesize recommendations from product-specific fields.
    internal = payload.get("internal") if isinstance(payload.get("internal"), Mapping) else {}
    state = str(internal.get("state_name") or payload.get("user_state") or payload.get("status") or "unknown")
    severity = _status_severity(state)
    alerts = []
    critical = payload.get("suricata_critical")
    warning = payload.get("suricata_warning")
    if critical is not None or warning is not None:
        try:
            critical_count = int(critical or 0)
        except (TypeError, ValueError):
            critical_count = 0
        try:
            warning_count = int(warning or 0)
        except (TypeError, ValueError):
            warning_count = 0
        alerts.append(
            {
                "category": "health.suricata",
                "summary": f"Suricata critical={critical_count} warning={warning_count}",
                "severity": "critical" if critical_count else ("caution" if warning_count else "info"),
            }
        )
    return {
        "system": "azazel-edge",
        "state": state,
        "state_severity": severity,
        "headline": f"azazel-edge state is {state}",
        "alerts": alerts,
        "recommendations": [],
        "metadata": {"status_view": "unavailable"},
    }


class AzazelEdgeStatusProvider:
    """Bounded, cached GET provider for Azazel-Edge ``/api/state``.

    Repeated calls inside one SituationEngine collection are served from a short
    monotonic TTL cache, preventing the observation and recommendation passes
    from issuing duplicate HTTP requests.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout_sec: float = 2.0,
        cache_ttl_sec: float = 1.0,
        max_response_bytes: int = 1024 * 1024,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        base = str(base_url or "").strip().rstrip("/")
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AZAZEL_EDGE_URL must be an http(s) URL")
        self.url = base + "/api/state"
        self.token = str(token or "").strip()
        self.timeout_sec = max(0.1, float(timeout_sec))
        self.cache_ttl_sec = max(0.0, float(cache_ttl_sec))
        self.max_response_bytes = max(1024, int(max_response_bytes))
        self.opener = opener
        self._cached_at: Optional[float] = None
        self._cached_payload: Optional[Dict[str, object]] = None

    def _request(self) -> Mapping[str, object]:
        headers = {
            "Accept": "application/json",
            "Cache-Control": "no-store",
        }
        if self.token:
            # Canonical Azazel-Fabric/Edge token header. Edge also accepts the
            # legacy X-Auth-Token header, but new Babbly code uses the canonical one.
            headers["X-AZAZEL-TOKEN"] = self.token
        request = Request(self.url, headers=headers, method="GET")
        response = None
        try:
            response = self.opener(request, timeout=self.timeout_sec)
            status = response.getcode() if hasattr(response, "getcode") else getattr(response, "status", 200)
            if status is not None and int(status) >= 400:
                raise AzazelEdgeTransportError(f"Azazel-Edge returned HTTP {status}")
            raw = response.read(self.max_response_bytes + 1)
        except AzazelEdgeTransportError:
            raise
        except Exception as exc:
            raise AzazelEdgeTransportError("Azazel-Edge status request failed") from exc
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

        if len(raw) > self.max_response_bytes:
            raise AzazelEdgeTransportError("Azazel-Edge status response exceeded size limit")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AzazelEdgeTransportError("Azazel-Edge returned invalid JSON") from exc
        if not isinstance(decoded, Mapping):
            raise AzazelEdgeTransportError("Azazel-Edge status payload is not an object")
        return decoded

    def __call__(self) -> Mapping[str, object]:
        now = time.monotonic()
        if (
            self._cached_payload is not None
            and self._cached_at is not None
            and now - self._cached_at <= self.cache_ttl_sec
        ):
            return self._cached_payload

        translated = translate_edge_state(self._request())
        self._cached_payload = translated
        self._cached_at = now
        return translated
