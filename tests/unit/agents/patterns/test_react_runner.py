"""Tests for ReACT execution pattern.

TDD: These tests define the contract for the ReACT runner that wraps
langgraph's create_react_agent for multi-step reasoning+acting.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="react_runner_basic")
class TestReactRunnerBasic:
    """Tests for ReACTRunner basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_react_runner_exists(self) -> None:
        """Test ReACTRunner class exists."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        assert ReACTRunner is not None

    def test_react_runner_has_run_method(self) -> None:
        """Test ReACTRunner has run method."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock())
        assert hasattr(runner, "run")
        assert callable(runner.run)

    def test_react_runner_accepts_model(self) -> None:
        """Test ReACTRunner accepts model parameter."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        runner = ReACTRunner(model=model)
        assert runner.model is model

    def test_react_runner_accepts_tools(self) -> None:
        """Test ReACTRunner accepts tools parameter."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        tools = [MagicMock(), MagicMock()]
        runner = ReACTRunner(model=model, tools=tools)
        assert runner.tools == tools

    def test_react_runner_tools_defaults_empty(self) -> None:
        """Test ReACTRunner tools defaults to empty list."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock())
        assert runner.tools == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="react_runner_execution")
class TestReactRunnerExecution:
    """Tests for ReACTRunner execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        """Test ReACTRunner.run returns a result."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        # Mock the model
        model = MagicMock()
        runner = ReACTRunner(model=model)

        # Mock internal agent execution
        with patch.object(runner, "_execute_agent", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"messages": [MagicMock(content="Result")]}

            result = await runner.run("Test message")

            assert result is not None
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_handles_timeout(self) -> None:
        """Test ReACTRunner.run handles timeout gracefully."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        runner = ReACTRunner(model=model, timeout_seconds=0.1)

        # Mock a slow execution
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)  # noqa: sleep-duration
            return {"messages": []}

        with patch.object(runner, "_execute_agent", side_effect=slow_execute):
            result = await runner.run("Test message")

            assert result is not None
            assert result.get("error") is not None or result.get("timeout") is True

    @pytest.mark.asyncio
    async def test_run_supports_cancellation(self) -> None:
        """Test ReACTRunner.run supports cancellation via event."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        runner = ReACTRunner(model=model)
        cancel_event = asyncio.Event()
        cancel_event.set()  # Set immediately

        result = await runner.run("Test message", cancel_event=cancel_event)

        assert result is not None
        assert result.get("cancelled") is True

    @pytest.mark.asyncio
    async def test_run_with_tools(self) -> None:
        """Test ReACTRunner.run executes with tools."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()

        # Create mock tools
        tool1 = MagicMock()
        tool1.name = "search"
        tool2 = MagicMock()
        tool2.name = "calculator"

        runner = ReACTRunner(model=model, tools=[tool1, tool2])

        with patch.object(runner, "_execute_agent", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"messages": [MagicMock(content="Used tools")]}

            result = await runner.run("Search for something")

            assert result is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="react_runner_config")
class TestReactRunnerConfiguration:
    """Tests for ReACTRunner configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_accepts_max_iterations(self) -> None:
        """Test ReACTRunner accepts max_iterations parameter."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock(), max_iterations=10)
        assert runner.max_iterations == 10

    def test_max_iterations_has_default(self) -> None:
        """Test ReACTRunner max_iterations has sensible default."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock())
        assert runner.max_iterations > 0  # Should have a default

    def test_accepts_timeout_seconds(self) -> None:
        """Test ReACTRunner accepts timeout_seconds parameter."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock(), timeout_seconds=30.0)
        assert runner.timeout_seconds == 30.0

    def test_timeout_has_default(self) -> None:
        """Test ReACTRunner timeout_seconds has sensible default."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        runner = ReACTRunner(model=MagicMock())
        assert runner.timeout_seconds > 0  # Should have a default


@pytest.mark.unit
@pytest.mark.xdist_group(name="react_runner_state")
class TestReactRunnerState:
    """Tests for ReACTRunner state management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_tracks_iterations(self) -> None:
        """Test ReACTRunner tracks iteration count in result."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        runner = ReACTRunner(model=model)

        with patch.object(runner, "_execute_agent", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"messages": [MagicMock(content="Done")]}

            result = await runner.run("Test")

            # Result should include iteration count
            assert "iterations" in result or "steps" in result or result.get("messages") is not None

    @pytest.mark.asyncio
    async def test_run_includes_tool_calls_in_result(self) -> None:
        """Test ReACTRunner includes tool calls in result."""
        from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

        model = MagicMock()
        tool = MagicMock()
        tool.name = "search"
        runner = ReACTRunner(model=model, tools=[tool])

        # Create a mock message with tool calls
        tool_call_msg = MagicMock()
        tool_call_msg.tool_calls = [{"name": "search", "args": {"query": "test"}}]

        with patch.object(runner, "_execute_agent", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"messages": [tool_call_msg, MagicMock(content="Result")]}

            result = await runner.run("Search test")

            assert "messages" in result
