"""
Integration tests for Handoff pattern with Orchestrators (ADR-0081).

Tests handoff execution between agents in orchestrator contexts,
context filtering during handoff, and callback invocation.

TDD: Tests written to verify integration behavior.
"""

import asyncio
import gc
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.agents]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_messages() -> list[dict[str, Any]]:
    """Create sample conversation messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, I need help with a refund."},
        {"role": "assistant", "content": "I can help with that. Let me check your order."},
        {
            "role": "assistant",
            "content": "I found your order.",
            "tool_calls": [{"id": "tc_1", "function": {"name": "get_order"}}],
        },
        {"role": "tool", "content": "Order #12345: $99.99", "tool_call_id": "tc_1"},
        {"role": "assistant", "content": "I see your order. The total was $99.99."},
        {"role": "user", "content": "I want a full refund please."},
        {"role": "assistant", "content": "I'll transfer you to our refund specialist."},
    ]


@pytest.fixture
def mock_triage_agent():
    """Create a mock triage agent for testing handoffs."""
    agent = MagicMock()
    agent.name = "triage_agent"
    agent.description = "Initial triage for customer requests"
    return agent


@pytest.fixture
def mock_refund_agent():
    """Create a mock refund agent that receives handoffs."""
    agent = MagicMock()
    agent.name = "refund_agent"
    agent.description = "Handles refund requests"

    async def process_request(messages: list[dict[str, Any]], **kwargs):
        await asyncio.sleep(0.01)  # Simulate processing
        return {
            "status": "approved",
            "amount": 99.99,
            "message": "Refund approved and processed.",
        }

    agent.process_request = process_request
    return agent


@pytest.fixture
def mock_escalation_agent():
    """Create a mock escalation agent for complex cases."""
    agent = MagicMock()
    agent.name = "escalation_agent"
    agent.description = "Handles complex escalated cases"

    async def process_request(messages: list[dict[str, Any]], **kwargs):
        await asyncio.sleep(0.01)
        return {
            "status": "escalated",
            "priority": "high",
            "assigned_to": "senior_support",
        }

    agent.process_request = process_request
    return agent


# =============================================================================
# Handoff Execution Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_orchestrator_integration")
class TestHandoffOrchestratorIntegration:
    """Integration tests for Handoff with orchestrator contexts."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handoff_executes_with_full_context(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test that handoff passes full conversation context by default."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="refund_agent")

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
        )

        assert result.target_agent == "refund_agent"
        assert len(result.filtered_messages) == len(sample_messages)
        # Verify messages are copied, not referenced
        assert result.filtered_messages is not sample_messages
        assert result.filtered_messages == sample_messages

    @pytest.mark.asyncio
    async def test_handoff_with_keep_last_n_filter(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff with KeepLastNFilter reduces context."""
        from mcp_server_langgraph.agents.context_filter import KeepLastNFilter
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="refund_agent",
            context_filter=KeepLastNFilter(n=3),
        )

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
        )

        assert result.target_agent == "refund_agent"
        assert len(result.filtered_messages) == 3
        # Should be last 3 messages
        assert result.filtered_messages == sample_messages[-3:]

    @pytest.mark.asyncio
    async def test_handoff_with_remove_tool_calls_filter(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff removes tool calls from context."""
        from mcp_server_langgraph.agents.context_filter import RemoveToolCallsFilter
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="refund_agent",
            context_filter=RemoveToolCallsFilter(),
        )

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
        )

        # Should remove tool messages and messages with tool_calls
        for msg in result.filtered_messages:
            assert msg.get("role") != "tool"
            assert "tool_calls" not in msg

        # Original had 8 messages, 2 were tool-related
        assert len(result.filtered_messages) == 6

    @pytest.mark.asyncio
    async def test_handoff_with_summarize_filter(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff with SummarizeHistoryFilter creates summary."""
        from mcp_server_langgraph.agents.context_filter import SummarizeHistoryFilter
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="refund_agent",
            context_filter=SummarizeHistoryFilter(keep_recent=2),
        )

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
        )

        # Should have summary + 2 recent messages = 3 total
        assert len(result.filtered_messages) == 3
        # First message should be the summary
        assert result.filtered_messages[0]["role"] == "system"
        assert "6 messages" in result.filtered_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_handoff_with_chained_filters(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff with multiple chained filters."""
        from mcp_server_langgraph.agents.context_filter import (
            ChainedFilter,
            KeepLastNFilter,
            RemoveToolCallsFilter,
        )
        from mcp_server_langgraph.agents.handoff import Handoff

        # Remove tool calls first, then keep last 3
        handoff = Handoff(
            target_agent="refund_agent",
            context_filter=ChainedFilter(
                filters=[
                    RemoveToolCallsFilter(),
                    KeepLastNFilter(n=3),
                ]
            ),
        )

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
        )

        # After removing tool calls (6 msgs), then last 3
        assert len(result.filtered_messages) == 3
        for msg in result.filtered_messages:
            assert msg.get("role") != "tool"
            assert "tool_calls" not in msg


# =============================================================================
# Handoff Callback Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_callback_integration")
class TestHandoffCallbackIntegration:
    """Test handoff callback invocation in orchestrator contexts."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handoff_invokes_on_handoff_callback(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test that on_handoff callback is invoked with correct context."""
        from mcp_server_langgraph.agents.handoff import Handoff, HandoffContext

        callback_invoked = False
        callback_context = None

        def on_handoff(context: HandoffContext) -> None:
            nonlocal callback_invoked, callback_context
            callback_invoked = True
            callback_context = context

        handoff = Handoff(
            target_agent="refund_agent",
            on_handoff=on_handoff,
        )

        await handoff.execute(
            messages=sample_messages,
            session_id="test-session-123",
            source_agent="triage_agent",
        )

        assert callback_invoked is True
        assert callback_context is not None
        assert callback_context.target_agent == "refund_agent"
        assert callback_context.source_agent == "triage_agent"
        assert callback_context.session_id == "test-session-123"
        assert callback_context.message_count == len(sample_messages)

    @pytest.mark.asyncio
    async def test_handoff_callback_can_log_metrics(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff callback can be used for logging/metrics."""
        from mcp_server_langgraph.agents.handoff import Handoff, HandoffContext

        handoff_log: list[dict[str, Any]] = []

        def metrics_callback(context: HandoffContext) -> None:
            handoff_log.append(
                {
                    "from": context.source_agent,
                    "to": context.target_agent,
                    "session": context.session_id,
                    "messages": context.message_count,
                }
            )

        handoff = Handoff(
            target_agent="escalation_agent",
            on_handoff=metrics_callback,
        )

        await handoff.execute(
            messages=sample_messages,
            session_id="session-1",
            source_agent="triage_agent",
        )

        await handoff.execute(
            messages=sample_messages[:3],
            session_id="session-2",
            source_agent="refund_agent",
        )

        assert len(handoff_log) == 2
        assert handoff_log[0]["from"] == "triage_agent"
        assert handoff_log[0]["to"] == "escalation_agent"
        assert handoff_log[0]["messages"] == 8
        assert handoff_log[1]["from"] == "refund_agent"
        assert handoff_log[1]["messages"] == 3


# =============================================================================
# Handoff Tool Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_tool_integration")
class TestHandoffToolIntegration:
    """Test handoff as_tool() integration for LLM use."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handoff_as_tool_creates_named_tool(self) -> None:
        """Test that as_tool creates a properly named tool."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="refund_agent",
            description="Transfer to refund specialist for processing refunds",
        )

        tool = handoff.as_tool()

        assert tool.name == "transfer_to_refund_agent"
        assert "refund" in tool.description.lower()
        assert tool.handoff is handoff

    def test_handoff_as_tool_generates_default_description(self) -> None:
        """Test tool gets default description when not provided."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="billing_agent")

        tool = handoff.as_tool()

        assert tool.name == "transfer_to_billing_agent"
        assert "billing_agent" in tool.description
        assert "transfer" in tool.description.lower()

    def test_multiple_handoffs_create_unique_tools(self) -> None:
        """Test multiple handoffs create distinct tools."""
        from mcp_server_langgraph.agents.handoff import Handoff

        refund_handoff = Handoff(target_agent="refund_agent")
        billing_handoff = Handoff(target_agent="billing_agent")
        support_handoff = Handoff(target_agent="support_agent")

        tools = [
            refund_handoff.as_tool(),
            billing_handoff.as_tool(),
            support_handoff.as_tool(),
        ]

        tool_names = [t.name for t in tools]
        assert len(set(tool_names)) == 3  # All unique
        assert "transfer_to_refund_agent" in tool_names
        assert "transfer_to_billing_agent" in tool_names
        assert "transfer_to_support_agent" in tool_names


# =============================================================================
# Handoff with Agent Definitions Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_agent_definition_integration")
class TestHandoffAgentDefinitionIntegration:
    """Test handoff integration with AgentDefinition and AgentRegistry."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handoff_with_agent_registry(self) -> None:
        """Test handoff works with AgentRegistry for agent resolution."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )
        from mcp_server_langgraph.agents.handoff import Handoff

        # Create and register agents
        registry = AgentRegistry()
        registry.register(
            AgentDefinition(
                name="triage_agent",
                description="Initial customer triage",
                prompt="You are a triage agent...",
                tools=["read_customer_info"],
            )
        )
        registry.register(
            AgentDefinition(
                name="refund_agent",
                description="Process refund requests",
                prompt="You are a refund specialist...",
                tools=["process_refund", "check_eligibility"],
            )
        )

        # Create handoff to registered agent
        handoff = Handoff(target_agent="refund_agent")

        # Verify target agent exists in registry
        target = registry.get(handoff.target_agent)
        assert target is not None
        assert target.name == "refund_agent"
        assert "process_refund" in target.tools

    @pytest.mark.asyncio
    async def test_handoff_with_input_data_for_target_agent(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff passes input_data to target agent."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(
            target_agent="refund_agent",
            input_data={
                "order_id": "12345",
                "refund_amount": 99.99,
                "reason": "customer_request",
            },
        )

        result = await handoff.execute(
            messages=sample_messages,
            session_id="test-session",
        )

        assert result.input_data is not None
        assert result.input_data["order_id"] == "12345"
        assert result.input_data["refund_amount"] == 99.99
        assert result.input_data["reason"] == "customer_request"


# =============================================================================
# Handoff Chain Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_chain_integration")
class TestHandoffChainIntegration:
    """Test chains of handoffs between multiple agents."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sequential_handoffs(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test sequential handoffs from triage -> refund -> confirmation."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff_chain: list[str] = []

        def track_handoff(agent_name: str):
            def callback(context):
                handoff_chain.append(f"{context.source_agent}->{context.target_agent}")

            return callback

        # First handoff: triage -> refund
        handoff1 = Handoff(
            target_agent="refund_agent",
            on_handoff=track_handoff("refund"),
        )

        # Second handoff: refund -> confirmation
        handoff2 = Handoff(
            target_agent="confirmation_agent",
            on_handoff=track_handoff("confirmation"),
        )

        # Execute chain
        result1 = await handoff1.execute(
            messages=sample_messages,
            session_id="session-1",
            source_agent="triage_agent",
        )

        # Add response from refund agent
        extended_messages = result1.filtered_messages + [
            {"role": "assistant", "content": "Refund approved. Transferring to confirmation."}
        ]

        result2 = await handoff2.execute(
            messages=extended_messages,
            session_id="session-1",
            source_agent="refund_agent",
        )

        assert len(handoff_chain) == 2
        assert handoff_chain[0] == "triage_agent->refund_agent"
        assert handoff_chain[1] == "refund_agent->confirmation_agent"
        assert result2.target_agent == "confirmation_agent"

    @pytest.mark.asyncio
    async def test_handoff_preserves_source_agent_chain(
        self, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Test handoff result tracks source agent for chain tracking."""
        from mcp_server_langgraph.agents.handoff import Handoff

        handoff = Handoff(target_agent="refund_agent")

        result = await handoff.execute(
            messages=sample_messages,
            session_id="session-1",
            source_agent="triage_agent",
        )

        assert result.source_agent == "triage_agent"
        assert result.target_agent == "refund_agent"


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.xdist_group(name="handoff_performance_integration")
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead",
)
class TestHandoffPerformanceIntegration:
    """Performance tests for handoff operations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handoff_with_large_message_history(self) -> None:
        """Test handoff handles large message history efficiently."""
        import time

        from mcp_server_langgraph.agents.context_filter import KeepLastNFilter
        from mcp_server_langgraph.agents.handoff import Handoff

        # Create 1000 messages
        large_messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1000)
        ]

        handoff = Handoff(
            target_agent="refund_agent",
            context_filter=KeepLastNFilter(n=10),
        )

        start = time.time()
        result = await handoff.execute(
            messages=large_messages,
            session_id="perf-test",
        )
        elapsed = time.time() - start

        # Should complete quickly even with 1000 messages
        assert elapsed < 0.1, f"Expected fast execution, got {elapsed:.3f}s"
        assert len(result.filtered_messages) == 10

    @pytest.mark.asyncio
    async def test_concurrent_handoffs_performance(self) -> None:
        """Test multiple concurrent handoffs complete efficiently."""
        import time

        from mcp_server_langgraph.agents.handoff import Handoff

        messages = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Response"},
        ]

        handoffs = [
            Handoff(target_agent=f"agent_{i}")
            for i in range(100)
        ]

        start = time.time()
        results = await asyncio.gather(
            *[
                h.execute(messages=messages, session_id=f"session-{i}")
                for i, h in enumerate(handoffs)
            ]
        )
        elapsed = time.time() - start

        # 100 concurrent handoffs should complete quickly
        assert elapsed < 0.5, f"Expected fast concurrent execution, got {elapsed:.3f}s"
        assert len(results) == 100
        assert all(r.target_agent.startswith("agent_") for r in results)
