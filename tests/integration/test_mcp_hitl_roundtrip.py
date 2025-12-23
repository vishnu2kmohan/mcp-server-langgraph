"""
Integration tests for MCP HITL (Human-in-the-Loop) Roundtrip.

Tests the complete HITL flow exposed via MCP elicitation:
- ApprovalRequired → Elicitation conversion
- AI Explanation integration
- Elicitation response → ApprovalResponse conversion
- Full approval/rejection lifecycle

TDD: Tests written FIRST.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mcp,
    pytest.mark.hitl,
]


@pytest.fixture
def mock_approval_required():
    """Create a mock ApprovalRequired for testing."""
    from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired

    return ApprovalRequired(
        approval_id="approval-123",
        node_name="risky_action",
        action_description="Delete all user data",
        risk_level="high",
        context={"user_count": 1000},
        requested_by="agent-456",
    )


@pytest.fixture
def mock_ai_explanation():
    """Create a mock AIExplanation for testing."""
    from mcp_server_langgraph.core.interrupts.ai_explanation import (
        AIExplanation,
        AlternativeSuggestion,
        ConfidenceFactor,
    )

    return AIExplanation(
        why_uncertain="The action affects a large number of users (1000) and is irreversible.",
        what_could_go_wrong="Permanent data loss with no recovery option. Potential compliance violations.",
        safer_alternatives=[
            AlternativeSuggestion(
                action="Archive data instead of deleting",
                confidence=0.95,
                trade_off="Requires additional storage space",
            ),
            AlternativeSuggestion(
                action="Delete in batches with confirmation",
                confidence=0.88,
                trade_off="Takes longer but allows rollback",
            ),
        ],
        confidence_factors=[
            ConfidenceFactor(
                factor="large_user_count",
                weight=-0.3,
                evidence="Action affects 1000 users",
            ),
            ConfidenceFactor(
                factor="irreversible_action",
                weight=-0.25,
                evidence="Delete operations cannot be undone",
            ),
        ],
        reasoning_trace=[
            "Identified action as delete operation",
            "Counted affected users: 1000",
            "Assessed reversibility: false",
        ],
    )


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestApprovalToElicitationConversion:
    """Tests for ApprovalRequired → Elicitation conversion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_basic_approval_to_elicitation(self, mock_approval_required) -> None:
        """
        GIVEN an ApprovalRequired without AI explanation
        WHEN converted to elicitation
        THEN should create valid elicitation with approval schema.
        """
        from mcp_server_langgraph.mcp.elicitation import approval_node_to_elicitation

        elicitation = approval_node_to_elicitation(mock_approval_required)

        assert elicitation.id == "approval-123"
        assert "Delete all user data" in elicitation.message
        assert "[HIGH]" in elicitation.message

        # Check schema has required fields
        props = elicitation.requestedSchema.properties
        assert "approved" in props
        assert props["approved"]["type"] == "boolean"
        assert "reason" in props
        assert elicitation.requestedSchema.required == ["approved"]

    def test_approval_with_explanation_to_elicitation(self, mock_approval_required, mock_ai_explanation) -> None:
        """
        GIVEN an ApprovalRequired with AI explanation
        WHEN converted to elicitation
        THEN should include explanation in message and alternatives in schema.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        # Attach AI explanation
        mock_approval_required.ai_explanation = mock_ai_explanation

        elicitation = approval_with_explanation_to_elicitation(mock_approval_required)

        # Check explanation is in message
        assert "Why I'm uncertain" in elicitation.message
        assert "large number of users" in elicitation.message
        assert "Risk:" in elicitation.message
        assert "data loss" in elicitation.message

        # Check alternatives are in schema as enum (SEP-1330)
        props = elicitation.requestedSchema.properties
        assert "selected_action" in props
        assert props["selected_action"]["type"] == "string"
        assert "original" in props["selected_action"]["enum"]
        assert "alt_0" in props["selected_action"]["enum"]
        assert "alt_1" in props["selected_action"]["enum"]
        assert len(props["selected_action"]["enumNames"]) == 3

    def test_low_risk_approval_no_prefix(self) -> None:
        """
        GIVEN a low-risk ApprovalRequired
        WHEN converted to elicitation
        THEN should NOT have risk level prefix in message.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import approval_node_to_elicitation

        approval = ApprovalRequired(
            approval_id="approval-456",
            node_name="simple_action",
            action_description="Update user preferences",
            risk_level="low",
        )

        elicitation = approval_node_to_elicitation(approval)

        assert "[LOW]" not in elicitation.message
        assert "Update user preferences" in elicitation.message


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestElicitationResponseConversion:
    """Tests for ElicitationResponse → ApprovalResponse conversion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_accept_with_approval_true(self) -> None:
        """
        GIVEN an elicitation response with action=accept and approved=true
        WHEN converted to ApprovalResponse
        THEN should return APPROVED status.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationResponse,
            elicitation_response_to_approval,
        )

        response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"approved": True, "reason": "Verified with team lead"},
        )

        approval_response = elicitation_response_to_approval(response, "approval-123")

        assert approval_response.approval_id == "approval-123"
        assert approval_response.status == ApprovalStatus.APPROVED
        assert approval_response.reason == "Verified with team lead"
        assert approval_response.approved_by == "mcp_client"

    def test_accept_with_approval_false(self) -> None:
        """
        GIVEN an elicitation response with action=accept and approved=false
        WHEN converted to ApprovalResponse
        THEN should return REJECTED status.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationResponse,
            elicitation_response_to_approval,
        )

        response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"approved": False, "reason": "Too risky"},
        )

        approval_response = elicitation_response_to_approval(response, "approval-123")

        assert approval_response.status == ApprovalStatus.REJECTED
        assert approval_response.reason == "Too risky"

    def test_decline_action_results_in_rejection(self) -> None:
        """
        GIVEN an elicitation response with action=decline
        WHEN converted to ApprovalResponse
        THEN should return REJECTED status with decline message.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationResponse,
            elicitation_response_to_approval,
        )

        response = ElicitationResponse(action=ElicitationAction.DECLINE)

        approval_response = elicitation_response_to_approval(response, "approval-789")

        assert approval_response.status == ApprovalStatus.REJECTED
        assert "declined" in approval_response.reason.lower()

    def test_cancel_action_results_in_rejection(self) -> None:
        """
        GIVEN an elicitation response with action=cancel
        WHEN converted to ApprovalResponse
        THEN should return REJECTED status with cancel message.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationResponse,
            elicitation_response_to_approval,
        )

        response = ElicitationResponse(action=ElicitationAction.CANCEL)

        approval_response = elicitation_response_to_approval(response, "approval-000")

        assert approval_response.status == ApprovalStatus.REJECTED
        assert "cancelled" in approval_response.reason.lower()


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestElicitationHandler:
    """Tests for ElicitationHandler workflow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_elicitation_generates_id(self) -> None:
        """
        GIVEN an ElicitationHandler
        WHEN creating an elicitation
        THEN should generate unique ID and request_id.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationHandler,
            ElicitationSchema,
        )

        handler = ElicitationHandler()

        schema = ElicitationSchema(
            properties={"approved": {"type": "boolean"}},
            required=["approved"],
        )

        elicitation = handler.create_elicitation(
            message="Approve this action?",
            schema=schema,
        )

        assert elicitation.id is not None
        assert elicitation.request_id == 1
        assert elicitation.status == "pending"
        assert elicitation.message == "Approve this action?"

    def test_list_pending_elicitations(self) -> None:
        """
        GIVEN multiple pending elicitations
        WHEN listing pending
        THEN should return all pending elicitations.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationHandler,
            ElicitationSchema,
        )

        handler = ElicitationHandler()
        schema = ElicitationSchema(
            properties={"approved": {"type": "boolean"}},
            required=["approved"],
        )

        handler.create_elicitation(message="First?", schema=schema)
        handler.create_elicitation(message="Second?", schema=schema)

        pending = handler.list_pending()

        assert len(pending) == 2
        assert pending[0].message == "First?"
        assert pending[1].message == "Second?"

    def test_respond_moves_to_completed(self) -> None:
        """
        GIVEN a pending elicitation
        WHEN responding
        THEN should move to completed and no longer be pending.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationHandler,
            ElicitationSchema,
        )

        handler = ElicitationHandler()
        schema = ElicitationSchema(
            properties={"approved": {"type": "boolean"}},
            required=["approved"],
        )

        elicitation = handler.create_elicitation(message="Approve?", schema=schema)
        elicitation_id = elicitation.id

        # Respond to the elicitation
        handler.respond(
            elicitation_id,
            action=ElicitationAction.ACCEPT,
            content={"approved": True},
        )

        # Should no longer be pending
        assert handler.get_pending_elicitation(elicitation_id) is None
        assert len(handler.list_pending()) == 0

        # Should be in completed
        completed = handler.get_completed(elicitation_id)
        assert completed is not None
        assert completed.status == "accept"

    def test_respond_raises_for_unknown_elicitation(self) -> None:
        """
        GIVEN an ElicitationHandler
        WHEN responding to unknown elicitation
        THEN should raise ValueError.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationHandler,
        )

        handler = ElicitationHandler()

        with pytest.raises(ValueError, match="not found"):
            handler.respond(
                "unknown-id",
                action=ElicitationAction.ACCEPT,
                content={"approved": True},
            )


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestElicitationJSONRPCFormat:
    """Tests for JSON-RPC format conversion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_elicitation_to_jsonrpc_request(self) -> None:
        """
        GIVEN an Elicitation
        WHEN converting to JSON-RPC format
        THEN should produce valid elicitation/create request.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            Elicitation,
            ElicitationSchema,
        )

        schema = ElicitationSchema(
            properties={"approved": {"type": "boolean"}},
            required=["approved"],
        )

        elicitation = Elicitation(
            id="elicit-123",
            request_id=42,
            message="Approve action?",
            requestedSchema=schema,
        )

        jsonrpc = elicitation.to_jsonrpc()

        assert jsonrpc["jsonrpc"] == "2.0"
        assert jsonrpc["id"] == 42
        assert jsonrpc["method"] == "elicitation/create"
        assert jsonrpc["params"]["message"] == "Approve action?"
        assert jsonrpc["params"]["mode"] == "inline"
        assert "url" not in jsonrpc["params"]

    def test_elicitation_url_mode_includes_url(self) -> None:
        """
        GIVEN an Elicitation with mode=url
        WHEN converting to JSON-RPC format
        THEN should include url in params.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            Elicitation,
            ElicitationSchema,
        )

        schema = ElicitationSchema(properties={})

        elicitation = Elicitation(
            id="oauth-123",
            request_id=99,
            message="Complete OAuth",
            requestedSchema=schema,
            mode="url",
            url="https://oauth.example.com/authorize",
        )

        jsonrpc = elicitation.to_jsonrpc()

        assert jsonrpc["params"]["mode"] == "url"
        assert jsonrpc["params"]["url"] == "https://oauth.example.com/authorize"

    def test_response_to_jsonrpc_response(self) -> None:
        """
        GIVEN an ElicitationResponse
        WHEN converting to JSON-RPC format
        THEN should produce valid response format.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationResponse,
        )

        response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"approved": True, "reason": "Looks good"},
        )

        jsonrpc = response.to_jsonrpc(request_id=42)

        assert jsonrpc["jsonrpc"] == "2.0"
        assert jsonrpc["id"] == 42
        assert jsonrpc["result"]["action"] == "accept"
        assert jsonrpc["result"]["content"]["approved"] is True


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestEnhancedEnumSchema:
    """Tests for SEP-1330 Enhanced Enum Schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enum_schema_with_enum_names(self) -> None:
        """
        GIVEN an EnumSchema with enumNames
        WHEN serialized
        THEN should include both enum values and human-readable names.
        """
        from mcp_server_langgraph.mcp.elicitation import EnumSchema

        schema = EnumSchema(
            enum=["low", "medium", "high"],
            enumNames=["Low Priority", "Medium Priority", "High Priority"],
            default="medium",
            title="Priority Level",
        )

        data = schema.model_dump()

        assert data["enum"] == ["low", "medium", "high"]
        assert data["enumNames"] == ["Low Priority", "Medium Priority", "High Priority"]
        assert data["default"] == "medium"
        assert data["title"] == "Priority Level"

    def test_enum_schema_optional_enum_names(self) -> None:
        """
        GIVEN an EnumSchema without enumNames
        WHEN serialized
        THEN enumNames should be None.
        """
        from mcp_server_langgraph.mcp.elicitation import EnumSchema

        schema = EnumSchema(
            enum=["yes", "no"],
        )

        data = schema.model_dump()

        assert data["enum"] == ["yes", "no"]
        assert data["enumNames"] is None


@pytest.mark.xdist_group(name="mcp_hitl_roundtrip")
class TestHITLFullLifecycle:
    """End-to-end tests for full HITL lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_full_approval_lifecycle(self, mock_approval_required) -> None:
        """
        GIVEN an ApprovalRequired
        WHEN going through full elicitation lifecycle
        THEN should complete with correct status.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationHandler,
            approval_node_to_elicitation,
            elicitation_response_to_approval,
        )

        handler = ElicitationHandler()

        # Step 1: Convert approval to elicitation
        elicitation = approval_node_to_elicitation(mock_approval_required)

        # Step 2: Add to handler (simulates sending to client)
        tracked_elicitation = handler.create_elicitation(
            message=elicitation.message,
            schema=elicitation.requestedSchema,
        )

        # Step 3: Simulate client response (approve)
        response = handler.respond(
            tracked_elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={"approved": True, "reason": "Confirmed with manager"},
        )

        # Step 4: Convert response back to ApprovalResponse
        approval_response = elicitation_response_to_approval(
            response,
            mock_approval_required.approval_id,
        )

        # Verify full lifecycle completed
        assert approval_response.status == ApprovalStatus.APPROVED
        assert approval_response.reason == "Confirmed with manager"
        assert handler.get_completed(tracked_elicitation.id) is not None

    def test_full_rejection_lifecycle(self, mock_approval_required) -> None:
        """
        GIVEN an ApprovalRequired
        WHEN user rejects through elicitation
        THEN should complete with REJECTED status.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationHandler,
            approval_node_to_elicitation,
            elicitation_response_to_approval,
        )

        handler = ElicitationHandler()

        elicitation = approval_node_to_elicitation(mock_approval_required)
        tracked_elicitation = handler.create_elicitation(
            message=elicitation.message,
            schema=elicitation.requestedSchema,
        )

        # User rejects
        response = handler.respond(
            tracked_elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={"approved": False, "reason": "Too risky without backup"},
        )

        approval_response = elicitation_response_to_approval(
            response,
            mock_approval_required.approval_id,
        )

        assert approval_response.status == ApprovalStatus.REJECTED
        assert "Too risky" in approval_response.reason

    def test_full_lifecycle_with_ai_explanation(self, mock_approval_required, mock_ai_explanation) -> None:
        """
        GIVEN an ApprovalRequired with AI explanation
        WHEN going through full elicitation lifecycle with alternative selection
        THEN should complete with selected alternative tracked.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationAction,
            ElicitationHandler,
            approval_with_explanation_to_elicitation,
            elicitation_response_to_approval,
        )

        handler = ElicitationHandler()
        mock_approval_required.ai_explanation = mock_ai_explanation

        # Convert with AI explanation
        elicitation = approval_with_explanation_to_elicitation(mock_approval_required)

        tracked_elicitation = handler.create_elicitation(
            message=elicitation.message,
            schema=elicitation.requestedSchema,
        )

        # User approves but selects alternative action
        response = handler.respond(
            tracked_elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={
                "approved": True,
                "selected_action": "alt_0",  # Archive instead of delete
                "reason": "Archive is safer",
            },
        )

        approval_response = elicitation_response_to_approval(
            response,
            mock_approval_required.approval_id,
        )

        assert approval_response.status == ApprovalStatus.APPROVED
        # Note: selected_action would be handled by the agent graph

        # Verify the completed elicitation has the full content
        completed = handler.get_completed(tracked_elicitation.id)
        assert completed.response.content["selected_action"] == "alt_0"
