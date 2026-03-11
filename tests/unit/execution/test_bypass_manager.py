"""
Unit tests for BypassManager - risk-aware auto-approval for bypass mode.

Tests cover:
1. Auto-approval matrix (complexity x risk_level)
2. Risk escalation from sandbox-required tools
3. BypassDecision dataclass attributes
"""

from decimal import Decimal

import pytest

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from mcp_server_langgraph.execution.bypass_manager import (
    BypassDecision,
    BypassManager,
    TOOL_RISK_ESCALATION,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def bypass_manager() -> BypassManager:
    """Create a BypassManager instance."""
    return BypassManager()


def _make_plan(
    complexity: str = "simple",
    risk_level: str = "low",
    tools_needed: list[str] | None = None,
) -> ExecutionPlan:
    """Create an ExecutionPlan with specified attributes."""
    return ExecutionPlan(
        plan_id="plan-test-123",
        session_id="session-test-456",
        status="awaiting_approval",
        complexity=complexity,
        risk_level=risk_level,
        task_type="chat",
        executor_model="claude-sonnet-4-20250514",
        estimated_cost=Decimal("0.05"),
        message="Test message",
        tools_needed=tools_needed or [],
    )


# =============================================================================
# Auto-Approval Matrix Tests
# =============================================================================


class TestAutoApprovalMatrix:
    """Test the auto-approval matrix based on risk_level and complexity."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "risk_level,complexity,expected_auto_approve",
        [
            # Low risk: auto-approve simple and complicated, not complex
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
    def test_auto_approval_matrix(
        self,
        bypass_manager: BypassManager,
        risk_level: str,
        complexity: str,
        expected_auto_approve: bool,
    ) -> None:
        """GIVEN a plan with specified risk_level and complexity
        WHEN evaluate_plan is called
        THEN it returns the expected auto_approved decision.
        """
        plan = _make_plan(complexity=complexity, risk_level=risk_level)
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.auto_approved == expected_auto_approve
        assert decision.requires_user_approval == (not expected_auto_approve)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# =============================================================================
# Risk Escalation Tests
# =============================================================================


class TestRiskEscalation:
    """Test risk level escalation based on sandbox-required tools."""

    @pytest.mark.unit
    def test_no_tools_no_escalation(self, bypass_manager: BypassManager) -> None:
        """GIVEN a plan with no tools
        WHEN evaluate_plan is called
        THEN risk level is not escalated.
        """
        plan = _make_plan(risk_level="low", tools_needed=[])
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "low"
        assert decision.original_risk_level == "low"
        assert len(decision.risk_factors) == 0

    @pytest.mark.unit
    def test_safe_tools_no_escalation(self, bypass_manager: BypassManager) -> None:
        """GIVEN a plan with only safe tools (not in SANDBOX_REQUIRED_TOOLS)
        WHEN evaluate_plan is called
        THEN risk level is not escalated.
        """
        plan = _make_plan(
            risk_level="low",
            tools_needed=["calculator", "search_knowledge_base"],
        )
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "low"
        assert decision.original_risk_level == "low"
        # No risk factors since these tools are safe
        assert len(decision.risk_factors) == 0

    @pytest.mark.unit
    def test_execute_bash_escalates_to_high(self, bypass_manager: BypassManager) -> None:
        """GIVEN a low-risk plan with execute_bash tool
        WHEN evaluate_plan is called
        THEN risk level is escalated to high.
        """
        plan = _make_plan(risk_level="low", tools_needed=["execute_bash"])
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "high"
        assert decision.original_risk_level == "low"
        assert "execute_bash" in decision.risk_factors[0]
        assert decision.auto_approved is False

    @pytest.mark.unit
    def test_execute_python_escalates_to_medium(self, bypass_manager: BypassManager) -> None:
        """GIVEN a low-risk plan with execute_python tool
        WHEN evaluate_plan is called
        THEN risk level is escalated to medium.
        """
        plan = _make_plan(risk_level="low", tools_needed=["execute_python"])
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "medium"
        assert decision.original_risk_level == "low"
        assert any("execute_python" in factor for factor in decision.risk_factors)

    @pytest.mark.unit
    def test_multiple_sandbox_tools_takes_highest_risk(self, bypass_manager: BypassManager) -> None:
        """GIVEN a plan with multiple sandbox tools of different risk levels
        WHEN evaluate_plan is called
        THEN the highest risk level is used.
        """
        plan = _make_plan(
            risk_level="low",
            tools_needed=["execute_python", "execute_bash", "capture_screenshot"],
        )
        decision = bypass_manager.evaluate_plan(plan)

        # execute_bash is high, execute_python is medium, so high wins
        assert decision.risk_level == "high"
        assert decision.original_risk_level == "low"

    @pytest.mark.unit
    def test_medium_plan_with_high_tool_escalates(self, bypass_manager: BypassManager) -> None:
        """GIVEN a medium-risk plan with execute_bash
        WHEN evaluate_plan is called
        THEN risk is still escalated to high.
        """
        plan = _make_plan(risk_level="medium", tools_needed=["execute_bash"])
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "high"
        assert decision.original_risk_level == "medium"

    @pytest.mark.unit
    def test_high_plan_with_high_tool_no_change(self, bypass_manager: BypassManager) -> None:
        """GIVEN a high-risk plan with high-risk tool
        WHEN evaluate_plan is called
        THEN risk stays at high (no escalation needed).
        """
        plan = _make_plan(risk_level="high", tools_needed=["execute_bash"])
        decision = bypass_manager.evaluate_plan(plan)

        assert decision.risk_level == "high"
        assert decision.original_risk_level == "high"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# =============================================================================
# BypassDecision Attribute Tests
# =============================================================================


class TestBypassDecisionAttributes:
    """Test BypassDecision dataclass attributes."""

    @pytest.mark.unit
    def test_decision_has_all_required_attributes(self, bypass_manager: BypassManager) -> None:
        """GIVEN any plan
        WHEN evaluate_plan is called
        THEN the decision has all required attributes.
        """
        plan = _make_plan()
        decision = bypass_manager.evaluate_plan(plan)

        assert isinstance(decision, BypassDecision)
        assert isinstance(decision.auto_approved, bool)
        assert isinstance(decision.requires_user_approval, bool)
        assert decision.risk_level in ("low", "medium", "high")
        assert decision.original_risk_level in ("low", "medium", "high")
        assert decision.complexity in ("simple", "complicated", "complex")
        assert isinstance(decision.risk_factors, list)

    @pytest.mark.unit
    def test_decision_risk_factors_are_descriptive(self, bypass_manager: BypassManager) -> None:
        """GIVEN a plan with sandbox tools
        WHEN evaluate_plan is called
        THEN risk factors contain descriptive messages.
        """
        plan = _make_plan(tools_needed=["execute_bash", "write_file"])
        decision = bypass_manager.evaluate_plan(plan)

        # Should have at least sandbox tools factor
        assert len(decision.risk_factors) >= 1
        assert any("Sandbox-required tools" in f for f in decision.risk_factors)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# =============================================================================
# Tool Risk Escalation Configuration Tests
# =============================================================================


class TestToolRiskEscalationConfig:
    """Test TOOL_RISK_ESCALATION configuration is correct."""

    @pytest.mark.unit
    def test_execute_bash_is_high_risk(self) -> None:
        """GIVEN TOOL_RISK_ESCALATION config
        THEN execute_bash is classified as high risk.
        """
        assert TOOL_RISK_ESCALATION.get("execute_bash") == "high"

    @pytest.mark.unit
    def test_execute_python_is_medium_risk(self) -> None:
        """GIVEN TOOL_RISK_ESCALATION config
        THEN execute_python is classified as medium risk.
        """
        assert TOOL_RISK_ESCALATION.get("execute_python") == "medium"

    @pytest.mark.unit
    def test_capture_screenshot_is_low_risk(self) -> None:
        """GIVEN TOOL_RISK_ESCALATION config
        THEN capture_screenshot is classified as low risk.
        """
        assert TOOL_RISK_ESCALATION.get("capture_screenshot") == "low"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# =============================================================================
# Prometheus Metrics Integration Tests
# =============================================================================


class TestBypassManagerPrometheusMetrics:
    """Test Prometheus metrics are recorded during bypass evaluation."""

    @pytest.mark.unit
    def test_tool_escalation_records_metric(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with tools that cause escalation
        WHEN evaluate_plan is called
        THEN record_tool_escalation is called for each escalation.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_manager.record_tool_escalation")

        plan = _make_plan(risk_level="low", tools_needed=["execute_bash"])
        bypass_manager.evaluate_plan(plan)

        # Should record escalation from low to high for execute_bash
        mock_record.assert_called_once_with(
            tool="execute_bash",
            from_level="low",
            to_level="high",
        )

    @pytest.mark.unit
    def test_no_tool_escalation_no_metric(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with no escalating tools
        WHEN evaluate_plan is called
        THEN record_tool_escalation is not called.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_manager.record_tool_escalation")

        plan = _make_plan(risk_level="low", tools_needed=["search_knowledge_base"])
        bypass_manager.evaluate_plan(plan)

        mock_record.assert_not_called()

    @pytest.mark.unit
    def test_multiple_tool_escalations_record_metrics(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with multiple escalating tools
        WHEN evaluate_plan is called
        THEN record_tool_escalation is called for each distinct escalation.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_manager.record_tool_escalation")

        # execute_python escalates low->medium, execute_bash escalates medium->high
        plan = _make_plan(risk_level="low", tools_needed=["execute_python", "execute_bash"])
        bypass_manager.evaluate_plan(plan)

        # Should have been called for escalations
        assert mock_record.call_count >= 1

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# =============================================================================
# Cost Estimator Integration Tests
# =============================================================================


class TestBypassManagerCostEstimation:
    """Test cost estimation integration in BypassManager."""

    @pytest.mark.unit
    def test_evaluate_plan_includes_estimated_cost(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with model and task_type
        WHEN evaluate_plan is called
        THEN the decision includes estimated_cost.
        """
        # Mock the cost estimation
        from decimal import Decimal

        mocker.patch(
            "mcp_server_langgraph.execution.bypass_manager.estimate_execution_cost",
            side_effect=lambda **kwargs: Decimal("0.05"),
        )

        plan = _make_plan(
            complexity="simple",
            risk_level="low",
        )
        decision = bypass_manager.evaluate_plan(plan)

        # Decision should include estimated_cost
        assert hasattr(decision, "estimated_cost")
        assert decision.estimated_cost == Decimal("0.05")

    @pytest.mark.unit
    def test_estimated_cost_uses_plan_parameters(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with specific complexity and task_type
        WHEN evaluate_plan is called
        THEN estimate_execution_cost is called with correct parameters.
        """
        mock_estimate = mocker.patch(
            "mcp_server_langgraph.execution.bypass_manager.estimate_execution_cost",
            side_effect=lambda **kwargs: Decimal("0.10"),
        )

        plan = _make_plan(
            complexity="complicated",
            risk_level="medium",
        )
        bypass_manager.evaluate_plan(plan)

        mock_estimate.assert_called_once_with(
            model=plan.executor_model,
            task_type=plan.task_type,
            complexity="complicated",
            thinking_budget=plan.thinking_budget or "none",
        )

    @pytest.mark.unit
    def test_records_estimated_cost_prometheus_metric(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN a plan with estimated cost
        WHEN evaluate_plan is called
        THEN record_estimated_cost Prometheus metric is recorded.
        """
        from decimal import Decimal

        mocker.patch(
            "mcp_server_langgraph.execution.bypass_manager.estimate_execution_cost",
            side_effect=lambda **kwargs: Decimal("0.07"),
        )
        mock_record_cost = mocker.patch("mcp_server_langgraph.execution.bypass_manager.record_estimated_cost")

        plan = _make_plan(complexity="simple", risk_level="low")
        bypass_manager.evaluate_plan(plan)

        mock_record_cost.assert_called_once_with(
            cost=Decimal("0.07"),
            complexity="simple",
            risk_level="low",  # Using effective risk level
        )

    @pytest.mark.unit
    def test_cost_estimation_failure_does_not_fail_evaluation(self, bypass_manager: BypassManager, mocker) -> None:
        """GIVEN cost estimation fails
        WHEN evaluate_plan is called
        THEN evaluation still succeeds with zero cost.
        """
        from decimal import Decimal

        mocker.patch(
            "mcp_server_langgraph.execution.bypass_manager.estimate_execution_cost",
            side_effect=Exception("LiteLLM pricing unavailable"),
        )

        plan = _make_plan(complexity="simple", risk_level="low")
        decision = bypass_manager.evaluate_plan(plan)

        # Should still return a valid decision with zero cost
        assert decision.auto_approved is True
        assert decision.estimated_cost == Decimal("0")

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
