"""
Handoff pattern for multi-agent control transfer (ADR-0081)

This module implements the Handoff pattern from OpenAI Agents SDK,
adapted for LLM-agnostic multi-agent orchestration.

A Handoff is an explicit transfer of control from one agent to another,
where the receiving agent gets the conversation history (optionally filtered).

Usage:
    from mcp_server_langgraph.agents.handoff import Handoff, HandoffResult
    from mcp_server_langgraph.agents.context_filter import KeepLastNFilter

    # Create a handoff to another agent
    handoff = Handoff(
        target_agent="refund_agent",
        context_filter=KeepLastNFilter(n=5),
        description="Transfer to refund specialist",
    )

    # Convert to tool for LLM use
    tool = handoff.as_tool()

    # Execute the handoff
    result = await handoff.execute(messages=messages, session_id="sess_123")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.context_filter import ContextFilter


@dataclass
class HandoffContext:
    """Context information passed to on_handoff callbacks.

    Provides metadata about the handoff for logging, metrics, etc.

    Attributes:
        target_agent: Name of the agent receiving control
        session_id: Current session identifier
        message_count: Number of messages in the conversation
        source_agent: Optional name of the agent initiating handoff
    """

    target_agent: str
    session_id: str
    message_count: int
    source_agent: str | None = None


@dataclass
class HandoffResult:
    """Result of executing a handoff.

    Contains the target agent and the filtered messages to pass.

    Attributes:
        target_agent: Name of the agent that should take over
        filtered_messages: Messages after context filtering
        input_data: Optional additional data for the target agent
        source_agent: Optional name of the agent that initiated handoff
    """

    target_agent: str
    filtered_messages: list[dict[str, Any]]
    input_data: dict[str, Any] | None = None
    source_agent: str | None = None


@dataclass
class HandoffTool:
    """Tool wrapper for a Handoff.

    This is returned by Handoff.as_tool() and provides a tool-compatible
    interface for LLMs to invoke handoffs.

    Attributes:
        name: Tool name (includes target agent)
        description: Human-readable description
        handoff: Reference to the parent Handoff
    """

    name: str
    description: str
    handoff: Handoff


@dataclass
class Handoff:
    """Explicit control transfer to another agent.

    A Handoff represents a transfer of conversation control from one agent
    to another. It can optionally filter the conversation context before
    passing it to the target agent.

    Attributes:
        target_agent: Name of the agent to transfer to
        context_filter: Optional filter for conversation history
        on_handoff: Optional callback invoked when handoff executes
        input_data: Optional additional data for target agent
        description: Human-readable description of the handoff
    """

    target_agent: str
    context_filter: ContextFilter | None = None
    on_handoff: Callable[[HandoffContext], None] | None = None
    input_data: dict[str, Any] | None = None
    description: str | None = None

    def as_tool(self) -> HandoffTool:
        """Convert this handoff to a tool for LLM use.

        Returns:
            HandoffTool that can be used by an LLM to invoke this handoff
        """
        name = f"transfer_to_{self.target_agent}"
        description = self.description or f"Transfer conversation to {self.target_agent}"

        return HandoffTool(
            name=name,
            description=description,
            handoff=self,
        )

    async def execute(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        source_agent: str | None = None,
    ) -> HandoffResult:
        """Execute the handoff.

        Applies context filtering and invokes callbacks.

        Args:
            messages: Current conversation messages
            session_id: Current session identifier
            source_agent: Optional name of the agent initiating handoff

        Returns:
            HandoffResult containing target agent and filtered messages
        """
        # Apply context filter if provided
        filtered_messages = (
            self.context_filter.filter(messages)
            if self.context_filter is not None
            else messages.copy()
        )

        # Create handoff context for callback
        context = HandoffContext(
            target_agent=self.target_agent,
            session_id=session_id,
            message_count=len(messages),
            source_agent=source_agent,
        )

        # Invoke callback if provided
        if self.on_handoff is not None:
            self.on_handoff(context)

        return HandoffResult(
            target_agent=self.target_agent,
            filtered_messages=filtered_messages,
            input_data=self.input_data,
            source_agent=source_agent,
        )


__all__ = [
    "Handoff",
    "HandoffContext",
    "HandoffResult",
    "HandoffTool",
]
