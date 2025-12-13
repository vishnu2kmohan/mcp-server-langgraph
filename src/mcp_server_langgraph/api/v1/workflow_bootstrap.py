"""
Workflow Bootstrap Router

Provides API for bootstrapping workflows from chat session traces.

Analyzes chat session history and creates workflow definitions based on
the conversation steps, enabling users to convert ad-hoc chat interactions
into reusable, automated workflows.

Usage:
    POST /api/v1/sessions/{id}/bootstrap-workflow - Bootstrap workflow from session
"""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.v1.sessions import SessionService, get_session_service


workflow_bootstrap_router = APIRouter(tags=["workflow-bootstrap"])


# Request/Response Models


class BootstrapRequest(BaseModel):
    """Request body for bootstrapping a workflow from a session."""

    name: str = Field(description="Workflow name", min_length=1, max_length=255)
    description: str | None = Field(default=None, description="Workflow description")
    selected_messages: list[int] | None = Field(
        default=None,
        description="Optional list of message indices to use (if not provided, uses all)",
    )


class BootstrapResponse(BaseModel):
    """Response model for bootstrapped workflow."""

    id: str = Field(description="Workflow ID")
    name: str = Field(description="Workflow name")
    description: str | None = Field(default=None, description="Workflow description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Workflow nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="Workflow edges")


# Workflow Bootstrapper Class


class WorkflowBootstrapper:
    """
    Service for bootstrapping workflows from chat session traces.

    Analyzes conversation history to identify action steps and creates
    workflow definitions with nodes and edges.
    """

    def __init__(self) -> None:
        """Initialize the workflow bootstrapper."""
        self.session_service: SessionService | None = None

    async def extract_steps_from_session(
        self, session_id: str, selected_messages: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """
        Extract action steps from a session's chat history.

        Args:
            session_id: The session ID to analyze
            selected_messages: Optional list of message indices to analyze

        Returns:
            List of action steps extracted from the conversation

        Raises:
            ValueError: If session not found or has no messages
        """
        # Get session service
        if self.session_service is None:
            self.session_service = get_session_service()

        # Fetch session
        session = await self.session_service.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Get messages
        messages = session.get("messages", [])
        if not messages:
            raise ValueError("Cannot bootstrap workflow from empty session")

        # Filter messages if selected_messages provided
        if selected_messages is not None:
            messages = [msg for i, msg in enumerate(messages) if i in selected_messages]

        # Extract steps from messages
        # For MVP: Simple heuristic - each assistant message represents a step
        steps = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                # Extract action from message content (simplified)
                content = msg.get("content", "")
                steps.append(
                    {
                        "action": f"step_{i}",
                        "description": content[:100],  # Truncate for description
                        "type": "llm",  # Default type
                    }
                )

        return steps

    def create_workflow_from_steps(
        self, steps: list[dict[str, Any]], name: str, description: str | None = None
    ) -> dict[str, Any]:
        """
        Create a workflow definition from extracted steps.

        Args:
            steps: List of action steps
            name: Workflow name
            description: Workflow description

        Returns:
            Complete workflow definition with nodes and edges
        """
        workflow_id = str(uuid4())

        # Create nodes
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # Start node
        start_node = {
            "id": "node_start",
            "type": "start",
            "position": {"x": 0, "y": 0},
            "data": {},
        }
        nodes.append(start_node)

        # Create nodes for each step
        x_offset = 200
        prev_node_id = "node_start"

        for i, step in enumerate(steps):
            node_id = f"node_{i + 1}"
            node = {
                "id": node_id,
                "type": step.get("type", "llm"),
                "position": {"x": x_offset * (i + 1), "y": 0},
                "data": {"action": step.get("action", ""), "description": step.get("description", "")},
            }
            nodes.append(node)

            # Create edge from previous node
            edge = {
                "source": prev_node_id,
                "target": node_id,
                "label": None,
            }
            edges.append(edge)

            prev_node_id = node_id

        # End node
        end_node = {
            "id": "node_end",
            "type": "end",
            "position": {"x": x_offset * (len(steps) + 1), "y": 0},
            "data": {},
        }
        nodes.append(end_node)

        # Final edge to end node
        final_edge = {
            "source": prev_node_id,
            "target": "node_end",
            "label": None,
        }
        edges.append(final_edge)

        # Build workflow
        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges,
            "created_at": None,  # Would be set by storage layer
            "updated_at": None,  # Would be set by storage layer
        }

        return workflow

    async def bootstrap_workflow(
        self,
        session_id: str,
        name: str,
        description: str | None = None,
        selected_messages: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Bootstrap a complete workflow from a chat session.

        This is the main entry point that orchestrates the entire process:
        1. Extract steps from session
        2. Create workflow from steps
        3. Return complete workflow definition

        Args:
            session_id: The session ID to analyze
            name: Name for the new workflow
            description: Description for the new workflow
            selected_messages: Optional list of message indices to use

        Returns:
            Complete workflow definition

        Raises:
            ValueError: If session not found or has no messages
        """
        # Extract steps from session
        steps = await self.extract_steps_from_session(session_id, selected_messages)

        # Create workflow from steps
        workflow = self.create_workflow_from_steps(steps, name, description)

        return workflow


# Service singleton (will be replaced by dependency injection in Phase 4)
_workflow_bootstrapper: WorkflowBootstrapper | None = None


def get_workflow_bootstrapper() -> WorkflowBootstrapper:
    """Get the workflow bootstrapper instance."""
    global _workflow_bootstrapper
    if _workflow_bootstrapper is None:
        _workflow_bootstrapper = WorkflowBootstrapper()
    return _workflow_bootstrapper


def set_workflow_bootstrapper(bootstrapper: WorkflowBootstrapper) -> None:
    """Set the workflow bootstrapper instance (for testing/DI)."""
    global _workflow_bootstrapper
    _workflow_bootstrapper = bootstrapper


# Endpoints


@workflow_bootstrap_router.post("/sessions/{session_id}/bootstrap-workflow")
async def bootstrap_workflow(session_id: str, request: BootstrapRequest) -> BootstrapResponse:
    """
    Bootstrap a workflow from a chat session's conversation trace.

    Analyzes the chat history to identify action steps and creates a
    workflow definition that can be saved and executed.

    Args:
        session_id: The session ID to analyze
        request: Bootstrap request with workflow name and description

    Returns:
        Complete workflow definition with nodes and edges

    Raises:
        HTTPException: 404 if session not found, 400 if session has no messages
    """
    bootstrapper = get_workflow_bootstrapper()

    try:
        workflow = await bootstrapper.bootstrap_workflow(
            session_id=session_id,
            name=request.name,
            description=request.description,
            selected_messages=request.selected_messages,
        )

        return BootstrapResponse(**workflow)

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
