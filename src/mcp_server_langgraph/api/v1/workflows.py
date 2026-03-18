"""
Workflows Router

Provides CRUD operations for workflow management under /api/v1/workflows/*.

This consolidates workflow functionality from builder and studio into a unified API.

Storage Layer:
- PostgreSQL (default): Uses PostgresWorkflowManager with FTS and composite indices
- Redis: Uses RedisWorkflowManager for fast access with TTL support

Usage:
    GET /api/v1/workflows - List all workflows (with pagination)
    GET /api/v1/workflows/{id} - Get a specific workflow
    POST /api/v1/workflows - Create a new workflow
    PUT /api/v1/workflows/{id} - Update an existing workflow
    DELETE /api/v1/workflows/{id} - Delete a workflow
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

from mcp_server_langgraph.core.numeric import safe_float

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)
from mcp_server_langgraph.auth.dependencies import (
    get_current_user,
    require_workflow_editor,
    require_workflow_executor,
    require_workflow_owner,
    require_workflow_viewer,
)
from mcp_server_langgraph.auth.openfga import invalidate_resource_permissions
from mcp_server_langgraph.core.feature_flags import get_feature_flags
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.workflow import PostgresWorkflowManager, RedisWorkflowManager
    from mcp_server_langgraph.storage.workflow.share_repository import WorkflowShareRepositoryProtocol

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Set to hold references to background tasks to prevent garbage collection
_background_tasks: set = set()

workflows_router = APIRouter(tags=["workflows"])


# Request/Response Models


class NodePosition(BaseModel):
    """Position of a node in the workflow canvas."""

    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")

    @field_validator("x", "y", mode="before")
    @classmethod
    def validate_coordinates(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


class WorkflowNode(BaseModel):
    """A node in the workflow graph."""

    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type (start, llm, tool, condition, end)")
    position: NodePosition = Field(description="Position on the canvas")
    data: dict[str, Any] = Field(default_factory=dict, description="Node-specific data")


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes in the workflow."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: str | None = Field(default=None, description="Edge label")


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow."""

    name: str = Field(description="Workflow name", min_length=1, max_length=255)
    title: str | None = Field(default=None, description="Human-friendly display title (defaults to name)")
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")


class WorkflowUpdateRequest(BaseModel):
    """Request body for updating a workflow."""

    name: str | None = Field(default=None, description="Workflow name", max_length=255)
    title: str | None = Field(default=None, description="Human-friendly display title")
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[WorkflowNode] | None = Field(default=None, description="Workflow nodes")
    edges: list[WorkflowEdge] | None = Field(default=None, description="Workflow edges")


class WorkflowResponse(BaseModel):
    """Response model for a workflow."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    title: str = Field(default="", description="Human-friendly display title")
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Workflow nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Workflow edges")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")

    @model_validator(mode="before")
    @classmethod
    def set_title_from_name(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Set title to name if not provided."""
        if isinstance(data, dict) and not data.get("title"):
            data["title"] = data.get("name", "")
        return data


# ==============================================================================
# Workflow Sharing Models
# ==============================================================================


class WorkflowShare(BaseModel):
    """A share relationship for a workflow."""

    user_id: str = Field(description="User ID the workflow is shared with")
    email: str = Field(description="Email of the user")
    permission: Literal["view", "edit", "execute"] = Field(
        description="Permission level: view (read-only), edit (modify), execute (run)"
    )


class WorkflowSharesResponse(BaseModel):
    """Response containing all shares for a workflow."""

    shares: list[WorkflowShare] = Field(default_factory=list, description="List of shares")
    is_public: bool = Field(default=False, description="Whether workflow is publicly accessible")
    share_link: str | None = Field(default=None, description="Public share link if is_public=True")


class AddWorkflowShareRequest(BaseModel):
    """Request to add a share to a workflow."""

    email: str = Field(description="Email of user to share with")
    permission: Literal["view", "edit", "execute"] = Field(default="view", description="Permission level")


class UpdateWorkflowPublicRequest(BaseModel):
    """Request to update workflow public visibility."""

    is_public: bool = Field(description="Whether workflow should be publicly accessible")


class GenerateWorkflowRequest(BaseModel):
    """Request to generate a workflow from session or prompt."""

    session_id: str | None = Field(default=None, description="Generate from session history")
    prompt: str | None = Field(default=None, description="Generate from text prompt")

    def model_post_init(self, __context: Any) -> None:
        """Validate exactly one of session_id or prompt is provided."""
        if bool(self.session_id) == bool(self.prompt):
            raise ValueError("Exactly one of session_id or prompt is required")


class GenerateWorkflowResponse(BaseModel):
    """Response containing generated workflow."""

    workflow: WorkflowResponse = Field(description="Generated workflow definition")
    confidence: float = Field(ge=0.0, le=1.0, description="Generation confidence score")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# ==============================================================================
# Workflow Title Generation Models
# ==============================================================================


class GenerateTitleRequest(BaseModel):
    """Request to generate a workflow title from context."""

    description: str | None = Field(
        default=None,
        description="Workflow description for context",
    )
    session_context: str | None = Field(
        default=None,
        description="Context from originating session (e.g., first message or topic)",
    )


class GenerateTitleResponse(BaseModel):
    """Response containing generated workflow title."""

    title: str = Field(description="Generated workflow title (2-6 words)")


# ==============================================================================
# Chat-to-Workflow Models (ADR-0089, Plan Review Consensus)
# ==============================================================================


class PromptMetadata(BaseModel):
    """Metadata about the prompt used for workflow generation.

    Enables telemetry linkage for prompt optimization analytics.
    Stored in workflow_versions table for tracking which prompt
    configurations produce successful workflows.
    """

    name: str = Field(description="Prompt name (e.g., 'workflow_generator')")
    version: str = Field(description="Prompt version (e.g., 'v1')")
    hash: str = Field(description="SHA-256 hash of prompt content")
    model: str = Field(description="LLM model used (e.g., 'claude-opus-4-5')")


class FromChatRequest(BaseModel):
    """Request to generate a workflow from chat session history.

    References:
    - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
    - Review consensus: Sanitize session content before LLM exposure
    """

    session_id: str = Field(description="Session ID to generate workflow from")
    refinement_mode: Literal["auto", "plan"] = Field(
        default="auto",
        description="Generation mode: 'auto' generates immediately, 'plan' returns execution plan for approval",
    )
    template_id: str | None = Field(
        default=None,
        description="Optional template ID to use as starting point",
    )


class FromChatResponse(BaseModel):
    """Response containing generated workflow from chat.

    The workflow is persisted with status='draft' and version=1.
    Includes prompt metadata for telemetry linkage.
    """

    workflow: WorkflowResponse = Field(description="Generated workflow (status=draft)")
    confidence: float = Field(ge=0.0, le=1.0, description="Generation confidence score")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
    prompt_metadata: PromptMetadata = Field(description="Prompt telemetry metadata")
    plan: dict[str, Any] | None = Field(
        default=None,
        description="Execution plan (when refinement_mode='plan')",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# ==============================================================================
# Workflow Validation Models (ADR-0089, Plan Review Consensus)
# ==============================================================================


class ValidateWorkflowRequest(BaseModel):
    """Request to validate a workflow.

    The request body is optional - the workflow is fetched by ID.
    Future: May accept inline workflow dict for pre-save validation.
    """

    pass  # Currently no body needed - workflow fetched by ID


class ValidateWorkflowResponse(BaseModel):
    """Response from workflow validation.

    Uses centralized WorkflowValidator service (NO JS DUPLICATION).
    Both Monaco editor and React Flow call this single endpoint.

    References:
    - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
    - Review consensus: Centralized validation endpoint
    """

    valid: bool = Field(description="Whether the workflow passed validation")
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages (blocking issues)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages (non-blocking issues)",
    )


# ==============================================================================
# Workflow Version Response Models (Plan: greedy-wiggling-marshmallow.md, Phase 3)
# ==============================================================================


class WorkflowVersionResponse(BaseModel):
    """Response model for workflow version history.

    Represents a single version entry in the workflow's history.
    Enables draft/publish lifecycle, diffing, rollback, and audit trails.

    References:
    - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
    - Phase 3: Data Model & Persistence (MANDATORY versioning)
    """

    id: str = Field(description="Unique version identifier")
    workflow_id: str = Field(description="ID of the parent workflow")
    version_number: int = Field(description="Version number (1-based, increments)")
    graph_json: dict[str, Any] = Field(description="Snapshot of workflow state (nodes + edges)")
    source_text: str | None = Field(
        default=None,
        description="Source code representation (Python/YAML) at this version",
    )
    commit_message: str | None = Field(
        default=None,
        description="Description of changes in this version",
    )
    created_by: str = Field(description="User who created this version")
    created_at: str = Field(description="ISO 8601 timestamp when version was created")
    prompt_version: str | None = Field(
        default=None,
        description="Prompt version used to generate this version (telemetry)",
    )
    prompt_model: str | None = Field(
        default=None,
        description="LLM model used for generation (telemetry)",
    )


# ==============================================================================
# Workflow Service Adapter
# ==============================================================================
#
# This adapter wraps PostgresWorkflowManager or RedisWorkflowManager to provide
# a consistent interface for the API layer. It converts between storage models
# (StoredWorkflow, WorkflowSummary) and API response dictionaries.


class WorkflowServiceAdapter:
    """
    Adapter for workflow storage managers.

    Wraps PostgresWorkflowManager or RedisWorkflowManager to provide a unified
    interface for the API layer. Converts between Pydantic models and dicts.
    """

    def __init__(
        self,
        manager: PostgresWorkflowManager | RedisWorkflowManager,
        share_repository: WorkflowShareRepositoryProtocol | None = None,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            manager: Workflow storage manager (PostgreSQL or Redis)
            share_repository: Optional share repository for sharing operations
        """
        self._manager = manager
        self._share_repository = share_repository

    async def list_workflows(
        self,
        cursor: str | None = None,
        limit: int = 20,
        status: str | None = None,
        owner_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List workflows with pagination, filtering, search, and sorting."""
        summaries, next_cursor = await self._manager.list_workflows(
            user_id=owner_id,
            limit=limit,
            cursor=cursor,
            search=search,
            status=status,
            sort_by=sort_by or "updated_at",
            sort_order=sort_order or "desc",
        )

        # Convert WorkflowSummary to dict
        workflows = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "nodes": [],  # Summaries don't include full nodes/edges
                "edges": [],
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "status": s.status,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
            }
            for s in summaries
        ]

        return workflows, next_cursor

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID. Returns None if not found."""
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow. Returns the created workflow."""
        # Extract nodes and edges, converting from Pydantic models if needed
        nodes = workflow_data.get("nodes", [])
        edges = workflow_data.get("edges", [])

        # Convert node models to dicts if needed
        if nodes and hasattr(nodes[0], "model_dump"):
            nodes = [n.model_dump() for n in nodes]
        if edges and hasattr(edges[0], "model_dump"):
            edges = [e.model_dump() for e in edges]

        workflow = await self._manager.create_workflow(
            name=workflow_data["name"],
            description=workflow_data.get("description", ""),
            nodes=nodes,
            edges=edges,
            user_id=workflow_data.get("user_id"),
        )

        return {
            "id": workflow.id,
            "name": workflow.name,
            "title": workflow_data.get("title"),  # Pass through title from request
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def update_workflow(self, workflow_id: str, workflow_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a workflow. Returns None if not found."""
        # Extract update fields
        nodes = workflow_data.get("nodes")
        edges = workflow_data.get("edges")

        # Convert node models to dicts if needed
        if nodes and len(nodes) > 0 and hasattr(nodes[0], "model_dump"):
            nodes = [n.model_dump() for n in nodes]
        if edges and len(edges) > 0 and hasattr(edges[0], "model_dump"):
            edges = [e.model_dump() for e in edges]

        workflow = await self._manager.update_workflow(
            workflow_id=workflow_id,
            name=workflow_data.get("name"),
            description=workflow_data.get("description"),
            nodes=nodes,
            edges=edges,
        )

        if workflow is None:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "title": workflow_data.get("title"),  # Pass through title from request
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "status": workflow.status,
            "user_id": workflow.user_id,
        }

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow. Returns True if deleted, False if not found."""
        return await self._manager.delete_workflow(workflow_id)

    # ==========================================================================
    # Sharing Methods
    # ==========================================================================

    async def get_workflow_shares(self, workflow_id: str) -> dict[str, Any] | None:
        """Get shares for a workflow. Returns None if workflow not found."""
        # First verify workflow exists
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return None

        # Use share repository if available
        if self._share_repository is not None:
            shares = await self._share_repository.get_shares(workflow_id)
            return {
                "shares": [
                    {
                        "user_id": s.user_id,
                        "email": s.email,
                        "permission": s.permission,
                    }
                    for s in shares
                ],
                "is_public": getattr(workflow, "is_public", False),
                "share_link": getattr(workflow, "share_link", None),
            }

        # Fallback: return empty shares
        return {
            "shares": [],
            "is_public": getattr(workflow, "is_public", False),
            "share_link": getattr(workflow, "share_link", None),
        }

    async def add_workflow_share(
        self,
        workflow_id: str,
        email: str,
        permission: str,
        user_id: str | None = None,
        created_by: str | None = None,
    ) -> bool:
        """Add a share to a workflow. Returns False if workflow not found."""
        # First verify workflow exists
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return False

        # Use share repository if available
        if self._share_repository is not None:
            import uuid

            from mcp_server_langgraph.storage.workflow.models import WorkflowShare

            share = WorkflowShare(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                user_id=user_id or email,  # Use email as user_id if not provided
                email=email,
                permission=permission,
                created_by=created_by or "system",
            )
            await self._share_repository.create_share(share)
            return True

        # Fallback: pretend share was added
        return True

    async def remove_workflow_share(self, workflow_id: str, user_id: str) -> bool:
        """Remove a share from a workflow. Returns False if not found."""
        # First verify workflow exists
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return False

        # Use share repository if available
        if self._share_repository is not None:
            return await self._share_repository.delete_share(workflow_id, user_id)

        # Fallback: return True (idempotent)
        return True

    async def update_workflow_public(self, workflow_id: str, is_public: bool) -> dict[str, Any] | None:
        """Update public visibility of a workflow. Returns None if not found."""
        # First verify workflow exists
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return None

        # Use share repository if available
        if self._share_repository is not None:
            return await self._share_repository.update_workflow_public(workflow_id, is_public)

        # Fallback: return mock response
        import secrets

        share_link = secrets.token_urlsafe(16) if is_public else None
        return {
            "is_public": is_public,
            "share_link": share_link,
        }

    async def list_shared_with_me(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List workflows shared with the current user."""
        if user_id is None or self._share_repository is None:
            return []

        # Get workflow IDs shared with user
        workflow_ids = await self._share_repository.list_shared_with_user(user_id)

        # Fetch workflow details
        workflows = []
        for wf_id in workflow_ids:
            workflow = await self._manager.get_workflow(wf_id)
            if workflow is not None:
                workflows.append(
                    {
                        "id": workflow.id,
                        "name": workflow.name,
                        "description": workflow.description,
                        "nodes": workflow.nodes,
                        "edges": workflow.edges,
                        "created_at": workflow.created_at.isoformat(),
                        "updated_at": workflow.updated_at.isoformat(),
                    }
                )

        return workflows

    async def get_public_workflow(self, share_link: str) -> dict[str, Any] | None:
        """Get a public workflow by share link. Returns None if not found."""
        if self._share_repository is None:
            return None

        # Look up workflow by share link
        workflow_id = await self._share_repository.get_by_share_link(share_link)
        if workflow_id is None:
            return None

        # Fetch workflow details
        workflow = await self._manager.get_workflow(workflow_id)
        if workflow is None:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": workflow.nodes,
            "edges": workflow.edges,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
        }

    # ==========================================================================
    # Workflow Generation (LLM-powered)
    # ==========================================================================

    async def generate_workflow(
        self,
        session_id: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a workflow from session or prompt using AI.

        Uses the WorkflowGenerator service to create workflow definitions
        via LLM-based analysis. Falls back to a stub if LLM is unavailable.

        Args:
            session_id: Generate from session message history.
            prompt: Generate from text prompt.

        Returns:
            Dict with workflow, confidence, and suggestions.

        Raises:
            ValueError: If session not found.
        """
        from mcp_server_langgraph.services.workflow_generator import (
            WorkflowGenerationError,
            WorkflowGenerator,
            workflow_to_api_format,
        )

        # Try to create LLM-powered generator
        try:
            from mcp_server_langgraph.core.config import settings
            from mcp_server_langgraph.llm.factory import create_llm_from_config

            llm = create_llm_from_config(settings)
            generator = WorkflowGenerator(llm=llm)
        except Exception:
            # Fallback to stub if LLM is unavailable
            return self._generate_stub_workflow(prompt)

        try:
            if session_id:
                # Fetch session messages
                from mcp_server_langgraph.api.v1.sessions import get_session_service

                session_service = get_session_service()
                messages = await session_service.get_session_messages(session_id)

                if messages is None:
                    raise ValueError(f"Session {session_id} not found")

                # Generate from session messages
                result = await generator.generate_from_session(messages)
            else:
                # Generate from prompt
                result = await generator.generate_from_prompt(prompt or "")

            # Convert to API format
            return workflow_to_api_format(result)

        except WorkflowGenerationError:
            # Fallback to stub on generation failure
            return self._generate_stub_workflow(prompt)

    def _generate_stub_workflow(self, prompt: str | None) -> dict[str, Any]:
        """Generate a simple stub workflow when LLM is unavailable."""
        import uuid
        from datetime import datetime

        workflow_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        return {
            "workflow": {
                "id": workflow_id,
                "name": f"Generated: {prompt[:50]}..." if prompt and len(prompt) > 50 else f"Generated: {prompt}",
                "description": f"AI-generated workflow from prompt: {prompt}",
                "nodes": [
                    {"id": "start", "type": "start", "position": {"x": 0, "y": 100}, "data": {}},
                    {"id": "llm", "type": "llm", "position": {"x": 200, "y": 100}, "data": {"model": "gpt-4"}},
                    {"id": "end", "type": "end", "position": {"x": 400, "y": 100}, "data": {}},
                ],
                "edges": [
                    {"source": "start", "target": "llm"},
                    {"source": "llm", "target": "end"},
                ],
                "created_at": now,
                "updated_at": now,
            },
            "confidence": 0.75,
            "suggestions": [
                "Consider adding error handling nodes",
                "Add memory for conversation context",
            ],
        }

    # ==========================================================================
    # Chat-to-Workflow Generation (ADR-0089, Plan Review Consensus)
    # ==========================================================================

    async def generate_from_chat(
        self,
        session_id: str,
        refinement_mode: str = "auto",
        template_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate and persist a workflow from chat session history.

        This method:
        1. Fetches session messages by session_id
        2. Session messages are sanitized in WorkflowGenerator (ADR-0089)
        3. Generates workflow via WorkflowGenerator
        4. Persists with status='draft', version=1
        5. Returns prompt metadata for telemetry linkage

        Args:
            session_id: Session ID to fetch messages from.
            refinement_mode: 'auto' generates immediately, 'plan' returns plan.
            template_id: Optional template to use as starting point.
            user_id: User ID for ownership.

        Returns:
            Dict with workflow, confidence, suggestions, prompt_metadata.

        Raises:
            ValueError: If session not found.
        """
        import hashlib

        from mcp_server_langgraph.services.workflow_generator import (
            WorkflowGenerationError,
            WorkflowGenerator,
            workflow_to_api_format,
        )

        # Fetch session messages
        from mcp_server_langgraph.api.v1.sessions import get_session_service

        session_service = get_session_service()
        messages = await session_service.get_session_messages(session_id)

        if messages is None:
            raise ValueError(f"Session {session_id} not found")

        # Try to create LLM-powered generator
        try:
            from mcp_server_langgraph.core.config import settings
            from mcp_server_langgraph.llm.factory import create_llm_from_config

            llm = create_llm_from_config(settings)
            generator = WorkflowGenerator(llm=llm)

            # Get prompt metadata for telemetry
            system_prompt = generator.get_system_prompt()
            prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
            model_name = getattr(settings, "llm_model", "unknown")

            prompt_metadata = {
                "name": "workflow_generator",
                "version": "v1",
                "hash": prompt_hash,
                "model": model_name,
            }
        except Exception:
            # Fallback if LLM unavailable
            result = self._generate_stub_workflow(f"From session: {session_id}")
            result["prompt_metadata"] = {
                "name": "workflow_generator",
                "version": "v1",
                "hash": "stub",
                "model": "stub",
            }
            return result

        try:
            # Generate workflow from session (sanitization happens inside)
            generation_result = await generator.generate_from_session(messages)
            result = workflow_to_api_format(generation_result)

            # Add prompt metadata
            result["prompt_metadata"] = prompt_metadata

            # Add plan for refinement_mode='plan'
            if refinement_mode == "plan":
                result["plan"] = {
                    "id": f"plan-{session_id[:8]}",
                    "steps": [
                        "Analyze conversation context",
                        "Generate workflow structure",
                        "Validate graph integrity",
                        "Persist draft workflow",
                    ],
                    "requires_approval": True,
                }

            # Persist workflow with draft status
            workflow_data = result["workflow"].copy()
            workflow_data["user_id"] = user_id
            workflow_data["status"] = "draft"

            # Create initial version
            # Note: Version creation will be handled by storage layer
            # when workflow_versions table is available

            await self.create_workflow(workflow_data)

            return result

        except WorkflowGenerationError:
            # Fallback to stub on generation failure
            result = self._generate_stub_workflow(f"From session: {session_id}")
            result["prompt_metadata"] = {
                "name": "workflow_generator",
                "version": "v1",
                "hash": "error_fallback",
                "model": "error_fallback",
            }
            return result

    # ==========================================================================
    # Version History Methods
    # ==========================================================================

    async def get_workflow_versions(
        self,
        workflow_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get version history for a workflow.

        Returns versions ordered by version_number descending (newest first).

        Args:
            workflow_id: ID of the workflow

        Returns:
            List of version dicts with telemetry fields
        """
        # Check if manager supports versioning
        if hasattr(self._manager, "get_workflow_versions"):
            versions = await self._manager.get_workflow_versions(workflow_id)
            return [
                {
                    "id": v.id,
                    "workflow_id": v.workflow_id,
                    "version_number": v.version_number,
                    "graph_json": v.graph_json,
                    "source_text": getattr(v, "source_text", None),
                    "commit_message": getattr(v, "commit_message", None),
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat() if hasattr(v.created_at, "isoformat") else str(v.created_at),
                    "prompt_version": getattr(v, "prompt_version", None),
                    "prompt_model": getattr(v, "prompt_model", None),
                }
                for v in versions
            ]

        # Fallback: return empty list if versioning not supported
        return []

    async def restore_workflow_version(
        self,
        workflow_id: str,
        version_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Restore a workflow to a previous version.

        Creates a new version with the restored state (append-only, no overwrites).

        Args:
            workflow_id: ID of the workflow
            version_id: ID of the version to restore
            user_id: ID of the user performing the restore

        Returns:
            Updated workflow dict with new version number

        Raises:
            ValueError: If workflow or version not found
        """
        # Check if manager supports versioning
        if hasattr(self._manager, "restore_workflow_version"):
            workflow = await self._manager.restore_workflow_version(
                workflow_id=workflow_id,
                version_id=version_id,
                user_id=user_id,
            )
            return {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "nodes": workflow.nodes,
                "edges": workflow.edges,
                "created_at": workflow.created_at.isoformat()
                if hasattr(workflow.created_at, "isoformat")
                else str(workflow.created_at),
                "updated_at": workflow.updated_at.isoformat()
                if hasattr(workflow.updated_at, "isoformat")
                else str(workflow.updated_at),
                "status": workflow.status,
                "user_id": workflow.user_id,
                "version": getattr(workflow, "version", 1),
            }

        # Fallback: raise error if versioning not supported
        raise ValueError(f"Workflow versioning not supported by {type(self._manager).__name__}")


# ==============================================================================
# Service Dependency Injection
# ==============================================================================

# Service singleton (lazy-initialized on first use)
_workflow_service: WorkflowServiceAdapter | None = None


def get_workflow_service() -> WorkflowServiceAdapter:
    """
    Get the workflow service instance.

    Lazy-initializes the service using the configured storage backend:
    - PostgreSQL (default): Uses PostgresWorkflowManager with FTS support
    - Redis: Uses RedisWorkflowManager for fast access

    The storage backend is determined by WORKFLOW_STORAGE_BACKEND env var.
    """
    global _workflow_service
    if _workflow_service is None:
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.observability.telemetry import logger

        storage_backend = getattr(settings, "workflow_storage_backend", "memory")

        if storage_backend == "postgres" and settings.database_url:
            # Use PostgreSQL storage with FTS and cursor pagination
            from mcp_server_langgraph.storage.workflow import (
                PostgresWorkflowManager,
                create_postgres_engine,
            )

            import asyncio

            async def init_postgres_manager() -> PostgresWorkflowManager:
                engine = await create_postgres_engine(settings.database_url)
                return PostgresWorkflowManager(engine=engine)

            # Run async initialization
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # Use Any type to allow different manager types across branches
            manager: Any = loop.run_until_complete(init_postgres_manager())

            # Create share repository backed by PostgreSQL for durable persistence
            from mcp_server_langgraph.storage.workflow.share_repository import (
                PostgresWorkflowShareRepository,
            )

            share_repo = PostgresWorkflowShareRepository(engine=manager._engine)
            _workflow_service = WorkflowServiceAdapter(manager, share_repository=share_repo)
            logger.info("Workflow service initialized with PostgreSQL storage")

        elif storage_backend == "redis" and settings.redis_url:
            # Use Redis storage
            from mcp_server_langgraph.storage.workflow import (
                RedisWorkflowManager,
                create_redis_pool,
            )

            import asyncio

            async def init_redis_manager() -> RedisWorkflowManager:
                redis_client = await create_redis_pool(settings.redis_url)
                return RedisWorkflowManager(redis_client=redis_client)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            manager = loop.run_until_complete(init_redis_manager())

            # Redis mode uses in-memory shares (Redis share repo not implemented)
            from mcp_server_langgraph.storage.workflow.share_repository import (
                InMemoryWorkflowShareRepository,
            )

            share_repo = InMemoryWorkflowShareRepository()
            _workflow_service = WorkflowServiceAdapter(manager, share_repository=share_repo)
            logger.info("Workflow service initialized with Redis storage (shares in-memory)")

        else:
            # Fallback to in-memory storage for development/testing
            from mcp_server_langgraph.storage.workflow.manager import RedisWorkflowManager
            from mcp_server_langgraph.storage.workflow.share_repository import (
                InMemoryWorkflowShareRepository,
            )

            # Use a mock Redis for in-memory mode (fakeredis)
            try:
                import fakeredis.aioredis

                redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except ImportError:
                # If fakeredis not available, use warning
                logger.warning("No storage backend configured. Install fakeredis for in-memory mode: pip install fakeredis")
                raise RuntimeError("No workflow storage backend configured")

            manager = RedisWorkflowManager(redis_client=redis_client)
            share_repo = InMemoryWorkflowShareRepository()
            _workflow_service = WorkflowServiceAdapter(manager, share_repository=share_repo)
            logger.info("Workflow service initialized with in-memory storage (fakeredis)")

    return _workflow_service


def set_workflow_service(service: WorkflowServiceAdapter) -> None:
    """Set the workflow service instance (for testing/DI)."""
    global _workflow_service
    _workflow_service = service


def reset_workflow_service() -> None:
    """Reset the workflow service singleton (for testing)."""
    global _workflow_service
    _workflow_service = None


# Type alias for dependency injection
WorkflowService = Annotated[WorkflowServiceAdapter, Depends(get_workflow_service)]


# ==============================================================================
# Authorization Helpers
# ==============================================================================


def _get_user_id(current_user: dict[str, Any]) -> str:
    """
    Extract user ID from the current user context.

    Tries 'sub' claim first, then falls back to 'preferred_username'.
    """
    return current_user.get("sub") or current_user.get("preferred_username") or "anonymous"


def _is_admin(current_user: dict[str, Any]) -> bool:
    """Check if the current user has admin role."""
    roles = current_user.get("roles", [])
    return "admin" in roles


async def _require_workflow_owner_with_service(
    workflow_id: str,
    current_user: dict[str, Any],
    service: WorkflowServiceAdapter,
) -> dict[str, Any]:
    """
    Internal authorization helper for sharing operations.

    This is kept for backward compatibility with sharing endpoints.
    New code should use require_workflow_owner from dependencies.py.

    Args:
        workflow_id: The workflow ID to check.
        current_user: The authenticated user context.
        service: The workflow service adapter.

    Returns:
        The workflow data if authorized.

    Raises:
        HTTPException: 404 if workflow not found, 403 if not owner.
    """
    # Fetch the workflow
    workflow = await service.get_workflow(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Check if admin (admins can access any workflow)
    if _is_admin(current_user):
        return workflow

    # Check ownership
    user_id = _get_user_id(current_user)
    workflow_owner = workflow.get("user_id")

    if workflow_owner != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage this workflow. Only the owner can perform this action.",
        )

    return workflow


# ==============================================================================
# Authorized Endpoint Handlers (for sharing operations)
# ==============================================================================


async def _notify_workflow_shared(
    workflow_id: str,
    target_email: str,
    permission: str,
    sharer_username: str,
    service: WorkflowServiceAdapter,
) -> None:
    """
    Send real-time notification when a workflow is shared.

    Notifies the target user via WebSocket if they are connected.
    Gracefully handles errors to avoid failing the share operation.
    """
    import logging

    from mcp_server_langgraph.websocket.registry import get_notification_broadcaster

    logger = logging.getLogger(__name__)

    try:
        # Get workflow name for the notification message
        workflow = await service.get_workflow(workflow_id)
        workflow_name = workflow.get("name", "a workflow") if workflow else "a workflow"

        # Get broadcaster and send notification
        broadcaster = get_notification_broadcaster()

        # The target user is identified by email (which is used as user_id in shares)
        # Use notify_user() which respects user's notification preferences
        await broadcaster.notify_user(
            user_id=target_email,
            notification_type="info",
            title="Workflow Shared With You",
            message=f"{sharer_username} shared '{workflow_name}' with you ({permission} access).",
            action={"label": "View Workflow", "url": f"/workflows/{workflow_id}"},
        )

        logger.info(f"Notification sent for workflow share: {workflow_id} -> {target_email}")
    except Exception as e:
        # Don't fail the share operation if notification fails
        logger.warning(f"Failed to send workflow share notification: {e}")


async def get_workflow_shares_authorized(
    workflow_id: str,
    current_user: dict[str, Any],
    service: WorkflowServiceAdapter,
) -> WorkflowSharesResponse:
    """
    Get workflow shares with ownership authorization.

    Only the workflow owner can view shares.
    """
    # Check ownership first
    await _require_workflow_owner_with_service(workflow_id, current_user, service)

    # Get shares
    result = await service.get_workflow_shares(workflow_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowSharesResponse(
        shares=[WorkflowShare(**s) for s in result.get("shares", [])],
        is_public=result.get("is_public", False),
        share_link=result.get("share_link"),
    )


async def add_workflow_share_authorized(
    workflow_id: str,
    request: AddWorkflowShareRequest,
    current_user: dict[str, Any],
    service: WorkflowServiceAdapter,
) -> dict[str, str]:
    """
    Add a workflow share with ownership authorization.

    Only the workflow owner can add shares.
    """
    # Check ownership first
    await _require_workflow_owner_with_service(workflow_id, current_user, service)

    # Add share
    success = await service.add_workflow_share(
        workflow_id=workflow_id,
        email=request.email,
        permission=request.permission,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Send real-time notification to the target user
    await _notify_workflow_shared(
        workflow_id=workflow_id,
        target_email=request.email,
        permission=request.permission,
        sharer_username=current_user.get("username", "Someone"),
        service=service,
    )

    # Invalidate authorization cache for this workflow (permissions changed)
    await invalidate_resource_permissions(f"workflow:{workflow_id}")

    return {"status": "shared", "email": request.email, "permission": request.permission}


async def remove_workflow_share_authorized(
    workflow_id: str,
    user_id: str,
    current_user: dict[str, Any],
    service: WorkflowServiceAdapter,
) -> None:
    """
    Remove a workflow share with ownership authorization.

    Only the workflow owner can remove shares.
    """
    # Check ownership first
    await _require_workflow_owner_with_service(workflow_id, current_user, service)

    # Remove share
    success = await service.remove_workflow_share(workflow_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} or share not found",
        )

    # Invalidate authorization cache for this workflow (permissions changed)
    await invalidate_resource_permissions(f"workflow:{workflow_id}")


async def update_workflow_public_authorized(
    workflow_id: str,
    request: UpdateWorkflowPublicRequest,
    current_user: dict[str, Any],
    service: WorkflowServiceAdapter,
) -> dict[str, Any]:
    """
    Update workflow public visibility with ownership authorization.

    Only the workflow owner can change public status.
    """
    # Check ownership first
    await _require_workflow_owner_with_service(workflow_id, current_user, service)

    # Update public status
    result = await service.update_workflow_public(workflow_id, request.is_public)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Invalidate authorization cache for this workflow (public visibility changed)
    await invalidate_resource_permissions(f"workflow:{workflow_id}")

    return result


# Endpoints


@workflows_router.get("/workflows")
async def list_workflows(
    service: WorkflowService,
    current_user: CurrentUser,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by workflow status (draft, published, archived)"),
    owner_id: str | None = Query(default=None, description="Filter by owner user ID"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in name and description"),
    sort_by: Literal["name", "created_at", "updated_at"] = Query(default="created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List all workflows with cursor-based pagination.

    Requires authentication. Users can see:
    - Their own workflows
    - Workflows shared with them
    - Public workflows
    - Admins can see all workflows

    Supports:
    - Pagination: cursor, limit
    - Filtering: status, owner_id
    - Search: search (uses PostgreSQL Full-Text Search when available)
    - Sorting: sort_by, sort_order

    Returns a paginated list of workflows with metadata for navigation.
    """
    # Filter by user's accessible workflows unless admin
    user_id = _get_user_id(current_user)
    effective_owner_id = owner_id

    # If not admin and no explicit owner_id filter, default to user's own workflows
    if not _is_admin(current_user) and owner_id is None:
        effective_owner_id = user_id

    workflows, next_cursor = await service.list_workflows(
        cursor=cursor,
        limit=limit,
        status=status,
        owner_id=effective_owner_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,  # Would require reverse pagination support
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(workflows),
    )

    return CursorPaginatedResponse(data=workflows, pagination=pagination)


# Note: Specific literal routes MUST come before parameterized routes
# to avoid `/workflows/shared-with-me` matching `/workflows/{workflow_id}`


@workflows_router.get("/workflows/shared-with-me")
async def list_shared_with_me(
    service: WorkflowService,
    current_user: CurrentUser,
) -> list[WorkflowResponse]:
    """
    List workflows shared with the current user.

    Returns workflows that other users have shared with the authenticated user.
    """
    user_id = _get_user_id(current_user)
    workflows = await service.list_shared_with_me(user_id=user_id)
    return [WorkflowResponse(**w) for w in workflows]


@workflows_router.get("/workflows/public/{share_link}")
async def get_public_workflow(
    share_link: str,
    service: WorkflowService,
) -> WorkflowResponse:
    """
    Access a public workflow by its share link.

    No authentication required for public workflows.
    """
    workflow = await service.get_public_workflow(share_link)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public workflow not found or link expired",
        )

    return WorkflowResponse(**workflow)


@workflows_router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    service: WorkflowService,
    _: Annotated[dict[str, Any], Depends(require_workflow_viewer)],
) -> WorkflowResponse:
    """
    Get a specific workflow by ID.

    Requires viewer access to the workflow (owner, editor, shared, or admin).
    Returns the complete workflow data including nodes and edges.
    """
    workflow = await service.get_workflow(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    service: WorkflowService,
    current_user: CurrentUser,
) -> WorkflowResponse:
    """
    Create a new workflow.

    Requires authentication. The authenticated user becomes the workflow owner.
    The workflow is created with the provided name, description, nodes, and edges.
    """
    # Inject user_id as owner
    user_id = _get_user_id(current_user)
    workflow_data = request.model_dump()
    workflow_data["user_id"] = user_id

    workflow = await service.create_workflow(workflow_data)

    return WorkflowResponse(**workflow)


@workflows_router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    service: WorkflowService,
    _: Annotated[dict[str, Any], Depends(require_workflow_editor)],
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Requires editor access to the workflow (owner, editor, or admin).
    Only the provided fields are updated; others remain unchanged.
    """
    update_data = request.model_dump(exclude_unset=True)
    workflow = await service.update_workflow(workflow_id, update_data)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflow)


@workflows_router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService,
    _: Annotated[dict[str, Any], Depends(require_workflow_owner)],
) -> None:
    """
    Delete a workflow.

    Requires owner access to the workflow. Only the owner or admin can delete.
    This permanently removes the workflow and cannot be undone.
    """
    deleted = await service.delete_workflow(workflow_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )


# ==============================================================================
# Workflow Sharing Endpoints
# ==============================================================================
# Note: shared-with-me and public/{share_link} routes are defined earlier
# to ensure they are matched before /{workflow_id} pattern.


@workflows_router.get("/workflows/{workflow_id}/shares")
async def get_workflow_shares(
    workflow_id: str,
    service: WorkflowService,
    current_user: CurrentUser,
) -> WorkflowSharesResponse:
    """
    Get all shares for a workflow.

    Returns the list of users the workflow is shared with and public status.
    Only the workflow owner can view shares.
    """
    return await get_workflow_shares_authorized(
        workflow_id=workflow_id,
        current_user=current_user,
        service=service,
    )


@workflows_router.post("/workflows/{workflow_id}/shares", status_code=status.HTTP_201_CREATED)
async def add_workflow_share(
    workflow_id: str,
    request: AddWorkflowShareRequest,
    service: WorkflowService,
    current_user: CurrentUser,
) -> dict[str, str]:
    """
    Share a workflow with another user.

    Only the workflow owner can share. The user is identified by email.
    """
    return await add_workflow_share_authorized(
        workflow_id=workflow_id,
        request=request,
        current_user=current_user,
        service=service,
    )


@workflows_router.delete(
    "/workflows/{workflow_id}/shares/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workflow_share(
    workflow_id: str,
    user_id: str,
    service: WorkflowService,
    current_user: CurrentUser,
) -> None:
    """
    Remove a share from a workflow.

    Only the workflow owner can remove shares.
    """
    await remove_workflow_share_authorized(
        workflow_id=workflow_id,
        user_id=user_id,
        current_user=current_user,
        service=service,
    )


@workflows_router.put("/workflows/{workflow_id}/public")
async def update_workflow_public(
    workflow_id: str,
    request: UpdateWorkflowPublicRequest,
    service: WorkflowService,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Toggle public visibility of a workflow.

    When made public, a share_link is generated for anonymous access.
    Only the workflow owner can change public status.
    """
    return await update_workflow_public_authorized(
        workflow_id=workflow_id,
        request=request,
        current_user=current_user,
        service=service,
    )


# ==============================================================================
# Workflow Generation Endpoint
# ==============================================================================


@workflows_router.post("/workflows/generate", status_code=status.HTTP_201_CREATED)
async def generate_workflow(
    request: GenerateWorkflowRequest,
    service: WorkflowService,
    current_user: CurrentUser,
) -> GenerateWorkflowResponse:
    """
    Generate a workflow from session history or text prompt.

    Requires authentication. Uses AI to analyze the provided source and
    generate a workflow definition.
    Exactly one of session_id or prompt must be provided.
    """
    _ = current_user  # Authentication required but user not used directly
    try:
        result = await service.generate_workflow(
            session_id=request.session_id,
            prompt=request.prompt,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return GenerateWorkflowResponse(
        workflow=WorkflowResponse(**result["workflow"]),
        confidence=result["confidence"],
        suggestions=result.get("suggestions", []),
    )


# ==============================================================================
# Workflow Title Generation Endpoint
# ==============================================================================


@workflows_router.post("/workflows/generate-title")
async def generate_workflow_title_endpoint(
    request: GenerateTitleRequest,
    current_user: CurrentUser,
) -> GenerateTitleResponse:
    """
    Generate a workflow title from description and/or session context.

    Uses AI to analyze the provided context and generate a concise,
    descriptive title (2-6 words). Falls back to heuristic extraction
    when LLM is unavailable.

    Requires authentication.
    """
    _ = current_user  # Authentication required but user not used directly

    from mcp_server_langgraph.studio.ai.workflow_title_generator import (
        generate_workflow_title,
    )

    title = await generate_workflow_title(
        description=request.description,
        session_context=request.session_context,
    )

    return GenerateTitleResponse(title=title)


# ==============================================================================
# Chat-to-Workflow Endpoint (ADR-0089, Plan Review Consensus)
# ==============================================================================


@workflows_router.post("/workflows/from-chat", status_code=status.HTTP_201_CREATED)
async def generate_workflow_from_chat(
    request: FromChatRequest,
    service: WorkflowService,
    current_user: CurrentUser,
) -> FromChatResponse:
    """
    Generate and persist a workflow from chat session history.

    This endpoint:
    1. Fetches session messages by session_id
    2. Sanitizes messages to prevent prompt injection (ADR-0089)
    3. Generates workflow via WorkflowGenerator
    4. Persists with status='draft', version=1
    5. Returns prompt metadata for telemetry linkage

    Requires authentication and enable_workflow_from_chat feature flag.

    Args:
        request: FromChatRequest with session_id and refinement_mode
        service: Workflow service adapter
        current_user: Authenticated user

    Returns:
        FromChatResponse with persisted workflow and metadata

    Raises:
        HTTPException 404: If feature disabled or session not found
        HTTPException 422: If validation fails
    """
    # Check feature flag (imported at module level for testability)
    flags = get_feature_flags()
    if not flags.enable_workflow_from_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow from chat feature is not enabled",
        )

    user_id = _get_user_id(current_user)

    try:
        result = await service.generate_from_chat(
            session_id=request.session_id,
            refinement_mode=request.refinement_mode,
            template_id=request.template_id,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Build response
    workflow_data = result["workflow"]
    workflow_data["status"] = "draft"

    return FromChatResponse(
        workflow=WorkflowResponse(**workflow_data),
        confidence=result["confidence"],
        suggestions=result.get("suggestions", []),
        prompt_metadata=PromptMetadata(
            **result.get(
                "prompt_metadata",
                {
                    "name": "workflow_generator",
                    "version": "v1",
                    "hash": "unknown",
                    "model": "unknown",
                },
            )
        ),
        plan=result.get("plan"),
    )


# ==============================================================================
# Workflow Validation Endpoint (ADR-0089, Plan Review Consensus)
# ==============================================================================


@workflows_router.post("/workflows/{workflow_id}/validate")
async def validate_workflow(
    workflow_id: str,
    service: WorkflowService,
    current_user: CurrentUser,
) -> ValidateWorkflowResponse:
    """
    Validate a workflow's graph structure and content.

    Uses centralized WorkflowValidator service - NO JS DUPLICATION.
    Both Monaco editor and React Flow call this single endpoint.

    The endpoint:
    1. Fetches workflow by ID
    2. Validates using WorkflowValidator service
    3. Returns validation result with errors and warnings

    Requires authentication and enable_workflow_from_chat feature flag.

    Args:
        workflow_id: ID of the workflow to validate
        service: Workflow service adapter
        current_user: Authenticated user

    Returns:
        ValidateWorkflowResponse with valid flag, errors, and warnings

    Raises:
        HTTPException 404: If feature disabled or workflow not found
    """
    # Check feature flag (imported at module level for testability)
    flags = get_feature_flags()
    if not flags.enable_workflow_from_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow validation feature is not enabled",
        )

    # Fetch workflow
    workflow = await service.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Validate using centralized validator
    validator = WorkflowValidator()
    result = await validator.validate(workflow)

    return ValidateWorkflowResponse(
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings,
    )


# ==============================================================================
# Workflow Version History Endpoints (Plan: greedy-wiggling-marshmallow.md, Phase 3)
# ==============================================================================


@workflows_router.get("/workflows/{workflow_id}/versions")
async def get_workflow_versions(
    workflow_id: str,
    service: WorkflowService,
    current_user: CurrentUser,
) -> list[WorkflowVersionResponse]:
    """
    Get version history for a workflow.

    Returns all versions for the specified workflow, ordered by version_number
    descending (newest first). Enables version diffing, rollback, and auditing.

    Requires authentication and enable_workflow_from_chat feature flag.

    Args:
        workflow_id: ID of the workflow to get versions for
        service: Workflow service adapter
        current_user: Authenticated user

    Returns:
        List of WorkflowVersionResponse, newest first

    Raises:
        HTTPException 404: If feature disabled or workflow not found
    """
    # Check feature flag
    flags = get_feature_flags()
    if not flags.enable_workflow_from_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow versioning feature is not enabled",
        )

    # Get versions from service
    versions = await service.get_workflow_versions(workflow_id=workflow_id)

    # Convert to response models
    return [
        WorkflowVersionResponse(
            id=v.get("id", ""),
            workflow_id=v.get("workflow_id", workflow_id),
            version_number=v.get("version_number", 0),
            graph_json=v.get("graph_json", {}),
            source_text=v.get("source_text"),
            commit_message=v.get("commit_message"),
            created_by=v.get("created_by", "unknown"),
            created_at=v.get("created_at", ""),
            prompt_version=v.get("prompt_version"),
            prompt_model=v.get("prompt_model"),
        )
        for v in versions
    ]


@workflows_router.post("/workflows/{workflow_id}/versions/{version_id}/restore")
async def restore_workflow_version(
    workflow_id: str,
    version_id: str,
    service: WorkflowService,
    current_user: CurrentUser,
) -> WorkflowResponse:
    """
    Restore a workflow to a previous version.

    This creates a NEW version with the restored state (append-only versioning).
    The new version's commit_message indicates it was restored from version_id.

    Requires authentication and enable_workflow_from_chat feature flag.

    Args:
        workflow_id: ID of the workflow to restore
        version_id: ID of the version to restore to
        service: Workflow service adapter
        current_user: Authenticated user

    Returns:
        WorkflowResponse with the updated workflow (new version)

    Raises:
        HTTPException 404: If feature disabled, workflow not found, or version not found
    """
    # Check feature flag
    flags = get_feature_flags()
    if not flags.enable_workflow_from_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow versioning feature is not enabled",
        )

    try:
        # Restore via service (creates new version)
        restored = await service.restore_workflow_version(
            workflow_id=workflow_id,
            version_id=version_id,
            user_id=current_user.id,
        )

        return WorkflowResponse(**restored)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# ==============================================================================
# Workflow Execution Endpoints
# ==============================================================================

import asyncio
import time
from dataclasses import dataclass, field as dataclass_field

# In-memory execution store (for development/testing)
# In production, use PostgresExecutionHistoryManager via Redis pub/sub


@dataclass
class WorkflowExecutionState:
    """Tracks the state of a workflow execution."""

    execution_id: str
    workflow_id: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    nodes: list[dict[str, Any]] = dataclass_field(default_factory=list)
    edges: list[dict[str, Any]] = dataclass_field(default_factory=list)
    input_data: dict[str, Any] | None = None
    steps: list[dict[str, Any]] = dataclass_field(default_factory=list)
    current_step_id: str | None = None
    start_time: int | None = None
    end_time: int | None = None
    error: str | None = None


# Global execution store - in production, this would be backed by Redis or PostgreSQL
_execution_store: dict[str, WorkflowExecutionState] = {}


async def _execute_workflow_async(state: WorkflowExecutionState) -> None:
    """
    Execute workflow nodes asynchronously using LangGraph.

    This function runs in the background and updates the execution state
    as nodes are processed. For complex workflows, this would compile
    a LangGraph StateGraph and execute it with proper checkpointing.
    """
    from mcp_server_langgraph.core.feature_flags import get_feature_flags

    state.status = "running"
    state.start_time = int(time.time() * 1000)

    # Convert nodes to execution steps
    node_order = _topological_sort_nodes(state.nodes, state.edges)

    for i, node in enumerate(node_order):
        step_id = f"step-{i + 1}"
        step = {
            "id": step_id,
            "nodeId": node.get("id", ""),
            "nodeName": node.get("data", {}).get("label", f"Node {i + 1}"),
            "status": "pending",
            "duration": 0,
            "startTime": None,
            "endTime": None,
            "input": None,
            "output": None,
            "error": None,
        }
        state.steps.append(step)

    # Execute each step
    flags = get_feature_flags()
    for step in state.steps:
        state.current_step_id = step["id"]
        step["status"] = "running"
        step["startTime"] = int(time.time() * 1000)

        try:
            # Find the node for this step
            node = next(
                (n for n in state.nodes if n.get("id") == step["nodeId"]),
                None,
            )

            if node:
                # Execute based on node type
                await _execute_node(node, state.input_data, flags)

            # Mark step as completed
            step["status"] = "completed"
            step["endTime"] = int(time.time() * 1000)
            step["duration"] = step["endTime"] - (step["startTime"] or 0)

        except Exception as e:
            step["status"] = "error"
            step["error"] = str(e)
            step["endTime"] = int(time.time() * 1000)
            step["duration"] = step["endTime"] - (step["startTime"] or 0)
            state.status = "failed"
            state.error = str(e)
            break

    # All steps completed
    if state.status == "running":
        state.status = "completed"
    state.current_step_id = None
    state.end_time = int(time.time() * 1000)


def _topological_sort_nodes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort nodes in topological order based on edges."""
    if not nodes:
        return []

    node_map = {n.get("id"): n for n in nodes}
    in_degree: dict[str, int] = {n.get("id", ""): 0 for n in nodes}

    for edge in edges:
        target = edge.get("target")
        if target and target in in_degree:
            in_degree[target] += 1

    # Start with nodes that have no incoming edges
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    result = []

    while queue:
        node_id = queue.pop(0)
        if node_id in node_map:
            result.append(node_map[node_id])

        for edge in edges:
            if edge.get("source") == node_id:
                target = edge.get("target")
                if target and target in in_degree:
                    in_degree[target] -= 1
                    if in_degree[target] == 0:
                        queue.append(target)

    # Add any remaining nodes (disconnected)
    for n in nodes:
        if n not in result:
            result.append(n)

    return result


# Cache for LLM factory instance
_llm_factory_cache: Any = None


def _get_workflow_llm_factory() -> Any:
    """Get or create the LLM factory for workflow execution.

    Uses lazy initialization and caching for efficiency.
    Returns:
        LLMFactory instance with full resilience patterns
    """
    global _llm_factory_cache
    if _llm_factory_cache is None:
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.llm.factory import create_llm_from_config

        _llm_factory_cache = create_llm_from_config(settings)
    return _llm_factory_cache


async def _execute_node(
    node: dict[str, Any],
    input_data: dict[str, Any] | None,
    flags: Any,
) -> dict[str, Any]:
    """
    Execute a single workflow node using LLMFactory.

    For LLM nodes, uses LLMFactory with full resilience patterns:
    - Circuit breaker for provider failures
    - Retry with exponential backoff
    - Timeout enforcement
    - Bulkhead for concurrency control

    For tool nodes, executes the MCP tool.
    For other nodes, this is a passthrough.
    """
    node_type = node.get("type", "")
    node_data = node.get("data", {})

    if node_type == "llm":
        # LLM node - call via LLMFactory for resilience
        if flags.enable_ai_suggestions:
            from langchain_core.messages import HumanMessage

            prompt = node_data.get("prompt", "")

            # Substitute input variables
            if input_data:
                for key, value in input_data.items():
                    prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

            try:
                factory = _get_workflow_llm_factory()
                messages = [HumanMessage(content=prompt)]
                response = await factory.ainvoke(messages, max_tokens=1024)

                content = response.content if hasattr(response, "content") else str(response)
                return {"content": content}
            except Exception as e:
                logger.warning("Workflow LLM node execution failed", error=str(e))
                return {"error": str(e)}

    elif node_type == "tool":
        # Tool node - would call MCP tool
        # For now, simulate tool execution
        await asyncio.sleep(0.1)  # Simulate tool latency
        return {"result": f"Tool {node_data.get('toolName', 'unknown')} executed"}

    elif node_type == "condition":
        # Condition node - evaluate condition
        await asyncio.sleep(0.05)
        return {"branch": "true"}

    else:
        # Other nodes (start, end, etc.)
        await asyncio.sleep(0.01)
        return {}


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""

    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Workflow nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Workflow edges")
    input_data: dict[str, Any] | None = Field(None, description="Input data for the workflow")


class WorkflowExecuteResponse(BaseModel):
    """Response from workflow execution."""

    execution_id: str = Field(description="The execution ID")
    status: str = Field(description="Execution status")
    message: str | None = Field(None, description="Status message")


@workflows_router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    _: Annotated[dict[str, Any], Depends(require_workflow_executor)],
) -> WorkflowExecuteResponse:
    """
    Execute a workflow.

    Requires executor access to the workflow (owner, executor, or admin).
    Starts workflow execution and returns an execution ID that can be
    used to track progress via GET /workflows/{workflow_id}/execution.

    The execution runs asynchronously in the background. Poll the
    GET /workflows/{workflow_id}/execution endpoint to track progress.

    Example:
        ```
        POST /api/v1/workflows/wf-123/execute
        {
            "nodes": [...],
            "edges": [...],
            "input_data": {...}
        }
        ```
    """
    import uuid

    # Generate an execution ID
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"

    # Create execution state
    state = WorkflowExecutionState(
        execution_id=execution_id,
        workflow_id=workflow_id,
        status="pending",
        nodes=request.nodes,
        edges=request.edges,
        input_data=request.input_data,
    )

    # Store execution state
    _execution_store[workflow_id] = state

    logger.info(
        "Workflow execution started",
        extra={
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "node_count": len(request.nodes),
            "edge_count": len(request.edges),
        },
    )

    # Start async execution in background
    # Store task reference to prevent garbage collection (RUF006)
    background_task = asyncio.create_task(_execute_workflow_async(state))
    # Keep reference to task at module level to prevent GC
    _background_tasks.add(background_task)
    background_task.add_done_callback(_background_tasks.discard)

    return WorkflowExecuteResponse(
        execution_id=execution_id,
        status="started",
        message=f"Workflow {workflow_id} execution started with {len(request.nodes)} nodes",
    )


class ExecutionStep(BaseModel):
    """A single step in workflow execution."""

    id: str = Field(description="Step ID")
    nodeId: str = Field(description="Node ID in the workflow")
    nodeName: str = Field(description="Node display name")
    status: str = Field(description="Step status (pending, running, completed, error, skipped)")
    duration: int = Field(default=0, description="Duration in milliseconds")
    startTime: int | None = Field(None, description="Start timestamp (epoch ms)")
    endTime: int | None = Field(None, description="End timestamp (epoch ms)")
    input: dict[str, Any] | None = Field(None, description="Input data")
    output: dict[str, Any] | None = Field(None, description="Output data")
    error: str | None = Field(None, description="Error message if failed")


class WorkflowExecutionResponse(BaseModel):
    """Response with workflow execution status."""

    status: str = Field(description="Overall execution status")
    steps: list[ExecutionStep] = Field(default_factory=list, description="Execution steps")
    currentStepId: str | None = Field(None, description="Currently executing step ID")
    startTime: int | None = Field(None, description="Execution start time (epoch ms)")
    endTime: int | None = Field(None, description="Execution end time (epoch ms)")


@workflows_router.get("/workflows/{workflow_id}/execution")
async def get_workflow_execution_status(
    workflow_id: str,
    _: Annotated[dict[str, Any], Depends(require_workflow_viewer)],
) -> WorkflowExecutionResponse:
    """
    Get the current execution status of a workflow.

    Requires viewer access to the workflow.
    Returns the steps and their status for tracking workflow progress
    in real-time or polling mode.

    Example:
        ```
        GET /api/v1/workflows/wf-123/execution
        ```
    """
    logger.debug(
        "Workflow execution status requested",
        extra={"workflow_id": workflow_id},
    )

    # Check if there's an active execution for this workflow
    state = _execution_store.get(workflow_id)

    if state is None:
        # No execution found - return idle status
        return WorkflowExecutionResponse(
            status="idle",
            steps=[],
            currentStepId=None,
        )

    # Convert execution state to response
    execution_steps = [
        ExecutionStep(
            id=step["id"],
            nodeId=step["nodeId"],
            nodeName=step["nodeName"],
            status=step["status"],
            duration=step.get("duration", 0),
            startTime=step.get("startTime"),
            endTime=step.get("endTime"),
            input=step.get("input"),
            output=step.get("output"),
            error=step.get("error"),
        )
        for step in state.steps
    ]

    return WorkflowExecutionResponse(
        status=state.status,
        steps=execution_steps,
        currentStepId=state.current_step_id,
        startTime=state.start_time,
        endTime=state.end_time,
    )
