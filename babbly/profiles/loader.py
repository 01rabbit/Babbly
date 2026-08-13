from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Mapping, Optional

from .model import AgentIdentity, AgentProfile, EnvironmentProfile, PersonaProfile


_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_ALLOWED_SITUATION_SOURCES = {"azazel-edge"}
_DEFAULT_PROFILE_DIR = Path("profiles")


def _require_mapping(value, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _require_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _text_list(value, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    items = tuple(_require_text(item, field) for item in value)
    if not items and not allow_empty:
        raise ValueError(f"{field} must not be empty")
    return items


def _profile_dir(root: Optional[str | Path] = None) -> Path:
    if root is not None:
        return Path(root)
    configured = os.environ.get("BABBLY_PROFILE_DIR")
    return Path(configured).expanduser() if configured else _DEFAULT_PROFILE_DIR


def list_profiles(root: Optional[str | Path] = None) -> tuple[str, ...]:
    directory = _profile_dir(root)
    try:
        names = [path.stem for path in directory.glob("*.json") if path.is_file()]
    except OSError:
        return ()
    return tuple(sorted(name for name in names if _PROFILE_NAME.fullmatch(name)))


def resolve_profile_name(
    cli_value: Optional[str],
    config: Mapping[str, object],
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    env = os.environ if environ is None else environ
    value = cli_value or env.get("BABBLY_PROFILE") or config.get("PROFILE") or "generic"
    name = str(value).strip().lower()
    if not _PROFILE_NAME.fullmatch(name):
        raise ValueError(f"invalid profile name: {name!r}")
    return name


def load_profile(name: str, root: Optional[str | Path] = None) -> AgentProfile:
    normalized = str(name).strip().lower()
    if not _PROFILE_NAME.fullmatch(normalized):
        raise ValueError(f"invalid profile name: {normalized!r}")

    path = _profile_dir(root) / f"{normalized}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"profile not found: {normalized}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"profile cannot be loaded: {normalized}: {exc}") from exc

    root_obj = _require_mapping(payload, "profile")
    profile_id = _require_text(root_obj.get("id"), "id").lower()
    if profile_id != normalized:
        raise ValueError(f"profile id mismatch: expected {normalized!r}, got {profile_id!r}")

    identity_obj = _require_mapping(root_obj.get("identity"), "identity")
    identity = AgentIdentity(
        id=_require_text(identity_obj.get("id"), "identity.id"),
        display_name=_require_text(identity_obj.get("display_name"), "identity.display_name"),
        spoken_name=_require_text(identity_obj.get("spoken_name"), "identity.spoken_name"),
        wake_phrases=_text_list(identity_obj.get("wake_phrases"), "identity.wake_phrases"),
        language=_require_text(identity_obj.get("language", "ja"), "identity.language"),
    )

    persona_obj = _require_mapping(root_obj.get("persona"), "persona")
    persona = PersonaProfile(
        tone=_require_text(persona_obj.get("tone"), "persona.tone"),
        style=_require_text(persona_obj.get("style"), "persona.style"),
        verbosity=_require_text(persona_obj.get("verbosity"), "persona.verbosity"),
        startup_phrase=_require_text(persona_obj.get("startup_phrase"), "persona.startup_phrase"),
        acknowledgement=_require_text(persona_obj.get("acknowledgement"), "persona.acknowledgement"),
        command_prompt=_require_text(persona_obj.get("command_prompt"), "persona.command_prompt"),
        unknown_prompt=_require_text(persona_obj.get("unknown_prompt"), "persona.unknown_prompt"),
        shutdown_phrase=_require_text(persona_obj.get("shutdown_phrase"), "persona.shutdown_phrase"),
        introduction=_text_list(persona_obj.get("introduction"), "persona.introduction"),
    )

    environment_obj = _require_mapping(root_obj.get("environment"), "environment")
    sources = _text_list(
        environment_obj.get("situation_sources", []),
        "environment.situation_sources",
        allow_empty=True,
    )
    unknown_sources = sorted(set(sources) - _ALLOWED_SITUATION_SOURCES)
    if unknown_sources:
        raise ValueError(f"unsupported situation source(s): {', '.join(unknown_sources)}")
    environment = EnvironmentProfile(
        type=_require_text(environment_obj.get("type"), "environment.type"),
        vocabulary_packs=_text_list(environment_obj.get("vocabulary_packs"), "environment.vocabulary_packs"),
        situation_sources=sources,
    )

    return AgentProfile(profile_id, identity, persona, environment)


def apply_profile_to_config(
    config: Mapping[str, object],
    profile: AgentProfile,
) -> dict[str, object]:
    """Project only non-authority profile fields into runtime configuration.

    Profiles may select identity, wake phrases, vocabulary, and read-only
    situation sources. They cannot modify DRY_RUN, intent thresholds, command
    registries, action policy, or any execution authority setting.
    """
    projected = dict(config)
    projected["ACTIVE_PROFILE"] = profile.id
    projected["WAKEUP_PHRASE"] = profile.identity.primary_wake_phrase
    projected["WAKEUP_PHRASES"] = list(profile.identity.wake_phrases)
    projected["DOMAIN_VOCABULARY"] = list(profile.environment.vocabulary_packs)
    projected["AZAZEL_EDGE_ENABLED"] = "azazel-edge" in profile.environment.situation_sources
    return projected
