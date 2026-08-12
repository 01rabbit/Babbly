from babbly.nlu.japanese import normalize_japanese
from babbly.nlu.vocabulary import build_aliases


def test_kali_pack_normalizes_nmap_pronunciation():
    aliases = build_aliases("kali")
    assert "nmap" in normalize_japanese("エンマップで確認", aliases)


def test_azazel_pack_normalizes_product_terms():
    aliases = build_aliases("azazel")
    normalized = normalize_japanese("アザセル エッジをシールトに", aliases)
    assert "azazel" in normalized
    assert "edge" in normalized
    assert "shield" in normalized


def test_unknown_pack_is_ignored():
    aliases = build_aliases("does-not-exist")
    assert normalize_japanese("ネットワーク スキャン", aliases) == "ネットワークスキャン"
