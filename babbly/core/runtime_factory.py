"""Factory for the optionally controlled operator runtime."""

from __future__ import annotations

from typing import Mapping, Optional

from babbly.adapters.factory import create_action_executor, parse_write_actions
from babbly.core.engine import SituationEngine
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.request import ControlledRequestManager


def build_operator_runtime(
    config: Mapping[str, object], situation_engine: Optional[SituationEngine] = None
) -> OperatorIntentRuntime:
    """Build an OperatorIntentRuntime wired from config.

    Always sets DRY_RUN. When the controlled write path is enabled in config
    (create_action_executor returns an executor AND parse_write_actions is
    non-empty), also wires a ControlledRequestManager, the Azazel-Edge action
    executor, and the write-action allowlist. Otherwise returns a runtime with
    no write path (unchanged read/confirmation behaviour).
    """
    dry_run = bool(config.get("DRY_RUN", False))
    executor = create_action_executor(config)
    write_actions = parse_write_actions(config)

    if executor is not None and write_actions:
        request_manager = ControlledRequestManager(
            dry_run=dry_run,
            default_timeout_seconds=float(
                config.get("AZAZEL_EDGE_APPROVAL_TIMEOUT_SEC", 120.0)
            ),
        )
        action_executor = executor
    else:
        request_manager = None
        action_executor = None
        write_actions = None

    return OperatorIntentRuntime(
        situation_engine,
        dry_run=dry_run,
        request_manager=request_manager,
        action_executor=action_executor,
        write_actions=write_actions,
    )
