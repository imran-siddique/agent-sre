"""Tests for circuit breaker."""

import time
from agent_sre.incidents.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("agent-1")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available

    def test_opens_after_failures(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("err1")
        cb.record_failure("err2")
        assert cb.state == CircuitState.CLOSED
        cb.record_failure("err3")
        assert cb.state == CircuitState.OPEN
        assert not cb.is_available

    def test_half_open_after_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=0.01)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("err1")
        cb.record_failure("err2")
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_available

    def test_half_open_to_closed_on_success(self):
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=0.01, success_threshold=2)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        cb.record_failure("e2")
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=0.01)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        cb.record_failure("e2")
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure("e3")
        assert cb.state == CircuitState.OPEN

    def test_force_open_and_close(self):
        cb = CircuitBreaker("agent-1")
        cb.force_open("maintenance")
        assert cb.state == CircuitState.OPEN
        cb.force_close("maintenance done")
        assert cb.state == CircuitState.CLOSED

    def test_reset(self):
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        cb.record_failure("e2")
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_events_tracked(self):
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        cb.record_failure("e2")
        events = cb.events
        assert len(events) >= 1
        assert events[-1].to_state == CircuitState.OPEN

    def test_total_trips(self):
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.01)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        assert cb._total_trips == 1
        cb.reset()
        cb.record_failure("e2")
        assert cb._total_trips == 2

    def test_to_dict(self):
        cb = CircuitBreaker("agent-1")
        d = cb.to_dict()
        assert d["agent_id"] == "agent-1"
        assert d["state"] == "closed"
        assert "config" in d

    def test_success_reduces_failure_count(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("agent-1", config)
        cb.record_failure("e1")
        cb.record_failure("e2")
        cb.record_success()
        cb.record_success()
        # Failures reduced, should still be closed
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerRegistry:
    def test_get_or_create(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("agent-1")
        assert cb.agent_id == "agent-1"
        assert registry.get("agent-1") is cb

    def test_is_available(self):
        registry = CircuitBreakerRegistry()
        assert registry.is_available("agent-1")

    def test_open_breakers(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("agent-1")
        cb.force_open("test")
        assert len(registry.open_breakers) == 1

    def test_summary(self):
        registry = CircuitBreakerRegistry()
        registry.get("agent-1")
        registry.get("agent-2")
        s = registry.summary()
        assert s["total_agents"] == 2
