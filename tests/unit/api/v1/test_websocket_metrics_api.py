"""
WebSocket Metrics API Tests.

TDD tests for the WebSocket metrics submission endpoint.
Frontend clients POST reconnection metrics to this endpoint,
which are then recorded in Prometheus.
"""

import gc
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="websocket_metrics_api")
class TestWebSocketMetricsAPI:
    """Test WebSocket metrics submission API endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_post_websocket_metrics_returns_200(self) -> None:
        """POST /api/v1/websocket/metrics should return 200 on valid payload."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "notifications",
            "total_attempts": 10,
            "total_reconnections": 8,
            "consecutive_failures": 0,
            "success_rate": 80.0,
            "failures_by_reason": {"network_error": 1, "token_expired": 1},
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_post_websocket_metrics_validates_endpoint_id(self) -> None:
        """Endpoint should reject empty endpoint_id."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "",  # Empty - should fail
            "total_attempts": 10,
            "total_reconnections": 8,
            "consecutive_failures": 0,
            "success_rate": 80.0,
            "failures_by_reason": {},
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422  # Validation error

    def test_post_websocket_metrics_validates_success_rate_bounds(self) -> None:
        """Success rate must be between 0 and 100."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "alerts",
            "total_attempts": 10,
            "total_reconnections": 8,
            "consecutive_failures": 0,
            "success_rate": 150.0,  # > 100% - should fail
            "failures_by_reason": {},
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422

    def test_post_websocket_metrics_validates_non_negative_counts(self) -> None:
        """Counts must be non-negative."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "traces",
            "total_attempts": -1,  # Negative - should fail
            "total_reconnections": 8,
            "consecutive_failures": 0,
            "success_rate": 80.0,
            "failures_by_reason": {},
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422

    def test_post_websocket_metrics_calls_prometheus_exporter(self) -> None:
        """Endpoint should call process_metrics_payload."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "devtools",
            "total_attempts": 5,
            "total_reconnections": 5,
            "consecutive_failures": 0,
            "success_rate": 100.0,
            "failures_by_reason": {},
        }

        with patch("mcp_server_langgraph.api.v1.websocket_metrics.process_metrics_payload") as mock_process:
            response = client.post("/api/v1/websocket/metrics", json=payload)

            assert response.status_code == 200
            mock_process.assert_called_once()

    def test_post_batch_metrics_returns_200(self) -> None:
        """POST /api/v1/websocket/metrics/batch should accept multiple endpoints."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoints": [
                {
                    "endpoint_id": "notifications",
                    "total_attempts": 10,
                    "total_reconnections": 10,
                    "consecutive_failures": 0,
                    "success_rate": 100.0,
                    "failures_by_reason": {},
                },
                {
                    "endpoint_id": "alerts",
                    "total_attempts": 5,
                    "total_reconnections": 4,
                    "consecutive_failures": 1,
                    "success_rate": 80.0,
                    "failures_by_reason": {"network_error": 1},
                },
            ]
        }

        response = client.post("/api/v1/websocket/metrics/batch", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert response.json()["processed"] == 2

    def test_post_batch_metrics_processes_all_endpoints(self) -> None:
        """Batch endpoint should call process_batch_metrics."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoints": [
                {
                    "endpoint_id": "ep1",
                    "total_attempts": 1,
                    "total_reconnections": 1,
                    "consecutive_failures": 0,
                    "success_rate": 100.0,
                    "failures_by_reason": {},
                },
                {
                    "endpoint_id": "ep2",
                    "total_attempts": 2,
                    "total_reconnections": 2,
                    "consecutive_failures": 0,
                    "success_rate": 100.0,
                    "failures_by_reason": {},
                },
            ]
        }

        with patch("mcp_server_langgraph.api.v1.websocket_metrics.process_batch_metrics") as mock_batch:
            response = client.post("/api/v1/websocket/metrics/batch", json=payload)

            assert response.status_code == 200
            mock_batch.assert_called_once()

    def test_post_metrics_with_optional_duration(self) -> None:
        """Payload may include optional avg_reconnection_duration_ms."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "mcp_tasks",
            "total_attempts": 10,
            "total_reconnections": 9,
            "consecutive_failures": 0,
            "success_rate": 90.0,
            "failures_by_reason": {"timeout": 1},
            "avg_reconnection_duration_ms": 250.5,
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 200

    def test_graceful_handling_when_prometheus_unavailable(self) -> None:
        """Endpoint should still return 200 if Prometheus is unavailable."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "test",
            "total_attempts": 1,
            "total_reconnections": 1,
            "consecutive_failures": 0,
            "success_rate": 100.0,
            "failures_by_reason": {},
        }

        # Mock Prometheus being unavailable
        with patch(
            "mcp_server_langgraph.api.v1.websocket_metrics.process_metrics_payload",
            side_effect=Exception("Prometheus unavailable"),
        ):
            response = client.post("/api/v1/websocket/metrics", json=payload)

            # Should still return 200 (fire-and-forget pattern)
            assert response.status_code == 200
            assert response.json()["status"] == "accepted"
