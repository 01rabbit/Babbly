from babbly.adapters.azazel_edge_action import AzazelEdgeActionExecutor
from babbly.core.engine import SituationEngine
from babbly.core.request import ControlledRequestManager, RiskClass
from babbly.core.runtime_factory import build_operator_runtime


def test_default_config_has_no_write_path():
    runtime = build_operator_runtime({})

    assert runtime.request_manager is None
    assert runtime.action_executor is None
    assert runtime.write_actions == {}


def test_dry_run_config_propagates_to_runtime():
    runtime = build_operator_runtime({"DRY_RUN": True})

    assert runtime.dry_run is True


def test_enabled_write_path_is_fully_wired():
    runtime = build_operator_runtime(
        {
            "AZAZEL_EDGE_WRITE_ENABLED": True,
            "AZAZEL_EDGE_WRITE_ACTIONS": ["isolate.target"],
            "AZAZEL_EDGE_URL": "http://127.0.0.1:8084",
        }
    )

    assert isinstance(runtime.request_manager, ControlledRequestManager)
    assert runtime.write_actions == {"isolate.target": RiskClass.HIGH}
    assert isinstance(runtime.action_executor, AzazelEdgeActionExecutor)


def test_enabled_write_path_without_actions_is_disabled():
    runtime = build_operator_runtime({"AZAZEL_EDGE_WRITE_ENABLED": True})

    assert runtime.request_manager is None


def test_passed_situation_engine_is_used():
    situation_engine = SituationEngine()

    runtime = build_operator_runtime({}, situation_engine=situation_engine)

    assert runtime.situation_engine is situation_engine
