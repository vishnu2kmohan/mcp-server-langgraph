"""
Frontend API Smoke Tests.

These tests verify that all frontend-facing API endpoints return valid
responses and don't raise NotImplementedError. They run against a real
backend without mocking.

Purpose:
- Catch NotImplementedError in production code paths
- Verify API contracts before deployment
- Ensure frontend pages can load without 500 errors

History:
- December 2024: Created after discovering NotImplementedError in
  CostService, ObservabilityService, and ChatService broke the frontend.

Note:
- Tests marked with @pytest.mark.infrastructure require external services
- Other tests should pass even without infrastructure
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e

if TYPE_CHECKING:
    pass


@pytest.fixture
def app_with_full_api() -> FastAPI:
    """Create a FastAPI app with the full v1 API mounted."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.router import v1_router

    app = FastAPI()
    app.include_router(v1_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app_with_full_api: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_full_api)


@pytest.mark.smoke
@pytest.mark.xdist_group(name="frontend_smoke")
class TestFrontendAPISmokeTests:
    """
    Smoke tests for frontend-facing API endpoints.

    These tests verify that endpoints return proper HTTP responses
    rather than 500 Internal Server Error due to NotImplementedError.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # MCP API Smoke Tests (new MCP 2025-11-25 endpoints - no infrastructure required)
    # =========================================================================

    def test_mcp_resources_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the MCP API
        WHEN GET /mcp/resources is called
        THEN it returns 200 (not 500 NotImplementedError)
        """
        response = client.get("/api/v1/mcp/resources")

        # MCP resources returns empty list when not configured
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert isinstance(data["resources"], list)

    def test_mcp_tasks_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the MCP API
        WHEN GET /mcp/tasks is called
        THEN it returns 200 (not 500 NotImplementedError)
        """
        response = client.get("/api/v1/mcp/tasks")

        # MCP tasks returns empty list when not configured
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    # =========================================================================
    # Feature Flags API Smoke Tests (no infrastructure required)
    # =========================================================================

    def test_features_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the features API
        WHEN GET /features is called
        THEN it returns 200 (features should always be available)
        """
        response = client.get("/api/v1/features")

        assert response.status_code == 200
        data = response.json()
        assert "features" in data or isinstance(data, dict)

    # =========================================================================
    # User API Smoke Tests (no infrastructure required)
    # =========================================================================

    def test_user_me_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the user API
        WHEN GET /me is called
        THEN it returns valid response (auth may be required)
        """
        response = client.get("/api/v1/me")

        # Without auth, should return 401 or anonymous user info
        assert response.status_code in [200, 401, 403]

    # =========================================================================
    # Sessions API Smoke Tests
    # =========================================================================

    def test_sessions_list_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the sessions API
        WHEN GET /sessions is called
        THEN it returns valid response (not 500 NotImplementedError)
        """
        response = client.get("/api/v1/sessions")

        # Sessions may require auth or storage
        assert response.status_code in [200, 401, 403, 500]
        if response.status_code == 500:
            # Ensure it's not NotImplementedError
            assert "NotImplementedError" not in response.text

    # =========================================================================
    # Chat API Smoke Tests
    # =========================================================================

    def test_chat_history_endpoint_responds(self, client: TestClient) -> None:
        """GIVEN the chat API
        WHEN GET /chat/{session_id}/history is called
        THEN it returns valid response (not 500 NotImplementedError)
        """
        response = client.get("/api/v1/chat/test-session/history")

        # Chat history returns empty when no storage
        assert response.status_code in [200, 404, 500]
        if response.status_code == 500:
            assert "NotImplementedError" not in response.text


@pytest.mark.smoke
@pytest.mark.infrastructure
@pytest.mark.xdist_group(name="frontend_smoke_infra")
class TestFrontendAPIInfrastructureTests:
    """
    Smoke tests that require external infrastructure.

    These tests verify API behavior when connected to real backends
    like PostgreSQL, Tempo, Prometheus, etc.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skip(reason="Requires DATABASE_URL configured")
    def test_cost_summary_endpoint_with_db(self, client: TestClient) -> None:
        """GIVEN the cost API with database configured
        WHEN GET /cost/summary is called
        THEN it returns 200 with cost data
        """
        response = client.get("/api/v1/cost/summary")
        assert response.status_code == 200

    @pytest.mark.skip(reason="Requires Tempo configured")
    def test_observability_traces_endpoint_with_tempo(self, client: TestClient) -> None:
        """GIVEN the observability API with Tempo configured
        WHEN GET /observability/traces is called
        THEN it returns 200 with trace data
        """
        response = client.get("/api/v1/observability/traces")
        assert response.status_code == 200


@pytest.mark.smoke
@pytest.mark.xdist_group(name="frontend_response_format")
class TestFrontendAPIResponseFormats:
    """
    Tests that verify API response formats match frontend expectations.

    These use mocked services to verify response structure.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_resources_returns_expected_structure(self, client: TestClient) -> None:
        """GIVEN the MCP API returns 200
        WHEN the response is parsed
        THEN it has the expected structure for the frontend
        """
        response = client.get("/api/v1/mcp/resources")

        assert response.status_code == 200
        data = response.json()
        # These fields are expected by MCPPage.tsx
        assert "resources" in data
        assert isinstance(data["resources"], list)

    def test_mcp_tasks_returns_expected_structure(self, client: TestClient) -> None:
        """GIVEN the MCP API returns 200
        WHEN the response is parsed
        THEN it has the expected structure for the frontend
        """
        response = client.get("/api/v1/mcp/tasks")

        assert response.status_code == 200
        data = response.json()
        # These fields are expected by MCPPage.tsx
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_features_returns_expected_structure(self, client: TestClient) -> None:
        """GIVEN the features API returns 200
        WHEN the response is parsed
        THEN it has the expected structure for the frontend
        """
        response = client.get("/api/v1/features")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
