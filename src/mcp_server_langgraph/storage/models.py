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
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from mcp_server_langgraph.core.config import settings


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


# =============================================================================
# Project Models (Unified Workspace Paradigm)
# =============================================================================


class ProjectWorkflowRef(BaseModel):
    """Reference to a workflow within a project."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When added to project")


class ProjectSessionRef(BaseModel):
    """Reference to a session within a project."""

    id: str = Field(description="Session ID")
    name: str = Field(description="Session name")
    message_count: int = Field(default=0, description="Number of messages")
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When added to project")


class ProjectConnection(BaseModel):
    """Connection (MCP server, vector store, API key) within a project."""

    id: str = Field(description="Connection ID")
    connection_type: str = Field(description="Type: mcp_server, vector_store, api_key")
    name: str = Field(description="Connection name")
    status: str = Field(default="active", description="Connection status")
    config: dict[str, Any] | None = Field(default=None, description="Connection configuration")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")


class ProjectMember(BaseModel):
    """Member of a project with role."""

    user_id: str = Field(description="User ID")
    role: str = Field(description="Role: owner, editor, viewer, executor")
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When added")


class Project(BaseModel):
    """Full project state for storage (Unified Workspace container)."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    id: str = Field(description="Unique project ID")
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    organization_id: str | None = Field(default=None, description="Organization ID")
    owner_id: str = Field(description="Owner user ID")
    status: str = Field(default="active", description="Project status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")

    # Child resources
    workflows: list[ProjectWorkflowRef] = Field(default_factory=list, description="Workflows in project")
    sessions: list[ProjectSessionRef] = Field(default_factory=list, description="Sessions in project")
    connections: list[ProjectConnection] = Field(default_factory=list, description="Connections in project")
    members: list[ProjectMember] = Field(default_factory=list, description="Project members")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat()

    def to_summary(self) -> "ProjectSummary":
        """Convert to summary model for list responses."""
        return ProjectSummary(
            id=self.id,
            name=self.name,
            description=self.description,
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            status=self.status,
            workflow_count=len(self.workflows),
            session_count=len(self.sessions),
            connection_count=len(self.connections),
            member_count=len(self.members),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ProjectSummary(BaseModel):
    """Summary of a project for list responses."""

    id: str = Field(description="Project ID")
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    organization_id: str | None = Field(default=None, description="Organization ID")
    owner_id: str = Field(description="Owner user ID")
    status: str = Field(default="active", description="Project status")
    workflow_count: int = Field(default=0, description="Number of workflows")
    session_count: int = Field(default=0, description="Number of sessions")
    connection_count: int = Field(default=0, description="Number of connections")
    member_count: int = Field(default=0, description="Number of members")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


# =============================================================================
# MCP Connection Models (OAuth2 and API Key Authentication)
# =============================================================================

AuthType = Literal["none", "api_key", "oauth2"]
ConnectionStatus = Literal["disconnected", "connecting", "connected", "error", "auth_required"]
TransportProtocol = Literal["streamable_http", "stdio"]


class OAuth2Config(BaseModel):
    """OAuth2 configuration (client credentials only, not tokens)."""

    client_id: str | None = Field(default=None, description="OAuth2 client ID")
    authorization_url: str | None = Field(default=None, description="Authorization endpoint URL")
    token_url: str | None = Field(default=None, description="Token endpoint URL")
    scopes: list[str] = Field(default_factory=list, description="OAuth2 scopes")


class MCPConnection(BaseModel):
    """Full MCP connection entity for storage."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    id: str = Field(description="Unique connection ID")
    name: str = Field(description="Display name")
    description: str | None = Field(default=None, description="Connection description")
    url: str = Field(description="MCP server URL")

    # Transport (per MCP 2025-11-25 spec)
    transport: TransportProtocol = Field(default="streamable_http", description="Transport protocol")

    # Authentication
    auth_type: AuthType = Field(default="none", description="Authentication method")
    oauth2_config: OAuth2Config | None = Field(default=None, description="OAuth2 configuration")

    # Stdio transport configuration
    command: str | None = Field(default=None, description="Command to execute (stdio transport)")
    args: list[str] | None = Field(default=None, description="Command arguments (stdio transport)")
    env: dict[str, str] | None = Field(default=None, description="Environment variables (stdio transport)")

    # Connection state
    status: ConnectionStatus = Field(default="disconnected", description="Connection status")
    last_error: str | None = Field(default=None, description="Last error message")
    last_connected_at: datetime | None = Field(default=None, description="Last successful connection")

    # Server info (populated after successful connection)
    server_name: str | None = Field(default=None, description="MCP server name")
    server_version: str | None = Field(default=None, description="MCP server version")
    server_capabilities: dict[str, Any] | None = Field(default=None, description="Server capabilities")

    # Cached counts
    tool_count: int = Field(default=0, description="Number of tools available")
    resource_count: int = Field(default=0, description="Number of resources available")
    prompt_count: int = Field(default=0, description="Number of prompts available")

    # Ownership
    owner_id: str = Field(description="Owner user ID")
    organization_id: str | None = Field(default=None, description="Organization ID")
    project_id: str | None = Field(default=None, description="Project ID")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update timestamp")

    @field_serializer("created_at", "updated_at", "last_connected_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        return value.isoformat() if value else None

    def to_summary(self) -> "MCPConnectionSummary":
        """Convert to summary model for list responses."""
        return MCPConnectionSummary(
            id=self.id,
            name=self.name,
            url=self.url,
            transport=self.transport,
            auth_type=self.auth_type,
            status=self.status,
            server_name=self.server_name,
            tool_count=self.tool_count,
            resource_count=self.resource_count,
            prompt_count=self.prompt_count,
            last_connected_at=self.last_connected_at,
            created_at=self.created_at,
        )


class MCPConnectionSummary(BaseModel):
    """Summary of an MCP connection for list responses."""

    id: str = Field(description="Connection ID")
    name: str = Field(description="Display name")
    url: str = Field(description="MCP server URL")
    transport: TransportProtocol = Field(description="Transport protocol")
    auth_type: AuthType = Field(description="Authentication method")
    status: ConnectionStatus = Field(description="Connection status")
    server_name: str | None = Field(default=None, description="MCP server name")
    tool_count: int = Field(default=0, description="Number of tools available")
    resource_count: int = Field(default=0, description="Number of resources available")
    prompt_count: int = Field(default=0, description="Number of prompts available")
    last_connected_at: datetime | None = Field(default=None, description="Last successful connection")
    created_at: datetime = Field(description="Creation timestamp")


class MCPConnectionCreate(BaseModel):
    """Request model for creating an MCP connection."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: str | None = Field(default=None, max_length=2000, description="Description")
    url: str = Field(..., min_length=1, max_length=2048, description="MCP server URL")

    # Transport (per MCP 2025-11-25 spec)
    transport: TransportProtocol = Field(default="streamable_http", description="Transport protocol")

    # Authentication
    auth_type: AuthType = Field(default="none", description="Authentication method")

    # API Key auth (stored securely in secrets provider)
    api_key: str | None = Field(default=None, description="API key (stored securely)")

    # OAuth2 configuration
    oauth2_client_id: str | None = Field(default=None, description="OAuth2 client ID")
    oauth2_client_secret: str | None = Field(default=None, description="OAuth2 client secret (stored securely)")
    oauth2_scopes: list[str] | None = Field(default=None, description="OAuth2 scopes")

    # Stdio transport configuration
    command: str | None = Field(default=None, description="Command to execute (stdio transport)")
    args: list[str] | None = Field(default=None, description="Command arguments (stdio transport)")
    env: dict[str, str] | None = Field(default=None, description="Environment variables (stdio transport)")

    # Association
    project_id: str | None = Field(default=None, description="Project to associate with")


class MCPConnectionUpdate(BaseModel):
    """Request model for updating an MCP connection."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Display name")
    description: str | None = Field(default=None, max_length=2000, description="Description")
    url: str | None = Field(default=None, min_length=1, max_length=2048, description="MCP server URL")
    # Auth changes require separate endpoints for security


class MCPConnectionTestResult(BaseModel):
    """Result of testing an MCP connection."""

    success: bool = Field(description="Whether the test was successful")
    server_name: str | None = Field(default=None, description="MCP server name")
    server_version: str | None = Field(default=None, description="MCP server version")
    tool_count: int = Field(default=0, description="Number of tools available")
    resource_count: int = Field(default=0, description="Number of resources available")
    prompt_count: int = Field(default=0, description="Number of prompts available")
    latency_ms: float | None = Field(default=None, description="Connection latency in milliseconds")
    error: str | None = Field(default=None, description="Error message if test failed")


class OAuth2StartResponse(BaseModel):
    """Response from starting an OAuth2 authorization flow."""

    authorization_url: str = Field(description="URL to redirect user to for authorization")
    state: str = Field(description="State parameter for CSRF protection")
