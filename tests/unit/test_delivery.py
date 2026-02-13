"""Tests for progressive delivery — shadow mode and canary rollout."""

from agent_sre.delivery.rollout import (
    AnalysisCriterion,
    CanaryRollout,
    RollbackCondition,
    RolloutState,
    RolloutStep,
    ShadowComparison,
    ShadowMode,
    ShadowResult,
)


class TestShadowComparison:
    def test_deltas(self) -> None:
        c = ShadowComparison(
            request_id="r1",
            current_latency_ms=100,
            candidate_latency_ms=150,
            current_cost_usd=0.01,
            candidate_cost_usd=0.02,
        )
        assert c.latency_delta_ms == 50
        assert abs(c.cost_delta_usd - 0.01) < 1e-10


class TestShadowResult:
    def test_empty(self) -> None:
        r = ShadowResult()
        assert r.total_requests == 0
        assert r.match_rate == 0.0
        assert r.confidence_score == 0.0

    def test_with_comparisons(self) -> None:
        r = ShadowResult()
        r.comparisons = [
            ShadowComparison("r1", match=True, similarity_score=1.0),
            ShadowComparison("r2", match=True, similarity_score=0.9),
            ShadowComparison("r3", match=False, similarity_score=0.5),
        ]
        assert r.total_requests == 3
        assert abs(r.match_rate - 2 / 3) < 0.01


class TestShadowMode:
    def test_exact_match(self) -> None:
        shadow = ShadowMode()
        c = shadow.compare("r1", "hello world", "hello world")
        assert c.match is True
        assert c.similarity_score == 1.0

    def test_mismatch(self) -> None:
        shadow = ShadowMode()
        c = shadow.compare("r1", "hello", "goodbye")
        assert c.match is False
        assert c.similarity_score == 0.0

    def test_custom_similarity(self) -> None:
        shadow = ShadowMode(similarity_threshold=0.8)
        shadow.set_similarity_function(lambda a, b: 0.85)
        c = shadow.compare("r1", "a", "b")
        assert c.match is True
        assert c.similarity_score == 0.85

    def test_is_passing(self) -> None:
        shadow = ShadowMode()
        for i in range(10):
            shadow.compare(f"r{i}", "same", "same")
        assert shadow.is_passing(min_confidence=0.5) is True

    def test_finish(self) -> None:
        shadow = ShadowMode()
        shadow.compare("r1", "a", "a")
        result = shadow.finish()
        assert result.end_time is not None
        assert result.total_requests == 1


class TestAnalysisCriterion:
    def test_gte(self) -> None:
        c = AnalysisCriterion(metric="success_rate", threshold=0.99, comparator="gte")
        assert c.evaluate(0.995) is True
        assert c.evaluate(0.98) is False

    def test_lte(self) -> None:
        c = AnalysisCriterion(metric="latency", threshold=5000, comparator="lte")
        assert c.evaluate(3000) is True
        assert c.evaluate(6000) is False


class TestCanaryRollout:
    def test_default_steps(self) -> None:
        r = CanaryRollout(name="test-v2")
        assert len(r.steps) == 4
        assert r.state == RolloutState.PENDING

    def test_start(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        assert r.state == RolloutState.CANARY
        assert r.current_step_index == 0
        assert r.current_weight == 0.05
        assert r.started_at is not None

    def test_advance(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        assert r.advance() is True  # 5% -> 25%
        assert r.current_weight == 0.25
        assert r.advance() is True  # 25% -> 50%
        assert r.advance() is True  # 50% -> 100%
        assert r.advance() is False  # Already at last step
        assert r.state == RolloutState.COMPLETE

    def test_rollback(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        r.rollback(reason="test failure")
        assert r.state == RolloutState.ROLLED_BACK
        assert r.completed_at is not None

    def test_auto_rollback(self) -> None:
        r = CanaryRollout(
            name="test-v2",
            rollback_conditions=[
                RollbackCondition(metric="error_rate", threshold=0.05, comparator="gte"),
            ],
        )
        r.start()
        triggered = r.check_rollback({"error_rate": 0.10})
        assert triggered is True
        assert r.state == RolloutState.ROLLED_BACK

    def test_no_rollback_when_healthy(self) -> None:
        r = CanaryRollout(
            name="test-v2",
            rollback_conditions=[
                RollbackCondition(metric="error_rate", threshold=0.05, comparator="gte"),
            ],
        )
        r.start()
        assert r.check_rollback({"error_rate": 0.01}) is False
        assert r.state == RolloutState.CANARY

    def test_analyze_step(self) -> None:
        r = CanaryRollout(
            name="test-v2",
            steps=[
                RolloutStep(
                    name="canary",
                    weight=0.05,
                    analysis=[AnalysisCriterion("success_rate", 0.99, "gte")],
                ),
            ],
        )
        r.start()
        assert r.analyze_step({"success_rate": 0.995}) is True
        assert r.analyze_step({"success_rate": 0.98}) is False

    def test_pause_resume(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        r.pause()
        assert r.state == RolloutState.PAUSED
        r.resume()
        assert r.state == RolloutState.CANARY

    def test_promote(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        r.promote()
        assert r.state == RolloutState.COMPLETE
        assert r.current_weight == 1.0

    def test_progress(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        assert r.progress_percent == 25.0  # 1/4 steps
        r.advance()
        assert r.progress_percent == 50.0

    def test_to_dict(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        d = r.to_dict()
        assert d["name"] == "test-v2"
        assert d["state"] == "canary"
        assert len(d["events"]) > 0

    def test_events_recorded(self) -> None:
        r = CanaryRollout(name="test-v2")
        r.start()
        r.advance()
        r.rollback(reason="bad")
        types = [e.event_type for e in r.events]
        assert "rollout_start" in types
        assert "step_start" in types
        assert "rollback" in types
