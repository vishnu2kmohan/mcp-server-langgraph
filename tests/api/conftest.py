"""
Shared fixtures for API endpoint tests.

Provides helper function for bypassing authentication in API tests.
This works around pytest-xdist state pollution issues with FastAPI dependency_overrides.

PROBLEM:
- FastAPI dependency_overrides doesn't work reliably in pytest-xdist
- bearer_scheme singleton causes state pollution across workers
- Dependency resolution happens at route definition time, not request time

SOLUTION:
- Monkeypatch approach: Patch get_current_user before importing routers
- Simpler than dependency_overrides and works with pytest-xdist
- Tests explicitly call helper function when needed (no autouse)
"""

import gc

import pytest


def bypass_authentication(monkeypatch, mock_user=None):
    """
    Helper function to bypass authentication for API endpoint tests.

    Call this in your test BEFORE importing any routers.

    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_user: Optional custom user dict, uses default if None

    Returns:
        The mock user dict being used

    Example:
        def test_create_something(monkeypatch):
            user = bypass_authentication(monkeypatch)
            # Now import router after patching
            from myapp import router
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post("/api/v1/things")
            assert response.status_code == 201
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
    async def mock_get_current_user(*args, **kwargs):
        return mock_user

    monkeypatch.setattr(middleware, "get_current_user", mock_get_current_user)

    return mock_user

