from __future__ import annotations

from typing import Any, Dict, List, Optional

from babbly.core.attention import OperatorAttentionState, policy_for
from babbly.core.render import STATUS_JA
from babbly.core.situation import SituationSnapshot


_SEVERITY_ORDER = {"critical": 0, "warning": 1, "caution": 2, "info": 3}


def build_situation_view(
    snapshot: SituationSnapshot,
    attention_state: OperatorAttentionState,
    *,
    pending_confirmation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the shared presentation view-model for TUI and Web surfaces.

    TUI and Web render from this single model so the two surfaces cannot drift
    into separate presentations of the same SituationSnapshot. The model is
    presentation-neutral data only: it carries no execution capability and never
    mutates the snapshot. Density follows the attention presentation policy.
    """
    state = OperatorAttentionState(attention_state)
    policy = policy_for(state)

    online = sum(1 for value in snapshot.systems.values() if value == "online")
    errors = sum(1 for value in snapshot.systems.values() if value == "error")
    systems_summary = {"online": online, "error": errors, "total": len(snapshot.systems)}

    observations = [
        {"summary": item.summary, "severity": item.severity, "source": item.source}
        for item in sorted(
            snapshot.observations,
            key=lambda item: _SEVERITY_ORDER.get(item.severity, 4),
        )[: policy.max_observations]
    ]

    recommendation: Optional[Dict[str, Any]] = None
    if snapshot.recommendations:
        top = snapshot.recommendations[0]
        recommendation = {
            "action": top.action,
            "advisory_only": top.advisory_only,
            "confidence": top.confidence if policy.include_recommendation_reason else None,
            "reason": top.reason if policy.include_recommendation_reason else None,
        }

    view: Dict[str, Any] = {
        "schema": "babbly.situation-view.v1",
        "attention_state": state.value,
        "speech_verbosity": policy.speech_verbosity,
        "status": snapshot.status,
        "status_label": STATUS_JA.get(snapshot.status, snapshot.status),
        "systems_summary": systems_summary,
        "systems": (
            [{"name": name, "state": value} for name, value in sorted(snapshot.systems.items())]
            if policy.include_adapter_health
            else []
        ),
        "observations": observations,
        "recommendation": recommendation,
        "controls": list(policy.control_affordances),
        "pending_confirmation": pending_confirmation,
        "degraded": errors > 0,
    }
    return view


def render_tui(view: Dict[str, Any]) -> str:
    """Render the shared view-model as a compact terminal panel.

    Progressive disclosure: NORMAL shows adapter health and the recommendation
    reason; HEADS_UP/CRITICAL compress to the current status, top findings, and
    the recommended action.
    """
    lines: List[str] = []
    lines.append(f"[{view['attention_state'].upper()}] 状態: {view['status_label']}")

    summary = view["systems_summary"]
    if view["systems"]:
        detail = "  ".join(f"{s['name']}={s['state']}" for s in view["systems"])
        lines.append(f"系統: 正常{summary['online']}/{summary['total']}  {detail}")
    elif summary["total"]:
        suffix = f" (エラー{summary['error']})" if summary["error"] else ""
        lines.append(f"系統: 正常{summary['online']}/{summary['total']}{suffix}")

    if view["degraded"]:
        lines.append("⚠ 一部アダプタが取得エラー")

    if view["observations"]:
        lines.append("観測:")
        for obs in view["observations"]:
            lines.append(f"  - [{obs['severity']}] {obs['summary']}")
    else:
        lines.append("観測: なし")

    rec = view["recommendation"]
    if rec:
        line = f"推奨: {rec['action']}"
        if rec.get("reason"):
            line += f" — {rec['reason']}"
        if rec.get("advisory_only"):
            line += "（助言）"
        lines.append(line)

    pending = view["pending_confirmation"]
    if pending:
        lines.append(f"確認待ち: {pending.get('operation', '?')} → 承認/却下")

    return "\n".join(lines)
