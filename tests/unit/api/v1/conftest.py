"""
Unit test fixtures for api/v1 tests.

Consolidates shared fixtures to avoid duplicate autouse fixtures.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_ai_circuit_breakers():
    """Reset all AI UX circuit breakers before each test to ensure clean state.

    This fixture is shared across all api/v1 unit tests that need circuit breaker
    isolation. Consolidated per tests/meta/test_fixture_organization.py requirements.
    """
    from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker

    reset_circuit_breaker("ai_ux_llm")
    yield
    # Clean up after test
    reset_circuit_breaker("ai_ux_llm")
