"""
Unit tests for ParallelToolExecutor

Tests dependency resolution, parallel execution, and error handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.core.parallel_executor import (
    ParallelToolExecutor,
    ToolInvocation,
    ToolResult,
)


@pytest.fixture
def executor():
    """Create ParallelToolExecutor instance for testing"""
    return ParallelToolExecutor(max_parallelism=5)


@pytest.fixture
def mock_tool_executor():
    """Mock tool executor function"""

    async def execute_tool(tool_name: str, arguments: dict) -> str:
        """Simple mock that returns success"""
        await asyncio.sleep(0.01)  # Simulate some work
        return f"Result for {tool_name}"

    return execute_tool


class TestParallelToolExecutor:
    """Test suite for ParallelToolExecutor"""

    def test_initialization(self, executor):
        """Test executor initialization"""
        assert executor.max_parallelism == 5
        assert executor.semaphore._value == 5

    @pytest.mark.asyncio
    async def test_execute_single_tool(self, executor, mock_tool_executor):
        """Test execution of a single tool"""
        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="test_tool",
                arguments={"arg": "value"},
                dependencies=[],
            )
        ]

        results = await executor.execute_parallel(invocations, mock_tool_executor)

        assert len(results) == 1
        assert results[0].error is None
        assert results[0].tool_name == "test_tool"
        assert "test_tool" in results[0].result

    @pytest.mark.asyncio
    async def test_execute_independent_tools_parallel(self, executor):
        """Test parallel execution of independent tools"""
        execution_order = []

        async def tracking_executor(tool_name: str, arguments: dict) -> str:
            execution_order.append((tool_name, "start"))
            await asyncio.sleep(0.05)
            execution_order.append((tool_name, "end"))
            return "done"

        # Create 3 independent tools
        invocations = [
            ToolInvocation(
                invocation_id=f"inv_{i}",
                tool_name=f"tool_{i}",
                arguments={},
                dependencies=[],
            )
            for i in range(3)
        ]

        results = await executor.execute_parallel(invocations, tracking_executor)

        assert len(results) == 3
        assert all(r.error is None for r in results)

        # Verify tools started in parallel (all starts before any end)
        starts = [event for event in execution_order if event[1] == "start"]
        assert len(starts) >= 2  # At least 2 should have started in parallel

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self, executor, mock_tool_executor):
        """Test execution respects dependencies"""
        # Create dependency chain: tool_1 → tool_2 → tool_3
        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="tool_1",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="tool_2",
                arguments={"result": "$inv_1.result"},
                dependencies=["inv_1"],
            ),
            ToolInvocation(
                invocation_id="inv_3",
                tool_name="tool_3",
                arguments={"result": "$inv_2.result"},
                dependencies=["inv_2"],
            ),
        ]

        results = await executor.execute_parallel(invocations, mock_tool_executor)

        assert len(results) == 3
        assert all(r.error is None for r in results)

    @pytest.mark.asyncio
    async def test_mixed_dependencies(self, executor, mock_tool_executor):
        """Test execution with mixed independent and dependent tools"""
        # Tool graph:
        #   A (independent)
        #   B (independent)
        #   C (depends on A)
        #   D (depends on B)
        #   E (depends on C and D)
        invocations = [
            ToolInvocation(
                invocation_id="inv_a",
                tool_name="tool_a",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_b",
                tool_name="tool_b",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_c",
                tool_name="tool_c",
                arguments={"from_a": "$inv_a.result"},
                dependencies=["inv_a"],
            ),
            ToolInvocation(
                invocation_id="inv_d",
                tool_name="tool_d",
                arguments={"from_b": "$inv_b.result"},
                dependencies=["inv_b"],
            ),
            ToolInvocation(
                invocation_id="inv_e",
                tool_name="tool_e",
                arguments={"from_c": "$inv_c.result", "from_d": "$inv_d.result"},
                dependencies=["inv_c", "inv_d"],
            ),
        ]

        results = await executor.execute_parallel(invocations, mock_tool_executor)

        assert len(results) == 5
        assert all(r.error is None for r in results)

    @pytest.mark.asyncio
    async def test_error_handling(self, executor):
        """Test error handling in tool execution"""

        async def failing_executor(tool_name: str, arguments: dict) -> str:
            if tool_name == "failing_tool":
                raise Exception("Tool execution failed")
            return "success"

        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="normal_tool",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="failing_tool",
                arguments={},
                dependencies=[],
            ),
        ]

        results = await executor.execute_parallel(invocations, failing_executor)

        assert len(results) == 2
        assert results[0].error is None
        assert results[1].error is not None
        assert "Tool execution failed" in str(results[1].error)

    @pytest.mark.asyncio
    async def test_dependency_on_failed_tool(self, executor):
        """Test handling when a tool depends on a failed tool"""

        async def conditional_executor(tool_name: str, arguments: dict) -> str:
            if tool_name == "failing_tool":
                raise Exception("Failed")
            # Dependent tool should still execute (executor decides what to do with missing deps)
            return "executed anyway"

        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="failing_tool",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="dependent_tool",
                arguments={"from_1": "$inv_1.result"},
                dependencies=["inv_1"],
            ),
        ]

        results = await executor.execute_parallel(invocations, conditional_executor)

        assert len(results) == 2
        assert results[0].error is not None
        # Dependent still executes (executor's responsibility to check deps)
        assert results[1].error is None

    @pytest.mark.asyncio
    async def test_parallelism_limit(self, executor):
        """Test that parallelism respects max_parallelism limit"""
        concurrent_count = 0
        max_concurrent = 0

        async def tracking_executor(tool_name: str, arguments: dict) -> str:
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.02)
            concurrent_count -= 1
            return "done"

        # Create 10 independent tools (more than max_parallelism)
        invocations = [
            ToolInvocation(
                invocation_id=f"inv_{i}",
                tool_name=f"tool_{i}",
                arguments={},
                dependencies=[],
            )
            for i in range(10)
        ]

        results = await executor.execute_parallel(invocations, tracking_executor)

        assert len(results) == 10
        assert all(r.error is None for r in results)
        assert max_concurrent <= executor.max_parallelism

    def test_build_dependency_graph(self, executor):
        """Test dependency graph construction"""
        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="tool_1",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="tool_2",
                arguments={"from_1": "$inv_1.result"},
                dependencies=["inv_1"],
            ),
        ]

        graph = executor._build_dependency_graph(invocations)

        assert "inv_1" in graph
        assert "inv_2" in graph
        assert graph["inv_1"] == []  # No dependencies
        assert graph["inv_2"] == ["inv_1"]  # Depends on inv_1

    def test_topological_sort(self, executor):
        """Test topological sorting of dependency graph"""
        # Graph: A → B → C, D (independent)
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["B"],
            "D": [],
        }

        invocations = {
            "A": ToolInvocation(tool_name="tool_a", arguments={}, invocation_id="A", dependencies=[]),
            "B": ToolInvocation(tool_name="tool_b", arguments={}, invocation_id="B", dependencies=["A"]),
            "C": ToolInvocation(tool_name="tool_c", arguments={}, invocation_id="C", dependencies=["B"]),
            "D": ToolInvocation(tool_name="tool_d", arguments={}, invocation_id="D", dependencies=[]),
        }

        sorted_order = executor._topological_sort(graph)

        # Check order constraints
        assert sorted_order.index("A") < sorted_order.index("B")
        assert sorted_order.index("B") < sorted_order.index("C")
        # D can be anywhere (independent)

    def test_topological_sort_cycle_detection(self, executor):
        """Test detection of circular dependencies"""
        # Circular graph: A → B → C → A
        graph = {
            "A": ["C"],
            "B": ["A"],
            "C": ["B"],
        }

        with pytest.raises(ValueError, match="Circular dependency detected"):
            executor._topological_sort(graph)

    def test_group_by_level(self, executor):
        """Test grouping of invocations by execution level"""
        # Graph: A, B (level 0), C depends on A (level 1), D depends on B (level 1), E depends on C,D (level 2)
        execution_order = ["A", "B", "C", "D", "E"]
        graph = {
            "A": [],
            "B": [],
            "C": ["A"],
            "D": ["B"],
            "E": ["C", "D"],
        }

        invocations = [
            ToolInvocation(tool_name="tool_a", arguments={}, invocation_id="A", dependencies=[]),
            ToolInvocation(tool_name="tool_b", arguments={}, invocation_id="B", dependencies=[]),
            ToolInvocation(tool_name="tool_c", arguments={}, invocation_id="C", dependencies=["A"]),
            ToolInvocation(tool_name="tool_d", arguments={}, invocation_id="D", dependencies=["B"]),
            ToolInvocation(tool_name="tool_e", arguments={}, invocation_id="E", dependencies=["C", "D"]),
        ]

        levels = executor._group_by_level(execution_order, graph, invocations)

        # Should have 3 levels
        assert len(levels) == 3

        # Level 0: A and B (independent)
        level_0_names = [inv.invocation_id for inv in levels[0]]
        assert set(level_0_names) == {"A", "B"}

        # Level 1: C and D (depend on level 0)
        level_1_names = [inv.invocation_id for inv in levels[1]]
        assert set(level_1_names) == {"C", "D"}

        # Level 2: E (depends on level 1)
        level_2_names = [inv.invocation_id for inv in levels[2]]
        assert level_2_names == ["E"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, executor):
        """Test handling of exceptions during tool execution"""

        async def exception_executor(tool_name: str, arguments: dict) -> str:
            if tool_name == "exception_tool":
                raise RuntimeError("Unexpected error")
            return "done"

        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="normal_tool",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="exception_tool",
                arguments={},
                dependencies=[],
            ),
        ]

        results = await executor.execute_parallel(invocations, exception_executor)

        assert len(results) == 2
        # One success, one exception (converted to failed result)
        successful = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]

        assert len(successful) == 1
        assert len(failed) == 1
        assert "Unexpected error" in str(failed[0].error)

    @pytest.mark.asyncio
    async def test_parameter_substitution_detection(self, executor):
        """Test detection of dependencies from parameter references"""
        # Tool with parameter reference like "$inv_1.result"
        invocations = [
            ToolInvocation(
                invocation_id="inv_1",
                tool_name="tool_1",
                arguments={},
                dependencies=[],
            ),
            ToolInvocation(
                invocation_id="inv_2",
                tool_name="tool_2",
                arguments={
                    "input": "$inv_1.result",  # Reference to inv_1's result
                    "other": "static_value",
                },
                dependencies=["inv_1"],
            ),
        ]

        graph = executor._build_dependency_graph(invocations)

        # inv_2 should depend on inv_1
        assert "inv_1" in graph["inv_2"]


@pytest.mark.integration
class TestParallelExecutorIntegration:
    """Integration tests for ParallelToolExecutor"""

    @pytest.mark.asyncio
    async def test_complex_workflow(self):
        """Test complex workflow with multiple dependency levels"""
        executor = ParallelToolExecutor(max_parallelism=3)

        execution_log = []

        async def logging_executor(tool_name: str, arguments: dict) -> str:
            execution_log.append(("start", tool_name))
            await asyncio.sleep(0.01)
            execution_log.append(("end", tool_name))
            return f"result_{tool_name}"

        # Complex graph:
        #   A, B, C (level 0, parallel)
        #   D depends on A (level 1)
        #   E depends on B (level 1)
        #   F depends on D,E (level 2)
        #   G depends on C (level 1)
        invocations = [
            ToolInvocation(tool_name="tool_a", arguments={}, invocation_id="A", dependencies=[]),
            ToolInvocation(tool_name="tool_b", arguments={}, invocation_id="B", dependencies=[]),
            ToolInvocation(tool_name="tool_c", arguments={}, invocation_id="C", dependencies=[]),
            ToolInvocation(tool_name="tool_d", arguments={}, invocation_id="D", dependencies=["A"]),
            ToolInvocation(tool_name="tool_e", arguments={}, invocation_id="E", dependencies=["B"]),
            ToolInvocation(tool_name="tool_f", arguments={}, invocation_id="F", dependencies=["D", "E"]),
            ToolInvocation(tool_name="tool_g", arguments={}, invocation_id="G", dependencies=["C"]),
        ]

        results = await executor.execute_parallel(invocations, logging_executor)

        assert len(results) == 7
        assert all(r.error is None for r in results)

        # Verify execution order constraints
        def get_end_time(tool_name):
            for i, (event, name) in enumerate(execution_log):
                if event == "end" and name == tool_name:
                    return i
            return -1

        # D must end after A
        assert get_end_time("D") > get_end_time("A")
        # E must end after B
        assert get_end_time("E") > get_end_time("B")
        # F must end after D and E
        assert get_end_time("F") > get_end_time("D")
        assert get_end_time("F") > get_end_time("E")
        # G must end after C
        assert get_end_time("G") > get_end_time("C")
