from pathlib import Path

import pytest

from babbly.profiles import apply_profile_to_config, list_profiles, load_profile, resolve_profile_name


PROFILE_DIR = Path("profiles")


def test_generic_profile_is_babbly():
    profile = load_profile("generic", PROFILE_DIR)
    assert profile.identity.display_name == "Babbly"
    assert profile.identity.spoken_name == "バブリー"
    assert profile.identity.primary_wake_phrase == "バブリー"
    assert profile.environment.situation_sources == ()


def test_azazel_edge_profile_is_mio_and_read_only_source_enabled():
    profile = load_profile("azazel-edge", PROFILE_DIR)
    assert profile.identity.display_name == "M.I.O"
    assert profile.identity.spoken_name == "ミオ"
    assert profile.identity.wake_phrases == ("ミオ",)
    assert profile.persona.style == "tactical_concise"
    assert profile.environment.vocabulary_packs == ("core", "azazel")
    assert profile.environment.situation_sources == ("azazel-edge",)


def test_profile_projection_cannot_change_authority_settings():
    base = {
        "DRY_RUN": True,
        "INTENT_EXECUTE_THRESHOLD": 0.97,
        "INTENT_CLARIFY_THRESHOLD": 0.80,
        "COMMANDS_PATH": "commands.json",
        "AZAZEL_EDGE_ENABLED": False,
    }
    profile = load_profile("azazel-edge", PROFILE_DIR)

    projected = apply_profile_to_config(base, profile)

    assert projected["DRY_RUN"] is True
    assert projected["INTENT_EXECUTE_THRESHOLD"] == 0.97
    assert projected["INTENT_CLARIFY_THRESHOLD"] == 0.80
    assert projected["COMMANDS_PATH"] == "commands.json"
    assert projected["AZAZEL_EDGE_ENABLED"] is True
    assert projected["WAKEUP_PHRASE"] == "ミオ"
    assert projected["WAKEUP_PHRASES"] == ["ミオ"]
    assert projected["DOMAIN_VOCABULARY"] == ["core", "azazel"]


def test_generic_profile_disables_environment_specific_source():
    projected = apply_profile_to_config(
        {"AZAZEL_EDGE_ENABLED": True},
        load_profile("generic", PROFILE_DIR),
    )
    assert projected["AZAZEL_EDGE_ENABLED"] is False


def test_profile_resolution_precedence():
    config = {"PROFILE": "generic"}
    assert resolve_profile_name("azazel-edge", config, {"BABBLY_PROFILE": "kali"}) == "azazel-edge"
    assert resolve_profile_name(None, config, {"BABBLY_PROFILE": "kali"}) == "kali"
    assert resolve_profile_name(None, config, {}) == "generic"


def test_profile_name_rejects_path_traversal():
    with pytest.raises(ValueError):
        load_profile("../secret", PROFILE_DIR)


def test_builtin_profiles_are_discoverable():
    names = list_profiles(PROFILE_DIR)
    assert "generic" in names
    assert "kali" in names
    assert "azazel-edge" in names
