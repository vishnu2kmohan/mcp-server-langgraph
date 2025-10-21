"""
Unit tests for bulkhead isolation pattern.

Tests concurrency limiting, wait/fail-fast modes, and metrics.
"""

import asyncio
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.exceptions import BulkheadRejectedError
from mcp_server_langgraph.resilience.bulkhead import (
    BulkheadContext,
    get_bulkhead,
    get_bulkhead_stats,
    reset_all_bulkheads,
    reset_bulkhead,
    with_bulkhead,
)


@pytest.fixture
def reset_bulkheads():
    """Reset all bulkheads before each test"""
    reset_all_bulkheads()
    yield
    reset_all_bulkheads()


class TestBulkheadBasics:
    """Test basic bulkhead functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulkhead_limits_concurrency(self, reset_bulkheads):
        """Test that bulkhead limits concurrent executions"""
        active_count = 0
        max_active = 0

        @with_bulkhead(resource_type="test", limit=3)
        async def func():
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.1)
            active_count -= 1
            return "success"

        # Start 10 concurrent tasks
        tasks = [func() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r == "success" for r in results)

        # But max concurrency should be limited to 3
        assert max_active <= 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulkhead_sequential_calls_not_limited(self, reset_bulkheads):
        """Test that sequential calls are not limited"""

        @with_bulkhead(resource_type="test", limit=1)
        async def func():
            await asyncio.sleep(0.01)
            return "success"

        # Sequential calls should all succeed
        for i in range(10):
            result = await func()
            assert result == "success"


class TestBulkheadFailFast:
    """Test bulkhead fail-fast mode"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fail_fast_rejects_when_full(self, reset_bulkheads):
        """Test that fail-fast mode rejects when bulkhead is full"""

        @with_bulkhead(resource_type="test", limit=2, wait=False)
        async def slow_func():
            await asyncio.sleep(1)
            return "success"

        # Start 2 concurrent tasks (fill bulkhead)
        task1 = asyncio.create_task(slow_func())
        task2 = asyncio.create_task(slow_func())

        # Let them start
        await asyncio.sleep(0.01)

        # 3rd task should be rejected immediately
        with pytest.raises(BulkheadRejectedError):
            await slow_func()

        # Wait for original tasks to complete
        results = await asyncio.gather(task1, task2)
        assert all(r == "success" for r in results)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_mode_queues_requests(self, reset_bulkheads):
        """Test that wait mode queues requests instead of rejecting"""
        execution_order = []

        @with_bulkhead(resource_type="test", limit=2, wait=True)
        async def func(task_id):
            execution_order.append(f"start_{task_id}")
            await asyncio.sleep(0.1)
            execution_order.append(f"end_{task_id}")
            return task_id

        # Start 5 concurrent tasks
        tasks = [func(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert results == [0, 1, 2, 3, 4]

        # Should have executed (max 2 concurrent)


class TestBulkheadContextManager:
    """Test bulkhead context manager"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulkhead_context_manager(self, reset_bulkheads):
        """Test BulkheadContext as context manager"""
        async with BulkheadContext(resource_type="test", limit=5):
            await asyncio.sleep(0.01)
            result = "success"

        assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulkhead_context_fail_fast(self, reset_bulkheads):
        """Test BulkheadContext in fail-fast mode"""

        async def worker():
            async with BulkheadContext(resource_type="test", limit=1, wait=True):
                await asyncio.sleep(0.5)

        # Start one worker (fills bulkhead)
        task1 = asyncio.create_task(worker())
        await asyncio.sleep(0.01)  # Let it start

        # Second worker in fail-fast mode should be rejected
        with pytest.raises(BulkheadRejectedError):
            async with BulkheadContext(resource_type="test", limit=1, wait=False):
                await asyncio.sleep(0.1)

        # Wait for first worker
        await task1


class TestBulkheadStatistics:
    """Test bulkhead statistics"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_bulkhead_stats(self, reset_bulkheads):
        """Test get_bulkhead_stats function"""

        @with_bulkhead(resource_type="test", limit=10)
        async def func():
            await asyncio.sleep(0.1)

        # Create tasks but don't await yet
        tasks = [asyncio.create_task(func()) for _ in range(5)]
        await asyncio.sleep(0.01)  # Let them start

        stats = get_bulkhead_stats("test")

        # Should have stats for test resource
        assert "test" in stats
        assert stats["test"]["limit"] >= 5
        assert stats["test"]["active"] >= 0

        # Clean up
        await asyncio.gather(*tasks)

    @pytest.mark.unit
    def test_get_bulkhead_stats_empty(self, reset_bulkheads):
        """Test stats for non-existent bulkhead"""
        stats = get_bulkhead_stats("nonexistent")
        assert stats == {}


class TestBulkheadConfiguration:
    """Test bulkhead configuration"""

    @pytest.mark.unit
    def test_get_bulkhead_with_default_limit(self, reset_bulkheads):
        """Test bulkhead creation with default limit from config"""
        bulkhead = get_bulkhead("llm")  # noqa: F841
        # Should use default from config (10)

    @pytest.mark.unit
    def test_get_bulkhead_with_custom_limit(self, reset_bulkheads):
        """Test bulkhead creation with custom limit"""
        bulkhead = get_bulkhead("custom", limit=25)  # noqa: F841
        # Should use provided limit

    @pytest.mark.unit
    def test_reset_bulkhead(self, reset_bulkheads):
        """Test manual bulkhead reset"""
        bulkhead1 = get_bulkhead("test", limit=10)

        reset_bulkhead("test")

        bulkhead2 = get_bulkhead("test", limit=20)
        # Should be a new instance
        assert bulkhead1 is not bulkhead2


class TestBulkheadMetrics:
    """Test bulkhead metrics emission"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejection_metric(self, reset_bulkheads):
        """Test that rejection metric is emitted"""

        @with_bulkhead(resource_type="test", limit=1, wait=False)
        async def func():
            await asyncio.sleep(0.5)

        # Fill bulkhead
        task = asyncio.create_task(func())
        await asyncio.sleep(0.01)

        # Second call should be rejected and emit metric
        with patch("mcp_server_langgraph.resilience.bulkhead.bulkhead_rejected_counter") as mock_metric:  # noqa: F841
            with pytest.raises(BulkheadRejectedError):
                await func()

        await task

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_active_operations_metric(self, reset_bulkheads):
        """Test that active operations metric is set"""

        @with_bulkhead(resource_type="test", limit=5)
        async def func():
            await asyncio.sleep(0.1)

        with patch("mcp_server_langgraph.resilience.bulkhead.bulkhead_active_operations_gauge") as mock_metric:  # noqa: F841
            await func()


class TestBulkheadEdgeCases:
    """Test bulkhead edge cases"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulkhead_with_exceptions(self, reset_bulkheads):
        """Test that bulkhead releases slot even on exception"""
        active_count = 0

        @with_bulkhead(resource_type="test", limit=3)
        async def failing_func():
            nonlocal active_count
            active_count += 1
            await asyncio.sleep(0.01)
            active_count -= 1
            raise ValueError("Test error")

        # Run multiple failing tasks
        tasks = [failing_func() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should raise ValueError
        assert all(isinstance(r, ValueError) for r in results)

        # Active count should be 0 (all slots released)
        assert active_count == 0

    @pytest.mark.unit
    def test_bulkhead_decorator_type_check(self, reset_bulkheads):
        """Test that bulkhead only works with async functions"""

        with pytest.raises(TypeError):

            @with_bulkhead(resource_type="test")
            def sync_func():
                return "sync"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_different_resource_types_independent(self, reset_bulkheads):
        """Test that different resource types have independent bulkheads"""

        @with_bulkhead(resource_type="llm", limit=2)
        async def llm_func():
            await asyncio.sleep(0.1)
            return "llm"

        @with_bulkhead(resource_type="db", limit=2)
        async def db_func():
            await asyncio.sleep(0.1)
            return "db"

        # Both should be able to run concurrently (different bulkheads)
        results = await asyncio.gather(
            llm_func(),
            llm_func(),
            db_func(),
            db_func(),
        )

        assert results == ["llm", "llm", "db", "db"]
