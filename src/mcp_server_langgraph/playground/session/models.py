"""
Session models for Redis-backed session storage.

Provides Pydantic models for session persistence:
- Session: Full session state with messages and config
- Message: Individual chat message with metadata
- SessionConfig: LLM configuration for the session

These models support JSON serialization for Redis storage.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    """Configuration for a playground session."""

    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=128000, description="Max tokens per response")


class Message(BaseModel):
    """A message in a session."""

    message_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """Full session state for Redis storage."""

    session_id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    messages: list[Message] = Field(default_factory=list)
    config: SessionConfig = Field(default_factory=SessionConfig)
    user_id: str | None = None
