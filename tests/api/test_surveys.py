"""
Tests for Surveys Endpoint.

TDD RED phase: These tests define expected behavior for SUS survey
collection and retrieval.

The endpoint should:
- Accept SUS survey submissions
- Calculate SUS scores
- Retrieve aggregated survey results
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
def surveys_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked surveys service."""
    from mcp_server_langgraph.api.v1.surveys import (
        router,
        set_surveys_service,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/surveys")

    # Override get_current_user to return authenticated user
    async def get_auth_user() -> dict[str, Any]:
        return _make_authenticated_user()

    app.dependency_overrides[get_current_user] = get_auth_user

    # Configure mock with return values to satisfy async-mock-config hook
    mock_service = AsyncMock()  # noqa: async-mock-config
    mock_service.submit_sus_survey.return_value = {"id": "survey-default", "sus_score": 68.0}
    mock_service.get_survey_results.return_value = {"total": 0, "average_score": 0.0}
    set_surveys_service(mock_service)

    yield app, mock_service

    # Cleanup
    set_surveys_service(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="surveys")
class TestSUSSurveyEndpoint:
    """Tests for /api/v1/surveys/sus endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sus_endpoint_exists(self, surveys_app: tuple) -> None:
        """
        GIVEN FastAPI app with surveys router
        WHEN checking routes
        THEN SUS endpoint exists.
        """
        app, _ = surveys_app

        routes = [route.path for route in app.routes]
        assert "/api/v1/surveys/sus" in routes

    def test_submit_sus_survey(self, surveys_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting SUS survey
        THEN survey is recorded with calculated score.
        """
        app, mock_service = surveys_app
        mock_service.submit_sus_survey.return_value = {
            "id": "survey-001",
            "sus_score": 72.5,
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/surveys/sus",
            json={
                "responses": [4, 2, 4, 1, 5, 2, 4, 1, 5, 2],  # 10 SUS questions
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "sus_score" in data
        mock_service.submit_sus_survey.assert_called_once()

    def test_sus_survey_requires_10_responses(self, surveys_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting SUS survey with wrong number of responses
        THEN validation error is returned.
        """
        app, mock_service = surveys_app

        client = TestClient(app)
        response = client.post(
            "/api/v1/surveys/sus",
            json={
                "responses": [4, 2, 4],  # Only 3 responses
            },
        )

        assert response.status_code == 422  # Validation error

    def test_sus_survey_validates_response_range(self, surveys_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN submitting SUS survey with out-of-range responses
        THEN validation error is returned.
        """
        app, mock_service = surveys_app

        client = TestClient(app)
        response = client.post(
            "/api/v1/surveys/sus",
            json={
                "responses": [4, 2, 4, 1, 6, 2, 4, 1, 5, 2],  # 6 is out of range
            },
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.api
@pytest.mark.xdist_group(name="surveys")
class TestSUSScoreCalculation:
    """Tests for SUS score calculation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_calculate_sus_score_perfect(self) -> None:
        """
        GIVEN perfect SUS responses (all 5s for odd, all 1s for even)
        WHEN calculating SUS score
        THEN score is 100.
        """
        from mcp_server_langgraph.api.v1.surveys import calculate_sus_score

        # Best case: strongly agree with positive, strongly disagree with negative
        responses = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]
        score = calculate_sus_score(responses)
        assert score == 100.0

    def test_calculate_sus_score_worst(self) -> None:
        """
        GIVEN worst SUS responses (all 1s for odd, all 5s for even)
        WHEN calculating SUS score
        THEN score is 0.
        """
        from mcp_server_langgraph.api.v1.surveys import calculate_sus_score

        # Worst case: strongly disagree with positive, strongly agree with negative
        responses = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]
        score = calculate_sus_score(responses)
        assert score == 0.0

    def test_calculate_sus_score_neutral(self) -> None:
        """
        GIVEN neutral SUS responses (all 3s)
        WHEN calculating SUS score
        THEN score is 50.
        """
        from mcp_server_langgraph.api.v1.surveys import calculate_sus_score

        responses = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
        score = calculate_sus_score(responses)
        assert score == 50.0


@pytest.mark.api
@pytest.mark.xdist_group(name="surveys")
class TestGetSUSSummary:
    """Tests for retrieving SUS survey summaries."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_sus_summary(self, surveys_app: tuple) -> None:
        """
        GIVEN authenticated user
        WHEN requesting SUS summary
        THEN aggregated results are returned.
        """
        app, mock_service = surveys_app
        mock_service.get_sus_summary.return_value = {
            "timeframe": "30d",
            "avg_score": 68.5,
            "response_count": 150,
            "score_distribution": {
                "excellent": 45,  # 80.3+
                "good": 60,  # 68-80.2
                "ok": 30,  # 51-67
                "poor": 15,  # <51
            },
        }

        client = TestClient(app)
        response = client.get("/api/v1/surveys/sus/summary?timeframe=30d")

        assert response.status_code == 200
        data = response.json()
        assert "avg_score" in data
        assert "response_count" in data
