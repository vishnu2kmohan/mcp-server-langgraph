"""
Studio AI API Router Unit Tests.

Tests for unified Studio AI endpoints following TDD methodology.

Endpoints tested:
- POST /api/v1/studio/analyze - Unified composite analysis for all StudioShell AI capabilities

Reference: StudioShell AI Enhancement Analysis Plan - Sprint 1
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.ai,
]


@pytest.fixture
def mock_studio_result() -> dict:
    """Provide a mock Studio orchestration result for testing."""
    return {
        "user_id": "user-123",
        "session_id": "session-456",
        "analyses": {
            "persona_analysis": {"detected_persona": "alice-builder", "confidence": 0.85},
        },
        "cross_insights": ["User shows advanced usage patterns"],
        "failed_analyses": [],
        "total_cost": "0.05",
    }


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock StudioOrchestrator."""
    orchestrator = MagicMock()
    orchestrator.analyze = AsyncMock(
        return_value={
            "user_id": "user-123",
            "session_id": "session-456",
            "analyses": {},
            "cross_insights": [],
            "failed_analyses": [],
            "total_cost": Decimal("0.05"),
        }
    )
    orchestrator.is_enabled = True
    orchestrator.get_session_cost.return_value = Decimal("0.05")
    return orchestrator


# =============================================================================
# Module Import Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIModuleExists:
    """Tests for verifying the studio_ai module exists."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_ai_router_module_exists(self) -> None:
        """
        GIVEN the API v1 package
        WHEN importing studio_ai module
        THEN should import successfully.
        """
        from mcp_server_langgraph.api.v1 import studio_ai

        assert studio_ai is not None

    def test_studio_ai_router_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN accessing the router
        THEN should have a studio_ai_router object.
        """
        from mcp_server_langgraph.api.v1.studio_ai import studio_ai_router

        assert studio_ai_router is not None

    def test_router_has_analyze_endpoint(self) -> None:
        """
        GIVEN the studio_ai_router
        WHEN checking routes
        THEN should have /analyze endpoint.
        """
        from mcp_server_langgraph.api.v1.studio_ai import studio_ai_router

        routes = [route.path for route in studio_ai_router.routes]
        assert "/analyze" in routes


# =============================================================================
# Request/Response Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIRequestModels:
    """Tests for Studio AI request models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_analyze_request_model_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN importing StudioAnalyzeRequest
        THEN should import successfully.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeRequest

        assert StudioAnalyzeRequest is not None

    def test_studio_analyze_request_has_user_id(self) -> None:
        """
        GIVEN the StudioAnalyzeRequest model
        WHEN creating an instance
        THEN should require user_id field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeRequest

        request = StudioAnalyzeRequest(
            user_id="user-123",
            session_id="session-456",
        )
        assert request.user_id == "user-123"

    def test_studio_analyze_request_has_session_id(self) -> None:
        """
        GIVEN the StudioAnalyzeRequest model
        WHEN creating an instance
        THEN should require session_id field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeRequest

        request = StudioAnalyzeRequest(
            user_id="user-123",
            session_id="session-456",
        )
        assert request.session_id == "session-456"

    def test_studio_analyze_request_has_tasks(self) -> None:
        """
        GIVEN the StudioAnalyzeRequest model
        WHEN creating an instance with tasks
        THEN should accept list of tasks.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeRequest

        request = StudioAnalyzeRequest(
            user_id="user-123",
            session_id="session-456",
            tasks=[
                {"category": "ux", "type": "persona_analysis", "data": {}},
            ],
        )
        assert len(request.tasks) == 1

    def test_studio_analyze_request_has_persona(self) -> None:
        """
        GIVEN the StudioAnalyzeRequest model
        WHEN creating an instance with persona
        THEN should accept persona field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeRequest

        request = StudioAnalyzeRequest(
            user_id="user-123",
            session_id="session-456",
            persona="alice-builder",
        )
        assert request.persona == "alice-builder"


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIResponseModels:
    """Tests for Studio AI response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_analyze_response_model_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN importing StudioAnalyzeResponse
        THEN should import successfully.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeResponse

        assert StudioAnalyzeResponse is not None

    def test_studio_analyze_response_has_analyses(self) -> None:
        """
        GIVEN the StudioAnalyzeResponse model
        WHEN creating an instance
        THEN should have analyses field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeResponse

        response = StudioAnalyzeResponse(
            user_id="user-123",
            session_id="session-456",
            analyses={},
            cross_insights=[],
            failed_analyses=[],
        )
        assert hasattr(response, "analyses")

    def test_studio_analyze_response_has_cross_insights(self) -> None:
        """
        GIVEN the StudioAnalyzeResponse model
        WHEN creating an instance
        THEN should have cross_insights field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeResponse

        response = StudioAnalyzeResponse(
            user_id="user-123",
            session_id="session-456",
            analyses={},
            cross_insights=["test insight"],
            failed_analyses=[],
        )
        assert response.cross_insights == ["test insight"]

    def test_studio_analyze_response_has_total_cost(self) -> None:
        """
        GIVEN the StudioAnalyzeResponse model
        WHEN creating an instance
        THEN should have total_cost field.
        """
        from mcp_server_langgraph.api.v1.studio_ai import StudioAnalyzeResponse

        response = StudioAnalyzeResponse(
            user_id="user-123",
            session_id="session-456",
            analyses={},
            cross_insights=[],
            failed_analyses=[],
            total_cost="0.05",
        )
        assert response.total_cost == "0.05"


# =============================================================================
# Endpoint Tests
# =============================================================================


@pytest.fixture
async def test_app() -> FastAPI:
    """Create a test FastAPI app with Studio AI routes."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.studio_ai import studio_ai_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(studio_ai_router, prefix="/api/v1/studio")

    # Mock authentication - return a test user
    mock_user = {
        "sub": "user-123",
        "user_id": "user-123",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
        "realm_access": {"roles": ["user"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/studio/analyze",
            json={
                "user_id": "user-123",
                "session_id": "session-456",
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_analyze_endpoint_returns_json(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze
        THEN should return JSON response.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator") as mock_get:
            mock_orchestrator = MagicMock()
            mock_orchestrator.analyze = AsyncMock(
                return_value={
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "analyses": {},
                    "cross_insights": [],
                    "failed_analyses": [],
                    "total_cost": Decimal("0.05"),
                }
            )
            mock_get.return_value = mock_orchestrator

            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "user-123",
                    "session_id": "session-456",
                },
            )
            assert response.headers.get("content-type") == "application/json"

    @pytest.mark.asyncio
    async def test_analyze_returns_user_id(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze
        THEN should return response with user_id.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            with patch("mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator") as mock_get:
                mock_orchestrator = MagicMock()
                mock_orchestrator.analyze = AsyncMock(
                    return_value={
                        "user_id": "user-123",
                        "session_id": "session-456",
                        "analyses": {},
                        "cross_insights": [],
                        "failed_analyses": [],
                        "total_cost": Decimal("0"),
                    }
                )
                mock_get.return_value = mock_orchestrator

                response = await client.post(
                    "/api/v1/studio/analyze",
                    json={
                        "user_id": "user-123",
                        "session_id": "session-456",
                    },
                )
                data = response.json()
                assert data.get("user_id") == "user-123"

    @pytest.mark.asyncio
    async def test_analyze_returns_session_id(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze
        THEN should return response with session_id.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            with patch("mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator") as mock_get:
                mock_orchestrator = MagicMock()
                mock_orchestrator.analyze = AsyncMock(
                    return_value={
                        "user_id": "user-123",
                        "session_id": "session-456",
                        "analyses": {},
                        "cross_insights": [],
                        "failed_analyses": [],
                        "total_cost": Decimal("0"),
                    }
                )
                mock_get.return_value = mock_orchestrator

                response = await client.post(
                    "/api/v1/studio/analyze",
                    json={
                        "user_id": "user-123",
                        "session_id": "session-456",
                    },
                )
                data = response.json()
                assert data.get("session_id") == "session-456"

    @pytest.mark.asyncio
    async def test_analyze_returns_analyses(self, test_app: FastAPI) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze with tasks
        THEN should return analyses in response.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            # Create mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.analyze = AsyncMock(
                return_value={
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "analyses": {"persona_analysis": {"detected_persona": "bob", "confidence": 0.9}},
                    "cross_insights": [],
                    "failed_analyses": [],
                    "total_cost": Decimal("0.02"),
                }
            )

            # Use FastAPI dependency override
            test_app.dependency_overrides[get_studio_orchestrator] = lambda: mock_orchestrator
            try:
                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/studio/analyze",
                        json={
                            "user_id": "user-123",
                            "session_id": "session-456",
                            "tasks": [
                                {"category": "ux", "type": "persona_analysis", "data": {}},
                            ],
                        },
                    )
                    data = response.json()
                    assert "analyses" in data
                    assert "persona_analysis" in data["analyses"]
            finally:
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_analyze_returns_cross_insights(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze
        THEN should return cross_insights in response.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            with patch("mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator") as mock_get:
                mock_orchestrator = MagicMock()
                mock_orchestrator.analyze = AsyncMock(
                    return_value={
                        "user_id": "user-123",
                        "session_id": "session-456",
                        "analyses": {},
                        "cross_insights": ["User shows advanced patterns"],
                        "failed_analyses": [],
                        "total_cost": Decimal("0"),
                    }
                )
                mock_get.return_value = mock_orchestrator

                response = await client.post(
                    "/api/v1/studio/analyze",
                    json={
                        "user_id": "user-123",
                        "session_id": "session-456",
                    },
                )
                data = response.json()
                assert "cross_insights" in data

    @pytest.mark.asyncio
    async def test_analyze_returns_failed_analyses(self, test_app: FastAPI) -> None:
        """
        GIVEN the Studio AI router
        WHEN a task fails during analysis
        THEN should return failed_analyses in response.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            # Create mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.analyze = AsyncMock(
                return_value={
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "analyses": {},
                    "cross_insights": [],
                    "failed_analyses": ["error_analysis"],
                    "total_cost": Decimal("0"),
                }
            )

            # Use FastAPI dependency override
            test_app.dependency_overrides[get_studio_orchestrator] = lambda: mock_orchestrator
            try:
                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/studio/analyze",
                        json={
                            "user_id": "user-123",
                            "session_id": "session-456",
                            "tasks": [
                                {"category": "ux", "type": "error_analysis", "data": {}},
                            ],
                        },
                    )
                    data = response.json()
                    assert "failed_analyses" in data
                    assert "error_analysis" in data["failed_analyses"]
            finally:
                test_app.dependency_overrides.clear()


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIFeatureFlag:
    """Tests for feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_respects_feature_flag_disabled(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router with feature flag disabled
        WHEN calling POST /api/v1/studio/analyze
        THEN should return 503 or appropriate error.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = False

            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "user-123",
                    "session_id": "session-456",
                },
            )
            # When feature flag is disabled, should return 503 Service Unavailable
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_analyze_works_when_feature_flag_enabled(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router with feature flag enabled
        WHEN calling POST /api/v1/studio/analyze
        THEN should return 200 OK.
        """
        with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
            mock_flags.enable_studio_ai = True

            with patch("mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator") as mock_get:
                mock_orchestrator = MagicMock()
                mock_orchestrator.analyze = AsyncMock(
                    return_value={
                        "user_id": "user-123",
                        "session_id": "session-456",
                        "analyses": {},
                        "cross_insights": [],
                        "failed_analyses": [],
                        "total_cost": Decimal("0"),
                    }
                )
                mock_get.return_value = mock_orchestrator

                response = await client.post(
                    "/api/v1/studio/analyze",
                    json={
                        "user_id": "user-123",
                        "session_id": "session-456",
                    },
                )
                assert response.status_code == 200


# =============================================================================
# Input Validation Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIValidation:
    """Tests for input validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_requires_user_id(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze without user_id
        THEN should return 422 Unprocessable Entity.
        """
        response = await client.post(
            "/api/v1/studio/analyze",
            json={
                "session_id": "session-456",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analyze_requires_session_id(self, client: AsyncClient) -> None:
        """
        GIVEN the Studio AI router
        WHEN calling POST /api/v1/studio/analyze without session_id
        THEN should return 422 Unprocessable Entity.
        """
        response = await client.post(
            "/api/v1/studio/analyze",
            json={
                "user_id": "user-123",
            },
        )
        assert response.status_code == 422


# =============================================================================
# Dependency Injection Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_studio_ai")
class TestStudioAIDependencies:
    """Tests for dependency injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_studio_orchestrator_dependency_exists(self) -> None:
        """
        GIVEN the studio_ai module
        WHEN importing get_studio_orchestrator
        THEN should import successfully.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        assert get_studio_orchestrator is not None

    def test_get_studio_orchestrator_is_callable(self) -> None:
        """
        GIVEN the get_studio_orchestrator function
        WHEN checking its type
        THEN should be callable.
        """
        from mcp_server_langgraph.api.v1.studio_ai import get_studio_orchestrator

        assert callable(get_studio_orchestrator)
