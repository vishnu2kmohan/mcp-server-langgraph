"""
TDD Tests for Handoff Pattern (ADR-0081)

These tests verify the Handoff pattern for multi-agent control transfer.
Written FIRST before implementation (RED phase) per TDD methodology.

Reference: ADR-0081 Handoff Pattern for Multi-Agent
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest



pytestmark = pytest.mark.unit

@pytest.mark.xdist_group(name="handoff")
class TestHandoffClass:
    """Test suite for Handoff class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_handoff_has_target_agent(self):
        """GIVEN a Handoff
        WHEN created with target agent
        THEN target_agent is accessible"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="refund_agent")

        assert handoff.target_agent == "refund_agent"

    @pytest.mark.unit
    def test_handoff_has_optional_context_filter(self):
        """GIVEN a Handoff
        WHEN created with context filter
        THEN context_filter is accessible"""
        from mcp_server_langgraph.agents.handoff import Handoff

        def my_filter(messages: list) -> list:
            return messages[-5:]

        handoff = Handoff(
            target_agent="expert_agent",
            context_filter=my_filter,
        )

        assert handoff.context_filter is my_filter

    @pytest.mark.unit
    def test_handoff_context_filter_is_optional(self):
        """GIVEN a Handoff
        WHEN created without context filter
        THEN context_filter is None"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="other_agent")

        assert handoff.context_filter is None

    @pytest.mark.unit
    def test_handoff_has_optional_on_handoff_callback(self):
        """GIVEN a Handoff
        WHEN created with on_handoff callback
        THEN on_handoff is accessible"""
        from mcp_server_langgraph.agents.handoff import Handoff

        def log_handoff(context):
            pass

        handoff = Handoff(
            target_agent="support_agent",
            on_handoff=log_handoff,
        )

        assert handoff.on_handoff is log_handoff

    @pytest.mark.unit
    def test_handoff_has_optional_input_data(self):
        """GIVEN a Handoff
        WHEN created with input data
        THEN input_data is accessible"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="analytics_agent",
            input_data={"query": "summarize trends"},
        )

        assert handoff.input_data == {"query": "summarize trends"}

    @pytest.mark.unit
    def test_handoff_has_optional_description(self):
        """GIVEN a Handoff
        WHEN created with description
        THEN description is accessible"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="expert_agent",
            description="Transfer to expert for complex analysis",
        )

        assert handoff.description == "Transfer to expert for complex analysis"


@pytest.mark.xdist_group(name="handoff")
class TestHandoffAsTool:
    """Test suite for Handoff.as_tool() method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_handoff_as_tool_returns_tool(self):
        """GIVEN a Handoff
        WHEN as_tool is called
        THEN it returns a BaseTool-compatible object"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="other_agent")
        tool = handoff.as_tool()

        assert tool is not None
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")

    @pytest.mark.unit
    def test_handoff_as_tool_name_includes_target(self):
        """GIVEN a Handoff
        WHEN as_tool is called
        THEN the tool name includes target agent"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="refund_agent")
        tool = handoff.as_tool()

        assert "refund_agent" in tool.name

    @pytest.mark.unit
    def test_handoff_as_tool_uses_description(self):
        """GIVEN a Handoff with description
        WHEN as_tool is called
        THEN the tool uses the description"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="expert_agent",
            description="Transfer to expert for complex issues",
        )
        tool = handoff.as_tool()

        assert "Transfer to expert" in tool.description


@pytest.mark.xdist_group(name="handoff")
class TestContextFilter:
    """Test suite for context filter implementations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_keep_last_n_filter(self):
        """GIVEN KeepLastNFilter with n=3
        WHEN filtering 5 messages
        THEN returns last 3 messages"""
        from mcp_server_langgraph.agents.context_filter import KeepLastNFilter

        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
            {"role": "assistant", "content": "msg4"},
            {"role": "user", "content": "msg5"},
        ]

        filter_obj = KeepLastNFilter(n=3)
        filtered = filter_obj.filter(messages)

        assert len(filtered) == 3
        assert filtered[0]["content"] == "msg3"
        assert filtered[-1]["content"] == "msg5"

    @pytest.mark.unit
    def test_remove_tool_calls_filter(self):
        """GIVEN RemoveToolCallsFilter
        WHEN filtering messages with tool calls
        THEN removes tool call messages"""
        from mcp_server_langgraph.agents.context_filter import RemoveToolCallsFilter

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "I'll help", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "content": "result", "tool_call_id": "1"},
            {"role": "assistant", "content": "Done"},
        ]

        filter_obj = RemoveToolCallsFilter()
        filtered = filter_obj.filter(messages)

        # Should remove tool_calls and tool messages
        assert len(filtered) == 2
        assert all(m.get("role") != "tool" for m in filtered)
        assert all("tool_calls" not in m for m in filtered)

    @pytest.mark.unit
    def test_summarize_history_filter(self):
        """GIVEN SummarizeHistoryFilter
        WHEN filtering messages
        THEN returns summary message plus recent messages"""
        from mcp_server_langgraph.agents.context_filter import SummarizeHistoryFilter

        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
            {"role": "assistant", "content": "msg4"},
            {"role": "user", "content": "msg5"},
        ]

        filter_obj = SummarizeHistoryFilter(
            keep_recent=2,
            summary_template="Previous context: {count} messages exchanged",
        )
        filtered = filter_obj.filter(messages)

        # Should have summary + last 2 messages
        assert len(filtered) == 3
        assert "Previous context" in filtered[0]["content"]
        assert filtered[-1]["content"] == "msg5"

    @pytest.mark.unit
    def test_chain_filters(self):
        """GIVEN multiple filters
        WHEN chained together
        THEN they compose correctly"""
        from mcp_server_langgraph.agents.context_filter import (
            ChainedFilter,
            KeepLastNFilter,
            RemoveToolCallsFilter,
        )

        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "I'll help", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "content": "result"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
        ]

        chained = ChainedFilter(
            filters=[
                RemoveToolCallsFilter(),
                KeepLastNFilter(n=2),
            ]
        )
        filtered = chained.filter(messages)

        # First removes tool calls (leaves 3), then keeps last 2
        assert len(filtered) == 2


@pytest.mark.xdist_group(name="handoff")
class TestHandoffExecution:
    """Test suite for Handoff execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handoff_execute_returns_handoff_result(self):
        """GIVEN a Handoff
        WHEN execute is called with context
        THEN it returns HandoffResult"""
        from mcp_server_langgraph.agents.handoff import Handoff, HandoffResult

        handoff = Handoff(target_agent="next_agent")

        messages = [{"role": "user", "content": "Hello"}]
        result = await handoff.execute(messages=messages, session_id="sess_123")

        assert isinstance(result, HandoffResult)
        assert result.target_agent == "next_agent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handoff_execute_applies_context_filter(self):
        """GIVEN a Handoff with context filter
        WHEN execute is called
        THEN messages are filtered"""
        from mcp_server_langgraph.agents.context_filter import KeepLastNFilter
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="next_agent",
            context_filter=KeepLastNFilter(n=2),
        )

        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
        ]
        result = await handoff.execute(messages=messages, session_id="sess_123")

        assert len(result.filtered_messages) == 2
        assert result.filtered_messages[0]["content"] == "msg2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handoff_execute_calls_on_handoff_callback(self):
        """GIVEN a Handoff with on_handoff callback
        WHEN execute is called
        THEN callback is invoked"""
        from mcp_server_langgraph.agents.handoff import Handoff, HandoffContext

        callback_called = []

        def on_handoff(ctx: HandoffContext):
            callback_called.append(ctx)

        handoff = Handoff(
            target_agent="next_agent",
            on_handoff=on_handoff,
        )

        messages = [{"role": "user", "content": "Hello"}]
        await handoff.execute(messages=messages, session_id="sess_123")

        assert len(callback_called) == 1
        assert callback_called[0].target_agent == "next_agent"
        assert callback_called[0].session_id == "sess_123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handoff_execute_includes_input_data(self):
        """GIVEN a Handoff with input_data
        WHEN execute is called
        THEN result includes input_data"""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="analysis_agent",
            input_data={"query": "summarize"},
        )

        messages = [{"role": "user", "content": "Hello"}]
        result = await handoff.execute(messages=messages, session_id="sess_123")

        assert result.input_data == {"query": "summarize"}


@pytest.mark.xdist_group(name="handoff")
class TestHandoffResult:
    """Test suite for HandoffResult data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_handoff_result_has_target_agent(self):
        """GIVEN HandoffResult
        WHEN created
        THEN target_agent is accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffResult

        result = HandoffResult(
            target_agent="next_agent",
            filtered_messages=[{"role": "user", "content": "Hi"}],
        )

        assert result.target_agent == "next_agent"

    @pytest.mark.unit
    def test_handoff_result_has_filtered_messages(self):
        """GIVEN HandoffResult
        WHEN created with messages
        THEN filtered_messages is accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffResult

        messages = [{"role": "user", "content": "Hello"}]
        result = HandoffResult(
            target_agent="next_agent",
            filtered_messages=messages,
        )

        assert result.filtered_messages == messages

    @pytest.mark.unit
    def test_handoff_result_has_optional_input_data(self):
        """GIVEN HandoffResult
        WHEN created with input_data
        THEN input_data is accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffResult

        result = HandoffResult(
            target_agent="next_agent",
            filtered_messages=[],
            input_data={"param": "value"},
        )

        assert result.input_data == {"param": "value"}

    @pytest.mark.unit
    def test_handoff_result_has_source_agent(self):
        """GIVEN HandoffResult
        WHEN created with source_agent
        THEN source_agent is accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffResult

        result = HandoffResult(
            target_agent="next_agent",
            filtered_messages=[],
            source_agent="triage_agent",
        )

        assert result.source_agent == "triage_agent"


@pytest.mark.xdist_group(name="handoff")
class TestHandoffContext:
    """Test suite for HandoffContext data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_handoff_context_has_required_fields(self):
        """GIVEN HandoffContext
        WHEN created
        THEN required fields are accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffContext

        context = HandoffContext(
            target_agent="next_agent",
            session_id="sess_123",
            message_count=5,
        )

        assert context.target_agent == "next_agent"
        assert context.session_id == "sess_123"
        assert context.message_count == 5

    @pytest.mark.unit
    def test_handoff_context_has_optional_source_agent(self):
        """GIVEN HandoffContext
        WHEN created with source_agent
        THEN source_agent is accessible"""
        from mcp_server_langgraph.agents.handoff import HandoffContext

        context = HandoffContext(
            target_agent="next_agent",
            session_id="sess_123",
            message_count=5,
            source_agent="triage_agent",
        )

        assert context.source_agent == "triage_agent"


@pytest.mark.xdist_group(name="handoff")
class TestExports:
    """Test suite for module exports."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_handoff_module_exports(self):
        """GIVEN handoff module
        WHEN checking exports
        THEN key classes are exported"""
        from mcp_server_langgraph.agents import handoff

        required_exports = [
            "Handoff",
            "HandoffResult",
            "HandoffContext",
        ]

        for export in required_exports:
            assert export in handoff.__all__, f"{export} not in __all__"
            assert hasattr(handoff, export), f"{export} not accessible"

    @pytest.mark.unit
    def test_context_filter_module_exports(self):
        """GIVEN context_filter module
        WHEN checking exports
        THEN filter classes are exported"""
        from mcp_server_langgraph.agents import context_filter

        required_exports = [
            "KeepLastNFilter",
            "RemoveToolCallsFilter",
            "SummarizeHistoryFilter",
            "ChainedFilter",
        ]

        for export in required_exports:
            assert export in context_filter.__all__, f"{export} not in __all__"
            assert hasattr(context_filter, export), f"{export} not accessible"
