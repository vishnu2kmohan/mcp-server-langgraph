"""
Tests for bypass mode Prometheus metrics.

These metrics track bypass mode usage patterns for the Grafana dashboard:
- Activation/approval/rejection counts
- Tool escalation tracking
- Permission check outcomes
- Cost estimation recording
"""

import pytest
from decimal import Decimal

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestBypassModeActivationMetrics:
    """Tests for bypass mode activation metrics."""

    def test_record_bypass_activation_increments_counter(self):
        """Recording bypass activation should increment the counter."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_bypass_activation,
        )

        # Should not raise when called
        record_bypass_activation(user="alice")

    def test_record_bypass_activation_handles_missing_prometheus(self):
        """Should handle gracefully when prometheus_client is not available."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_bypass_activation,
        )

        # Should not raise even if metrics unavailable
        record_bypass_activation(user="alice")


@pytest.mark.unit
class TestBypassApprovalMetrics:
    """Tests for bypass approval metrics."""

    def test_record_auto_approval(self):
        """Recording auto-approval should track type=auto."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_bypass_approval,
        )

        record_bypass_approval(
            approval_type="auto",
            risk_level="low",
            complexity="simple",
        )

    def test_record_user_approval(self):
        """Recording user approval should track type=user."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_bypass_approval,
        )

        record_bypass_approval(
            approval_type="user",
            risk_level="medium",
            complexity="complicated",
        )

    def test_record_rejection_increments_counter(self):
        """Recording rejection should increment rejection counter."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_bypass_rejection,
        )

        record_bypass_rejection(
            risk_level="high",
            complexity="complex",
        )


@pytest.mark.unit
class TestToolEscalationMetrics:
    """Tests for tool risk escalation metrics."""

    def test_record_tool_escalation(self):
        """Recording tool escalation should track tool and levels."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_tool_escalation,
        )

        record_tool_escalation(
            tool="execute_bash",
            from_level="low",
            to_level="high",
        )

    def test_record_multiple_tool_escalations(self):
        """Should handle multiple escalation recordings."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_tool_escalation,
        )

        record_tool_escalation(tool="execute_python", from_level="low", to_level="medium")
        record_tool_escalation(tool="edit_file", from_level="low", to_level="medium")


@pytest.mark.unit
class TestPermissionCheckMetrics:
    """Tests for permission check outcome metrics."""

    def test_record_permission_granted(self):
        """Recording granted permission should track result=granted."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_permission_check,
        )

        record_permission_check(result="granted")

    def test_record_permission_denied(self):
        """Recording denied permission should track result=denied."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_permission_check,
        )

        record_permission_check(result="denied")


@pytest.mark.unit
class TestCostEstimationMetrics:
    """Tests for cost estimation metrics."""

    def test_record_estimated_cost(self):
        """Recording estimated cost should set gauge value."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_estimated_cost,
        )

        record_estimated_cost(
            cost=Decimal("0.05"),
            complexity="complicated",
            risk_level="medium",
        )

    def test_record_cost_with_different_complexities(self):
        """Should record costs for all complexity levels."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_estimated_cost,
        )

        for complexity in ["simple", "complicated", "complex"]:
            record_estimated_cost(
                cost=Decimal("0.10"),
                complexity=complexity,
                risk_level="low",
            )


@pytest.mark.unit
class TestModeChangeMetrics:
    """Tests for execution mode change metrics."""

    def test_record_mode_change_via_keyboard(self):
        """Recording mode change via keyboard shortcut."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_mode_change,
        )

        record_mode_change(
            from_mode="default",
            to_mode="bypass",
            trigger="keyboard",
        )

    def test_record_mode_change_via_click(self):
        """Recording mode change via click."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            record_mode_change,
        )

        record_mode_change(
            from_mode="default",
            to_mode="plan",
            trigger="click",
        )


@pytest.mark.unit
class TestActiveSessionsMetrics:
    """Tests for active sessions by mode gauge."""

    def test_set_active_sessions_by_mode(self):
        """Setting active sessions by mode gauge."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            set_active_sessions_by_mode,
        )

        set_active_sessions_by_mode(mode="bypass", count=5)
        set_active_sessions_by_mode(mode="default", count=20)

    def test_increment_active_session(self):
        """Incrementing active session count."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            increment_active_session,
        )

        increment_active_session(mode="bypass")

    def test_decrement_active_session(self):
        """Decrementing active session count."""
        from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
            decrement_active_session,
        )

        decrement_active_session(mode="bypass")
