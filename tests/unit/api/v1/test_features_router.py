"""
Features Router Unit Tests

Tests for /api/v1/features endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The features endpoint returns UI feature flags for the frontend.
"""

import gc
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the features router."""
    from mcp_server_langgraph.api.v1.features import features_router

    app = FastAPI()
    app.include_router(features_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_features_router")
class TestFeaturesEndpoint:
    """Tests for GET /api/v1/features endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_features_returns_200(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/features
        WHEN GET request is made
        THEN response should be 200 OK
        """
        response = client.get("/api/v1/features")

        assert response.status_code == 200

    def test_get_features_returns_feature_dict(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/features
        WHEN GET request is made
        THEN response should contain feature keys
        """
        response = client.get("/api/v1/features")
        data = response.json()

        assert "workflows" in data
        assert "sessions" in data
        assert "cost_dashboard" in data
        assert "observability" in data
        assert "code_export" in data
        assert "ai_suggestions" in data
        assert "mcp_websocket" in data

    def test_get_features_defaults_to_user_role(self, client: TestClient) -> None:
        """
        GIVEN no role specified
        WHEN GET request is made
        THEN features should be for 'user' role (cost_dashboard False by default)
        """
        response = client.get("/api/v1/features")
        data = response.json()

        # Default user role should not see cost dashboard (by default)
        assert data["cost_dashboard"] is False

    def test_get_features_with_admin_role(self, client: TestClient) -> None:
        """
        GIVEN role=admin query parameter
        WHEN GET request is made
        THEN admin should see all features including cost_dashboard
        """
        response = client.get("/api/v1/features?role=admin")
        data = response.json()

        assert data["cost_dashboard"] is True
        assert data["workflows"] is True
        assert data["sessions"] is True


@pytest.mark.xdist_group(name="test_features_router")
class TestFeaturesEndpointWithMockedFlags:
    """
    Tests for features endpoint with mocked feature flags.

    NOTE: These tests are skipped in pytest-xdist parallel mode due to mock pollution
    from GCP observability tests. Run serially with: pytest tests/unit/api/v1/test_features_router.py -xvs
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Mock pollution in xdist parallel mode. Run serially for reliable results.",
    )
    def test_features_reflect_disabled_workflow_feature(self, test_app: FastAPI) -> None:
        """
        GIVEN enable_workflows_feature is False
        WHEN GET request is made
        THEN workflows should be False in response
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.get_ui_features_for_role.return_value = {
            "workflows": False,
            "sessions": True,
            "cost_dashboard": False,
            "observability": True,
            "code_export": True,
            "ai_suggestions": True,
            "mcp_websocket": False,
        }

        with patch("mcp_server_langgraph.api.v1.features.get_feature_flags", return_value=mock_flags):
            client = TestClient(test_app)
            response = client.get("/api/v1/features")
            data = response.json()

            assert data["workflows"] is False

    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Mock pollution in xdist parallel mode. Run serially for reliable results.",
    )
    def test_features_with_mcp_websocket_enabled(self, test_app: FastAPI) -> None:
        """
        GIVEN enable_mcp_websocket is True
        WHEN GET request is made
        THEN mcp_websocket should be True in response
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.get_ui_features_for_role.return_value = {
            "workflows": True,
            "sessions": True,
            "cost_dashboard": True,
            "observability": True,
            "code_export": True,
            "ai_suggestions": True,
            "mcp_websocket": True,
        }

        with patch("mcp_server_langgraph.api.v1.features.get_feature_flags", return_value=mock_flags):
            client = TestClient(test_app)
            response = client.get("/api/v1/features?role=admin")
            data = response.json()

            assert data["mcp_websocket"] is True


@pytest.mark.xdist_group(name="test_features_router")
class TestFeaturesResponseModel:
    """Tests for features response model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_model_validates_schema(self, client: TestClient) -> None:
        """
        GIVEN a valid request
        WHEN GET request is made
        THEN response should match UIFeaturesResponse schema
        """
        response = client.get("/api/v1/features")
        data = response.json()

        # All values should be booleans or strings (for strategy enums)
        allowed_types = (bool, str)
        for key, value in data.items():
            assert isinstance(value, allowed_types), f"{key} should be bool or str, got {type(value)}"

    def test_response_includes_content_type_json(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/features
        WHEN GET request is made
        THEN content-type should be application/json
        """
        response = client.get("/api/v1/features")

        assert "application/json" in response.headers.get("content-type", "")
