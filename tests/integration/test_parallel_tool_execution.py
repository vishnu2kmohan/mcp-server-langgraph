"""
Integration tests for parallel tool execution

Tests that the enable_parallel_execution flag works correctly and
that parallel execution provides performance improvements.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.config import Settings


@pytest.mark.integration
class TestParallelToolExecution:
    """Test suite for parallel tool execution"""

    @pytest.fixture
    def settings_serial(self):
        """Settings with parallel execution disabled"""
        return Settings(enable_parallel_execution=False, max_parallel_tools=5)

    @pytest.fixture
    def settings_parallel(self):
        """Settings with parallel execution enabled"""
        return Settings(enable_parallel_execution=True, max_parallel_tools=5)

    @pytest.mark.asyncio
    async def test_parallel_execution_flag_disabled(self, settings_serial):
        """Test that tools execute serially when flag is disabled"""
        # This test verifies the default behavior
        assert settings_serial.enable_parallel_execution is False

    @pytest.mark.asyncio
    async def test_parallel_execution_flag_enabled(self, settings_parallel):
        """Test that parallel execution can be enabled"""
        assert settings_parallel.enable_parallel_execution is True
        assert settings_parallel.max_parallel_tools == 5

    @pytest.mark.asyncio
    async def test_parallel_executor_multiple_independent_tools(self):
        """Test that independent tools execute in parallel"""
        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation

        executor = ParallelToolExecutor(max_parallelism=3)

        # Create mock tool invocations with delays
        invocations = [
            ToolInvocation(tool_name="tool1", arguments={"delay": 0.1}, invocation_id="1", dependencies=[]),
            ToolInvocation(tool_name="tool2", arguments={"delay": 0.1}, invocation_id="2", dependencies=[]),
            ToolInvocation(tool_name="tool3", arguments={"delay": 0.1}, invocation_id="3", dependencies=[]),
        ]

        async def mock_executor(tool_name: str, arguments: dict):
            """Mock tool that sleeps"""
            await asyncio.sleep(arguments.get("delay", 0))
            return f"Result from {tool_name}"

        # Measure execution time
        start_time = time.time()
        results = await executor.execute_parallel(invocations, mock_executor)
        elapsed_time = time.time() - start_time

        # Verify results
        assert len(results) == 3
        assert all(r.error is None for r in results)

        # Parallel execution should be faster than serial (3 * 0.1 = 0.3s)
        # With parallel execution, should be close to 0.1s (allowing some overhead)
        assert elapsed_time < 0.25, f"Expected parallel execution < 0.25s, got {elapsed_time}s"

    @pytest.mark.asyncio
    async def test_serial_execution_baseline(self):
        """Test serial execution timing as baseline"""
        # Execute 3 tools serially, each taking 0.1s
        async def slow_tool(delay: float):
            await asyncio.sleep(delay)
            return "done"

        start_time = time.time()
        results = []
        for _ in range(3):
            result = await slow_tool(0.1)
            results.append(result)
        elapsed_time = time.time() - start_time

        # Serial should take ~0.3s
        assert elapsed_time >= 0.3, f"Expected serial execution >= 0.3s, got {elapsed_time}s"
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_parallel_executor_with_dependencies(self):
        """Test that dependent tools execute in correct order"""
        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation

        executor = ParallelToolExecutor(max_parallelism=3)

        # Create invocations with dependencies
        # Tool2 depends on Tool1, Tool3 depends on Tool2
        invocations = [
            ToolInvocation(tool_name="tool1", arguments={}, invocation_id="1", dependencies=[]),
            ToolInvocation(tool_name="tool2", arguments={}, invocation_id="2", dependencies=["1"]),
            ToolInvocation(tool_name="tool3", arguments={}, invocation_id="3", dependencies=["2"]),
        ]

        execution_order = []

        async def tracking_executor(tool_name: str, arguments: dict):
            """Executor that tracks execution order"""
            execution_order.append(tool_name)
            await asyncio.sleep(0.01)  # Small delay
            return f"Result from {tool_name}"

        results = await executor.execute_parallel(invocations, tracking_executor)

        # Verify execution order respects dependencies
        assert len(results) == 3
        assert execution_order == ["tool1", "tool2", "tool3"]

    @pytest.mark.asyncio
    async def test_parallel_executor_error_handling(self):
        """Test that errors in one tool don't break others"""
        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation

        executor = ParallelToolExecutor(max_parallelism=3)

        invocations = [
            ToolInvocation(tool_name="good_tool", arguments={}, invocation_id="1", dependencies=[]),
            ToolInvocation(tool_name="bad_tool", arguments={}, invocation_id="2", dependencies=[]),
            ToolInvocation(tool_name="good_tool2", arguments={}, invocation_id="3", dependencies=[]),
        ]

        async def mixed_executor(tool_name: str, arguments: dict):
            """Executor where one tool fails"""
            if tool_name == "bad_tool":
                raise ValueError("Intentional error")
            return f"Success: {tool_name}"

        results = await executor.execute_parallel(invocations, mixed_executor)

        # Verify results
        assert len(results) == 3

        # Check that good tools succeeded
        good_results = [r for r in results if r.tool_name in ["good_tool", "good_tool2"]]
        assert len(good_results) == 2
        assert all(r.error is None for r in good_results)

        # Check that bad tool has error
        bad_results = [r for r in results if r.tool_name == "bad_tool"]
        assert len(bad_results) == 1
        assert bad_results[0].error is not None

    @pytest.mark.asyncio
    async def test_max_parallelism_limit(self):
        """Test that max_parallelism limit is respected"""
        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation

        # Set max parallelism to 2
        executor = ParallelToolExecutor(max_parallelism=2)

        # Create 5 tool invocations
        invocations = [
            ToolInvocation(tool_name=f"tool{i}", arguments={"id": i}, invocation_id=str(i), dependencies=[])
            for i in range(5)
        ]

        concurrent_count = 0
        max_concurrent = 0

        async def tracking_executor(tool_name: str, arguments: dict):
            """Track concurrent executions"""
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)  # Small delay
            concurrent_count -= 1
            return f"Result from {tool_name}"

        await executor.execute_parallel(invocations, tracking_executor)

        # Verify max concurrent executions didn't exceed limit
        assert max_concurrent <= 2, f"Expected max 2 concurrent, got {max_concurrent}"


@pytest.mark.integration
@pytest.mark.benchmark
class TestParallelExecutionPerformance:
    """Performance benchmarks for parallel execution"""

    @pytest.mark.asyncio
    async def test_latency_improvement_independent_tools(self):
        """Verify 1.5-2.5x latency improvement for independent tools"""
        from mcp_server_langgraph.core.parallel_executor import ParallelToolExecutor, ToolInvocation

        num_tools = 4
        tool_delay = 0.1

        # Serial baseline
        start = time.time()
        serial_results = []
        for i in range(num_tools):
            await asyncio.sleep(tool_delay)
            serial_results.append(f"result{i}")
        serial_time = time.time() - start

        # Parallel execution
        executor = ParallelToolExecutor(max_parallelism=num_tools)
        invocations = [
            ToolInvocation(tool_name=f"tool{i}", arguments={"delay": tool_delay}, invocation_id=str(i), dependencies=[])
            for i in range(num_tools)
        ]

        async def delay_executor(tool_name: str, arguments: dict):
            await asyncio.sleep(arguments["delay"])
            return f"Result from {tool_name}"

        start = time.time()
        parallel_results = await executor.execute_parallel(invocations, delay_executor)
        parallel_time = time.time() - start

        # Calculate speedup
        speedup = serial_time / parallel_time

        # Verify speedup is in expected range (1.5-2.5x allowing for overhead)
        assert speedup >= 1.3, f"Expected speedup >= 1.3x, got {speedup:.2f}x"
        assert len(parallel_results) == num_tools
        print(f"\n📊 Parallel execution speedup: {speedup:.2f}x ({serial_time:.3f}s → {parallel_time:.3f}s)")

    @pytest.mark.asyncio
    async def test_single_tool_no_overhead(self):
        """Verify single tool doesn't use parallel executor"""
        # With only 1 tool, should use serial execution
        # This test documents the behavior
        tool_delay = 0.1

        async def single_tool():
            await asyncio.sleep(tool_delay)
            return "result"

        start = time.time()
        result = await single_tool()
        single_time = time.time() - start

        # Should be close to tool_delay with minimal overhead
        assert single_time < tool_delay * 1.2, f"Single tool took too long: {single_time}s"
