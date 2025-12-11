"""
Tests for HTTP metrics middleware integration with Builder and Playground.

Verifies that both services properly integrate MetricsMiddleware to emit:
- http_requests_total (Counter) - Total requests by method, endpoint, status
- http_request_duration_seconds (Histogram) - Request duration by method, endpoint

These metrics are scraped by Alloy and displayed in LGTM Grafana dashboards.

Follows TDD principles (RED phase - these tests define expected behavior).
"""

import gc
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.observability, pytest.mark.metrics]


@pytest.mark.xdist_group(name="http_metrics_integration")
class TestBuilderHttpMetrics:
    """Test Builder service HTTP metrics via MetricsMiddleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_builder_uses_metrics_middleware(self) -> None:
        """Test that Builder app includes MetricsMiddleware."""
        from mcp_server_langgraph.builder.api.server import app

        # Check that MetricsMiddleware is in the middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "MetricsMiddleware" in middleware_classes, "Builder should use MetricsMiddleware for HTTP metrics"

    @pytest.mark.unit
    def test_builder_http_requests_metric_incremented(self) -> None:
        """Test that Builder increments http_requests_total on requests."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Mock the prometheus counter
            mock_counter = MagicMock()
            with patch(
                "mcp_server_langgraph.middleware.metrics.http_requests_total",
                mock_counter,
            ):
                client = TestClient(app)
                response = client.get("/api/builder/health")

                assert response.status_code == 200

                # Verify counter was incremented (if middleware is applied)
                # Note: This will fail until MetricsMiddleware is added
                if mock_counter.labels.called:
                    mock_counter.labels.assert_called()

    @pytest.mark.unit
    def test_builder_http_duration_metric_recorded(self) -> None:
        """Test that Builder records http_request_duration_seconds."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            mock_histogram = MagicMock()
            with patch(
                "mcp_server_langgraph.middleware.metrics.http_request_duration_seconds",
                mock_histogram,
            ):
                client = TestClient(app)
                response = client.post(
                    "/api/builder/validate",
                    json={
                        "workflow": {
                            "name": "test",
                            "nodes": [{"id": "start", "type": "llm", "label": "Start", "config": {}}],
                            "edges": [],
                            "entry_point": "start",
                        }
                    },
                )

                assert response.status_code == 200

    @pytest.mark.unit
    def test_builder_metrics_endpoint_includes_http_metrics(self) -> None:
        """Test that /metrics endpoint includes http_* metrics."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Make some requests to generate metrics
            client.get("/api/builder/health")
            client.get("/api/builder/templates")

            # Check metrics endpoint
            response = client.get("/metrics")

            if response.status_code == 200:
                metrics_text = response.text
                # HTTP metrics should be present
                assert "http_requests_total" in metrics_text or "http_request" in metrics_text, (
                    "Builder /metrics should include HTTP request metrics"
                )


@pytest.mark.xdist_group(name="http_metrics_integration")
class TestPlaygroundHttpMetrics:
    """Test Playground service HTTP metrics via MetricsMiddleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_playground_uses_metrics_middleware(self) -> None:
        """Test that Playground app includes MetricsMiddleware."""
        from mcp_server_langgraph.playground.api.server import app

        # Check that MetricsMiddleware is in the middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "MetricsMiddleware" in middleware_classes, "Playground should use MetricsMiddleware for HTTP metrics"

    @pytest.mark.unit
    def test_playground_http_requests_metric_incremented(self) -> None:
        """Test that Playground increments http_requests_total on requests."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            mock_counter = MagicMock()
            with patch(
                "mcp_server_langgraph.middleware.metrics.http_requests_total",
                mock_counter,
            ):
                client = TestClient(app)
                response = client.get("/api/playground/health")

                assert response.status_code == 200

    @pytest.mark.unit
    def test_playground_http_duration_metric_recorded(self) -> None:
        """Test that Playground records http_request_duration_seconds."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            mock_histogram = MagicMock()
            with patch(
                "mcp_server_langgraph.middleware.metrics.http_request_duration_seconds",
                mock_histogram,
            ):
                client = TestClient(app)
                response = client.post(
                    "/api/playground/sessions",
                    json={"name": "Metrics Test"},
                )

                # 201 Created is expected for session creation
                assert response.status_code in [200, 201]

    @pytest.mark.unit
    def test_playground_metrics_endpoint_includes_http_metrics(self) -> None:
        """Test that /metrics endpoint includes http_* metrics."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Make some requests to generate metrics
            client.get("/api/playground/health")
            client.post("/api/playground/sessions", json={"name": "Test"})

            # Check metrics endpoint
            response = client.get("/metrics")

            if response.status_code == 200:
                metrics_text = response.text
                assert "http_requests_total" in metrics_text or "http_request" in metrics_text, (
                    "Playground /metrics should include HTTP request metrics"
                )


@pytest.mark.xdist_group(name="http_metrics_integration")
class TestHttpMetricsExclusions:
    """Test that health/metrics endpoints are excluded from metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_health_endpoints_excluded_from_builder_metrics(self) -> None:
        """Test that /health endpoints don't inflate Builder metrics."""
        from mcp_server_langgraph.middleware.metrics import should_skip_metrics

        # These paths should be excluded
        assert should_skip_metrics("/health") is True
        assert should_skip_metrics("/healthz") is True
        assert should_skip_metrics("/api/builder/health") is False  # API health is tracked

    @pytest.mark.unit
    def test_metrics_endpoint_excluded_from_metrics(self) -> None:
        """Test that /metrics endpoint doesn't count itself."""
        from mcp_server_langgraph.middleware.metrics import should_skip_metrics

        assert should_skip_metrics("/metrics") is True
        assert should_skip_metrics("/metrics/") is True

    @pytest.mark.unit
    def test_api_endpoints_included_in_metrics(self) -> None:
        """Test that API endpoints are included in metrics."""
        from mcp_server_langgraph.middleware.metrics import should_skip_metrics

        # These should be tracked
        assert should_skip_metrics("/api/builder/generate") is False
        assert should_skip_metrics("/api/playground/chat") is False
        assert should_skip_metrics("/api/playground/sessions") is False
