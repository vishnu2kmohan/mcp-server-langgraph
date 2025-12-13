"""
Tests for HEART Metrics API

TDD: Tests written for the metrics API endpoints.

Follows memory safety patterns for pytest-xdist.
"""

import gc

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.metrics import router

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def app():
    """Create a test FastAPI app with the metrics router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.mark.xdist_group(name="metrics_api")
class TestSubmitHeartMetrics:
    """Tests for POST /api/v1/metrics/heart"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_submit_minimal_metrics(self, client):
        """Should accept minimal metrics batch."""
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "test-session-123",
                "app_name": "builder",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["message"] == "Metrics received successfully"

    def test_submit_full_metrics(self, client):
        """Should accept full metrics batch."""
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "test-session-456",
                "app_name": "playground",
                "task_success": {
                    "tasks_started": 10,
                    "tasks_completed": 8,
                    "tasks_errored": 2,
                },
                "engagement": {
                    "session_duration_ms": 300000,
                    "interaction_count": 50,
                    "feature_usage": {"code_generation": 5, "dark_mode": 2},
                },
                "happiness": {
                    "nps_score": 9,
                    "satisfaction_score": 4,
                },
                "adoption": {
                    "is_new_user": True,
                    "onboarding_steps_completed": ["welcome", "tutorial", "completed"],
                },
                "retention": {
                    "return_visits": 5,
                    "days_active": 7,
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "received_at" in data

    def test_invalid_app_name(self, client):
        """Should reject invalid app name."""
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "test-session",
                "app_name": "invalid",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_invalid_nps_score(self, client):
        """Should reject NPS score out of range."""
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "test-session",
                "app_name": "builder",
                "happiness": {"nps_score": 11},  # Max is 10
            },
        )
        assert response.status_code == 422


@pytest.mark.xdist_group(name="metrics_api")
class TestSubmitEvents:
    """Tests for POST /api/v1/metrics/events"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_submit_events_with_valid_batch_returns_count(self, client):
        """Should accept event batch."""
        response = client.post(
            "/api/v1/metrics/events",
            json={
                "session_id": "test-session-123",
                "app_name": "builder",
                "events": [
                    {"feature_name": "code_generation", "event_type": "used"},
                    {"feature_name": "dark_mode", "event_type": "clicked"},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 2
        assert "received_at" in data

    def test_submit_empty_events(self, client):
        """Should accept empty event list."""
        response = client.post(
            "/api/v1/metrics/events",
            json={
                "session_id": "test-session",
                "app_name": "builder",
                "events": [],
            },
        )
        assert response.status_code == 201
        assert response.json()["count"] == 0

    def test_submit_events_with_metadata(self, client):
        """Should accept events with metadata."""
        response = client.post(
            "/api/v1/metrics/events",
            json={
                "session_id": "test-session",
                "app_name": "playground",
                "events": [
                    {
                        "feature_name": "error",
                        "event_type": "error",
                        "metadata": {"error_code": 500, "retried": True},
                    },
                ],
            },
        )
        assert response.status_code == 201


@pytest.mark.xdist_group(name="metrics_api")
class TestAggregateMetrics:
    """Tests for GET /api/v1/metrics/heart/aggregate"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_aggregate_metrics(self, client):
        """Should return aggregate metrics."""
        response = client.get("/api/v1/metrics/heart/aggregate")
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "nps_score_avg" in data
        assert "task_success_rate" in data

    def test_get_aggregate_with_period(self, client):
        """Should accept period parameter."""
        response = client.get("/api/v1/metrics/heart/aggregate?period=30d")
        assert response.status_code == 200
        assert response.json()["period"] == "30d"

    def test_get_aggregate_with_app_filter(self, client):
        """Should accept app filter parameter."""
        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        assert response.status_code == 200
        assert response.json()["app_name"] == "builder"


@pytest.mark.xdist_group(name="metrics_api")
class TestDashboard:
    """Tests for GET /api/v1/metrics/dashboard"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_dashboard_returns_both_apps_data(self, client):
        """Should return dashboard data."""
        response = client.get("/api/v1/metrics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "builder" in data
        assert "playground" in data
        assert "total_metrics_count" in data
        assert "total_events_count" in data
        assert "generated_at" in data
