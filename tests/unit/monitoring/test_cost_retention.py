"""
Unit tests for CostRetentionPolicy extracted from CostMetricsCollector.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.2 SRP decomposition - Testing retention logic separately
from storage and cost collection.

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

import gc
from datetime import datetime, timedelta, UTC
from decimal import Decimal

import pytest

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.monitoring,
]


@pytest.mark.xdist_group(name="test_cost_retention")
class TestCostRetentionPolicy:
    """Test CostRetentionPolicy for cleanup operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_records(self):
        """
        GIVEN: Storage backend with old records and CostRetentionPolicy
        WHEN: Running cleanup with 90-day retention
        THEN: Should delete records older than 90 days
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add old record (100 days old)
        old_usage = TokenUsage(
            timestamp=now - timedelta(days=100),
            user_id="user:alice",
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(old_usage)

        # Add new record (10 days old)
        new_usage = TokenUsage(
            timestamp=now - timedelta(days=10),
            user_id="user:bob",
            session_id="session-new",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(new_usage)

        policy = CostRetentionPolicy(retention_days=90)

        # Act
        deleted = await policy.cleanup(storage)

        # Assert
        assert deleted == 1
        remaining = await storage.get_records()
        assert len(remaining) == 1

    @pytest.mark.asyncio
    async def test_cleanup_with_custom_retention_days(self):
        """
        GIVEN: Storage backend with records and custom retention period
        WHEN: Running cleanup with 30-day retention
        THEN: Should delete records older than 30 days
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add record 40 days old (should be deleted with 30-day retention)
        usage_40d = TokenUsage(
            timestamp=now - timedelta(days=40),
            user_id="user:alice",
            session_id="session-40d",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(usage_40d)

        # Add record 20 days old (should be kept)
        usage_20d = TokenUsage(
            timestamp=now - timedelta(days=20),
            user_id="user:bob",
            session_id="session-20d",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(usage_20d)

        policy = CostRetentionPolicy(retention_days=30)

        # Act
        deleted = await policy.cleanup(storage)

        # Assert
        assert deleted == 1
        remaining = await storage.get_records()
        assert len(remaining) == 1
        assert remaining[0].session_id == "session-20d"

    @pytest.mark.asyncio
    async def test_cleanup_no_old_records(self):
        """
        GIVEN: Storage backend with only new records
        WHEN: Running cleanup
        THEN: Should not delete any records
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add only new records
        for i in range(3):
            usage = TokenUsage(
                timestamp=now - timedelta(days=i),
                user_id=f"user:{i}",
                session_id=f"session-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        policy = CostRetentionPolicy(retention_days=90)

        # Act
        deleted = await policy.cleanup(storage)

        # Assert
        assert deleted == 0
        remaining = await storage.get_records()
        assert len(remaining) == 3

    @pytest.mark.asyncio
    async def test_cleanup_empty_storage(self):
        """
        GIVEN: Empty storage backend
        WHEN: Running cleanup
        THEN: Should return 0 deleted records
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        policy = CostRetentionPolicy(retention_days=90)

        # Act
        deleted = await policy.cleanup(storage)

        # Assert
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_default_retention_is_90_days(self):
        """
        GIVEN: CostRetentionPolicy with default settings
        WHEN: Checking retention_days property
        THEN: Should default to 90 days
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy

        # Arrange & Act
        policy = CostRetentionPolicy()

        # Assert
        assert policy.retention_days == 90

    @pytest.mark.asyncio
    async def test_cleanup_calculates_correct_cutoff(self):
        """
        GIVEN: Storage with records at exactly the retention boundary
        WHEN: Running cleanup
        THEN: Should use correct cutoff calculation
        """
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add record exactly at boundary (should be deleted - >= comparison)
        boundary_usage = TokenUsage(
            timestamp=now - timedelta(days=90, seconds=1),  # Just over 90 days
            user_id="user:boundary",
            session_id="session-boundary",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(boundary_usage)

        # Add record just within boundary (should be kept)
        within_usage = TokenUsage(
            timestamp=now - timedelta(days=89, hours=23),
            user_id="user:within",
            session_id="session-within",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(within_usage)

        policy = CostRetentionPolicy(retention_days=90)

        # Act
        deleted = await policy.cleanup(storage)

        # Assert
        assert deleted == 1
        remaining = await storage.get_records()
        assert len(remaining) == 1
        assert remaining[0].session_id == "session-within"


@pytest.mark.xdist_group(name="test_cost_retention")
class TestCostRetentionPolicyLogging:
    """Test CostRetentionPolicy logging behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_logs_result(self):
        """
        GIVEN: CostRetentionPolicy with logger
        WHEN: Running cleanup that deletes records
        THEN: Should log the cleanup result
        """
        from unittest.mock import patch

        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add old record
        old_usage = TokenUsage(
            timestamp=now - timedelta(days=100),
            user_id="user:alice",
            session_id="session-old",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.01"),
        )
        await storage.store(old_usage)

        policy = CostRetentionPolicy(retention_days=90)

        # Act
        with patch("mcp_server_langgraph.monitoring.cost_retention.logger") as mock_logger:
            await policy.cleanup(storage)

            # Assert - should log cleanup info
            mock_logger.info.assert_called()
