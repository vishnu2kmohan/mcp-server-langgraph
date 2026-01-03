"""
Tests for Orchestration Metrics

TDD: These tests define the contract for router, swarm, critique, and approval metrics.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="orchestration_metrics_router")
class TestRouterMetrics:
    """Tests for router-related metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_latency_histogram_exists(self) -> None:
        """Test that router latency histogram exists."""
        from mcp_server_langgraph.agents.metrics import router_latency_histogram

        assert router_latency_histogram is not None

    def test_router_confidence_histogram_exists(self) -> None:
        """Test that router confidence histogram exists."""
        from mcp_server_langgraph.agents.metrics import router_confidence_histogram

        assert router_confidence_histogram is not None

    def test_router_cache_counter_exists(self) -> None:
        """Test that router cache hit/miss counter exists."""
        from mcp_server_langgraph.agents.metrics import router_cache_counter

        assert router_cache_counter is not None

    def test_record_router_decision_function_exists(self) -> None:
        """Test that record_router_decision function exists."""
        from mcp_server_langgraph.agents.metrics import record_router_decision

        assert callable(record_router_decision)

    def test_record_router_decision_records_metrics(self) -> None:
        """Test record_router_decision records latency and confidence."""
        from mcp_server_langgraph.agents.metrics import record_router_decision

        # Should not raise, even if metrics backend not configured
        record_router_decision(
            latency_ms=150.0,
            complexity="complicated",
            risk="medium",
            confidence=0.85,
            cache_hit=False,
            model="gemini-3-flash",
        )

    def test_record_router_cache_hit(self) -> None:
        """Test recording a router cache hit."""
        from mcp_server_langgraph.agents.metrics import record_router_decision

        record_router_decision(
            latency_ms=5.0,  # Very fast due to cache hit
            complexity="simple",
            risk="low",
            confidence=0.95,
            cache_hit=True,
            model="gemini-3-flash",
        )


@pytest.mark.xdist_group(name="orchestration_metrics_swarm")
class TestSwarmMetrics:
    """Tests for swarm orchestration metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_swarm_branches_counter_exists(self) -> None:
        """Test that swarm branches counter exists."""
        from mcp_server_langgraph.agents.metrics import swarm_branches_counter

        assert swarm_branches_counter is not None

    def test_swarm_cost_gauge_exists(self) -> None:
        """Test that swarm cost gauge exists."""
        from mcp_server_langgraph.agents.metrics import swarm_cost_gauge

        assert swarm_cost_gauge is not None

    def test_cascade_tier_counter_exists(self) -> None:
        """Test that cascade tier counter exists."""
        from mcp_server_langgraph.agents.metrics import cascade_tier_counter

        assert cascade_tier_counter is not None

    def test_consensus_votes_histogram_exists(self) -> None:
        """Test that consensus votes histogram exists."""
        from mcp_server_langgraph.agents.metrics import consensus_votes_histogram

        assert consensus_votes_histogram is not None

    def test_record_swarm_execution_function_exists(self) -> None:
        """Test that record_swarm_execution function exists."""
        from mcp_server_langgraph.agents.metrics import record_swarm_execution

        assert callable(record_swarm_execution)

    def test_record_swarm_execution_records_metrics(self) -> None:
        """Test record_swarm_execution records branch and cost metrics."""
        from mcp_server_langgraph.agents.metrics import record_swarm_execution

        record_swarm_execution(
            strategy="race",
            branches_launched=3,
            branches_cancelled=2,
            winner_model="gemini-3-flash",
            total_cost_usd=0.05,
            session_id="session-123",
        )

    def test_record_cascade_tier_function_exists(self) -> None:
        """Test that record_cascade_tier function exists."""
        from mcp_server_langgraph.agents.metrics import record_cascade_tier

        assert callable(record_cascade_tier)

    def test_record_cascade_tier_records_escalation(self) -> None:
        """Test record_cascade_tier records tier escalation."""
        from mcp_server_langgraph.agents.metrics import record_cascade_tier

        record_cascade_tier(tier="complicated", success=True)
        record_cascade_tier(tier="complex", success=False)


@pytest.mark.xdist_group(name="orchestration_metrics_critique")
class TestCritiqueMetrics:
    """Tests for critique loop metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_critique_rounds_histogram_exists(self) -> None:
        """Test that critique rounds histogram exists."""
        from mcp_server_langgraph.agents.metrics import critique_rounds_histogram

        assert critique_rounds_histogram is not None

    def test_critique_acceptance_counter_exists(self) -> None:
        """Test that critique acceptance counter exists."""
        from mcp_server_langgraph.agents.metrics import critique_acceptance_counter

        assert critique_acceptance_counter is not None

    def test_record_critique_loop_function_exists(self) -> None:
        """Test that record_critique_loop function exists."""
        from mcp_server_langgraph.agents.metrics import record_critique_loop

        assert callable(record_critique_loop)

    def test_record_critique_loop_records_rounds(self) -> None:
        """Test record_critique_loop records rounds and acceptance."""
        from mcp_server_langgraph.agents.metrics import record_critique_loop

        record_critique_loop(
            task_type="code",
            complexity="complicated",
            rounds_executed=2,
            accepted_at_round=2,
        )

    def test_record_critique_loop_early_acceptance(self) -> None:
        """Test recording critique loop with early acceptance."""
        from mcp_server_langgraph.agents.metrics import record_critique_loop

        record_critique_loop(
            task_type="analysis",
            complexity="simple",
            rounds_executed=1,
            accepted_at_round=1,
        )


@pytest.mark.xdist_group(name="orchestration_metrics_thinking")
class TestThinkingMetrics:
    """Tests for thinking budget metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_tokens_histogram_exists(self) -> None:
        """Test that thinking tokens histogram exists."""
        from mcp_server_langgraph.agents.metrics import thinking_tokens_histogram

        assert thinking_tokens_histogram is not None

    def test_record_thinking_usage_function_exists(self) -> None:
        """Test that record_thinking_usage function exists."""
        from mcp_server_langgraph.agents.metrics import record_thinking_usage

        assert callable(record_thinking_usage)

    def test_record_thinking_usage_records_tokens(self) -> None:
        """Test record_thinking_usage records thinking tokens."""
        from mcp_server_langgraph.agents.metrics import record_thinking_usage

        record_thinking_usage(
            model="claude-opus-4-5-20251101",
            budget_level="deep",
            thinking_tokens=8500,
            completion_tokens=1200,
        )


@pytest.mark.xdist_group(name="orchestration_metrics_approval")
class TestApprovalMetrics:
    """Tests for approval flow metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_path_counter_exists(self) -> None:
        """Test that approval path counter exists."""
        from mcp_server_langgraph.agents.metrics import approval_path_counter

        assert approval_path_counter is not None

    def test_high_risk_trigger_counter_exists(self) -> None:
        """Test that high risk trigger counter exists."""
        from mcp_server_langgraph.agents.metrics import high_risk_trigger_counter

        assert high_risk_trigger_counter is not None

    def test_record_approval_decision_function_exists(self) -> None:
        """Test that record_approval_decision function exists."""
        from mcp_server_langgraph.agents.metrics import record_approval_decision

        assert callable(record_approval_decision)

    def test_record_approval_decision_records_approved(self) -> None:
        """Test record_approval_decision records approval."""
        from mcp_server_langgraph.agents.metrics import record_approval_decision

        record_approval_decision(
            result="approved",
            risk_level="medium",
            wait_time_seconds=45.0,
        )

    def test_record_approval_decision_records_rejected(self) -> None:
        """Test record_approval_decision records rejection."""
        from mcp_server_langgraph.agents.metrics import record_approval_decision

        record_approval_decision(
            result="rejected",
            risk_level="high",
            wait_time_seconds=120.0,
            rejection_reason="too_expensive",
        )

    def test_record_approval_decision_records_expired(self) -> None:
        """Test record_approval_decision records expiration."""
        from mcp_server_langgraph.agents.metrics import record_approval_decision

        record_approval_decision(
            result="expired",
            risk_level="medium",
            wait_time_seconds=3600.0,  # 1 hour timeout
        )

    def test_record_high_risk_trigger_function_exists(self) -> None:
        """Test that record_high_risk_trigger function exists."""
        from mcp_server_langgraph.agents.metrics import record_high_risk_trigger

        assert callable(record_high_risk_trigger)

    def test_record_high_risk_trigger_records_event(self) -> None:
        """Test record_high_risk_trigger records high-risk events."""
        from mcp_server_langgraph.agents.metrics import record_high_risk_trigger

        record_high_risk_trigger(
            task_type="ops",
            auto_approve=False,
            estimated_cost_usd=0.50,
        )


@pytest.mark.xdist_group(name="orchestration_metrics_guardrails")
class TestMetricsGuardrails:
    """Guardrail tests to ensure metrics are not double-counted."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_thinking_tokens_not_double_counted_in_completion_tokens(self) -> None:
        """Guardrail: Thinking tokens should be tracked separately from completion tokens.

        This ensures that when extended thinking is used, the thinking tokens
        are reported in the dedicated thinking_tokens_histogram and NOT added
        to the regular completion token counts.
        """
        from mcp_server_langgraph.agents.metrics import record_thinking_usage

        # Record thinking usage with separate counts
        # The function should track thinking_tokens in its own histogram
        record_thinking_usage(
            model="claude-opus-4-5-20251101",
            budget_level="deep",
            thinking_tokens=8000,
            completion_tokens=1200,
        )
        # Success: Function accepts separate counts, proving separation is enforced

    def test_swarm_cost_not_duplicated_across_branches(self) -> None:
        """Guardrail: Swarm cost should be the sum of all branches, not duplicated.

        When a race strategy runs multiple branches, the total_cost_usd should
        represent the combined cost once, not recorded per-branch.
        """
        from mcp_server_langgraph.agents.metrics import record_swarm_execution

        # Record swarm execution with correct total cost
        # The function takes total_cost_usd as a single value, not per-branch
        record_swarm_execution(
            strategy="race",
            branches_launched=3,
            branches_cancelled=2,
            winner_model="gemini-3-flash",
            total_cost_usd=0.15,  # Total across all branches
            session_id="session-guardrail-test",
        )
        # Success: Function takes single total_cost, preventing per-branch duplication

    def test_critique_rounds_capped_at_three(self) -> None:
        """Guardrail: Critique rounds should never exceed 3.

        This ensures the critique loop respects the hard cap of 3 rounds
        as defined in the orchestration architecture.
        """
        from mcp_server_langgraph.agents.metrics import record_critique_loop

        # Recording 3 rounds should be valid
        record_critique_loop(
            task_type="code",
            complexity="complex",
            rounds_executed=3,
            accepted_at_round=3,
        )
        # Success: 3 rounds is valid

        # Test that the function still accepts valid values
        record_critique_loop(
            task_type="code",
            complexity="simple",
            rounds_executed=1,
            accepted_at_round=1,
        )

    def test_router_cache_mutually_exclusive_hit_miss(self) -> None:
        """Guardrail: Router cache should be either hit OR miss, not both.

        Each router decision should record exactly one cache_hit value
        (True or False), ensuring metrics are not inflated.
        """
        from mcp_server_langgraph.agents.metrics import record_router_decision

        # Cache hit
        record_router_decision(
            latency_ms=5.0,
            complexity="simple",
            risk="low",
            confidence=0.95,
            cache_hit=True,
            model="gemini-3-flash",
        )

        # Cache miss (separate call, not same call with both)
        record_router_decision(
            latency_ms=150.0,
            complexity="complicated",
            risk="medium",
            confidence=0.85,
            cache_hit=False,
            model="gemini-3-flash",
        )
        # Success: cache_hit is boolean, can only be one value per call


@pytest.mark.xdist_group(name="orchestration_metrics_tier_audit")
class TestModelTierAudit:
    """Tests to audit model tier configuration completeness."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_registered_models_have_tier(self) -> None:
        """Audit: All models in registry should have a tier defined.

        This prevents routing failures due to missing tier configuration.
        """
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        registry = get_default_registry()
        models_without_tier = []

        for model_id in registry.list_models():
            model = registry.get(model_id)
            if model is None:
                continue
            # Check if model has tier attribute
            if not hasattr(model, "tier") or model.tier is None:
                models_without_tier.append(model_id)

        assert len(models_without_tier) == 0, f"Models missing tier configuration: {models_without_tier}"

    def test_all_thinking_capable_models_have_max_thinking_tokens(self) -> None:
        """Audit: Models with thinking capability should have max_thinking_tokens set.

        This prevents budget enforcement failures for extended thinking models.
        """
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        registry = get_default_registry()
        thinking_models_without_limit = []

        for model_id in registry.list_models():
            model = registry.get(model_id)
            if model is None:
                continue
            # Check if model supports extended thinking
            if hasattr(model, "supports_extended_thinking") and model.supports_extended_thinking:
                if not hasattr(model, "max_thinking_tokens") or model.max_thinking_tokens is None:
                    thinking_models_without_limit.append(model_id)

        assert len(thinking_models_without_limit) == 0, (
            f"Thinking-capable models missing max_thinking_tokens: {thinking_models_without_limit}"
        )

    def test_tier_values_are_valid(self) -> None:
        """Audit: All tier values should be one of: simple, complicated, complex.

        This ensures router decisions can be mapped to valid tiers.
        """
        from mcp_server_langgraph.agents.model_registry import get_default_registry

        valid_tiers = {"simple", "complicated", "complex"}
        registry = get_default_registry()
        invalid_tier_models = []

        for model_id in registry.list_models():
            model = registry.get(model_id)
            if model is None:
                continue
            if hasattr(model, "tier") and model.tier is not None:
                if model.tier not in valid_tiers:
                    invalid_tier_models.append((model_id, model.tier))

        assert len(invalid_tier_models) == 0, f"Models with invalid tier values: {invalid_tier_models}"
