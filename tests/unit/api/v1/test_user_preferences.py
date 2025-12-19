"""
User Preferences API Tests.

TDD tests for the user preferences API endpoints.

Endpoints tested:
- GET /api/v1/preferences - Get current user's preferences
- PATCH /api/v1/preferences - Update preferences
- DELETE /api/v1/preferences - Reset to defaults
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.user_preferences import (
    user_preferences_router,
)

# Module-level pytest marker
pytestmark = pytest.mark.unit


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_current_user() -> dict[str, Any]:
    """Mock authenticated user."""
    return {
        "user_id": "user:testuser",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def app(mock_current_user: dict[str, Any]) -> FastAPI:
    """Create test FastAPI app with preferences router."""
    from mcp_server_langgraph.api.v1.user_preferences import (
        set_preferences_store,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    test_app = FastAPI()

    # Override auth dependency
    async def override_get_current_user() -> dict[str, Any]:
        return mock_current_user

    test_app.dependency_overrides[get_current_user] = override_get_current_user

    # Use in-memory store for tests
    test_store: dict[str, dict[str, Any]] = {}
    set_preferences_store(test_store)

    test_app.include_router(user_preferences_router, prefix="/api/v1")

    yield test_app

    # Cleanup
    set_preferences_store(None)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# ==============================================================================
# GET /preferences Tests
# ==============================================================================


@pytest.mark.unit
class TestGetPreferences:
    """Tests for GET /api/v1/preferences endpoint."""

    def test_get_preferences_returns_defaults_for_new_user(self, client: TestClient) -> None:
        """New users should get default preferences."""
        response = client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "system"
        assert data["language"] == "en"

    def test_get_preferences_returns_saved_preferences(self, client: TestClient) -> None:
        """Saved preferences should be returned correctly."""
        # First save some preferences
        client.patch("/api/v1/preferences", json={"theme": "dark"})

        # Then get them
        response = client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"

    def test_get_preferences_requires_auth(self) -> None:
        """Endpoint should require authentication."""

        app = FastAPI()
        app.include_router(user_preferences_router, prefix="/api/v1")

        # Don't override auth - should fail
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/preferences")

        # Should get 401 or 403
        assert response.status_code in [401, 403, 500]  # 500 if dep raises


# ==============================================================================
# PATCH /preferences Tests
# ==============================================================================


@pytest.mark.unit
class TestUpdatePreferences:
    """Tests for PATCH /api/v1/preferences endpoint."""

    def test_update_theme_preference(self, client: TestClient) -> None:
        """Should update theme preference."""
        response = client.patch("/api/v1/preferences", json={"theme": "dark"})

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"

    def test_update_language_preference(self, client: TestClient) -> None:
        """Should update language preference."""
        response = client.patch("/api/v1/preferences", json={"language": "es"})

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "es"

    def test_update_multiple_preferences(self, client: TestClient) -> None:
        """Should update multiple preferences at once."""
        response = client.patch(
            "/api/v1/preferences",
            json={
                "theme": "light",
                "language": "fr",
                "auto_scroll": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["language"] == "fr"
        assert data["auto_scroll"] is False

    def test_partial_update_preserves_other_preferences(self, client: TestClient) -> None:
        """Partial update should not reset other preferences."""
        # Set initial preferences
        client.patch(
            "/api/v1/preferences",
            json={"theme": "dark", "language": "de"},
        )

        # Update only theme
        client.patch("/api/v1/preferences", json={"theme": "light"})

        # Language should be preserved
        response = client.get("/api/v1/preferences")
        data = response.json()
        assert data["theme"] == "light"
        assert data["language"] == "de"

    def test_update_invalid_theme_returns_error(self, client: TestClient) -> None:
        """Invalid theme value should return 422."""
        response = client.patch("/api/v1/preferences", json={"theme": "invalid"})

        assert response.status_code == 422

    def test_update_accessibility_preferences(self, client: TestClient) -> None:
        """Should update accessibility preferences."""
        response = client.patch(
            "/api/v1/preferences",
            json={
                "reduced_motion": True,
                "high_contrast": True,
                "screen_reader_mode": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reduced_motion"] is True
        assert data["high_contrast"] is True
        assert data["screen_reader_mode"] is True

    def test_update_model_defaults(self, client: TestClient) -> None:
        """Should update model default preferences."""
        response = client.patch(
            "/api/v1/preferences",
            json={
                "default_model": "gpt-4",
                "default_temperature": 0.5,
                "default_max_tokens": 2048,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["default_model"] == "gpt-4"
        assert data["default_temperature"] == 0.5
        assert data["default_max_tokens"] == 2048


# ==============================================================================
# DELETE /preferences Tests
# ==============================================================================


@pytest.mark.unit
class TestResetPreferences:
    """Tests for DELETE /api/v1/preferences endpoint."""

    def test_reset_preferences_to_defaults(self, client: TestClient) -> None:
        """Resetting should restore default preferences."""
        # First set custom preferences
        client.patch(
            "/api/v1/preferences",
            json={"theme": "dark", "language": "ja"},
        )

        # Reset
        response = client.delete("/api/v1/preferences")

        assert response.status_code == 200

        # Verify defaults are restored
        get_response = client.get("/api/v1/preferences")
        data = get_response.json()
        assert data["theme"] == "system"
        assert data["language"] == "en"

    def test_reset_returns_defaults(self, client: TestClient) -> None:
        """Reset endpoint should return the new default preferences."""
        response = client.delete("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "system"


# ==============================================================================
# Validation Tests
# ==============================================================================


@pytest.mark.unit
class TestPreferencesValidation:
    """Tests for preferences validation."""

    def test_temperature_range_validation(self, client: TestClient) -> None:
        """Temperature must be between 0 and 2."""
        # Too high
        response = client.patch("/api/v1/preferences", json={"default_temperature": 3.0})
        assert response.status_code == 422

        # Too low
        response = client.patch("/api/v1/preferences", json={"default_temperature": -1.0})
        assert response.status_code == 422

        # Valid
        response = client.patch("/api/v1/preferences", json={"default_temperature": 1.0})
        assert response.status_code == 200

    def test_max_tokens_validation(self, client: TestClient) -> None:
        """Max tokens must be positive."""
        response = client.patch("/api/v1/preferences", json={"default_max_tokens": -100})
        assert response.status_code == 422

    def test_font_size_validation(self, client: TestClient) -> None:
        """Font size must be valid enum value."""
        response = client.patch("/api/v1/preferences", json={"font_size": "invalid"})
        assert response.status_code == 422

        response = client.patch("/api/v1/preferences", json={"font_size": "large"})
        assert response.status_code == 200
