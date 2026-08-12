from babbly.nlu.japanese import IntentResult
from babbly.nlu.policy import Decision, IntentPolicy


def test_unknown_intent_is_rejected():
    policy = IntentPolicy()
    result = policy.evaluate(IntentResult("unknown", 0.0, "不明"))
    assert result.decision == Decision.REJECT


def test_high_confidence_intent_executes():
    policy = IntentPolicy(execute_threshold=0.90, clarify_threshold=0.60)
    result = policy.evaluate(IntentResult("network.scan", 0.98, "ネットワークをスキャン"), 0.95)
    assert result.decision == Decision.EXECUTE


def test_medium_confidence_intent_requires_clarification():
    policy = IntentPolicy(execute_threshold=0.90, clarify_threshold=0.60)
    result = policy.evaluate(IntentResult("network.scan", 0.98, "ネットワークをスキャン"), 0.75)
    assert result.decision == Decision.CLARIFY


def test_low_confidence_intent_is_rejected():
    policy = IntentPolicy(execute_threshold=0.90, clarify_threshold=0.60)
    result = policy.evaluate(IntentResult("network.scan", 0.98, "ネットワークをスキャン"), 0.40)
    assert result.decision == Decision.REJECT


def test_missing_backend_confidence_uses_deterministic_intent_score():
    policy = IntentPolicy(execute_threshold=0.90, clarify_threshold=0.60)
    result = policy.evaluate(IntentResult("network.scan", 0.98, "ネットワークをスキャン"), None)
    assert result.decision == Decision.EXECUTE
