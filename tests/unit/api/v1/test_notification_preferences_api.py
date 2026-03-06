"""
Notification Preferences API Tests.

TDD tests for notification preferences API endpoints.
Tests cover:
- GET /api/v1/notifications/preferences
- PUT /api/v1/notifications/preferences
"""

from __future__ import annotations

import gc
from typing import Any, Generator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


def mock_get_current_user() -> dict[str, Any]:
    """Mock user for testing."""
    return {"user_id": "user:alice", "sub": "alice", "email": "alice@example.com"}


@pytest.fixture
def preferences_app() -> Generator[FastAPI, None, None]:
    """Create a test FastAPI app with preferences router."""
    from mcp_server_langgraph.api.v1.notification_preferences import (
        notification_preferences_router,
        set_preferences_repository,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository

    repo = InMemoryPreferencesRepository()
    set_preferences_repository(repo)

    app = FastAPI()

    # Override auth dependency with mock
    app.dependency_overrides[get_current_user] = mock_get_current_user

    app.include_router(notification_preferences_router, prefix="/api/v1")

    yield app

    set_preferences_repository(None)
    app.dependency_overrides.clear()


@pytest.fixture
def preferences_client(preferences_app: FastAPI) -> TestClient:
    """Create a test client for the preferences app."""
    return TestClient(preferences_app)


class TestNotificationPreferencesAPI:
    """Tests for notification preferences API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_preferences_returns_defaults_for_new_user(self, preferences_client: TestClient) -> None:
        """
        GIVEN no saved preferences for a user
        WHEN getting preferences
        THEN default preferences are returned.
        """
        response = preferences_client.get("/api/v1/notifications/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user:alice"
        assert data["info_enabled"] is True
        assert data["success_enabled"] is True
        assert data["warning_enabled"] is True
        assert data["error_enabled"] is True

    def test_get_preferences_returns_saved_preferences(self, preferences_client: TestClient) -> None:
        """
        GIVEN saved preferences for a user
        WHEN getting preferences
        THEN saved preferences are returned.
        """
        # First save preferences
        preferences_client.put(
            "/api/v1/notifications/preferences",
            json={
                "info_enabled": False,
                "success_enabled": True,
                "warning_enabled": True,
                "error_enabled": True,
            },
        )

        # Then get them
        response = preferences_client.get("/api/v1/notifications/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["info_enabled"] is False

    def test_update_preferences_saves_changes(self, preferences_client: TestClient) -> None:
        """
        GIVEN a user
        WHEN updating preferences
        THEN the preferences are saved.
        """
        response = preferences_client.put(
            "/api/v1/notifications/preferences",
            json={
                "info_enabled": False,
                "success_enabled": False,
                "warning_enabled": True,
                "error_enabled": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["info_enabled"] is False
        assert data["success_enabled"] is False
        assert data["warning_enabled"] is True
        assert data["error_enabled"] is True

    def test_update_preferences_partial_update(self, preferences_client: TestClient) -> None:
        """
        GIVEN existing preferences
        WHEN updating only some fields
        THEN only those fields are changed.
        """
        # Set initial preferences
        preferences_client.put(
            "/api/v1/notifications/preferences",
            json={
                "info_enabled": True,
                "success_enabled": True,
                "warning_enabled": True,
                "error_enabled": True,
            },
        )

        # Partial update - only disable info
        response = preferences_client.put(
            "/api/v1/notifications/preferences",
            json={
                "info_enabled": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["info_enabled"] is False
        # Other fields should retain their values
        assert data["success_enabled"] is True
        assert data["warning_enabled"] is True
        assert data["error_enabled"] is True

    def test_reset_preferences_restores_defaults(self, preferences_client: TestClient) -> None:
        """
        GIVEN custom preferences
        WHEN resetting preferences
        THEN default preferences are restored.
        """
        # Set custom preferences
        preferences_client.put(
            "/api/v1/notifications/preferences",
            json={
                "info_enabled": False,
                "success_enabled": False,
                "warning_enabled": False,
                "error_enabled": True,
            },
        )

        # Reset to defaults
        response = preferences_client.post("/api/v1/notifications/preferences/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["info_enabled"] is True
        assert data["success_enabled"] is True
        assert data["warning_enabled"] is True
        assert data["error_enabled"] is True
