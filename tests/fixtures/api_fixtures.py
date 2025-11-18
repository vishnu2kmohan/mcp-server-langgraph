"""
Shared API Testing Fixtures

Provides reusable fixtures for FastAPI endpoint testing with proper dependency injection.

This module addresses common test fixture issues by providing standardized, properly
configured test clients that include all required dependency overrides.

Usage:
    Import in conftest.py or test files:

    from tests.fixtures.api_fixtures import mock_openfga_client, create_api_test_client

    @pytest.fixture
    def test_client(mock_openfga_client):
        return create_api_test_client(
            router=my_router,
            dependency_overrides={
                get_openfga_client: lambda: mock_openfga_client,
            },
        )

Prevents:
    - Missing dependency overrides (401 errors)
    - Async/sync mismatch in dependency overrides
    - State pollution in pytest-xdist parallel execution

References:
    - tests/api/test_service_principals_endpoints.py (4 tests fixed)
    - Root cause: Incomplete dependency override patterns
"""

from typing import Any, Callable, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient

# ==============================================================================
# Reusable Mock Fixtures
# ==============================================================================


@pytest.fixture
def mock_openfga_client():
    """
    Shared OpenFGA client mock for API tests.

    Provides a properly configured AsyncMock that:
    - Has check_permission method returning True (authorized) by default
    - Can be reconfigured per test for denied scenarios
    - Prevents 401 errors from missing OpenFGA dependency

    Example:
        >>> def test_endpoint(mock_openfga_client):
        ...     # Override for specific test
        ...     mock_openfga_client.check_permission.return_value = False
        ...     response = client.post("/api/endpoint")
        ...     assert response.status_code == 403

    Returns:
        AsyncMock configured as OpenFGA client

    References:
        - tests/utils/mock_factories.py::create_mock_openfga_client
        - Fixed: tests/api/test_service_principals_endpoints.py (4 tests)
    """
    from tests.utils.mock_factories import create_mock_openfga_client

    return create_mock_openfga_client(authorized=True)


# ==============================================================================
# Test Client Factory
# ==============================================================================


def create_api_test_client(
    router: APIRouter,
    dependency_overrides: Dict[Callable[..., Any], Callable[..., Any]],
) -> TestClient:
    """
    Create a FastAPI TestClient with properly configured dependency overrides.

    Provides a standardized way to create test clients that:
    - Includes all required dependency overrides
    - Handles async/sync dependency matching correctly
    - Cleans up overrides after test to prevent state pollution

    Args:
        router: FastAPI router to test
        dependency_overrides: Dict mapping dependency functions to mock functions
                            MUST match async/sync of original dependencies!

    Returns:
        TestClient instance with configured overrides

    Example:
        >>> from mcp_server_langgraph.api.service_principals import router
        >>> from mcp_server_langgraph.core.dependencies import (
        ...     get_current_user,
        ...     get_openfga_client,
        ... )
        >>>
        >>> client = create_api_test_client(
        ...     router=router,
        ...     dependency_overrides={
        ...         get_current_user: lambda: {"user_id": "test_user"},
        ...         get_openfga_client: lambda: mock_openfga_client,
        ...     },
        ... )

    Warning:
        Dependency override functions MUST match the async/sync signature of the
        original dependency, otherwise FastAPI will ignore the override in pytest-xdist!

    References:
        - tests/api/test_service_principals_endpoints.py (4 tests fixed)
        - Root cause: Missing OpenFGA dependency override
    """
    app = FastAPI()
    app.include_router(router)

    # Apply dependency overrides
    for original_dep, mock_dep in dependency_overrides.items():
        app.dependency_overrides[original_dep] = mock_dep

    # Create test client
    client = TestClient(app)

    # Note: TestClient cleanup should clear overrides automatically,
    # but we can't do it here since this is a factory function, not a fixture.
    # Callers should use this in a fixture with proper cleanup.

    return client


# ==============================================================================
# Common Dependency Override Patterns
# ==============================================================================


def create_mock_current_user(user_id: str = "test_user", roles: list[str] = None) -> Dict[str, Any]:
    """
    Create a mock current_user dict for authentication testing.

    Args:
        user_id: User ID in OpenFGA format (e.g., "user:test_gw0")
        roles: List of roles (e.g., ["admin", "user"])

    Returns:
        Dict representing authenticated user

    Example:
        >>> async def mock_get_current_user():
        ...     # Use get_user_id() for worker-safe IDs in actual tests
        ...     return create_mock_current_user(user_id="user:test_gw0", roles=["admin"])
    """
    if roles is None:
        roles = ["user"]

    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "roles": roles,
        "sub": user_id,
    }


# ==============================================================================
# Documentation
# ==============================================================================

# IMPORTANT: Required dependency overrides by endpoint type
#
# Service Principal Endpoints (src/mcp_server_langgraph/api/service_principals.py):
#   - get_current_user (async) - Authentication
#   - get_service_principal_manager (sync) - Service principal operations
#   - get_openfga_client (sync) - Authorization checks
#
# Auth Endpoints (src/mcp_server_langgraph/api/auth.py):
#   - get_keycloak_client (sync) - User authentication
#   - get_api_key_manager (sync) - API key validation
#
# Tool Endpoints (src/mcp_server_langgraph/api/tools.py):
#   - get_current_user (async) - Authentication
#   - get_openfga_client (sync) - Authorization checks
#
# If you get 401/403 errors in API tests, verify you've overridden ALL dependencies!
