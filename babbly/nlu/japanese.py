import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple


DEFAULT_ALIASES: Dict[str, str] = {
    "シールト": "シールド",
    "シールど": "シールド",
    "エッヂ": "エッジ",
    "スキャンニング": "スキャン",
    "ネットワークスキャン": "ネットワークをスキャン",
}


def normalize_japanese(text: str, aliases: Optional[Dict[str, str]] = None) -> str:
    """Normalize ASR output without depending on tokenizer whitespace.

    The normalized form is intended for intent matching, not for display.
    """
    value = unicodedata.normalize("NFKC", text or "").strip().lower()
    value = re.sub(r"[\s\u3000]+", "", value)
    value = re.sub(r"[、。,.!?！？・:：;；\"'「」『』（）()\[\]{}]", "", value)

    mapping = dict(DEFAULT_ALIASES)
    if aliases:
        mapping.update(aliases)
    for source, target in mapping.items():
        value = value.replace(normalize_japanese(source, {}) if source != target else source, target)
    return value


@dataclass(frozen=True)
class IntentResult:
    name: str
    confidence: float
    normalized_text: str


class IntentResolver:
    """Small deterministic resolver for safety-critical command routing.

    AI/LLM layers may suggest candidates later, but executable intents should
    continue through this explicit resolver/policy boundary.
    """

    RULES: Tuple[Tuple[str, Tuple[Tuple[str, ...], ...]], ...] = (
        ("system.exit", (("終了",), ("システム", "終了"))),
        ("system.introduce", (("自己紹介",),)),
        ("network.scan", (("ネットワーク", "スキャン"), ("周辺", "スキャン"))),
        ("target.show", (("ターゲット", "教え"), ("ターゲット", "表示"), ("ターゲット", "確認"))),
        ("command.mode", (("コマンド",),)),
    )

    def resolve(self, text: str) -> IntentResult:
        normalized = normalize_japanese(text)
        for intent, alternatives in self.RULES:
            for required_terms in alternatives:
                if all(normalize_japanese(term) in normalized for term in required_terms):
                    confidence = 0.98 if len(required_terms) > 1 else 0.90
                    return IntentResult(intent, confidence, normalized)
        return IntentResult("unknown", 0.0, normalized)
