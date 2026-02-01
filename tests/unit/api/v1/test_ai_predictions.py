"""
AI Predictions Router Unit Tests

Tests for GET /api/v1/ai/predictions endpoint per TDD methodology.
Tests written FIRST before full implementation (RED phase).

The predictions endpoint provides AI-powered HEART metrics predictions
(churn risk, adoption forecasts, engagement decline).

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
"""

import gc
from typing import Any, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Mock authenticated user for testing."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def test_app(mock_user: dict[str, Any]) -> Generator[FastAPI, None, None]:
    """Create a test app with the AI router and mock authentication."""
    from mcp_server_langgraph.api.v1.ai import ai_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(ai_router, prefix="/api/v1/ai")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_ai_predictions")
class TestPredictionsEndpoint:
    """Tests for GET /api/v1/ai/predictions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_predictions_returns_200(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions
        WHEN GET request is made
        THEN response should be 200 OK with predictions array
        """
        response = client.get("/api/v1/ai/predictions")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert isinstance(data["predictions"], list)

    def test_get_predictions_empty_by_default(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions
        WHEN GET request is made without any predictions stored
        THEN response should return empty predictions array (stub behavior)
        """
        response = client.get("/api/v1/ai/predictions")

        assert response.status_code == 200
        data = response.json()
        assert data["predictions"] == []

    def test_get_predictions_with_session_id_filter(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions with session_id filter
        WHEN GET request is made
        THEN response should be 200 OK (filter applied, stub returns empty)
        """
        response = client.get("/api/v1/ai/predictions?session_id=test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data

    def test_get_predictions_with_type_filter(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions with type filter
        WHEN GET request is made
        THEN response should be 200 OK (filter applied)
        """
        response = client.get("/api/v1/ai/predictions?type=churn_risk")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data

    def test_get_predictions_with_min_confidence_filter(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions with min_confidence filter
        WHEN GET request is made
        THEN response should be 200 OK (filter applied)
        """
        response = client.get("/api/v1/ai/predictions?min_confidence=0.8")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data

    def test_get_predictions_with_all_filters(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions with all filters
        WHEN GET request is made
        THEN response should be 200 OK with all filters applied
        """
        response = client.get("/api/v1/ai/predictions?session_id=session-123&type=adoption_forecast&min_confidence=0.5")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data

    def test_get_predictions_requires_authentication(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/ai/predictions
        WHEN GET request is made without authentication
        THEN response should be 401 Unauthorized
        """
        # Remove the auth override
        test_app.dependency_overrides.clear()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/api/v1/ai/predictions")

        # Without auth override, should get 401 or error
        # The exact behavior depends on auth middleware configuration
        assert response.status_code in [401, 403, 500]


@pytest.mark.xdist_group(name="test_ai_predictions_models")
class TestPredictionModels:
    """Tests for prediction Pydantic models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prediction_type_enum_values(self) -> None:
        """
        GIVEN the PredictionType enum
        WHEN checking enum values
        THEN should have churn_risk, adoption_forecast, engagement_decline
        """
        from mcp_server_langgraph.api.v1.ai import PredictionType

        assert PredictionType.CHURN_RISK.value == "churn_risk"
        assert PredictionType.ADOPTION_FORECAST.value == "adoption_forecast"
        assert PredictionType.ENGAGEMENT_DECLINE.value == "engagement_decline"

    def test_prediction_factor_model(self) -> None:
        """
        GIVEN a PredictionFactor model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.ai import PredictionFactor

        factor = PredictionFactor(name="session_frequency", impact=0.3)
        assert factor.name == "session_frequency"
        assert factor.impact == 0.3

    def test_prediction_factor_impact_bounds(self) -> None:
        """
        GIVEN a PredictionFactor model
        WHEN creating with impact outside [-1, 1]
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.ai import PredictionFactor

        with pytest.raises(ValidationError):
            PredictionFactor(name="test", impact=1.5)

        with pytest.raises(ValidationError):
            PredictionFactor(name="test", impact=-1.5)

    def test_ai_prediction_model(self) -> None:
        """
        GIVEN an AIPrediction model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.ai import AIPrediction, PredictionType

        prediction = AIPrediction(
            id="pred-123",
            type=PredictionType.CHURN_RISK,
            metric="user_engagement",
            predicted_value=0.75,
            confidence=0.85,
            timeframe="7d",
            factors=[],
            created_at=1705123456789,
        )

        assert prediction.id == "pred-123"
        assert prediction.type == PredictionType.CHURN_RISK
        assert prediction.predicted_value == 0.75
        assert prediction.confidence == 0.85
        assert prediction.timeframe == "7d"

    def test_ai_prediction_value_bounds(self) -> None:
        """
        GIVEN an AIPrediction model
        WHEN creating with predicted_value or confidence outside [0, 1]
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.ai import AIPrediction, PredictionType

        with pytest.raises(ValidationError):
            AIPrediction(
                id="pred-123",
                type=PredictionType.CHURN_RISK,
                metric="test",
                predicted_value=1.5,  # Invalid: > 1
                confidence=0.5,
                timeframe="7d",
                factors=[],
                created_at=1705123456789,
            )

    def test_ai_prediction_timeframe_validation(self) -> None:
        """
        GIVEN an AIPrediction model
        WHEN creating with invalid timeframe
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.ai import AIPrediction, PredictionType

        with pytest.raises(ValidationError):
            AIPrediction(
                id="pred-123",
                type=PredictionType.CHURN_RISK,
                metric="test",
                predicted_value=0.5,
                confidence=0.5,
                timeframe="invalid",  # Invalid: must be 7d, 30d, or 90d
                factors=[],
                created_at=1705123456789,
            )

    def test_predictions_response_model(self) -> None:
        """
        GIVEN a PredictionsResponse model
        WHEN creating with valid predictions list
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.ai import (
            AIPrediction,
            PredictionsResponse,
            PredictionType,
        )

        prediction = AIPrediction(
            id="pred-123",
            type=PredictionType.ADOPTION_FORECAST,
            metric="feature_adoption",
            predicted_value=0.6,
            confidence=0.72,
            timeframe="30d",
            factors=[],
            created_at=1705123456789,
        )

        response = PredictionsResponse(predictions=[prediction])
        assert len(response.predictions) == 1
        assert response.predictions[0].id == "pred-123"
