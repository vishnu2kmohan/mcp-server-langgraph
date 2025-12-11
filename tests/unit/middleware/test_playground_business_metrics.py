"""
Tests for Playground service business metrics.

Verifies that Playground properly emits business-level metrics:
- playground_active_sessions (Gauge) - Active session count
- playground_chat_messages_total (Counter) - Chat message count
- playground_chat_latency_seconds (Histogram) - Chat response latency

These metrics are scraped by Alloy and displayed in the Playground Grafana dashboard.

Follows TDD principles (RED phase - these tests define expected behavior).
"""

import gc
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.observability, pytest.mark.metrics]


@pytest.mark.xdist_group(name="playground_business_metrics")
class TestPlaygroundBusinessMetrics:
    """Test Playground service business metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_playground_session_metric_exists(self) -> None:
        """Test that playground session metrics are defined."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create a session
            response = client.post(
                "/api/playground/sessions",
                json={"name": "Metrics Test Session"},
            )
            assert response.status_code == 201

            # Check metrics endpoint
            metrics_response = client.get("/metrics")
            assert metrics_response.status_code == 200

            metrics_text = metrics_response.text
            assert "playground_sessions" in metrics_text or "playground_active_sessions" in metrics_text, (
                "Playground should emit session metrics"
            )

    @pytest.mark.unit
    def test_playground_chat_metric_exists(self) -> None:
        """Test that playground_chat_messages_total metric is defined."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session first
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Chat Metrics Test"},
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["session_id"]

            # Send a chat message
            client.post(
                "/api/playground/chat",
                json={"session_id": session_id, "message": "Hello, world!"},
            )

            # Check metrics endpoint
            metrics_response = client.get("/metrics")
            assert metrics_response.status_code == 200

            metrics_text = metrics_response.text
            assert "playground_chat" in metrics_text, "Playground should emit chat message metrics"

    @pytest.mark.unit
    def test_playground_llm_tokens_metric_exists(self) -> None:
        """Test that playground_llm_tokens_total metric is defined."""
        from mcp_server_langgraph.playground.api import metrics

        # Initialize metrics
        metrics._init_metrics()

        # Check that the metric is registered
        assert metrics._playground_llm_tokens_total is not None, "playground_llm_tokens_total metric should be defined"

    @pytest.mark.unit
    def test_playground_tool_calls_metric_exists(self) -> None:
        """Test that playground_tool_calls_total metric is defined."""
        from mcp_server_langgraph.playground.api import metrics

        # Initialize metrics
        metrics._init_metrics()

        # Check that the metric is registered
        assert metrics._playground_tool_calls_total is not None, "playground_tool_calls_total metric should be defined"

    @pytest.mark.unit
    def test_playground_tool_duration_metric_exists(self) -> None:
        """Test that playground_tool_duration_seconds metric is defined."""
        from mcp_server_langgraph.playground.api import metrics

        # Initialize metrics
        metrics._init_metrics()

        # Check that the metric is registered
        assert metrics._playground_tool_duration is not None, "playground_tool_duration_seconds metric should be defined"

    @pytest.mark.unit
    def test_playground_traces_metric_exists(self) -> None:
        """Test that playground_traces_total metric is defined."""
        from mcp_server_langgraph.playground.api import metrics

        # Initialize metrics
        metrics._init_metrics()

        # Check that the metric is registered
        assert metrics._playground_traces_total is not None, "playground_traces_total metric should be defined"

    @pytest.mark.unit
    def test_record_llm_tokens(self) -> None:
        """Test recording LLM token usage."""
        from mcp_server_langgraph.playground.api import metrics

        # Should not raise
        metrics.record_llm_tokens(prompt_tokens=100, completion_tokens=50)

    @pytest.mark.unit
    def test_record_tool_call(self) -> None:
        """Test recording tool call metrics."""
        from mcp_server_langgraph.playground.api import metrics

        # Should not raise
        metrics.record_tool_call(tool_name="search", duration=0.5, success=True)

    @pytest.mark.unit
    def test_record_trace_created(self) -> None:
        """Test recording trace creation."""
        from mcp_server_langgraph.playground.api import metrics

        # Should not raise
        metrics.record_trace_created(span_count=5)
