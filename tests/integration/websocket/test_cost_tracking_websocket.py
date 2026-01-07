"""
Cost Tracking WebSocket Integration Tests.

Integration tests for /api/v1/ws/cost-tracking endpoint.
Tests the full WebSocket flow for cost tracking and budget monitoring.

Architecture:
- Uses Starlette TestClient for actual WebSocket connections
- Tests subscription (session/user), message broadcasting, and lifecycle events
- Validates authorization, message format, and push functionality
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from typing import Any, Generator

import jwt
import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from mcp_server_langgraph.websocket.handlers.cost_tracking import (
    CostTrackingHandler,
)
from mcp_server_langgraph.websocket.types import WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.cost_tracking,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-cost-tracking"


def _create_test_jwt(
    user_id: str = "user:alice",
    username: str = "alice",
    roles: list[str] | None = None,
    email: str = "alice@example.com",
    expires_in: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create a test JWT token for integration tests."""
    if roles is None:
        roles = ["user"]
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "jti": f"{username}_{int(now.timestamp() * 1000)}",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class MockCostService:
    """Mock cost service for integration tests."""

    def __init__(self) -> None:
        self.session_costs: dict[str, dict[str, Any]] = {}
        self.user_budgets: dict[str, dict[str, Any]] = {}

    async def get_session_cost(self, session_id: str) -> dict[str, Any]:
        """Get current cost for a session."""
        return self.session_costs.get(
            session_id,
            {
                "session_id": session_id,
                "total_cost": 0.0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "model_breakdown": {},
            },
        )

    async def get_user_budget(self, user_id: str) -> dict[str, Any]:
        """Get budget status for a user."""
        return self.user_budgets.get(
            user_id,
            {
                "user_id": user_id,
                "budget_limit": 100.0,
                "current_usage": 0.0,
                "remaining": 100.0,
                "percentage_used": 0.0,
            },
        )


@pytest.fixture
def mock_cost_service() -> MockCostService:
    """Create a mock cost service with test data."""
    service = MockCostService()
    service.session_costs = {
        "session-123": {
            "session_id": "session-123",
            "total_cost": 0.0523,
            "total_tokens": 1500,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "model_breakdown": {
                "gpt-4": {"cost": 0.0423, "tokens": 1000},
                "gpt-3.5-turbo": {"cost": 0.01, "tokens": 500},
            },
        }
    }
    service.user_budgets = {
        "user:alice": {
            "user_id": "user:alice",
            "budget_limit": 50.0,
            "current_usage": 12.50,
            "remaining": 37.50,
            "percentage_used": 25.0,
        }
    }
    return service


@pytest.fixture
def test_app(mock_cost_service: MockCostService) -> FastAPI:
    """Create a test FastAPI app with cost tracking endpoint."""
    app = FastAPI()

    @app.websocket("/api/v1/ws/cost-tracking")
    async def cost_tracking_endpoint(websocket: WebSocket) -> None:
        handler = CostTrackingHandler(
            config=WebSocketConfig(
                endpoint_name="cost-tracking-test",
                require_auth=False,  # Disable auth for testing
                rate_limit_per_minute=600,
                message_timeout=30,
            ),
            cost_service=mock_cost_service,
        )
        await handler.run(websocket)

    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client for the app."""
    with TestClient(test_app) as client:
        yield client


@pytest.mark.xdist_group(name="cost_tracking_websocket")
class TestCostTrackingWebSocketConnection:
    """Test WebSocket connection lifecycle for cost tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connection_succeeds(self, test_client: TestClient) -> None:
        """Test that WebSocket connection can be established."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            # Connection successful
            assert ws is not None

    def test_websocket_subscribe_session_returns_cost(self, test_client: TestClient) -> None:
        """Test that subscribing to a session returns current cost."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "test-1",
                    "payload": {"session_id": "session-123"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "session_total"
            assert response["id"] == "test-1"
            assert response["payload"]["session_id"] == "session-123"
            assert response["payload"]["total_cost"] == 0.0523
            assert response["payload"]["total_tokens"] == 1500

    def test_websocket_subscribe_session_unknown_returns_zero(self, test_client: TestClient) -> None:
        """Test that subscribing to unknown session returns zero cost."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "test-2",
                    "payload": {"session_id": "unknown-session"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "session_total"
            assert response["payload"]["session_id"] == "unknown-session"
            assert response["payload"]["total_cost"] == 0.0

    def test_websocket_subscribe_session_missing_id_returns_error(self, test_client: TestClient) -> None:
        """Test that subscribe_session without session_id returns error."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "test-3",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-3"
            assert response["payload"]["code"] == "missing_session_id"


@pytest.mark.xdist_group(name="cost_tracking_websocket")
class TestCostTrackingUserBudget:
    """Test user budget subscription and monitoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_subscribe_user_returns_budget(self, test_client: TestClient) -> None:
        """Test that subscribing to user budget returns budget status."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_user",
                    "id": "test-4",
                    "payload": {"user_id": "user:alice"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "user_budget"
            assert response["id"] == "test-4"
            assert response["payload"]["user_id"] == "user:alice"
            assert response["payload"]["budget_limit"] == 50.0
            assert response["payload"]["current_usage"] == 12.50
            assert response["payload"]["percentage_used"] == 25.0

    def test_websocket_subscribe_user_unknown_returns_default(self, test_client: TestClient) -> None:
        """Test that subscribing to unknown user returns default budget."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_user",
                    "id": "test-5",
                    "payload": {"user_id": "user:unknown"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "user_budget"
            assert response["payload"]["user_id"] == "user:unknown"
            assert response["payload"]["budget_limit"] == 100.0
            assert response["payload"]["current_usage"] == 0.0

    def test_websocket_subscribe_user_missing_id_returns_error(self, test_client: TestClient) -> None:
        """Test that subscribe_user without user_id returns error."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_user",
                    "id": "test-6",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-6"
            assert response["payload"]["code"] == "missing_user_id"


@pytest.mark.xdist_group(name="cost_tracking_websocket")
class TestCostTrackingUnsubscribe:
    """Test unsubscription functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_unsubscribe_session(self, test_client: TestClient) -> None:
        """Test unsubscribing from session cost updates."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            # First subscribe
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "test-7",
                    "payload": {"session_id": "session-123"},
                }
            )
            ws.receive_json()  # Consume session_total response

            # Then unsubscribe
            ws.send_json(
                {
                    "type": "unsubscribe",
                    "id": "test-8",
                    "payload": {"session_id": "session-123"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert response["id"] == "test-8"
            assert response["payload"]["session_id"] == "session-123"

    def test_websocket_unsubscribe_user(self, test_client: TestClient) -> None:
        """Test unsubscribing from user budget updates."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            # First subscribe
            ws.send_json(
                {
                    "type": "subscribe_user",
                    "id": "test-9",
                    "payload": {"user_id": "user:alice"},
                }
            )
            ws.receive_json()  # Consume user_budget response

            # Then unsubscribe
            ws.send_json(
                {
                    "type": "unsubscribe",
                    "id": "test-10",
                    "payload": {"user_id": "user:alice"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert response["id"] == "test-10"
            assert response["payload"]["user_id"] == "user:alice"


@pytest.mark.xdist_group(name="cost_tracking_websocket")
class TestCostTrackingErrorHandling:
    """Test error handling for cost tracking WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_unknown_message_type_returns_error(self, test_client: TestClient) -> None:
        """Test that unknown message type returns error."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "invalid_type",
                    "id": "test-11",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-11"
            assert response["payload"]["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="cost_tracking_websocket")
class TestCostTrackingMessageFormats:
    """Test message format validation for cost tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_total_message_format(self, test_client: TestClient) -> None:
        """Test session_total message format matches frontend expectations."""
        # Frontend hook (useCostTracking) expects:
        # {
        #   type: "session_total",
        #   payload: {
        #     session_id: string,
        #     total_cost: number,
        #     total_tokens: number,
        #     prompt_tokens: number,
        #     completion_tokens: number,
        #     model_breakdown?: Record<string, {cost: number, tokens: number}>
        #   }
        # }
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "format-test",
                    "payload": {"session_id": "session-123"},
                }
            )
            response = ws.receive_json()

            # Verify structure
            assert "type" in response
            assert "payload" in response
            assert "session_id" in response["payload"]
            assert "total_cost" in response["payload"]
            assert "total_tokens" in response["payload"]
            assert "model_breakdown" in response["payload"]

    def test_user_budget_message_format(self, test_client: TestClient) -> None:
        """Test user_budget message format matches frontend expectations."""
        # Frontend hook (useCostTracking) expects:
        # {
        #   type: "user_budget",
        #   payload: {
        #     user_id: string,
        #     budget_limit: number,
        #     current_usage: number,
        #     remaining: number,
        #     percentage_used: number
        #   }
        # }
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_user",
                    "id": "format-test-2",
                    "payload": {"user_id": "user:alice"},
                }
            )
            response = ws.receive_json()

            # Verify structure
            assert "type" in response
            assert "payload" in response
            assert "user_id" in response["payload"]
            assert "budget_limit" in response["payload"]
            assert "current_usage" in response["payload"]
            assert "remaining" in response["payload"]
            assert "percentage_used" in response["payload"]

    def test_unsubscribed_message_format(self, test_client: TestClient) -> None:
        """Test unsubscribed message format."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "unsubscribe",
                    "id": "format-test-3",
                    "payload": {"session_id": "session-123"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert "payload" in response
            assert "session_id" in response["payload"]

    def test_error_message_format(self, test_client: TestClient) -> None:
        """Test error message format."""
        with test_client.websocket_connect("/api/v1/ws/cost-tracking?v=1.0.0") as ws:
            ws.send_json(
                {
                    "type": "subscribe_session",
                    "id": "format-test-4",
                    "payload": {},  # Missing session_id
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert "payload" in response
            assert "code" in response["payload"]
            assert "message" in response["payload"]
