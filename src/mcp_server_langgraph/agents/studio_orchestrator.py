"""
Studio Orchestrator (HybridShell AI Enhancement)

Unified orchestrator for ALL Studio AI capabilities.

Consolidates UXOrchestrator + HybridShellOrchestrator for:
- 8 task categories: UX, SESSION, CONVERSATION, CANVAS, DIAGRAM, TRACE, HITL, COMMAND
- 25+ task types across all categories
- Cross-category insights synthesis
- Feature flag for gradual rollout
- Cost tracking per category
- Persona-aware permission checks

Benefits:
- Single cost tracking pool across all AI features
- Unified resilience patterns
- Cross-category insights synthesis
- Simplified dependency injection
- Consistent observability

Usage:
    from mcp_server_langgraph.agents.studio_orchestrator import (
        StudioOrchestrator,
        StudioTask,
        StudioResult,
        TaskCategory,
    )

    orchestrator = StudioOrchestrator(ai_ux_service=service)
    result = await orchestrator.analyze(
        user_id="user-123",
        session_id="session-456",
        include_ux=True,
        include_session=True,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class TaskCategory(str, Enum):
    """Categories for task routing and cost allocation.

    8 categories covering all Studio AI capabilities:
    - UX: Persona, disclosure, error, nudges
    - SESSION: Summarize, group, similarity
    - CONVERSATION: Intent, context, goal
    - CANVAS: Artifact, code, diff
    - DIAGRAM: Analyze, to-code
    - TRACE: Summarize, anomaly
    - HITL: Risk assess, decision history
    - COMMAND: Command palette, inline suggestions
    """

    UX = "ux"
    SESSION = "session"
    CONVERSATION = "conversation"
    CANVAS = "canvas"
    DIAGRAM = "diagram"
    TRACE = "trace"
    HITL = "hitl"
    COMMAND = "command"


# Supported task types for Studio orchestration
STUDIO_TASK_TYPES = frozenset({
    # UX (migrated from UXOrchestrator)
    "persona_analysis",
    "disclosure_analysis",
    "error_analysis",
    "nudge_recommendation",
    "onboarding_personalization",
    "empty_state_suggestions",
    "metrics_insights",
    # Session Intelligence
    "session_summarize",
    "session_group",
    "session_similarity",
    # Conversation Intelligence
    "intent_detect",
    "context_optimize",
    "goal_track",
    # Canvas Intelligence
    "artifact_suggest_type",
    "code_analyze",
    "diff_explain",
    # Diagram Intelligence
    "diagram_analyze",
    "diagram_to_code",
    # Trace Intelligence
    "trace_summarize",
    "trace_anomaly",
    # HITL Intelligence
    "risk_assess",
    "decision_history",
    # Command Intelligence
    "command_interpret",
    "inline_suggest",
    "ai_edit_generate",
    # UX Intelligence (extended)
    "nav_prediction",
    "contextual_help",
    "learning_path",
    # Cost Intelligence
    "cost_project",
    "token_predict",
})

# Map task types to categories
TASK_TYPE_TO_CATEGORY: dict[str, TaskCategory] = {
    # UX category
    "persona_analysis": TaskCategory.UX,
    "disclosure_analysis": TaskCategory.UX,
    "error_analysis": TaskCategory.UX,
    "nudge_recommendation": TaskCategory.UX,
    "onboarding_personalization": TaskCategory.UX,
    "empty_state_suggestions": TaskCategory.UX,
    "metrics_insights": TaskCategory.UX,
    "nav_prediction": TaskCategory.UX,
    "contextual_help": TaskCategory.UX,
    "learning_path": TaskCategory.UX,
    # Session category
    "session_summarize": TaskCategory.SESSION,
    "session_group": TaskCategory.SESSION,
    "session_similarity": TaskCategory.SESSION,
    # Conversation category
    "intent_detect": TaskCategory.CONVERSATION,
    "context_optimize": TaskCategory.CONVERSATION,
    "goal_track": TaskCategory.CONVERSATION,
    # Canvas category
    "artifact_suggest_type": TaskCategory.CANVAS,
    "code_analyze": TaskCategory.CANVAS,
    "diff_explain": TaskCategory.CANVAS,
    # Diagram category
    "diagram_analyze": TaskCategory.DIAGRAM,
    "diagram_to_code": TaskCategory.DIAGRAM,
    # Trace category (includes cost intelligence)
    "trace_summarize": TaskCategory.TRACE,
    "trace_anomaly": TaskCategory.TRACE,
    "cost_project": TaskCategory.TRACE,
    "token_predict": TaskCategory.TRACE,
    # HITL category
    "risk_assess": TaskCategory.HITL,
    "decision_history": TaskCategory.HITL,
    # Command category
    "command_interpret": TaskCategory.COMMAND,
    "inline_suggest": TaskCategory.COMMAND,
    "ai_edit_generate": TaskCategory.COMMAND,
}


@dataclass
class StudioTask(BaseTask):
    """Unified task type for all Studio AI capabilities.

    Extends BaseTask with category, user context, and persona for RBAC.

    Attributes:
        category: Task category for routing and cost allocation
        task_type: Specific task type within the category
        user_id: User identifier for the analysis
        session_id: Optional session identifier
        persona: Optional sub-persona for permission checks
        data: Optional data payload for the task
    """

    category: TaskCategory = field(default=TaskCategory.UX)
    user_id: str = ""
    session_id: str | None = None
    persona: str | None = None


@dataclass
class StudioResult(BaseResult):
    """Result from a Studio AI task.

    Extends BaseResult for Studio analysis results. Inherits all base fields.

    Attributes:
        task_type: Type of task performed
        success: Whether the task succeeded
        result: Task result data (if successful)
        error: Error message (if failed)
    """

    pass


class StudioOrchestrator(BaseOrchestrator[StudioTask, StudioResult]):
    """Unified orchestrator for ALL Studio AI capabilities.

    Consolidates UXOrchestrator + HybridShellOrchestrator to:
    - Single cost tracking pool across all AI features
    - Unified resilience patterns
    - Cross-category insights synthesis
    - Simplified dependency injection
    - Consistent observability

    Coordinates 8 task categories in parallel, then synthesizes
    results into cross-category insights.

    Inherits from BaseOrchestrator to use common parallel execution patterns.
    """

    def __init__(
        self,
        ai_ux_service: Any | None = None,
        llm_factory: Any | None = None,
        artifact_storage: Any | None = None,
        enable_metrics: bool = True,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize Studio Orchestrator.

        Args:
            ai_ux_service: Optional AIUXService instance for UX analysis methods
            llm_factory: Optional LLMFactory for direct LLM calls
            artifact_storage: Optional ArtifactStorage for intermediate results
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
        """
        super().__init__(
            enable_metrics=enable_metrics,
            cost_tracker=cost_tracker,
            session_id=session_id,
        )
        self._ai_ux_service = ai_ux_service
        self._llm_factory = llm_factory
        self._artifact_storage = artifact_storage

    @property
    def ai_ux_service(self) -> Any | None:
        """Get the AI UX service instance."""
        return self._ai_ux_service

    @property
    def llm_factory(self) -> Any | None:
        """Get the LLM factory instance."""
        return self._llm_factory

    @property
    def artifact_storage(self) -> Any | None:
        """Get the artifact storage instance."""
        return self._artifact_storage

    @property
    def feature_flag_name(self) -> str:
        """Return the feature flag name for this orchestrator."""
        return "enable_studio_ai"

    def _create_failed_result(
        self, task: StudioTask, error: str
    ) -> StudioResult:
        """Create a failed result for a task.

        Args:
            task: The task that failed
            error: Error message

        Returns:
            Failed StudioResult
        """
        return StudioResult(
            task_type=task.task_type,
            success=False,
            error=error,
        )

    async def _execute_task(self, task: StudioTask) -> StudioResult:
        """Execute a single Studio AI task.

        Routes tasks to appropriate handlers based on category.

        Args:
            task: The task to execute

        Returns:
            StudioResult from the task
        """
        try:
            # Validate task type is supported
            if task.task_type not in STUDIO_TASK_TYPES:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown task type: {task.task_type}",
                )

            # Use category from task (has default value of UX)
            category = task.category

            # Route to appropriate handler using dispatch map
            handlers = {
                TaskCategory.UX: self._handle_ux_task,
                TaskCategory.SESSION: self._handle_session_task,
                TaskCategory.CONVERSATION: self._handle_conversation_task,
                TaskCategory.CANVAS: self._handle_canvas_task,
                TaskCategory.DIAGRAM: self._handle_diagram_task,
                TaskCategory.TRACE: self._handle_trace_task,
                TaskCategory.HITL: self._handle_hitl_task,
                TaskCategory.COMMAND: self._handle_command_task,
            }

            handler = handlers.get(category)
            if handler is None:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unsupported category: {category}",
                )

            return await handler(task)

        except Exception as e:
            logger.exception(f"Error executing {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_ux_task(self, task: StudioTask) -> StudioResult:
        """Handle UX-related tasks (migrated from UXOrchestrator).

        Args:
            task: The UX task to execute

        Returns:
            StudioResult from the UX task
        """
        if self._ai_ux_service is None:
            return StudioResult(
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
            elif task.task_type == "nudge_recommendation":
                result = await self._ai_ux_service.recommend_nudge(
                    user_id=task.user_id,
                    **task.data,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unsupported UX task type: {task.task_type}",
                )

            # Extract result dict
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"result": result}

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result_dict,
            )

        except Exception as e:
            logger.exception(f"Error in UX task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_session_task(self, task: StudioTask) -> StudioResult:
        """Handle Session Intelligence tasks.

        Supports three session task types:
        - session_summarize: Generate AI summary of a session
        - session_group: Group sessions by topic/project
        - session_similarity: Find sessions similar to a given session

        Args:
            task: The session task to execute

        Returns:
            StudioResult from the session task
        """
        if self._ai_ux_service is None:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured for session tasks",
            )

        try:
            result: dict[str, Any] | None = None

            if task.task_type == "session_summarize":
                # Generate AI summary for a single session
                result = await self._ai_ux_service.summarize_session(
                    session_id=task.session_id,
                    **task.data,
                )
            elif task.task_type == "session_group":
                # Group multiple sessions by topic/project
                session_ids = task.data.get("session_ids", [])
                result = await self._ai_ux_service.group_sessions(
                    session_ids=session_ids,
                    user_id=task.user_id,
                    **{k: v for k, v in task.data.items() if k != "session_ids"},
                )
            elif task.task_type == "session_similarity":
                # Find sessions similar to the given session
                result = await self._ai_ux_service.find_similar_sessions(
                    session_id=task.session_id,
                    user_id=task.user_id,
                    **task.data,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unsupported session task type: {task.task_type}",
                )

            # Convert result to dict if needed
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"result": result}

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result_dict,
            )

        except Exception as e:
            logger.exception(f"Error in session task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_conversation_task(self, task: StudioTask) -> StudioResult:
        """Handle Conversation Intelligence tasks.

        Supports the following task types:
        - intent_detect: Classify user intent from input text
        - context_optimize: Suggest context trimming when approaching token limit
        - goal_track: Track session goals across multiple messages

        Args:
            task: The conversation task to execute

        Returns:
            StudioResult from the conversation task
        """
        if self._ai_ux_service is None:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured for conversation tasks",
            )

        try:
            result: dict[str, Any] | None = None

            if task.task_type == "intent_detect":
                result = await self._ai_ux_service.detect_intent(
                    query=task.data.get("query", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "context_optimize":
                result = await self._ai_ux_service.optimize_context(
                    current_tokens=task.data.get("current_tokens", 0),
                    max_tokens=task.data.get("max_tokens", 128000),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "goal_track":
                result = await self._ai_ux_service.track_goal(
                    user_id=task.user_id,
                    session_id=task.session_id,
                    **task.data,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown conversation task type: {task.task_type}",
                )

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result or {},
            )

        except Exception as e:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_canvas_task(self, task: StudioTask) -> StudioResult:
        """Handle Canvas Intelligence tasks.

        Supports the following task types:
        - artifact_suggest_type: Suggest optimal artifact type for content
        - code_analyze: Analyze code quality and complexity
        - diff_explain: Explain changes between versions in natural language

        Args:
            task: The canvas task to execute

        Returns:
            StudioResult from the canvas task
        """
        if self._ai_ux_service is None:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured for canvas tasks",
            )

        try:
            result: dict[str, Any] | None = None

            if task.task_type == "artifact_suggest_type":
                result = await self._ai_ux_service.suggest_artifact_type(
                    content=task.data.get("content", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "code_analyze":
                result = await self._ai_ux_service.analyze_code(
                    code=task.data.get("code", ""),
                    language=task.data.get("language"),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "diff_explain":
                result = await self._ai_ux_service.explain_diff(
                    old_content=task.data.get("old_content", ""),
                    new_content=task.data.get("new_content", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown canvas task type: {task.task_type}",
                )

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result or {},
            )

        except Exception as e:
            logger.exception(f"Error in canvas task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_diagram_task(self, task: StudioTask) -> StudioResult:
        """Handle Diagram Intelligence tasks.

        Supports the following task types:
        - diagram_analyze: Validate and analyze Mermaid diagrams
        - diagram_to_code: Generate code from flowchart/sequence diagrams

        Args:
            task: The diagram task to execute

        Returns:
            StudioResult from the diagram task
        """
        if self._ai_ux_service is None:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured for diagram tasks",
            )

        try:
            result: dict[str, Any] | None = None

            if task.task_type == "diagram_analyze":
                result = await self._ai_ux_service.analyze_diagram(
                    diagram_code=task.data.get("diagram_code", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "diagram_to_code":
                result = await self._ai_ux_service.diagram_to_code(
                    diagram_code=task.data.get("diagram_code", ""),
                    target_language=task.data.get("target_language", "typescript"),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown diagram task type: {task.task_type}",
                )

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result or {},
            )

        except Exception as e:
            logger.exception(f"Error in diagram task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_trace_task(self, task: StudioTask) -> StudioResult:
        """Handle Trace Intelligence tasks.

        Supports the following task types:
        - trace_summarize: Generate one-sentence summary of agent execution
        - trace_anomaly: Detect bottlenecks and anomalies in execution
        - cost_project: Estimate real-time session costs
        - token_predict: Forecast token usage and optimization opportunities

        Args:
            task: The trace task to execute

        Returns:
            StudioResult from the trace task
        """
        if self._ai_ux_service is None:
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error="AI UX service not configured for trace tasks",
            )

        try:
            result: dict[str, Any] | None = None

            if task.task_type == "trace_summarize":
                result = await self._ai_ux_service.summarize_trace(
                    trace_id=task.data.get("trace_id", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "trace_anomaly":
                result = await self._ai_ux_service.detect_trace_anomalies(
                    trace_id=task.data.get("trace_id", ""),
                    user_id=task.user_id,
                    session_id=task.session_id,
                )
            elif task.task_type == "cost_project":
                result = await self._ai_ux_service.project_cost(
                    session_id=task.data.get("session_id", task.session_id),
                    user_id=task.user_id,
                )
            elif task.task_type == "token_predict":
                result = await self._ai_ux_service.predict_tokens(
                    session_id=task.data.get("session_id", task.session_id),
                    user_id=task.user_id,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown trace task type: {task.task_type}",
                )

            return StudioResult(
                task_type=task.task_type,
                success=True,
                result=result or {},
            )

        except Exception as e:
            logger.exception(f"Error in trace task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_hitl_task(self, task: StudioTask) -> StudioResult:
        """Handle HITL Intelligence tasks.

        Task types:
        - risk_assess: AI-generated risk score for pending actions
        - decision_history: Show how user decided similar requests before

        Args:
            task: The HITL task to execute

        Returns:
            StudioResult from the HITL task
        """
        try:
            if task.task_type == "risk_assess":
                result = await self._ai_ux_service.assess_risk(
                    request_id=task.data.get("request_id", ""),
                    action_type=task.data.get("action_type", ""),
                    parameters=task.data.get("parameters", {}),
                    user_id=task.user_id,
                )
                return StudioResult(
                    task_type=task.task_type,
                    success=True,
                    result=result,
                )
            elif task.task_type == "decision_history":
                result = await self._ai_ux_service.get_decision_history(
                    action_type=task.data.get("action_type", ""),
                    persona=task.data.get("persona"),
                    time_range_days=task.data.get("time_range_days"),
                    user_id=task.user_id,
                )
                return StudioResult(
                    task_type=task.task_type,
                    success=True,
                    result=result,
                )
            else:
                return StudioResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown HITL task type: {task.task_type}",
                )

        except Exception as e:
            logger.exception(f"Error in HITL task {task.task_type}: {e}")
            return StudioResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _handle_command_task(self, task: StudioTask) -> StudioResult:
        """Handle Command Intelligence tasks.

        Args:
            task: The command task to execute

        Returns:
            StudioResult from the command task
        """
        # Placeholder - to be implemented with LLM calls
        return StudioResult(
            task_type=task.task_type,
            success=True,
            result={"status": "placeholder", "message": "Command task placeholder"},
        )

    def synthesize(self, results: list[StudioResult]) -> dict[str, Any]:
        """Synthesize cross-category insights from analysis results.

        Combines results from all categories to generate cross-cutting insights.

        Args:
            results: List of StudioResult to synthesize

        Returns:
            Dict containing cross_insights and individual results
        """
        cross_insights: list[str] = []

        # Extract successful results by type
        results_by_type: dict[str, StudioResult] = {}
        for result in results:
            if result.success:
                results_by_type[result.task_type] = result

        # Generate cross-insights based on result combinations
        persona_result = results_by_type.get("persona_analysis")
        session_result = results_by_type.get("session_summarize")
        intent_result = results_by_type.get("intent_detect")

        # Persona + Session insight
        if persona_result and session_result:
            persona_data = persona_result.result or {}
            detected_persona = persona_data.get("detected_persona", "unknown")
            cross_insights.append(
                f"User persona '{detected_persona}' combined with session context for personalized experience"
            )

        # Session + Intent insight
        if session_result and intent_result:
            cross_insights.append(
                "Session history combined with detected intent for context-aware suggestions"
            )

        # Persona + Disclosure insight (from UXOrchestrator)
        disclosure_result = results_by_type.get("disclosure_analysis")
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

        return {
            "cross_insights": cross_insights,
            "results": {r.task_type: r.result for r in results if r.success},
            "failed_analyses": [r.task_type for r in results if not r.success],
        }

    async def analyze(
        self,
        user_id: str,
        session_id: str,
        include_ux: bool = False,
        include_session: bool = False,
        include_conversation: bool = False,
        include_canvas: bool = False,
        include_diagram: bool = False,
        include_trace: bool = False,
        include_hitl: bool = False,
        include_command: bool = False,
        persona: str | None = None,
        ux_data: dict[str, Any] | None = None,
        session_data: dict[str, Any] | None = None,
        conversation_data: dict[str, Any] | None = None,
        canvas_data: dict[str, Any] | None = None,
        diagram_data: dict[str, Any] | None = None,
        trace_data: dict[str, Any] | None = None,
        hitl_data: dict[str, Any] | None = None,
        command_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run unified analysis with parallel execution.

        This is the main entry point for orchestrated Studio AI analysis.
        Runs selected analyses in parallel and synthesizes results.

        Args:
            user_id: User identifier
            session_id: Session identifier
            include_ux: Include UX analysis (persona, disclosure, etc.)
            include_session: Include session analysis
            include_conversation: Include conversation analysis
            include_canvas: Include canvas analysis
            include_diagram: Include diagram analysis
            include_trace: Include trace analysis
            include_hitl: Include HITL analysis
            include_command: Include command analysis
            persona: Optional sub-persona for permission checks
            ux_data: Data for UX analysis
            session_data: Data for session analysis
            conversation_data: Data for conversation analysis
            canvas_data: Data for canvas analysis
            diagram_data: Data for diagram analysis
            trace_data: Data for trace analysis
            hitl_data: Data for HITL analysis
            command_data: Data for command analysis

        Returns:
            Unified analysis result with cross-insights
        """
        tasks: list[StudioTask] = []

        if include_ux:
            tasks.append(
                StudioTask(
                    category=TaskCategory.UX,
                    task_type="persona_analysis",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=ux_data or {},
                )
            )

        if include_session:
            tasks.append(
                StudioTask(
                    category=TaskCategory.SESSION,
                    task_type="session_summarize",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=session_data or {},
                )
            )

        if include_conversation:
            tasks.append(
                StudioTask(
                    category=TaskCategory.CONVERSATION,
                    task_type="intent_detect",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=conversation_data or {},
                )
            )

        if include_canvas:
            tasks.append(
                StudioTask(
                    category=TaskCategory.CANVAS,
                    task_type="artifact_suggest_type",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=canvas_data or {},
                )
            )

        if include_diagram:
            tasks.append(
                StudioTask(
                    category=TaskCategory.DIAGRAM,
                    task_type="diagram_analyze",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=diagram_data or {},
                )
            )

        if include_trace:
            tasks.append(
                StudioTask(
                    category=TaskCategory.TRACE,
                    task_type="trace_summarize",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=trace_data or {},
                )
            )

        if include_hitl:
            tasks.append(
                StudioTask(
                    category=TaskCategory.HITL,
                    task_type="risk_assess",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=hitl_data or {},
                )
            )

        if include_command:
            tasks.append(
                StudioTask(
                    category=TaskCategory.COMMAND,
                    task_type="command_interpret",
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    data=command_data or {},
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
