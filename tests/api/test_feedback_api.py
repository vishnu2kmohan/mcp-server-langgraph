"""
Tests for Feedback API Endpoints

TDD tests for NPS/CSAT feedback submission.
Tests cover:
- Submit feedback with NPS score
- Submit feedback with CSAT rating
- Submit feedback with both
- Submit feedback with comment
- Validation errors
"""

import gc

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app


pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def feedback_with_nps():
    """Sample feedback with NPS score."""
    return {
        "nps_score": 9,
    }


@pytest.fixture
def feedback_with_csat():
    """Sample feedback with CSAT rating."""
    return {
        "csat_rating": 5,
    }


@pytest.fixture
def full_feedback():
    """Complete feedback payload."""
    return {
        "nps_score": 8,
        "csat_rating": 4,
        "comment": "Great product!",
    }


@pytest.mark.xdist_group(name="testfeedbacksubmission")
class TestFeedbackSubmission:
    """Tests for POST /api/v1/metrics/feedback."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_submit_feedback_with_nps_success(self, client, feedback_with_nps):
        """Should successfully submit feedback with NPS score."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json=feedback_with_nps,
            headers={"Authorization": "Bearer mock-token"},
        )

        # 201 Created for new feedback resource
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data
        assert "received_at" in data

    def test_submit_feedback_with_csat_success(self, client, feedback_with_csat):
        """Should successfully submit feedback with CSAT rating."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json=feedback_with_csat,
            headers={"Authorization": "Bearer mock-token"},
        )

        # 201 Created for new feedback resource
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_submit_feedback_complete(self, client, full_feedback):
        """Should successfully submit complete feedback."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json=full_feedback,
            headers={"Authorization": "Bearer mock-token"},
        )

        # 201 Created for new feedback resource
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_submit_feedback_empty_rejected(self, client):
        """Should reject empty feedback submission."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json={},
            headers={"Authorization": "Bearer mock-token"},
        )

        # Either validation error (422) or business logic error (400)
        assert response.status_code in [400, 422]

    def test_submit_feedback_invalid_nps_score(self, client):
        """Should reject NPS score outside 0-10 range."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json={"nps_score": 15},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422

    def test_submit_feedback_invalid_csat_rating(self, client):
        """Should reject CSAT rating outside 1-5 range."""
        response = client.post(
            "/api/v1/metrics/feedback",
            json={"csat_rating": 10},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422


@pytest.mark.xdist_group(name="testfeedbackendpointexists")
class TestFeedbackEndpointExists:
    """Tests to verify feedback endpoint is registered."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feedback_endpoint_exists(self, client):
        """Should have feedback endpoint registered."""
        response = client.options("/api/v1/metrics/feedback")
        assert response.status_code != 404
