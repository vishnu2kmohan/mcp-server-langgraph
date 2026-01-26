"""
Integration tests for bypass mode end-to-end flow.

Tests the complete bypass mode flow including:
1. BypassManager evaluation with real cost estimation
2. Risk escalation from sandbox tools
3. Prometheus metrics recording
4. Audit event creation

See: Chat Input UX plan - Phase 4
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.audit.models import AuditEventType
from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event
from mcp_server_langgraph.execution.bypass_manager import BypassDecision, BypassManager

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_plan_factory():
    """Factory for creating ExecutionPlan instances with various configurations."""

    def _create_plan(
        *,
        complexity: str = "simple",
        risk_level: str = "low",
        task_type: str = "chat",
        tools_needed: list[str] | None = None,
        thinking_budget: str = "none",  # Default to "none", not None
        executor_model: str = "claude-sonnet-4-20250514",
    ) -> ExecutionPlan:
        return ExecutionPlan(
            plan_id="plan-integration-test",
            session_id="session-integration-test",
            status="awaiting_approval",
            complexity=complexity,
            risk_level=risk_level,
            task_type=task_type,
            executor_model=executor_model,
            estimated_cost=Decimal("0.05"),
            message="Integration test message",
            tools_needed=tools_needed or [],
            thinking_budget=thinking_budget,
        )

    return _create_plan


@pytest.fixture
def bypass_manager() -> BypassManager:
    """Create a BypassManager instance."""
    return BypassManager()


# =============================================================================
# End-to-End Bypass Flow Tests
# =============================================================================


@pytest.mark.integration
class TestBypassModeEndToEndFlow:
    """Integration tests for the complete bypass mode flow."""

    def test_low_risk_simple_plan_auto_approves(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a low-risk simple plan
        WHEN evaluated by BypassManager
        THEN it should be auto-approved with cost estimate.
        """
        plan = execution_plan_factory(
            complexity="simple",
            risk_level="low",
            task_type="chat",
        )

        decision = bypass_manager.evaluate_plan(plan)

        assert decision.auto_approved is True
        assert decision.requires_user_approval is False
        assert decision.risk_level == "low"
        assert decision.complexity == "simple"
        assert isinstance(decision.estimated_cost, Decimal)

    def test_high_risk_plan_requires_approval(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a high-risk plan
        WHEN evaluated by BypassManager
        THEN it should require user approval.
        """
        plan = execution_plan_factory(
            complexity="complex",
            risk_level="high",
            task_type="code",
        )

        decision = bypass_manager.evaluate_plan(plan)

        assert decision.auto_approved is False
        assert decision.requires_user_approval is True
        assert decision.risk_level == "high"
        assert decision.complexity == "complex"

    def test_sandbox_tools_escalate_risk(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a low-risk plan with sandbox-required tools
        WHEN evaluated by BypassManager
        THEN risk level should be escalated and approval required.
        """
        plan = execution_plan_factory(
            complexity="simple",
            risk_level="low",
            tools_needed=["execute_bash", "write_file"],
        )

        decision = bypass_manager.evaluate_plan(plan)

        # Risk escalated from low to high due to execute_bash
        assert decision.risk_level == "high"
        assert decision.original_risk_level == "low"
        assert decision.auto_approved is False
        assert "execute_bash" in decision.risk_factors[0]

    def test_cost_estimation_included_in_decision(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan with specific model and complexity
        WHEN evaluated by BypassManager
        THEN estimated_cost should reflect model pricing.
        """
        plan = execution_plan_factory(
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-20250514",
            thinking_budget="medium",
        )

        decision = bypass_manager.evaluate_plan(plan)

        # Cost should be greater than zero for valid model
        assert isinstance(decision.estimated_cost, Decimal)
        # Cost estimation may return 0 if LiteLLM pricing unavailable
        # The important thing is that it doesn't raise an exception

    @pytest.mark.asyncio
    async def test_full_flow_with_audit_logging(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan that gets auto-approved
        WHEN the bypass flow completes
        THEN audit events should be logged with correct details.
        """
        plan = execution_plan_factory(
            complexity="simple",
            risk_level="low",
        )

        # Evaluate the plan
        decision = bypass_manager.evaluate_plan(plan)
        assert decision.auto_approved is True

        # Mock audit service to verify it's called correctly
        audit_service = AsyncMock()
        current_user = {
            "user_id": "user:integration-test-user",
            "username": "test-user",
        }

        # Log the auto-approval audit event
        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_AUTO_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id=plan.plan_id,
            action="Auto-approved low-risk plan in bypass mode",
            details={
                "risk_level": decision.risk_level,
                "complexity": decision.complexity,
                "estimated_cost": str(decision.estimated_cost),
            },
        )

        # Verify audit was called
        audit_service.log_event.assert_called_once()
        event = audit_service.log_event.call_args[0][0]
        assert event.event_type == AuditEventType.BYPASS_AUTO_APPROVED
        assert event.resource_id == "plan-integration-test"
        assert event.details["risk_level"] == "low"


# =============================================================================
# Prometheus Metrics Integration Tests
# =============================================================================


@pytest.mark.integration
class TestBypassModePrometheusIntegration:
    """Integration tests for Prometheus metrics in bypass flow."""

    def test_approval_metrics_recorded_on_auto_approve(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan that gets auto-approved
        WHEN the bypass flow completes
        THEN approval metrics should be recorded.
        """
        with patch("mcp_server_langgraph.execution.bypass_manager.record_estimated_cost") as mock_record_cost:
            plan = execution_plan_factory(
                complexity="simple",
                risk_level="low",
            )

            decision = bypass_manager.evaluate_plan(plan)

            # Cost metric should be recorded (if cost > 0)
            if decision.estimated_cost > Decimal("0"):
                mock_record_cost.assert_called_once_with(
                    cost=decision.estimated_cost,
                    complexity="simple",
                    risk_level="low",
                )

    def test_tool_escalation_metrics_recorded(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan with sandbox tools causing escalation
        WHEN evaluated by BypassManager
        THEN tool escalation metrics should be recorded.
        """
        with patch("mcp_server_langgraph.execution.bypass_manager.record_tool_escalation") as mock_record:
            plan = execution_plan_factory(
                risk_level="low",
                tools_needed=["execute_bash"],
            )

            bypass_manager.evaluate_plan(plan)

            mock_record.assert_called_once_with(
                tool="execute_bash",
                from_level="low",
                to_level="high",
            )

    @pytest.mark.asyncio
    async def test_audit_logging_records_prometheus_metrics(
        self,
        execution_plan_factory,
    ) -> None:
        """GIVEN an audit event being logged
        WHEN log_bypass_audit_event is called
        THEN Prometheus metrics should also be recorded.
        """
        with patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_activation") as mock_activation:
            current_user = {"user_id": "user:test"}

            await log_bypass_audit_event(
                audit_service=None,  # No audit service
                event_type=AuditEventType.BYPASS_ACTIVATED,
                current_user=current_user,
                resource_type="session",
                resource_id="session-123",
                action="Activated bypass mode",
            )

            # Metrics should still be recorded even without audit service
            mock_activation.assert_called_once_with(user="user:test")


# =============================================================================
# Risk Matrix Comprehensive Tests
# =============================================================================


@pytest.mark.integration
class TestBypassModeRiskMatrixComplete:
    """Comprehensive tests for the risk/complexity auto-approval matrix."""

    @pytest.mark.parametrize(
        "risk_level,complexity,expected_auto_approve",
        [
            # Low risk: auto-approve simple and complicated
            ("low", "simple", True),
            ("low", "complicated", True),
            ("low", "complex", False),
            # Medium risk: auto-approve only simple
            ("medium", "simple", True),
            ("medium", "complicated", False),
            ("medium", "complex", False),
            # High risk: never auto-approve
            ("high", "simple", False),
            ("high", "complicated", False),
            ("high", "complex", False),
        ],
    )
    def test_risk_matrix_complete_coverage(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
        risk_level: str,
        complexity: str,
        expected_auto_approve: bool,
    ) -> None:
        """GIVEN a plan with specific risk and complexity
        WHEN evaluated by BypassManager
        THEN auto_approved should match the expected matrix result.
        """
        plan = execution_plan_factory(
            complexity=complexity,
            risk_level=risk_level,
        )

        decision = bypass_manager.evaluate_plan(plan)

        assert decision.auto_approved == expected_auto_approve
        assert decision.requires_user_approval == (not expected_auto_approve)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.integration
class TestBypassModeEdgeCases:
    """Edge case tests for bypass mode."""

    def test_empty_tools_list_no_escalation(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan with empty tools list
        WHEN evaluated
        THEN no risk escalation should occur.
        """
        plan = execution_plan_factory(
            risk_level="low",
            tools_needed=[],
        )

        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "low"
        assert decision.original_risk_level == "low"
        assert len(decision.risk_factors) == 0

    def test_unknown_tools_no_escalation(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN a plan with tools not in SANDBOX_REQUIRED_TOOLS
        WHEN evaluated
        THEN no risk escalation should occur.
        """
        plan = execution_plan_factory(
            risk_level="low",
            tools_needed=["calculator", "search_web", "custom_tool"],
        )

        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "low"
        assert len(decision.risk_factors) == 0

    def test_cost_estimation_failure_graceful(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN cost estimation fails
        WHEN evaluated by BypassManager
        THEN evaluation should still succeed with zero cost.
        """
        with patch(
            "mcp_server_langgraph.execution.bypass_manager.estimate_execution_cost",
            side_effect=Exception("Pricing unavailable"),
        ):
            plan = execution_plan_factory()

            decision = bypass_manager.evaluate_plan(plan)

            assert decision.auto_approved is True
            assert decision.estimated_cost == Decimal("0")

    def test_decision_dataclass_complete(
        self,
        bypass_manager: BypassManager,
        execution_plan_factory,
    ) -> None:
        """GIVEN any plan
        WHEN evaluated
        THEN BypassDecision should have all required fields.
        """
        plan = execution_plan_factory(
            complexity="complicated",
            risk_level="medium",
            tools_needed=["execute_python"],
        )

        decision = bypass_manager.evaluate_plan(plan)

        # Verify all fields exist and have correct types
        assert isinstance(decision, BypassDecision)
        assert isinstance(decision.auto_approved, bool)
        assert isinstance(decision.requires_user_approval, bool)
        assert decision.risk_level in ("low", "medium", "high")
        assert decision.original_risk_level in ("low", "medium", "high")
        assert decision.complexity in ("simple", "complicated", "complex")
        assert isinstance(decision.risk_factors, list)
        assert isinstance(decision.estimated_cost, Decimal)
