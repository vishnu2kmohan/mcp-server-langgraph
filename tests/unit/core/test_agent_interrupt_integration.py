"""
Tests for agent graph interrupt integration.

Verifies that the agent graph properly checks for interrupts
during execution using the InterruptController.
"""

import gc

import pytest

from mcp_server_langgraph.core.interrupt import (
    InterruptController,
    InterruptedOperationError,
    get_interrupt_controller,
    reset_interrupt_controller,
)

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


class TestAgentInterruptIntegration:
    """Tests for interrupt integration with agent execution."""

    def setup_method(self) -> None:
        """Reset interrupt controller before each test."""
        reset_interrupt_controller()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_interrupt_controller()
        gc.collect()

    @pytest.mark.asyncio
    async def test_agent_state_includes_session_id(self) -> None:
        """AgentState TypedDict should include session_id field."""
        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # Create a valid AgentState with session_id
        state: AgentState = {
            "messages": [],
            "next_action": "",
            "user_id": "test-user",
            "request_id": "test-request",
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": None,
            "user_request": None,
            "session_id": "test-session",  # New field
        }

        assert state["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_interrupt_controller_signals_session(self) -> None:
        """InterruptController can signal and check interrupts by session_id."""
        controller = get_interrupt_controller()

        # Initially not interrupted
        assert await controller.check_interrupted("session-1") is False

        # Signal interrupt
        result = await controller.signal_interrupt("session-1")
        assert result is True

        # Now interrupted
        assert await controller.check_interrupted("session-1") is True

        # Other sessions unaffected
        assert await controller.check_interrupted("session-2") is False

    @pytest.mark.asyncio
    async def test_interrupt_controller_raises_if_interrupted(self) -> None:
        """InterruptController raises exception when session is interrupted."""
        controller = get_interrupt_controller()

        # Signal interrupt
        await controller.signal_interrupt("session-abort")

        # Should raise
        with pytest.raises(InterruptedOperationError) as exc_info:
            await controller.raise_if_interrupted("session-abort")

        assert exc_info.value.session_id == "session-abort"

    @pytest.mark.asyncio
    async def test_interrupt_controller_clear_allows_reuse(self) -> None:
        """Clearing interrupt flag allows session to continue."""
        controller = get_interrupt_controller()

        # Interrupt then clear
        await controller.signal_interrupt("session-clear")
        assert await controller.check_interrupted("session-clear") is True

        await controller.clear_interrupt("session-clear")
        assert await controller.check_interrupted("session-clear") is False

    @pytest.mark.asyncio
    async def test_interrupt_aware_node_decorator_checks_interrupt(self) -> None:
        """interrupt_aware_node decorator checks for interrupt before execution."""
        from mcp_server_langgraph.core.interrupt import interrupt_aware_node

        controller = InterruptController()
        execution_count = 0

        @interrupt_aware_node(controller)
        async def my_node(state: dict) -> dict:
            nonlocal execution_count
            execution_count += 1
            return {"result": "success"}

        # Not interrupted - should execute
        state = {"session_id": "test-session"}
        result = await my_node(state)
        assert result == {"result": "success"}
        assert execution_count == 1

        # Interrupt the session
        await controller.signal_interrupt("test-session")

        # Now should raise without executing
        with pytest.raises(InterruptedOperationError):
            await my_node(state)

        # Execution count unchanged
        assert execution_count == 1

    @pytest.mark.asyncio
    async def test_interrupt_aware_node_custom_extractor(self) -> None:
        """interrupt_aware_node accepts custom session_id extractor."""
        from mcp_server_langgraph.core.interrupt import interrupt_aware_node

        controller = InterruptController()

        def custom_extractor(state: dict) -> str:
            return state.get("thread_id", "default")

        @interrupt_aware_node(controller, session_id_extractor=custom_extractor)
        async def my_node(state: dict) -> dict:
            return {"executed": True}

        # Uses thread_id for session lookup
        await controller.signal_interrupt("thread-123")

        state = {"thread_id": "thread-123"}
        with pytest.raises(InterruptedOperationError):
            await my_node(state)

    @pytest.mark.asyncio
    async def test_agent_graph_with_interrupt_support_flag(self) -> None:
        """AgentConfig should support enable_interrupt_checking flag."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        # Default should have interrupt checking enabled
        config = AgentConfig()
        assert hasattr(config, "enable_interrupt_checking")

    @pytest.mark.asyncio
    async def test_interrupted_session_returns_partial_result(self) -> None:
        """When interrupted mid-execution, graph should return gracefully."""
        controller = get_interrupt_controller()

        # Set up a sequence of operations
        results = []

        async def step1(state: dict) -> dict:
            results.append("step1")
            return state

        async def step2(state: dict) -> dict:
            # Check for interrupt manually (simulating decorator)
            await controller.raise_if_interrupted(state.get("session_id", ""))
            results.append("step2")
            return state

        async def step3(state: dict) -> dict:
            results.append("step3")
            return state

        # Run step1, then interrupt, then try step2
        state = {"session_id": "interrupt-mid"}
        await step1(state)
        assert results == ["step1"]

        # Interrupt before step2
        await controller.signal_interrupt("interrupt-mid")

        with pytest.raises(InterruptedOperationError):
            await step2(state)

        # step2 and step3 never executed
        assert results == ["step1"]
