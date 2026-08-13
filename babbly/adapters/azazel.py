from typing import Callable, Iterable, Mapping, Optional

from babbly.adapters.base import BabblyAdapter
from babbly.core import Observation, Recommendation


class AzazelAdapter(BabblyAdapter):
    """Translate Azazel status payloads into Babbly's generic situation model.

    The adapter is intentionally read-only. A future write path must use an
    explicit request/approval contract and must not bypass Azazel-Edge authority.
    """

    name = "azazel"

    def __init__(self, status_provider: Callable[[], Mapping[str, object]]):
        self.status_provider = status_provider

    def _payload(self) -> Mapping[str, object]:
        payload = self.status_provider()
        return payload if isinstance(payload, Mapping) else {}

    def observations(self) -> Iterable[Observation]:
        payload = self._payload()
        observations = []

        system = str(payload.get("system", "azazel"))
        state = str(payload.get("state", "unknown"))
        headline = str(payload.get("headline") or f"{system} state is {state}")
        state_severity = _normalize_severity(payload.get("state_severity"), state)
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        observations.append(
            Observation(
                source=system,
                category="system.state",
                summary=headline,
                severity=state_severity,
                data={"state": state, **dict(metadata)},
            )
        )

        for alert in payload.get("alerts", []) or []:
            if not isinstance(alert, Mapping):
                continue
            data = alert.get("data") if isinstance(alert.get("data"), Mapping) else alert
            observations.append(
                Observation(
                    source=system,
                    category=str(alert.get("category", "security.alert")),
                    summary=str(alert.get("summary", "Azazel alert")),
                    severity=_normalize_severity(alert.get("severity"), "warning"),
                    confidence=_optional_float(alert.get("confidence")),
                    data=dict(data),
                )
            )
        return observations

    def recommendations(self) -> Iterable[Recommendation]:
        payload = self._payload()
        system = str(payload.get("system", "azazel"))
        recommendations = []
        for item in payload.get("recommendations", []) or []:
            if not isinstance(item, Mapping):
                continue
            try:
                priority = int(item.get("priority", 100))
            except (TypeError, ValueError):
                priority = 100
            recommendations.append(
                Recommendation(
                    source=system,
                    action=str(item.get("action", "observe")),
                    reason=str(item.get("reason", "Azazel advisory")),
                    priority=priority,
                    confidence=_optional_float(item.get("confidence")),
                    advisory_only=True,
                )
            )
        return recommendations


def _normalize_severity(value: object, state: object = "unknown") -> str:
    word = str(value or "").strip().lower()
    if word in {"info", "caution", "warning", "critical"}:
        return word
    state_word = str(state or "unknown").strip().lower()
    if state_word in {"normal", "ok", "safe", "healthy", "quiet", "online", "shield"}:
        return "info"
    if state_word in {"degraded", "caution", "warn", "unknown"}:
        return "caution"
    if state_word in {"contain", "containment", "deception", "warning"}:
        return "warning"
    if state_word in {"critical", "lockdown", "offline", "danger"}:
        return "critical"
    return "caution"


def _optional_float(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
