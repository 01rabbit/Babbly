from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import List, Optional, Tuple


class OperatorAttentionState(str, Enum):
    """Operator-controlled attention budget.

    This is deliberately separate from threat/system severity. It expresses how
    much visual/manual attention the operator can currently spend on the device,
    not how dangerous the situation is. It changes presentation only; it never
    changes execution authority, confirmation policy, or the SituationSnapshot.
    """

    NORMAL = "normal"
    HEADS_UP = "heads_up"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AttentionPresentationPolicy:
    """Presentation density for one attention state.

    Every field influences how the same SituationSnapshot/Recommendation is
    rendered or which control affordances a surface should expose. None of these
    fields grants execution capability: the runtime enforces authority and
    confirmation identically regardless of attention state.
    """

    state: OperatorAttentionState
    max_observations: int
    include_adapter_health: bool
    include_recommendation_reason: bool
    include_action_affordances: bool
    speech_verbosity: str  # "full" | "compact" | "minimal"
    control_affordances: Tuple[str, ...]


# Control affordances are presentation hints only. The executable intent set and
# its confirmation rules are owned by OperatorIntentRuntime and do not change
# with attention state. CRITICAL narrows the *visible* surface, not authority.
_FULL_CONTROLS: Tuple[str, ...] = (
    "situation.report",
    "recommendation.explain",
    "operation.run",
    "confirm",
    "deny",
    "stop",
    "repeat",
)
_ESSENTIAL_CONTROLS: Tuple[str, ...] = (
    "situation.report",
    "confirm",
    "deny",
    "stop",
    "repeat",
)


_POLICIES = {
    OperatorAttentionState.NORMAL: AttentionPresentationPolicy(
        state=OperatorAttentionState.NORMAL,
        max_observations=3,
        include_adapter_health=True,
        include_recommendation_reason=True,
        include_action_affordances=True,
        speech_verbosity="full",
        control_affordances=_FULL_CONTROLS,
    ),
    OperatorAttentionState.HEADS_UP: AttentionPresentationPolicy(
        state=OperatorAttentionState.HEADS_UP,
        max_observations=2,
        include_adapter_health=False,
        include_recommendation_reason=False,
        include_action_affordances=False,
        speech_verbosity="compact",
        control_affordances=_ESSENTIAL_CONTROLS,
    ),
    OperatorAttentionState.CRITICAL: AttentionPresentationPolicy(
        state=OperatorAttentionState.CRITICAL,
        max_observations=1,
        include_adapter_health=False,
        include_recommendation_reason=False,
        include_action_affordances=False,
        speech_verbosity="minimal",
        control_affordances=_ESSENTIAL_CONTROLS,
    ),
}


def policy_for(state: OperatorAttentionState) -> AttentionPresentationPolicy:
    """Return the presentation policy for an attention state."""
    return _POLICIES[OperatorAttentionState(state)]


def coerce_state(value: object) -> OperatorAttentionState:
    """Parse an operator-supplied attention state.

    Accepts the enum, its value ("normal"/"heads_up"/"critical"), or common
    spellings ("headsup", "heads-up"). Raises ValueError on anything else so an
    unknown state fails closed instead of silently defaulting.
    """
    if isinstance(value, OperatorAttentionState):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized == "headsup":
            normalized = "heads_up"
        for state in OperatorAttentionState:
            if state.value == normalized:
                return state
    raise ValueError(f"unknown operator attention state: {value!r}")


@dataclass(frozen=True)
class AttentionTransition:
    """One recorded, operator-initiated attention-state change."""

    sequence: int
    from_state: OperatorAttentionState
    to_state: OperatorAttentionState
    source_modality: str
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "source_modality": self.source_modality,
            "reason": self.reason,
        }


@dataclass
class AttentionController:
    """Operator-controlled attention state with an auditable transition log.

    Transitions happen only through :meth:`request_state`, which is driven by an
    explicit operator action from some surface. There is no autonomous or
    inferred transition: Babbly does not switch modes from speculative tactical
    or battlefield judgment. Every accepted change is appended to ``history``.
    """

    state: OperatorAttentionState = OperatorAttentionState.NORMAL
    history: List[AttentionTransition] = field(default_factory=list)

    def request_state(
        self,
        state: object,
        source_modality: str,
        reason: Optional[str] = None,
    ) -> AttentionTransition:
        """Apply an operator-requested attention state and record the transition.

        Any of the three states is reachable from any other (the operator may
        jump NORMAL -> CRITICAL directly). A request for the current state is a
        valid no-op that is still recorded, so the audit trail reflects every
        deliberate operator action. Raises ValueError for an unknown state.
        """
        target = coerce_state(state)
        transition = AttentionTransition(
            sequence=len(self.history) + 1,
            from_state=self.state,
            to_state=target,
            source_modality=str(source_modality),
            reason=reason,
        )
        self.state = target
        self.history.append(transition)
        return transition

    @property
    def policy(self) -> AttentionPresentationPolicy:
        return policy_for(self.state)

    def snapshot(self) -> dict:
        return {
            "state": self.state.value,
            "sequence": len(self.history),
            "policy": {
                "max_observations": self.policy.max_observations,
                "speech_verbosity": self.policy.speech_verbosity,
                "control_affordances": list(self.policy.control_affordances),
            },
        }
