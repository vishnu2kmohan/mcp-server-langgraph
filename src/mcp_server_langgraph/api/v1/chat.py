"""
Chat Router

Provides real-time chat interactions under /api/v1/chat/*.

This consolidates chat functionality from playground into a unified API.

Usage:
    POST /api/v1/chat/completions - Create a chat completion
    POST /api/v1/chat/completions/stream - Create a streaming chat completion
    GET /api/v1/chat/{session_id}/history - Get chat history for a session
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from litellm import acompletion
from opentelemetry import trace
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings

if TYPE_CHECKING:
    pass


chat_router = APIRouter(tags=["chat"])


# Request/Response Models


class ChatMessage(BaseModel):
    """A message in the chat conversation."""

    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request body for chat completion."""

    session_id: str = Field(description="Session ID for the conversation")
    messages: list[ChatMessage] = Field(description="List of messages in the conversation", min_length=1)
    model: str | None = Field(default=None, description="Model to use for completion")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=None, ge=1, le=4096, description="Maximum tokens to generate")
    resource_uris: list[str] | None = Field(
        default=None,
        description="Optional list of MCP resource URIs to inject as context (MCP 2025-11-25)",
    )
    # Extended thinking / reasoning effort parameters
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Reasoning effort level for models supporting extended thinking (Claude Opus 4.5, Sonnet 4, Gemini 2.5). "
        "Maps to LiteLLM's reasoning_effort parameter which translates to Anthropic's thinking budget.",
    )
    enable_thinking: bool = Field(
        default=True,
        description="Whether to enable extended thinking for supported models. Set to False to disable thinking even on models that support it.",
    )


class ChatUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(description="Tokens in the prompt")
    completion_tokens: int = Field(description="Tokens in the completion")
    total_tokens: int | None = Field(default=None, description="Total tokens used")


class ThinkingContent(BaseModel):
    """Thinking/reasoning content from extended thinking models."""

    content: str = Field(description="The model's internal reasoning/thinking content")
    tokens: int | None = Field(default=None, description="Number of tokens used for thinking")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""

    id: str = Field(description="Completion ID")
    message: ChatMessage = Field(description="Assistant's response message")
    usage: ChatUsage | None = Field(default=None, description="Token usage")
    model: str | None = Field(default=None, description="Model used")
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID for observability correlation")
    thinking: ThinkingContent | None = Field(
        default=None,
        description="Thinking/reasoning content from extended thinking models (Claude Opus 4.5, Sonnet 4, Gemini 2.5)",
    )


# ==============================================================================
# Extended Thinking Support
# ==============================================================================

# Models that support extended thinking / reasoning effort
# Based on LiteLLM docs: https://docs.litellm.ai/docs/reasoning_content
THINKING_MODELS = frozenset(
    {
        # Anthropic models with extended thinking
        "claude-opus-4-5",
        "claude-opus-4-5-20250514",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-20250514",
        "claude-sonnet-4",
        "claude-3-7-sonnet",
        "claude-3-7-sonnet-20250219",
        "claude-3.7-sonnet",
        "claude-3.5-sonnet",  # May support thinking in newer versions
        # Anthropic prefixed models
        "anthropic/claude-opus-4-5",
        "anthropic/claude-opus-4-5-20250514",
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-sonnet-4-5-20250514",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3-7-sonnet",
        "anthropic/claude-3-7-sonnet-20250219",
        "anthropic/claude-3.7-sonnet",
        # Google Gemini models with thinking
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-thinking",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-flash-thinking",
        # OpenAI o-series reasoning models
        "o1",
        "o1-preview",
        "o1-mini",
        "o3",
        "o3-mini",
        "openai/o1",
        "openai/o1-preview",
        "openai/o1-mini",
        "openai/o3",
        "openai/o3-mini",
        # DeepSeek reasoning models
        "deepseek-reasoner",
        "deepseek/deepseek-reasoner",
    }
)


def model_supports_thinking(model_name: str) -> bool:
    """
    Check if a model supports extended thinking / reasoning effort.

    Args:
        model_name: The model name to check (e.g., "claude-opus-4-5", "gemini-2.5-flash")

    Returns:
        True if the model supports extended thinking, False otherwise.
    """
    if not model_name:
        return False

    model_lower = model_name.lower()

    # Check exact match first
    if model_lower in THINKING_MODELS:
        return True

    # Check pattern-based matching for common naming variants
    thinking_patterns = [
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-3.7",
        "claude-3-7",
        "gemini-2.5",
        "o1-",
        "o3-",
        "deepseek-reasoner",
    ]

    return any(pattern in model_lower for pattern in thinking_patterns)


# Service Interface


class ChatService:
    """Interface for chat operations. Implemented by LLM layer."""

    async def create_completion(self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Create a chat completion. Returns the response."""
        raise NotImplementedError

    async def create_stream(
        self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Create a streaming chat completion. Yields chunks."""
        raise NotImplementedError
        yield  # type: ignore[unreachable]  # Makes mypy recognize this as an async generator

    async def get_history(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get chat history for a session. Returns None if not found."""
        raise NotImplementedError


class ChatServiceImpl(ChatService):
    """
    Implementation of ChatService that integrates with MCP agent and LiteLLM.

    Provides:
    - Non-streaming chat completions via create_completion()
    - Streaming chat completions via create_stream()
    - Session history retrieval via get_history()

    Uses MCPBridge for full agent execution with MCP tools when available,
    falls back to LiteLLM for direct LLM calls when MCP is not configured.
    """

    def __init__(
        self,
        session_storage: Any | None = None,
        mcp_bridge: Any | None = None,
        langgraph_agent: Any | None = None,
    ) -> None:
        """
        Initialize with optional dependencies.

        Args:
            session_storage: Optional storage backend for session history.
                             If None, history will return empty list.
            mcp_bridge: Optional MCPBridge instance for agent communication.
                        If None, uses LiteLLM as fallback.
            langgraph_agent: Optional compiled LangGraph agent for astream_events.
                             If provided, enables real-time node/edge streaming.
        """
        self._session_storage = session_storage
        self._mcp_bridge = mcp_bridge
        self._langgraph_agent = langgraph_agent

    @property
    def mcp_bridge(self) -> Any | None:
        """Get the MCP bridge, lazily initializing from environment if available."""
        if self._mcp_bridge is None:
            from mcp_server_langgraph.api.v1.mcp_bridge import get_mcp_bridge

            self._mcp_bridge = get_mcp_bridge()
        return self._mcp_bridge

    def _get_current_trace_id(self) -> str | None:
        """Get the current OpenTelemetry trace ID for observability correlation.

        Returns:
            32-character hex string trace ID, or None if no active trace.
        """
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if not span_context.is_valid or not span_context.trace_id:
            return None
        # Format as 32-character hex string (padded with zeros)
        return format(span_context.trace_id, "032x")

    async def _create_completion_via_mcp(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create completion using MCP agent."""
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError

        bridge = self.mcp_bridge
        if not bridge or not bridge.is_configured:
            raise ChatError("MCP bridge not configured")

        # Extract the last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        user_id = kwargs.get("user_id", "anonymous")

        response = await bridge.send_chat_message(
            session_id=session_id,
            message=last_user_message,
            user_id=user_id,
        )

        # Prefer trace_id from MCP response, fallback to current span
        trace_id = response.trace_id or self._get_current_trace_id()

        return {
            "id": f"chatcmpl-{uuid4().hex[:8]}",
            "message": {
                "role": "assistant",
                "content": response.content,
            },
            "usage": response.usage,
            "model": "mcp-agent",
            "trace_id": trace_id,
        }

    async def _read_resources_for_context(
        self,
        resource_uris: list[str],
    ) -> str:
        """
        Read resources and build context string for injection.

        Args:
            resource_uris: List of resource URIs to read

        Returns:
            Formatted context string with all resource contents
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError
        from mcp_server_langgraph.observability.telemetry import logger

        bridge = self.mcp_bridge
        if bridge is None:
            logger.warning("Cannot inject resources: MCP bridge not configured")
            return ""

        context_parts: list[str] = []

        for uri in resource_uris:
            try:
                contents = await bridge.read_resource(uri)
                for content in contents:
                    if content.text:
                        context_parts.append(f"[Resource: {uri}]\n{content.text}\n")
                    elif content.blob:
                        # For binary content, just note it's available
                        context_parts.append(f"[Resource: {uri}] (binary content, {len(content.blob)} bytes)\n")
            except MCPResourceNotFoundError as e:
                logger.warning(f"Resource not found, skipping: {e}")
            except Exception as e:
                logger.warning(f"Failed to read resource {uri}: {e}")

        return "\n".join(context_parts)

    async def _inject_resource_context(
        self,
        messages: list[dict[str, Any]],
        resource_uris: list[str] | None,
    ) -> list[dict[str, Any]]:
        """
        Inject resource context into messages.

        If resource_uris are provided, reads the resources and prepends
        a system message with their contents.

        Args:
            messages: Original message list
            resource_uris: Optional list of resource URIs to inject

        Returns:
            Message list with optional resource context prepended
        """
        if not resource_uris:
            return messages

        context = await self._read_resources_for_context(resource_uris)
        if not context:
            return messages

        # Create a system message with resource context
        context_message = {
            "role": "system",
            "content": f"The following resources are available as context:\n\n{context}",
        }

        # Prepend context to messages
        return [context_message] + list(messages)

    async def _create_completion_via_litellm(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create completion using LiteLLM directly."""
        model = kwargs.get("model") or settings.model_name
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")
        reasoning_effort = kwargs.get("reasoning_effort")
        enable_thinking = kwargs.get("enable_thinking", True)

        # Inject resource context if provided
        resource_uris = kwargs.get("resource_uris")
        messages = await self._inject_resource_context(messages, resource_uris)

        # Build completion parameters
        completion_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Add reasoning_effort for models that support extended thinking
        # Only add if thinking is enabled and the model supports it
        supports_thinking = model_supports_thinking(model)
        if supports_thinking and enable_thinking and reasoning_effort:
            completion_params["reasoning_effort"] = reasoning_effort

        response = await acompletion(**completion_params)

        choice = response.choices[0]
        message_data = {
            "role": choice.message.role,
            "content": choice.message.content,
        }

        usage_data = None
        if response.usage:
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }

        # Extract thinking content from response if available
        # LiteLLM returns thinking content in different ways:
        # 1. response.reasoning_content (unified field)
        # 2. response.thinking_blocks (Anthropic-specific)
        thinking_data = None
        reasoning_content = getattr(response, "reasoning_content", None)
        if reasoning_content:
            thinking_data = {
                "content": reasoning_content,
                "tokens": getattr(response.usage, "reasoning_tokens", None) if response.usage else None,
            }
        elif hasattr(choice.message, "thinking_blocks") and choice.message.thinking_blocks:
            # Anthropic-specific thinking blocks
            thinking_blocks = choice.message.thinking_blocks
            combined_thinking = "\n\n".join(block.get("text", "") for block in thinking_blocks if block.get("text"))
            if combined_thinking:
                thinking_data = {
                    "content": combined_thinking,
                    "tokens": None,  # Anthropic doesn't provide separate token count for thinking
                }

        # Get current trace_id for observability correlation
        trace_id = self._get_current_trace_id()

        return {
            "id": response.id or f"chatcmpl-{uuid4().hex[:8]}",
            "message": message_data,
            "usage": usage_data,
            "model": response.model or model,
            "trace_id": trace_id,
            "thinking": thinking_data,
        }

    async def create_completion(self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """
        Create a chat completion.

        Tries MCP agent first (for full tool support), falls back to LiteLLM.

        Args:
            session_id: Session ID for tracking
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, max_tokens, user_id)

        Returns:
            Dict matching ChatCompletionResponse format
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.observability.telemetry import logger

        # Try MCP agent first if configured
        if self.mcp_bridge and self.mcp_bridge.is_configured:
            try:
                return await self._create_completion_via_mcp(session_id, messages, **kwargs)
            except ChatError as e:
                logger.warning(f"MCP agent failed, falling back to LiteLLM: {e}")

        # Fallback to LiteLLM
        return await self._create_completion_via_litellm(session_id, messages, **kwargs)

    async def _stream_via_mcp(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream completion using MCP agent."""
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError

        bridge = self.mcp_bridge
        if not bridge or not bridge.is_configured:
            raise ChatError("MCP bridge not configured")

        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        user_id = kwargs.get("user_id", "anonymous")

        async for chunk in bridge.stream_chat_message(
            session_id=session_id,
            message=last_user_message,
            user_id=user_id,
        ):
            if not chunk.is_final:
                yield {
                    "delta": {
                        "content": chunk.content,
                    },
                }

    async def _stream_via_litellm(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream completion using LiteLLM directly."""
        model = kwargs.get("model") or settings.model_name
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")
        reasoning_effort = kwargs.get("reasoning_effort")
        enable_thinking = kwargs.get("enable_thinking", True)

        # Inject resource context if provided
        resource_uris = kwargs.get("resource_uris")
        messages = await self._inject_resource_context(messages, resource_uris)

        # Build completion parameters
        completion_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # Add reasoning_effort for models that support extended thinking
        # Only add if thinking is enabled and the model supports it
        supports_thinking = model_supports_thinking(model)
        if supports_thinking and enable_thinking and reasoning_effort:
            completion_params["reasoning_effort"] = reasoning_effort

        response = await acompletion(**completion_params)

        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta
                chunk_data: dict[str, Any] = {
                    "delta": {
                        "content": delta.content if hasattr(delta, "content") else "",
                    },
                }

                # Include thinking content in stream if available
                # LiteLLM may stream thinking blocks or reasoning_content
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    chunk_data["delta"]["thinking"] = delta.reasoning_content
                elif hasattr(delta, "thinking") and delta.thinking:
                    chunk_data["delta"]["thinking"] = delta.thinking

                yield chunk_data

    async def _stream_via_langgraph(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream completion using LangGraph agent with astream_events.

        Emits:
        - langgraph_node: Node execution updates (name, type, status)
        - langgraph_edge: Edge traversals (from, to, condition)
        - current_node: Currently executing node ID
        - delta.content: Streaming content from LLM
        """
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.observability.telemetry import logger

        agent = self._langgraph_agent
        if not agent or not hasattr(agent, "astream_events"):
            raise ValueError("LangGraph agent not configured or doesn't support astream_events")

        # Build initial state from messages
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        initial_state = {
            "messages": [HumanMessage(content=last_user_message)],
            "next_action": "",
            "user_id": kwargs.get("user_id"),
            "request_id": session_id,
        }

        config = {"configurable": {"thread_id": session_id}}
        node_statuses: dict[str, str] = {}  # Track node statuses
        last_node: str | None = None

        try:
            async for event in agent.astream_events(initial_state, config=config, version="v2"):
                event_type = event.get("event", "")
                metadata = event.get("metadata", {})
                langgraph_node = metadata.get("langgraph_node")

                # Handle node start events
                if event_type == "on_chain_start" and langgraph_node:
                    node_name = langgraph_node
                    node_statuses[node_name] = "running"

                    # Emit current_node update
                    yield {"current_node": node_name}

                    # Emit langgraph_node event
                    yield {
                        "langgraph_node": {
                            "id": node_name,
                            "name": node_name,
                            "type": self._infer_node_type(node_name),
                            "status": "running",
                        }
                    }

                    # Emit edge from previous node if exists
                    if last_node and last_node != node_name:
                        yield {
                            "langgraph_edge": {
                                "from": last_node,
                                "to": node_name,
                            }
                        }

                    last_node = node_name

                # Handle node end events
                elif event_type == "on_chain_end" and langgraph_node:
                    node_name = langgraph_node
                    node_statuses[node_name] = "completed"

                    # Emit langgraph_node event with completed status
                    yield {
                        "langgraph_node": {
                            "id": node_name,
                            "name": node_name,
                            "type": self._infer_node_type(node_name),
                            "status": "completed",
                        }
                    }

                    # Check for triggered edges in metadata
                    triggers = metadata.get("langgraph_triggers", [])
                    for trigger in triggers:
                        yield {
                            "langgraph_edge": {
                                "from": node_name,
                                "to": trigger,
                            }
                        }

                # Handle streaming content from chat model
                elif event_type == "on_chat_model_stream":
                    data = event.get("data", {})
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {
                            "delta": {
                                "content": chunk.content,
                            }
                        }

        except Exception as e:
            logger.error(f"LangGraph streaming error: {e}", exc_info=True)
            raise

    def _infer_node_type(self, node_name: str) -> str:
        """Infer node type from name for visualization."""
        name_lower = node_name.lower()
        if name_lower in ("__start__", "start"):
            return "start"
        elif name_lower in ("__end__", "end"):
            return "end"
        elif "tool" in name_lower:
            return "tool"
        elif "router" in name_lower or "route" in name_lower:
            return "conditional"
        elif "agent" in name_lower:
            return "agent"
        return "default"

    async def create_stream(
        self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Create a streaming chat completion.

        Tries LangGraph (if use_langgraph=True), then MCP agent, then LiteLLM.

        Args:
            session_id: Session ID for tracking
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, max_tokens, user_id, use_langgraph)

        Yields:
            Streaming chunks with delta content and optional langgraph_node/edge events
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.observability.telemetry import logger

        use_langgraph = kwargs.pop("use_langgraph", False)

        # Try LangGraph agent if requested and configured
        if use_langgraph and self._langgraph_agent is not None:
            try:
                async for chunk in self._stream_via_langgraph(session_id, messages, **kwargs):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"LangGraph streaming failed, falling back: {e}")

        # Try MCP agent if configured
        if self.mcp_bridge and self.mcp_bridge.is_configured:
            try:
                async for chunk in self._stream_via_mcp(session_id, messages, **kwargs):
                    yield chunk
                return
            except ChatError as e:
                logger.warning(f"MCP streaming failed, falling back to LiteLLM: {e}")

        # Fallback to LiteLLM
        async for chunk in self._stream_via_litellm(session_id, messages, **kwargs):
            yield chunk

    async def get_history(self, session_id: str) -> list[dict[str, Any]] | None:
        """
        Get chat history for a session.

        Args:
            session_id: Session ID to retrieve history for

        Returns:
            List of messages or None if session not found.
            Returns empty list if no storage configured (graceful fallback).
        """
        if self._session_storage is None:
            # No storage configured - return empty list as graceful fallback
            return []

        # Delegate to storage backend
        result = await self._session_storage.get_messages(session_id)
        return list(result) if result is not None else None


# Service singleton
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get the chat service instance (returns ChatServiceImpl)."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatServiceImpl()
    return _chat_service


def set_chat_service(service: ChatService) -> None:
    """Set the chat service instance (for testing/DI)."""
    global _chat_service
    _chat_service = service


def reset_chat_service() -> None:
    """Reset the chat service singleton (for testing)."""
    global _chat_service
    _chat_service = None


# Endpoints


@chat_router.post("/chat/completions")
async def create_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """
    Create a chat completion.

    Sends messages to the LLM and returns the assistant's response.

    Raises:
        HTTPException 428: When MCP requires user elicitation (authentication, consent)
        HTTPException 403: When permission is denied
        HTTPException 503: When MCP server is unavailable
    """
    from mcp_server_langgraph.api.v1.mcp_bridge import (
        MCPConnectionError,
        MCPElicitationRequiredError,
        MCPPermissionError,
    )

    service = get_chat_service()
    messages = [msg.model_dump() for msg in request.messages]

    try:
        response = await service.create_completion(
            session_id=request.session_id,
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            resource_uris=request.resource_uris,
            reasoning_effort=request.reasoning_effort,
            enable_thinking=request.enable_thinking,
        )
        return ChatCompletionResponse(**response)
    except MCPElicitationRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"detail": str(e), "elicitations": e.elicitations},
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )


@chat_router.post("/chat/completions/stream")
async def create_stream(request: ChatCompletionRequest) -> StreamingResponse:
    """
    Create a streaming chat completion.

    Sends messages to the LLM and streams the response as Server-Sent Events.
    """
    service = get_chat_service()
    messages = [msg.model_dump() for msg in request.messages]

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in service.create_stream(
            session_id=request.session_id,
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            resource_uris=request.resource_uris,
            reasoning_effort=request.reasoning_effort,
            enable_thinking=request.enable_thinking,
        ):
            # Format as SSE
            import json

            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@chat_router.get("/chat/{session_id}/history")
async def get_history(session_id: str) -> list[dict[str, Any]]:
    """
    Get chat history for a session.

    Returns all messages in chronological order.
    """
    service = get_chat_service()
    history = await service.get_history(session_id)

    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return history
