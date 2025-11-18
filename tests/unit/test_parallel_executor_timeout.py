"""TDD tests for ParallelExecutor timeout functionality.

These tests verify that the parallel executor can handle timeouts gracefully
without blocking other tool executions.

CODEX FINDING #2: Optimized to use short sleeps (0.05-0.3s instead of 5-10s)
for fast test execution while maintaining timeout behavior validation.
"""

import asyncio
import gc

import pytest

from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testparallelexecutortimeouts")
class TestParallelExecutorTimeouts:
    """Test suite for parallel executor timeout handling (TDD RED → GREEN)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_executor_respects_per_task_timeout(self):
        """
        Test that parallel executor respects per-task timeout configuration.

        CODEX FINDING #2: Optimized to use short sleeps for fast test execution.
        """
        # GIVEN: Executor with 0.05-second timeout
        executor = ParallelToolExecutor(max_parallelism=3, task_timeout_seconds=0.05)

        # Mock tool that hangs for 0.2 seconds (exceeds timeout)
        async def slow_tool(name: str, args: dict):
            await asyncio.sleep(0.2)
            return "should not reach here"

        invocations = [ToolInvocation(tool_name="slow", arguments={}, invocation_id="inv1")]

        # WHEN: Execute with timeout
        results = await executor.execute_parallel(invocations, slow_tool)

        # THEN: Should timeout and return error result (not hang)
        assert len(results) == 1
        assert results[0].error is not None
        assert "timeout" in str(results[0].error).lower() or isinstance(results[0].error, asyncio.TimeoutError)

    async def test_hung_tool_doesnt_block_other_tools(self):
        """
        Test that a hung tool doesn't block execution of other independent tools.

        CODEX FINDING #2: Optimized to use short sleeps for fast test execution.
        """
        # GIVEN: Executor with 0.05-second timeout
        executor = ParallelToolExecutor(max_parallelism=3, task_timeout_seconds=0.05)

        # Mock tools: one hangs, two are fast
        async def slow_tool(name: str, args: dict):
            if name == "hung":
                await asyncio.sleep(0.3)  # Hangs for 0.3 seconds (exceeds 0.05s timeout)
                return "should timeout"
            return f"result_{name}"

        invocations = [
            ToolInvocation(tool_name="hung", arguments={}, invocation_id="inv1"),
            ToolInvocation(tool_name="fast1", arguments={}, invocation_id="inv2"),
            ToolInvocation(tool_name="fast2", arguments={}, invocation_id="inv3"),
        ]

        # WHEN: Execute all three tools
        import time

        start = time.time()
        results = await executor.execute_parallel(invocations, slow_tool)
        duration = time.time() - start

        # THEN:
        # - Should complete in ~0.05 second (timeout), not 0.3 seconds (hang)
        assert duration < 0.5, f"Took {duration}s, should timeout at ~0.05s"

        # - Hung tool should have timeout error
        hung_result = next(r for r in results if r.invocation_id == "inv1")
        assert hung_result.error is not None

        # - Fast tools should succeed
        fast1_result = next(r for r in results if r.invocation_id == "inv2")
        assert fast1_result.result == "result_fast1"
        assert fast1_result.error is None

        fast2_result = next(r for r in results if r.invocation_id == "inv3")
        assert fast2_result.result == "result_fast2"
        assert fast2_result.error is None

    async def test_timeout_none_means_no_timeout(self):
        """
        Test that timeout=None disables timeout (backward compatibility).

        CODEX FINDING #2: Optimized to use short sleeps for fast test execution.
        """
        # GIVEN: Executor with no timeout
        executor = ParallelToolExecutor(max_parallelism=2, task_timeout_seconds=None)

        # Mock tool that takes 0.05 seconds
        async def normal_tool(name: str, args: dict):
            await asyncio.sleep(0.05)
            return "completed"

        invocations = [ToolInvocation(tool_name="normal", arguments={}, invocation_id="inv1")]

        # WHEN: Execute without timeout
        results = await executor.execute_parallel(invocations, normal_tool)

        # THEN: Should complete successfully (no timeout)
        assert len(results) == 1
        assert results[0].result == "completed"
        assert results[0].error is None

    async def test_timeout_value_in_tool_result(self):
        """
        Test that timeout errors are properly recorded in ToolResult.

        CODEX FINDING #2: Optimized to use short sleeps for fast test execution.
        """
        # GIVEN: Executor with very short timeout
        executor = ParallelToolExecutor(max_parallelism=1, task_timeout_seconds=0.02)

        # Mock tool that exceeds timeout
        async def slow_tool(name: str, args: dict):
            await asyncio.sleep(0.1)
            return "too slow"

        invocations = [ToolInvocation(tool_name="slow", arguments={}, invocation_id="inv1")]

        # WHEN: Execute with timeout
        results = await executor.execute_parallel(invocations, slow_tool)

        # THEN: Result should contain timeout error
        assert len(results) == 1
        result = results[0]
        assert result.invocation_id == "inv1"
        assert result.tool_name == "slow"
        assert result.error is not None
        assert result.result is None  # No successful result
        assert result.duration_ms > 0  # Should track duration even on timeout
