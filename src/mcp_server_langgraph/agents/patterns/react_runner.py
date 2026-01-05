"""ReACT execution pattern for multi-step reasoning+acting.

Wraps LangGraph's create_react_agent for structured ReACT execution
with timeout, cancellation, and iteration tracking.

ReACT (Reasoning + Acting) pattern:
1. Agent reasons about the task
2. Agent selects and calls a tool
3. Agent observes the result
4. Agent decides if done or repeats

Usage:
    from mcp_server_langgraph.agents.patterns.react_runner import ReACTRunner

    runner = ReACTRunner(model=llm, tools=[search_tool, calc_tool])
    result = await runner.run("Search for X and calculate Y")

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage


class ReACTRunner:
    """ReACT execution pattern runner.

    Executes multi-step reasoning+acting loops with tool calling.
    Provides timeout handling, cancellation support, and iteration tracking.

    Attributes:
        model: LLM model for reasoning
        tools: List of tools available for agent
        max_iterations: Maximum number of reasoning+acting cycles
        timeout_seconds: Timeout for entire execution
    """

    DEFAULT_MAX_ITERATIONS = 10
    DEFAULT_TIMEOUT_SECONDS = 60.0

    def __init__(
        self,
        model: Any,
        tools: list[Any] | None = None,
        max_iterations: int | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """Initialize ReACTRunner.

        Args:
            model: LLM model to use for reasoning
            tools: List of LangChain tools available to the agent
            max_iterations: Maximum number of ReACT cycles (default: 10)
            timeout_seconds: Timeout for entire execution (default: 60.0)
        """
        self.model = model
        self.tools = tools if tools is not None else []
        self.max_iterations = max_iterations if max_iterations is not None else self.DEFAULT_MAX_ITERATIONS
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else self.DEFAULT_TIMEOUT_SECONDS
        self._agent: Any | None = None

    async def run(
        self,
        message: str,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        """Execute ReACT agent with the given message.

        Args:
            message: User message/task to process
            cancel_event: Optional event for cancellation

        Returns:
            Dict with execution results including:
            - messages: List of conversation messages
            - iterations: Number of ReACT cycles executed
            - error: Error message if failed
            - timeout: True if execution timed out
            - cancelled: True if execution was cancelled
        """
        # Check for immediate cancellation
        if cancel_event and cancel_event.is_set():
            return {
                "messages": [],
                "iterations": 0,
                "cancelled": True,
            }

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_agent(message, cancel_event),
                timeout=self.timeout_seconds,
            )
            return result

        except TimeoutError:
            return {
                "messages": [],
                "iterations": 0,
                "timeout": True,
                "error": f"Execution timed out after {self.timeout_seconds} seconds",
            }
        except asyncio.CancelledError:
            return {
                "messages": [],
                "iterations": 0,
                "cancelled": True,
            }
        except Exception as e:
            return {
                "messages": [],
                "iterations": 0,
                "error": str(e),
            }

    async def _execute_agent(
        self,
        message: str,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        """Execute the ReACT agent internally.

        Args:
            message: User message to process
            cancel_event: Optional cancellation event

        Returns:
            Execution result dict
        """
        # Check cancellation before execution
        if cancel_event and cancel_event.is_set():
            return {
                "messages": [],
                "iterations": 0,
                "cancelled": True,
            }

        # Create agent if not already created
        if self._agent is None:
            self._agent = self._create_agent()

        # Execute agent
        input_messages = [HumanMessage(content=message)]
        config = {"recursion_limit": self.max_iterations * 2}

        # Invoke the agent
        result = await self._agent.ainvoke(
            {"messages": input_messages},
            config=config,
        )

        # Extract messages from result
        messages = result.get("messages", [])

        # Count iterations (tool calls)
        iterations = sum(1 for msg in messages if hasattr(msg, "tool_calls") and msg.tool_calls)

        return {
            "messages": messages,
            "iterations": iterations,
        }

    def _create_agent(self) -> Any:
        """Create the ReACT agent using LangGraph.

        Returns:
            Compiled LangGraph agent
        """
        try:
            from langgraph.prebuilt import create_react_agent

            return create_react_agent(self.model, self.tools)
        except ImportError:
            # Fallback for when langgraph.prebuilt is not available
            # Create a simple mock agent for testing
            return self._create_fallback_agent()

    def _create_fallback_agent(self) -> Any:
        """Create a fallback agent for testing when LangGraph is not available.

        Returns:
            Simple mock agent
        """

        class FallbackAgent:
            """Simple fallback agent for testing."""

            def __init__(self, model: Any, tools: list[Any]) -> None:
                self.model = model
                self.tools = tools

            async def ainvoke(self, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
                """Simple invoke that just returns the input messages."""
                return {"messages": inputs.get("messages", [])}

        return FallbackAgent(self.model, self.tools)
