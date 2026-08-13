import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from babbly.nlu.vocabulary import build_aliases


def _basic_normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").strip().lower()
    value = re.sub(r"[\s\u3000]+", "", value)
    value = re.sub(r"[、。,.!?！？・:：;；\"'「」『』（）()\[\]{}]", "", value)
    return value


def normalize_japanese(text: str, aliases: Optional[Dict[str, str]] = None) -> str:
    """Normalize ASR output without depending on tokenizer whitespace."""
    value = _basic_normalize(text)
    mapping = build_aliases("core")
    if aliases:
        mapping.update(aliases)
    for source, target in mapping.items():
        value = value.replace(_basic_normalize(source), _basic_normalize(target))
    return value


@dataclass(frozen=True)
class IntentResult:
    name: str
    confidence: float
    normalized_text: str


class IntentResolver:
    """Deterministic resolver for command and read-only operator intents."""

    RULES: Tuple[Tuple[str, Tuple[Tuple[str, ...], ...]], ...] = (
        ("system.exit", (("終了",), ("システム", "終了"))),
        ("system.introduce", (("自己紹介",),)),
        ("situation.report", (("状況", "報告"), ("状況", "確認"), ("状況", "教え"))),
        ("recommendation.explain", (("推奨", "説明"), ("推奨", "教え"), ("どうすれば",), ("何をすべき",))),
        ("network.scan", (("ネットワーク", "スキャン"), ("周辺", "スキャン"))),
        ("target.show", (("ターゲット", "教え"), ("ターゲット", "表示"), ("ターゲット", "確認"))),
        ("command.mode", (("コマンド",),)),
    )

    def __init__(self, aliases: Optional[Dict[str, str]] = None):
        self.aliases = aliases or build_aliases("core")

    def resolve(self, text: str) -> IntentResult:
        normalized = normalize_japanese(text, self.aliases)
        for intent, alternatives in self.RULES:
            for required_terms in alternatives:
                if all(_basic_normalize(term) in normalized for term in required_terms):
                    confidence = 0.98 if len(required_terms) > 1 else 0.90
                    return IntentResult(intent, confidence, normalized)
        return IntentResult("unknown", 0.0, normalized)
