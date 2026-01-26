"""
Session models for Redis-backed session storage.

Provides Pydantic models for session persistence:
- Session: Full session state with messages and config
- Message: Individual chat message with metadata
- SessionConfig: LLM configuration for the session

These models support JSON serialization for Redis storage.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings


class SessionConfig(BaseModel):
    """Configuration for a studio session."""

    model: str = Field(
        default_factory=lambda: settings.model_name,
        description="LLM model to use",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(
        default_factory=lambda: settings.model_max_tokens,
        ge=1,
        le=128000,
        description="Max tokens per response",
    )
    execution_mode: Literal["default", "plan", "auto_accept", "bypass"] = Field(
        default="default",
        description="Execution mode for bypass auto-approval: default, plan, auto_accept, bypass",
    )


class Message(BaseModel):
    """A message in a session.

    v8: Added user_id as required field for ownership tracking (Finding 53).
    SECURITY: Required for user-scoped message access control.
    """

    message_id: str
    role: str  # "user" or "assistant"
    content: str
    # v8: Explicit user_id field for ownership (Finding 53, Finding 56)
    user_id: str = Field(..., description="User ID who owns this message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Source citations for the message (web search results, KB references)",
    )


class Session(BaseModel):
    """Full session state for Redis storage.

    v8: Made user_id required for ownership tracking (Finding 56).
    SECURITY: All sessions must be owned by a user for access control.
    """

    session_id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    messages: list[Message] = Field(default_factory=list)
    config: SessionConfig = Field(default_factory=SessionConfig)
    # v8: Required, not Optional (Finding 56)
    user_id: str = Field(..., description="User ID who owns this session")
    status: str = Field(default="active", description="Session status: active, archived")
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
