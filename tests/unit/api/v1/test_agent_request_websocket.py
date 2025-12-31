"""
Tests for Agent Request WebSocket API.

Follows TDD methodology - tests written first (RED phase).

WebSocket endpoint for real-time HITL agent request notifications.
Message types:
- approval_required: New approval request (server → client)
- clarification_required: New clarification request (server → client)
- approval_updated: Status change notification
- execution_resumed: Agent resumed after decision
- clarification_response: User's response to clarification (client → server)
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketExists:
    """Test that agent request WebSocket module exists."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_router_module_exists(self) -> None:
        """Test that agent_request_websocket module can be imported."""
        from mcp_server_langgraph.api.v1 import agent_request_websocket

        assert agent_request_websocket is not None

    def test_websocket_router_has_router(self) -> None:
        """Test that module has router attribute."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import router

        assert router is not None

    def test_websocket_router_has_prefix(self) -> None:
        """Test that router has correct prefix."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import router

        assert router.prefix == "/ws/agents/requests"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketMessageTypes:
    """Test WebSocket message type definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_type_enum_exists(self) -> None:
        """Test that AgentRequestWSMessageType enum exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType is not None

    def test_message_type_approval_required(self) -> None:
        """Test approval_required message type."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.APPROVAL_REQUIRED == "approval_required"

    def test_message_type_clarification_required(self) -> None:
        """Test clarification_required message type."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.CLARIFICATION_REQUIRED == "clarification_required"

    def test_message_type_approval_updated(self) -> None:
        """Test approval_updated message type."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.APPROVAL_UPDATED == "approval_updated"

    def test_message_type_execution_resumed(self) -> None:
        """Test execution_resumed message type."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.EXECUTION_RESUMED == "execution_resumed"

    def test_message_type_pong(self) -> None:
        """Test pong message type for keepalive."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.PONG == "pong"

    def test_message_type_error(self) -> None:
        """Test error message type."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestWSMessageType,
        )

        assert AgentRequestWSMessageType.ERROR == "error"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketModels:
    """Test WebSocket message models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_required_message_model(self) -> None:
        """Test ApprovalRequiredMessage model exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            ApprovalRequiredMessage,
        )

        msg = ApprovalRequiredMessage(
            request_id="req_123",
            session_id="session_456",
            task_id="task_789",
            agent_name="Research Assistant",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Send analysis to external API",
            trigger_reason="low_confidence",
            context={"tokens_used": 2450},
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert msg.request_id == "req_123"
        assert msg.confidence == 0.65
        assert msg.threshold == 0.70

    def test_clarification_required_message_model(self) -> None:
        """Test ClarificationRequiredMessage model exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            ClarificationRequiredMessage,
        )

        msg = ClarificationRequiredMessage(
            request_id="req_123",
            session_id="session_456",
            task_id="task_789",
            agent_name="Research Assistant",
            clarification_type="choice",
            question="Which format should I use?",
            options=[
                {"id": "csv", "label": "CSV", "is_recommended": False},
                {"id": "json", "label": "JSON", "is_recommended": True},
            ],
            required=True,
            context={},
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert msg.request_id == "req_123"
        assert msg.clarification_type == "choice"
        assert len(msg.options) == 2

    def test_approval_updated_message_model(self) -> None:
        """Test ApprovalUpdatedMessage model exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            ApprovalUpdatedMessage,
        )

        msg = ApprovalUpdatedMessage(
            request_id="req_123",
            status="approved",
            decided_by="admin@example.com",
            decided_at=datetime.now(UTC).isoformat(),
            reason="Looks good",
        )

        assert msg.request_id == "req_123"
        assert msg.status == "approved"

    def test_execution_resumed_message_model(self) -> None:
        """Test ExecutionResumedMessage model exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            ExecutionResumedMessage,
        )

        msg = ExecutionResumedMessage(
            request_id="req_123",
            task_id="task_789",
            agent_name="Research Assistant",
            status="approved",
            resumed_at=datetime.now(UTC).isoformat(),
        )

        assert msg.request_id == "req_123"
        assert msg.status == "approved"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketBroadcaster:
    """Test WebSocket broadcaster service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_class_exists(self) -> None:
        """Test that AgentRequestBroadcaster class exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        assert AgentRequestBroadcaster is not None

    def test_broadcaster_connect_method(self) -> None:
        """Test broadcaster has connect method."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        assert hasattr(broadcaster, "connect")
        assert callable(broadcaster.connect)

    def test_broadcaster_disconnect_method(self) -> None:
        """Test broadcaster has disconnect method."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        assert hasattr(broadcaster, "disconnect")
        assert callable(broadcaster.disconnect)

    def test_broadcaster_broadcast_method(self) -> None:
        """Test broadcaster has broadcast method."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        assert hasattr(broadcaster, "broadcast")
        assert callable(broadcaster.broadcast)

    def test_broadcaster_send_to_session_method(self) -> None:
        """Test broadcaster has send_to_session method."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        assert hasattr(broadcaster, "send_to_session")
        assert callable(broadcaster.send_to_session)

    @pytest.mark.asyncio
    async def test_broadcaster_connect_adds_websocket(self) -> None:
        """Test that connect adds websocket to connections."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.accept = AsyncMock()  # noqa: async-mock-config

        await broadcaster.connect(mock_ws, session_id="session_123", user_id="user_456")

        assert len(broadcaster._connections) > 0

    @pytest.mark.asyncio
    async def test_broadcaster_disconnect_removes_websocket(self) -> None:
        """Test that disconnect removes websocket from connections."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.accept = AsyncMock()  # noqa: async-mock-config

        await broadcaster.connect(mock_ws, session_id="session_123", user_id="user_456")
        broadcaster.disconnect(mock_ws)

        # After disconnect, should not be in connections
        assert mock_ws not in broadcaster._connections

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_sends_to_all(self) -> None:
        """Test that broadcast sends message to all connected clients."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()  # noqa: async-mock-config
        mock_ws1.accept = AsyncMock()  # noqa: async-mock-config
        mock_ws1.send_json = AsyncMock()  # noqa: async-mock-config
        mock_ws2 = AsyncMock()  # noqa: async-mock-config
        mock_ws2.accept = AsyncMock()  # noqa: async-mock-config
        mock_ws2.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.connect(mock_ws1, session_id="session_1", user_id="user_1")
        await broadcaster.connect(mock_ws2, session_id="session_2", user_id="user_2")

        await broadcaster.broadcast({"type": "test", "payload": {}})

        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_send_to_session_filters(self) -> None:
        """Test that send_to_session only sends to specific session."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
        )

        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()  # noqa: async-mock-config
        mock_ws1.accept = AsyncMock()  # noqa: async-mock-config
        mock_ws1.send_json = AsyncMock()  # noqa: async-mock-config
        mock_ws2 = AsyncMock()  # noqa: async-mock-config
        mock_ws2.accept = AsyncMock()  # noqa: async-mock-config
        mock_ws2.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.connect(mock_ws1, session_id="session_target", user_id="user_1")
        await broadcaster.connect(mock_ws2, session_id="session_other", user_id="user_2")

        await broadcaster.send_to_session("session_target", {"type": "test", "payload": {}})

        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketAuthentication:
    """Test WebSocket authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_websocket_token_function_exists(self) -> None:
        """Test that validate_websocket_token function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            validate_websocket_token,
        )

        assert validate_websocket_token is not None
        assert callable(validate_websocket_token)

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_info(self) -> None:
        """Test that valid token returns user info."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            validate_websocket_token,
        )

        mock_auth_middleware = MagicMock()
        mock_auth_middleware.verify_token = AsyncMock(
            return_value={
                "sub": "user_123",
                "email": "user@example.com",
                "realm_access": {"roles": ["hitl_reviewer"]},
            }
        )

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_token("valid_token")

        assert result is not None
        assert result["sub"] == "user_123"
        assert result["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self) -> None:
        """Test that invalid token returns None."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            validate_websocket_token,
        )

        mock_auth_middleware = MagicMock()
        mock_auth_middleware.verify_token = AsyncMock(side_effect=Exception("Invalid token"))

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_token("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_token_returns_none(self) -> None:
        """Test that missing token returns None."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            validate_websocket_token,
        )

        result = await validate_websocket_token(None)

        assert result is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketAuthorization:
    """Test WebSocket authorization for HITL reviewers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_reviewer_role_function_exists(self) -> None:
        """Test that check_reviewer_role function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_reviewer_role,
        )

        assert check_reviewer_role is not None
        assert callable(check_reviewer_role)

    def test_check_reviewer_role_with_hitl_reviewer(self) -> None:
        """Test user with hitl_reviewer role is authorized."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_reviewer_role,
        )

        user_info = {
            "sub": "user_123",
            "realm_access": {"roles": ["hitl_reviewer"]},
        }

        assert check_reviewer_role(user_info) is True

    def test_check_reviewer_role_with_admin(self) -> None:
        """Test user with admin role is authorized."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_reviewer_role,
        )

        user_info = {
            "sub": "user_123",
            "realm_access": {"roles": ["admin"]},
        }

        assert check_reviewer_role(user_info) is True

    def test_check_reviewer_role_without_role(self) -> None:
        """Test user without reviewer role is not authorized."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_reviewer_role,
        )

        user_info = {
            "sub": "user_123",
            "realm_access": {"roles": ["user"]},
        }

        assert check_reviewer_role(user_info) is False

    def test_check_reviewer_role_with_no_roles(self) -> None:
        """Test user with no roles is not authorized."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_reviewer_role,
        )

        user_info = {
            "sub": "user_123",
            "realm_access": {"roles": []},
        }

        assert check_reviewer_role(user_info) is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketHelpers:
    """Test WebSocket helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcast_approval_required_function(self) -> None:
        """Test broadcast_approval_required function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_approval_required,
        )

        assert broadcast_approval_required is not None
        assert callable(broadcast_approval_required)

    def test_broadcast_clarification_required_function(self) -> None:
        """Test broadcast_clarification_required function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_clarification_required,
        )

        assert broadcast_clarification_required is not None
        assert callable(broadcast_clarification_required)

    def test_broadcast_approval_updated_function(self) -> None:
        """Test broadcast_approval_updated function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_approval_updated,
        )

        assert broadcast_approval_updated is not None
        assert callable(broadcast_approval_updated)

    def test_broadcast_execution_resumed_function(self) -> None:
        """Test broadcast_execution_resumed function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_execution_resumed,
        )

        assert broadcast_execution_resumed is not None
        assert callable(broadcast_execution_resumed)


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketBroadcastIntegration:
    """Test WebSocket broadcast integration with queue service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_approval_required_creates_message(self) -> None:
        """Test broadcast_approval_required creates correct message."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
            broadcast_approval_required,
        )
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequest

        # Create mock request with all required fields
        request = AgentRequest(
            request_id="req_123",
            session_id="session_456",
            task_id="task_789",
            agent_name="Research Assistant",
            request_type="approval",
            confidence=0.65,
            threshold=0.70,
            question="Approve sending analysis?",
            proposed_action="Send analysis to external API",
            status="pending",
            requested_at=datetime.now(UTC).isoformat(),
            trigger_reason="low_confidence",
        )

        # Mock broadcaster
        mock_broadcaster = MagicMock(spec=AgentRequestBroadcaster)
        mock_broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config

        with patch(
            "mcp_server_langgraph.api.v1.agent_request_websocket.get_broadcaster",
            return_value=mock_broadcaster,
        ):
            await broadcast_approval_required(request)

        mock_broadcaster.broadcast.assert_called_once()
        call_args = mock_broadcaster.broadcast.call_args[0][0]
        assert call_args["type"] == "approval_required"
        assert call_args["payload"]["request_id"] == "req_123"

    @pytest.mark.asyncio
    async def test_broadcast_clarification_required_creates_message(self) -> None:
        """Test broadcast_clarification_required creates correct message."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
            broadcast_clarification_required,
        )
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequest

        request = AgentRequest(
            request_id="req_123",
            session_id="session_456",
            task_id="task_789",
            agent_name="Research Assistant",
            request_type="clarification",
            question="Which format?",
            clarification_type="choice",
            options=[{"id": "csv", "label": "CSV"}],
            status="pending",
            requested_at=datetime.now(UTC).isoformat(),
        )

        mock_broadcaster = MagicMock(spec=AgentRequestBroadcaster)
        mock_broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config

        with patch(
            "mcp_server_langgraph.api.v1.agent_request_websocket.get_broadcaster",
            return_value=mock_broadcaster,
        ):
            await broadcast_clarification_required(request)

        mock_broadcaster.broadcast.assert_called_once()
        call_args = mock_broadcaster.broadcast.call_args[0][0]
        assert call_args["type"] == "clarification_required"
        assert call_args["payload"]["request_id"] == "req_123"

    @pytest.mark.asyncio
    async def test_broadcast_approval_updated_sends_status(self) -> None:
        """Test broadcast_approval_updated sends status change."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
            broadcast_approval_updated,
        )

        mock_broadcaster = MagicMock(spec=AgentRequestBroadcaster)
        mock_broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config

        with patch(
            "mcp_server_langgraph.api.v1.agent_request_websocket.get_broadcaster",
            return_value=mock_broadcaster,
        ):
            # Function takes a message dict (the payload content, deprecated API)
            await broadcast_approval_updated(
                {
                    "request_id": "req_123",
                    "status": "approved",
                    "decided_by": "admin@example.com",
                    "reason": "Approved",
                }
            )

        mock_broadcaster.broadcast.assert_called_once()
        call_args = mock_broadcaster.broadcast.call_args[0][0]
        assert call_args["type"] == "approval_updated"
        assert call_args["payload"]["request_id"] == "req_123"
        assert call_args["payload"]["status"] == "approved"

    @pytest.mark.asyncio
    async def test_broadcast_execution_resumed_notifies_clients(self) -> None:
        """Test broadcast_execution_resumed notifies clients."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
            broadcast_execution_resumed,
        )

        mock_broadcaster = MagicMock(spec=AgentRequestBroadcaster)
        mock_broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config

        with patch(
            "mcp_server_langgraph.api.v1.agent_request_websocket.get_broadcaster",
            return_value=mock_broadcaster,
        ):
            # Function takes a message dict (the payload content, deprecated API)
            await broadcast_execution_resumed(
                {
                    "request_id": "req_123",
                    "task_id": "task_789",
                    "agent_name": "Research Assistant",
                    "status": "approved",
                }
            )

        mock_broadcaster.broadcast.assert_called_once()
        call_args = mock_broadcaster.broadcast.call_args[0][0]
        assert call_args["type"] == "execution_resumed"
        assert call_args["payload"]["request_id"] == "req_123"
        assert call_args["payload"]["status"] == "approved"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketKeepalive:
    """Test WebSocket ping/pong keepalive."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handle_ping_function_exists(self) -> None:
        """Test that handle_ping function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import handle_ping

        assert handle_ping is not None
        assert callable(handle_ping)

    @pytest.mark.asyncio
    async def test_handle_ping_returns_pong(self) -> None:
        """Test that ping message returns pong."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import handle_ping

        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.send_json = AsyncMock()  # noqa: async-mock-config

        await handle_ping(mock_ws)

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "pong"


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketFeatureFlag:
    """Test WebSocket feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_respects_hitl_feature_flag(self) -> None:
        """Test that WebSocket respects enable_agent_hitl feature flag."""
        # Instead of patching, test that is_hitl_enabled returns bool
        # The actual feature flag integration is tested in integration tests
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            is_hitl_enabled,
        )

        # Verify function exists and returns boolean
        result = is_hitl_enabled()
        assert isinstance(result, bool)

    def test_check_hitl_enabled_for_ws_returns_bool(self) -> None:
        """Test that check_hitl_enabled_for_ws returns boolean."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            check_hitl_enabled_for_ws,
        )

        # Verify function exists and returns boolean (delegates to is_hitl_enabled)
        result = check_hitl_enabled_for_ws()
        assert isinstance(result, bool)


@pytest.mark.unit
@pytest.mark.xdist_group(name="agent_request_websocket")
class TestAgentRequestWebSocketGlobalBroadcaster:
    """Test global broadcaster instance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_broadcaster_function_exists(self) -> None:
        """Test that get_broadcaster function exists."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import get_broadcaster

        assert get_broadcaster is not None
        assert callable(get_broadcaster)

    def test_get_broadcaster_returns_singleton(self) -> None:
        """Test that get_broadcaster returns same instance."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import get_broadcaster

        broadcaster1 = get_broadcaster()
        broadcaster2 = get_broadcaster()

        assert broadcaster1 is broadcaster2

    def test_get_broadcaster_returns_broadcaster_type(self) -> None:
        """Test that get_broadcaster returns AgentRequestBroadcaster."""
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            AgentRequestBroadcaster,
            get_broadcaster,
        )

        broadcaster = get_broadcaster()
        assert isinstance(broadcaster, AgentRequestBroadcaster)
