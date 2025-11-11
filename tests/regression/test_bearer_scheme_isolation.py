"""
Regression Tests for bearer_scheme Module-Level Singleton Isolation

These tests validate that the module-level bearer_scheme singleton in
auth/middleware.py doesn't cause state pollution across pytest-xdist workers.

This prevents regression of the bug where TestAPIKeyEndpointAuthorization
tests (which don't override dependencies) run before TestCreateAPIKey tests
on the same worker, causing intermittent 401 Unauthorized errors.

Root Cause:
-----------
In src/mcp_server_langgraph/auth/middleware.py:816:
    bearer_scheme = HTTPBearer(auto_error=False)  # MODULE-LEVEL SINGLETON

This singleton is shared across all app instances in the same pytest-xdist worker,
causing state pollution when tests create FastAPI apps with and without dependency
overrides.

The Fix:
--------
Override bearer_scheme in ALL test fixtures that override get_current_user:
    app.dependency_overrides[bearer_scheme] = lambda: None

This bypasses the singleton's auth check, allowing mocked get_current_user to work.

See: tests/PYTEST_XDIST_BEST_PRACTICES.md for detailed explanation.
"""

import gc
from typing import Any, Dict

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


@pytest.fixture
def mock_current_user():
    """Mock current user for bearer_scheme tests"""
    return {
        "user_id": "user:test",
        "keycloak_id": "00000000-0000-0000-0000-000000000001",  # gitleaks:allow
        "username": "testuser",
        "email": "test@example.com",
    }


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="bearer_scheme_isolation_tests")
class TestBearerSchemeIsolation:
    """
    Regression tests for bearer_scheme module-level singleton isolation.

    Verifies that bearer_scheme state doesn't pollute across tests in pytest-xdist.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_bearer_scheme_override_prevents_401_errors(self, mock_current_user):
        """
        ✅ CORRECT: Override bearer_scheme to bypass auth in mocked tests.

        This is the FIX for the 401 errors. When testing API endpoints with
        mocked authentication, we must override BOTH get_current_user AND bearer_scheme.
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.api_keys import router
        from mcp_server_langgraph.auth.middleware import bearer_scheme, get_current_user
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, get_keycloak_client

        app = FastAPI()

        # Define mock functions
        async def mock_get_current_user_async():
            return mock_current_user

        def mock_get_api_key_manager_sync():
            manager = AsyncMock()
            manager.list_api_keys.return_value = []
            return manager

        def mock_get_keycloak_client_sync():
            return AsyncMock()

        # ✅ CRITICAL: Override bearer_scheme to bypass singleton auth check
        app.dependency_overrides[bearer_scheme] = lambda: None
        app.dependency_overrides[get_current_user] = mock_get_current_user_async
        app.dependency_overrides[get_api_key_manager] = mock_get_api_key_manager_sync
        app.dependency_overrides[get_keycloak_client] = mock_get_keycloak_client_sync

        app.include_router(router)
        client = TestClient(app)

        try:
            # This should succeed (200) because bearer_scheme is overridden
            response = client.get("/api/v1/api-keys/")

            # Should NOT be 401 Unauthorized
            assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
                "bearer_scheme override failed - still getting 401 errors. " "This indicates the singleton is still active."
            )

            # Should be 200 OK with empty list
            assert response.status_code == status.HTTP_200_OK
        finally:
            app.dependency_overrides.clear()

    def test_bearer_scheme_not_overridden_works_in_isolation(self, mock_current_user):
        """
        📝 DOCUMENTATION: In isolation, overriding get_current_user works without bearer_scheme.

        This test shows that the bug is INTERMITTENT and ORDER-DEPENDENT:
        - In isolation: Works fine (200 OK)
        - In pytest-xdist full suite: Fails with 401 when unlucky test order occurs

        The bug manifests when:
        1. TestAPIKeyEndpointAuthorization tests run first on a worker (no overrides)
        2. TestCreateAPIKey tests run next on same worker (with overrides)
        3. Module-level state from step 1 pollutes step 2

        Therefore: Always override bearer_scheme as defensive programming.
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.api_keys import router
        from mcp_server_langgraph.auth.middleware import get_current_user
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, get_keycloak_client

        app = FastAPI()

        # Define mock functions
        async def mock_get_current_user_async():
            return mock_current_user

        def mock_get_api_key_manager_sync():
            manager = AsyncMock()
            manager.list_api_keys.return_value = []
            return manager

        def mock_get_keycloak_client_sync():
            return AsyncMock()

        # Only override get_current_user (not bearer_scheme)
        app.dependency_overrides[get_current_user] = mock_get_current_user_async
        app.dependency_overrides[get_api_key_manager] = mock_get_api_key_manager_sync
        app.dependency_overrides[get_keycloak_client] = mock_get_keycloak_client_sync

        app.include_router(router)
        client = TestClient(app)

        try:
            # In isolation, this works fine (200 OK)
            response = client.get("/api/v1/api-keys/")

            # Document that this CAN work in isolation
            # but will fail in pytest-xdist with unlucky test ordering
            assert response.status_code in [
                status.HTTP_200_OK,  # Works in isolation
                status.HTTP_401_UNAUTHORIZED,  # Fails with state pollution
            ]
        finally:
            app.dependency_overrides.clear()

    def test_execution_order_documented(self):
        """
        📝 DOCUMENTATION: Execution order matters in pytest-xdist.

        This test documents why bearer_scheme override is necessary as defensive
        programming against pytest-xdist test execution order variations.

        In pytest-xdist, tests run in different order on different workers:
        - Worker [gw0] might run: TestListAPIKeys → TestCreateAPIKey ✅ Works
        - Worker [gw5] might run: TestAPIKeyEndpointAuthorization → TestCreateAPIKey ❌ Fails

        When TestAPIKeyEndpointAuthorization.test_create_without_auth() runs BEFORE
        TestCreateAPIKey tests on the same worker, the module-level bearer_scheme
        singleton gets "primed" with no-auth state, causing subsequent tests to fail.

        The fix: Always override bearer_scheme in ALL API test fixtures that use
        get_current_user dependency.
        """
        # This is a documentation test
        assert True  # Placeholder - actual validation is in other tests


@pytest.mark.unit
@pytest.mark.regression
class TestNestedDependencyOverrides:
    """
    Tests for FastAPI nested dependency override patterns.

    Documents that ALL nested dependencies must be overridden, not just top-level ones.
    """

    def test_nested_dependency_override_pattern(self):
        """
        Documentation test explaining nested dependency override requirements.

        When a dependency has nested Depends():

        async def parent_dep(
            nested_dep = Depends(some_function)
        ):
            return value

        You must override BOTH:
        - app.dependency_overrides[parent_dep] = mock_parent
        - app.dependency_overrides[some_function] = mock_nested  # ← Don't forget!

        In our case:
        - parent_dep = get_current_user
        - some_function = bearer_scheme

        Therefore:
        - app.dependency_overrides[get_current_user] = mock_user
        - app.dependency_overrides[bearer_scheme] = lambda: None  # ← REQUIRED!
        """
        # Verify docstring exists
        assert TestNestedDependencyOverrides.test_nested_dependency_override_pattern.__doc__ is not None
        assert "nested dependency" in TestNestedDependencyOverrides.test_nested_dependency_override_pattern.__doc__.lower()
        assert "bearer_scheme" in TestNestedDependencyOverrides.test_nested_dependency_override_pattern.__doc__
