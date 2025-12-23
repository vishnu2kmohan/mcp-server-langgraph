"""
LoopAgent Pattern Implementation (ADR-0084 / Google ADK parity)

Provides iterative task execution until a condition is met,
with maximum iteration limits, termination condition evaluation,
continue-on-error option, and iteration state tracking.

Reference: Google ADK LoopAgent pattern
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator, BaseResult, BaseTask
from mcp_server_langgraph.core.feature_flags import feature_flags

# Type variable for task function return type
T = TypeVar("T")


@dataclass
class LoopConfig:
    """Configuration for LoopAgent execution."""

    max_iterations: int
    termination_condition: Callable[[Any], bool] | None = None
    continue_on_error: bool = False
    timeout_per_iteration_ms: int | None = None


@dataclass
class LoopTask(BaseTask):
    """Task for a single loop iteration."""

    task_type: str = field(default="loop_iteration")
    iteration: int = 0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopIterationResult:
    """Result from a single loop iteration."""

    iteration: int
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class LoopResult(BaseResult):
    """Complete result from LoopAgent execution."""

    success: bool = True
    iterations_completed: int = 0
    terminated_early: bool = False
    final_result: dict[str, Any] | None = None
    iteration_results: list[LoopIterationResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    failed_at_iteration: int | None = None
    total_duration_ms: float = 0.0


class LoopAgent(BaseOrchestrator[LoopTask, LoopIterationResult]):
    """
    Iterative task execution agent with termination conditions.

    Implements the LoopAgent pattern from Google ADK for running
    a task repeatedly until a condition is met or max iterations reached.

    Args:
        max_iterations: Maximum number of iterations (required)
        termination_condition: Optional callback to check if loop should stop
        continue_on_error: If True, continue loop even if iteration fails

    Example:
        agent = LoopAgent(
            max_iterations=10,
            termination_condition=lambda r: r.get("done", False)
        )
        result = await agent.execute_loop(my_task_fn)
    """

    def __init__(
        self,
        max_iterations: int,
        termination_condition: Callable[[Any], bool] | None = None,
        continue_on_error: bool = False,
    ) -> None:
        """Initialize LoopAgent with configuration."""
        # Check feature flag
        feature_flags.require_feature("enable_loop_agent", "Loop Agent")

        super().__init__()
        self.max_iterations = max_iterations
        self.termination_condition = termination_condition
        self.continue_on_error = continue_on_error

    @property
    def feature_flag_name(self) -> str:
        """Feature flag controlling this orchestrator."""
        return "enable_loop_agent"

    def check_termination(self, result: Any) -> bool:
        """
        Check if the loop should terminate based on the result.

        Args:
            result: The result from the latest iteration

        Returns:
            True if termination condition is met, False otherwise
        """
        if self.termination_condition is None:
            return False
        return self.termination_condition(result)

    async def _execute_task(self, task: LoopTask) -> LoopIterationResult:
        """
        Execute a single iteration task.

        This method is called by the base orchestrator for each task.
        For LoopAgent, we override execute_loop to handle iteration logic.

        Args:
            task: The loop task to execute

        Returns:
            Result from the iteration
        """
        # This is a placeholder - actual execution happens in execute_loop
        return LoopIterationResult(
            iteration=task.iteration,
            success=True,
            result=task.context,
        )

    def synthesize(self, results: list[LoopIterationResult]) -> dict[str, Any]:
        """
        Synthesize results from loop iterations.

        For LoopAgent, this collects all iteration results into a summary.

        Args:
            results: List of iteration results

        Returns:
            Synthesized result dictionary
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        return {
            "total_iterations": len(results),
            "successful_iterations": len(successful),
            "failed_iterations": len(failed),
            "final_result": results[-1].result if results else None,
            "all_results": [
                {
                    "iteration": r.iteration,
                    "success": r.success,
                    "result": r.result,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

    async def execute_loop(
        self,
        task_fn: Callable[..., Any],
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the loop with the given task function.

        Args:
            task_fn: The async or sync function to call each iteration.
                    Can optionally accept a context dict parameter.
            initial_context: Optional initial context to pass to first iteration

        Returns:
            Dictionary with loop execution results:
                - iterations_completed: Number of iterations run
                - terminated_early: True if termination condition was met
                - final_result: Result from final iteration
                - iteration_results: List of all iteration results
                - errors: List of errors if continue_on_error=True
                - error: Error message if loop stopped on error
                - failed_at_iteration: Iteration number where error occurred
                - total_duration_ms: Total execution time
        """
        import asyncio
        import inspect

        start_time = time.perf_counter()
        context = dict(initial_context) if initial_context else {}
        iteration_results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        terminated_early = False
        error_msg: str | None = None
        failed_at_iteration: int | None = None
        final_result: dict[str, Any] | None = None

        for iteration in range(1, self.max_iterations + 1):
            iter_start = time.perf_counter()
            try:
                # Check if task_fn accepts context parameter
                sig = inspect.signature(task_fn)
                if sig.parameters:
                    # Call with context
                    if asyncio.iscoroutinefunction(task_fn):
                        result = await task_fn(context)
                    else:
                        result = task_fn(context)
                else:
                    # Call without arguments
                    if asyncio.iscoroutinefunction(task_fn):
                        result = await task_fn()
                    else:
                        result = task_fn()

                iter_duration = (time.perf_counter() - iter_start) * 1000
                iteration_results.append(
                    {
                        "iteration": iteration,
                        "success": True,
                        "result": result,
                        "duration_ms": iter_duration,
                    }
                )

                # Update context with result for next iteration
                if isinstance(result, dict):
                    context.update(result)
                    final_result = result

                # Check termination condition
                if self.check_termination(result):
                    terminated_early = True
                    break

            except Exception as e:
                iter_duration = (time.perf_counter() - iter_start) * 1000
                error_info = {
                    "iteration": iteration,
                    "error": str(e),
                    "duration_ms": iter_duration,
                }

                if self.continue_on_error:
                    errors.append(error_info)
                    iteration_results.append(
                        {
                            "iteration": iteration,
                            "success": False,
                            "error": str(e),
                            "duration_ms": iter_duration,
                        }
                    )
                else:
                    # Stop execution on error
                    error_msg = str(e)
                    failed_at_iteration = iteration
                    break

        total_duration = (time.perf_counter() - start_time) * 1000

        return {
            "iterations_completed": len(iteration_results),
            "terminated_early": terminated_early,
            "final_result": final_result,
            "iteration_results": iteration_results,
            "errors": errors,
            "error": error_msg,
            "failed_at_iteration": failed_at_iteration,
            "total_duration_ms": total_duration,
        }
