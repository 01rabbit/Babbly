from typing import Dict


CORE_ALIASES: Dict[str, str] = {
    "シールト": "シールド",
    "シールど": "シールド",
    "エッヂ": "エッジ",
    "スキャンニング": "スキャン",
    "ネットワークスキャン": "ネットワークをスキャン",
}

KALI_ALIASES: Dict[str, str] = {
    "エヌマップ": "nmap",
    "エンマップ": "nmap",
    "ワイヤーシャーク": "wireshark",
    "ティーシーピーダンプ": "tcpdump",
}

AZAZEL_ALIASES: Dict[str, str] = {
    "アザゼル": "azazel",
    "アザセル": "azazel",
    "エッジ": "edge",
    "ガジェット": "gadget",
    "ナレッジ": "knowledge",
    "デセプション": "deception",
    "スケープゴート": "scapegoat",
    "ポータル": "portal",
    "シールド": "shield",
}


def build_aliases(*packs: str) -> Dict[str, str]:
    aliases = dict(CORE_ALIASES)
    available = {
        "core": CORE_ALIASES,
        "kali": KALI_ALIASES,
        "azazel": AZAZEL_ALIASES,
    }
    for pack in packs:
        aliases.update(available.get(str(pack).strip().lower(), {}))
    return aliases
