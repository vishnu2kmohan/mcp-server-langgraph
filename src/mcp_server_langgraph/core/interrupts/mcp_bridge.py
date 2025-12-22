"""
MCP Bridge for Approval System.

Bridges LangGraph ApprovalNode interrupts to MCP Elicitation protocol,
enabling human-in-the-loop workflows via MCP clients.

Architecture:
    LangGraph Interrupt → MCP Bridge → Elicitation Request → Client UI
    Client Response → MCP Bridge → ApprovalResponse → Resume Graph

Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation
"""

from typing import Any

from mcp_server_langgraph.core.interrupts.ai_explanation import (
    AlternativeSuggestion,
)
from mcp_server_langgraph.core.interrupts.approval import (
    ApprovalRequired,
    ApprovalResponse,
    ApprovalStatus,
)
from mcp_server_langgraph.mcp.elicitation import (
    Elicitation,
    ElicitationAction,
    ElicitationHandler,
    ElicitationResponse,
    ElicitationSchema,
)


class MCPApprovalBridge:
    """Bridge between LangGraph ApprovalNode and MCP Elicitation.

    This bridge translates between LangGraph's interrupt-based approval
    system and MCP's elicitation protocol, enabling MCP clients to
    handle approval workflows.
    """

    def __init__(self, elicitation_handler: ElicitationHandler | None = None) -> None:
        """Initialize the bridge.

        Args:
            elicitation_handler: Optional handler for managing elicitations.
                                If None, creates a new handler.
        """
        self._handler = elicitation_handler or ElicitationHandler()
        self._pending_approvals: dict[str, ApprovalRequired] = {}
        self._elicitation_to_approval: dict[str, str] = {}  # Maps elicitation ID to approval ID

    @property
    def elicitation_handler(self) -> ElicitationHandler:
        """Get the underlying elicitation handler."""
        return self._handler

    def approval_to_elicitation(
        self,
        approval: ApprovalRequired,
    ) -> Elicitation:
        """Convert an ApprovalRequired to an MCP Elicitation.

        Args:
            approval: ApprovalRequired from LangGraph interrupt

        Returns:
            Elicitation configured for approval workflow

        AI-Native Enhancement (Phase 1):
            When approval includes ai_explanation, the elicitation message
            includes the uncertainty reason and risk analysis. Safer
            alternatives are mapped to enum options using SEP-1330 EnumSchema.
        """
        # Store the pending approval
        self._pending_approvals[approval.approval_id] = approval

        # Build base properties for approval form
        properties: dict[str, Any] = {
            "approved": {
                "type": "boolean",
                "description": "Approve this action?",
            },
            "reason": {
                "type": "string",
                "description": "Optional reason for your decision",
            },
        }

        # Add alternatives as enum options if available (SEP-1330)
        explanation = approval.ai_explanation
        if explanation and explanation.safer_alternatives:
            properties["selected_action"] = self._build_alternatives_enum(
                approval.action_description,
                explanation.safer_alternatives,
            )

        # Build JSON schema for approval form
        schema = ElicitationSchema(
            type="object",
            properties=properties,
            required=["approved"],
        )

        # Format message with AI explanation if available
        message = self._build_elicitation_message(approval)

        # Create elicitation via handler
        elicitation = self._handler.create_elicitation(
            message=message,
            schema=schema,
        )

        # Track the mapping
        self._elicitation_to_approval[elicitation.id] = approval.approval_id

        return elicitation

    def _build_elicitation_message(self, approval: ApprovalRequired) -> str:
        """Build elicitation message with optional AI explanation.

        Args:
            approval: ApprovalRequired with optional ai_explanation

        Returns:
            Formatted message string
        """
        risk_level = approval.risk_level
        message = f"Approve: {approval.action_description}"

        # Add risk level prefix for high/critical
        if risk_level in ("high", "critical"):
            message = f"[{risk_level.upper()}] {message}"

        # Add AI explanation if available
        explanation = approval.ai_explanation
        if explanation:
            message += f"\n\n**Why I'm uncertain:** {explanation.why_uncertain}"
            message += f"\n\n**What could go wrong:** {explanation.what_could_go_wrong}"

        return message

    def _build_alternatives_enum(
        self,
        original_action: str,
        alternatives: list[AlternativeSuggestion],
    ) -> dict[str, Any]:
        """Build enum schema for action alternatives (SEP-1330).

        Args:
            original_action: Description of the original action
            alternatives: List of safer alternatives

        Returns:
            Dict suitable for ElicitationSchema properties
        """
        # Build enum values: original + alt_0, alt_1, ...
        enum_values = ["original"] + [f"alt_{i}" for i in range(len(alternatives))]

        # Build human-readable names with confidence
        enum_names = [original_action]
        for alt in alternatives:
            confidence_pct = f"{int(alt.confidence * 100)}%"
            enum_names.append(f"{alt.action} ({confidence_pct})")

        return {
            "type": "string",
            "enum": enum_values,
            "enumNames": enum_names,
            "default": "original",
            "title": "Preferred Action",
            "description": "Choose the original action or a safer alternative",
        }

    def elicitation_to_approval(
        self,
        elicitation_id: str,
        response: ElicitationResponse,
    ) -> ApprovalResponse:
        """Convert an ElicitationResponse to an ApprovalResponse.

        Args:
            elicitation_id: ID of the elicitation being responded to
            response: Response from MCP client

        Returns:
            ApprovalResponse for LangGraph

        Raises:
            ValueError: If elicitation ID not found
        """
        # Get the original approval ID
        approval_id = self._elicitation_to_approval.get(elicitation_id)
        if not approval_id:
            raise ValueError(f"No approval found for elicitation {elicitation_id}")

        # Get the original approval request
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found in pending approvals")

        # Convert based on action
        if response.action == ElicitationAction.ACCEPT:
            content = response.content or {}
            approved = content.get("approved", False)
            reason = content.get("reason", "")
            selected_action = content.get("selected_action")

            # Build modifications dict if alternative was selected
            modifications: dict[str, Any] | None = None
            if selected_action and selected_action != "original":
                modifications = {"selected_alternative": selected_action}

            if approved:
                return ApprovalResponse(
                    approval_id=approval_id,
                    status=ApprovalStatus.APPROVED,
                    approved_by="mcp_client",
                    reason=reason or "Approved via MCP",
                    modifications=modifications,
                )
            else:
                return ApprovalResponse(
                    approval_id=approval_id,
                    status=ApprovalStatus.REJECTED,
                    approved_by="mcp_client",
                    reason=reason or "Rejected by user",
                    modifications=modifications,
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

    def handle_response(
        self,
        elicitation_id: str,
        action: ElicitationAction,
        content: dict[str, Any] | None = None,
    ) -> ApprovalResponse:
        """Handle an elicitation response and convert to approval.

        This is a convenience method that combines responding to the
        elicitation and converting to an approval response.

        Args:
            elicitation_id: ID of the elicitation
            action: Accept, decline, or cancel
            content: Response content (required for accept)

        Returns:
            ApprovalResponse for LangGraph

        Raises:
            ValueError: If elicitation not found
        """
        # Respond to the elicitation
        response = self._handler.respond(
            elicitation_id=elicitation_id,
            action=action,
            content=content,
        )

        # Convert to approval response
        return self.elicitation_to_approval(elicitation_id, response)

    def get_pending_approvals(self) -> list[ApprovalRequired]:
        """Get all pending approvals.

        Returns:
            List of pending ApprovalRequired objects
        """
        return list(self._pending_approvals.values())

    def get_pending_elicitations(self) -> list[Elicitation]:
        """Get all pending elicitations.

        Returns:
            List of pending Elicitation objects
        """
        return self._handler.list_pending()

    def cleanup_approval(self, approval_id: str) -> None:
        """Clean up a completed approval.

        Args:
            approval_id: ID of approval to clean up
        """
        if approval_id in self._pending_approvals:
            del self._pending_approvals[approval_id]

        # Clean up the mapping
        elicitation_ids_to_remove = [eid for eid, aid in self._elicitation_to_approval.items() if aid == approval_id]
        for eid in elicitation_ids_to_remove:
            del self._elicitation_to_approval[eid]


# =============================================================================
# Integration Helpers
# =============================================================================


def create_mcp_approval_bridge() -> MCPApprovalBridge:
    """Create a new MCP approval bridge.

    Returns:
        Configured MCPApprovalBridge instance
    """
    return MCPApprovalBridge()


def extract_approval_from_state(state: dict[str, Any]) -> ApprovalRequired | None:
    """Extract the pending approval from LangGraph state.

    Args:
        state: LangGraph agent state

    Returns:
        ApprovalRequired if pending, None otherwise
    """
    if not state.get("pending_approval"):
        return None

    approval_requests = state.get("approval_requests", [])
    if not approval_requests:
        return None

    # Get the most recent pending approval
    for request in reversed(approval_requests):
        approval_id = request.get("approval_id")
        if approval_id and approval_id == state.get("current_approval_id"):
            return ApprovalRequired(**request)

    return None


def apply_approval_to_state(
    state: dict[str, Any],
    response: ApprovalResponse,
) -> dict[str, Any]:
    """Apply an approval response to LangGraph state.

    Args:
        state: Current LangGraph state
        response: ApprovalResponse from the bridge

    Returns:
        Updated state
    """
    if "approval_responses" not in state:
        state["approval_responses"] = {}

    state["approval_responses"][response.approval_id] = response.model_dump()
    state["pending_approval"] = False

    if response.status == ApprovalStatus.REJECTED:
        state["workflow_halted"] = True

    return state
