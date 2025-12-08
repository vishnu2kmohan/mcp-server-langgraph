"""
Workflow storage models for Redis-backed workflow storage.

Pydantic models for workflow CRUD operations.
These models support JSON serialization for Redis storage.
"""

from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class StoredWorkflow(BaseModel):
    """Full workflow state for Redis storage."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    id: str
    name: str
    description: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    user_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()


class WorkflowSummary(BaseModel):
    """Summary of a workflow for list responses."""

    id: str
    name: str
    description: str = ""
    node_count: int = 0
    edge_count: int = 0
    created_at: datetime
    updated_at: datetime
