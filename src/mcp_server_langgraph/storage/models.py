"""
Unified Storage Models

Provides consolidated Pydantic models for:
- Workflow: Visual workflow state with nodes and edges
- Session: Chat session with messages
- Message: Individual chat message
- CostRecord: LLM usage cost tracking

These models support both Redis and PostgreSQL storage backends.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Workflow(BaseModel):
    """Full workflow state for storage."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    id: str = Field(description="Unique workflow ID")
    name: str = Field(description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Workflow nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Workflow edges")
    user_id: str | None = Field(default=None, description="Owner user ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()

    def to_summary(self) -> "WorkflowSummary":
        """Convert to summary model for list responses."""
        return WorkflowSummary(
            id=self.id,
            name=self.name,
            description=self.description,
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class WorkflowSummary(BaseModel):
    """Summary of a workflow for list responses."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    node_count: int = Field(default=0, description="Number of nodes")
    edge_count: int = Field(default=0, description="Number of edges")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class SessionConfig(BaseModel):
    """Configuration for a chat session."""

    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=128000, description="Max tokens per response")


class Message(BaseModel):
    """A message in a chat session."""

    message_id: str = Field(description="Unique message ID")
    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Message timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()


class Session(BaseModel):
    """Full chat session state for storage."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    session_id: str = Field(description="Unique session ID")
    name: str = Field(description="Session name/title")
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    user_id: str | None = Field(default=None, description="Owner user ID")
    messages: list[Message] = Field(default_factory=list, description="Session messages")
    config: SessionConfig = Field(default_factory=SessionConfig, description="LLM configuration")
    status: str = Field(default="active", description="Session status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()

    def to_summary(self) -> "SessionSummary":
        """Convert to summary model for list responses."""
        return SessionSummary(
            session_id=self.session_id,
            name=self.name,
            workflow_id=self.workflow_id,
            message_count=len(self.messages),
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class SessionSummary(BaseModel):
    """Summary of a session for list responses."""

    session_id: str = Field(description="Session ID")
    name: str = Field(description="Session name")
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    message_count: int = Field(default=0, description="Number of messages")
    status: str = Field(default="active", description="Session status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class CostRecord(BaseModel):
    """Record of LLM usage cost."""

    id: str = Field(description="Unique record ID")
    session_id: str | None = Field(default=None, description="Associated session")
    workflow_id: str | None = Field(default=None, description="Associated workflow")
    user_id: str | None = Field(default=None, description="User ID")
    model: str = Field(description="LLM model used")
    prompt_tokens: int = Field(default=0, description="Prompt tokens used")
    completion_tokens: int = Field(default=0, description="Completion tokens used")
    total_tokens: int = Field(default=0, description="Total tokens used")
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Usage timestamp")

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()
