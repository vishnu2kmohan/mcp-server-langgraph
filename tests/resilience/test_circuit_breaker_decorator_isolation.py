"""
Regression tests for circuit breaker decorator closure isolation.

This module contains tests to ensure that circuit breaker decorators
maintain correct references to their circuit breaker instances even
after registry operations like reset_all_circuit_breakers().

Background:
-----------
The circuit breaker decorator creates a closure over the circuit breaker
instance at decoration time. If reset_all_circuit_breakers() clears the
registry, subsequent calls to get_circuit_breaker() may return a different
instance than the one captured in the decorator's closure, leading to
state inspection failures in tests.

Failure Scenario:
-----------------
1. Function decorated with @circuit_breaker at module import time
2. Decorator closure captures circuit breaker instance A
3. Test calls reset_all_circuit_breakers() which clears registry
4. Test calls get_circuit_breaker() which creates new instance B
5. Test inspects instance B state, but decorator uses instance A
6. Assertions fail because inspecting wrong circuit breaker object

See Also:
---------
- src/mcp_server_langgraph/resilience/circuit_breaker.py:395-416
- tests/test_openfga_client.py:518, :559, :600 (original failures)
- docs-internal/adr/ADR-0053-circuit-breaker-decorator-closure-isolation.md
"""

import gc

import pytest

from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError
from mcp_server_langgraph.resilience.circuit_breaker import (
    circuit_breaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
    reset_circuit_breaker,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="circuit_breaker_isolation")
class TestCircuitBreakerDecoratorIsolation:
    """Test circuit breaker decorator closure isolation."""

    def teardown_method(self) -> None:
        """Clean up circuit breakers and force GC to prevent mock accumulation in xdist workers."""
        reset_all_circuit_breakers()
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_decorator_closure_persists_after_registry_clear(self):
        """
        Test that decorator closure doesn't go stale after registry clear.

        This test validates the fix for the circuit breaker closure isolation bug
        where reset_all_circuit_breakers() was clearing the registry, causing
        get_circuit_breaker() to return a different instance than the one the
        decorator was using.

        Expected behavior (after fix):
        - reset_all_circuit_breakers() resets state without clearing registry
        - Decorator continues working with same circuit breaker instance
        - State inspections reflect actual circuit breaker state
        - No stale closure references
        """

        # Define a function with circuit breaker decorator
        @circuit_breaker(
            name="test_decorator_isolation",
            fail_max=3,
            timeout=1,
        )
        async def protected_function():
            """Function that always fails to trigger circuit breaker."""
            raise Exception("Intentional failure")

        # Trigger failures to open the circuit breaker
        for i in range(5):
            try:
                await protected_function()
            except Exception:
                pass  # Expected failures

        # Get circuit breaker instance BEFORE reset
        cb_before = get_circuit_breaker("test_decorator_isolation")
        id_before = id(cb_before)
        state_before = cb_before.state.name

        # Circuit should be open after 3+ failures
        assert state_before == "open", f"Expected state 'open', got '{state_before}'"

        # Now reset all circuit breakers (should reset state, not clear registry)
        reset_all_circuit_breakers()

        # Get circuit breaker instance AFTER reset
        cb_after = get_circuit_breaker("test_decorator_isolation")
        id_after = id(cb_after)

        # FIXED: Instance identity should be preserved
        assert id_before == id_after, (
            f"Instance identity changed after reset: {id_before} != {id_after}. "
            "This indicates reset_all_circuit_breakers() cleared the registry instead of resetting state."
        )

        # State should be reset to closed
        assert cb_after.state.name == "closed", f"Expected state 'closed' after reset, got '{cb_after.state.name}'"

        # Decorator should allow calls now (circuit is closed)
        try:
            await protected_function()
        except Exception as e:
            # We expect the intentional Exception, not CircuitBreakerOpenError
            assert "Intentional failure" in str(e)
            assert not isinstance(e, CircuitBreakerOpenError), "Circuit breaker should be closed after reset"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reset_circuit_breaker_preserves_instance_identity(self):
        """
        Test that reset_circuit_breaker() preserves instance identity.

        reset_circuit_breaker() should reset the state without creating
        a new instance, preserving decorator closure integrity.
        """

        # Define a function with circuit breaker decorator
        @circuit_breaker(
            name="test_reset_preserves_identity",
            fail_max=3,
            timeout=1,
        )
        async def protected_function():
            """Function that always fails to trigger circuit breaker."""
            raise Exception("Intentional failure")

        # Get initial instance
        cb_initial = get_circuit_breaker("test_reset_preserves_identity")
        initial_id = id(cb_initial)

        # Trigger failures to open circuit
        for i in range(5):
            try:
                await protected_function()
            except Exception:
                pass

        # Verify circuit is open
        assert cb_initial.state.name == "open"

        # Reset the circuit breaker (should preserve instance)
        reset_circuit_breaker("test_reset_preserves_identity")

        # Get instance after reset
        cb_after_reset = get_circuit_breaker("test_reset_preserves_identity")
        after_reset_id = id(cb_after_reset)

        # Verify instance identity is preserved
        assert initial_id == after_reset_id, f"Instance identity changed after reset: {initial_id} != {after_reset_id}"

        # Verify state is reset to closed
        assert cb_after_reset.state.name == "closed"

        # Verify decorator uses the same instance (should allow calls now)
        try:
            await protected_function()
        except Exception as e:
            # We expect the intentional Exception, not CircuitBreakerOpenError
            assert "Intentional failure" in str(e)
            assert not isinstance(e, CircuitBreakerOpenError), "Circuit breaker should be closed after reset"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_decorators_with_same_name_share_instance(self):
        """
        Test that multiple decorators with the same name share the same
        circuit breaker instance.

        This validates that the get_circuit_breaker() registry works correctly
        and that all decorators using the same name reference the same instance.
        """

        # Define two functions with the same circuit breaker name
        @circuit_breaker(
            name="shared_breaker",
            fail_max=3,
            timeout=1,
        )
        async def function_a():
            """First function sharing circuit breaker."""
            raise Exception("Function A failure")

        @circuit_breaker(
            name="shared_breaker",
            fail_max=3,
            timeout=1,
        )
        async def function_b():
            """Second function sharing circuit breaker."""
            raise Exception("Function B failure")

        # Trigger failures in function_a to open the circuit
        for i in range(5):
            try:
                await function_a()
            except Exception:
                pass

        # Verify circuit is open
        cb = get_circuit_breaker("shared_breaker")
        assert cb.state.name == "open"

        # function_b should also see the circuit as open
        # because it shares the same circuit breaker instance
        with pytest.raises(CircuitBreakerOpenError):
            await function_b()

        # Both functions should be blocked now
        with pytest.raises(CircuitBreakerOpenError):
            await function_a()
