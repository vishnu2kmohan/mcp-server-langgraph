"""
Pydantic AI Agent - Type-safe agent implementation with structured outputs

This module provides strongly-typed agent responses using Pydantic AI,
ensuring LLM outputs match expected schemas and improving reliability.
"""

from typing import Literal, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from config import settings
from observability import logger, metrics, tracer


# Structured Response Models
class RouterDecision(BaseModel):
    """Routing decision with reasoning for agent workflow."""

    action: Literal["use_tools", "respond", "clarify"] = Field(description="Next action to take in the agent workflow")
    reasoning: str = Field(description="Explanation of why this action was chosen")
    tool_name: Optional[str] = Field(default=None, description="Name of tool to use if action is 'use_tools'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for this decision (0-1)")


class ToolExecution(BaseModel):
    """Result of tool execution with metadata."""

    tool_name: str = Field(description="Name of the executed tool")
    result: str = Field(description="Tool execution result")
    success: bool = Field(description="Whether tool execution succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata about the execution")


class AgentResponse(BaseModel):
    """Final agent response with confidence and metadata."""

    content: str = Field(description="The main response content to show to the user")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this response (0-1)")
    requires_clarification: bool = Field(default=False, description="Whether the agent needs more information")
    clarification_question: Optional[str] = Field(default=None, description="Question to ask user if clarification needed")
    sources: list[str] = Field(default_factory=list, description="Sources or references used to generate response")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional response metadata")


class PydanticAIAgentWrapper:
    """
    Wrapper for Pydantic AI agents with type-safe responses.

    Provides strongly-typed interactions with LLMs, ensuring outputs
    match expected schemas for improved reliability and debugging.
    """

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None):
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

        # Create specialized agents for different tasks
        self.router_agent = Agent(
            self.pydantic_model_name,
            result_type=RouterDecision,
            system_prompt="""You are a routing assistant for an AI agent.
Your job is to analyze user messages and decide the best action:
- 'use_tools': If the user needs external tools (search, calculate, lookup)
- 'respond': If you can answer directly without tools
- 'clarify': If the request is unclear or needs more information

Always provide clear reasoning and a confidence score.""",
        )

        self.response_agent = Agent(
            self.pydantic_model_name,
            result_type=AgentResponse,
            system_prompt="""You are a helpful AI assistant.
Provide clear, accurate, and helpful responses to user questions.
If you're uncertain, indicate that in your confidence score.
If you need clarification, set requires_clarification=True and ask a specific question.""",
        )

        logger.info(
            "Pydantic AI agent wrapper initialized",
            extra={"model": self.model_name, "provider": self.provider, "pydantic_model": self.pydantic_model_name},
        )

    def _get_pydantic_model_name(self) -> str:
        """
        Map provider/model to Pydantic AI format.

        Returns:
            Pydantic AI compatible model name
        """
        # Pydantic AI supports model names like:
        # - "openai:gpt-4"
        # - "anthropic:claude-3-5-sonnet-20241022"
        # - "gemini-2.5-flash-002" (Google models use simple name)

        if self.provider == "google" or self.provider == "gemini":
            # Google Gemini models work with simple names
            return self.model_name
        elif self.provider == "anthropic":
            return f"anthropic:{self.model_name}"
        elif self.provider == "openai":
            return f"openai:{self.model_name}"
        else:
            # Default: try simple name
            logger.warning(f"Unknown provider '{self.provider}', using model name directly", extra={"model": self.model_name})
            return self.model_name

    async def route_message(self, message: str, context: Optional[dict] = None) -> RouterDecision:
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
                result = await self.router_agent.run(prompt)
                decision = result.data

                span.set_attribute("decision.action", decision.action)
                span.set_attribute("decision.confidence", decision.confidence)

                logger.info(
                    "Message routed",
                    extra={"action": decision.action, "confidence": decision.confidence, "reasoning": decision.reasoning},
                )

                metrics.successful_calls.add(1, {"operation": "route_message"})

                return decision

            except Exception as e:
                logger.error(f"Routing failed: {e}", extra={"message": message}, exc_info=True)
                metrics.failed_calls.add(1, {"operation": "route_message"})
                span.record_exception(e)
                raise

    async def generate_response(self, messages: list[BaseMessage], context: Optional[dict] = None) -> AgentResponse:
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
                result = await self.response_agent.run(conversation)
                response = result.data

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
def create_pydantic_agent(model_name: Optional[str] = None, provider: Optional[str] = None) -> PydanticAIAgentWrapper:
    """
    Create a Pydantic AI agent wrapper.

    Args:
        model_name: Model to use (defaults to settings)
        provider: Provider name (defaults to settings)

    Returns:
        Configured PydanticAIAgentWrapper instance
    """
    return PydanticAIAgentWrapper(model_name=model_name, provider=provider)
