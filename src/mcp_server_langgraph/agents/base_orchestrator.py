"""
Base Orchestrator (REFACTOR phase)

Abstract base class for orchestration patterns shared between UX and Alert orchestrators.

Provides:
- Parallel task execution with asyncio.gather
- Exception handling with conversion to failed results
- Feature flag integration via abstract property
- Metrics instrumentation support
- Generic type support for custom Task/Result types

Usage:
    from mcp_server_langgraph.agents.base_orchestrator import (
        BaseOrchestrator,
        BaseTask,
        BaseResult,
    )

    class MyOrchestrator(BaseOrchestrator[MyTask, MyResult]):
        @property
        def feature_flag_name(self) -> str:
            return "enable_my_orchestrator"

        async def _execute_task(self, task: MyTask) -> MyResult:
            # Implementation
            ...

        def synthesize(self, results: list[MyResult]) -> dict[str, Any]:
            # Implementation
            ...
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Type aliases for lifecycle callbacks
TaskStartCallback = Callable[[Any], Awaitable[None] | None]
TaskCompleteCallback = Callable[[Any, Any], Awaitable[None] | None]
TaskFailCallback = Callable[[Any, str], Awaitable[None] | None]


@dataclass
class BaseTask:
    """Base task dataclass for orchestration.

    Attributes:
        task_type: Type identifier for the task
        data: Optional data payload for the task
    """

    task_type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseResult:
    """Base result dataclass for orchestration.

    Attributes:
        task_type: Type of task that produced this result
        success: Whether the task succeeded
        result: Optional result data (if successful)
        error: Optional error message (if failed)
    """

    task_type: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


# Type variables for generic orchestrator
TaskT = TypeVar("TaskT", bound=BaseTask)
ResultT = TypeVar("ResultT", bound=BaseResult)


class BaseOrchestrator(ABC, Generic[TaskT, ResultT]):
    """Abstract base class for orchestrators.

    Provides common orchestration patterns:
    - Parallel task execution using asyncio.gather
    - Exception handling with conversion to failed results
    - Feature flag integration
    - Metrics instrumentation support

    Type Parameters:
        TaskT: Task type (must have task_type and data attributes)
        ResultT: Result type (must have task_type, success, result, error attributes)
    """

    def __init__(
        self,
        enable_metrics: bool = True,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
        on_task_start: TaskStartCallback | None = None,
        on_task_complete: TaskCompleteCallback | None = None,
        on_task_fail: TaskFailCallback | None = None,
    ) -> None:
        """Initialize base orchestrator.

        Args:
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
            on_task_start: Optional callback invoked when a task starts.
                Signature: (task: TaskT) -> None or Awaitable[None]
            on_task_complete: Optional callback invoked when a task completes.
                Signature: (task: TaskT, result: ResultT) -> None or Awaitable[None]
            on_task_fail: Optional callback invoked when a task fails with exception.
                Signature: (task: TaskT, error: str) -> None or Awaitable[None]
        """
        self._enable_metrics = enable_metrics
        self._cost_tracker = cost_tracker
        self._session_id = session_id
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_fail = on_task_fail

    @property
    def cost_tracker(self) -> CostTracker | None:
        """Get the cost tracker instance."""
        return self._cost_tracker

    @property
    def session_id(self) -> str | None:
        """Get the session ID."""
        return self._session_id

    def get_session_cost(self) -> Decimal:
        """Get current session cost.

        Returns:
            Current session cost as Decimal, or 0 if no tracker configured
        """
        if self._cost_tracker is None or self._session_id is None:
            return Decimal("0")
        return self._cost_tracker.get_session_cost(self._session_id)

    def check_budget(self) -> Any:
        """Check budget status for the current session.

        Returns:
            CostAlert with current budget status
        """
        from mcp_server_langgraph.agents.cost_models import BudgetStatus, CostAlert

        if self._cost_tracker is None or self._session_id is None:
            return CostAlert(
                status=BudgetStatus.OK,
                message="No cost tracking configured",
                current_cost=Decimal("0"),
                limit=Decimal("0"),
                threshold_percentage=0.0,
                session_id=self._session_id or "",
            )
        return self._cost_tracker.check_budget(self._session_id)

    @property
    def enable_metrics(self) -> bool:
        """Whether metrics recording is enabled."""
        return self._enable_metrics

    @property
    @abstractmethod
    def feature_flag_name(self) -> str:
        """Name of the feature flag controlling this orchestrator.

        Returns:
            Feature flag name (e.g., 'enable_orchestrated_ai_ux')
        """
        ...

    @property
    def is_enabled(self) -> bool:
        """Check if this orchestrator is enabled via feature flag.

        Returns:
            True if the feature flag is enabled, False otherwise
        """
        return getattr(feature_flags, self.feature_flag_name, False)

    @abstractmethod
    async def _execute_task(self, task: TaskT) -> ResultT:
        """Execute a single task.

        Subclasses must implement this method to define task execution logic.

        Args:
            task: The task to execute

        Returns:
            Result from executing the task
        """
        ...

    @abstractmethod
    def synthesize(self, results: list[ResultT]) -> dict[str, Any]:
        """Synthesize results from multiple tasks.

        Subclasses must implement this method to define synthesis logic.

        Args:
            results: List of results to synthesize

        Returns:
            Synthesized result dictionary
        """
        ...

    async def _invoke_callback(
        self,
        callback: Callable[..., Awaitable[None] | None] | None,
        *args: Any,
    ) -> None:
        """Invoke a callback, handling both sync and async callbacks.

        Args:
            callback: The callback to invoke (sync or async)
            *args: Arguments to pass to the callback
        """
        if callback is None:
            return

        try:
            result = callback(*args)
            # If callback returns a coroutine, await it
            if inspect.iscoroutine(result):
                await result
        except Exception as e:
            # Log callback errors but don't propagate them
            logger.warning(
                f"Lifecycle callback error: {e}",
                extra={"error": str(e)},
            )

    async def _execute_task_with_callbacks(self, task: TaskT) -> ResultT:
        """Execute a single task with lifecycle callbacks.

        Wraps _execute_task to invoke on_task_start, on_task_complete,
        and on_task_fail callbacks at the appropriate times.

        Args:
            task: The task to execute

        Returns:
            Result from executing the task
        """
        # Call on_task_start callback
        await self._invoke_callback(self._on_task_start, task)

        try:
            result = await self._execute_task(task)

            # Call on_task_complete callback
            await self._invoke_callback(self._on_task_complete, task, result)

            return result
        except Exception as e:
            # Call on_task_fail callback
            await self._invoke_callback(self._on_task_fail, task, str(e))

            # Re-raise so execute() can convert to failed result
            raise

    async def execute(self, tasks: list[TaskT]) -> list[ResultT]:
        """Execute tasks in parallel.

        Uses asyncio.gather to run all tasks concurrently.
        Exceptions are converted to failed results.
        Lifecycle callbacks are invoked for each task.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of results from all tasks
        """
        if not tasks:
            return []

        # Create coroutines for each task (with callbacks)
        coroutines = [self._execute_task_with_callbacks(task) for task in tasks]

        # Execute all tasks in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Convert exceptions to failed results
        final_results: list[ResultT] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create a failed result for the exception
                # We need to create a result with the same type as ResultT
                failed_result = self._create_failed_result(
                    task=tasks[i],
                    error=str(result),
                )
                final_results.append(failed_result)
            else:
                final_results.append(result)  # type: ignore[arg-type]

        return final_results

    def _create_failed_result(self, task: TaskT, error: str) -> ResultT:
        """Create a failed result for a task.

        Default implementation creates a BaseResult. Subclasses can override
        to create custom result types.

        Args:
            task: The task that failed
            error: Error message

        Returns:
            Failed result
        """
        # Default implementation - subclasses may override
        return BaseResult(  # type: ignore
            task_type=task.task_type,
            success=False,
            error=error,
        )
