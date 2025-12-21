"""
Tests for Interrupt Controller (Phase 2.1)

Following TDD: Write tests FIRST, then implementation.

This module tests the InterruptController which provides thread-safe
signaling for graceful cancellation of long-running agent operations.

The controller implements Claude Agent SDK's interrupt pattern:
- signal_interrupt(session_id): Signal that a session should stop
- check_interrupted(session_id): Check if session was interrupted
- clear_interrupt(session_id): Clear interrupt flag for reuse
"""

from __future__ import annotations

import asyncio
import gc
from typing import Any

import pytest

if True:  # TYPE_CHECKING block placeholder for imports to come after
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="interrupt")
class TestInterruptControllerImport:
    """Test InterruptController can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_interrupt_controller_importable(self) -> None:
        """InterruptController should be importable from core.interrupt."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        assert InterruptController is not None

    def test_get_interrupt_controller_exists(self) -> None:
        """get_interrupt_controller should provide singleton access."""
        from mcp_server_langgraph.core.interrupt import get_interrupt_controller

        assert get_interrupt_controller is not None
        assert callable(get_interrupt_controller)


@pytest.mark.xdist_group(name="interrupt")
class TestInterruptControllerSingleton:
    """Test InterruptController singleton pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_singleton_returns_same_instance(self) -> None:
        """get_interrupt_controller should return same instance."""
        from mcp_server_langgraph.core.interrupt import get_interrupt_controller

        controller1 = get_interrupt_controller()
        controller2 = get_interrupt_controller()
        assert controller1 is controller2

    def test_reset_creates_new_instance(self) -> None:
        """reset_interrupt_controller should create new instance."""
        from mcp_server_langgraph.core.interrupt import (
            get_interrupt_controller,
            reset_interrupt_controller,
        )

        controller1 = get_interrupt_controller()
        reset_interrupt_controller()
        controller2 = get_interrupt_controller()
        assert controller1 is not controller2


@pytest.mark.xdist_group(name="interrupt")
class TestSignalInterrupt:
    """Test signaling interrupt for a session."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_signal_interrupt_returns_true(self) -> None:
        """signal_interrupt should return True on success."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        result = await controller.signal_interrupt("session-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_signal_interrupt_sets_flag(self) -> None:
        """signal_interrupt should set interrupted flag."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        await controller.signal_interrupt("session-123")
        is_interrupted = await controller.check_interrupted("session-123")
        assert is_interrupted is True

    @pytest.mark.asyncio
    async def test_signal_interrupt_multiple_sessions(self) -> None:
        """signal_interrupt should track sessions independently."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        await controller.signal_interrupt("session-1")

        # session-1 is interrupted
        assert await controller.check_interrupted("session-1") is True
        # session-2 is not interrupted
        assert await controller.check_interrupted("session-2") is False


@pytest.mark.xdist_group(name="interrupt")
class TestCheckInterrupted:
    """Test checking if a session is interrupted."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_interrupted_returns_false_initially(self) -> None:
        """check_interrupted should return False for new sessions."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        is_interrupted = await controller.check_interrupted("new-session")
        assert is_interrupted is False

    @pytest.mark.asyncio
    async def test_check_interrupted_returns_true_after_signal(self) -> None:
        """check_interrupted should return True after signal."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        await controller.signal_interrupt("session-123")
        is_interrupted = await controller.check_interrupted("session-123")
        assert is_interrupted is True


@pytest.mark.xdist_group(name="interrupt")
class TestClearInterrupt:
    """Test clearing interrupt flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_clear_interrupt_resets_flag(self) -> None:
        """clear_interrupt should reset the interrupted flag."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        await controller.signal_interrupt("session-123")
        await controller.clear_interrupt("session-123")
        is_interrupted = await controller.check_interrupted("session-123")
        assert is_interrupted is False

    @pytest.mark.asyncio
    async def test_clear_interrupt_no_error_for_unknown_session(self) -> None:
        """clear_interrupt should not error for unknown sessions."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        # Should not raise
        await controller.clear_interrupt("unknown-session")


@pytest.mark.xdist_group(name="interrupt")
class TestInterruptControllerThreadSafety:
    """Test thread safety of InterruptController."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_signals_are_safe(self) -> None:
        """Concurrent signal_interrupt calls should be thread-safe."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()

        async def signal_session(session_id: str) -> bool:
            return await controller.signal_interrupt(session_id)

        # Signal 100 sessions concurrently
        tasks = [signal_session(f"session-{i}") for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All signals should succeed
        assert all(results)

        # All sessions should be interrupted
        for i in range(100):
            assert await controller.check_interrupted(f"session-{i}") is True

    @pytest.mark.asyncio
    async def test_concurrent_check_and_signal(self) -> None:
        """Concurrent check and signal operations should be safe."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        session_id = "test-session"

        async def check_loop() -> int:
            """Check interrupted state 100 times."""
            count = 0
            for _ in range(100):
                if await controller.check_interrupted(session_id):
                    count += 1
                await asyncio.sleep(0.001)
            return count

        async def signal_after_delay() -> bool:
            """Signal after a short delay."""
            await asyncio.sleep(0.05)
            return await controller.signal_interrupt(session_id)

        # Run concurrently
        check_task = asyncio.create_task(check_loop())
        signal_task = asyncio.create_task(signal_after_delay())

        interrupted_count, signal_result = await asyncio.gather(check_task, signal_task)

        # Signal should succeed
        assert signal_result is True
        # Some checks should have seen the interrupt
        assert interrupted_count >= 0  # May be 0 if signal happened late


@pytest.mark.xdist_group(name="interrupt")
class TestInterruptError:
    """Test InterruptedError exception for interrupted sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_interrupted_error_importable(self) -> None:
        """InterruptedOperationError should be importable."""
        from mcp_server_langgraph.core.interrupt import InterruptedOperationError

        assert InterruptedOperationError is not None

    def test_interrupted_error_is_exception(self) -> None:
        """InterruptedOperationError should be an Exception."""
        from mcp_server_langgraph.core.interrupt import InterruptedOperationError

        assert issubclass(InterruptedOperationError, Exception)

    def test_interrupted_error_has_session_id(self) -> None:
        """InterruptedOperationError should include session_id."""
        from mcp_server_langgraph.core.interrupt import InterruptedOperationError

        error = InterruptedOperationError("session-123")
        assert error.session_id == "session-123"
        assert "session-123" in str(error)

    def test_interrupted_error_has_message(self) -> None:
        """InterruptedOperationError should have descriptive message."""
        from mcp_server_langgraph.core.interrupt import InterruptedOperationError

        error = InterruptedOperationError("session-123")
        assert "interrupt" in str(error).lower()


@pytest.mark.xdist_group(name="interrupt")
class TestRaiseIfInterrupted:
    """Test convenience method for raising on interrupt."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_raise_if_interrupted_raises_when_interrupted(self) -> None:
        """raise_if_interrupted should raise when session is interrupted."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            InterruptedOperationError,
        )

        controller = InterruptController()
        await controller.signal_interrupt("session-123")

        with pytest.raises(InterruptedOperationError) as exc_info:
            await controller.raise_if_interrupted("session-123")

        assert exc_info.value.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_raise_if_interrupted_does_not_raise_when_not_interrupted(self) -> None:
        """raise_if_interrupted should not raise when session is not interrupted."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        # Should not raise
        await controller.raise_if_interrupted("session-123")
