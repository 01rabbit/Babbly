import json
from pathlib import Path

import pytest

from tools.evaluate_human_factors import evaluate


def _rec(rid, condition, **kw):
    base = dict(
        id=rid, condition=condition, task_id="t", completed=True,
        completion_time_s=40.0, intent_attempts=4, intent_correct=4,
        false_executions=0, clarifications=0, eyes_on_device_s=40.0, hands_on_device_s=38.0,
    )
    base.update(kw)
    return base


def test_per_condition_summary_and_rates():
    records = [
        _rec("a", "laptop_cli", intent_attempts=4, intent_correct=3, false_executions=1, clarifications=2, eyes_on_device_s=40.0),
        _rec("b", "laptop_cli", completed=False, eyes_on_device_s=50.0),
    ]
    summary, _ = evaluate(records)
    cli = summary["per_condition"]["laptop_cli"]
    assert cli["n"] == 2
    assert cli["task_completion_rate"] == 0.5
    # intent accuracy = (3+4)/(4+4) = 0.875
    assert cli["intent_accuracy"] == pytest.approx(0.875)
    # false-execution rate = 1 / 8 attempts
    assert cli["false_execution_rate"] == pytest.approx(0.125)
    assert cli["total_false_executions"] == 1
    # completion time only over completed tasks
    assert cli["mean_completion_time_s"] == 40.0
    assert cli["mean_eyes_on_device_s"] == 45.0


def test_comparison_reports_eyes_on_device_reduction():
    records = [
        _rec("base", "laptop_cli", eyes_on_device_s=40.0, hands_on_device_s=40.0, completion_time_s=50.0),
        _rec("hy", "hybrid_voice", eyes_on_device_s=10.0, hands_on_device_s=8.0, completion_time_s=40.0),
    ]
    summary, _ = evaluate(records)
    cmp = summary["comparison_vs_baseline"]["hybrid_voice"]
    assert cmp["eyes_on_device_s"]["delta"] == -30.0
    assert cmp["eyes_on_device_s"]["pct_change"] == pytest.approx(-75.0)
    assert cmp["completion_time_s"]["delta"] == -10.0


def test_mode_switch_continuity_error_rate():
    records = [
        _rec("m1", "eyes_free", mode_switches=2, mode_switch_continuity_errors=1),
        _rec("m2", "eyes_free", mode_switches=2, mode_switch_continuity_errors=0),
    ]
    summary, _ = evaluate(records)
    assert summary["per_condition"]["eyes_free"]["mode_switch_continuity_error_rate"] == pytest.approx(0.25)


def test_limitations_flag_small_samples_and_missing_baseline():
    records = [_rec("h", "hybrid_voice")]
    summary, _ = evaluate(records)
    assert any("no baseline" in item for item in summary["limitations"])
    assert any("hybrid_voice: only 1 sample" in item for item in summary["limitations"])
    assert summary["comparison_vs_baseline"] == {}


def test_strict_validation():
    with pytest.raises(ValueError):
        evaluate([_rec("x", "laptop_cli", completed="yes")])  # string bool
    with pytest.raises(ValueError):
        evaluate([_rec("x", "bogus_condition")])
    with pytest.raises(ValueError):
        evaluate([_rec("x", "laptop_cli", intent_attempts=1, intent_correct=2)])  # correct > attempts
    with pytest.raises(ValueError):
        evaluate([_rec("x", "laptop_cli"), _rec("x", "laptop_cli")])  # duplicate id
    with pytest.raises(ValueError):
        evaluate([_rec("x", "laptop_cli", eyes_on_device_s=-1.0)])  # negative


def test_example_fixture_is_valid_and_evaluates():
    path = Path("benchmarks/example_human_factors_results.json")
    records = json.loads(path.read_text(encoding="utf-8"))
    summary, _ = evaluate(records)
    assert summary["total_records"] == len(records)
    assert "hybrid_voice" in summary["conditions_present"]
    # hybrid/eyes-free should show reduced eyes-on-device vs the laptop baseline
    assert summary["comparison_vs_baseline"]["eyes_free"]["eyes_on_device_s"]["delta"] < 0
