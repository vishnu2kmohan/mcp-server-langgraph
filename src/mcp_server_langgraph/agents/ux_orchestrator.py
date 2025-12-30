"""
UX Orchestrator (Phase 11)

Orchestrates AI UX Service composite analysis using parallel execution.

Migrates the sequential AI UX Service's composite analysis to the
orchestrator-worker pattern for improved performance:

Before:
  run_composite_analysis()
    → analyze_persona() [LLM]
    → analyze_disclosure() [LLM]
    → analyze_error() [LLM]
    → synthesize [sequential]

After:
  UXOrchestrator
    → PersonaAgent [parallel]
    → DisclosureAgent [parallel]
    → ErrorAgent [parallel]
    → Synthesizer [aggregates via ArtifactStorage]

Usage:
    from mcp_server_langgraph.agents.ux_orchestrator import (
        UXOrchestrator,
        UXAnalysisTask,
        UXAnalysisResult,
    )

    orchestrator = UXOrchestrator(ai_ux_service=service)
    result = await orchestrator.run_composite_analysis(
        user_id="user-123",
        session_id="session-456",
        include_persona=True,
        include_disclosure=True,
        persona_data={"assigned_persona": "bob"},
        disclosure_data={"feature_usage": {}},
    )
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
    TaskCompleteCallback,
    TaskFailCallback,
    TaskStartCallback,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker
    from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
        OrchestratorStatusBroadcasterProtocol,
    )

logger = logging.getLogger(__name__)

# Supported analysis types for UX orchestration
UX_ANALYSIS_TYPES = frozenset(
    {
        "persona_analysis",
        "disclosure_analysis",
        "error_analysis",
    }
)


@dataclass
class UXAnalysisTask(BaseTask):
    """Task definition for UX analysis.

    Extends BaseTask with user context for UX analysis operations.

    Attributes:
        task_type: Type of analysis (persona_analysis, disclosure_analysis, error_analysis)
        user_id: User identifier for the analysis
        data: Optional data payload for the analysis
    """

    user_id: str = ""


@dataclass
class UXAnalysisResult(BaseResult):
    """Result from a UX analysis task.

    Extends BaseResult for UX analysis results. Inherits all base fields.

    Attributes:
        task_type: Type of analysis performed
        success: Whether the analysis succeeded
        result: Analysis result data (if successful)
        error: Error message (if failed)
    """

    pass


class UXOrchestrator(BaseOrchestrator[UXAnalysisTask, UXAnalysisResult]):
    """Orchestrates parallel UX analysis tasks.

    Coordinates persona, disclosure, and error analysis tasks in parallel,
    then synthesizes results into cross-service insights.

    Inherits from BaseOrchestrator to use common parallel execution patterns.
    """

    def __init__(
        self,
        ai_ux_service: Any | None = None,
        artifact_storage: Any | None = None,
        enable_metrics: bool = True,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
        status_broadcaster: OrchestratorStatusBroadcasterProtocol | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialize UX Orchestrator.

        Args:
            ai_ux_service: Optional AIUXService instance for analysis methods
            artifact_storage: Optional ArtifactStorage for intermediate results
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
            status_broadcaster: Optional broadcaster for real-time status updates
            user_id: Optional user ID for filtering WebSocket broadcasts
        """
        # Store broadcaster and user_id before super().__init__ for callbacks
        self._status_broadcaster = status_broadcaster
        self._user_id = user_id
        self._task_start_times: dict[str, tuple[str, datetime]] = {}

        # Create lifecycle callbacks for WebSocket broadcasting
        on_task_start = self._create_task_start_callback() if status_broadcaster else None
        on_task_complete = self._create_task_complete_callback() if status_broadcaster else None
        on_task_fail = self._create_task_fail_callback() if status_broadcaster else None

        super().__init__(
            enable_metrics=enable_metrics,
            cost_tracker=cost_tracker,
            session_id=session_id,
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
            on_task_fail=on_task_fail,
        )
        self._ai_ux_service = ai_ux_service
        self._artifact_storage = artifact_storage

    def _create_task_start_callback(self) -> TaskStartCallback:
        """Create callback for task start events."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            TaskCategory,
            TaskInfo,
        )

        async def on_task_start(task: UXAnalysisTask) -> None:
            if self._status_broadcaster is None:
                return

            task_id = str(uuid.uuid4())
            start_time = datetime.now(UTC)
            self._task_start_times[task.task_type] = (task_id, start_time)

            task_info = TaskInfo(
                task_id=task_id,
                task_type=task.task_type,
                category=TaskCategory.UX,  # All UX tasks are UX category
                started_at=start_time,
            )

            await self._status_broadcaster.broadcast_task_started(
                task_info=task_info,
                user_id=self._user_id,
            )

            await self._status_broadcaster.broadcast_status(
                status=OrchestratorStatus.PROCESSING,
                message=f"Processing {task.task_type}...",
                task_type=task.task_type,
                category=TaskCategory.UX,
                user_id=self._user_id,
            )

        return on_task_start

    def _create_task_complete_callback(self) -> TaskCompleteCallback:
        """Create callback for task completion events."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            TaskCategory,
            TaskInfo,
        )

        async def on_task_complete(task: UXAnalysisTask, result: UXAnalysisResult) -> None:
            if self._status_broadcaster is None:
                return

            task_id, start_time = self._task_start_times.pop(
                task.task_type,
                (str(uuid.uuid4()), datetime.now(UTC)),
            )

            task_info = TaskInfo(
                task_id=task_id,
                task_type=task.task_type,
                category=TaskCategory.UX,
                started_at=start_time,
                completed_at=datetime.now(UTC),
                success=result.success,
            )

            await self._status_broadcaster.broadcast_task_completed(
                task_info=task_info,
                user_id=self._user_id,
            )

        return on_task_complete

    def _create_task_fail_callback(self) -> TaskFailCallback:
        """Create callback for task failure events."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            TaskCategory,
            TaskInfo,
        )

        async def on_task_fail(task: UXAnalysisTask, error: str) -> None:
            if self._status_broadcaster is None:
                return

            task_id, start_time = self._task_start_times.pop(
                task.task_type,
                (str(uuid.uuid4()), datetime.now(UTC)),
            )

            task_info = TaskInfo(
                task_id=task_id,
                task_type=task.task_type,
                category=TaskCategory.UX,
                started_at=start_time,
                completed_at=datetime.now(UTC),
                success=False,
                error=error,
            )

            await self._status_broadcaster.broadcast_task_failed(
                task_info=task_info,
                user_id=self._user_id,
            )

            await self._status_broadcaster.broadcast_status(
                status=OrchestratorStatus.ERROR,
                message=f"Task {task.task_type} failed: {error}",
                task_type=task.task_type,
                category=TaskCategory.UX,
                user_id=self._user_id,
            )

        return on_task_fail

    async def execute(self, tasks: list[UXAnalysisTask]) -> list[UXAnalysisResult]:
        """Execute tasks and broadcast IDLE status when complete.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of results from all tasks
        """
        results = await super().execute(tasks)

        # Broadcast IDLE status after all tasks complete
        if self._status_broadcaster is not None and tasks:
            from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
                OrchestratorStatus,
            )

            await self._status_broadcaster.broadcast_status(
                status=OrchestratorStatus.IDLE,
                message="All tasks completed",
                user_id=self._user_id,
            )

        return results

    @property
    def status_broadcaster(self) -> OrchestratorStatusBroadcasterProtocol | None:
        """Get the status broadcaster instance."""
        return self._status_broadcaster

    @property
    def ai_ux_service(self) -> Any | None:
        """Get the AI UX service instance."""
        return self._ai_ux_service

    @property
    def artifact_storage(self) -> Any | None:
        """Get the artifact storage instance."""
        return self._artifact_storage

    @property
    def feature_flag_name(self) -> str:
        """Return the feature flag name for this orchestrator."""
        return "enable_orchestrated_ai_ux"

    def _create_failed_result(self, task: UXAnalysisTask, error: str) -> UXAnalysisResult:
        """Create a failed result for a task.

        Args:
            task: The task that failed
            error: Error message

        Returns:
            Failed UXAnalysisResult
        """
        return UXAnalysisResult(
            task_type=task.task_type,
            success=False,
            error=error,
        )

    async def _execute_task(self, task: UXAnalysisTask) -> UXAnalysisResult:
        """Execute a single UX analysis task.

        Args:
            task: The task to execute

        Returns:
            UXAnalysisResult from the task
        """
        if self._ai_ux_service is None:
            return UXAnalysisResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured",
            )

        try:
            if task.task_type == "persona_analysis":
                result = await self._ai_ux_service.analyze_persona(
                    user_id=task.user_id,
                    **task.data,
                )
            elif task.task_type == "disclosure_analysis":
                result = await self._ai_ux_service.analyze_disclosure(
                    user_id=task.user_id,
                    **task.data,
                )
            elif task.task_type == "error_analysis":
                result = await self._ai_ux_service.analyze_error(
                    user_id=task.user_id,
                    **task.data,
                )
            else:
                return UXAnalysisResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown task type: {task.task_type}",
                )

            # Try to extract result dict
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"result": result}

            return UXAnalysisResult(
                task_type=task.task_type,
                success=True,
                result=result_dict,
            )

        except Exception as e:
            logger.exception(f"Error executing {task.task_type}: {e}")
            return UXAnalysisResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    def synthesize(self, results: list[UXAnalysisResult]) -> dict[str, Any]:
        """Synthesize cross-service insights from analysis results.

        Combines results from persona, disclosure, and error analyses
        to generate cross-cutting insights.

        Args:
            results: List of UXAnalysisResult to synthesize

        Returns:
            Dict containing cross_insights and individual results
        """
        cross_insights: list[str] = []

        # Extract successful results by type
        results_by_type: dict[str, UXAnalysisResult] = {}
        for result in results:
            if result.success:
                results_by_type[result.task_type] = result

        # Generate cross-insights based on result combinations
        persona_result = results_by_type.get("persona_analysis")
        disclosure_result = results_by_type.get("disclosure_analysis")
        error_result = results_by_type.get("error_analysis")

        # Persona + Disclosure insight
        if persona_result and disclosure_result:
            persona_data = persona_result.result or {}
            disclosure_data = disclosure_result.result or {}

            detected_persona = persona_data.get("detected_persona", "unknown")
            current_level = disclosure_data.get("current_level", "unknown")
            recommended_level = disclosure_data.get("recommended_level", "unknown")

            if current_level != recommended_level:
                cross_insights.append(
                    f"User persona '{detected_persona}' suggests disclosure level should be "
                    f"'{recommended_level}' (currently '{current_level}')"
                )

        # Persona + Error insight
        if persona_result and error_result:
            persona_data = persona_result.result or {}
            confidence = persona_data.get("confidence", 0)

            if confidence < 0.5:
                cross_insights.append(
                    "Low persona confidence may indicate user is exploring - consider more forgiving error recovery"
                )

        return {
            "cross_insights": cross_insights,
            "results": {r.task_type: r.result for r in results if r.success},
            "failed_analyses": [r.task_type for r in results if not r.success],
        }

    async def run_composite_analysis(
        self,
        user_id: str,
        session_id: str,
        include_persona: bool = True,
        include_disclosure: bool = True,
        include_error: bool = False,
        persona_data: dict[str, Any] | None = None,
        disclosure_data: dict[str, Any] | None = None,
        error_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run composite analysis with parallel execution.

        This is the main entry point for orchestrated AI UX analysis.
        Runs selected analyses in parallel and synthesizes results.

        Args:
            user_id: User identifier
            session_id: Session identifier
            include_persona: Include persona analysis
            include_disclosure: Include disclosure analysis
            include_error: Include error analysis
            persona_data: Data for persona analysis
            disclosure_data: Data for disclosure analysis
            error_data: Data for error analysis

        Returns:
            Composite analysis result with cross-insights
        """
        tasks: list[UXAnalysisTask] = []

        if include_persona:
            tasks.append(
                UXAnalysisTask(
                    task_type="persona_analysis",
                    user_id=user_id,
                    data=persona_data or {},
                )
            )

        if include_disclosure:
            tasks.append(
                UXAnalysisTask(
                    task_type="disclosure_analysis",
                    user_id=user_id,
                    data=disclosure_data or {},
                )
            )

        if include_error:
            tasks.append(
                UXAnalysisTask(
                    task_type="error_analysis",
                    user_id=user_id,
                    data=error_data or {},
                )
            )

        # Execute tasks in parallel
        results = await self.execute(tasks)

        # Synthesize cross-insights
        synthesis = self.synthesize(results)

        return {
            "user_id": user_id,
            "session_id": session_id,
            "analyses": synthesis["results"],
            "cross_insights": synthesis["cross_insights"],
            "failed_analyses": synthesis["failed_analyses"],
        }
