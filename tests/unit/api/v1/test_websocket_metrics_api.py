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
            "reconnect_count": 8,
            "total_connect_time_ms": 1500.0,
            "error_count": 2,
            "messages_sent": 50,
            "messages_received": 100,
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
            "endpoint_id": "",  # Empty - should fail validation
            "reconnect_count": 0,
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422  # Validation error

    def test_post_websocket_metrics_validates_non_negative_reconnect_count(self) -> None:
        """reconnect_count must be non-negative."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "alerts",
            "reconnect_count": -1,  # Negative - should fail
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422

    def test_post_websocket_metrics_validates_non_negative_error_count(self) -> None:
        """error_count must be non-negative."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "traces",
            "error_count": -5,  # Negative - should fail
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
            "reconnect_count": 5,
            "error_count": 0,
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
                    "reconnect_count": 10,
                    "error_count": 0,
                },
                {
                    "endpoint_id": "alerts",
                    "reconnect_count": 4,
                    "error_count": 1,
                    "last_disconnect_reason": "network_error",
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
                    "reconnect_count": 1,
                },
                {
                    "endpoint_id": "ep2",
                    "reconnect_count": 2,
                },
            ]
        }

        with patch("mcp_server_langgraph.api.v1.websocket_metrics.process_batch_metrics") as mock_batch:
            response = client.post("/api/v1/websocket/metrics/batch", json=payload)

            assert response.status_code == 200
            mock_batch.assert_called_once()

    def test_post_metrics_with_optional_fields(self) -> None:
        """Payload may include optional total_connect_time_ms and last_disconnect_reason."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "mcp_tasks",
            "reconnect_count": 9,
            "total_connect_time_ms": 2500.0,
            "last_disconnect_reason": "timeout",
            "error_count": 1,
            "messages_sent": 100,
            "messages_received": 200,
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
            "reconnect_count": 1,
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

    def test_post_websocket_metrics_minimal_payload(self) -> None:
        """Endpoint should accept minimal payload with just endpoint_id."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        # Only required field
        payload = {
            "endpoint_id": "minimal",
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert response.json()["endpoint_id"] == "minimal"

    def test_post_websocket_metrics_validates_non_negative_connect_time(self) -> None:
        """total_connect_time_ms must be non-negative."""
        from mcp_server_langgraph.api.v1.websocket_metrics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        payload = {
            "endpoint_id": "test",
            "total_connect_time_ms": -100.0,  # Negative - should fail
        }

        response = client.post("/api/v1/websocket/metrics", json=payload)

        assert response.status_code == 422
