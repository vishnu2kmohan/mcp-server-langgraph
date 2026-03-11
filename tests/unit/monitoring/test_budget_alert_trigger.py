"""
Budget Alert Trigger Integration Tests

TDD tests for automatic budget alert broadcasting when cost thresholds are crossed.
Tests written FIRST (RED phase).

The integration should:
1. Check budget status after each cost is recorded
2. Broadcast alert to WebSocket subscribers when status changes
3. Only broadcast on status transitions (ok→warning, warning→critical, etc.)
"""

import gc
from datetime import UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.monitoring]


class TestBudgetAlertTriggerFunction:
    """Tests for the budget alert trigger function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_and_broadcast_budget_alert_exists(self) -> None:
        """
        GIVEN the litellm_cost_callback module
        WHEN importing check_and_broadcast_budget_alert
        THEN it should be available.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        assert check_and_broadcast_budget_alert is not None
        assert callable(check_and_broadcast_budget_alert)

    @pytest.mark.asyncio
    async def test_trigger_does_nothing_when_no_entity_ids(self) -> None:
        """
        GIVEN no organizational context (no org_id, project_id, team_id)
        WHEN check_and_broadcast_budget_alert is called
        THEN it should return without checking budgets.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )

        # No entity IDs - should return early
        result = await check_and_broadcast_budget_alert(
            organization_id=None,
            project_id=None,
            team_id=None,
            user_id=None,
        )

        # Should return None or empty when no entities to check
        assert result is None or result == []

    @pytest.mark.asyncio
    async def test_trigger_checks_organization_budget(self) -> None:
        """
        GIVEN an organization_id in the metadata
        WHEN check_and_broadcast_budget_alert is called
        THEN it should check the organization's budget.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
            _reset_budget_storage,
        )

        # Setup: Create a budget
        storage = MemoryBudgetStorage()
        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )
        await storage.save_budget(budget)
        set_budget_storage(storage)

        try:
            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.get_current_spend_for_entity",
                new_callable=AsyncMock,
                side_effect=lambda *a, **kw: Decimal("850.00"),
            ):
                with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
                    mock_broadcaster = MagicMock()
                    mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
                    mock_get_broadcaster.return_value = mock_broadcaster

                    result = await check_and_broadcast_budget_alert(
                        organization_id="organization:acme",
                        project_id=None,
                        team_id=None,
                        user_id=None,
                    )

                    # Should have checked the organization budget
                    assert result is not None
        finally:
            _reset_budget_storage()


class TestBudgetAlertTriggerBroadcast:
    """Tests for broadcasting when thresholds are crossed."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcasts_when_warning_threshold_crossed(self) -> None:
        """
        GIVEN spend crosses warning threshold (80%)
        WHEN check_and_broadcast_budget_alert is called
        THEN it should broadcast a warning alert.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
            _reset_budget_storage,
        )

        storage = MemoryBudgetStorage()
        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.00,
        )
        await storage.save_budget(budget)
        set_budget_storage(storage)

        try:
            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.get_current_spend_for_entity",
                new_callable=AsyncMock,
                side_effect=lambda *a, **kw: Decimal("850.00"),  # 85% - above warning
            ):
                with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
                    mock_broadcaster = MagicMock()
                    mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
                    mock_get_broadcaster.return_value = mock_broadcaster

                    await check_and_broadcast_budget_alert(
                        organization_id="organization:acme",
                        project_id=None,
                        team_id=None,
                        user_id=None,
                    )

                    # Should broadcast warning status
                    mock_broadcaster.broadcast_budget_status.assert_called_once()
                    call_args = mock_broadcaster.broadcast_budget_status.call_args[0][0]
                    assert call_args.status == "warning"
        finally:
            _reset_budget_storage()

    @pytest.mark.asyncio
    async def test_broadcasts_when_critical_threshold_crossed(self) -> None:
        """
        GIVEN spend crosses critical threshold (100%)
        WHEN check_and_broadcast_budget_alert is called
        THEN it should broadcast a critical alert.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
            _reset_budget_storage,
        )

        storage = MemoryBudgetStorage()
        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.00,
        )
        await storage.save_budget(budget)
        set_budget_storage(storage)

        try:
            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.get_current_spend_for_entity",
                new_callable=AsyncMock,
                side_effect=lambda *a, **kw: Decimal("1000.00"),  # 100% - at critical
            ):
                with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
                    mock_broadcaster = MagicMock()
                    mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
                    mock_get_broadcaster.return_value = mock_broadcaster

                    await check_and_broadcast_budget_alert(
                        organization_id="organization:acme",
                        project_id=None,
                        team_id=None,
                        user_id=None,
                    )

                    # Should broadcast critical status
                    mock_broadcaster.broadcast_budget_status.assert_called_once()
                    call_args = mock_broadcaster.broadcast_budget_status.call_args[0][0]
                    assert call_args.status == "critical"
        finally:
            _reset_budget_storage()

    @pytest.mark.asyncio
    async def test_does_not_broadcast_when_ok_status(self) -> None:
        """
        GIVEN spend is below warning threshold
        WHEN check_and_broadcast_budget_alert is called
        THEN it should NOT broadcast (to avoid noise).
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
            _reset_budget_storage,
        )

        storage = MemoryBudgetStorage()
        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
        )
        await storage.save_budget(budget)
        set_budget_storage(storage)

        try:
            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.get_current_spend_for_entity",
                new_callable=AsyncMock,
                side_effect=lambda *a, **kw: Decimal("500.00"),  # 50% - below warning
            ):
                with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
                    mock_broadcaster = MagicMock()
                    mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
                    mock_get_broadcaster.return_value = mock_broadcaster

                    await check_and_broadcast_budget_alert(
                        organization_id="organization:acme",
                        project_id=None,
                        team_id=None,
                        user_id=None,
                    )

                    # Should NOT broadcast for ok status
                    mock_broadcaster.broadcast_budget_status.assert_not_called()
        finally:
            _reset_budget_storage()


class TestBudgetAlertTriggerMultiEntity:
    """Tests for checking multiple entity budgets."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_checks_all_provided_entity_budgets(self) -> None:
        """
        GIVEN org_id, project_id, and user_id
        WHEN check_and_broadcast_budget_alert is called
        THEN it should check all entity budgets.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            check_and_broadcast_budget_alert,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            set_budget_storage,
            _reset_budget_storage,
        )

        storage = MemoryBudgetStorage()

        # Create budgets for multiple entities
        org_budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("10000.00"),
        )
        project_budget = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("5000.00"),
        )
        user_budget = Budget(
            entity_type="user",
            entity_id="user:alice",
            monthly_limit_usd=Decimal("500.00"),
        )
        await storage.save_budget(org_budget)
        await storage.save_budget(project_budget)
        await storage.save_budget(user_budget)
        set_budget_storage(storage)

        try:
            # All entities in warning state
            async def mock_spend(entity_type: str, entity_id: str) -> Decimal:
                spend_map = {
                    "organization:acme": Decimal("8500.00"),  # 85%
                    "project:backend": Decimal("4250.00"),  # 85%
                    "user:alice": Decimal("425.00"),  # 85%
                }
                return spend_map.get(entity_id, Decimal("0"))

            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.get_current_spend_for_entity",
                new_callable=AsyncMock,
                side_effect=mock_spend,
            ):
                with patch("mcp_server_langgraph.monitoring.cost_budget.get_budget_alert_broadcaster") as mock_get_broadcaster:
                    mock_broadcaster = MagicMock()
                    mock_broadcaster.broadcast_budget_status = AsyncMock(return_value=None)
                    mock_get_broadcaster.return_value = mock_broadcaster

                    await check_and_broadcast_budget_alert(
                        organization_id="organization:acme",
                        project_id="project:backend",
                        team_id=None,
                        user_id="user:alice",
                    )

                    # Should broadcast for all 3 entities in warning
                    assert mock_broadcaster.broadcast_budget_status.call_count == 3
        finally:
            _reset_budget_storage()


class TestBudgetAlertCallbackIntegration:
    """Tests for integration with CostTrackingCallback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_callback_calls_budget_check_after_recording(self) -> None:
        """
        GIVEN CostTrackingCallback with budget check enabled
        WHEN async_log_success_event is called
        THEN it should check budgets after recording cost.
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        callback = CostTrackingCallback()

        # Mock response object with usage
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        kwargs = {
            "response_cost": 0.01,
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

        with patch("mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            with patch(
                "mcp_server_langgraph.monitoring.litellm_cost_callback.check_and_broadcast_budget_alert",
                new_callable=AsyncMock,
            ) as mock_check:
                from datetime import datetime

                await callback.async_log_success_event(
                    kwargs=kwargs,
                    response_obj=mock_response,
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                )

                # Should call budget check with entity IDs from metadata
                mock_check.assert_called_once_with(
                    organization_id="organization:acme",
                    project_id="project:backend",
                    team_id=None,
                    user_id="user:alice",
                )
