"""
AI UX Endpoints Unit Tests.

Tests for AI-powered UX features following TDD methodology.

Endpoints tested:
- POST /api/v1/ai/disclosure/analyze - Progressive disclosure analysis
- POST /api/v1/ai/empty-state/suggestions - Empty state suggestions
- POST /api/v1/ai/nudges/recommend - Smart nudge recommendations
- POST /api/v1/ai/errors/analyze - Error recovery analysis
- POST /api/v1/ai/onboarding/personalize - Onboarding personalization
- GET /api/v1/ai/metrics/insights - HEART metrics insights
- POST /api/v1/ai/persona/analyze - Persona behavior analysis

Reference: UX Audit Plan - Phase 6 AI-Native Integration
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

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
def mock_llm_response() -> dict:
    """Provide a mock LLM response for testing."""
    return {
        "content": "Test response",
        "confidence": 0.85,
    }


@pytest.fixture
async def test_app() -> FastAPI:
    """Create a test FastAPI app with AI UX routes."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(ai_ux_router, prefix="/api/v1/ai")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
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


# =============================================================================
# Disclosure Analyzer Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestDisclosureAnalyzer:
    """Tests for the disclosure analyzer endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_disclosure_analyze_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/disclosure/analyze
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/disclosure/analyze",
            json={
                "user_id": "user-123",
                "session_history": [],
                "feature_usage": {},
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_disclosure_analyze_returns_level_recommendation(self, client: AsyncClient) -> None:
        """
        GIVEN a user with intermediate feature usage
        WHEN analyzing disclosure level
        THEN should return level recommendation with confidence.
        """
        response = await client.post(
            "/api/v1/ai/disclosure/analyze",
            json={
                "user_id": "user-123",
                "session_history": [
                    {"page": "/workflows", "duration_ms": 60000},
                    {"page": "/chat", "duration_ms": 120000},
                ],
                "feature_usage": {
                    "chat": 50,
                    "workflows": 10,
                    "mcp": 2,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "current_level" in data
        assert "recommended_level" in data
        assert "confidence" in data
        assert data["confidence"] >= 0 and data["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_disclosure_analyze_validates_input(self, client: AsyncClient) -> None:
        """
        GIVEN invalid input
        WHEN analyzing disclosure level
        THEN should return 422 validation error.
        """
        response = await client.post(
            "/api/v1/ai/disclosure/analyze",
            json={},  # Missing required fields
        )
        assert response.status_code == 422


# =============================================================================
# Empty State Suggestions Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestEmptyStateSuggestions:
    """Tests for the empty state suggestions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_empty_state_suggestions_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/empty-state/suggestions
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/empty-state/suggestions",
            json={
                "context": "workflows",
                "persona": "alice-builder",
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_empty_state_returns_suggestions(self, client: AsyncClient) -> None:
        """
        GIVEN a context and persona
        WHEN requesting empty state suggestions
        THEN should return actionable suggestions.
        """
        response = await client.post(
            "/api/v1/ai/empty-state/suggestions",
            json={
                "context": "workflows",
                "persona": "alice-builder",
                "session_id": "session-123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        if data["suggestions"]:
            suggestion = data["suggestions"][0]
            assert "text" in suggestion
            assert "action" in suggestion


# =============================================================================
# Nudge Recommendations Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestNudgeRecommendations:
    """Tests for the nudge recommendations endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_nudge_recommend_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/nudges/recommend
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/nudges/recommend",
            json={
                "user_id": "user-123",
                "current_context": {"page": "/chat"},
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_nudge_recommend_returns_nudge_or_null(self, client: AsyncClient) -> None:
        """
        GIVEN user context
        WHEN requesting nudge recommendation
        THEN should return nudge object or indicate not to show.
        """
        response = await client.post(
            "/api/v1/ai/nudges/recommend",
            json={
                "user_id": "user-123",
                "current_context": {
                    "page": "/chat",
                    "action": "viewing",
                    "time_on_page": 30000,
                },
                "nudge_history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "should_show" in data
        if data["should_show"]:
            assert "nudge" in data
            assert "confidence" in data


# =============================================================================
# Error Analysis Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestErrorAnalysis:
    """Tests for the error analysis endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_errors_analyze_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/errors/analyze
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/errors/analyze",
            json={
                "error": {
                    "message": "Connection timeout",
                    "name": "TimeoutError",
                },
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_errors_analyze_returns_classification(self, client: AsyncClient) -> None:
        """
        GIVEN an error object
        WHEN analyzing the error
        THEN should return classification and suggestions.
        """
        response = await client.post(
            "/api/v1/ai/errors/analyze",
            json={
                "error": {
                    "message": "Network request failed: timeout",
                    "name": "NetworkError",
                    "stack_trace": "at fetch() line 42",
                },
                "user_context": {
                    "persona": "alice-builder",
                    "recent_actions": ["save_workflow", "test_run"],
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "classification" in data
        assert "category" in data["classification"]
        assert "confidence" in data["classification"]
        assert "root_cause" in data
        assert "suggestions" in data


# =============================================================================
# Onboarding Personalization Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestOnboardingPersonalization:
    """Tests for the onboarding personalization endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_onboarding_personalize_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/onboarding/personalize
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/onboarding/personalize",
            json={
                "user_id": "new-user-123",
                "initial_actions": [],
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_onboarding_returns_personalized_path(self, client: AsyncClient) -> None:
        """
        GIVEN a new user with initial actions
        WHEN personalizing onboarding
        THEN should return detected intent and recommended path.
        """
        response = await client.post(
            "/api/v1/ai/onboarding/personalize",
            json={
                "user_id": "new-user-123",
                "initial_actions": ["viewed_workflows", "clicked_templates"],
                "signup_context": {"referrer": "github", "utm_source": "docs"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "detected_intent" in data
        assert "confidence" in data
        assert "recommended_path" in data


# =============================================================================
# Metrics Insights Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestMetricsInsights:
    """Tests for the metrics insights endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_metrics_insights_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling GET /api/v1/ai/metrics/insights
        THEN should return a valid response (not 404).
        """
        response = await client.get("/api/v1/ai/metrics/insights")
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_metrics_insights_returns_insights(self, client: AsyncClient) -> None:
        """
        GIVEN metrics data
        WHEN requesting insights
        THEN should return AI-generated insights and predictions.
        """
        response = await client.get("/api/v1/ai/metrics/insights")
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert "predictions" in data


# =============================================================================
# Persona Analysis Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_ai_ux_endpoints")
class TestPersonaAnalysis:
    """Tests for the persona analysis endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_persona_analyze_endpoint_exists(self, client: AsyncClient) -> None:
        """
        GIVEN the AI UX router
        WHEN calling POST /api/v1/ai/persona/analyze
        THEN should return a valid response (not 404).
        """
        response = await client.post(
            "/api/v1/ai/persona/analyze",
            json={
                "user_id": "user-123",
                "assigned_persona": "bob",
                "recent_actions": [],
            },
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_persona_analyze_returns_behavior_analysis(self, client: AsyncClient) -> None:
        """
        GIVEN user behavior data
        WHEN analyzing persona fit
        THEN should return detected persona and recommendations.
        """
        response = await client.post(
            "/api/v1/ai/persona/analyze",
            json={
                "user_id": "user-123",
                "assigned_persona": "bob",
                "recent_actions": [
                    "create_workflow",
                    "edit_node",
                    "run_test",
                    "view_traces",
                ],
                "feature_usage": {
                    "workflow_builder": 25,
                    "traces": 15,
                    "chat": 5,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "assigned_persona" in data
        assert "detected_persona" in data
        assert "confidence" in data
        assert "behavior_signals" in data
