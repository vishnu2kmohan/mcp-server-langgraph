"""
Resilience pattern test fixtures.

Extracted from conftest.py as part of P1.3 Test Fixture Optimization.
Contains fixtures for circuit breaker and bulkhead testing.
"""

import pytest


def _reset_circuit_breakers(reset_fn):
    """Helper to reset all known circuit breakers."""
    if not reset_fn:
        return
    known_services = ["llm", "openfga", "redis", "keycloak", "qdrant"]
    for service in known_services:
        try:
            reset_fn(service)
        except Exception:
            pass  # Ignore errors if service not initialized


def _reset_bulkheads(reset_fn):
    """Helper to reset all known bulkheads."""
    if not reset_fn:
        return
    known_bulkheads = ["default", "llm", "openfga", "redis"]
    for bulkhead_name in known_bulkheads:
        try:
            reset_fn(bulkhead_name)
        except Exception:
            pass  # Ignore errors if bulkhead not initialized


@pytest.fixture
def test_circuit_breaker_config():
    """
    Configure circuit breaker with minimal timeout for testing.

    Use this fixture in tests that need fast circuit breaker recovery.
    By default, circuit breakers have 60s timeout which is too slow for tests.
    This fixture configures 1s timeout for faster test iteration.

    Usage:
        def test_my_feature(test_circuit_breaker_config):
            # Circuit breaker now has 1s timeout
            pass
    """
    from mcp_server_langgraph.resilience.circuit_breaker import _circuit_breakers
    from mcp_server_langgraph.resilience.config import (
        CircuitBreakerConfig,
        ResilienceConfig,
        set_resilience_config,
    )

    # Set up test-friendly resilience config with very short timeout
    test_config = ResilienceConfig(
        enabled=True,
        circuit_breakers={
            "llm": CircuitBreakerConfig(
                name="llm",
                fail_max=5,
                timeout_duration=1,  # 1 second instead of 60 - allows quick recovery in tests
            ),
        },
    )
    set_resilience_config(test_config)

    # Clear any existing circuit breaker instances to force recreation with new config
    # This is critical for CI where state can pollute between sequential tests
    if "llm" in _circuit_breakers:
        del _circuit_breakers["llm"]

    return

    # Cleanup handled by reset_resilience_state autouse fixture


@pytest.fixture
def fast_resilience_config():
    """
    Configure all circuit breakers with minimal timeouts for fast testing.

    Use this fixture in tests that need fast circuit breaker recovery across all services.
    This is especially important for tests that intentionally trigger circuit breaker opens
    and need to verify fail-open/fail-closed behavior quickly.

    Reduces test time from 45s → <2s by using:
    - fail_max=3 (need only 3 failures to open, down from 5-10)
    - timeout_duration=1 (circuit recovers in 1 second, down from 30-60s)

    Usage:
        def test_circuit_breaker_behavior(fast_resilience_config):
            # All circuit breakers now have 1s timeout and fail_max=3
            pass
    """
    from mcp_server_langgraph.resilience.circuit_breaker import _circuit_breakers
    from mcp_server_langgraph.resilience.config import (
        CircuitBreakerConfig,
        ResilienceConfig,
        set_resilience_config,
    )

    # Set up test-friendly resilience config with very short timeouts for all services
    test_config = ResilienceConfig(
        enabled=True,
        circuit_breakers={
            "llm": CircuitBreakerConfig(name="llm", fail_max=3, timeout_duration=1),
            "openfga": CircuitBreakerConfig(name="openfga", fail_max=3, timeout_duration=1),
            "redis": CircuitBreakerConfig(name="redis", fail_max=3, timeout_duration=1),
            "keycloak": CircuitBreakerConfig(name="keycloak", fail_max=3, timeout_duration=1),
            "prometheus": CircuitBreakerConfig(name="prometheus", fail_max=3, timeout_duration=1),
        },
    )
    set_resilience_config(test_config)

    # Clear any existing circuit breaker instances to force recreation with new config
    _circuit_breakers.clear()

    return

    # Cleanup handled by reset_resilience_state autouse fixture
