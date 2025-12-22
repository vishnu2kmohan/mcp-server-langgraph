"""
Tests for Elicitation ↔ HITL Mapping with AI Explanations.

Tests for enhanced elicitation schemas that include AI explanations
and alternatives from the ExplanationOrchestrator.

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
    pytest.mark.hitl,
    pytest.mark.ai_explanations,
]


@pytest.mark.xdist_group(name="elicitation_ai_explanation")
class TestApprovalWithExplanationToElicitation:
    """Tests for converting ApprovalRequired with AI explanation to Elicitation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_with_explanation_to_elicitation_exists(self) -> None:
        """
        GIVEN the elicitation module
        WHEN importing approval_with_explanation_to_elicitation
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        assert approval_with_explanation_to_elicitation is not None

    def test_converts_approval_with_explanation_to_elicitation(self) -> None:
        """
        GIVEN an ApprovalRequired with AI explanation
        WHEN converted to elicitation
        THEN should include explanation in message.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        explanation = AIExplanation(
            why_uncertain="The file pattern matches multiple directories.",
            what_could_go_wrong="Important files could be deleted.",
        )

        approval = ApprovalRequired(
            approval_id="approval-test-001",
            task_id="task-001",
            session_id="session-001",
            agent_name="FileAgent",
            node_name="delete_node",
            action_description="Delete files matching *.tmp",
            confidence=0.62,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        elicitation = approval_with_explanation_to_elicitation(approval)

        # Verify explanation is included in message
        assert "Why I'm uncertain" in elicitation.message
        assert "file pattern matches multiple directories" in elicitation.message

    def test_includes_risk_analysis_in_message(self) -> None:
        """
        GIVEN an ApprovalRequired with AI explanation containing risks
        WHEN converted to elicitation
        THEN should include risk analysis in message.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        explanation = AIExplanation(
            why_uncertain="Input is ambiguous",
            what_could_go_wrong="Wrong files could be deleted permanently.",
        )

        approval = ApprovalRequired(
            approval_id="approval-test-002",
            task_id="task-002",
            session_id="session-002",
            agent_name="FileAgent",
            node_name="delete_node",
            action_description="Delete files",
            confidence=0.55,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        elicitation = approval_with_explanation_to_elicitation(approval)

        # Verify risk is included
        assert "Risk" in elicitation.message
        assert "Wrong files could be deleted" in elicitation.message

    def test_includes_alternatives_as_enum_schema(self) -> None:
        """
        GIVEN an ApprovalRequired with AI explanation containing alternatives
        WHEN converted to elicitation
        THEN should include alternatives as enum options (SEP-1330).
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        alternatives = [
            AlternativeSuggestion(
                action="Delete only files older than 30 days",
                confidence=0.85,
                trade_off="Some recent temp files will remain",
            ),
            AlternativeSuggestion(
                action="Move files to trash instead of deleting",
                confidence=0.92,
                trade_off="Files can be recovered but take up space",
            ),
        ]

        explanation = AIExplanation(
            why_uncertain="Input is ambiguous",
            what_could_go_wrong="Wrong files deleted",
            safer_alternatives=alternatives,
        )

        approval = ApprovalRequired(
            approval_id="approval-test-003",
            task_id="task-003",
            session_id="session-003",
            agent_name="FileAgent",
            node_name="delete_node",
            action_description="Delete files matching *.tmp",
            confidence=0.60,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        elicitation = approval_with_explanation_to_elicitation(approval)

        # Verify schema has selected_action enum
        schema_props = elicitation.requestedSchema.properties
        assert "selected_action" in schema_props

        action_schema = schema_props["selected_action"]
        assert action_schema.get("type") == "string"
        assert "enum" in action_schema
        assert len(action_schema["enum"]) == 3  # original + 2 alternatives

        # Verify enumNames are present (SEP-1330)
        assert "enumNames" in action_schema
        assert len(action_schema["enumNames"]) == 3

    def test_fallback_without_explanation(self) -> None:
        """
        GIVEN an ApprovalRequired WITHOUT AI explanation
        WHEN converted to elicitation
        THEN should use basic message format.
        """
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        approval = ApprovalRequired(
            approval_id="approval-test-004",
            task_id="task-004",
            session_id="session-004",
            agent_name="FileAgent",
            node_name="delete_node",
            action_description="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
            # No ai_explanation
        )

        elicitation = approval_with_explanation_to_elicitation(approval)

        # Should still create valid elicitation
        assert elicitation is not None
        assert "Delete files" in elicitation.message

        # Should NOT have selected_action enum (no alternatives)
        schema_props = elicitation.requestedSchema.properties
        assert "selected_action" not in schema_props


@pytest.mark.xdist_group(name="elicitation_ai_explanation")
class TestElicitationSchemaWithAlternatives:
    """Tests for elicitation schema with alternatives as enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enum_schema_has_default_value(self) -> None:
        """
        GIVEN alternatives in elicitation schema
        WHEN schema is created
        THEN should have default value set to 'original'.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Alternative 1",
                    confidence=0.9,
                    trade_off="Trade-off 1",
                ),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-001",
            task_id="task-001",
            session_id="session-001",
            agent_name="TestAgent",
            node_name="test_node",
            action_description="Test action",
            confidence=0.6,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        elicitation = approval_with_explanation_to_elicitation(approval)
        action_schema = elicitation.requestedSchema.properties.get("selected_action", {})

        assert action_schema.get("default") == "original"

    def test_enum_values_include_original_and_alternatives(self) -> None:
        """
        GIVEN 2 alternatives
        WHEN schema is created
        THEN enum should have 3 values: original + 2 alternatives.
        """
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.mcp.elicitation import (
            approval_with_explanation_to_elicitation,
        )

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
            safer_alternatives=[
                AlternativeSuggestion(action="Alt 1", confidence=0.8, trade_off="T1"),
                AlternativeSuggestion(action="Alt 2", confidence=0.9, trade_off="T2"),
            ],
        )

        approval = ApprovalRequired(
            approval_id="test-002",
            task_id="task-002",
            session_id="session-002",
            agent_name="TestAgent",
            node_name="test_node",
            action_description="Original action",
            confidence=0.6,
            threshold=0.7,
            trigger_reason="low_confidence",
            ai_explanation=explanation,
        )

        elicitation = approval_with_explanation_to_elicitation(approval)
        action_schema = elicitation.requestedSchema.properties.get("selected_action", {})

        enum_values = action_schema.get("enum", [])
        assert enum_values == ["original", "alt_0", "alt_1"]

        enum_names = action_schema.get("enumNames", [])
        assert len(enum_names) == 3
        assert "Original action" in enum_names[0]
        assert "Alt 1" in enum_names[1]
        assert "Alt 2" in enum_names[2]
