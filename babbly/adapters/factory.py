"""Configuration factory for optional read-only situation adapters."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping

from babbly.adapters.azazel import AzazelAdapter
from babbly.adapters.azazel_edge_transport import AzazelEdgeStatusProvider
from babbly.core.engine import SituationEngine


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
