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
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


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


# Service singleton
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get the chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def set_chat_service(service: ChatService) -> None:
    """Set the chat service instance (for testing/DI)."""
    global _chat_service
    _chat_service = service


# Endpoints


@chat_router.post("/chat/completions")
async def create_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """
    Create a chat completion.

    Sends messages to the LLM and returns the assistant's response.
    """
    service = get_chat_service()
    messages = [msg.model_dump() for msg in request.messages]

    response = await service.create_completion(
        session_id=request.session_id,
        messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    return ChatCompletionResponse(**response)


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
