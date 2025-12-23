"""
Tests for Confidence-Based Interrupt Node.

Phase 1 of the Confidence-Based HITL Implementation Plan.

TDD: Write tests FIRST, then implementation.

Tests:
1. ConfidenceApprovalNode exists and is callable
2. ConfidenceApprovalNode triggers when confidence < threshold
3. ConfidenceApprovalNode passes through when confidence >= threshold
4. check_confidence helper function works correctly
5. Interrupt payload includes confidence and threshold info
"""

from __future__ import annotations

import gc
from typing import Any

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="confidence_interrupt")
class TestConfidenceApprovalNodeImport:
    """Test ConfidenceApprovalNode can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_confidence_approval_node_importable(self) -> None:
        """ConfidenceApprovalNode should be importable."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        assert ConfidenceApprovalNode is not None

    def test_default_confidence_threshold_importable(self) -> None:
        """DEFAULT_CONFIDENCE_THRESHOLD should be importable from confidence module."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            DEFAULT_CONFIDENCE_THRESHOLD,
        )

        assert DEFAULT_CONFIDENCE_THRESHOLD == 0.7

    def test_check_confidence_helper_importable(self) -> None:
        """check_confidence helper should be importable."""
        from mcp_server_langgraph.core.interrupts.confidence import check_confidence

        assert callable(check_confidence)


@pytest.mark.xdist_group(name="confidence_interrupt")
class TestConfidenceApprovalNodeInitialization:
    """Test ConfidenceApprovalNode initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_accepts_threshold_parameter(self) -> None:
        """ConfidenceApprovalNode should accept threshold parameter."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.8)
        assert node.threshold == 0.8

    def test_node_uses_default_threshold_when_not_specified(self) -> None:
        """ConfidenceApprovalNode should use 0.7 default threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode()
        assert node.threshold == 0.7

    def test_node_accepts_name_parameter(self) -> None:
        """ConfidenceApprovalNode should accept name parameter."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(name="critical_action_approval")
        assert node.name == "critical_action_approval"

    def test_node_has_default_name(self) -> None:
        """ConfidenceApprovalNode should have default name."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode()
        assert node.name == "confidence_approval"

    def test_node_is_callable(self) -> None:
        """ConfidenceApprovalNode instance should be callable."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode()
        assert callable(node)


@pytest.mark.xdist_group(name="confidence_interrupt_behavior")
class TestConfidenceApprovalNodeBehavior:
    """Test ConfidenceApprovalNode behavior with different confidence levels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_passes_through_when_confidence_above_threshold(self) -> None:
        """Node should pass through state when confidence >= threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.85,
            "messages": ["hello"],
        }

        result = node(state)

        # Should pass through without marking pending_approval
        assert result.get("pending_approval") is not True

    def test_node_triggers_when_confidence_below_threshold(self) -> None:
        """Node should trigger approval when confidence < threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
            "messages": ["hello"],
        }

        result = node(state)

        # Should mark pending_approval
        assert result.get("pending_approval") is True

    def test_node_triggers_at_exact_threshold(self) -> None:
        """Node should NOT trigger at exactly threshold (>= passes)."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.7,
            "messages": ["hello"],
        }

        result = node(state)

        # Exactly at threshold should pass through
        assert result.get("pending_approval") is not True

    def test_node_uses_verification_score_if_routing_confidence_absent(self) -> None:
        """Node should fallback to verification_score if routing_confidence missing."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "verification_score": 0.55,
            "messages": ["hello"],
        }

        result = node(state)

        # Should trigger based on verification_score
        assert result.get("pending_approval") is True

    def test_node_passes_through_when_no_confidence_in_state(self) -> None:
        """Node should pass through if no confidence field in state."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "messages": ["hello"],
        }

        result = node(state)

        # No confidence = pass through (conservative approach)
        assert result.get("pending_approval") is not True


@pytest.mark.xdist_group(name="confidence_interrupt_payload")
class TestConfidenceApprovalNodePayload:
    """Test ConfidenceApprovalNode creates proper approval request payload."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_adds_approval_request_to_state(self) -> None:
        """Node should add approval_requests list to state when triggered."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
        }

        result = node(state)

        assert "approval_requests" in result
        assert len(result["approval_requests"]) == 1

    def test_approval_request_includes_confidence_info(self) -> None:
        """Approval request should include confidence and threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
        }

        result = node(state)
        request = result["approval_requests"][0]

        assert request["context"]["confidence"] == 0.55
        assert request["context"]["threshold"] == 0.7
        assert "low_confidence" in request["risk_level"] or request["risk_level"] in [
            "low",
            "medium",
            "high",
        ]

    def test_approval_request_has_descriptive_action(self) -> None:
        """Approval request should have descriptive action_description."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7, name="critical_action")
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
        }

        result = node(state)
        request = result["approval_requests"][0]

        assert "confidence" in request["action_description"].lower()
        assert "55%" in request["action_description"] or "0.55" in request["action_description"]

    def test_node_sets_current_approval_id(self) -> None:
        """Node should set current_approval_id in state."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
        }

        result = node(state)

        assert "current_approval_id" in result
        assert result["current_approval_id"] is not None


@pytest.mark.xdist_group(name="confidence_check_helper")
class TestCheckConfidenceHelper:
    """Test check_confidence helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_confidence_returns_true_when_above_threshold(self) -> None:
        """check_confidence should return True when confidence >= threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import check_confidence

        assert check_confidence(0.85, 0.7) is True
        assert check_confidence(0.7, 0.7) is True
        assert check_confidence(1.0, 0.9) is True

    def test_check_confidence_returns_false_when_below_threshold(self) -> None:
        """check_confidence should return False when confidence < threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import check_confidence

        assert check_confidence(0.55, 0.7) is False
        assert check_confidence(0.69, 0.7) is False
        assert check_confidence(0.0, 0.1) is False

    def test_check_confidence_uses_default_threshold(self) -> None:
        """check_confidence should use 0.7 as default threshold."""
        from mcp_server_langgraph.core.interrupts.confidence import check_confidence

        assert check_confidence(0.75) is True  # >= 0.7
        assert check_confidence(0.65) is False  # < 0.7


@pytest.mark.xdist_group(name="confidence_interrupt_integration")
class TestConfidenceApprovalNodeIntegration:
    """Test ConfidenceApprovalNode integration with existing approval system."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_request_follows_approval_required_schema(self) -> None:
        """Approval request should follow ApprovalRequired schema."""
        from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
        }

        result = node(state)
        request_dict = result["approval_requests"][0]

        # Should be valid ApprovalRequired schema
        approval = ApprovalRequired(**request_dict)
        assert approval.approval_id is not None
        assert approval.node_name == "confidence_approval"
        assert "confidence" in approval.context

    def test_node_preserves_existing_state(self) -> None:
        """Node should preserve existing state keys when adding approval."""
        from mcp_server_langgraph.core.interrupts.confidence import (
            ConfidenceApprovalNode,
        )

        node = ConfidenceApprovalNode(threshold=0.7)
        state: dict[str, Any] = {
            "routing_confidence": 0.55,
            "messages": ["hello", "world"],
            "custom_key": {"nested": "value"},
        }

        result = node(state)

        assert result["messages"] == ["hello", "world"]
        assert result["custom_key"] == {"nested": "value"}
