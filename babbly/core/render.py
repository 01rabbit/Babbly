from babbly.core.attention import (
    AttentionPresentationPolicy,
    OperatorAttentionState,
    policy_for,
)
from babbly.core.situation import Recommendation, SituationSnapshot


STATUS_JA = {
    "unknown": "状況不明",
    "info": "平常",
    "caution": "注意",
    "warning": "警戒",
    "critical": "重大警戒",
}


def render_situation_ja(snapshot: SituationSnapshot, max_observations: int = 2) -> str:
    """Render a concise operator-facing Japanese situation report."""
    status = STATUS_JA.get(snapshot.status, snapshot.status)
    parts = [f"現在の状態は{status}です"]

    online = sum(1 for state in snapshot.systems.values() if state == "online")
    errors = sum(1 for state in snapshot.systems.values() if state == "error")
    if snapshot.systems:
        parts.append(f"接続系統は{online}件正常")
        if errors:
            parts.append(f"{errors}件で取得エラー")

    important = sorted(
        snapshot.observations,
        key=lambda item: {"critical": 0, "warning": 1, "caution": 2, "info": 3}.get(item.severity, 4),
    )[:max_observations]
    if important:
        parts.append("主な観測は" + "。".join(item.summary for item in important))
    else:
        parts.append("報告可能な観測はありません")

    if snapshot.recommendations:
        top = snapshot.recommendations[0]
        parts.append(f"最優先の推奨は{top.action}です")

    return "。".join(parts) + "。"


def render_recommendation_ja(snapshot: SituationSnapshot) -> str:
    """Explain the highest-priority advisory recommendation without executing it."""
    if not snapshot.recommendations:
        return "現在、提示できる推奨はありません。"

    item: Recommendation = snapshot.recommendations[0]
    advisory = "これは助言のみで、自動実行はしません" if item.advisory_only else ""
    message = f"最優先の推奨は{item.action}です。理由は{item.reason}です。"
    if item.confidence is not None:
        message += f"信頼度は{item.confidence:.0%}です。"
    if advisory:
        message += advisory + "。"
    return message


def render_situation_for_attention(
    snapshot: SituationSnapshot,
    state: OperatorAttentionState,
) -> str:
    """Render the situation at the density allowed by the attention state.

    This is progressive disclosure over the *same* SituationSnapshot: NORMAL
    exposes adapter health, more observations, and the recommendation; CRITICAL
    compresses to the essentials for eyes-free use. It never changes the
    snapshot itself and never adds or removes any capability.
    """
    policy: AttentionPresentationPolicy = policy_for(state)
    status = STATUS_JA.get(snapshot.status, snapshot.status)
    parts = [f"現在の状態は{status}です"]

    if policy.include_adapter_health and snapshot.systems:
        online = sum(1 for value in snapshot.systems.values() if value == "online")
        errors = sum(1 for value in snapshot.systems.values() if value == "error")
        parts.append(f"接続系統は{online}件正常")
        if errors:
            parts.append(f"{errors}件で取得エラー")

    important = sorted(
        snapshot.observations,
        key=lambda item: {"critical": 0, "warning": 1, "caution": 2, "info": 3}.get(item.severity, 4),
    )[: policy.max_observations]
    if important:
        parts.append("主な観測は" + "。".join(item.summary for item in important))
    elif policy.speech_verbosity != "minimal":
        parts.append("報告可能な観測はありません")

    if snapshot.recommendations:
        top = snapshot.recommendations[0]
        if policy.include_recommendation_reason:
            parts.append(f"最優先の推奨は{top.action}です。理由は{top.reason}です")
        else:
            parts.append(f"推奨は{top.action}")

    return "。".join(parts) + "。"


def render_recommendation_for_attention(
    snapshot: SituationSnapshot,
    state: OperatorAttentionState,
) -> str:
    """Render the top recommendation at the density allowed by the attention state.

    The recommendation stays advisory in every state; attention mode only
    controls how much of the reasoning is spoken, never whether it executes.
    """
    policy = policy_for(state)
    if not snapshot.recommendations:
        return "推奨なし。" if policy.speech_verbosity == "minimal" else "現在、提示できる推奨はありません。"

    item: Recommendation = snapshot.recommendations[0]
    if policy.speech_verbosity == "minimal":
        return f"推奨は{item.action}。"

    message = f"最優先の推奨は{item.action}です。"
    if policy.include_recommendation_reason:
        message += f"理由は{item.reason}です。"
        if item.confidence is not None:
            message += f"信頼度は{item.confidence:.0%}です。"
    if item.advisory_only:
        message += "助言のみです。"
    return message
