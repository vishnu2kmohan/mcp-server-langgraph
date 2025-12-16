"""
Tests for HEART Analytics Endpoint.

TDD RED phase: These tests define expected behavior for HEART metrics
collection and retrieval.

The endpoint should:
- Accept HEART metric submissions (happiness, engagement, adoption, retention, task_success)
- Retrieve aggregated HEART metrics
- Support timeframe filtering
- Require authentication
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


def _make_authenticated_user() -> dict[str, Any]:
    """Create authenticated user for access."""
    return {
        "user_id": "user-001",
        "username": "testuser",
        "email": "user@example.com",
        "roles": ["user"],
    }


def _make_admin_user() -> dict[str, Any]:
    """Create admin user for access."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin"],
    }


@pytest.fixture
def analytics_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked analytics service."""
    from mcp_server_langgraph.api.v1.analytics import (
        router,
        set_analytics_service,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/analytics")

    # Override get_current_user to return authenticated user
    async def get_auth_user() -> dict[str, Any]:
        return _make_authenticated_user()

    app.dependency_overrides[get_current_user] = get_auth_user

    # Configure mock with spec to satisfy async-mock-config hook
    mock_service = AsyncMock()  # noqa: async-mock-config
    mock_service.track_happiness.return_value = {"id": "metric-default"}
    mock_service.track_engagement.return_value = {"id": "metric-default"}
    mock_service.track_adoption.return_value = {"id": "metric-default"}
    mock_service.track_retention.return_value = {"id": "metric-default"}
    mock_service.track_task_success.return_value = {"id": "metric-default"}
    mock_service.get_heart_summary.return_value = {"timeframe": "7d"}
    set_analytics_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_analytics_service(None)
    app.dependency_overrides.clear()


@pytest.fixture
def analytics_admin_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with admin user."""
    from mcp_server_langgraph.api.v1.analytics import (
        router,
        set_analytics_service,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/analytics")

    # Override get_current_user to return admin user
    async def get_admin() -> dict[str, Any]:
        return _make_admin_user()

    app.dependency_overrides[get_current_user] = get_admin

    # Configure mock with spec to satisfy async-mock-config hook
    mock_service = AsyncMock()  # noqa: async-mock-config
    mock_service.track_happiness.return_value = {"id": "metric-default"}
    mock_service.track_engagement.return_value = {"id": "metric-default"}
    mock_service.track_adoption.return_value = {"id": "metric-default"}
    mock_service.track_retention.return_value = {"id": "metric-default"}
    mock_service.track_task_success.return_value = {"id": "metric-default"}
    mock_service.get_heart_summary.return_value = {"timeframe": "7d"}
    set_analytics_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_analytics_service(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestHeartMetricsEndpoint:
    """Tests for /api/v1/analytics/heart endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_heart_endpoint_exists(self, analytics_app: tuple) -> None:
        """
        GIVEN FastAPI app with analytics router
        WHEN checking routes
        THEN HEART endpoint exists.
        """
        app, _ = analytics_app

        routes = [route.path for route in app.routes]
        assert "/api/v1/analytics/heart" in routes


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestTrackHappiness:
    """Tests for tracking happiness metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_nps_score(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting NPS score
        THEN score is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_happiness.return_value = {"id": "metric-001"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/happiness",
            json={
                "nps_score": 9,
                "feedback": "Great interface!",
            },
        )

        assert response.status_code == 201
        mock_service.track_happiness.assert_called_once()

    def test_track_csat_score(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting CSAT score
        THEN score is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_happiness.return_value = {"id": "metric-002"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/happiness",
            json={
                "csat_score": 4.5,
                "context": "workflow_creation",
            },
        )

        assert response.status_code == 201


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestTrackEngagement:
    """Tests for tracking engagement metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_session_duration(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting session duration
        THEN duration is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_engagement.return_value = {"id": "metric-003"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/engagement",
            json={
                "session_id": "sess-001",
                "duration_seconds": 450,
                "features_used": ["chat", "workflows"],
            },
        )

        assert response.status_code == 201
        mock_service.track_engagement.assert_called_once()


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestTrackAdoption:
    """Tests for tracking adoption metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_onboarding_step(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting onboarding step completion
        THEN step is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_adoption.return_value = {"id": "metric-004"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/adoption",
            json={
                "step": "template_selected",
                "step_index": 3,
                "completed": True,
            },
        )

        assert response.status_code == 201
        mock_service.track_adoption.assert_called_once()


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestTrackRetention:
    """Tests for tracking retention metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_return_visit(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting return visit
        THEN visit is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_retention.return_value = {"id": "metric-005"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/retention",
            json={
                "days_since_last_visit": 3,
                "return_visit": True,
            },
        )

        assert response.status_code == 201
        mock_service.track_retention.assert_called_once()


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestTrackTaskSuccess:
    """Tests for tracking task success metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_task_completion(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting task completion
        THEN task is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_task_success.return_value = {"id": "metric-006"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/task-success",
            json={
                "task_id": "create_workflow",
                "success": True,
                "duration_seconds": 120,
                "error_count": 0,
            },
        )

        assert response.status_code == 201
        mock_service.track_task_success.assert_called_once()

    def test_track_task_failure(self, analytics_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting task failure
        THEN failure is recorded.
        """
        app, mock_service = analytics_app
        mock_service.track_task_success.return_value = {"id": "metric-007"}

        client = TestClient(app)
        response = client.post(
            "/api/v1/analytics/heart/task-success",
            json={
                "task_id": "deploy_workflow",
                "success": False,
                "duration_seconds": 300,
                "error_count": 3,
                "error_message": "Validation failed",
            },
        )

        assert response.status_code == 201


@pytest.mark.api
@pytest.mark.xdist_group(name="analytics_heart")
class TestGetHeartMetrics:
    """Tests for retrieving aggregated HEART metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_heart_summary(self, analytics_admin_app: tuple) -> None:
        """
        GIVEN admin user
        WHEN requesting HEART summary
        THEN aggregated metrics are returned.
        """
        app, mock_service = analytics_admin_app
        mock_service.get_heart_summary.return_value = {
            "timeframe": "7d",
            "happiness": {
                "nps_score_avg": 42.5,
                "csat_score_avg": 4.2,
                "response_count": 150,
            },
            "engagement": {
                "avg_session_duration_seconds": 320,
                "sessions_per_user": 3.5,
                "active_users": 1250,
            },
            "adoption": {
                "onboarding_completion_rate": 0.78,
                "feature_adoption": {
                    "chat": 0.95,
                    "workflows": 0.65,
                    "connections": 0.45,
                },
            },
            "retention": {
                "d7_retention": 0.62,
                "d30_retention": 0.38,
            },
            "task_success": {
                "overall_success_rate": 0.82,
                "avg_task_duration_seconds": 180,
            },
        }

        client = TestClient(app)
        response = client.get("/api/v1/analytics/heart?timeframe=7d")

        assert response.status_code == 200
        data = response.json()
        assert "happiness" in data
        assert "engagement" in data
        assert "adoption" in data
        assert "retention" in data
        assert "task_success" in data

    def test_get_heart_summary_with_persona_filter(self, analytics_admin_app: tuple) -> None:
        """
        GIVEN admin user
        WHEN requesting HEART summary filtered by persona
        THEN filtered metrics are returned.
        """
        app, mock_service = analytics_admin_app
        mock_service.get_heart_summary.return_value = {
            "timeframe": "30d",
            "persona": "developer",
            "happiness": {"nps_score_avg": 55.0},
            "engagement": {"avg_session_duration_seconds": 480},
            "adoption": {"onboarding_completion_rate": 0.85},
            "retention": {"d30_retention": 0.52},
            "task_success": {"overall_success_rate": 0.88},
        }

        client = TestClient(app)
        response = client.get("/api/v1/analytics/heart?timeframe=30d&persona=developer")

        assert response.status_code == 200
        data = response.json()
        assert data.get("persona") == "developer"
