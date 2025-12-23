"""
Tests for HITL Push Notification Integration.

Verifies that push notifications are sent when HITL approval requests are created.
This enables users to be notified even when not actively viewing the application.

TDD: GREEN phase - tests now pass with implemented functions:
- send_hitl_approval_notification
- send_hitl_clarification_notification
- create_approval_push_message
- create_clarification_push_message
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# TDD GREEN phase - functions have been implemented
pytestmark = [
    pytest.mark.unit,
    pytest.mark.hitl,
    pytest.mark.push_notifications,
]


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_push_notifications")
class TestHITLPushNotificationIntegration:
    """Test suite for HITL push notification integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_hitl_approval_notification_exists(self) -> None:
        """GIVEN the agent_request_websocket module
        WHEN importing send_hitl_approval_notification
        THEN the function should exist.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            send_hitl_approval_notification,
        )

        assert callable(send_hitl_approval_notification)

    @pytest.mark.asyncio
    async def test_send_hitl_approval_notification_when_enabled(self) -> None:
        """GIVEN HITL push notifications are enabled
        WHEN an approval request is created
        THEN a push notification should be sent to the user.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            send_hitl_approval_notification,
        )
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        # Create a mock push sender
        mock_push_sender = AsyncMock()
        mock_push_sender.send_to_user = AsyncMock(return_value=1)

        # Create a mock approval request
        request = AgentRequest(
            request_id="approval-push-001",
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            request_type=AgentRequestType.APPROVAL,
            confidence=0.65,
            threshold=0.7,
            proposed_action="Analyze dataset",
            question="Confidence 65% is below threshold 70%. Approve?",
            trigger_reason="low_confidence",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        # Patch feature flag and push sender
        with (
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_push_sender") as mock_get_sender,
        ):
            mock_flags.return_value.enable_agent_hitl_push_notifications = True
            mock_get_sender.return_value = mock_push_sender

            await send_hitl_approval_notification(request, user_id="user-123")

            # Verify push notification was sent
            mock_push_sender.send_to_user.assert_called_once()
            call_args = mock_push_sender.send_to_user.call_args
            assert call_args[0][0] == "user-123"  # user_id

            # Verify message content
            message = call_args[0][1]
            assert "Agent needs approval" in message.title
            assert "65%" in message.title
            assert request.proposed_action in message.body

    @pytest.mark.asyncio
    async def test_send_hitl_approval_notification_when_disabled(self) -> None:
        """GIVEN HITL push notifications are disabled
        WHEN an approval request is created
        THEN no push notification should be sent.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            send_hitl_approval_notification,
        )
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        # Create a mock push sender
        mock_push_sender = AsyncMock()

        # Create a mock approval request
        request = AgentRequest(
            request_id="approval-push-002",
            session_id="session-002",
            task_id="task-002",
            agent_name="Data Analyst",
            request_type=AgentRequestType.APPROVAL,
            confidence=0.55,
            threshold=0.7,
            proposed_action="Delete records",
            question="Approve deletion?",
            trigger_reason="destructive_action",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        # Patch feature flag to disable push notifications
        with (
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_push_sender") as mock_get_sender,
        ):
            mock_flags.return_value.enable_agent_hitl_push_notifications = False
            mock_get_sender.return_value = mock_push_sender

            await send_hitl_approval_notification(request, user_id="user-456")

            # Verify push notification was NOT sent
            mock_push_sender.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_hitl_clarification_notification_exists(self) -> None:
        """GIVEN the agent_request_websocket module
        WHEN importing send_hitl_clarification_notification
        THEN the function should exist.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            send_hitl_clarification_notification,
        )

        assert callable(send_hitl_clarification_notification)

    @pytest.mark.asyncio
    async def test_send_hitl_clarification_notification_sends_message(self) -> None:
        """GIVEN HITL push notifications are enabled
        WHEN a clarification request is created
        THEN a push notification should be sent with the question.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            send_hitl_clarification_notification,
        )
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        # Create a mock push sender
        mock_push_sender = AsyncMock()
        mock_push_sender.send_to_user = AsyncMock(return_value=1)

        # Create a mock clarification request
        request = AgentRequest(
            request_id="clarify-push-001",
            session_id="session-003",
            task_id="task-003",
            agent_name="Code Reviewer",
            request_type=AgentRequestType.CLARIFICATION,
            confidence=0.8,
            threshold=0.7,
            proposed_action=None,
            question="Which file should I focus on?",
            clarification_type="choice",
            trigger_reason="ambiguous_input",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        # Patch feature flag and push sender
        with (
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_push_sender") as mock_get_sender,
        ):
            mock_flags.return_value.enable_agent_hitl_push_notifications = True
            mock_get_sender.return_value = mock_push_sender

            await send_hitl_clarification_notification(request, user_id="user-789")

            # Verify push notification was sent
            mock_push_sender.send_to_user.assert_called_once()
            call_args = mock_push_sender.send_to_user.call_args

            # Verify message content
            message = call_args[0][1]
            assert "Agent has a question" in message.title
            assert request.question in message.body


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_push_notification_message")
class TestHITLPushNotificationMessage:
    """Test suite for HITL push notification message formatting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_approval_push_message_exists(self) -> None:
        """GIVEN the agent_request_websocket module
        WHEN importing create_approval_push_message
        THEN the function should exist.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            create_approval_push_message,
        )

        assert callable(create_approval_push_message)

    @pytest.mark.asyncio
    async def test_create_approval_push_message_format(self) -> None:
        """GIVEN an approval request
        WHEN creating a push message
        THEN it should have correct title, body, and actions.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            create_approval_push_message,
        )
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        request = AgentRequest(
            request_id="format-001",
            session_id="session-format",
            task_id="task-format",
            agent_name="Research Assistant",
            request_type=AgentRequestType.APPROVAL,
            confidence=0.65,
            threshold=0.7,
            proposed_action="Send report to external API",
            question="Approve sending?",
            trigger_reason="external_api",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        message = create_approval_push_message(request)

        # Check title contains confidence percentage
        assert "65%" in message.title
        assert "approval" in message.title.lower()

        # Check body contains proposed action
        assert request.proposed_action in message.body

        # Check tag for notification grouping
        assert message.tag == f"hitl-{request.request_id}"

        # Check actions for approve/reject
        assert message.actions is not None
        action_names = [a["action"] for a in message.actions]
        assert "approve" in action_names
        assert "reject" in action_names

        # Check data payload
        assert message.data is not None
        assert message.data["request_id"] == request.request_id
        assert message.data["type"] == "approval"

    @pytest.mark.asyncio
    async def test_create_clarification_push_message_exists(self) -> None:
        """GIVEN the agent_request_websocket module
        WHEN importing create_clarification_push_message
        THEN the function should exist.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            create_clarification_push_message,
        )

        assert callable(create_clarification_push_message)

    @pytest.mark.asyncio
    async def test_create_clarification_push_message_format(self) -> None:
        """GIVEN a clarification request
        WHEN creating a push message
        THEN it should have correct title and body with question.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            create_clarification_push_message,
        )
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        request = AgentRequest(
            request_id="clarify-format-001",
            session_id="session-clarify",
            task_id="task-clarify",
            agent_name="Data Analyst",
            request_type=AgentRequestType.CLARIFICATION,
            confidence=0.8,
            threshold=0.7,
            proposed_action=None,
            question="Which dataset version should I use?",
            clarification_type="choice",
            trigger_reason="ambiguous_input",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        message = create_clarification_push_message(request)

        # Check title indicates question
        assert "question" in message.title.lower() or "input" in message.title.lower()

        # Check body contains the question
        assert request.question in message.body

        # Check tag for notification grouping
        assert message.tag == f"hitl-{request.request_id}"

        # Check data payload
        assert message.data is not None
        assert message.data["request_id"] == request.request_id
        assert message.data["type"] == "clarification"


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_push_broadcast_integration")
class TestHITLPushBroadcastIntegration:
    """Test suite for HITL push notification integration with broadcast functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_approval_required_sends_push(self) -> None:
        """GIVEN broadcast_approval_required is called
        WHEN push notifications are enabled
        THEN a push notification should also be sent.
        """
        from mcp_server_langgraph.api.v1.agent_request_websocket import (
            broadcast_approval_required,
        )

        # Create a mock request with user context
        request = MagicMock()
        request.request_id = "broadcast-push-001"
        request.session_id = "session-broadcast"
        request.task_id = "task-broadcast"
        request.agent_name = "Test Agent"
        request.confidence = 0.62
        request.threshold = 0.7
        request.proposed_action = "Run analysis"
        request.trigger_reason = "low_confidence"
        request.context = {"user_id": "user-broadcast"}
        request.requested_at = datetime.now(UTC)

        # Patch broadcaster and push notification function
        with (
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.get_broadcaster") as mock_get_broadcaster,
            patch("mcp_server_langgraph.api.v1.agent_request_websocket.send_hitl_approval_notification") as mock_send_push,
        ):
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster
            mock_send_push.return_value = None

            await broadcast_approval_required(request)

            # Verify WebSocket broadcast happened
            mock_broadcaster.broadcast.assert_called_once()

            # Verify push notification was triggered
            mock_send_push.assert_called_once()
            call_args = mock_send_push.call_args
            assert call_args[0][0] == request  # The request object
