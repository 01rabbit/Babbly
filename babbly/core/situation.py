from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class Observation:
    source: str
    category: str
    summary: str
    severity: str = "info"
    confidence: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class Recommendation:
    source: str
    action: str
    reason: str
    priority: int = 100
    confidence: Optional[float] = None
    advisory_only: bool = True


@dataclass
class SituationSnapshot:
    status: str = "unknown"
    observations: List[Observation] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    systems: Dict[str, str] = field(default_factory=dict)

    def add_observation(self, observation: Observation) -> None:
        self.observations.append(observation)
        self._recompute_status()

    def add_recommendation(self, recommendation: Recommendation) -> None:
        self.recommendations.append(recommendation)
        self.recommendations.sort(key=lambda item: item.priority)

    def set_system_state(self, system: str, state: str) -> None:
        self.systems[system] = state

    def _recompute_status(self) -> None:
        rank = {"info": 0, "caution": 1, "warning": 2, "critical": 3}
        current = "info"
        for observation in self.observations:
            if rank.get(observation.severity, 0) > rank.get(current, 0):
                current = observation.severity
        self.status = current if self.observations else "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "systems": dict(self.systems),
            "observations": [asdict(item) for item in self.observations],
            "recommendations": [asdict(item) for item in self.recommendations],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SituationSnapshot":
        snapshot = cls(status=str(payload.get("status") or "unknown"))
        systems = payload.get("systems") or {}
        if isinstance(systems, Mapping):
            snapshot.systems = {str(key): str(value) for key, value in systems.items()}

        observations = payload.get("observations") or []
        if isinstance(observations, list):
            for item in observations:
                if not isinstance(item, Mapping):
                    continue
                snapshot.observations.append(
                    Observation(
                        source=str(item.get("source") or "unknown"),
                        category=str(item.get("category") or "unknown"),
                        summary=str(item.get("summary") or ""),
                        severity=str(item.get("severity") or "info"),
                        confidence=item.get("confidence"),
                        data=dict(item.get("data") or {}),
                        observed_at=str(item.get("observed_at") or datetime.now(timezone.utc).isoformat()),
                    )
                )

        recommendations = payload.get("recommendations") or []
        if isinstance(recommendations, list):
            for item in recommendations:
                if not isinstance(item, Mapping):
                    continue
                snapshot.recommendations.append(
                    Recommendation(
                        source=str(item.get("source") or "unknown"),
                        action=str(item.get("action") or ""),
                        reason=str(item.get("reason") or ""),
                        priority=int(item.get("priority", 100)),
                        confidence=item.get("confidence"),
                        advisory_only=bool(item.get("advisory_only", True)),
                    )
                )
        snapshot.recommendations.sort(key=lambda item: item.priority)
        return snapshot
