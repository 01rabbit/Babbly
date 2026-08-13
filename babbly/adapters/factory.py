"""Configuration factory for optional read-only situation adapters."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping

from babbly.adapters.azazel import AzazelAdapter
from babbly.adapters.azazel_edge_action import AzazelEdgeActionExecutor
from babbly.adapters.azazel_edge_transport import AzazelEdgeStatusProvider
from babbly.core.engine import SituationEngine
from babbly.core.request import RiskClass


logger = logging.getLogger(__name__)


def _load_edge_token(config: Mapping[str, object]) -> str:
    env_name = str(config.get("AZAZEL_EDGE_TOKEN_ENV") or "AZAZEL_EDGE_TOKEN").strip()
    if env_name:
        value = str(os.environ.get(env_name, "")).strip()
        if value:
            return value

    token_file = str(config.get("AZAZEL_EDGE_TOKEN_FILE") or "").strip()
    if token_file:
        try:
            return Path(token_file).expanduser().read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("Azazel-Edge token file is unreadable: %s", exc)
    return ""


def create_situation_engine(config: Mapping[str, object]) -> SituationEngine:
    """Build Babbly's optional read-only situation integrations.

    Integrations default to disabled so standalone Babbly behavior is unchanged.
    Configuration errors never grant authority or create a write path; the
    affected adapter simply remains unavailable.
    """
    adapters = []
    if bool(config.get("AZAZEL_EDGE_ENABLED", False)):
        try:
            provider = AzazelEdgeStatusProvider(
                str(config.get("AZAZEL_EDGE_URL") or "http://127.0.0.1:8084"),
                token=_load_edge_token(config),
                timeout_sec=float(config.get("AZAZEL_EDGE_TIMEOUT_SEC", 2.0)),
                cache_ttl_sec=float(config.get("AZAZEL_EDGE_CACHE_TTL_SEC", 1.0)),
                max_response_bytes=int(config.get("AZAZEL_EDGE_MAX_RESPONSE_BYTES", 1024 * 1024)),
            )
            adapters.append(AzazelAdapter(provider))
        except (TypeError, ValueError) as exc:
            logger.warning("Azazel-Edge adapter configuration rejected: %s", exc)

    return SituationEngine(adapters)


def parse_write_actions(config: Mapping[str, object]) -> dict:
    """Read the operator-configured external write-action allowlist.

    Accepts a list of action names (each defaults to HIGH risk) or a mapping of
    name -> risk class. Empty/unset means no external write action exists, so a
    confirmed operation stays at the registered-executor boundary.
    """
    raw = config.get("AZAZEL_EDGE_WRITE_ACTIONS")
    actions: dict = {}
    if isinstance(raw, Mapping):
        for name, risk in raw.items():
            try:
                actions[str(name)] = RiskClass(str(risk))
            except ValueError:
                logger.warning("Ignoring write action %s with invalid risk class %r", name, risk)
    elif isinstance(raw, (list, tuple)):
        for name in raw:
            if name:
                actions[str(name)] = RiskClass.HIGH
    return actions


def create_action_executor(config: Mapping[str, object]):
    """Build the controlled write executor, or None when the write path is off.

    Disabled by default. Requires both `AZAZEL_EDGE_WRITE_ENABLED` and at least
    one configured write action. A configuration error never grants authority;
    the executor simply remains unavailable.
    """
    if not bool(config.get("AZAZEL_EDGE_WRITE_ENABLED", False)):
        return None
    if not parse_write_actions(config):
        logger.warning("Azazel-Edge write enabled but no AZAZEL_EDGE_WRITE_ACTIONS configured; write path stays off")
        return None
    try:
        return AzazelEdgeActionExecutor(
            str(config.get("AZAZEL_EDGE_URL") or "http://127.0.0.1:8084"),
            token=_load_edge_token(config),
            path=str(config.get("AZAZEL_EDGE_ACTION_PATH") or "/api/action"),
            timeout_sec=float(config.get("AZAZEL_EDGE_ACTION_TIMEOUT_SEC", 3.0)),
            max_response_bytes=int(config.get("AZAZEL_EDGE_MAX_RESPONSE_BYTES", 256 * 1024)),
        )
    except (TypeError, ValueError) as exc:
        logger.warning("Azazel-Edge action executor configuration rejected: %s", exc)
        return None
