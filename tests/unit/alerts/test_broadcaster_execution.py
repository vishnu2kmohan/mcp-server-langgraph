"""
Alert Broadcaster Execution Status Tests.

TDD tests for broadcasting remediation execution results via WebSocket.

Features tested:
- broadcast_execution_result method exists
- Execution result message format
- Broadcast to all subscribers
- Failed connection cleanup

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.alerts,
]


@pytest.mark.xdist_group(name="test_broadcaster_execution")
class TestBroadcasterExecutionExists:
    """Tests for broadcast execution result method existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_broadcaster_class_exists(self) -> None:
        """
        GIVEN the alerts.broadcaster module
        WHEN importing AlertBroadcaster
        THEN should export the class.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        assert AlertBroadcaster is not None

    def test_broadcast_execution_result_method_exists(self) -> None:
        """
        GIVEN an AlertBroadcaster instance
        WHEN checking for broadcast_execution_result method
        THEN should have the method.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        assert hasattr(broadcaster, "broadcast_execution_result")
        assert callable(broadcaster.broadcast_execution_result)


@pytest.mark.xdist_group(name="test_broadcaster_execution")
class TestBroadcastExecutionResult:
    """Tests for broadcasting execution results."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_websocket(self) -> AsyncMock:
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.fixture
    def sample_execution_result(self) -> dict:
        """Create a sample execution result."""
        from mcp_server_langgraph.alerts.executor import ExecutionResult

        return ExecutionResult(
            remediation_id="rem-001",
            success=True,
            exit_code=0,
            stdout="Deployment restarted successfully",
            stderr="",
            executed_at=datetime.now(UTC).isoformat(),
            duration_ms=1500,
            error_message=None,
        )

    @pytest.mark.asyncio
    async def test_broadcast_execution_result_sends_to_subscriber(
        self, mock_websocket: AsyncMock, sample_execution_result
    ) -> None:
        """
        GIVEN a broadcaster with a subscriber
        WHEN broadcasting an execution result
        THEN should send to the subscriber.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        await broadcaster.subscribe(mock_websocket, user_id="admin-1")

        await broadcaster.broadcast_execution_result(sample_execution_result)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "execution_result"
        assert call_args["payload"]["remediation_id"] == "rem-001"
        assert call_args["payload"]["success"] is True

    @pytest.mark.asyncio
    async def test_broadcast_execution_result_no_subscribers(
        self, sample_execution_result
    ) -> None:
        """
        GIVEN a broadcaster with no subscribers
        WHEN broadcasting an execution result
        THEN should complete without error.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()

        # Should not raise
        await broadcaster.broadcast_execution_result(sample_execution_result)

    @pytest.mark.asyncio
    async def test_broadcast_execution_result_failure(
        self, mock_websocket: AsyncMock
    ) -> None:
        """
        GIVEN a failed execution result
        WHEN broadcasting
        THEN should include error details in message.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
        from mcp_server_langgraph.alerts.executor import ExecutionResult

        broadcaster = AlertBroadcaster()
        await broadcaster.subscribe(mock_websocket, user_id="admin-1")

        result = ExecutionResult(
            remediation_id="rem-002",
            success=False,
            exit_code=1,
            stdout="",
            stderr="Error: pod not found",
            executed_at=datetime.now(UTC).isoformat(),
            duration_ms=500,
            error_message="Command failed with exit code 1",
        )

        await broadcaster.broadcast_execution_result(result)

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["payload"]["success"] is False
        assert call_args["payload"]["error_message"] == "Command failed with exit code 1"

    @pytest.mark.asyncio
    async def test_broadcast_execution_removes_failed_connections(
        self, sample_execution_result
    ) -> None:
        """
        GIVEN a broadcaster with a subscriber that fails to receive
        WHEN broadcasting an execution result
        THEN should remove the failed connection.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()

        # Create a mock that raises an exception
        failing_ws = AsyncMock()
        failing_ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        await broadcaster.subscribe(failing_ws, user_id="admin-1")

        assert broadcaster.subscriber_count == 1

        await broadcaster.broadcast_execution_result(sample_execution_result)

        # Failed connection should be removed
        assert broadcaster.subscriber_count == 0


@pytest.mark.xdist_group(name="test_broadcaster_execution")
class TestExecutionResultMessageFormat:
    """Tests for execution result message format."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_result_to_message_exists(self) -> None:
        """
        GIVEN the alerts.broadcaster module
        WHEN importing execution_result_to_message
        THEN should export the function.
        """
        from mcp_server_langgraph.alerts.broadcaster import execution_result_to_message

        assert execution_result_to_message is not None
        assert callable(execution_result_to_message)

    def test_execution_result_to_message_format(self) -> None:
        """
        GIVEN an ExecutionResult
        WHEN converting to message
        THEN should have correct format.
        """
        from mcp_server_langgraph.alerts.broadcaster import execution_result_to_message
        from mcp_server_langgraph.alerts.executor import ExecutionResult

        result = ExecutionResult(
            remediation_id="rem-001",
            success=True,
            exit_code=0,
            stdout="OK",
            stderr="",
            executed_at="2025-12-20T10:00:00Z",
            duration_ms=1000,
            error_message=None,
        )

        message = execution_result_to_message(result)

        assert message["type"] == "execution_result"
        assert "payload" in message
        assert message["payload"]["remediation_id"] == "rem-001"
        assert message["payload"]["success"] is True
        assert message["payload"]["exit_code"] == 0
        assert message["payload"]["stdout"] == "OK"
        assert message["payload"]["duration_ms"] == 1000
