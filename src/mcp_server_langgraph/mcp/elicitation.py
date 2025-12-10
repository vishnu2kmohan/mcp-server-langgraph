"""
MCP Elicitation Protocol Handler (2025-11-25 Spec).

Implements elicitation/create for servers to request user input
via JSON schema forms. Clients respond with accept/decline/cancel.

New in 2025-11-25:
- SEP-1330: Enhanced enum schemas with enumNames, default values
- SEP-1036: URL mode for secure OAuth credential collection

Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# SEP-1330: Enhanced Enum Schema (New in 2025-11-25)
# =============================================================================


class EnumSchema(BaseModel):
    """Enhanced enum schema with enumNames and defaults (SEP-1330).

    MCP 2025-11-25 adds enumNames for human-readable labels and
    default values for enum fields in elicitation schemas.

    Attributes:
        type: JSON schema type (default: "string")
        enum: List of allowed values
        enumNames: Human-readable labels for enum values (same order as enum)
        default: Default value (must be in enum list)
        title: Display title
        description: Description text
    """

    type: str = "string"
    enum: list[str]
    enumNames: list[str] | None = None
    default: str | None = None
    title: str | None = None
    description: str | None = None


class ElicitationAction(str, Enum):
    """Possible actions for elicitation response."""

    ACCEPT = "accept"
    DECLINE = "decline"
    CANCEL = "cancel"


class ElicitationSchema(BaseModel):
    """JSON Schema for elicitation form.

    Per MCP spec, schemas are restricted to flat objects with primitive properties.
    """

    type: str = "object"
    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ElicitationRequest(BaseModel):
    """Request sent to client for elicitation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: int = Field(default=0)
    message: str
    requestedSchema: ElicitationSchema


class ElicitationResponse(BaseModel):
    """Response from client for elicitation."""

    action: ElicitationAction
    content: dict[str, Any] | None = None

    def to_jsonrpc(self, request_id: int) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 response format."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "action": self.action.value,
                "content": self.content,
            },
        }


class Elicitation(BaseModel):
    """Full elicitation state including request and status."""

    id: str
    request_id: int
    message: str
    requestedSchema: ElicitationSchema
    status: str = "pending"
    response: ElicitationResponse | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_jsonrpc(self) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 request format."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "elicitation/create",
            "params": {
                "message": self.message,
                "requestedSchema": self.requestedSchema.model_dump(),
            },
        }


class ElicitationHandler:
    """Handler for managing elicitation requests and responses."""

    def __init__(self) -> None:
        """Initialize the elicitation handler."""
        self._pending: dict[str, Elicitation] = {}
        self._completed: dict[str, Elicitation] = {}
        self._next_request_id: int = 1

    def create_elicitation(
        self,
        message: str,
        schema: ElicitationSchema,
    ) -> Elicitation:
        """Create a new elicitation request.

        Args:
            message: Human-readable message explaining what's needed
            schema: JSON schema describing expected input structure

        Returns:
            Elicitation object with pending status
        """
        elicitation = Elicitation(
            id=str(uuid.uuid4()),
            request_id=self._next_request_id,
            message=message,
            requestedSchema=schema,
        )
        self._next_request_id += 1
        self._pending[elicitation.id] = elicitation
        return elicitation

    def get_pending_elicitation(self, elicitation_id: str) -> Elicitation | None:
        """Get a pending elicitation by ID.

        Args:
            elicitation_id: Unique elicitation identifier

        Returns:
            Elicitation if found and pending, None otherwise
        """
        return self._pending.get(elicitation_id)

    def respond(
        self,
        elicitation_id: str,
        action: ElicitationAction,
        content: dict[str, Any] | None = None,
    ) -> ElicitationResponse:
        """Respond to an elicitation request.

        Args:
            elicitation_id: ID of the elicitation to respond to
            action: Accept, decline, or cancel
            content: Response content (required for accept, optional otherwise)

        Returns:
            ElicitationResponse object

        Raises:
            ValueError: If elicitation not found
        """
        elicitation = self._pending.get(elicitation_id)
        if not elicitation:
            raise ValueError(f"Elicitation {elicitation_id} not found")

        response = ElicitationResponse(action=action, content=content)
        elicitation.response = response
        elicitation.status = action.value

        # Move from pending to completed
        del self._pending[elicitation_id]
        self._completed[elicitation_id] = elicitation

        return response

    def list_pending(self) -> list[Elicitation]:
        """List all pending elicitations.

        Returns:
            List of pending elicitation objects
        """
        return list(self._pending.values())

    def get_completed(self, elicitation_id: str) -> Elicitation | None:
        """Get a completed elicitation by ID.

        Args:
            elicitation_id: Unique elicitation identifier

        Returns:
            Elicitation if found and completed, None otherwise
        """
        return self._completed.get(elicitation_id)


# =============================================================================
# ApprovalNode Integration
# =============================================================================


def approval_node_to_elicitation(approval_node: Any) -> Elicitation:
    """Convert an ApprovalNode interrupt to an elicitation request.

    Args:
        approval_node: ApprovalNode or ApprovalRequired object

    Returns:
        Elicitation configured for approval workflow
    """
    # Build schema for approval
    schema = ElicitationSchema(
        type="object",
        properties={
            "approved": {
                "type": "boolean",
                "description": "Approve this action?",
            },
            "reason": {
                "type": "string",
                "description": "Optional reason for your decision",
            },
        },
        required=["approved"],
    )

    # Get risk level styling
    risk_level = getattr(approval_node, "risk_level", "medium")
    action_description = getattr(approval_node, "action_description", "Perform action")

    message = f"Approve: {action_description}"
    if risk_level in ("high", "critical"):
        message = f"[{risk_level.upper()}] {message}"

    return Elicitation(
        id=getattr(approval_node, "approval_id", str(uuid.uuid4())),
        request_id=0,  # Will be set by handler
        message=message,
        requestedSchema=schema,
    )


def elicitation_response_to_approval(
    response: ElicitationResponse,
    approval_id: str,
) -> Any:
    """Convert elicitation response to ApprovalResponse.

    Args:
        response: Elicitation response from client
        approval_id: ID of the original approval request

    Returns:
        ApprovalResponse object
    """
    from mcp_server_langgraph.core.interrupts.approval import (
        ApprovalResponse,
        ApprovalStatus,
    )

    if response.action == ElicitationAction.ACCEPT:
        content = response.content or {}
        approved = content.get("approved", False)
        reason = content.get("reason", "")

        if approved:
            return ApprovalResponse(
                approval_id=approval_id,
                status=ApprovalStatus.APPROVED,
                approved_by="mcp_client",
                reason=reason,
            )
        else:
            return ApprovalResponse(
                approval_id=approval_id,
                status=ApprovalStatus.REJECTED,
                approved_by="mcp_client",
                reason=reason or "User rejected",
            )

    elif response.action == ElicitationAction.DECLINE:
        return ApprovalResponse(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            approved_by="mcp_client",
            reason="User declined to respond",
        )

    else:  # CANCEL
        return ApprovalResponse(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            approved_by="mcp_client",
            reason="User cancelled the request",
        )
