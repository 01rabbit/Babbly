from dataclasses import dataclass
from enum import Enum
from typing import Optional

from babbly.nlu.japanese import IntentResult


class Decision(str, Enum):
    EXECUTE = "execute"
    CLARIFY = "clarify"
    REJECT = "reject"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str


class IntentPolicy:
    """Gate executable intents using deterministic confidence thresholds."""

    def __init__(self, execute_threshold: float = 0.90, clarify_threshold: float = 0.60):
        self.execute_threshold = float(execute_threshold)
        self.clarify_threshold = float(clarify_threshold)

    def evaluate(self, intent: IntentResult, asr_confidence: Optional[float] = None) -> PolicyDecision:
        if intent.name == "unknown":
            return PolicyDecision(Decision.REJECT, "unknown intent")

        effective = intent.confidence
        if asr_confidence is not None:
            effective = min(effective, max(0.0, min(1.0, asr_confidence)))

        if effective >= self.execute_threshold:
            return PolicyDecision(Decision.EXECUTE, f"confidence={effective:.2f}")
        if effective >= self.clarify_threshold:
            return PolicyDecision(Decision.CLARIFY, f"confidence={effective:.2f}")
        return PolicyDecision(Decision.REJECT, f"confidence={effective:.2f}")
