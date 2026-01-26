"""
Tests for Feedback Endpoints.

TDD RED phase: These tests define expected behavior for user feedback
collection including hallucination reports.

The endpoint should:
- Accept hallucination reports with message context
- Accept general feedback (thumbs up/down)
- Retrieve feedback aggregates for analysis
- Require authentication
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


def _make_authenticated_user() -> dict[str, Any]:
    """Create authenticated user for access."""
    return {
        "user_id": "user-001",
        "username": "testuser",
        "email": "user@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def feedback_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked feedback service."""
    from mcp_server_langgraph.api.v1.feedback import (
        router,
        set_feedback_service,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/feedback")

    # Override get_current_user to return authenticated user
    async def get_auth_user() -> dict[str, Any]:
        return _make_authenticated_user()

    app.dependency_overrides[get_current_user] = get_auth_user

    # Configure mock with return values to satisfy async-mock-config hook
    mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
    mock_service.submit_hallucination_report.return_value = {"id": "report-default", "status": "received"}
    mock_service.submit_message_rating.return_value = {"id": "rating-default"}
    mock_service.get_feedback_summary.return_value = {"total": 0}
    set_feedback_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_feedback_service(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="feedback")
class TestHallucinationReportEndpoint:
    """Tests for /api/v1/feedback/hallucination endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hallucination_endpoint_exists(self, feedback_app: tuple) -> None:
        """
        GIVEN FastAPI app with feedback router
        WHEN checking routes
        THEN hallucination endpoint exists.
        """
        app, _ = feedback_app

        routes = [route.path for route in app.routes]
        assert "/api/v1/feedback/hallucination" in routes

    def test_submit_hallucination_report(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN reporting a hallucination
        THEN report is recorded.
        """
        app, mock_service = feedback_app
        mock_service.submit_hallucination_report.return_value = {
            "id": "report-001",
            "status": "received",
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/feedback/hallucination",
            json={
                "message_id": "msg-123",
                "session_id": "sess-456",
                "category": "factual_error",
                "description": "The AI claimed the Earth is flat.",
                "severity": "high",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "received"
        mock_service.submit_hallucination_report.assert_called_once()

    def test_hallucination_report_requires_message_id(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting hallucination report without message_id
        THEN validation error is returned.
        """
        app, mock_service = feedback_app

        client = TestClient(app)
        response = client.post(
            "/api/v1/feedback/hallucination",
            json={
                "category": "factual_error",
                "description": "Missing message ID",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_submit_hallucination_with_valid_category_is_accepted(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting with valid category
        THEN report is accepted.
        """
        app, mock_service = feedback_app
        mock_service.submit_hallucination_report.return_value = {
            "id": "report-002",
            "status": "received",
        }

        client = TestClient(app)

        # Test each valid category
        categories = ["factual_error", "outdated_info", "made_up_source", "other"]
        for category in categories:
            response = client.post(
                "/api/v1/feedback/hallucination",
                json={
                    "message_id": "msg-123",
                    "session_id": "sess-456",
                    "category": category,
                    "description": f"Test {category}",
                },
            )
            assert response.status_code == 201, f"Failed for category: {category}"


@pytest.mark.api
@pytest.mark.xdist_group(name="feedback")
class TestMessageFeedbackEndpoint:
    """Tests for /api/v1/feedback/message endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_feedback_endpoint_exists(self, feedback_app: tuple) -> None:
        """
        GIVEN FastAPI app with feedback router
        WHEN checking routes
        THEN message feedback endpoint exists.
        """
        app, _ = feedback_app

        routes = [route.path for route in app.routes]
        assert "/api/v1/feedback/message" in routes

    def test_submit_thumbs_up(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting thumbs up feedback
        THEN feedback is recorded.
        """
        app, mock_service = feedback_app
        mock_service.submit_message_feedback.return_value = {
            "id": "feedback-001",
            "rating": "positive",
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/feedback/message",
            json={
                "message_id": "msg-123",
                "session_id": "sess-456",
                "rating": "positive",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "positive"
        mock_service.submit_message_feedback.assert_called_once()

    def test_submit_thumbs_down_with_reason(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting thumbs down with reason
        THEN feedback with reason is recorded.
        """
        app, mock_service = feedback_app
        mock_service.submit_message_feedback.return_value = {
            "id": "feedback-002",
            "rating": "negative",
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/feedback/message",
            json={
                "message_id": "msg-123",
                "session_id": "sess-456",
                "rating": "negative",
                "reason": "Response was unhelpful",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "negative"


@pytest.mark.api
@pytest.mark.xdist_group(name="feedback")
class TestFeedbackSummary:
    """Tests for retrieving feedback summaries."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_feedback_summary(self, feedback_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN requesting feedback summary
        THEN aggregated results are returned.
        """
        app, mock_service = feedback_app
        mock_service.get_feedback_summary.return_value = {
            "timeframe": "7d",
            "total_feedback": 150,
            "positive_count": 120,
            "negative_count": 30,
            "positive_rate": 0.80,
            "hallucination_reports": 5,
            "hallucination_categories": {
                "factual_error": 2,
                "outdated_info": 1,
                "made_up_source": 1,
                "other": 1,
            },
        }

        client = TestClient(app)
        response = client.get("/api/v1/feedback/summary?timeframe=7d")

        assert response.status_code == 200
        data = response.json()
        assert "positive_rate" in data
        assert "hallucination_reports" in data
        assert data["positive_rate"] == 0.80
