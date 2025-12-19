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


class ChatUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(description="Tokens in the prompt")
    completion_tokens: int = Field(description="Tokens in the completion")
    total_tokens: int | None = Field(default=None, description="Total tokens used")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""

    id: str = Field(description="Completion ID")
    message: ChatMessage = Field(description="Assistant's response message")
    usage: ChatUsage | None = Field(default=None, description="Token usage")
    model: str | None = Field(default=None, description="Model used")
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID for observability correlation")


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
    ) -> None:
        """
        Initialize with optional dependencies.

        Args:
            session_storage: Optional storage backend for session history.
                             If None, history will return empty list.
            mcp_bridge: Optional MCPBridge instance for agent communication.
                        If None, uses LiteLLM as fallback.
        """
        self._session_storage = session_storage
        self._mcp_bridge = mcp_bridge

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

        # Inject resource context if provided
        resource_uris = kwargs.get("resource_uris")
        messages = await self._inject_resource_context(messages, resource_uris)

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

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

        # Get current trace_id for observability correlation
        trace_id = self._get_current_trace_id()

        return {
            "id": response.id or f"chatcmpl-{uuid4().hex[:8]}",
            "message": message_data,
            "usage": usage_data,
            "model": response.model or model,
            "trace_id": trace_id,
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

        # Inject resource context if provided
        resource_uris = kwargs.get("resource_uris")
        messages = await self._inject_resource_context(messages, resource_uris)

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta
                yield {
                    "delta": {
                        "content": delta.content if hasattr(delta, "content") else "",
                    },
                }

    async def create_stream(
        self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Create a streaming chat completion.

        Tries MCP agent first (for full tool support), falls back to LiteLLM.

        Args:
            session_id: Session ID for tracking
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, max_tokens, user_id)

        Yields:
            Streaming chunks with delta content
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.observability.telemetry import logger

        # Try MCP agent first if configured
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
