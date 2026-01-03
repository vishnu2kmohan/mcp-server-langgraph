"""
Base Agent Abstraction Layer

Provides the contract for individual agent execution that sits between
orchestrators (BaseOrchestrator) and LLM providers (LLMFactory).

This abstraction enables:
- Unified agent interface for all orchestration patterns
- Cancellation support via asyncio.Event
- Thinking budget integration
- Clean separation of concerns

Usage:
    from mcp_server_langgraph.agents.base_agent import (
        AgentRequest,
        AgentResult,
        BaseAgent,
    )

    class MyAgent(BaseAgent):
        async def run(self, request: AgentRequest, cancel_event=None) -> AgentResult:
            # Implementation here
            ...
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class AgentRequest:
    """Request for agent execution.

    Minimal structure for orchestration - avoids duplicating fields
    already tracked by telemetry/metrics systems.

    Attributes:
        message: The user message or task to process
        context: Additional context dict (session data, history, etc.)
        thinking_budget: Thinking budget level (none, light, medium, deep)
        max_tokens: Maximum output tokens (None = model default)
        timeout_seconds: Request timeout in seconds
        session_id: Session ID for tracing
        trace_id: Trace ID for distributed tracing
    """

    message: str
    context: dict[str, Any] = field(default_factory=dict)
    thinking_budget: Literal["none", "light", "medium", "deep"] = "none"
    max_tokens: int | None = None
    timeout_seconds: float = 60.0
    session_id: str | None = None
    trace_id: str | None = None


@dataclass
class AgentResult:
    """Result from agent execution.

    Minimal structure for orchestration decisions - tokens/cost/latency
    are tracked by CostTracker/metrics, not duplicated here.

    Attributes:
        content: The agent's response content
        success: Whether execution completed successfully
        error: Error message if success is False
        thinking_content: Extended thinking content (if model supports it)
        thinking_tokens: Number of tokens used for thinking
        model_used: Model ID that was used for generation
    """

    content: str
    success: bool
    error: str | None = None
    thinking_content: str | None = None
    thinking_tokens: int = 0
    model_used: str = ""


class BaseAgent(ABC):
    """Abstract base class for individual agent execution.

    Provides the contract for agents that orchestrators use to execute tasks.
    Implementations should handle:
    - LLM invocation via LLMFactory
    - Thinking budget mapping for models that support it
    - Cancellation via cancel_event
    - Timeout handling
    - Error handling

    Example implementation:
        class WorkerAgent(BaseAgent):
            def __init__(self, llm_factory: LLMFactory):
                self.llm_factory = llm_factory

            async def run(
                self,
                request: AgentRequest,
                cancel_event: asyncio.Event | None = None
            ) -> AgentResult:
                if cancel_event and cancel_event.is_set():
                    return AgentResult(content="", success=False, error="Cancelled")

                try:
                    response = await self.llm_factory.create_completion(...)
                    return AgentResult(content=response.content, success=True)
                except Exception as e:
                    return AgentResult(content="", success=False, error=str(e))
    """

    @abstractmethod
    async def run(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """Execute agent with cancellation support.

        Args:
            request: The AgentRequest with message and configuration
            cancel_event: Optional asyncio.Event for cancellation.
                         If set before or during execution, agent should
                         return early with success=False.

        Returns:
            AgentResult with content, success status, and optional thinking.
        """
        ...
