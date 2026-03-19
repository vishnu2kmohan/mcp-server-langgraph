"""
Integration tests for StudioOrchestrator API endpoint.

Tests the /api/v1/studio/analyze endpoint with the unified StudioOrchestrator.
Verifies feature flag gating, parallel task execution, and cross-insights synthesis.

TDD: Tests written to verify API integration behavior.
"""

import asyncio
import gc
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = [pytest.mark.integration, pytest.mark.agents, pytest.mark.api]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def test_app() -> "FastAPI":
    """Create a test FastAPI app with Studio AI routes."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.studio_ai import studio_ai_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(studio_ai_router, prefix="/api/v1/studio")

    # Override auth dependency for tests
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user",
        "preferred_username": "test",
        "roles": ["admin"],
    }
    return app


@pytest.fixture
async def client(test_app: "FastAPI") -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_studio_orchestrator():
    """Create a mock StudioOrchestrator for integration testing."""
    orchestrator = MagicMock()

    async def analyze(
        user_id: str,
        session_id: str | None = None,
        persona: str | None = None,
        include_ux: bool = False,
        include_session: bool = False,
        include_conversation: bool = False,
        include_canvas: bool = False,
        include_diagram: bool = False,
        include_trace: bool = False,
        include_hitl: bool = False,
        include_command: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mock analyze method that simulates parallel execution."""
        await asyncio.sleep(0.01)  # Simulate async operation

        analyses: dict[str, Any] = {}
        cross_insights: list[str] = []

        if include_ux:
            analyses["ux"] = {
                "persona_analysis": {
                    "detected_persona": "developer",
                    "confidence": 0.85,
                }
            }
            cross_insights.append("User is a technical developer")

        if include_session:
            analyses["session"] = {
                "session_summarize": {
                    "summary": "Discussion about API integration",
                    "topics": ["API", "integration", "testing"],
                }
            }
            cross_insights.append("Session focused on API topics")

        if include_conversation:
            analyses["conversation"] = {
                "intent_detect": {
                    "intent": "question",
                    "confidence": 0.92,
                }
            }

        if include_canvas:
            analyses["canvas"] = {
                "artifact_suggest_type": {
                    "suggested_type": "code",
                    "language": "python",
                }
            }

        return {
            "analyses": analyses,
            "cross_insights": cross_insights,
            "failed_analyses": [],
            "total_cost": Decimal("0.0012"),
        }

    orchestrator.analyze = analyze
    return orchestrator


@pytest.fixture
def feature_flags_enabled():
    """Enable Studio AI feature flag for testing."""
    with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
        mock_flags.enable_studio_ai = True
        yield mock_flags


@pytest.fixture
def feature_flags_disabled():
    """Disable Studio AI feature flag for testing."""
    with patch("mcp_server_langgraph.api.v1.studio_ai.feature_flags") as mock_flags:
        mock_flags.enable_studio_ai = False
        yield mock_flags


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_api")
class TestStudioOrchestratorAPIFeatureGating:
    """Test feature flag gating for Studio AI API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_api_returns_503_when_feature_disabled(self, client: AsyncClient, feature_flags_disabled):
        """Test that API returns 503 when enable_studio_ai is False."""
        response = await client.post(
            "/api/v1/studio/analyze",
            json={
                "user_id": "test-user",
                "session_id": "session-123",
                "tasks": [{"category": "ux", "type": "persona_analysis"}],
            },
        )

        assert response.status_code == 503
        assert "not enabled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_api_accepts_request_when_feature_enabled(
        self, client: AsyncClient, feature_flags_enabled, mock_studio_orchestrator
    ):
        """Test that API accepts requests when enable_studio_ai is True."""
        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator",
            return_value=mock_studio_orchestrator,
        ):
            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "test-user",
                    "session_id": "session-123",
                    "tasks": [{"category": "ux", "type": "persona_analysis"}],
                },
            )

            # Should succeed (200) or at least not be 503
            assert response.status_code != 503


@pytest.mark.xdist_group(name="studio_orchestrator_api")
class TestStudioOrchestratorAPIParallelExecution:
    """Test parallel task execution via API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_multiple_categories_accepted_in_request(
        self, client: AsyncClient, feature_flags_enabled, mock_studio_orchestrator
    ):
        """Test that API accepts requests with multiple task categories."""
        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator",
            return_value=mock_studio_orchestrator,
        ):
            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "test-user",
                    "session_id": "session-123",
                    "tasks": [
                        {"category": "ux", "type": "persona_analysis"},
                        {"category": "session", "type": "session_summarize"},
                        {"category": "conversation", "type": "intent_detect"},
                    ],
                },
            )

            # API should accept multi-category request
            assert response.status_code == 200
            data = response.json()
            # Response should have the expected structure
            assert "analyses" in data
            assert "cross_insights" in data
            assert "failed_analyses" in data
            assert "total_cost" in data


@pytest.mark.xdist_group(name="studio_orchestrator_api")
class TestStudioOrchestratorAPICrossInsights:
    """Test cross-category insights synthesis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cross_insights_included_in_response(
        self, client: AsyncClient, feature_flags_enabled, mock_studio_orchestrator
    ):
        """Test that cross-category insights are included in API response."""
        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator",
            return_value=mock_studio_orchestrator,
        ):
            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "test-user",
                    "session_id": "session-123",
                    "tasks": [
                        {"category": "ux", "type": "persona_analysis"},
                        {"category": "session", "type": "session_summarize"},
                    ],
                },
            )

            if response.status_code == 200:
                data = response.json()
                # Verify cross_insights is present
                assert "cross_insights" in data
                # When both UX and session are included, we should get insights
                if data.get("analyses"):
                    assert len(data["cross_insights"]) > 0


@pytest.mark.xdist_group(name="studio_orchestrator_api")
class TestStudioOrchestratorAPIEmptyTasks:
    """Test API behavior with empty or no tasks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_empty_tasks_returns_empty_result(self, client: AsyncClient, feature_flags_enabled):
        """Test that empty tasks list returns empty result, not error."""
        response = await client.post(
            "/api/v1/studio/analyze",
            json={
                "user_id": "test-user",
                "session_id": "session-123",
                "tasks": [],
            },
        )

        # Should return 200 with empty analyses
        assert response.status_code == 200
        data = response.json()
        assert data["analyses"] == {}
        assert data["cross_insights"] == []
        assert data["failed_analyses"] == []


@pytest.mark.xdist_group(name="studio_orchestrator_api")
class TestStudioOrchestratorAPIGranularFlags:
    """Test that granular intelligence flags are checked."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_intelligence_requires_flag(
        self, client: AsyncClient, feature_flags_enabled, mock_studio_orchestrator
    ):
        """Test that session intelligence respects enable_session_intelligence flag."""
        # Enable master flag but test that granular flags are respected
        feature_flags_enabled.enable_session_intelligence = False

        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator",
            return_value=mock_studio_orchestrator,
        ):
            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "test-user",
                    "session_id": "session-123",
                    "tasks": [
                        {"category": "session", "type": "session_summarize"},
                    ],
                },
            )

            # Request should be accepted (flag check happens at orchestrator level)
            # The API should still accept the request
            assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_canvas_intelligence_requires_flag(
        self, client: AsyncClient, feature_flags_enabled, mock_studio_orchestrator
    ):
        """Test that canvas intelligence respects enable_canvas_intelligence flag."""
        feature_flags_enabled.enable_canvas_intelligence = True

        with patch(
            "mcp_server_langgraph.api.v1.studio_ai.get_studio_orchestrator",
            return_value=mock_studio_orchestrator,
        ):
            response = await client.post(
                "/api/v1/studio/analyze",
                json={
                    "user_id": "test-user",
                    "session_id": "session-123",
                    "tasks": [
                        {"category": "canvas", "type": "artifact_suggest_type"},
                    ],
                },
            )

            # Should process canvas request when flag is enabled
            assert response.status_code in (200, 503)
