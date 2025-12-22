"""
Orchestrator

Lead agent that decomposes complex tasks and delegates to subagents.

Implements the orchestrator-worker pattern with:
- Task decomposition into subtasks
- Parallel subagent execution
- Artifact-based synthesis
- Cross-vendor verification

Usage:
    from mcp_server_langgraph.agents.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    decomposition = orchestrator.decompose_task("Research...", num_subtasks=3)
    results = await orchestrator.execute(decomposition)
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker
    from mcp_server_langgraph.agents.definition import AgentDefinition

from mcp_server_langgraph.agents.artifacts import ArtifactStorage
from mcp_server_langgraph.agents.coordinator import Coordinator
from mcp_server_langgraph.agents.cost_models import BudgetStatus, CostAlert
from mcp_server_langgraph.agents.metrics import (
    record_artifact_storage,
    record_orchestrator_execution,
    record_synthesis_operation,
)
from mcp_server_langgraph.agents.model_selector import ModelSelector
from mcp_server_langgraph.agents.subagent import Subagent, SubagentResult
from mcp_server_langgraph.core.feature_flags import feature_flags, feature_gated


class Subtask(BaseModel):
    """A subtask in a task decomposition."""

    task_id: str = Field(description="Unique subtask identifier")
    title: str = Field(description="Short title for the subtask")
    instructions: str = Field(description="Detailed delegation instructions")
    complexity: str = Field(
        default="simple",
        description="Complexity level (simple, complicated, complex)",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs this subtask depends on",
    )


class TaskDecomposition(BaseModel):
    """Decomposition of a complex task into subtasks."""

    original_task: str = Field(description="Original task description")
    subtasks: list[Subtask] = Field(description="List of subtasks")
    synthesis_instructions: str = Field(
        default="",
        description="Instructions for synthesizing subtask results",
    )


class Orchestrator:
    """Lead agent for multi-agent orchestration.

    Decomposes complex tasks into subtasks, delegates to subagents,
    and synthesizes results using artifact storage.
    """

    def __init__(
        self,
        model_selector: ModelSelector | None = None,
        artifact_storage: ArtifactStorage | None = None,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            model_selector: Optional model selector (creates default if None)
            artifact_storage: Optional shared artifact storage
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
        """
        self.model_selector = model_selector or ModelSelector()
        self.artifact_storage = artifact_storage or ArtifactStorage()
        self.coordinator = Coordinator(artifact_storage=self.artifact_storage)
        self.cost_tracker = cost_tracker
        self.session_id = session_id

    @feature_gated("enable_multi_agent_orchestration", "Multi-Agent Orchestration")
    def decompose_task(
        self,
        task: str,
        num_subtasks: int = 3,
    ) -> TaskDecomposition:
        """Decompose a complex task into subtasks.

        Args:
            task: Original task description
            num_subtasks: Number of subtasks to create

        Returns:
            TaskDecomposition with subtasks

        Raises:
            FeatureDisabledError: If multi-agent orchestration is disabled

        Note:
            In production, this would use the orchestrator model
            to intelligently decompose the task. This provides
            the structure for that integration.
        """
        subtasks = []

        for i in range(num_subtasks):
            subtask = Subtask(
                task_id=f"subtask-{i+1}",
                title=f"Subtask {i+1}",
                instructions=f"Execute part {i+1} of: {task}",
                complexity="simple" if i < num_subtasks - 1 else "complicated",
            )
            subtasks.append(subtask)

        return TaskDecomposition(
            original_task=task,
            subtasks=subtasks,
            synthesis_instructions=f"Synthesize results from {num_subtasks} subtasks into final output.",
        )

    def scale_effort(self, task: str) -> int:
        """Determine number of subagents based on task complexity.

        Args:
            task: Task description

        Returns:
            Recommended number of subagents (1 to max_subagents)
        """
        # Simple heuristic based on task length and keywords
        words = task.lower().split()

        # Complex keywords that suggest more subagents
        complex_keywords = {
            "comprehensive", "thorough", "detailed", "analyze",
            "research", "investigate", "compare", "multiple",
        }

        complexity_score = sum(1 for w in words if w in complex_keywords)
        base_count = max(1, min(len(words) // 20, 5))

        # Use configurable max_subagents from feature flags
        max_limit = feature_flags.max_subagents
        return max(1, min(base_count + complexity_score, max_limit))

    def get_session_cost(self) -> Decimal:
        """Get current session cost.

        Returns:
            Current session cost as Decimal, or 0 if no tracker configured
        """
        if self.cost_tracker is None or self.session_id is None:
            return Decimal("0")
        return self.cost_tracker.get_session_cost(self.session_id)

    def check_budget(self) -> CostAlert:
        """Check budget status for the current session.

        Returns:
            CostAlert with current budget status
        """
        if self.cost_tracker is None or self.session_id is None:
            return CostAlert(
                status=BudgetStatus.OK,
                message="No cost tracking configured",
                current_cost=Decimal("0"),
                limit=Decimal("0"),
                threshold_percentage=0.0,
                session_id=self.session_id or "",
            )
        return self.cost_tracker.check_budget(self.session_id)

    @feature_gated("enable_multi_agent_orchestration", "Multi-Agent Orchestration")
    async def execute(
        self,
        decomposition: TaskDecomposition,
    ) -> list[SubagentResult]:
        """Execute a task decomposition.

        Creates subagents for each subtask, executes them in parallel,
        and collects results.

        Args:
            decomposition: Task decomposition with subtasks

        Returns:
            List of SubagentResult from all subtasks

        Raises:
            FeatureDisabledError: If multi-agent orchestration is disabled
            BudgetExceededError: If session budget is exceeded
        """
        from mcp_server_langgraph.core.exceptions import BudgetExceededError

        start_time = time.perf_counter()

        # Check budget before execution (if cost tracking enabled)
        if self.cost_tracker is not None and feature_flags.enable_cost_tracking:
            alert = self.check_budget()
            if alert.status == BudgetStatus.EXCEEDED:
                raise BudgetExceededError(
                    message=f"Session budget exceeded: {alert.current_cost} > {alert.limit}",
                    metadata={
                        "session_id": self.session_id,
                        "current": str(alert.current_cost),
                        "limit": str(alert.limit),
                    },
                )

        # Create subagents for each subtask
        for subtask in decomposition.subtasks:
            model = self.model_selector.select_model(subtask.complexity)
            subagent = Subagent(
                task_id=subtask.task_id,
                instructions=subtask.instructions,
                model=model,
            )
            self.coordinator.register_subagent(subagent)

        # Execute all subagents in parallel
        results = await self.coordinator.execute_all()

        # Track costs for each result (if cost tracking enabled)
        if self.cost_tracker is not None and feature_flags.enable_cost_tracking:
            for result in results:
                if result.input_tokens > 0 or result.output_tokens > 0:
                    model_name = result.model or "claude-opus-4-5-20251101"
                    self.cost_tracker.track_usage(
                        model=model_name,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        task_id=result.task_id,
                        session_id=self.session_id,
                    )

        # Store results as artifacts for synthesis
        successful_count = 0
        for result in results:
            if result.success and result.output:
                successful_count += 1
                # Store artifact
                self.artifact_storage.store(
                    task_id=result.task_id,
                    name="result",
                    data=result.output,
                )
                # Record artifact storage metrics
                output_data = str(result.output)
                record_artifact_storage(
                    task_id=result.task_id,
                    artifact_name="result",
                    size_bytes=len(output_data.encode("utf-8")),
                    operation="store",
                )

        duration_ms = (time.perf_counter() - start_time) * 1000
        task_count = len(decomposition.subtasks)
        success = successful_count > 0

        # Record orchestrator execution metrics
        record_orchestrator_execution(
            task_count=task_count,
            successful_count=successful_count,
            duration_ms=duration_ms,
            success=success,
        )

        return results

    async def synthesize(
        self,
        decomposition: TaskDecomposition,
        results: list[SubagentResult],
    ) -> Any:
        """Synthesize subtask results into final output.

        Args:
            decomposition: Original task decomposition
            results: Results from subtask execution

        Returns:
            Synthesized final result

        Note:
            In production, this would use the orchestrator model
            to intelligently synthesize results from artifacts.
        """
        start_time = time.perf_counter()
        error_type = None

        try:
            # Collect all successful outputs
            successful_outputs = [
                r.output for r in results
                if r.success and r.output
            ]

            synthesis_result = {
                "original_task": decomposition.original_task,
                "subtask_count": len(decomposition.subtasks),
                "successful_count": len(successful_outputs),
                "outputs": successful_outputs,
                "synthesis": f"Synthesized {len(successful_outputs)} subtask results",
            }

            duration_ms = (time.perf_counter() - start_time) * 1000
            success = True

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            success = False
            error_type = type(e).__name__
            successful_outputs = []
            synthesis_result = None
            raise

        finally:
            # Record synthesis metrics
            record_synthesis_operation(
                input_count=len(results),
                successful_inputs=len(successful_outputs),
                duration_ms=duration_ms,
                success=success,
                error_type=error_type,
            )

        return synthesis_result

    def get_verifier_model(self) -> str:
        """Get model for cross-vendor verification.

        Returns:
            Model identifier for verification
        """
        return self.model_selector.select_verifier("auto")

    @feature_gated("enable_sdk_agent_definition", "SDK AgentDefinition")
    async def execute_definition(
        self,
        agent: AgentDefinition,
        task_id: str,
    ) -> SubagentResult:
        """Execute an AgentDefinition as a subagent.

        Claude Agent SDK Integration:
        This method bridges the SDK's AgentDefinition pattern with
        the existing Subagent infrastructure, enabling simpler
        declarative agent configuration.

        Args:
            agent: AgentDefinition specifying the agent configuration
            task_id: Unique identifier for this execution

        Returns:
            SubagentResult with execution outcome

        Raises:
            FeatureDisabledError: If SDK AgentDefinition is disabled

        Example:
            agent = AgentDefinition(
                name="code_reviewer",
                description="Reviews code for issues",
                prompt="You are a code reviewer...",
                model="sonnet"
            )
            result = await orchestrator.execute_definition(agent, "task-123")
        """
        # Convert AgentDefinition to Subagent configuration
        config = agent.to_subagent_config(task_id)

        # Create and execute Subagent
        subagent = Subagent(
            task_id=config["task_id"],
            instructions=config["instructions"],
            model=config.get("model"),
            system_prompt=config.get("system_prompt"),
        )

        return await subagent.execute()

    async def execute_with_hitl(
        self,
        decomposition: TaskDecomposition,
        threshold: float = 0.7,
        on_approval_required: Any | None = None,
    ) -> list[SubagentResult]:
        """Execute a task decomposition with Human-in-the-Loop checkpoints.

        Executes subtasks and marks low-confidence results as requiring
        human approval before proceeding. Optionally calls a callback
        when approval is needed.

        Args:
            decomposition: Task decomposition with subtasks
            threshold: Confidence threshold (0-1). Below this requires approval.
            on_approval_required: Optional async callback for approval requests.
                Receives dict with task_id, confidence, threshold, and result.

        Returns:
            List of SubagentResult with requires_approval set for low-confidence

        Example:
            async def handle_approval(request):
                # Send to WebSocket for user approval
                await ws.send(request)

            results = await orchestrator.execute_with_hitl(
                decomposition,
                threshold=0.7,
                on_approval_required=handle_approval,
            )
        """
        # Check if HITL is enabled via feature flags
        hitl_enabled = feature_flags.enable_agent_hitl

        # Execute all subtasks (reuse existing execute logic)
        results = await self.execute(decomposition)

        # If HITL is disabled, return results as-is
        if not hitl_enabled:
            return results

        # Process each result for confidence-based approval
        processed_results: list[SubagentResult] = []

        for result in results:
            # Check if confidence is below threshold
            if result.confidence < threshold:
                # Mark as requiring approval
                confidence_pct = f"{result.confidence:.0%}"
                threshold_pct = f"{threshold:.0%}"

                approval_reason = (
                    f"Confidence {confidence_pct} is below threshold {threshold_pct}. "
                    f"Human approval required."
                )

                # Create updated result with approval fields set
                result = SubagentResult(
                    task_id=result.task_id,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration_ms=result.duration_ms,
                    artifacts=result.artifacts,
                    confidence=result.confidence,
                    requires_approval=True,
                    approval_reason=approval_reason,
                )

                # Call callback if provided
                if on_approval_required is not None:
                    approval_request = {
                        "task_id": result.task_id,
                        "confidence": result.confidence,
                        "threshold": threshold,
                        "result": result,
                        "reason": approval_reason,
                    }
                    await on_approval_required(approval_request)

            processed_results.append(result)

        return processed_results
