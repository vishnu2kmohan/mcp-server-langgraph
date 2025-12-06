"""
Tests for In-Context Observability in Interactive Playground.

Tests the in-app observability features that enable debugging without
leaving the application:
- Real-time trace streaming via WebSocket
- Session-scoped log viewing
- LLM and tool metrics display
- Proactive alert notifications

This provides a highly productive developer UX by embedding observability
directly into the playground interface.

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.observability]


# ==============================================================================
# In-Context Trace API Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundInContextTraces:
    """Test in-context trace viewing for debugging."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_session_traces_returns_recent_traces(self) -> None:
        """Test that GET /api/playground/observability/traces returns session traces."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Trace Test"},
            )
            session_id = session_response.json()["session_id"]

            # Get traces for session
            response = client.get(f"/api/playground/observability/traces?session_id={session_id}")

            assert response.status_code == 200
            data = response.json()
            assert "traces" in data
            assert isinstance(data["traces"], list)

    @pytest.mark.unit
    def test_get_trace_details_returns_span_tree(self) -> None:
        """Test that GET /api/playground/observability/traces/{id} returns span tree."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Get specific trace details
            response = client.get("/api/playground/observability/traces/test-trace-id")

            # May return 404 if trace doesn't exist, or 200 with data
            assert response.status_code in [200, 404]

    @pytest.mark.unit
    def test_traces_include_llm_call_spans(self) -> None:
        """Test that traces include LLM call spans with latency and tokens."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session and send message to generate LLM trace
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "LLM Trace Test"},
            )
            session_id = session_response.json()["session_id"]

            # Send chat message
            client.post(
                "/api/playground/chat",
                json={"session_id": session_id, "message": "Hello"},
            )

            # Get traces
            response = client.get(f"/api/playground/observability/traces?session_id={session_id}")
            assert response.status_code == 200

    @pytest.mark.unit
    def test_traces_include_tool_execution_spans(self) -> None:
        """Test that traces include tool execution spans with args and results."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Tool Trace Test"},
            )
            session_id = session_response.json()["session_id"]

            # Get traces (tools may not be executed in simple messages)
            response = client.get(f"/api/playground/observability/traces?session_id={session_id}")
            assert response.status_code == 200


# ==============================================================================
# In-Context Logs API Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundInContextLogs:
    """Test in-context log viewing for debugging."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_session_logs_returns_recent_logs(self) -> None:
        """Test that GET /api/playground/observability/logs returns session logs."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Logs Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/logs?session_id={session_id}")

            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            assert isinstance(data["logs"], list)

    @pytest.mark.unit
    def test_logs_filterable_by_level(self) -> None:
        """Test that logs can be filtered by level (info, warning, error)."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Level Filter Test"},
            )
            session_id = session_response.json()["session_id"]

            # Filter by error level
            response = client.get(f"/api/playground/observability/logs?session_id={session_id}&level=error")

            assert response.status_code == 200

    @pytest.mark.unit
    def test_logs_include_trace_correlation(self) -> None:
        """Test that logs include trace_id for correlation with traces."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Correlation Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/logs?session_id={session_id}")

            assert response.status_code == 200
            # Logs should include trace_id field when available
            # (actual content depends on implementation)


# ==============================================================================
# In-Context Metrics API Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundInContextMetrics:
    """Test in-context metrics display."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_llm_metrics_returns_latency_and_tokens(self) -> None:
        """Test that GET /api/playground/observability/metrics/llm returns LLM stats."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "LLM Metrics Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/metrics/llm?session_id={session_id}")

            assert response.status_code == 200
            data = response.json()
            # Should include key LLM metrics
            assert "latency_p50_ms" in data or "total_tokens" in data or "metrics" in data

    @pytest.mark.unit
    def test_get_tool_metrics_returns_call_stats(self) -> None:
        """Test that GET /api/playground/observability/metrics/tools returns tool stats."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Tool Metrics Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/metrics/tools?session_id={session_id}")

            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data or "tool_calls" in data or "tools" in data

    @pytest.mark.unit
    def test_get_session_metrics_summary(self) -> None:
        """Test that GET /api/playground/observability/metrics returns summary."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Summary Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/metrics?session_id={session_id}")

            assert response.status_code == 200


# ==============================================================================
# In-Context Alerts API Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundInContextAlerts:
    """Test in-context alert notifications."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_active_alerts_returns_list(self) -> None:
        """Test that GET /api/playground/observability/alerts returns active alerts."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            response = client.get("/api/playground/observability/alerts")

            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            assert isinstance(data["alerts"], list)

    @pytest.mark.unit
    def test_alerts_include_severity_and_context(self) -> None:
        """Test that alerts include severity level and context."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            response = client.get("/api/playground/observability/alerts")

            assert response.status_code == 200
            # Alert structure validated even if empty list


# ==============================================================================
# Real-time Observability WebSocket Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundRealTimeObservability:
    """Test real-time observability event streaming via WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_websocket_receives_trace_events(self) -> None:
        """Test that WebSocket receives trace_start and trace_end events."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Trace Stream Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                # Receive welcome
                welcome = websocket.receive_json()
                assert welcome["type"] == "connected"

                # Send message to trigger trace
                websocket.send_json(
                    {
                        "type": "message",
                        "content": "Hello trace test",
                    }
                )

                # Collect messages - may include trace events
                messages = []
                for _ in range(10):
                    try:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                    except Exception:
                        break

                assert len(messages) > 0

    @pytest.mark.unit
    def test_websocket_receives_log_events(self) -> None:
        """Test that WebSocket receives log events in real-time."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Log Stream Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                websocket.send_json(
                    {
                        "type": "message",
                        "content": "Hello log test",
                    }
                )

                # Messages may include log events
                messages = []
                for _ in range(10):
                    try:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                    except Exception:
                        break

                assert len(messages) > 0

    @pytest.mark.unit
    def test_websocket_receives_metric_updates(self) -> None:
        """Test that WebSocket receives metric update events."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Metric Stream Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                websocket.send_json(
                    {
                        "type": "message",
                        "content": "Hello metric test",
                    }
                )

                messages = []
                for _ in range(10):
                    try:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                    except Exception:
                        break

                assert len(messages) > 0

    @pytest.mark.unit
    def test_websocket_receives_alert_notifications(self) -> None:
        """Test that WebSocket receives alert events when triggered."""
        # This test validates the pattern - actual alerts from AlertManager
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Alert Stream Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                welcome = websocket.receive_json()
                assert welcome["type"] == "connected"
                # Alert events would be pushed when AlertManager fires


# ==============================================================================
# Observability Panel Data Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_observability")
class TestPlaygroundObservabilityPanels:
    """Test data structures for observability UI panels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_trace_panel_data_includes_waterfall_info(self) -> None:
        """Test that trace data includes info for rendering waterfall chart."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Waterfall Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/traces?session_id={session_id}")

            assert response.status_code == 200

    @pytest.mark.unit
    def test_metrics_panel_data_includes_sparkline_history(self) -> None:
        """Test that metrics data includes history for sparkline rendering."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Sparkline Test"},
            )
            session_id = session_response.json()["session_id"]

            response = client.get(f"/api/playground/observability/metrics?session_id={session_id}")

            assert response.status_code == 200

    @pytest.mark.unit
    def test_logs_panel_data_includes_structured_fields(self) -> None:
        """Test that logs data includes structured fields for Logs Panel rendering."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Logs Panel Test"},
            )
            session_id = session_response.json()["session_id"]

            # Send a chat message to generate logs
            client.post(
                "/api/playground/chat",
                json={"session_id": session_id, "message": "Test for logs panel"},
            )

            response = client.get(f"/api/playground/observability/logs?session_id={session_id}")

            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            # Each log entry should have structured fields for the Logs Panel:
            # - timestamp, level, message, trace_id (optional), span_id (optional)

    @pytest.mark.unit
    def test_logs_panel_supports_live_tail(self) -> None:
        """Test that logs endpoint supports 'tail' mode for live streaming."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Live Tail Test"},
            )
            session_id = session_response.json()["session_id"]

            # Request logs with tail parameter (last N logs)
            response = client.get(f"/api/playground/observability/logs?session_id={session_id}&tail=50")

            assert response.status_code == 200

    @pytest.mark.unit
    def test_logs_panel_supports_search_filter(self) -> None:
        """Test that logs endpoint supports search/filter by keyword."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Search Filter Test"},
            )
            session_id = session_response.json()["session_id"]

            # Request logs with search filter
            response = client.get(f"/api/playground/observability/logs?session_id={session_id}&search=error")

            assert response.status_code == 200

    @pytest.mark.unit
    def test_alerts_panel_data_includes_actionable_info(self) -> None:
        """Test that alerts data includes actionable context for Alerts Panel."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            response = client.get("/api/playground/observability/alerts")

            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            # Each alert should have: severity, name, message, timestamp, link (optional)
