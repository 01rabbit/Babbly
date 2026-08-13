import pytest

from tools.evaluate_wake_results import evaluate


def test_wake_evaluator_computes_false_accept_reject_and_latency():
    corpus = [
        {"id": "p1", "expected_trigger": True, "class": "wake"},
        {"id": "p2", "expected_trigger": True, "class": "wake"},
        {"id": "n1", "expected_trigger": False, "class": "non-wake"},
        {"id": "n2", "expected_trigger": False, "class": "non-wake"},
    ]
    results = [
        {"id": "p1", "actual_trigger": True, "latency_ms": 100.0},
        {"id": "p2", "actual_trigger": False, "latency_ms": None},
        {"id": "n1", "actual_trigger": True, "latency_ms": 50.0},
        {"id": "n2", "actual_trigger": False, "latency_ms": None},
    ]

    summary, _rows = evaluate(corpus, results)
    assert summary["true_positive"] == 1
    assert summary["false_negative"] == 1
    assert summary["false_positive"] == 1
    assert summary["true_negative"] == 1
    assert summary["false_accept_rate"] == 0.5
    assert summary["false_reject_rate"] == 0.5
    assert summary["mean_true_positive_latency_ms"] == 100.0


def test_wake_evaluator_reports_missing_samples_without_counting_them():
    summary, rows = evaluate(
        [{"id": "p1", "expected_trigger": True}],
        [],
    )
    assert summary["evaluated"] == 0
    assert summary["missing"] == 1
    assert rows == [{"id": "p1", "status": "missing"}]


def test_wake_evaluator_rejects_string_booleans():
    with pytest.raises(ValueError):
        evaluate(
            [{"id": "p1", "expected_trigger": "true"}],
            [{"id": "p1", "actual_trigger": True}],
        )


def test_wake_evaluator_rejects_duplicate_result_ids():
    with pytest.raises(ValueError):
        evaluate(
            [{"id": "p1", "expected_trigger": True}],
            [
                {"id": "p1", "actual_trigger": True},
                {"id": "p1", "actual_trigger": False},
            ],
        )
