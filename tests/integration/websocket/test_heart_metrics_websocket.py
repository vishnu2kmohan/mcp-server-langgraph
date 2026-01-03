"""
HEART Metrics WebSocket Integration Tests.

Integration tests for /api/v1/ws/heart-metrics endpoint.
Tests the full WebSocket flow for HEART metrics streaming.

HEART Framework Dimensions:
- Happiness: User satisfaction (NPS, CSAT)
- Engagement: User activity levels
- Adoption: Feature adoption rates
- Retention: User retention metrics
- Task Success: Task completion rates

Architecture:
- Uses Starlette TestClient for actual WebSocket connections
- Tests time range configuration, dimension subscriptions, and lifecycle events
- Validates message format and error handling
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from typing import Any, Generator

import jwt
import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from mcp_server_langgraph.websocket.handlers.heart_metrics import (
    HEART_DIMENSIONS,
    VALID_TIME_RANGES,
    HeartMetricsHandler,
    HeartMetricsServiceProtocol,
)
from mcp_server_langgraph.websocket.types import WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.heart_metrics,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-heart-metrics"


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


class MockHeartMetricsService:
    """Mock HEART metrics service for integration tests."""

    def __init__(self) -> None:
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.dimension_metrics: dict[str, dict[str, Any]] = {}
        self._setup_test_data()

    def _setup_test_data(self) -> None:
        """Set up test data for all time ranges."""
        base_snapshot = {
            "happiness": {"score": 78.5, "trend": "up", "change": 2.3},
            "engagement": {"rate": 65.2, "trend": "stable", "change": 0.1},
            "adoption": {"rate": 45.8, "trend": "up", "change": 5.7},
            "retention": {"rate": 82.1, "trend": "down", "change": -1.2},
            "task_success": {"rate": 91.3, "trend": "up", "change": 3.4},
        }
        for time_range in VALID_TIME_RANGES:
            self.snapshots[time_range] = {
                "time_range": time_range,
                "timestamp": datetime.now(UTC).isoformat(),
                **base_snapshot,
            }

        self.dimension_metrics = {
            "happiness": {
                "dimension": "happiness",
                "score": 78.5,
                "trend": "up",
                "change": 2.3,
                "details": {
                    "nps": 42,
                    "csat": 4.2,
                    "positive_feedback_ratio": 0.73,
                },
            },
            "engagement": {
                "dimension": "engagement",
                "rate": 65.2,
                "trend": "stable",
                "change": 0.1,
                "details": {
                    "daily_active_users": 1250,
                    "session_duration_avg": 12.5,
                    "actions_per_session": 8.3,
                },
            },
            "adoption": {
                "dimension": "adoption",
                "rate": 45.8,
                "trend": "up",
                "change": 5.7,
                "details": {
                    "new_users_this_week": 150,
                    "feature_adoption_rate": 0.45,
                    "onboarding_completion": 0.82,
                },
            },
            "retention": {
                "dimension": "retention",
                "rate": 82.1,
                "trend": "down",
                "change": -1.2,
                "details": {
                    "day_1_retention": 0.85,
                    "day_7_retention": 0.72,
                    "day_30_retention": 0.55,
                },
            },
            "task_success": {
                "dimension": "task_success",
                "rate": 91.3,
                "trend": "up",
                "change": 3.4,
                "details": {
                    "completion_rate": 0.91,
                    "avg_time_to_complete": 45.2,
                    "error_rate": 0.03,
                },
            },
        }

    async def get_current_snapshot(self, time_range: str = "24h") -> dict[str, Any]:
        """Get current HEART metrics snapshot."""
        return self.snapshots.get(
            time_range,
            {"time_range": time_range, "error": "No data available"},
        )

    async def get_dimension_metrics(
        self, dimension: str, time_range: str = "24h"
    ) -> dict[str, Any]:
        """Get metrics for a specific dimension."""
        return self.dimension_metrics.get(
            dimension,
            {"dimension": dimension, "error": "Unknown dimension"},
        )


@pytest.fixture
def mock_metrics_service() -> MockHeartMetricsService:
    """Create a mock HEART metrics service with test data."""
    return MockHeartMetricsService()


@pytest.fixture
def test_app(mock_metrics_service: MockHeartMetricsService) -> FastAPI:
    """Create a test FastAPI app with HEART metrics endpoint."""
    app = FastAPI()

    @app.websocket("/api/v1/ws/heart-metrics")
    async def heart_metrics_endpoint(websocket: WebSocket) -> None:
        handler = HeartMetricsHandler(
            config=WebSocketConfig(
                endpoint_name="heart-metrics-test",
                require_auth=False,  # Disable auth for testing
                rate_limit_per_minute=600,
                message_timeout=30,
            ),
            metrics_service=mock_metrics_service,
        )
        await handler.run(websocket)

    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client for the app."""
    with TestClient(test_app) as client:
        yield client


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsWebSocketConnection:
    """Test WebSocket connection lifecycle for HEART metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connection_succeeds(self, test_client: TestClient) -> None:
        """Test that WebSocket connection can be established."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            # Connection successful, should receive initial snapshot
            response = ws.receive_json()
            assert response["type"] == "metrics_snapshot"

    def test_websocket_receives_initial_snapshot_on_connect(
        self, test_client: TestClient
    ) -> None:
        """Test that client receives metrics snapshot on connect."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            response = ws.receive_json()

            assert response["type"] == "metrics_snapshot"
            assert "metrics" in response
            assert "time_range" in response
            assert response["time_range"] == "24h"  # Default

            # Verify all HEART dimensions are present
            metrics = response["metrics"]
            assert "happiness" in metrics
            assert "engagement" in metrics
            assert "adoption" in metrics
            assert "retention" in metrics
            assert "task_success" in metrics


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsTimeRange:
    """Test time range configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_time_range_returns_new_snapshot(
        self, test_client: TestClient
    ) -> None:
        """Test that setting time range returns new snapshot."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "set_time_range",
                "id": "test-1",
                "payload": {"time_range": "7d"},
            })
            response = ws.receive_json()

            assert response["type"] == "metrics_snapshot"
            assert response["id"] == "test-1"
            assert response["payload"]["time_range"] == "7d"
            assert "metrics" in response["payload"]

    def test_set_invalid_time_range_returns_error(
        self, test_client: TestClient
    ) -> None:
        """Test that invalid time range returns error."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "set_time_range",
                "id": "test-2",
                "payload": {"time_range": "invalid"},
            })
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-2"
            assert response["payload"]["code"] == "invalid_time_range"

    def test_all_valid_time_ranges_work(self, test_client: TestClient) -> None:
        """Test that all valid time ranges are accepted."""
        for time_range in VALID_TIME_RANGES:
            with test_client.websocket_connect(
                "/api/v1/ws/heart-metrics?v=1.0.0"
            ) as ws:
                ws.receive_json()  # Consume initial snapshot

                ws.send_json({
                    "type": "set_time_range",
                    "id": f"test-{time_range}",
                    "payload": {"time_range": time_range},
                })
                response = ws.receive_json()

                assert response["type"] == "metrics_snapshot", (
                    f"Failed for time_range={time_range}"
                )
                assert response["payload"]["time_range"] == time_range


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsDimensionSubscription:
    """Test dimension subscription functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_dimension_returns_metrics(
        self, test_client: TestClient
    ) -> None:
        """Test that subscribing to a dimension returns dimension metrics."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "subscribe_dimension",
                "id": "test-3",
                "payload": {"dimension": "happiness"},
            })
            response = ws.receive_json()

            assert response["type"] == "dimension_update"
            assert response["id"] == "test-3"
            assert response["payload"]["dimension"] == "happiness"
            assert "metrics" in response["payload"]
            assert response["payload"]["metrics"]["score"] == 78.5

    def test_subscribe_all_valid_dimensions(self, test_client: TestClient) -> None:
        """Test that all valid HEART dimensions can be subscribed."""
        for dimension in HEART_DIMENSIONS:
            with test_client.websocket_connect(
                "/api/v1/ws/heart-metrics?v=1.0.0"
            ) as ws:
                ws.receive_json()  # Consume initial snapshot

                ws.send_json({
                    "type": "subscribe_dimension",
                    "id": f"test-{dimension}",
                    "payload": {"dimension": dimension},
                })
                response = ws.receive_json()

                assert response["type"] == "dimension_update", (
                    f"Failed for dimension={dimension}"
                )
                assert response["payload"]["dimension"] == dimension

    def test_subscribe_invalid_dimension_returns_error(
        self, test_client: TestClient
    ) -> None:
        """Test that invalid dimension returns error."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "subscribe_dimension",
                "id": "test-4",
                "payload": {"dimension": "invalid_dimension"},
            })
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-4"
            assert response["payload"]["code"] == "invalid_dimension"

    def test_subscribe_missing_dimension_returns_error(
        self, test_client: TestClient
    ) -> None:
        """Test that missing dimension returns error."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "subscribe_dimension",
                "id": "test-5",
                "payload": {},
            })
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-5"
            assert response["payload"]["code"] == "missing_dimension"


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsUnsubscribe:
    """Test unsubscription functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unsubscribe_dimension(self, test_client: TestClient) -> None:
        """Test unsubscribing from a dimension."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            # First subscribe
            ws.send_json({
                "type": "subscribe_dimension",
                "id": "test-6",
                "payload": {"dimension": "engagement"},
            })
            ws.receive_json()  # Consume dimension_update

            # Then unsubscribe
            ws.send_json({
                "type": "unsubscribe_dimension",
                "id": "test-7",
                "payload": {"dimension": "engagement"},
            })
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert response["id"] == "test-7"
            assert response["payload"]["dimension"] == "engagement"


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsErrorHandling:
    """Test error handling for HEART metrics WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unknown_message_type_returns_error(
        self, test_client: TestClient
    ) -> None:
        """Test that unknown message type returns error."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "invalid_type",
                "id": "test-8",
                "payload": {},
            })
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-8"
            assert response["payload"]["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsMessageFormats:
    """Test message format validation for HEART metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_snapshot_message_format(self, test_client: TestClient) -> None:
        """Test metrics_snapshot message format matches frontend expectations."""
        # Frontend hook (useHeartDashboard) expects:
        # {
        #   type: "metrics_snapshot",
        #   metrics: {
        #     happiness: { score, trend, change },
        #     engagement: { rate, trend, change },
        #     adoption: { rate, trend, change },
        #     retention: { rate, trend, change },
        #     task_success: { rate, trend, change }
        #   },
        #   time_range: string
        # }
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            response = ws.receive_json()

            # Verify structure
            assert response["type"] == "metrics_snapshot"
            assert "metrics" in response
            assert "time_range" in response

            # Verify happiness dimension structure
            assert "happiness" in response["metrics"]
            happiness = response["metrics"]["happiness"]
            assert "score" in happiness
            assert "trend" in happiness
            assert "change" in happiness

    def test_dimension_update_message_format(self, test_client: TestClient) -> None:
        """Test dimension_update message format matches frontend expectations."""
        # Frontend expects:
        # {
        #   type: "dimension_update",
        #   payload: {
        #     dimension: string,
        #     metrics: { ... dimension-specific data }
        #   }
        # }
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "subscribe_dimension",
                "id": "format-test",
                "payload": {"dimension": "task_success"},
            })
            response = ws.receive_json()

            # Verify structure
            assert response["type"] == "dimension_update"
            assert "payload" in response
            assert "dimension" in response["payload"]
            assert "metrics" in response["payload"]
            assert response["payload"]["dimension"] == "task_success"

    def test_error_message_format(self, test_client: TestClient) -> None:
        """Test error message format."""
        with test_client.websocket_connect("/api/v1/ws/heart-metrics?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial snapshot

            ws.send_json({
                "type": "subscribe_dimension",
                "id": "format-test-2",
                "payload": {},  # Missing dimension
            })
            response = ws.receive_json()

            assert response["type"] == "error"
            assert "payload" in response
            assert "code" in response["payload"]
            assert "message" in response["payload"]


@pytest.mark.xdist_group(name="heart_metrics_websocket")
class TestHeartMetricsConstants:
    """Test HEART metrics constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_heart_dimensions_includes_all_five(self) -> None:
        """Test that HEART_DIMENSIONS includes all 5 dimensions."""
        expected = {"happiness", "engagement", "adoption", "retention", "task_success"}
        assert HEART_DIMENSIONS == expected

    def test_valid_time_ranges_includes_common_ranges(self) -> None:
        """Test that VALID_TIME_RANGES includes common time ranges."""
        expected = {"1h", "6h", "24h", "7d", "30d", "90d"}
        assert VALID_TIME_RANGES == expected
