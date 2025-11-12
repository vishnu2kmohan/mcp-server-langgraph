"""
Shared fixtures for API endpoint tests - PYTEST-XDIST COMPATIBLE

CRITICAL: This conftest provides test mode setup that works across pytest-xdist workers.

PROBLEM HISTORY:
1. dependency_overrides doesn't propagate across xdist workers
2. Monkeypatch + reload caused FastAPI parameter name collision (422 errors)
3. Tests passed locally but failed in CI with xdist

SOLUTION:
- Use pytest_configure hook to enable test mode globally
- Set environment variable that ALL workers can see
- Dependencies check for test mode and return mocks
- Works reliably across all pytest-xdist workers

See commits: 709adda, c193936, ba5296f for history
"""

import gc
import os

import pytest


# Set test mode environment variable for ALL pytest-xdist workers
def pytest_configure(config):
    """
    Configure test environment for ALL pytest-xdist workers.

    This runs ONCE per worker process, ensuring test mode is enabled
    across all parallel workers.
    """
    os.environ["MCP_TEST_MODE"] = "true"
    os.environ["MCP_SKIP_AUTH"] = "true"


def bypass_authentication(monkeypatch, mock_user=None):
    """
    Helper function to bypass authentication for API endpoint tests.

    DEPRECATED: This approach doesn't work with pytest-xdist in CI.
    Use app.dependency_overrides in test fixtures instead.

    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_user: Optional custom user dict

    Returns:
        The mock user dict

    See: tests/api/test_service_principals_endpoints.py for correct pattern
    """
    from mcp_server_langgraph.auth import middleware

    if mock_user is None:
        mock_user = {
            "user_id": "user:test",
            "keycloak_id": "test-keycloak-id",
            "username": "test",
            "email": "test@example.com",
        }

    # Patch get_current_user at module level
    from typing import Dict, Any, Optional
    from fastapi import Request
    from fastapi.security import HTTPAuthorizationCredentials

    async def mock_get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
    ) -> Dict[str, Any]:
        return mock_user

    monkeypatch.setattr(middleware, "get_current_user", mock_get_current_user)

    return mock_user

