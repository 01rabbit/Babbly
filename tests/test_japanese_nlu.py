from babbly.nlu.japanese import IntentResolver, normalize_japanese


def test_normalize_ignores_whitespace_and_punctuation():
    assert normalize_japanese(" ネットワーク を スキャンして。 ") == "ネットワークをスキャンして"


def test_normalize_applies_asr_aliases():
    assert "シールド" in normalize_japanese("エッジをシールトにして")


def test_network_scan_intent_does_not_depend_on_tokenization():
    resolver = IntentResolver()
    result = resolver.resolve("ネットワークをスキャンして")
    assert result.name == "network.scan"
    assert result.confidence >= 0.9


def test_target_show_intent_accepts_natural_phrase():
    resolver = IntentResolver()
    assert resolver.resolve("ターゲットを表示して").name == "target.show"


def test_unknown_text_fails_closed():
    resolver = IntentResolver()
    result = resolver.resolve("なんとなくいい感じにして")
    assert result.name == "unknown"
    assert result.confidence == 0.0
