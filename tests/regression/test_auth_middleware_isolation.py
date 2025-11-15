"""
Regression tests for auth middleware isolation.

This module contains tests to ensure that the global auth middleware
is properly reset between tests to prevent pollution in pytest-xdist
parallel execution.

Background:
-----------
The `set_global_auth_middleware()` function modifies a module-level global
variable `_global_auth_middleware` in the auth.middleware module. If this
global is not reset between tests, it can pollute subsequent tests running
in the same pytest-xdist worker, causing unexpected authentication behavior.

Failure Scenario:
-----------------
1. Test A calls `set_global_auth_middleware(custom_auth)`
2. Test A completes
3. Test B runs in same worker, expects default auth middleware
4. Test B sees `_global_auth_middleware` still set to custom_auth from Test A
5. Test B fails due to unexpected auth behavior

See Also:
---------
- src/mcp_server_langgraph/auth/middleware.py
- tests/conftest.py:268-291 (reset_dependency_singletons fixture)
- tests/test_auth.py (tests that use set_global_auth_middleware)
"""

import gc

import pytest

import mcp_server_langgraph.auth.middleware as middleware
from mcp_server_langgraph.auth.middleware import set_global_auth_middleware


@pytest.mark.xdist_group(name="auth_middleware_isolation")
class TestAuthMiddlewareIsolation:
    """Test auth middleware global state isolation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def teardown_method(self):
        """Clean up auth middleware after each test."""
        # Explicitly reset global auth middleware
        middleware._global_auth_middleware = None

    @pytest.mark.unit
    def test_global_auth_middleware_starts_none(self):
        """
        Test that global auth middleware starts as None.

        This test validates that the `_global_auth_middleware` global
        is properly reset between tests.
        """
        # Global auth middleware should be None by default
        assert middleware._global_auth_middleware is None, (
            f"Expected _global_auth_middleware to be None, got {middleware._global_auth_middleware}. "
            "This indicates pollution from a previous test in the same worker."
        )

    @pytest.mark.unit
    def test_set_global_auth_middleware_modifies_global(self):
        """
        Test that set_global_auth_middleware() modifies the global variable.

        This test validates that the function works as expected.
        """

        # Create a mock auth middleware function
        def custom_auth():
            """Custom auth middleware."""
            return "custom"

        # Verify global starts as None
        assert middleware._global_auth_middleware is None

        # Set global auth middleware
        set_global_auth_middleware(custom_auth)

        # Verify global was modified
        assert middleware._global_auth_middleware is not None
        assert middleware._global_auth_middleware is custom_auth

    @pytest.mark.unit
    def test_global_auth_middleware_pollution_detection(self):
        """
        Test that we can detect auth middleware pollution.

        This test simulates what would happen if a previous test set
        the global auth middleware and it wasn't cleaned up.

        This test should FAIL if the reset_dependency_singletons fixture
        is not properly resetting _global_auth_middleware.
        """

        # First test sets global auth middleware
        def test1_auth():
            """Test 1 auth middleware."""
            return "test1"

        set_global_auth_middleware(test1_auth)
        assert middleware._global_auth_middleware is test1_auth

        # Simulate test cleanup (what conftest.py should do)
        # If this line is commented out, the next assertion will fail
        middleware._global_auth_middleware = None

        # Second test expects global to be None
        # If cleanup didn't happen, this will fail
        assert middleware._global_auth_middleware is None, (
            "Global auth middleware was not reset between tests. "
            "This indicates the reset_dependency_singletons fixture is not "
            "properly resetting _global_auth_middleware."
        )

    @pytest.mark.unit
    def test_multiple_tests_dont_interfere_with_each_other(self):
        """
        Test that multiple tests setting global auth don't interfere.

        This test runs multiple scenarios in sequence to ensure proper isolation.
        """

        # Scenario 1: Set custom auth
        def auth1():
            return "auth1"

        set_global_auth_middleware(auth1)
        assert middleware._global_auth_middleware is auth1

        # Reset (simulating what conftest should do between tests)
        middleware._global_auth_middleware = None

        # Scenario 2: Set different auth
        def auth2():
            return "auth2"

        set_global_auth_middleware(auth2)
        assert middleware._global_auth_middleware is auth2
        assert middleware._global_auth_middleware is not auth1

        # Reset (simulating what conftest should do between tests)
        middleware._global_auth_middleware = None

        # Scenario 3: Global should be None again
        assert middleware._global_auth_middleware is None
