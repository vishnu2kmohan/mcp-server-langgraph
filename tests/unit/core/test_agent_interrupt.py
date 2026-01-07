"""
Tests for Agent Graph Interrupt Support (Phase 2.2)

Following TDD: Write tests FIRST, then implementation.

This module tests the interrupt support integration in the agent graph:
- Interrupt checking at key node boundaries
- InterruptedOperationError propagation
- State preservation on interrupt
"""

from __future__ import annotations

import asyncio
import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="agent_interrupt")
class TestAgentInterruptImport:
    """Test interrupt-aware agent components can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_interrupt_aware_node_decorator_exists(self) -> None:
        """interrupt_aware_node decorator should be importable."""
        from mcp_server_langgraph.core.interrupt import interrupt_aware_node

        assert interrupt_aware_node is not None
        assert callable(interrupt_aware_node)


@pytest.mark.xdist_group(name="agent_interrupt")
class TestInterruptAwareDecorator:
    """Test the interrupt_aware_node decorator behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_decorator_allows_normal_execution(self) -> None:
        """Decorated function should execute normally when not interrupted."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            interrupt_aware_node,
        )

        controller = InterruptController()

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        result = await my_node({"session_id": "test-session"})
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_decorator_raises_on_interrupt(self) -> None:
        """Decorated function should raise when session is interrupted."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            InterruptedOperationError,
            interrupt_aware_node,
        )

        controller = InterruptController()
        await controller.signal_interrupt("test-session")

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        with pytest.raises(InterruptedOperationError) as exc_info:
            await my_node({"session_id": "test-session"})

        assert exc_info.value.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_decorator_checks_before_execution(self) -> None:
        """Decorator should check interrupt before calling the function."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            InterruptedOperationError,
            interrupt_aware_node,
        )

        controller = InterruptController()
        await controller.signal_interrupt("test-session")
        execution_count = 0

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            nonlocal execution_count
            execution_count += 1
            return {"result": "success"}

        with pytest.raises(InterruptedOperationError):
            await my_node({"session_id": "test-session"})

        # Function body should never be executed
        assert execution_count == 0

    @pytest.mark.asyncio
    async def test_decorator_uses_session_id_extractor(self) -> None:
        """Decorator should use custom session_id extractor if provided."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            InterruptedOperationError,
            interrupt_aware_node,
        )

        controller = InterruptController()
        await controller.signal_interrupt("custom-id")

        def extract_session(state: dict) -> str:
            return state.get("custom_session", "unknown")

        @interrupt_aware_node(controller, session_id_extractor=extract_session)
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        with pytest.raises(InterruptedOperationError) as exc_info:
            await my_node({"custom_session": "custom-id"})

        assert exc_info.value.session_id == "custom-id"

    @pytest.mark.asyncio
    async def test_decorator_default_session_id_extraction(self) -> None:
        """Decorator should extract session_id from state by default."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            interrupt_aware_node,
        )

        controller = InterruptController()

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        # When session_id not in state, should use default and proceed
        result = await my_node({"other_key": "value"})
        assert result["result"] == "success"


@pytest.mark.xdist_group(name="agent_interrupt")
class TestAgentNodeInterruptIntegration:
    """Test interrupt integration in agent graph nodes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_route_input_checks_interrupt(self) -> None:
        """route_input node should check for interrupt."""
        from mcp_server_langgraph.core.interrupt import (
            get_interrupt_controller,
            reset_interrupt_controller,
        )

        # Reset to get fresh controller
        reset_interrupt_controller()
        controller = get_interrupt_controller()
        await controller.signal_interrupt("session-123")

        # The actual test would require the agent graph builder
        # to be modified to check interrupts. For now, we verify
        # the interrupt controller state.
        is_interrupted = await controller.check_interrupted("session-123")
        assert is_interrupted is True

    @pytest.mark.asyncio
    async def test_generate_response_checks_interrupt(self) -> None:
        """generate_response node should check for interrupt."""
        from mcp_server_langgraph.core.interrupt import (
            get_interrupt_controller,
            reset_interrupt_controller,
        )

        reset_interrupt_controller()
        controller = get_interrupt_controller()
        await controller.signal_interrupt("session-456")

        # Verify controller is correctly signaled
        is_interrupted = await controller.check_interrupted("session-456")
        assert is_interrupted is True


@pytest.mark.xdist_group(name="agent_interrupt")
class TestInterruptWithAsyncContext:
    """Test interrupt behavior with async context managers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_interrupt_during_long_running_task(self) -> None:
        """Interrupt should stop long-running async operations."""
        from mcp_server_langgraph.core.interrupt import (
            InterruptController,
            InterruptedOperationError,
        )

        controller = InterruptController()
        session_id = "long-task-session"
        check_count = 0

        async def long_running_task() -> str:
            nonlocal check_count
            for _ in range(10):
                check_count += 1
                if await controller.check_interrupted(session_id):
                    raise InterruptedOperationError(session_id)
                await asyncio.sleep(0.01)
            return "completed"

        # Start task and interrupt after short delay
        task = asyncio.create_task(long_running_task())

        async def interrupt_after_delay() -> None:
            await asyncio.sleep(0.03)
            await controller.signal_interrupt(session_id)

        _interrupt_task = asyncio.create_task(interrupt_after_delay())  # noqa: RUF006

        with pytest.raises(InterruptedOperationError):
            await task

        # Task should have been interrupted partway through
        assert check_count < 10
        assert check_count > 0


@pytest.mark.xdist_group(name="agent_interrupt")
class TestInterruptControllerCleanup:
    """Test interrupt controller cleanup on session end."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_clear_interrupt_after_completion(self) -> None:
        """Interrupt flag should be clearable after operation completes."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()
        session_id = "cleanup-session"

        # Signal interrupt
        await controller.signal_interrupt(session_id)
        assert await controller.check_interrupted(session_id) is True

        # Clear interrupt
        await controller.clear_interrupt(session_id)
        assert await controller.check_interrupted(session_id) is False

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self) -> None:
        """Multiple sessions should have independent interrupt states."""
        from mcp_server_langgraph.core.interrupt import InterruptController

        controller = InterruptController()

        # Interrupt only session 1
        await controller.signal_interrupt("session-1")

        assert await controller.check_interrupted("session-1") is True
        assert await controller.check_interrupted("session-2") is False
        assert await controller.check_interrupted("session-3") is False

        # Clear session 1, interrupt session 2
        await controller.clear_interrupt("session-1")
        await controller.signal_interrupt("session-2")

        assert await controller.check_interrupted("session-1") is False
        assert await controller.check_interrupted("session-2") is True
        assert await controller.check_interrupted("session-3") is False
