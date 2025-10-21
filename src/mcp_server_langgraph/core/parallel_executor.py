"""
Parallel Tool Execution

Implements Anthropic's parallelization pattern for independent operations.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


@dataclass
class ToolInvocation:
    """Represents a tool invocation."""

    tool_name: str
    arguments: dict[str, Any]
    invocation_id: str
    dependencies: list[str] = field(default_factory=list)  # IDs of tools this depends on


@dataclass
class ToolResult:
    """Result from tool execution."""

    invocation_id: str
    tool_name: str
    result: Any
    error: Exception | None = None
    duration_ms: float = 0.0


class ParallelToolExecutor:
    """
    Executes tools in parallel when they have no dependencies.

    Implements Anthropic's parallelization pattern:
    - Detects independent operations
    - Schedules parallel execution
    - Respects dependencies
    - Aggregates results
    """

    def __init__(self, max_parallelism: int = 5) -> None:
        """
        Initialize parallel executor.

        Args:
            max_parallelism: Maximum concurrent tool executions
        """
        self.max_parallelism = max_parallelism
        self.semaphore = asyncio.Semaphore(max_parallelism)

    async def execute_parallel(
        self, invocations: list[ToolInvocation], tool_executor: Callable[[str, dict[str, Any]], Any]
    ) -> list[ToolResult]:
        """
        Execute tool invocations in parallel where possible.

        Args:
            invocations: List of tool invocations
            tool_executor: Async function to execute a single tool

        Returns:
            List of tool results
        """
        with tracer.start_as_current_span("tools.parallel_execute") as span:
            span.set_attribute("total_invocations", len(invocations))

            # Build dependency graph
            dependency_graph = self._build_dependency_graph(invocations)

            # Topological sort for execution order
            execution_order = self._topological_sort(dependency_graph)

            # Group by dependency level (all items in same level can run in parallel)
            levels = self._group_by_level(execution_order, dependency_graph, invocations)

            span.set_attribute("parallelization_levels", len(levels))

            logger.info(
                "Executing tools in parallel",
                extra={
                    "total_tools": len(invocations),
                    "levels": len(levels),
                    "max_parallelism": self.max_parallelism,
                },
            )

            # Execute level by level
            all_results = {}

            for level_idx, level_invocations in enumerate(levels):
                logger.info(f"Executing level {level_idx + 1}/{len(levels)} with {len(level_invocations)} tools")

                # Execute all invocations in this level in parallel
                tasks = [self._execute_single(inv, tool_executor) for inv in level_invocations]

                level_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Store results
                for inv, result in zip(level_invocations, level_results):
                    all_results[inv.invocation_id] = result

            # Convert to list maintaining original order
            results = [all_results[inv.invocation_id] for inv in invocations]

            # Calculate metrics
            successful = sum(1 for r in results if isinstance(r, ToolResult) and r.error is None)
            failed = len(results) - successful

            span.set_attribute("successful", successful)
            span.set_attribute("failed", failed)

            metrics.successful_calls.add(successful, {"operation": "parallel_tool_execution"})
            if failed > 0:
                metrics.failed_calls.add(failed, {"operation": "parallel_tool_execution"})

            return results  # type: ignore[ToolResult ]

    # type: ignore[type-arg]
    async def _execute_single(self, invocation: ToolInvocation, tool_executor: Callable) -> ToolResult:
        """Execute a single tool invocation."""
        async with self.semaphore:  # Limit concurrency
            start_time = time.time()

            try:
                result = await tool_executor(invocation.tool_name, invocation.arguments)
                duration_ms = (time.time() - start_time) * 1000

                return ToolResult(
                    invocation_id=invocation.invocation_id,
                    tool_name=invocation.tool_name,
                    result=result,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Tool execution failed: {invocation.tool_name}",
                    extra={"error": str(e)},
                    exc_info=True,
                )

                return ToolResult(
                    invocation_id=invocation.invocation_id,
                    tool_name=invocation.tool_name,
                    result=None,
                    error=e,
                    duration_ms=duration_ms,
                )

    def _build_dependency_graph(self, invocations: list[ToolInvocation]) -> dict[str, list[str]]:
        """Build dependency graph from invocations."""
        graph = {inv.invocation_id: inv.dependencies for inv in invocations}
        return graph

    def _topological_sort(self, graph: dict[str, list[str]]) -> list[str]:
        """
        Topological sort of dependency graph.

        Returns nodes in an order where dependencies come before dependents.
        """
        # Calculate in-degrees (number of dependencies each node has)
        in_degree = {node: len(graph[node]) for node in graph}

        # Queue nodes with no dependencies (in-degree = 0)
        queue = deque([node for node in graph if in_degree[node] == 0])
        sorted_order = []

        while queue:
            node = queue.popleft()
            sorted_order.append(node)

            # Find nodes that depend on this node and reduce their in-degree
            for other_node in graph:
                if node in graph[other_node]:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)

        # Check for circular dependencies
        if len(sorted_order) != len(graph):
            raise ValueError("Circular dependency detected in tool execution graph")

        return sorted_order

    def _group_by_level(
        self, sorted_nodes: list[str], graph: dict[str, list[str]], invocations: list[ToolInvocation]
    ) -> list[list[ToolInvocation]]:
        """Group nodes by dependency level for parallel execution."""
        # Create invocation lookup
        inv_lookup = {inv.invocation_id: inv for inv in invocations}

        levels = []
        processed = set()

        while processed != set(sorted_nodes):
            current_level = []

            for node in sorted_nodes:
                if node in processed:
                    continue

                # Check if all dependencies are processed
                deps_satisfied = all(dep in processed for dep in graph[node])

                if deps_satisfied:
                    current_level.append(node)

            if current_level:
                # Convert node IDs to ToolInvocations
                level_invocations = [inv_lookup[node_id] for node_id in current_level]
                levels.append(level_invocations)
                processed.update(current_level)
            else:
                # Circular dependency or error
                break

        return levels


# Example usage function
async def execute_multi_tool_request(user_request: str, tool_calls: list[dict[str, Any]]) -> list[ToolResult]:
    """
    Execute multiple tool calls efficiently with parallelization.

    Example:
        user_request = "Search for Python and JavaScript, then compare them"
        tool_calls = [
            {"tool": "search", "args": {"query": "Python"}},
            {"tool": "search", "args": {"query": "JavaScript"}},
            {"tool": "compare", "args": {"items": ["result_1", "result_2"]}, "deps": ["1", "2"]}
        ]

    Args:
        user_request: The original user request
        tool_calls: List of tool call specifications

    Returns:
        List of tool results
    """
    executor = ParallelToolExecutor(max_parallelism=5)

    # Convert to invocations
    invocations = []
    for i, call in enumerate(tool_calls):
        inv = ToolInvocation(
            tool_name=call["tool"],
            arguments=call["args"],
            invocation_id=str(i + 1),
            dependencies=call.get("deps", []),
        )
        invocations.append(inv)

    # Mock tool executor for demonstration
    async def mock_tool_executor(name: str, args: dict) -> Any:  # type: ignore[type-arg]
        await asyncio.sleep(0.1)  # Simulate work
        return f"Result from {name}"

    results = await executor.execute_parallel(invocations, mock_tool_executor)

    return results
