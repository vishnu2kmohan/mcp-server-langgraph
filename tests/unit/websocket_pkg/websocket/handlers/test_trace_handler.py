"""
Unit tests for TraceWebSocketHandler.

TDD: These tests define expected behavior for real-time trace streaming.
The handler should:
- Support subscription to trace events with optional filters
- Push real-time span updates when traces are received
- Filter by service_name, operation_name, or trace_id
- Clear filters to receive all traces
"""

import gc
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@dataclass
class TraceFilter:
    """Expected filter structure for traces."""

    service_name: str | None = None
    operation_name: str | None = None
    trace_id: str | None = None
    min_duration_ms: float | None = None
    status: str | None = None  # "OK", "ERROR", "UNSET"


@pytest.fixture
def mock_broadcaster():
    """Create a mock trace broadcaster."""
    from mcp_server_langgraph.observability.trace_broadcaster import TraceBroadcaster

    broadcaster = AsyncMock(spec=TraceBroadcaster)
    broadcaster.subscribe = AsyncMock(return_value=None)
    broadcaster.unsubscribe = AsyncMock(return_value=None)
    return broadcaster


@pytest.fixture
def trace_handler_config():
    """Create a standard trace handler configuration."""
    return WebSocketConfig(
        endpoint_name="traces",
        require_auth=True,
        authz_resource_type="traces",
        authz_resource_id="trace-stream",
        authz_required_relation="viewer",
        rate_limit_per_minute=600,
        message_timeout=30,
    )


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return AuthUser(
        id="user-123",
        username="testuser",
        email="test@example.com",
        roles=["developer"],
    )


class TestTraceHandler:
    """Tests for TraceHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_initializes_with_config_and_broadcaster(self, trace_handler_config, mock_broadcaster) -> None:
        """Test handler initialization with required dependencies."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )

        assert handler._broadcaster is mock_broadcaster
        assert handler._current_filter is not None

    @pytest.mark.asyncio
    async def test_on_connect_subscribes_to_broadcaster(self, trace_handler_config, mock_broadcaster, mock_user) -> None:
        """Test that on_connect subscribes to trace broadcaster."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        # Simulate base class run() which sets _user before calling on_connect
        handler._user = mock_user

        await handler.on_connect(mock_user)

        mock_broadcaster.subscribe.assert_called_once()
        assert handler.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes_from_broadcaster(
        self, trace_handler_config, mock_broadcaster, mock_user
    ) -> None:
        """Test that on_disconnect unsubscribes from trace broadcaster."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._subscribed = True

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, trace_handler_config, mock_broadcaster) -> None:
        """Test handling subscribe message."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user = AuthUser(id="user-123", username="testuser", email="test@example.com", roles=["developer"])

        message = MessageEnvelope(type="subscribe", id="req-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.id == "req-1"

    @pytest.mark.asyncio
    async def test_handle_set_filter_message(self, trace_handler_config, mock_broadcaster) -> None:
        """Test handling set_filter message with trace criteria."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user = AuthUser(id="user-123", username="testuser", email="test@example.com", roles=["developer"])
        handler._subscribed = True

        message = MessageEnvelope(
            type="set_filter",
            id="req-2",
            payload={
                "service_name": "mcp-server-langgraph",
                "min_duration_ms": 100.0,
                "status": "ERROR",
            },
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        assert response.id == "req-2"
        # Verify broadcaster was called with new filter
        assert mock_broadcaster.unsubscribe.called
        assert mock_broadcaster.subscribe.called

    @pytest.mark.asyncio
    async def test_handle_clear_filter_message(self, trace_handler_config, mock_broadcaster) -> None:
        """Test handling clear_filter message."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user = AuthUser(id="user-123", username="testuser", email="test@example.com", roles=["developer"])
        handler._subscribed = True

        message = MessageEnvelope(type="clear_filter", id="req-3")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_cleared"
        assert response.id == "req-3"

    @pytest.mark.asyncio
    async def test_handle_get_recent_traces_message(self, trace_handler_config, mock_broadcaster) -> None:
        """Test handling get_recent message for recent traces."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        # Mock broadcaster to return sample traces
        mock_broadcaster.get_recent_traces = AsyncMock(
            return_value=[
                {
                    "trace_id": "abc123",
                    "service_name": "mcp-server",
                    "operation_name": "chat.completion",
                    "duration_ms": 150.5,
                }
            ]
        )

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user = AuthUser(id="user-123", username="testuser", email="test@example.com", roles=["developer"])

        message = MessageEnvelope(
            type="get_recent",
            id="req-4",
            payload={"limit": 10},
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "recent_traces"
        assert response.id == "req-4"
        assert "traces" in response.payload

    @pytest.mark.asyncio
    async def test_handle_unknown_message_returns_error(self, trace_handler_config, mock_broadcaster) -> None:
        """Test that unknown message types return error."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=trace_handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()

        message = MessageEnvelope(type="invalid_type", id="req-5")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.id == "req-5"
        assert "unknown" in response.payload.get("message", "").lower()


class TestTraceFilter:
    """Tests for TraceFilter dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_creation_with_defaults(self) -> None:
        """Test creating a filter with default values."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceFilter

        filter_ = TraceFilter()

        assert filter_.service_name is None
        assert filter_.operation_name is None
        assert filter_.trace_id is None
        assert filter_.min_duration_ms is None
        assert filter_.status is None

    def test_filter_creation_with_all_fields(self) -> None:
        """Test creating a filter with all fields populated."""
        from mcp_server_langgraph.websocket.handlers.trace import TraceFilter

        filter_ = TraceFilter(
            service_name="my-service",
            operation_name="api.request",
            trace_id="abc123",
            min_duration_ms=50.0,
            status="ERROR",
        )

        assert filter_.service_name == "my-service"
        assert filter_.operation_name == "api.request"
        assert filter_.trace_id == "abc123"
        assert filter_.min_duration_ms == 50.0
        assert filter_.status == "ERROR"
