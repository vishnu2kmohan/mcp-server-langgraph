"""
Tests for MCP Interrupt Handler (Phase 2.3)

Following TDD: Write tests FIRST, then implementation.

This module tests the interrupt handler for MCP server:
- Signal interrupt for a session
- Check interrupt status
- Clear interrupt for a session
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="interrupt_handler")
class TestInterruptHandlerImport:
    """Test InterruptHandler can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_interrupt_handler_importable(self) -> None:
        """InterruptHandler should be importable from mcp.handlers."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        assert InterruptHandler is not None

    def test_interrupt_input_model_importable(self) -> None:
        """InterruptInput should be importable from mcp.models."""
        from mcp_server_langgraph.mcp.models import InterruptInput

        assert InterruptInput is not None


@pytest.mark.xdist_group(name="interrupt_handler")
class TestInterruptHandlerSignal:
    """Test signaling interrupt via handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_signal_interrupt_succeeds(self) -> None:
        """Signal interrupt should return success for valid session."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        # Create mock dependencies
        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)

        # Create mock span
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        result = await handler.handle(
            arguments={"session_id": "test-session", "action": "signal"},
            span=mock_span,
            user_id="test-user",
        )

        assert len(result) == 1
        assert "success" in result[0].text.lower() or "interrupted" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_signal_interrupt_requires_session_id(self) -> None:
        """Signal interrupt should require session_id."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        with pytest.raises(ValueError):
            await handler.handle(
                arguments={"action": "signal"},  # Missing session_id
                span=mock_span,
                user_id="test-user",
            )


@pytest.mark.xdist_group(name="interrupt_handler")
class TestInterruptHandlerCheck:
    """Test checking interrupt status via handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_interrupt_returns_status(self) -> None:
        """Check interrupt should return current status."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        result = await handler.handle(
            arguments={"session_id": "test-session", "action": "check"},
            span=mock_span,
            user_id="test-user",
        )

        assert len(result) == 1
        # Result should indicate status (interrupted: true/false)
        assert "interrupted" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_after_signal_returns_true(self) -> None:
        """Check should return true after signal."""
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        reset_interrupt_controller()
        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        # First signal
        await handler.handle(
            arguments={"session_id": "signal-check-session", "action": "signal"},
            span=mock_span,
            user_id="test-user",
        )

        # Then check
        result = await handler.handle(
            arguments={"session_id": "signal-check-session", "action": "check"},
            span=mock_span,
            user_id="test-user",
        )

        assert "true" in result[0].text.lower()


@pytest.mark.xdist_group(name="interrupt_handler")
class TestInterruptHandlerClear:
    """Test clearing interrupt via handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_clear_interrupt_succeeds(self) -> None:
        """Clear interrupt should succeed."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        result = await handler.handle(
            arguments={"session_id": "test-session", "action": "clear"},
            span=mock_span,
            user_id="test-user",
        )

        assert len(result) == 1
        assert "cleared" in result[0].text.lower() or "success" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_clear_after_signal_resets_status(self) -> None:
        """Clear should reset interrupt status to false."""
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        reset_interrupt_controller()
        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        session_id = "clear-test-session"

        # Signal
        await handler.handle(
            arguments={"session_id": session_id, "action": "signal"},
            span=mock_span,
            user_id="test-user",
        )

        # Clear
        await handler.handle(
            arguments={"session_id": session_id, "action": "clear"},
            span=mock_span,
            user_id="test-user",
        )

        # Check should now be false
        result = await handler.handle(
            arguments={"session_id": session_id, "action": "check"},
            span=mock_span,
            user_id="test-user",
        )

        assert "false" in result[0].text.lower()


@pytest.mark.xdist_group(name="interrupt_handler")
class TestInterruptHandlerValidation:
    """Test input validation for interrupt handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalid_action_raises_error(self) -> None:
        """Invalid action should raise ValueError."""
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        with pytest.raises(ValueError):
            await handler.handle(
                arguments={"session_id": "test-session", "action": "invalid_action"},
                span=mock_span,
                user_id="test-user",
            )

    @pytest.mark.asyncio
    async def test_default_action_is_signal(self) -> None:
        """Default action should be 'signal' when not specified."""
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller
        from mcp_server_langgraph.mcp.handlers.interrupt import InterruptHandler

        reset_interrupt_controller()
        mock_auth = MagicMock()
        mock_auth.check_permission = AsyncMock(return_value=True)

        handler = InterruptHandler(auth=mock_auth)
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        mock_span.get_span_context = MagicMock(return_value=None)

        session_id = "default-action-session"

        # Call without action (should default to signal)
        result = await handler.handle(
            arguments={"session_id": session_id},
            span=mock_span,
            user_id="test-user",
        )

        assert "interrupted" in result[0].text.lower() or "success" in result[0].text.lower()

        # Verify the session was actually interrupted by checking
        check_result = await handler.handle(
            arguments={"session_id": session_id, "action": "check"},
            span=mock_span,
            user_id="test-user",
        )

        assert "true" in check_result[0].text.lower()
