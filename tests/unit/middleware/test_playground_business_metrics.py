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
