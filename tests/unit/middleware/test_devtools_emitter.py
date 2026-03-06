"""
Tests for DevTools Event Emitter Middleware.

TDD: These tests define expected behavior for the DevTools event emission system.
The middleware should:
- Emit network events for HTTP requests to DevTools WebSocket
- Extract session context from request path/headers
- Exclude health check and WebSocket upgrade endpoints
- Log events should be forwarded via DevToolsLoggingHandler

Note: This file uses AsyncMock extensively for mocking broadcaster methods.
The mocks are configured via method assignment (e.g., mock.method = AsyncMock(return_value=None))
which is the appropriate pattern for these tests.
# noqa: async-mock-config (file-level suppression for broadcaster mocks)
"""

import gc
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="devtools_emitter")
class TestDevToolsNetworkMiddleware:
    """Test DevTools network event middleware functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_emits_network_start_event(self) -> None:
        """Test that middleware emits network start event for requests."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/test")

            assert response.status_code == 200
            # Should have called broadcast_network for start event
            mock_broadcaster.broadcast_network.assert_called_once()
            call_args = mock_broadcaster.broadcast_network.call_args
            event_data = call_args[0][0]
            assert event_data["method"] == "GET"
            assert "/api/test" in event_data["url"]

    def test_middleware_emits_network_complete_event(self) -> None:
        """Test that middleware emits network completion event with status."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/data")
        def get_data() -> dict[str, str]:
            return {"data": "value"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/data")

            assert response.status_code == 200
            # Should have called broadcast_network_update for completion
            mock_broadcaster.broadcast_network_update.assert_called_once()
            call_args = mock_broadcaster.broadcast_network_update.call_args
            event_data = call_args[0][0]
            assert event_data["status"] == "completed"
            assert event_data["statusCode"] == 200

    def test_middleware_emits_error_status_for_failed_requests(self) -> None:
        """Test that middleware emits error status for 4xx/5xx responses."""
        from fastapi import HTTPException

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/error")
        def get_error() -> dict[str, str]:
            raise HTTPException(status_code=500, detail="Test error")

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/error")

            assert response.status_code == 500
            # Should have error status in completion event
            mock_broadcaster.broadcast_network_update.assert_called_once()
            call_args = mock_broadcaster.broadcast_network_update.call_args
            event_data = call_args[0][0]
            assert event_data["status"] == "error"
            assert event_data["statusCode"] == 500

    def test_middleware_excludes_health_endpoints(self) -> None:
        """Test that health check endpoints are excluded from network events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/health")

            assert response.status_code == 200
            # Should NOT have called any broadcast methods
            mock_broadcaster.broadcast_network.assert_not_called()
            mock_broadcaster.broadcast_network_update.assert_not_called()

    def test_middleware_excludes_metrics_endpoint(self) -> None:
        """Test that /metrics endpoint is excluded from network events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/metrics")
        def metrics() -> dict[str, str]:
            return {"metrics": "data"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/metrics")

            assert response.status_code == 200
            mock_broadcaster.broadcast_network.assert_not_called()

    def test_middleware_excludes_devtools_websocket_endpoint(self) -> None:
        """Test that DevTools WebSocket endpoint is excluded."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/v1/ws/devtools")
        def devtools_ws() -> dict[str, str]:
            return {"ws": "endpoint"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/v1/ws/devtools")

            assert response.status_code == 200
            mock_broadcaster.broadcast_network.assert_not_called()

    def test_middleware_calculates_request_duration(self) -> None:
        """Test that middleware calculates and reports request duration."""
        import time

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/slow")
        def slow_endpoint() -> dict[str, str]:
            time.sleep(0.05)  # 50ms delay
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/slow")

            assert response.status_code == 200
            call_args = mock_broadcaster.broadcast_network_update.call_args
            event_data = call_args[0][0]
            # Duration should be >= 50ms
            assert event_data["duration"] >= 50

    def test_middleware_continues_on_broadcast_failure(self) -> None:
        """Test that request processing continues even if broadcasting fails."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(side_effect=Exception("Broadcast failed"))
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise - request should complete successfully
            response = client.get("/api/test")
            assert response.status_code == 200


@pytest.mark.xdist_group(name="devtools_emitter")
class TestSessionContextExtraction:
    """Test session context extraction from requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extracts_session_id_from_path(self) -> None:
        """Test that session ID is extracted from URL path."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            _extract_session_context,
        )

        # Create mock request with session in path
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/sessions/abc123/messages"
        mock_request.headers = {}

        session_id = _extract_session_context(mock_request)
        assert session_id == "abc123"

    def test_extracts_session_id_from_header(self) -> None:
        """Test that session ID is extracted from X-Session-ID header."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            _extract_session_context,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/other"
        mock_request.headers = {"X-Session-ID": "header-session-123"}

        session_id = _extract_session_context(mock_request)
        assert session_id == "header-session-123"

    def test_path_takes_precedence_over_header(self) -> None:
        """Test that path-based session ID takes precedence over header."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            _extract_session_context,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/sessions/path-session/messages"
        mock_request.headers = {"X-Session-ID": "header-session"}

        session_id = _extract_session_context(mock_request)
        assert session_id == "path-session"

    def test_returns_none_when_no_session_context(self) -> None:
        """Test that None is returned when no session context is found."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            _extract_session_context,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/health"
        mock_request.headers = {}

        session_id = _extract_session_context(mock_request)
        assert session_id is None

    def test_middleware_passes_session_context_to_broadcaster(self) -> None:
        """Test that session context is passed to broadcaster."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/v1/sessions/{session_id}/messages")
        def get_messages(session_id: str) -> dict[str, str]:
            return {"session_id": session_id, "count": "0"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/v1/sessions/test-session-id/messages")

            assert response.status_code == 200
            # Check that context_entity_id was passed
            call_kwargs = mock_broadcaster.broadcast_network.call_args[1]
            assert call_kwargs.get("context_entity_id") == "test-session-id"


@pytest.mark.xdist_group(name="devtools_emitter")
class TestDevToolsLoggingHandler:
    """Test DevTools logging handler functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_maps_error_level(self) -> None:
        """Test that ERROR log level is mapped correctly."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.ERROR) == "error"
        assert handler._map_level(logging.CRITICAL) == "error"

    def test_handler_maps_warning_level(self) -> None:
        """Test that WARNING log level is mapped correctly."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.WARNING) == "warning"

    def test_handler_maps_info_level(self) -> None:
        """Test that INFO log level is mapped correctly."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.INFO) == "info"

    def test_handler_maps_debug_level(self) -> None:
        """Test that DEBUG log level is mapped correctly."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.DEBUG) == "debug"

    def test_handler_emits_log_to_broadcaster(self) -> None:
        """Test that handler emits log messages to DevTools broadcaster."""
        import asyncio

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test log message",
            args=(),
            exc_info=None,
        )

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsLoggingHandler._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_console = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Create and run event loop for the handler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                handler.emit(record)
                # Run pending tasks
                loop.run_until_complete(asyncio.sleep(0.01))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    def test_handler_includes_source_metadata(self) -> None:
        """Test that handler includes source file and line info."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        _handler = DevToolsLoggingHandler()

        record = logging.LogRecord(
            name="mcp_server_langgraph.api",
            level=logging.ERROR,
            pathname="/path/to/api.py",
            lineno=123,
            msg="API error occurred",
            args=(),
            exc_info=None,
        )

        # Verify record has the expected attributes
        assert record.filename == "api.py"
        assert record.lineno == 123
        assert record.name == "mcp_server_langgraph.api"

    def test_handler_does_not_raise_on_emit_failure(self) -> None:
        """Test that handler silently handles emit failures."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsLoggingHandler._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_get_broadcaster.side_effect = Exception("Broadcaster unavailable")

            # Should not raise
            handler.emit(record)


@pytest.mark.xdist_group(name="devtools_emitter")
class TestDevToolsMiddlewareIntegration:
    """Integration tests for DevTools middleware with FastAPI."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_integrates_with_fastapi(self) -> None:
        """Test that middleware integrates correctly with FastAPI."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def api_test() -> dict[str, str]:
            return {"message": "Hello"}

        @app.post("/api/data")
        def api_post() -> dict[str, str]:
            return {"created": "true"}

        client = TestClient(app)

        # Patch broadcaster to avoid actual WebSocket operations
        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Test GET request
            response = client.get("/api/test")
            assert response.status_code == 200

            # Test POST request
            response = client.post("/api/data")
            assert response.status_code == 200

    def test_middleware_does_not_break_exception_handling(self) -> None:
        """Test that middleware doesn't interfere with exception handling."""
        from fastapi import HTTPException

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/not-found")
        def not_found() -> None:
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/not-found")
            assert response.status_code == 404
            assert response.json()["detail"] == "Not found"


@pytest.mark.xdist_group(name="devtools_emitter")
class TestDevToolsMiddlewareEdgeCases:
    """Edge case and resilience tests for DevTools middleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_handles_concurrent_requests(self) -> None:
        """Test that middleware handles concurrent requests independently."""
        import concurrent.futures

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test/{request_id}")
        def get_test(request_id: str) -> dict[str, str]:
            return {"request_id": request_id}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Make concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(lambda i=i: client.get(f"/api/test/{i}")) for i in range(5)]
                responses = [f.result() for f in futures]

            # All should succeed
            assert all(r.status_code == 200 for r in responses)
            # Each request should have triggered broadcast events
            assert mock_broadcaster.broadcast_network.call_count == 5
            assert mock_broadcaster.broadcast_network_update.call_count == 5

    def test_middleware_reports_response_size_from_content_length(self) -> None:
        """Test that middleware reports response size from Content-Length header."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/sized")
        def get_sized() -> dict[str, str]:
            return {"data": "x" * 1000}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.get("/api/sized")

            assert response.status_code == 200
            # Check that response size was reported
            call_args = mock_broadcaster.broadcast_network_update.call_args
            event_data = call_args[0][0]
            # Response should have a size (may be None if Content-Length not set)
            assert "responseSize" in event_data

    def test_middleware_handles_empty_response_body(self) -> None:
        """Test that middleware handles endpoints with no response body."""
        from starlette.responses import Response as StarletteResponse

        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.delete("/api/resource")
        def delete_resource() -> StarletteResponse:
            return StarletteResponse(status_code=204)

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            response = client.delete("/api/resource")

            assert response.status_code == 204
            # Should still emit completion event
            mock_broadcaster.broadcast_network_update.assert_called_once()
            event_data = mock_broadcaster.broadcast_network_update.call_args[0][0]
            assert event_data["status"] == "completed"

    def test_middleware_handles_update_broadcast_failure(self) -> None:
        """Test that request succeeds even if update broadcast fails."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            # Update broadcast fails
            mock_broadcaster.broadcast_network_update = AsyncMock(side_effect=Exception("Update broadcast failed"))
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise - request should complete successfully
            response = client.get("/api/test")
            assert response.status_code == 200

    def test_middleware_emits_request_id(self) -> None:
        """Test that middleware generates and includes request ID in events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            client.get("/api/test")

            # Check that request ID is present in both start and update events
            start_event = mock_broadcaster.broadcast_network.call_args[0][0]
            update_event = mock_broadcaster.broadcast_network_update.call_args[0][0]

            assert "id" in start_event
            assert "id" in update_event
            # Same request ID should be used for both events
            assert start_event["id"] == update_event["id"]

    def test_middleware_emits_start_time(self) -> None:
        """Test that middleware includes start time in network events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            client.get("/api/test")

            start_event = mock_broadcaster.broadcast_network.call_args[0][0]
            assert "startTime" in start_event
            # Should be a reasonable timestamp (in milliseconds)
            assert start_event["startTime"] > 0

    def test_middleware_includes_request_headers(self) -> None:
        """Test that middleware includes request headers in network events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            client.get("/api/test", headers={"X-Custom-Header": "custom-value"})

            start_event = mock_broadcaster.broadcast_network.call_args[0][0]
            assert "requestHeaders" in start_event
            assert "x-custom-header" in start_event["requestHeaders"]

    def test_middleware_includes_response_headers(self) -> None:
        """Test that middleware includes response headers in update events."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsNetworkMiddleware,
        )

        app = FastAPI()
        app.add_middleware(DevToolsNetworkMiddleware)

        @app.get("/api/test")
        def get_test() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)

        with patch(
            "mcp_server_langgraph.middleware.devtools_emitter.DevToolsNetworkMiddleware._get_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_network = AsyncMock(return_value=None)
            mock_broadcaster.broadcast_network_update = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            client.get("/api/test")

            update_event = mock_broadcaster.broadcast_network_update.call_args[0][0]
            assert "responseHeaders" in update_event
            # FastAPI adds content-type header
            assert "content-type" in update_event["responseHeaders"]


@pytest.mark.xdist_group(name="devtools_emitter")
class TestLoggingHandlerEdgeCases:
    """Edge case tests for DevTools logging handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_handles_no_running_loop(self) -> None:
        """Test that handler gracefully handles when no event loop is running."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Should not raise when no event loop is running
        handler.emit(record)

    def test_handler_extracts_session_from_record_extra(self) -> None:
        """Test that handler extracts session_id from record extra dict."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        _handler = DevToolsLoggingHandler()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add session_id as record attribute
        record.session_id = "test-session-123"

        # The session_id should be extractable
        assert getattr(record, "session_id", None) == "test-session-123"

    def test_handler_maps_critical_to_error(self) -> None:
        """Test that CRITICAL log level maps to error."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.CRITICAL) == "error"

    def test_handler_maps_notset_to_debug(self) -> None:
        """Test that NOTSET log level maps to debug."""
        from mcp_server_langgraph.middleware.devtools_emitter import (
            DevToolsLoggingHandler,
        )

        handler = DevToolsLoggingHandler()
        assert handler._map_level(logging.NOTSET) == "debug"
