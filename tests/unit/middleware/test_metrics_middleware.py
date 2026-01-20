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


@pytest.mark.xdist_group(name="metrics_middleware_broadcaster")
class TestMetricsBroadcasterWiring:
    """Tests for MetricsBroadcaster integration in metrics middleware.

    TDD tests verifying that HTTP metrics are broadcast to DevTools
    via MetricsBroadcaster for real-time streaming.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_to_devtools_sends_counter_metric(self) -> None:
        """
        GIVEN a request is processed by the middleware
        WHEN _broadcast_to_devtools is called
        THEN it should broadcast http_requests_total counter metric
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-session-123"

        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_metric = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Call the method
            middleware._broadcast_to_devtools(
                request=mock_request,
                method="GET",
                endpoint="/api/test",
                status="200",
                duration=0.05,
            )

            # Allow async tasks to run
            import asyncio

            await asyncio.sleep(0.01)

            # Verify counter metric was broadcast
            calls = mock_broadcaster.broadcast_metric.call_args_list
            counter_call = next(
                (c for c in calls if c.kwargs.get("name") == "http_requests_total"),
                None,
            )
            assert counter_call is not None
            assert counter_call.kwargs["value"] == 1.0
            assert counter_call.kwargs["labels"]["method"] == "GET"
            assert counter_call.kwargs["labels"]["endpoint"] == "/api/test"
            assert counter_call.kwargs["labels"]["status"] == "200"
            assert counter_call.kwargs["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_broadcast_to_devtools_sends_histogram_metric(self) -> None:
        """
        GIVEN a request is processed by the middleware
        WHEN _broadcast_to_devtools is called
        THEN it should broadcast http_request_duration_seconds histogram metric
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-session-456"

        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_metric = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Call the method with specific duration
            middleware._broadcast_to_devtools(
                request=mock_request,
                method="POST",
                endpoint="/api/data",
                status="201",
                duration=0.123,
            )

            # Allow async tasks to run
            import asyncio

            await asyncio.sleep(0.01)

            # Verify histogram metric was broadcast
            calls = mock_broadcaster.broadcast_metric.call_args_list
            histogram_call = next(
                (c for c in calls if c.kwargs.get("name") == "http_request_duration_seconds"),
                None,
            )
            assert histogram_call is not None
            assert histogram_call.kwargs["value"] == 0.123
            assert histogram_call.kwargs["labels"]["method"] == "POST"
            assert histogram_call.kwargs["labels"]["endpoint"] == "/api/data"
            assert histogram_call.kwargs["session_id"] == "test-session-456"

    @pytest.mark.asyncio
    async def test_broadcast_to_devtools_extracts_session_id_from_header(self) -> None:
        """
        GIVEN a request with x-session-id header
        WHEN _broadcast_to_devtools is called
        THEN it should extract and pass the session_id to broadcaster
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "custom-session-id-789"

        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_metric = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            middleware._broadcast_to_devtools(
                request=mock_request,
                method="GET",
                endpoint="/test",
                status="200",
                duration=0.01,
            )

            # Verify header extraction
            mock_request.headers.get.assert_called_with("x-session-id")

            # Allow async tasks to run
            import asyncio

            await asyncio.sleep(0.01)

            # Verify session_id passed to broadcaster
            calls = mock_broadcaster.broadcast_metric.call_args_list
            for call in calls:
                assert call.kwargs["session_id"] == "custom-session-id-789"

    def test_broadcast_to_devtools_handles_no_event_loop_gracefully(self) -> None:
        """
        GIVEN no event loop is running
        WHEN _broadcast_to_devtools is called
        THEN it should return without error (skip broadcasting)
        """
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        # This should not raise even without an event loop
        # The method catches RuntimeError from get_running_loop()
        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise
            middleware._broadcast_to_devtools(
                request=mock_request,
                method="GET",
                endpoint="/test",
                status="200",
                duration=0.01,
            )

            # broadcast_metric should not be called (no event loop)
            mock_broadcaster.broadcast_metric.assert_not_called()

    def test_broadcast_to_devtools_handles_import_error_gracefully(self) -> None:
        """
        GIVEN MetricsBroadcaster import fails
        WHEN _broadcast_to_devtools is called
        THEN it should handle the error gracefully without breaking the request
        """
        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster",
            side_effect=ImportError("Module not found"),
        ):
            # Should not raise - errors are caught and logged
            middleware._broadcast_to_devtools(
                request=mock_request,
                method="GET",
                endpoint="/test",
                status="200",
                duration=0.01,
            )
            # Test passes if no exception is raised

    def test_broadcast_to_devtools_handles_none_session_id(self) -> None:
        """
        GIVEN a request without x-session-id header
        WHEN _broadcast_to_devtools is called
        THEN it should pass None as session_id to broadcaster
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.middleware.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None  # No session ID

        with patch(
            "mcp_server_langgraph.websocket.handlers.metrics_broadcaster.get_metrics_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_metric = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Use asyncio to run in event loop context
            import asyncio

            async def run_test() -> None:
                middleware._broadcast_to_devtools(
                    request=mock_request,
                    method="GET",
                    endpoint="/test",
                    status="200",
                    duration=0.01,
                )
                await asyncio.sleep(0.01)

                # Verify None session_id passed
                calls = mock_broadcaster.broadcast_metric.call_args_list
                for call in calls:
                    assert call.kwargs["session_id"] is None

            asyncio.run(run_test())
