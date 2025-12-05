"""
Playground API Models

Pydantic models for request/response validation in the Interactive Playground.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# Session Models
# ==============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new playground session."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name for the session",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize session name."""
        # Strip whitespace
        v = v.strip()
        if not v:
            msg = "Session name cannot be empty"
            raise ValueError(msg)
        return v


class Session(BaseModel):
    """Session model returned from API."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Session name")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    message_count: int = Field(0, description="Number of messages in session")


class SessionListResponse(BaseModel):
    """Response containing list of sessions."""

    sessions: list[Session] = Field(default_factory=list)
    total: int = Field(0, description="Total number of sessions")


# ==============================================================================
# Chat Models
# ==============================================================================


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    session_id: str = Field(..., description="Session to send message in")
    message: str = Field(
        ...,
        min_length=1,
        max_length=50_000,  # 50KB limit
        description="Message content",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message content."""
        if len(v) > 50_000:
            msg = "Message exceeds maximum length of 50,000 characters"
            raise ValueError(msg)
        return v


class ChatResponse(BaseModel):
    """Response from chat endpoint (non-streaming)."""

    message_id: str = Field(..., description="Unique message identifier")
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")


# ==============================================================================
# WebSocket Models
# ==============================================================================


class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages."""

    type: Literal[
        "message",
        "cancel",
        "ping",
        "connection_ack",
        "message_start",
        "token",
        "message_end",
        "cancelled",
        "pong",
        "error",
    ] = Field(..., description="Message type")


class WebSocketIncomingMessage(BaseModel):
    """Incoming WebSocket message from client."""

    type: Literal["message", "cancel", "ping"] = Field(..., description="Message type")
    content: str | None = Field(None, description="Message content (for type=message)")


class WebSocketOutgoingMessage(BaseModel):
    """Outgoing WebSocket message to client."""

    type: str = Field(..., description="Message type")
    session_id: str | None = Field(None, description="Session ID")
    message_id: str | None = Field(None, description="Message ID")
    content: str | None = Field(None, description="Content/token")
    timestamp: datetime | None = Field(None, description="Timestamp")
    message: str | None = Field(None, description="Error message")


# ==============================================================================
# Health Models
# ==============================================================================


class DependencyHealth(BaseModel):
    """Health status of a dependency."""

    status: Literal["healthy", "unhealthy", "unknown"] = "unknown"
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    version: str = Field(..., description="Playground API version")
    dependencies: dict[str, DependencyHealth] = Field(default_factory=dict)


# ==============================================================================
# API Info Models
# ==============================================================================


class APIInfoResponse(BaseModel):
    """API information response."""

    name: str = "Interactive Playground API"
    version: str = Field(..., description="API version")
    description: str = "Real-time chat interface for MCP Server LangGraph agents"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
