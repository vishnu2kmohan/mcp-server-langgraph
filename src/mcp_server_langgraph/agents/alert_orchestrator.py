"""
Alert Orchestrator (Phase 12)

Orchestrates multi-alert correlation and root cause analysis using parallel execution.

Migrates the sequential alert recommendations to the orchestrator-worker pattern
for improved performance on multi-alert incidents:

Before:
  analyze_alerts()
    → correlate [deterministic]
    → root_cause [LLM]
    → remediation [LLM]
    → sequential

After:
  AlertOrchestrator
    → CorrelationAgent [deterministic, fast]
    → RootCauseAgent [LLM, per alert group]
    → RemediationAgent [LLM, per root cause]
    → PatternDetectionAgent [rule-based]
    → Synthesizer

Usage:
    from mcp_server_langgraph.agents.alert_orchestrator import (
        AlertOrchestrator,
        AlertAnalysisTask,
        AlertAnalysisResult,
    )

    orchestrator = AlertOrchestrator(
        correlation_engine=engine,
        recommendation_service=service,
    )
    result = await orchestrator.analyze_alerts(
        alert_ids=["alert-1", "alert-2"],
        include_correlation=True,
        include_root_cause=True,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Supported analysis types for alert orchestration
ALERT_ANALYSIS_TYPES = frozenset({
    "correlation",
    "root_cause",
    "remediation",
    "pattern_detection",
})


@dataclass
class AlertAnalysisTask(BaseTask):
    """Task definition for alert analysis.

    Extends BaseTask with alert context for analysis operations.

    Attributes:
        task_type: Type of analysis (correlation, root_cause, remediation, pattern_detection)
        alert_ids: List of alert identifiers to analyze
        data: Optional data payload for the analysis
    """

    alert_ids: list[str] = field(default_factory=list)


@dataclass
class AlertAnalysisResult(BaseResult):
    """Result from an alert analysis task.

    Extends BaseResult for alert analysis results. Inherits all base fields.

    Attributes:
        task_type: Type of analysis performed
        success: Whether the analysis succeeded
        result: Analysis result data (if successful)
        error: Error message (if failed)
    """

    pass


class AlertOrchestrator(BaseOrchestrator[AlertAnalysisTask, AlertAnalysisResult]):
    """Orchestrates parallel alert analysis tasks.

    Coordinates correlation, root cause, remediation, and pattern detection
    tasks in parallel, then synthesizes results.

    Inherits from BaseOrchestrator to use common parallel execution patterns.
    """

    def __init__(
        self,
        correlation_engine: Any | None = None,
        recommendation_service: Any | None = None,
        enable_metrics: bool = True,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize Alert Orchestrator.

        Args:
            correlation_engine: Optional AlertCorrelationEngine for correlation
            recommendation_service: Optional AIRecommendationService for LLM analysis
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
        """
        super().__init__(
            enable_metrics=enable_metrics,
            cost_tracker=cost_tracker,
            session_id=session_id,
        )
        self._correlation_engine = correlation_engine
        self._recommendation_service = recommendation_service

    @property
    def correlation_engine(self) -> Any | None:
        """Get the correlation engine instance."""
        return self._correlation_engine

    @property
    def recommendation_service(self) -> Any | None:
        """Get the recommendation service instance."""
        return self._recommendation_service

    @property
    def feature_flag_name(self) -> str:
        """Return the feature flag name for this orchestrator."""
        return "enable_orchestrated_alert_analysis"

    def _create_failed_result(
        self, task: AlertAnalysisTask, error: str
    ) -> AlertAnalysisResult:
        """Create a failed result for a task.

        Args:
            task: The task that failed
            error: Error message

        Returns:
            Failed AlertAnalysisResult
        """
        return AlertAnalysisResult(
            task_type=task.task_type,
            success=False,
            error=error,
        )

    async def _execute_task(self, task: AlertAnalysisTask) -> AlertAnalysisResult:
        """Execute a single alert analysis task.

        Args:
            task: The task to execute

        Returns:
            AlertAnalysisResult from the task
        """
        try:
            if task.task_type == "correlation":
                return await self._execute_correlation(task)
            elif task.task_type == "root_cause":
                return await self._execute_root_cause(task)
            elif task.task_type == "remediation":
                return await self._execute_remediation(task)
            elif task.task_type == "pattern_detection":
                return await self._execute_pattern_detection(task)
            else:
                return AlertAnalysisResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown task type: {task.task_type}",
                )
        except Exception as e:
            logger.exception(f"Error executing {task.task_type}: {e}")
            return AlertAnalysisResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _execute_correlation(self, task: AlertAnalysisTask) -> AlertAnalysisResult:
        """Execute correlation analysis (deterministic, fast)."""
        if self._correlation_engine is None:
            return AlertAnalysisResult(
                task_type="correlation",
                success=True,
                result={"groups": [], "note": "No correlation engine configured"},
            )

        # Correlation is typically synchronous/fast
        groups = self._correlation_engine.correlate(task.alert_ids)
        return AlertAnalysisResult(
            task_type="correlation",
            success=True,
            result={"groups": groups},
        )

    async def _execute_root_cause(self, task: AlertAnalysisTask) -> AlertAnalysisResult:
        """Execute root cause analysis (LLM-powered)."""
        if self._recommendation_service is None:
            return AlertAnalysisResult(
                task_type="root_cause",
                success=False,
                error="Recommendation service not configured",
            )

        result = await self._recommendation_service.analyze_root_cause(
            alert_ids=task.alert_ids,
            **task.data,
        )

        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"result": result}

        return AlertAnalysisResult(
            task_type="root_cause",
            success=True,
            result=result_dict,
        )

    async def _execute_remediation(self, task: AlertAnalysisTask) -> AlertAnalysisResult:
        """Execute remediation analysis (LLM-powered)."""
        if self._recommendation_service is None:
            return AlertAnalysisResult(
                task_type="remediation",
                success=False,
                error="Recommendation service not configured",
            )

        result = await self._recommendation_service.generate_remediation(
            alert_ids=task.alert_ids,
            **task.data,
        )

        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"result": result}

        return AlertAnalysisResult(
            task_type="remediation",
            success=True,
            result=result_dict,
        )

    async def _execute_pattern_detection(self, task: AlertAnalysisTask) -> AlertAnalysisResult:
        """Execute pattern detection (rule-based)."""
        if self._correlation_engine is None:
            return AlertAnalysisResult(
                task_type="pattern_detection",
                success=True,
                result={"patterns": []},
            )

        if hasattr(self._correlation_engine, "detect_patterns"):
            patterns = self._correlation_engine.detect_patterns(task.alert_ids)
        else:
            patterns = []

        return AlertAnalysisResult(
            task_type="pattern_detection",
            success=True,
            result={"patterns": patterns},
        )

    def detect_patterns(self, alert_ids: list[str]) -> list[dict[str, Any]]:
        """Detect patterns across alert groups.

        Synchronous method for rule-based pattern detection.

        Args:
            alert_ids: List of alert identifiers

        Returns:
            List of detected patterns
        """
        if self._correlation_engine is None:
            return []

        if hasattr(self._correlation_engine, "detect_patterns"):
            return cast(list[dict[str, Any]], self._correlation_engine.detect_patterns(alert_ids))

        return []

    def synthesize(self, results: list[AlertAnalysisResult]) -> dict[str, Any]:
        """Synthesize correlation summary from analysis results.

        Combines results from correlation, root cause, and remediation
        into a unified summary.

        Args:
            results: List of AlertAnalysisResult to synthesize

        Returns:
            Dict containing correlation_summary and individual results
        """
        correlation_summary: dict[str, Any] = {
            "total_results": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
        }

        # Extract results by type
        results_by_type: dict[str, AlertAnalysisResult] = {}
        for result in results:
            if result.success:
                results_by_type[result.task_type] = result

        # Build correlation summary from results
        if "correlation" in results_by_type:
            correlation_result = results_by_type["correlation"].result or {}
            groups = correlation_result.get("groups", [])
            correlation_summary["alert_groups"] = len(groups) if isinstance(groups, list) else 0

        if "root_cause" in results_by_type:
            root_cause_result = results_by_type["root_cause"].result or {}
            correlation_summary["root_cause"] = root_cause_result.get("root_cause", "Unknown")

        if "pattern_detection" in results_by_type:
            pattern_result = results_by_type["pattern_detection"].result or {}
            patterns = pattern_result.get("patterns", [])
            correlation_summary["patterns_detected"] = len(patterns) if isinstance(patterns, list) else 0

        return {
            "correlation_summary": correlation_summary,
            "results": {r.task_type: r.result for r in results if r.success},
            "failed_analyses": [r.task_type for r in results if not r.success],
        }

    async def analyze_alerts(
        self,
        alert_ids: list[str],
        include_correlation: bool = True,
        include_root_cause: bool = True,
        include_remediation: bool = False,
        include_pattern_detection: bool = False,
        correlation_data: dict[str, Any] | None = None,
        root_cause_data: dict[str, Any] | None = None,
        remediation_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run comprehensive alert analysis with parallel execution.

        This is the main entry point for orchestrated alert analysis.
        Runs selected analyses in parallel and synthesizes results.

        Args:
            alert_ids: List of alert identifiers to analyze
            include_correlation: Include correlation analysis
            include_root_cause: Include root cause analysis
            include_remediation: Include remediation analysis
            include_pattern_detection: Include pattern detection
            correlation_data: Data for correlation analysis
            root_cause_data: Data for root cause analysis
            remediation_data: Data for remediation analysis

        Returns:
            Comprehensive analysis result with correlation summary
        """
        tasks: list[AlertAnalysisTask] = []

        if include_correlation:
            tasks.append(
                AlertAnalysisTask(
                    task_type="correlation",
                    alert_ids=alert_ids,
                    data=correlation_data or {},
                )
            )

        if include_root_cause:
            tasks.append(
                AlertAnalysisTask(
                    task_type="root_cause",
                    alert_ids=alert_ids,
                    data=root_cause_data or {},
                )
            )

        if include_remediation:
            tasks.append(
                AlertAnalysisTask(
                    task_type="remediation",
                    alert_ids=alert_ids,
                    data=remediation_data or {},
                )
            )

        if include_pattern_detection:
            tasks.append(
                AlertAnalysisTask(
                    task_type="pattern_detection",
                    alert_ids=alert_ids,
                )
            )

        # Execute tasks in parallel
        results = await self.execute(tasks)

        # Synthesize summary
        synthesis = self.synthesize(results)

        return {
            "alert_ids": alert_ids,
            "analyses": synthesis["results"],
            "correlation_summary": synthesis["correlation_summary"],
            "failed_analyses": synthesis["failed_analyses"],
        }
