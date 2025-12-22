"""
Tests for MCP Elicitation with AI Explanation Integration.

Tests the enhanced elicitation schema that maps AI explanations
from HITL approval requests to MCP Elicitation protocol.

TDD: RED phase - Define expected behavior for AI-enhanced elicitations.

References:
- Plan Section 10.3: Tighten Elicitation ↔ HITL Mapping
- SEP-1330: Enhanced enum schemas with enumNames
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_elicitation_explanation")
class TestElicitationWithAIExplanation:
    """Test elicitation generation with AI explanations."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_approval_without_explanation_generates_basic_elicitation(self) -> None:
        """Approval without AI explanation generates basic elicitation message."""
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        approval = ApprovalRequired(
            approval_id="test-approval-001",
            node_name="risky_action",
            action_description="Delete temporary files older than 30 days",
            risk_level="medium",
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Basic elicitation should have standard message
        assert "Delete temporary files" in elicitation.message
        assert elicitation.requestedSchema is not None
        assert "approved" in elicitation.requestedSchema.properties

    def test_approval_with_explanation_includes_why_uncertain(self) -> None:
        """Approval with AI explanation includes why_uncertain in message."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="The term 'temporary files' is ambiguous and could match production data.",
            what_could_go_wrong="May accidentally delete important files if path matching is incorrect.",
        )

        approval = ApprovalRequired(
            approval_id="test-approval-002",
            node_name="risky_action",
            action_description="Delete temporary files older than 30 days",
            risk_level="high",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Message should include the AI explanation
        assert "Why I'm uncertain" in elicitation.message or "uncertain" in elicitation.message.lower()
        assert "ambiguous" in elicitation.message.lower()

    def test_approval_with_explanation_includes_what_could_go_wrong(self) -> None:
        """Approval with AI explanation includes what_could_go_wrong in message."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="The target database is not clearly specified.",
            what_could_go_wrong="Could execute migration on production instead of staging.",
        )

        approval = ApprovalRequired(
            approval_id="test-approval-003",
            node_name="migration_action",
            action_description="Run database migration",
            risk_level="critical",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Message should include risk analysis
        assert "could" in elicitation.message.lower() or "risk" in elicitation.message.lower()
        assert "migration" in elicitation.message.lower() or "production" in elicitation.message.lower()

    def test_high_risk_approval_with_explanation_formatted_prominently(self) -> None:
        """High-risk approvals with AI explanation have prominent formatting."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="Multiple valid interpretations of the command.",
            what_could_go_wrong="Irreversible data deletion if target is wrong.",
        )

        approval = ApprovalRequired(
            approval_id="test-approval-004",
            node_name="delete_action",
            action_description="Delete user data",
            risk_level="critical",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Critical risk should be prominently displayed
        assert "CRITICAL" in elicitation.message.upper() or "[critical]" in elicitation.message.lower()


@pytest.mark.xdist_group(name="mcp_elicitation_explanation")
class TestElicitationAlternativesAsEnum:
    """Test safer alternatives mapped to enum options (SEP-1330)."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_alternatives_added_as_enum_options(self) -> None:
        """Safer alternatives should be converted to enum options."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="Target path is ambiguous.",
            what_could_go_wrong="Wrong files may be affected.",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Preview files before deletion",
                    confidence=0.95,
                    trade_off="Adds confirmation step",
                ),
                AlternativeSuggestion(
                    action="Delete only from staging environment",
                    confidence=0.90,
                    trade_off="Production files remain",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-approval-005",
            node_name="file_delete",
            action_description="Delete matching files",
            risk_level="high",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Check schema has selected_action with alternatives
        properties = elicitation.requestedSchema.properties
        assert "selected_action" in properties, "Should have selected_action property for alternatives"

        selected_action = properties["selected_action"]
        assert "enum" in selected_action, "selected_action should be an enum"
        assert "enumNames" in selected_action, "selected_action should have enumNames (SEP-1330)"

        # Should have original + alternatives
        enum_values = selected_action["enum"]
        assert len(enum_values) == 3, "Should have original + 2 alternatives"
        assert "original" in enum_values, "Should include original action option"

    def test_enum_names_include_confidence_percentages(self) -> None:
        """Enum names should include confidence percentages for alternatives."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="Uncertainty reason",
            what_could_go_wrong="Risk description",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Use read-only mode",
                    confidence=0.92,
                    trade_off="Cannot make changes",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-approval-006",
            node_name="data_access",
            action_description="Access production data",
            risk_level="medium",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        properties = elicitation.requestedSchema.properties
        assert "selected_action" in properties

        enum_names = properties["selected_action"]["enumNames"]
        # Check confidence percentage appears in enum names
        alternative_name = enum_names[1]  # First alternative after original
        assert "92%" in alternative_name or "0.92" in alternative_name

    def test_original_action_is_first_enum_option(self) -> None:
        """Original action should be the first (default) enum option."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="Reason",
            what_could_go_wrong="Risk",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Alternative action",
                    confidence=0.88,
                    trade_off="Trade-off",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-approval-007",
            node_name="action_node",
            action_description="Original action description",
            risk_level="low",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        properties = elicitation.requestedSchema.properties
        assert "selected_action" in properties

        enum_values = properties["selected_action"]["enum"]
        enum_names = properties["selected_action"]["enumNames"]

        # Original should be first
        assert enum_values[0] == "original"
        assert "Original action description" in enum_names[0]

        # Should have default set to original
        assert properties["selected_action"].get("default") == "original"

    def test_no_alternatives_skips_selected_action(self) -> None:
        """Without alternatives, selected_action should not be added."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge

        explanation = AIExplanation(
            why_uncertain="Some uncertainty",
            what_could_go_wrong="Some risk",
            safer_alternatives=[],  # Empty alternatives
        )

        approval = ApprovalRequired(
            approval_id="test-approval-008",
            node_name="action_node",
            action_description="Some action",
            risk_level="medium",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        properties = elicitation.requestedSchema.properties
        # Should NOT have selected_action when no alternatives
        assert "selected_action" not in properties


@pytest.mark.xdist_group(name="mcp_elicitation_explanation")
class TestElicitationResponseWithAlternatives:
    """Test handling responses when alternatives are selected."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_response_with_original_action_approved(self) -> None:
        """Response selecting original action is approved normally."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import (
            ApprovalRequired,
            ApprovalStatus,
        )
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge
        from mcp_server_langgraph.mcp.elicitation import ElicitationAction

        explanation = AIExplanation(
            why_uncertain="Reason",
            what_could_go_wrong="Risk",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Alternative",
                    confidence=0.9,
                    trade_off="Trade-off",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-approval-009",
            node_name="action_node",
            action_description="Original action",
            risk_level="medium",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Respond with original action selected and approved
        response = bridge.handle_response(
            elicitation_id=elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={
                "approved": True,
                "selected_action": "original",
                "reason": "Proceeding with original action",
            },
        )

        assert response.status == ApprovalStatus.APPROVED
        assert response.approval_id == approval.approval_id

    def test_response_with_alternative_action_records_modification(self) -> None:
        """Response selecting alternative records modification in approval."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import (
            ApprovalRequired,
            ApprovalStatus,
        )
        from mcp_server_langgraph.core.interrupts.mcp_bridge import MCPApprovalBridge
        from mcp_server_langgraph.mcp.elicitation import ElicitationAction

        explanation = AIExplanation(
            why_uncertain="Reason",
            what_could_go_wrong="Risk",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Preview files first",
                    confidence=0.95,
                    trade_off="Extra step",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-approval-010",
            node_name="action_node",
            action_description="Delete files",
            risk_level="high",
            ai_explanation=explanation,
        )

        bridge = MCPApprovalBridge()
        elicitation = bridge.approval_to_elicitation(approval)

        # Respond with alternative selected
        response = bridge.handle_response(
            elicitation_id=elicitation.id,
            action=ElicitationAction.ACCEPT,
            content={
                "approved": True,
                "selected_action": "alt_0",
                "reason": "Using safer alternative",
            },
        )

        assert response.status == ApprovalStatus.APPROVED
        # Response should include modification info
        assert response.modifications is not None
        assert "selected_alternative" in response.modifications
        assert response.modifications["selected_alternative"] == "alt_0"
