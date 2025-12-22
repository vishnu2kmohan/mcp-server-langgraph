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
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


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
    ) -> None:
        """Initialize base orchestrator.

        Args:
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
        """
        self._enable_metrics = enable_metrics
        self._cost_tracker = cost_tracker
        self._session_id = session_id

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

    async def execute(self, tasks: list[TaskT]) -> list[ResultT]:
        """Execute tasks in parallel.

        Uses asyncio.gather to run all tasks concurrently.
        Exceptions are converted to failed results.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of results from all tasks
        """
        if not tasks:
            return []

        # Create coroutines for each task
        coroutines = [self._execute_task(task) for task in tasks]

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
