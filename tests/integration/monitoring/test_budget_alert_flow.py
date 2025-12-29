"""
Integration Test for Full Budget Alert Flow.

Tests the complete flow:
1. LLM call with organizational context
2. Cost recorded via CostTrackingCallback
3. Budget threshold check triggered
4. WebSocket broadcast to subscribers

This validates the end-to-end integration of:
- LiteLLM CostTrackingCallback
- Budget storage and checking
- Real-time WebSocket alert broadcasting

Reference: Plan - Budget Alert Broadcasting Integration
"""

import gc
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.monitoring,
    pytest.mark.cost,
]


@pytest.fixture
def reset_singletons():
    """Reset all monitoring singletons before and after tests."""
    from mcp_server_langgraph.monitoring.budget_storage import _reset_budget_storage
    from mcp_server_langgraph.monitoring.cost_storage_factory import (
        reset_cost_storage_backend,
    )
    from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

    # Setup - use memory backend
    os.environ["COST_STORAGE_BACKEND"] = "memory"

    _reset_budget_storage()
    reset_cost_storage_backend()
    _reset_cost_collector()

    yield

    # Teardown
    _reset_budget_storage()
    reset_cost_storage_backend()
    _reset_cost_collector()

    if "COST_STORAGE_BACKEND" in os.environ:
        del os.environ["COST_STORAGE_BACKEND"]


@pytest.mark.xdist_group(name="test_budget_alert_flow")
class TestBudgetAlertFlowIntegration:
    """Integration tests for full budget alert flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cost_recording_triggers_budget_check(self, reset_singletons: Any) -> None:
        """
        GIVEN: A budget configured for an organization
        WHEN: Cost is recorded via CostTrackingCallback
        THEN: Budget check should be triggered automatically

        This tests the integration between:
        - CostTrackingCallback.async_log_success_event()
        - check_and_broadcast_budget_alert()
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Setup budget storage with a budget
        budget_storage = MemoryBudgetStorage()
        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.00,
        )
        await budget_storage.save_budget(org_budget)
        set_budget_storage(budget_storage)

        # Create mock LLM response
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 500

        kwargs: dict[str, Any] = {
            "response_cost": 0.05,  # $0.05
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "litellm_params": {
                "metadata": {
                    "user_id": "user:alice",
                    "session_id": "session-123",
                    "organization_id": "organization:acme",
                    "project_id": "project:backend",
                }
            },
        }

        callback = CostTrackingCallback()

        # Mock the cost collector to avoid actual storage
        with patch("mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            # Mock budget alert check to track calls
            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.check_and_broadcast_budget_alert",
                new_callable=AsyncMock,
            ) as mock_check:
                await callback.async_log_success_event(
                    kwargs=kwargs,
                    response_obj=mock_response,
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                )

                # Verify budget check was called with correct parameters
                mock_check.assert_called_once_with(
                    organization_id="organization:acme",
                    project_id="project:backend",
                    team_id=None,
                    user_id="user:alice",
                )

    @pytest.mark.asyncio
    async def test_budget_warning_triggers_broadcast(self, reset_singletons: Any) -> None:
        """
        GIVEN: A budget at 85% utilization (above warning threshold)
        WHEN: Budget check is performed
        THEN: Warning alert should be broadcast

        This tests the budget checking and broadcasting integration.
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        # Setup budget: $1000 limit, 80% warning threshold
        budget_storage = MemoryBudgetStorage()
        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.00,
        )
        await budget_storage.save_budget(org_budget)
        set_budget_storage(budget_storage)

        # Setup cost storage with existing spend of $850 (85%)
        cost_storage = MemoryCostStorage()
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=10000,
            completion_tokens=5000,
            estimated_cost_usd=Decimal("850.00"),
            organization_id="organization:acme",
        )
        await cost_storage.store(usage)
        set_cost_storage_backend(cost_storage)

        # Mock the broadcaster
        with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            # Trigger budget check
            results = await check_and_broadcast_budget_alert(
                organization_id="organization:acme",
            )

            # Verify warning was broadcast
            assert results is not None
            assert len(results) == 1
            assert results[0].status == "warning"
            mock_broadcaster.broadcast_budget_status.assert_called_once()

            # Verify broadcast payload
            broadcast_call = mock_broadcaster.broadcast_budget_status.call_args[0][0]
            assert broadcast_call.status == "warning"
            assert broadcast_call.budget.entity_id == "organization:acme"

    @pytest.mark.asyncio
    async def test_budget_critical_triggers_broadcast(self, reset_singletons: Any) -> None:
        """
        GIVEN: A budget at 100% utilization (at critical threshold)
        WHEN: Budget check is performed
        THEN: Critical alert should be broadcast
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        # Setup budget: $1000 limit
        budget_storage = MemoryBudgetStorage()
        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.00,
        )
        await budget_storage.save_budget(org_budget)
        set_budget_storage(budget_storage)

        # Setup cost storage with spend at exactly $1000 (100%)
        cost_storage = MemoryCostStorage()
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=10000,
            completion_tokens=5000,
            estimated_cost_usd=Decimal("1000.00"),
            organization_id="organization:acme",
        )
        await cost_storage.store(usage)
        set_cost_storage_backend(cost_storage)

        with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            results = await check_and_broadcast_budget_alert(
                organization_id="organization:acme",
            )

            assert results is not None
            assert len(results) == 1
            assert results[0].status == "critical"
            mock_broadcaster.broadcast_budget_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_entity_budget_check_flow(self, reset_singletons: Any) -> None:
        """
        GIVEN: Budgets for organization, project, and user
        WHEN: Cost is recorded with full org hierarchy
        THEN: All entity budgets should be checked

        This tests the hierarchical budget checking.
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        # Setup budgets for multiple entities
        budget_storage = MemoryBudgetStorage()

        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("10000.00"),
            warning_threshold=0.80,
        )
        project_budget = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("5000.00"),
            warning_threshold=0.80,
        )
        user_budget = Budget(
            entity_type="user",
            entity_id="user:alice",
            monthly_limit_usd=Decimal("500.00"),
            warning_threshold=0.80,
        )

        await budget_storage.save_budget(org_budget)
        await budget_storage.save_budget(project_budget)
        await budget_storage.save_budget(user_budget)
        set_budget_storage(budget_storage)

        # Setup cost storage with spend that triggers warning for user only
        cost_storage = MemoryCostStorage()

        # Org spend: $1000 (10% of $10000) - OK
        # Project spend: $500 (10% of $5000) - OK
        # User spend: $450 (90% of $500) - WARNING
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=10000,
            completion_tokens=5000,
            estimated_cost_usd=Decimal("450.00"),
            organization_id="organization:acme",
            project_id="project:backend",
        )
        await cost_storage.store(usage)
        set_cost_storage_backend(cost_storage)

        with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            results = await check_and_broadcast_budget_alert(
                organization_id="organization:acme",
                project_id="project:backend",
                user_id="user:alice",
            )

            # Should have checked 3 budgets
            assert results is not None
            assert len(results) == 3

            # Find the user budget result (should be warning)
            user_result = next((r for r in results if r.budget.entity_id == "user:alice"), None)
            assert user_result is not None
            assert user_result.status == "warning"

            # Org and project should be OK (not broadcast)
            org_result = next((r for r in results if r.budget.entity_id == "organization:acme"), None)
            assert org_result is not None
            assert org_result.status == "ok"

            # Only user budget should trigger broadcast (warning status)
            assert mock_broadcaster.broadcast_budget_status.call_count == 1

    @pytest.mark.asyncio
    async def test_no_broadcast_for_ok_status(self, reset_singletons: Any) -> None:
        """
        GIVEN: A budget at 50% utilization (below warning threshold)
        WHEN: Budget check is performed
        THEN: No alert should be broadcast (avoid noise)
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        # Setup budget: $1000 limit
        budget_storage = MemoryBudgetStorage()
        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
        )
        await budget_storage.save_budget(org_budget)
        set_budget_storage(budget_storage)

        # Setup cost storage with spend at $500 (50% - below warning)
        cost_storage = MemoryCostStorage()
        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
            prompt_tokens=5000,
            completion_tokens=2500,
            estimated_cost_usd=Decimal("500.00"),
            organization_id="organization:acme",
        )
        await cost_storage.store(usage)
        set_cost_storage_backend(cost_storage)

        with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
            mock_broadcaster = MagicMock()
            mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
            mock_get_broadcaster.return_value = mock_broadcaster

            results = await check_and_broadcast_budget_alert(
                organization_id="organization:acme",
            )

            assert results is not None
            assert len(results) == 1
            assert results[0].status == "ok"

            # No broadcast for OK status
            mock_broadcaster.broadcast_budget_status.assert_not_called()


@pytest.mark.xdist_group(name="test_budget_alert_flow_entity_specific")
class TestEntitySpecificSpendCalculation:
    """Integration tests for entity-specific spend calculation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_organization_spend_calculation_uses_org_filter(self, reset_singletons: Any) -> None:
        """
        GIVEN: Cost records for multiple organizations
        WHEN: Calculating spend for a specific organization
        THEN: Should only include that organization's costs
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_current_spend_for_entity,
        )

        cost_storage = MemoryCostStorage()

        # Acme spend: $100
        acme_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("100.00"),
            organization_id="organization:acme",
        )
        await cost_storage.store(acme_usage)

        # Globex spend: $200
        globex_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:bob",
            session_id="session-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=2000,
            completion_tokens=1000,
            estimated_cost_usd=Decimal("200.00"),
            organization_id="organization:globex",
        )
        await cost_storage.store(globex_usage)

        set_cost_storage_backend(cost_storage)

        # Get spend for Acme only
        acme_spend = await get_current_spend_for_entity("organization", "organization:acme")

        assert acme_spend == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_project_spend_calculation_uses_project_filter(self, reset_singletons: Any) -> None:
        """
        GIVEN: Cost records for multiple projects
        WHEN: Calculating spend for a specific project
        THEN: Should only include that project's costs
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_current_spend_for_entity,
        )

        cost_storage = MemoryCostStorage()

        # Backend project: $150
        backend_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=1500,
            completion_tokens=750,
            estimated_cost_usd=Decimal("150.00"),
            project_id="project:backend",
        )
        await cost_storage.store(backend_usage)

        # Frontend project: $75
        frontend_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:bob",
            session_id="session-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=750,
            completion_tokens=375,
            estimated_cost_usd=Decimal("75.00"),
            project_id="project:frontend",
        )
        await cost_storage.store(frontend_usage)

        set_cost_storage_backend(cost_storage)

        # Get spend for backend only
        backend_spend = await get_current_spend_for_entity("project", "project:backend")

        assert backend_spend == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_team_spend_calculation_uses_team_filter(self, reset_singletons: Any) -> None:
        """
        GIVEN: Cost records for multiple teams
        WHEN: Calculating spend for a specific team
        THEN: Should only include that team's costs
        """
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            set_cost_storage_backend,
        )
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            get_current_spend_for_entity,
        )

        cost_storage = MemoryCostStorage()

        # Platform team: $250
        platform_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="session-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=2500,
            completion_tokens=1250,
            estimated_cost_usd=Decimal("250.00"),
            team_id="team:platform",
        )
        await cost_storage.store(platform_usage)

        # ML team: $500
        ml_usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:bob",
            session_id="session-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=5000,
            completion_tokens=2500,
            estimated_cost_usd=Decimal("500.00"),
            team_id="team:ml",
        )
        await cost_storage.store(ml_usage)

        set_cost_storage_backend(cost_storage)

        # Get spend for platform team only
        platform_spend = await get_current_spend_for_entity("team", "team:platform")

        assert platform_spend == Decimal("250.00")
