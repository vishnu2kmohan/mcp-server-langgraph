"""
Integration tests for HEART Metrics API.

Tests the full end-to-end flow of HEART framework metrics:
- Happiness: NPS scores, satisfaction ratings
- Engagement: Session duration, feature usage
- Adoption: New user tracking, onboarding
- Retention: Return visits, active days
- Task Success: Completion rates, error rates

These tests verify:
1. Metrics submission with real HTTP calls
2. Dashboard aggregation across multiple submissions
3. Metrics persistence and retrieval
4. Event batch processing

References:
    - ADR-0070: Unified Audit Logging Facility
    - src/mcp_server_langgraph/api/metrics.py
"""

import gc

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.metrics import (
    _events_store,
    _feedback_store,
    _metrics_store,
    router,
)

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.health]


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


@pytest.fixture(autouse=True)
def clear_stores():
    """Clear in-memory stores before each test."""
    _metrics_store.clear()
    _events_store.clear()
    _feedback_store.clear()
    yield
    # Cleanup after test
    _metrics_store.clear()
    _events_store.clear()
    _feedback_store.clear()


@pytest.mark.xdist_group(name="heart_metrics_integration")
class TestHeartMetricsIntegration:
    """Integration tests for HEART metrics end-to-end flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_full_metrics_flow_submit_and_aggregate(self, client):
        """
        GIVEN: Multiple HEART metrics submissions from different users
        WHEN: Aggregation is requested
        THEN: Dashboard shows correct aggregated values
        """
        # Submit metrics from builder app - User 1
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "user-1-session",
                "app_name": "builder",
                "task_success": {
                    "tasks_started": 10,
                    "tasks_completed": 8,
                    "tasks_errored": 2,
                },
                "happiness": {
                    "nps_score": 9,
                    "satisfaction_score": 4,
                },
                "engagement": {
                    "session_duration_ms": 300000,
                    "interaction_count": 50,
                    "feature_usage": {"code_generation": 5},
                },
            },
        )
        assert response.status_code == 201

        # Submit metrics from builder app - User 2
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "user-2-session",
                "app_name": "builder",
                "task_success": {
                    "tasks_started": 20,
                    "tasks_completed": 18,
                    "tasks_errored": 2,
                },
                "happiness": {
                    "nps_score": 7,
                    "satisfaction_score": 3,
                },
                "engagement": {
                    "session_duration_ms": 600000,
                    "interaction_count": 100,
                    "feature_usage": {"code_generation": 10, "dark_mode": 2},
                },
            },
        )
        assert response.status_code == 201

        # Submit metrics from playground app - User 3
        response = client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "user-3-session",
                "app_name": "playground",
                "task_success": {
                    "tasks_started": 5,
                    "tasks_completed": 5,
                    "tasks_errored": 0,
                },
                "happiness": {
                    "nps_score": 10,
                    "satisfaction_score": 5,
                },
            },
        )
        assert response.status_code == 201

        # Get aggregate for builder app only
        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation
        assert data["app_name"] == "builder"
        assert data["nps_score_avg"] == 8.0  # (9 + 7) / 2
        assert data["satisfaction_avg"] == 3.5  # (4 + 3) / 2
        assert data["total_tasks_started"] == 30  # 10 + 20
        assert data["total_tasks_completed"] == 26  # 8 + 18
        assert data["total_tasks_errored"] == 4  # 2 + 2
        assert data["total_interactions"] == 150  # 50 + 100
        assert "code_generation" in data["top_features"]
        assert data["top_features"]["code_generation"] == 15  # 5 + 10

        # Get dashboard data (all apps)
        response = client.get("/api/v1/metrics/dashboard")
        assert response.status_code == 200
        dashboard = response.json()

        assert dashboard["total_metrics_count"] == 3
        assert "builder" in dashboard
        assert "playground" in dashboard

    def test_task_success_rate_calculation(self, client):
        """
        GIVEN: Multiple task success metrics submissions
        WHEN: Aggregation is requested
        THEN: Task success rate is correctly calculated
        """
        # Perfect success rate
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "session-1",
                "app_name": "builder",
                "task_success": {
                    "tasks_started": 100,
                    "tasks_completed": 100,
                    "tasks_errored": 0,
                },
            },
        )

        # 50% success rate
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "session-2",
                "app_name": "builder",
                "task_success": {
                    "tasks_started": 100,
                    "tasks_completed": 50,
                    "tasks_errored": 50,
                },
            },
        )

        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        data = response.json()

        # (100 + 50) / (100 + 100) = 0.75
        assert data["task_success_rate"] == 0.75
        assert data["total_tasks_started"] == 200
        assert data["total_tasks_completed"] == 150
        assert data["total_tasks_errored"] == 50

    def test_event_batch_integration(self, client):
        """
        GIVEN: Multiple event batches from same session
        WHEN: Events are submitted
        THEN: All events are stored and counted
        """
        # First batch
        response = client.post(
            "/api/v1/metrics/events",
            json={
                "session_id": "session-1",
                "app_name": "builder",
                "events": [
                    {"feature_name": "code_generation", "event_type": "used"},
                    {"feature_name": "save_workflow", "event_type": "used"},
                ],
            },
        )
        assert response.status_code == 201
        assert response.json()["count"] == 2

        # Second batch
        response = client.post(
            "/api/v1/metrics/events",
            json={
                "session_id": "session-1",
                "app_name": "builder",
                "events": [
                    {"feature_name": "code_generation", "event_type": "used"},
                    {"feature_name": "error_recovery", "event_type": "error"},
                ],
            },
        )
        assert response.status_code == 201
        assert response.json()["count"] == 2

        # Check dashboard shows total events
        response = client.get("/api/v1/metrics/dashboard")
        dashboard = response.json()
        assert dashboard["total_events_count"] == 4

    def test_feedback_flow_nps_and_csat(self, client):
        """
        GIVEN: Multiple feedback submissions
        WHEN: NPS and CSAT scores are submitted
        THEN: All feedback is stored successfully
        """
        # NPS promoter (9-10)
        response = client.post(
            "/api/v1/metrics/feedback",
            json={
                "nps_score": 10,
                "comment": "Amazing product!",
            },
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

        # NPS passive (7-8)
        response = client.post(
            "/api/v1/metrics/feedback",
            json={
                "nps_score": 8,
                "comment": "Good but could be better",
            },
        )
        assert response.status_code == 201

        # CSAT only
        response = client.post(
            "/api/v1/metrics/feedback",
            json={
                "csat_rating": 4,
            },
        )
        assert response.status_code == 201

        # Combined NPS and CSAT
        response = client.post(
            "/api/v1/metrics/feedback",
            json={
                "nps_score": 9,
                "csat_rating": 5,
                "comment": "Excellent!",
            },
        )
        assert response.status_code == 201

        # Verify all feedback stored
        assert len(_feedback_store) == 4

    def test_adoption_and_retention_metrics(self, client):
        """
        GIVEN: Adoption and retention metrics from multiple users
        WHEN: Aggregation is requested
        THEN: New user count and averages are correct
        """
        # New user with onboarding complete
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "new-user-1",
                "app_name": "builder",
                "adoption": {
                    "is_new_user": True,
                    "onboarding_steps_completed": ["welcome", "tutorial", "completed"],
                },
                "retention": {
                    "return_visits": 1,
                    "days_active": 1,
                },
            },
        )

        # Returning user (no "completed" step - already finished onboarding long ago)
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "returning-user-1",
                "app_name": "builder",
                "adoption": {
                    "is_new_user": False,
                    "onboarding_steps_completed": [],  # Returning user, no onboarding
                },
                "retention": {
                    "return_visits": 10,
                    "days_active": 30,
                },
            },
        )

        # New user partial onboarding (no "completed" step)
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "new-user-2",
                "app_name": "builder",
                "adoption": {
                    "is_new_user": True,
                    "onboarding_steps_completed": ["welcome", "tutorial"],  # No "completed"
                },
                "retention": {
                    "return_visits": 2,
                    "days_active": 3,
                },
            },
        )

        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        data = response.json()

        assert data["new_users_count"] == 2
        # Implementation counts all users with "completed" (1) / new_users (2) = 0.5
        # Note: Only new-user-1 has "completed" in their steps
        assert data["onboarding_completion_rate"] == 0.5
        # (1 + 10 + 2) / 3 = 4.33...
        assert abs(data["avg_return_visits"] - 4.333) < 0.01
        # (1 + 30 + 3) / 3 = 11.33...
        assert abs(data["avg_days_active"] - 11.333) < 0.01

    def test_multi_app_isolation(self, client):
        """
        GIVEN: Metrics from different apps (builder, playground)
        WHEN: Filtered aggregation is requested
        THEN: Each app's metrics are isolated correctly
        """
        # Builder metrics
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "builder-session",
                "app_name": "builder",
                "happiness": {"nps_score": 10},
            },
        )

        # Playground metrics
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "playground-session",
                "app_name": "playground",
                "happiness": {"nps_score": 5},
            },
        )

        # Check builder aggregation
        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        builder_data = response.json()
        assert builder_data["nps_score_avg"] == 10.0

        # Check playground aggregation
        response = client.get("/api/v1/metrics/heart/aggregate?app=playground")
        playground_data = response.json()
        assert playground_data["nps_score_avg"] == 5.0

        # Check combined (no filter)
        response = client.get("/api/v1/metrics/heart/aggregate")
        combined = response.json()
        assert combined["nps_score_avg"] == 7.5  # (10 + 5) / 2


@pytest.mark.xdist_group(name="heart_metrics_integration")
class TestHeartMetricsValidation:
    """Integration tests for HEART metrics validation edge cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_empty_aggregation_returns_nulls(self, client):
        """
        GIVEN: No metrics have been submitted
        WHEN: Aggregation is requested
        THEN: All averages return null (no division by zero)
        """
        response = client.get("/api/v1/metrics/heart/aggregate")
        assert response.status_code == 200
        data = response.json()

        assert data["nps_score_avg"] is None
        assert data["satisfaction_avg"] is None
        assert data["task_success_rate"] is None
        assert data["avg_session_duration_ms"] is None
        assert data["onboarding_completion_rate"] is None
        assert data["avg_return_visits"] is None
        assert data["avg_days_active"] is None
        assert data["total_tasks_started"] == 0
        assert data["total_interactions"] == 0

    def test_partial_metrics_submission(self, client):
        """
        GIVEN: Metrics submission with only some fields
        WHEN: Aggregation is requested
        THEN: Only submitted fields contribute to aggregation
        """
        # Only happiness metrics
        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "partial-session",
                "app_name": "builder",
                "happiness": {"nps_score": 8},
            },
        )

        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        data = response.json()

        assert data["nps_score_avg"] == 8.0
        assert data["task_success_rate"] is None  # Not submitted
        assert data["avg_session_duration_ms"] is None  # Not submitted

    def test_feature_usage_top_10_limit(self, client):
        """
        GIVEN: Many different features used
        WHEN: Aggregation is requested
        THEN: Only top 10 features by usage are returned
        """
        features = {f"feature_{i}": i + 1 for i in range(15)}

        client.post(
            "/api/v1/metrics/heart",
            json={
                "session_id": "feature-heavy-session",
                "app_name": "builder",
                "engagement": {
                    "session_duration_ms": 1000,
                    "interaction_count": 100,
                    "feature_usage": features,
                },
            },
        )

        response = client.get("/api/v1/metrics/heart/aggregate?app=builder")
        data = response.json()

        # Should only have top 10 features
        assert len(data["top_features"]) == 10
        # Highest usage features should be present
        assert "feature_14" in data["top_features"]  # Usage: 15
        assert "feature_13" in data["top_features"]  # Usage: 14
        # Lowest usage features should be excluded
        assert "feature_0" not in data["top_features"]  # Usage: 1
