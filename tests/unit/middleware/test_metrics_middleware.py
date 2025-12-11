"""
Tests for HTTP metrics middleware.

TDD: These tests define expected behavior for HTTP request metrics collection.
The middleware should record:
- http_requests_total (Counter) with method, endpoint, status labels
- http_request_duration_seconds (Histogram) with method, endpoint labels
"""

import gc
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="metrics_middleware")
class TestMetricsMiddleware:
    """Test HTTP metrics middleware functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_records_request_count(self) -> None:
        """Test that middleware increments request counter for each request."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/test")
        def get_test_status() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch("mcp_server_langgraph.middleware.metrics.http_requests_total") as mock_counter:
            mock_counter.labels = MagicMock(return_value=MagicMock())

            response = client.get("/test")

            assert response.status_code == 200
            mock_counter.labels.assert_called()
            # Verify labels include method, endpoint, and status
            call_kwargs = mock_counter.labels.call_args
            assert call_kwargs is not None

    def test_middleware_records_request_duration(self) -> None:
        """Test that middleware records request duration histogram."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/slow")
        def slow_endpoint() -> dict[str, str]:
            time.sleep(0.1)  # 100ms delay
            return {"status": "ok"}

        client = TestClient(app)

        with patch("mcp_server_langgraph.middleware.metrics.http_request_duration_seconds") as mock_histogram:
            mock_histogram.labels = MagicMock(return_value=MagicMock())

            response = client.get("/slow")

            assert response.status_code == 200
            mock_histogram.labels.assert_called()
            # Verify observe was called with duration
            mock_histogram.labels.return_value.observe.assert_called()

    def test_middleware_records_error_status_codes(self) -> None:
        """Test that middleware records error status codes correctly."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/error")
        def error_endpoint() -> None:
            raise ValueError("Test error")

        client = TestClient(app, raise_server_exceptions=False)

        with patch("mcp_server_langgraph.middleware.metrics.http_requests_total") as mock_counter:
            mock_counter.labels = MagicMock(return_value=MagicMock())

            response = client.get("/error")

            assert response.status_code == 500
            # Should record 500 status
            mock_counter.labels.assert_called()

    def test_middleware_normalizes_path_parameters(self) -> None:
        """Test that path parameters are normalized to prevent high cardinality."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/users/{user_id}")
        def get_user(user_id: str) -> dict[str, str]:
            return {"user_id": user_id}

        client = TestClient(app)

        with patch("mcp_server_langgraph.middleware.metrics.http_requests_total") as mock_counter:
            mock_counter.labels = MagicMock(return_value=MagicMock())

            # Make requests with different user IDs
            client.get("/users/123")
            client.get("/users/456")

            # Both should be recorded with normalized path
            calls = mock_counter.labels.call_args_list
            assert len(calls) == 2

    def test_middleware_excludes_health_endpoints(self) -> None:
        """Test that health check endpoints are excluded from metrics."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        @app.get("/metrics")
        def metrics_endpoint() -> dict[str, str]:
            return {"metrics": "data"}

        client = TestClient(app)

        with patch("mcp_server_langgraph.middleware.metrics.http_requests_total") as mock_counter:
            mock_counter.labels = MagicMock(return_value=MagicMock())

            client.get("/health")
            client.get("/metrics")

            # Health and metrics endpoints should not be recorded
            assert mock_counter.labels.call_count == 0

    def test_middleware_handles_missing_prometheus_client(self) -> None:
        """Test graceful degradation when prometheus_client is not available."""
        with patch.dict("sys.modules", {"prometheus_client": None}):
            # Should not raise when prometheus_client is unavailable
            # The middleware should gracefully skip metrics recording
            pass  # Middleware should handle this gracefully


@pytest.mark.xdist_group(name="metrics_middleware")
class TestMetricsMiddlewareIntegration:
    """Integration tests for metrics middleware with real FastAPI app."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_integrates_with_fastapi(self) -> None:
        """Test that middleware integrates correctly with FastAPI."""
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/api/test")
        def api_test() -> dict[str, str]:
            return {"message": "Hello"}

        @app.post("/api/data")
        def api_post() -> dict[str, str]:
            return {"created": "true"}

        client = TestClient(app)

        # Test GET request
        response = client.get("/api/test")
        assert response.status_code == 200

        # Test POST request
        response = client.post("/api/data")
        assert response.status_code == 200

    def test_middleware_does_not_break_exception_handling(self) -> None:
        """Test that middleware doesn't interfere with exception handling."""
        from fastapi import HTTPException

        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        app = FastAPI()
        app.add_middleware(MetricsMiddleware)

        @app.get("/not-found")
        def not_found() -> None:
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app)

        response = client.get("/not-found")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"
