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
        remaining, _ = await storage.get_records()
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
        remaining, _ = await storage.get_records()
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
        remaining, _ = await storage.get_records()
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
        remaining, _ = await storage.get_records()
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


# ==============================================================================
# Performance Tests for Cost Retention Cleanup
# ==============================================================================


@pytest.mark.xdist_group(name="test_cost_retention_performance")
class TestCostRetentionPerformance:
    """Performance tests for CostRetentionPolicy cleanup operations.

    These tests validate that cleanup operations complete within acceptable
    time bounds for various record counts. Tests are skipped in pytest-xdist
    parallel mode to avoid memory overhead.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cleanup_1000_records_completes_under_1_second(self):
        """
        GIVEN storage with 1000 old records
        WHEN cleanup is executed
        THEN it should complete in under 1 second
        """
        import time
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange - create storage with 1000 old records
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        for i in range(1000):
            usage = TokenUsage(
                timestamp=now - timedelta(days=100 + (i % 30)),
                user_id=f"user:perf_test_{i}",
                session_id=f"session-perf-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        assert storage.total_records == 1000

        policy = CostRetentionPolicy(retention_days=90)

        # Act - measure cleanup time
        start_time = time.perf_counter()
        deleted = await policy.cleanup(storage)
        elapsed_time = time.perf_counter() - start_time

        # Assert - should complete quickly and delete all records
        assert deleted == 1000
        assert elapsed_time < 1.0, f"Cleanup took {elapsed_time:.2f}s, expected < 1.0s"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cleanup_mixed_records_maintains_correct_count(self):
        """
        GIVEN storage with mix of old and new records
        WHEN cleanup is executed
        THEN correct number of records should be deleted and retained
        """
        import time
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange - 500 old records, 500 new records
        storage = MemoryCostStorage()
        now = datetime.now(UTC)

        # Add old records (to be deleted)
        for i in range(500):
            usage = TokenUsage(
                timestamp=now - timedelta(days=100 + (i % 30)),
                user_id=f"user:old_{i}",
                session_id=f"session-old-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        # Add new records (to be kept)
        for i in range(500):
            usage = TokenUsage(
                timestamp=now - timedelta(days=i % 30),
                user_id=f"user:new_{i}",
                session_id=f"session-new-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost_usd=Decimal("0.01"),
            )
            await storage.store(usage)

        assert storage.total_records == 1000

        policy = CostRetentionPolicy(retention_days=90)

        # Act
        start_time = time.perf_counter()
        deleted = await policy.cleanup(storage)
        elapsed_time = time.perf_counter() - start_time

        # Assert
        assert deleted == 500
        assert storage.total_records == 500
        assert elapsed_time < 1.0, f"Cleanup took {elapsed_time:.2f}s, expected < 1.0s"

        # Verify remaining records are all new
        remaining, _ = await storage.get_records()
        for record in remaining:
            assert "new" in record.session_id

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cleanup_empty_storage_is_fast(self):
        """
        GIVEN empty storage
        WHEN cleanup is executed
        THEN it should complete almost instantaneously
        """
        import time
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        policy = CostRetentionPolicy(retention_days=90)

        # Act
        start_time = time.perf_counter()
        deleted = await policy.cleanup(storage)
        elapsed_time = time.perf_counter() - start_time

        # Assert - should be nearly instantaneous
        assert deleted == 0
        assert elapsed_time < 0.1, f"Empty cleanup took {elapsed_time:.4f}s, expected < 0.1s"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_multiple_cleanup_cycles_are_consistent(self):
        """
        GIVEN storage with records that span multiple retention periods
        WHEN multiple cleanup cycles are executed
        THEN each cycle should maintain consistent performance
        """
        import time
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        # Arrange
        storage = MemoryCostStorage()
        now = datetime.now(UTC)
        policy = CostRetentionPolicy(retention_days=30)

        cycle_times = []

        # Run 3 cleanup cycles, adding records before each
        for cycle in range(3):
            # Add 200 old records for this cycle
            for i in range(200):
                usage = TokenUsage(
                    timestamp=now - timedelta(days=40 + (i % 10)),
                    user_id=f"user:cycle_{cycle}_{i}",
                    session_id=f"session-cycle-{cycle}-{i}",
                    model="gpt-4",
                    provider="openai",
                    prompt_tokens=100,
                    completion_tokens=50,
                    estimated_cost_usd=Decimal("0.01"),
                )
                await storage.store(usage)

            # Run cleanup
            start_time = time.perf_counter()
            deleted = await policy.cleanup(storage)
            elapsed_time = time.perf_counter() - start_time

            cycle_times.append(elapsed_time)
            assert deleted == 200, f"Cycle {cycle}: Expected 200 deleted, got {deleted}"

        # Assert - all cycles should complete quickly
        for i, cycle_time in enumerate(cycle_times):
            assert cycle_time < 0.5, f"Cycle {i} took {cycle_time:.4f}s, expected < 0.5s"

        # Cycle times should be roughly consistent (no memory leaks)
        if len(cycle_times) > 1:
            max_ratio = max(cycle_times) / min(cycle_times)
            assert max_ratio < 3.0, f"Cycle time ratio {max_ratio:.2f} too high, possible performance degradation"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cleanup_scales_linearly_with_record_count(self):
        """
        GIVEN storage with increasing record counts
        WHEN cleanup is executed for each size
        THEN cleanup time should scale roughly linearly
        """
        import time
        from mcp_server_langgraph.monitoring.cost_retention import CostRetentionPolicy
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        results = []

        for count in [100, 500, 1000]:
            # Fresh storage for each test
            storage = MemoryCostStorage()
            now = datetime.now(UTC)

            # Add old records
            for i in range(count):
                usage = TokenUsage(
                    timestamp=now - timedelta(days=100),
                    user_id=f"user:scale_{i}",
                    session_id=f"session-scale-{i}",
                    model="gpt-4",
                    provider="openai",
                    prompt_tokens=100,
                    completion_tokens=50,
                    estimated_cost_usd=Decimal("0.01"),
                )
                await storage.store(usage)

            policy = CostRetentionPolicy(retention_days=90)

            # Measure cleanup time
            start_time = time.perf_counter()
            deleted = await policy.cleanup(storage)
            elapsed_time = time.perf_counter() - start_time

            assert deleted == count
            results.append({"count": count, "time": elapsed_time})

        # Assert - time should scale roughly linearly (not exponentially)
        # Allow 5x increase from 100 to 1000 records (would be ~10x for quadratic)
        time_100 = results[0]["time"]
        time_1000 = results[2]["time"]

        if time_100 > 0.0001:  # Avoid division by tiny numbers
            ratio = time_1000 / time_100
            # Should scale at most 15x (linear with some overhead)
            assert ratio < 15, f"Cleanup scaled {ratio:.1f}x from 100 to 1000 records, expected < 15x"
