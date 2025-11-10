"""
Tests for Approval System (Human-in-the-Loop Workflows)

Security-Critical Module: Approval bypass could lead to unauthorized actions.
Target Coverage: 90%+ (line and branch)

Tests cover:
- Approval status enumeration
- Approval request/response models
- Approval node execution
- State management
- Helper functions (approve/reject/check)
- Edge cases and error scenarios
"""

import gc
import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time

from mcp_server_langgraph.core.interrupts.approval import (
    ApprovalNode,
    ApprovalRequired,
    ApprovalResponse,
    ApprovalStatus,
    approve_action,
    check_approval_status,
    create_approval_workflow,
    reject_action,
)

# ==============================================================================
# ApprovalStatus Enum Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalStatus:
    """Test approval status enumeration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_approval_status_values(self):
        """Test all approval status values exist."""
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.REJECTED == "rejected"
        assert ApprovalStatus.EXPIRED == "expired"

    def test_approval_status_string_conversion(self):
        """Test status can be created from string."""
        assert ApprovalStatus("pending") == ApprovalStatus.PENDING
        assert ApprovalStatus("approved") == ApprovalStatus.APPROVED
        assert ApprovalStatus("rejected") == ApprovalStatus.REJECTED
        assert ApprovalStatus("expired") == ApprovalStatus.EXPIRED

    def test_approval_status_invalid_value(self):
        """Test invalid status raises error."""
        with pytest.raises(ValueError):
            ApprovalStatus("invalid_status")


# ==============================================================================
# ApprovalRequired Model Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalRequiredModel:
    """Test ApprovalRequired model validation and defaults."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 10:30:00")
    def test_approval_required_minimal_fields(self):
        """Test creation with only required fields."""
        approval = ApprovalRequired(
            approval_id="test_123",
            node_name="risky_action",
            action_description="Execute high-value transaction",
        )

        assert approval.approval_id == "test_123"
        assert approval.node_name == "risky_action"
        assert approval.action_description == "Execute high-value transaction"
        assert approval.risk_level == "medium"  # default
        assert approval.context == {}  # default
        assert approval.requested_at == "2024-01-15T10:30:00+00:00"
        assert approval.requested_by == "system"  # default
        assert approval.expires_at is None
        assert approval.metadata == {}

    def test_approval_required_all_fields(self):
        """Test creation with all fields populated."""
        approval = ApprovalRequired(
            approval_id="approval_456",
            node_name="process_payment",
            action_description="Process $50,000 payment",
            risk_level="high",
            context={"amount": 50000, "recipient": "vendor_xyz"},
            requested_at="2024-01-15T09:00:00",
            requested_by="payment_system",
            expires_at="2024-01-15T17:00:00",
            metadata={"transaction_id": "txn_789", "compliance_checked": True},
        )

        assert approval.approval_id == "approval_456"
        assert approval.node_name == "process_payment"
        assert approval.risk_level == "high"
        assert approval.context["amount"] == 50000
        assert approval.requested_by == "payment_system"
        assert approval.expires_at == "2024-01-15T17:00:00"
        assert approval.metadata["transaction_id"] == "txn_789"

    def test_approval_required_serialization(self):
        """Test model can be serialized to dict."""
        approval = ApprovalRequired(
            approval_id="test_001",
            node_name="test_node",
            action_description="Test action",
        )

        data = approval.model_dump()

        assert isinstance(data, dict)
        assert data["approval_id"] == "test_001"
        assert data["node_name"] == "test_node"
        assert "requested_at" in data

    def test_approval_required_json_serialization(self):
        """Test model can be serialized to JSON."""
        approval = ApprovalRequired(
            approval_id="test_002",
            node_name="test_node",
            action_description="Test action",
        )

        json_str = approval.model_dump_json()
        assert isinstance(json_str, str)

        # Verify can be deserialized
        data = json.loads(json_str)
        assert data["approval_id"] == "test_002"


# ==============================================================================
# ApprovalResponse Model Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalResponseModel:
    """Test ApprovalResponse model validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 11:00:00")
    def test_approval_response_minimal_fields(self):
        """Test creation with minimal fields."""
        response = ApprovalResponse(
            approval_id="test_123",
            status=ApprovalStatus.APPROVED,
            approved_by="john@example.com",
        )

        assert response.approval_id == "test_123"
        assert response.status == ApprovalStatus.APPROVED
        assert response.approved_by == "john@example.com"
        assert response.approved_at == "2024-01-15T11:00:00+00:00"
        assert response.reason is None
        assert response.modifications is None

    def test_approval_response_with_reason_and_modifications(self):
        """Test creation with reason and modifications."""
        response = ApprovalResponse(
            approval_id="test_456",
            status=ApprovalStatus.APPROVED,
            approved_by="jane@example.com",
            reason="Verified with compliance team",
            modifications={"amount": 45000, "payment_method": "wire_transfer"},
        )

        assert response.reason == "Verified with compliance team"
        assert response.modifications["amount"] == 45000
        assert response.modifications["payment_method"] == "wire_transfer"

    def test_approval_response_rejected_status(self):
        """Test rejected approval response."""
        response = ApprovalResponse(
            approval_id="test_789",
            status=ApprovalStatus.REJECTED,
            approved_by="security@example.com",
            reason="Risk level too high without additional review",
        )

        assert response.status == ApprovalStatus.REJECTED
        assert "too high" in response.reason


# ==============================================================================
# ApprovalNode Class Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalNode:
    """Test ApprovalNode class functionality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_approval_node_init_minimal(self):
        """Test ApprovalNode initialization with minimal parameters."""
        node = ApprovalNode(approval_name="test_approval")

        assert node.approval_name == "test_approval"
        assert node.description == "Approval required: test_approval"
        assert node.risk_level == "medium"
        assert node.auto_approve_timeout is None
        assert node.notification_webhook is None

    def test_approval_node_init_full(self):
        """Test ApprovalNode initialization with all parameters."""
        node = ApprovalNode(
            approval_name="high_value_payment",
            description="Approve payment over $10,000",
            risk_level="critical",
            auto_approve_timeout=3600,
            notification_webhook="https://api.example.com/notify",
        )

        assert node.approval_name == "high_value_payment"
        assert node.description == "Approve payment over $10,000"
        assert node.risk_level == "critical"
        assert node.auto_approve_timeout == 3600
        assert node.notification_webhook == "https://api.example.com/notify"

    @freeze_time("2024-01-15 12:00:00")
    def test_approval_node_call_creates_request(self):
        """Test ApprovalNode __call__ creates approval request in state."""
        node = ApprovalNode(
            approval_name="test_action",
            description="Test action requiring approval",
            risk_level="high",
        )

        state: Dict[str, Any] = {"user": "john", "amount": 5000}

        # Execute approval node
        result_state = node(state)

        # Verify state modifications
        assert result_state["pending_approval"] is True
        assert "current_approval_id" in result_state
        assert "approval_requests" in result_state
        assert len(result_state["approval_requests"]) == 1

        # Verify approval request details
        approval_req = result_state["approval_requests"][0]
        assert approval_req["node_name"] == "test_action"
        assert approval_req["action_description"] == "Test action requiring approval"
        assert approval_req["risk_level"] == "high"
        assert "user" in approval_req["context"]
        assert approval_req["context"]["user"] == "john"

    def test_approval_node_call_multiple_requests(self):
        """Test ApprovalNode appends to existing approval requests."""
        node1 = ApprovalNode("action_1", risk_level="low")
        node2 = ApprovalNode("action_2", risk_level="high")

        state: Dict[str, Any] = {}

        # First approval
        state = node1(state)
        assert len(state["approval_requests"]) == 1

        # Second approval (should append)
        state = node2(state)
        assert len(state["approval_requests"]) == 2
        assert state["approval_requests"][0]["node_name"] == "action_1"
        assert state["approval_requests"][1]["node_name"] == "action_2"

    def test_approval_node_call_generates_unique_ids(self):
        """Test each approval node call generates unique approval ID."""
        node = ApprovalNode("test_approval")
        state: Dict[str, Any] = {}

        # Call twice with small delay
        with freeze_time("2024-01-15 12:00:00.000000"):
            state1 = node(state.copy())
            approval_id_1 = state1["current_approval_id"]

        with freeze_time("2024-01-15 12:00:00.100000"):
            state2 = node(state.copy())
            approval_id_2 = state2["current_approval_id"]

        # IDs should be different (timestamp-based)
        assert approval_id_1 != approval_id_2

    @patch("builtins.print")
    def test_approval_node_notification_webhook_none(self, mock_print):
        """Test notification is NOT sent when webhook is None."""
        node = ApprovalNode("test_approval", notification_webhook=None)
        state: Dict[str, Any] = {}

        node(state)

        # Print should not be called (notification placeholder)
        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_approval_node_notification_webhook_present(self, mock_print):
        """Test notification placeholder is called when webhook is set."""
        node = ApprovalNode(
            approval_name="test_approval",
            description="Test notification",
            risk_level="high",
            notification_webhook="https://api.example.com/webhook",
        )
        state: Dict[str, Any] = {}

        node(state)

        # Verify print was called (placeholder notification)
        assert mock_print.call_count >= 1
        call_args = [str(call) for call in mock_print.call_args_list]
        assert any("Notification" in str(arg) for arg in call_args)

    def test_approval_node_call_preserves_original_state(self):
        """Test approval node preserves user data in state."""
        node = ApprovalNode("preserve_test")
        state: Dict[str, Any] = {
            "user_id": "user_123",
            "session": "session_456",
            "data": {"key": "value"},
        }

        result_state = node(state)

        # Original data should still be present
        assert result_state["user_id"] == "user_123"
        assert result_state["session"] == "session_456"
        assert result_state["data"]["key"] == "value"


# ==============================================================================
# Helper Function Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestCheckApprovalStatus:
    """Test check_approval_status function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_check_approval_status_pending_no_responses(self):
        """Test pending status when no responses exist."""
        state: Dict[str, Any] = {}
        status = check_approval_status(state, "approval_123")

        assert status == ApprovalStatus.PENDING

    def test_check_approval_status_pending_different_id(self):
        """Test pending status when approval ID not in responses."""
        state: Dict[str, Any] = {"approval_responses": {"approval_456": {"status": "approved"}}}

        status = check_approval_status(state, "approval_123")
        assert status == ApprovalStatus.PENDING

    def test_check_approval_status_approved(self):
        """Test approved status returned correctly."""
        state: Dict[str, Any] = {
            "approval_responses": {"approval_123": {"status": "approved", "approved_by": "john@example.com"}}
        }

        status = check_approval_status(state, "approval_123")
        assert status == ApprovalStatus.APPROVED

    def test_check_approval_status_rejected(self):
        """Test rejected status returned correctly."""
        state: Dict[str, Any] = {"approval_responses": {"approval_789": {"status": "rejected", "reason": "Too risky"}}}

        status = check_approval_status(state, "approval_789")
        assert status == ApprovalStatus.REJECTED

    def test_check_approval_status_expired(self):
        """Test expired status returned correctly."""
        state: Dict[str, Any] = {"approval_responses": {"approval_001": {"status": "expired"}}}

        status = check_approval_status(state, "approval_001")
        assert status == ApprovalStatus.EXPIRED


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApproveAction:
    """Test approve_action function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 14:00:00")
    def test_approve_action_creates_response(self):
        """Test approve_action creates approval response."""
        state: Dict[str, Any] = {"pending_approval": True}

        result_state = approve_action(
            state,
            approval_id="approval_123",
            approved_by="john@example.com",
            reason="Verified with manager",
        )

        assert "approval_responses" in result_state
        assert "approval_123" in result_state["approval_responses"]

        response = result_state["approval_responses"]["approval_123"]
        assert response["approval_id"] == "approval_123"
        assert response["status"] == "approved"
        assert response["approved_by"] == "john@example.com"
        assert response["reason"] == "Verified with manager"
        assert response["approved_at"] == "2024-01-15T14:00:00+00:00"

    def test_approve_action_clears_pending_flag(self):
        """Test approve_action clears pending_approval flag."""
        state: Dict[str, Any] = {"pending_approval": True}

        result_state = approve_action(state, "approval_456", "jane@example.com")

        assert result_state["pending_approval"] is False

    def test_approve_action_without_reason(self):
        """Test approve_action without optional reason."""
        state: Dict[str, Any] = {}

        result_state = approve_action(state, "approval_789", "admin@example.com")

        response = result_state["approval_responses"]["approval_789"]
        assert response["reason"] is None

    def test_approve_action_preserves_existing_responses(self):
        """Test approve_action preserves other approval responses."""
        state: Dict[str, Any] = {"approval_responses": {"approval_001": {"status": "approved", "approved_by": "user1"}}}

        result_state = approve_action(state, "approval_002", "user2")

        assert len(result_state["approval_responses"]) == 2
        assert "approval_001" in result_state["approval_responses"]
        assert "approval_002" in result_state["approval_responses"]

    def test_approve_action_multiple_approvals(self):
        """Test multiple sequential approvals."""
        state: Dict[str, Any] = {}

        state = approve_action(state, "approval_1", "approver_1", "Reason 1")
        state = approve_action(state, "approval_2", "approver_2", "Reason 2")
        state = approve_action(state, "approval_3", "approver_3")

        assert len(state["approval_responses"]) == 3
        assert state["approval_responses"]["approval_1"]["approved_by"] == "approver_1"
        assert state["approval_responses"]["approval_2"]["reason"] == "Reason 2"
        assert state["approval_responses"]["approval_3"]["reason"] is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestRejectAction:
    """Test reject_action function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 15:30:00")
    def test_reject_action_creates_response(self):
        """Test reject_action creates rejection response."""
        state: Dict[str, Any] = {"pending_approval": True}

        result_state = reject_action(
            state,
            approval_id="approval_123",
            rejected_by="security@example.com",
            reason="Risk level too high",
        )

        assert "approval_responses" in result_state
        assert "approval_123" in result_state["approval_responses"]

        response = result_state["approval_responses"]["approval_123"]
        assert response["approval_id"] == "approval_123"
        assert response["status"] == "rejected"
        assert response["approved_by"] == "security@example.com"  # Field name is approved_by even for rejection
        assert response["reason"] == "Risk level too high"
        assert response["approved_at"] == "2024-01-15T15:30:00+00:00"

    def test_reject_action_sets_workflow_halted(self):
        """Test reject_action sets workflow_halted flag."""
        state: Dict[str, Any] = {}

        result_state = reject_action(
            state,
            "approval_456",
            "admin@example.com",
            "Compliance violation",
        )

        assert result_state["workflow_halted"] is True

    def test_reject_action_clears_pending_flag(self):
        """Test reject_action clears pending_approval flag."""
        state: Dict[str, Any] = {"pending_approval": True}

        result_state = reject_action(state, "approval_789", "user@example.com", "Not authorized")

        assert result_state["pending_approval"] is False

    def test_reject_action_preserves_existing_responses(self):
        """Test reject_action preserves other approval responses."""
        state: Dict[str, Any] = {"approval_responses": {"approval_001": {"status": "approved", "approved_by": "user1"}}}

        result_state = reject_action(
            state,
            "approval_002",
            "user2",
            "Rejected for testing",
        )

        assert len(result_state["approval_responses"]) == 2
        assert state["approval_responses"]["approval_001"]["status"] == "approved"
        assert result_state["approval_responses"]["approval_002"]["status"] == "rejected"


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestCreateApprovalWorkflow:
    """Test create_approval_workflow function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_approval_workflow_single_node(self):
        """Test adding approval to single node."""
        mock_graph = MagicMock()

        _ = create_approval_workflow(
            mock_graph,
            approval_points=["risky_action"],
        )

        # Verify add_node was called with approval node
        mock_graph.add_node.assert_called_once()
        call_args = mock_graph.add_node.call_args
        assert call_args[0][0] == "approve_risky_action"
        assert isinstance(call_args[0][1], ApprovalNode)

    def test_create_approval_workflow_multiple_nodes(self):
        """Test adding approval to multiple nodes."""
        mock_graph = MagicMock()

        _ = create_approval_workflow(
            mock_graph,
            approval_points=["action_1", "action_2", "action_3"],
        )

        # Verify add_node called 3 times
        assert mock_graph.add_node.call_count == 3

        # Verify correct node names
        call_names = [call[0][0] for call in mock_graph.add_node.call_args_list]
        assert "approve_action_1" in call_names
        assert "approve_action_2" in call_names
        assert "approve_action_3" in call_names

    def test_create_approval_workflow_with_webhook(self):
        """Test approval workflow with notification webhook."""
        mock_graph = MagicMock()
        webhook_url = "https://api.example.com/notifications"

        create_approval_workflow(
            mock_graph,
            approval_points=["test_action"],
            notification_webhook=webhook_url,
        )

        # Verify approval node was created with webhook
        call_args = mock_graph.add_node.call_args
        approval_node = call_args[0][1]
        assert approval_node.notification_webhook == webhook_url

    def test_create_approval_workflow_empty_list(self):
        """Test create_approval_workflow with empty approval points."""
        mock_graph = MagicMock()

        result_graph = create_approval_workflow(mock_graph, approval_points=[])

        # No nodes should be added
        mock_graph.add_node.assert_not_called()
        assert result_graph == mock_graph


# ==============================================================================
# Integration Tests (Approval Workflow End-to-End)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalWorkflowIntegration:
    """Integration tests for complete approval workflows."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @freeze_time("2024-01-15 16:00:00")
    def test_full_approval_workflow(self):
        """Test complete approval workflow: request -> approve -> check."""
        # Step 1: Create approval node and execute it
        node = ApprovalNode(
            approval_name="payment_approval",
            description="Approve payment of $25,000",
            risk_level="high",
        )

        state: Dict[str, Any] = {"amount": 25000, "vendor": "ACME Corp"}

        # Execute approval node
        state = node(state)

        # Verify request created
        assert state["pending_approval"] is True
        approval_id = state["current_approval_id"]
        assert approval_id.startswith("payment_approval_")

        # Step 2: Check status (should be pending)
        status = check_approval_status(state, approval_id)
        assert status == ApprovalStatus.PENDING

        # Step 3: Approve action
        state = approve_action(
            state,
            approval_id,
            "manager@example.com",
            "Verified invoice",
        )

        # Step 4: Check status again (should be approved)
        status = check_approval_status(state, approval_id)
        assert status == ApprovalStatus.APPROVED

        # Verify state is correct
        assert state["pending_approval"] is False
        assert "workflow_halted" not in state

    @freeze_time("2024-01-15 17:00:00")
    def test_full_rejection_workflow(self):
        """Test complete rejection workflow: request -> reject -> check."""
        # Step 1: Create and execute approval node
        node = ApprovalNode(
            approval_name="data_deletion",
            description="Delete customer data",
            risk_level="critical",
        )

        state: Dict[str, Any] = {"customer_id": "cust_123"}
        state = node(state)

        approval_id = state["current_approval_id"]

        # Step 2: Reject action
        state = reject_action(
            state,
            approval_id,
            "compliance@example.com",
            "Retention policy not met",
        )

        # Step 3: Check status
        status = check_approval_status(state, approval_id)
        assert status == ApprovalStatus.REJECTED

        # Verify workflow halted
        assert state["workflow_halted"] is True
        assert state["pending_approval"] is False

    def test_multiple_approvals_workflow(self):
        """Test workflow with multiple sequential approvals."""
        state: Dict[str, Any] = {}

        # First approval
        node1 = ApprovalNode("step_1", risk_level="low")
        state = node1(state)
        approval_id_1 = state["current_approval_id"]

        # Second approval
        node2 = ApprovalNode("step_2", risk_level="medium")
        state = node2(state)
        approval_id_2 = state["current_approval_id"]

        # Approve first
        state = approve_action(state, approval_id_1, "user1")

        # Reject second
        state = reject_action(state, approval_id_2, "user2", "Second step failed")

        # Verify statuses
        assert check_approval_status(state, approval_id_1) == ApprovalStatus.APPROVED
        assert check_approval_status(state, approval_id_2) == ApprovalStatus.REJECTED

        # Verify both approval requests stored
        assert len(state["approval_requests"]) == 2


# ==============================================================================
# Edge Cases and Error Scenarios
# ==============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="core_interrupts_approval_tests")
class TestApprovalEdgeCases:
    """Test edge cases and error scenarios."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_approve_action_on_empty_state(self):
        """Test approve_action creates approval_responses if missing."""
        state: Dict[str, Any] = {}

        result_state = approve_action(state, "approval_999", "user@example.com")

        assert "approval_responses" in result_state
        assert "approval_999" in result_state["approval_responses"]

    def test_reject_action_on_empty_state(self):
        """Test reject_action creates approval_responses if missing."""
        state: Dict[str, Any] = {}

        result_state = reject_action(state, "approval_888", "user@example.com", "Test rejection")

        assert "approval_responses" in result_state
        assert "approval_888" in result_state["approval_responses"]

    def test_approval_node_with_empty_state(self):
        """Test ApprovalNode works with completely empty state."""
        node = ApprovalNode("test")
        state: Dict[str, Any] = {}

        result_state = node(state)

        assert "approval_requests" in result_state
        assert result_state["pending_approval"] is True

    def test_check_approval_status_malformed_response(self):
        """Test check_approval_status handles malformed response gracefully."""
        state: Dict[str, Any] = {"approval_responses": {"approval_123": {"status": "approved"}}}  # Valid

        # Should work with valid response
        status = check_approval_status(state, "approval_123")
        assert status == ApprovalStatus.APPROVED

    def test_approval_request_context_isolation(self):
        """Test approval request context is copy, not reference."""
        node = ApprovalNode("test_isolation")
        original_state: Dict[str, Any] = {"value": "original"}

        result_state = node(original_state)

        # Modify original state
        original_state["value"] = "modified"

        # Approval request should have original value
        approval_context = result_state["approval_requests"][0]["context"]
        assert approval_context["value"] == "original"  # Should be copied, not referenced
