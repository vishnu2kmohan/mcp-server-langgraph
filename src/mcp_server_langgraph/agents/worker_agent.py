"""
Worker Agent Implementation

Concrete BaseAgent implementation that uses LLMFactory for LLM invocation
and ThinkingBudgetManager for extended thinking support.

Usage:
    from mcp_server_langgraph.agents.worker_agent import WorkerAgent
    from mcp_server_langgraph.llm.factory import get_llm_factory

    agent = WorkerAgent(llm_factory=get_llm_factory())
    request = AgentRequest(message="Hello, how are you?")
    result = await agent.run(request)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.agents.base_agent import (
    AgentRequest,
    AgentResult,
    BaseAgent,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.thinking_budget import ThinkingBudgetManager


class WorkerAgent(BaseAgent):
    """Worker agent that uses LLMFactory for LLM calls.

    This is the primary agent implementation for executing individual
    LLM invocations within orchestration patterns.

    Attributes:
        llm_factory: Factory for creating LLM completions
        thinking_budget_manager: Optional manager for thinking budget mapping
        model_id: Optional model ID override (uses factory default if None)
    """

    def __init__(
        self,
        llm_factory: Any,
        thinking_budget_manager: ThinkingBudgetManager | None = None,
        model_id: str | None = None,
    ) -> None:
        """Initialize WorkerAgent.

        Args:
            llm_factory: LLMFactory instance for creating completions
            thinking_budget_manager: Optional ThinkingBudgetManager for
                mapping thinking budget levels to provider params
            model_id: Optional model ID override. If not provided,
                uses the factory's default model.
        """
        self.llm_factory = llm_factory
        self.thinking_budget_manager = thinking_budget_manager
        self.model_id = model_id

    async def run(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """Execute agent with cancellation support.

        Args:
            request: The AgentRequest with message and configuration
            cancel_event: Optional asyncio.Event for cancellation

        Returns:
            AgentResult with content, success status, and model info
        """
        # Check for cancellation before starting
        if cancel_event and cancel_event.is_set():
            return AgentResult(
                content="",
                success=False,
                error="Cancelled before execution",
            )

        try:
            # Build completion kwargs
            kwargs: dict[str, Any] = {
                "messages": [{"role": "user", "content": request.message}],
            }

            # Add model override if specified
            if self.model_id:
                kwargs["model"] = self.model_id

            # Add max tokens if specified
            if request.max_tokens:
                kwargs["max_tokens"] = request.max_tokens

            # Handle thinking budget if manager available and budget requested
            thinking_content = None
            thinking_tokens = 0
            if self.thinking_budget_manager and request.thinking_budget != "none" and self.model_id is not None:
                # Map thinking budget to provider-specific params
                # Convert string level to ThinkingLevel enum
                thinking_level = self.thinking_budget_manager.level_from_string(request.thinking_budget)
                thinking_params = self.thinking_budget_manager.get_params(
                    model=self.model_id,
                    level=thinking_level,
                )
                kwargs.update(thinking_params)

            # Execute LLM call with timeout
            response = await asyncio.wait_for(
                self.llm_factory.create_completion(**kwargs),
                timeout=request.timeout_seconds,
            )

            # Extract response content
            content = ""
            model_used = getattr(response, "model", self.model_id or "")

            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    content = choice.message.content or ""

                # Extract thinking content if available
                if hasattr(choice.message, "thinking"):
                    thinking_content = choice.message.thinking
                if hasattr(choice.message, "thinking_tokens"):
                    thinking_tokens = choice.message.thinking_tokens

            return AgentResult(
                content=content,
                success=True,
                model_used=model_used,
                thinking_content=thinking_content,
                thinking_tokens=thinking_tokens,
            )

        except TimeoutError:
            return AgentResult(
                content="",
                success=False,
                error=f"Timeout after {request.timeout_seconds} seconds",
            )
        except asyncio.CancelledError:
            return AgentResult(
                content="",
                success=False,
                error="Cancelled during execution",
            )
        except Exception as e:
            return AgentResult(
                content="",
                success=False,
                error=str(e),
                model_used=self.model_id or "",
            )
