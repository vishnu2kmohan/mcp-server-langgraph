"""
Pydantic AI Agent - Type-safe agent implementation with structured outputs

This module provides strongly-typed agent responses using Pydantic AI,
ensuring LLM outputs match expected schemas and improving reliability.

Note: pydantic-ai is an optional dependency. If not installed, this module will raise
ImportError when used. The agent.py module handles this gracefully with PYDANTIC_AI_AVAILABLE flag.
"""

from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

# Conditional import - pydantic-ai is optional for type-safe responses
# If not available, agent.py will fall back to standard routing
try:
    from pydantic_ai import Agent

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    Agent = None  # type: ignore[unused-ignore,assignment,misc]

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.prompts import RESPONSE_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


# Structured Response Models
class RouterDecision(BaseModel):
    """Routing decision with reasoning for agent workflow."""

    action: Literal["use_tools", "respond", "clarify"] = Field(description="Next action to take in the agent workflow")
    reasoning: str = Field(description="Explanation of why this action was chosen")
    tool_name: str | None = Field(default=None, description="Name of tool to use if action is 'use_tools'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for this decision (0-1)")


class ToolExecution(BaseModel):
    """Result of tool execution with metadata."""

    tool_name: str = Field(description="Name of the executed tool")
    result: str = Field(description="Tool execution result")
    success: bool = Field(description="Whether tool execution succeeded")
    error_message: str | None = Field(default=None, description="Error message if execution failed")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata about the execution")


class AgentResponse(BaseModel):
    """Final agent response with confidence and metadata."""

    content: str = Field(description="The main response content to show to the user")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this response (0-1)")
    requires_clarification: bool = Field(default=False, description="Whether the agent needs more information")
    clarification_question: str | None = Field(default=None, description="Question to ask user if clarification needed")
    sources: list[str] = Field(default_factory=list, description="Sources or references used to generate response")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional response metadata")


class PydanticAIAgentWrapper:
    """
    Wrapper for Pydantic AI agents with type-safe responses.

    Provides strongly-typed interactions with LLMs, ensuring outputs
    match expected schemas for improved reliability and debugging.
    """

    def __init__(self, model_name: str | None = None, provider: str | None = None) -> None:
        """
        Initialize Pydantic AI agent wrapper.

        Args:
            model_name: Model to use (defaults to settings.model_name)
            provider: Provider name (defaults to settings.llm_provider)
        """
        self.model_name = model_name or settings.model_name
        self.provider = provider or settings.llm_provider

        # Map provider to Pydantic AI model format
        self.pydantic_model_name = self._get_pydantic_model_name()

        # Create specialized agents for different tasks with XML-structured prompts
        # Note: output_type replaces deprecated result_type in pydantic-ai 0.1.0+
        self.router_agent = Agent(
            self.pydantic_model_name,
            output_type=RouterDecision,
            system_prompt=ROUTER_SYSTEM_PROMPT,
        )

        self.response_agent = Agent(
            self.pydantic_model_name,
            output_type=AgentResponse,
            system_prompt=RESPONSE_SYSTEM_PROMPT,
        )

        logger.info(
            "Pydantic AI agent wrapper initialized",
            extra={"model": self.model_name, "provider": self.provider, "pydantic_model": self.pydantic_model_name},
        )

    def _get_pydantic_model_name(self) -> str:
        """
        Map provider/model to Pydantic AI format with required provider prefix.

        PYDANTIC-AI REQUIREMENT (v0.0.14+): All model names must include provider prefix.

        Deprecation Warning Fixed:
        --------------------------
        Old (deprecated): 'gemini-2.5-flash'
        New (required):   'google-gla:gemini-2.5-flash'

        Without prefix, pydantic-ai emits:
        "DeprecationWarning: Specifying a model name without a provider prefix is deprecated.
        Instead of 'gemini-2.5-flash', use 'google-gla:gemini-2.5-flash'."

        Provider Prefix Mapping:
        ------------------------
        - Google Gemini: 'google-gla:' (e.g., 'google-gla:gemini-2.5-flash')
        - Anthropic Claude: 'anthropic:' (e.g., 'anthropic:claude-sonnet-4-5-20250929')
        - OpenAI: 'openai:' (e.g., 'openai:gpt-4')
        - Unknown: 'provider:' (generic fallback)

        Returns:
            Pydantic AI compatible model name with provider prefix
        """
        # Check if model name already has a prefix (edge case)
        if ":" in self.model_name:
            # Model name already includes provider prefix
            logger.debug(
                f"Model name '{self.model_name}' already has provider prefix",
                extra={"model": self.model_name, "provider": self.provider},
            )
            return self.model_name

        # Add provider prefix based on provider type
        if self.provider == "google" or self.provider == "gemini":
            # Google Gemini models require google-gla prefix
            return f"google-gla:{self.model_name}"
        elif self.provider == "anthropic":
            return f"anthropic:{self.model_name}"
        elif self.provider == "openai":
            return f"openai:{self.model_name}"
        else:
            # Unknown provider: use provider name as prefix
            logger.warning(
                f"Unknown provider '{self.provider}', using provider-prefixed format",
                extra={"model": self.model_name, "provider": self.provider},
            )
            return f"{self.provider}:{self.model_name}"

    async def route_message(self, message: str, context: dict | None = None) -> RouterDecision:  # type: ignore[type-arg]
        """
        Determine the appropriate action for a user message.

        Args:
            message: User message to route
            context: Optional context about the conversation

        Returns:
            RouterDecision with action and reasoning
        """
        with tracer.start_as_current_span("pydantic_ai.route") as span:
            span.set_attribute("message.length", len(message))

            try:
                # Build prompt with context
                prompt = message
                if context:
                    context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                    prompt = f"Context:\n{context_str}\n\nUser message: {message}"

                # Get routing decision
                # Note: .output replaces deprecated .data in pydantic-ai 1.0+
                # See: https://ai.pydantic.dev/changelog/
                result = await self.router_agent.run(prompt)
                decision = result.output

                span.set_attribute("decision.action", decision.action)
                span.set_attribute("decision.confidence", decision.confidence)

                logger.info(
                    "Message routed",
                    extra={"action": decision.action, "confidence": decision.confidence, "reasoning": decision.reasoning},
                )

                metrics.successful_calls.add(1, {"operation": "route_message"})

                return decision

            except Exception as e:
                logger.error(f"Routing failed: {e}", extra={"user_message": message}, exc_info=True)
                metrics.failed_calls.add(1, {"operation": "route_message"})
                span.record_exception(e)
                raise

    async def generate_response(self, messages: list[BaseMessage], context: dict[str, Any] | None = None) -> AgentResponse:
        """
        Generate a typed response to user messages.

        Args:
            messages: Conversation history
            context: Optional context information

        Returns:
            AgentResponse with content and metadata
        """
        with tracer.start_as_current_span("pydantic_ai.generate_response") as span:
            span.set_attribute("message.count", len(messages))

            try:
                # Convert messages to prompt
                conversation = self._format_conversation(messages)

                # Add context if provided
                if context:
                    context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                    conversation = f"Context:\n{context_str}\n\n{conversation}"

                # Generate response
                # Note: .output replaces deprecated .data in pydantic-ai 1.0+
                # See: https://ai.pydantic.dev/changelog/
                result = await self.response_agent.run(conversation)
                response = result.output

                span.set_attribute("response.length", len(response.content))
                span.set_attribute("response.confidence", response.confidence)
                span.set_attribute("response.requires_clarification", response.requires_clarification)

                logger.info(
                    "Response generated",
                    extra={
                        "confidence": response.confidence,
                        "requires_clarification": response.requires_clarification,
                        "content_length": len(response.content),
                    },
                )

                metrics.successful_calls.add(1, {"operation": "generate_response"})

                return response

            except Exception as e:
                logger.error(f"Response generation failed: {e}", extra={"message_count": len(messages)}, exc_info=True)
                metrics.failed_calls.add(1, {"operation": "generate_response"})
                span.record_exception(e)
                raise

    def _format_conversation(self, messages: list[BaseMessage]) -> str:
        """
        Format conversation history for Pydantic AI.

        Args:
            messages: List of LangChain messages

        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"Assistant: {msg.content}")
            else:
                lines.append(f"System: {msg.content}")

        return "\n\n".join(lines)


# Factory function for easy integration
def create_pydantic_agent(model_name: str | None = None, provider: str | None = None) -> PydanticAIAgentWrapper:
    """
    Create a Pydantic AI agent wrapper.

    Args:
        model_name: Model to use (defaults to settings)
        provider: Provider name (defaults to settings)

    Returns:
        Configured PydanticAIAgentWrapper instance

    Raises:
        ImportError: If pydantic-ai is not installed
    """
    if not PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is not installed. "
            "Add 'pydantic-ai' to pyproject.toml dependencies, then run: uv sync\n"
            "The agent will fall back to standard routing without Pydantic AI."
        )

    return PydanticAIAgentWrapper(model_name=model_name, provider=provider)
