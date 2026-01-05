"""Execution Mode Selector for ADR-0092.

Determines the optimal execution mode based on task characteristics,
tool/skill requirements, risk levels, and other factors.

The selector implements a decision tree that considers:
- Tool and skill counts
- Task complexity and risk
- Exploration and multi-step requirements
- Determinism and batch processing needs
- Human approval and clarification requirements
- External dependencies

Usage:
    from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
    from mcp_server_langgraph.core.execution_modes import ExecutionMode

    selector = ExecutionModeSelector()
    mode = selector.select(
        tool_count=3,
        task_complexity="complicated",
        requires_exploration=True,
    )
    # Returns ExecutionMode.REACT

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from mcp_server_langgraph.core.execution_modes import ExecutionMode


class ExecutionModeSelector:
    """Selects the optimal execution mode based on task characteristics.

    The selector uses a decision tree that prioritizes:
    1. ORCHESTRATOR: For high-risk, complex tasks or when approval/clarification needed
    2. REACT: For exploration and multi-step reasoning tasks
    3. PROGRAMMATIC: For batch processing and deterministic execution
    4. TOOL_CALLING: Default when tools are present
    5. PURE_LLM: When no tools or skills are needed

    Decision Priority (highest to lowest):
    - Approval/clarification required → ORCHESTRATOR
    - Complex + high risk → ORCHESTRATOR
    - External dependencies + complex → ORCHESTRATOR
    - Exploration required → REACT
    - Multi-step required → REACT
    - Batch processing or determinism → PROGRAMMATIC
    - Tools present → TOOL_CALLING
    - No tools/skills → PURE_LLM
    """

    def select(
        self,
        tool_count: int = 0,
        skill_count: int = 0,
        task_complexity: str = "simple",
        risk_level: str = "low",
        requires_exploration: bool = False,
        requires_multi_step: bool = False,
        requires_determinism: bool = False,
        requires_batch_processing: bool = False,
        context_budget: str = "normal",  # noqa: S107
        latency_requirement: str = "normal",
        requires_approval: bool = False,
        requires_clarification: bool = False,
        has_external_dependencies: bool = False,
    ) -> ExecutionMode:
        """Select the optimal execution mode based on task characteristics.

        Args:
            tool_count: Number of tools available/needed
            skill_count: Number of skills available/needed
            task_complexity: Task complexity level (simple, complicated, complex)
            risk_level: Risk level (low, medium, high)
            requires_exploration: Whether task needs exploration/discovery
            requires_multi_step: Whether multi-step reasoning is needed
            requires_determinism: Whether deterministic execution is required
            requires_batch_processing: Whether batch processing is needed
            token_budget: Token budget constraint (tight, normal, generous)
            latency_requirement: Latency requirement (low, normal, high)
            requires_approval: Whether human approval is required
            requires_clarification: Whether clarification from user is needed
            has_external_dependencies: Whether task has external service dependencies

        Returns:
            The optimal ExecutionMode for the task characteristics.
        """
        # Priority 1: ORCHESTRATOR for human-in-the-loop requirements
        if requires_approval or requires_clarification:
            return ExecutionMode.ORCHESTRATOR

        # Priority 2: ORCHESTRATOR for complex high-risk tasks
        if task_complexity == "complex" and risk_level == "high":
            return ExecutionMode.ORCHESTRATOR

        # Priority 3: ORCHESTRATOR for complex tasks with external dependencies
        if task_complexity == "complex" and has_external_dependencies:
            return ExecutionMode.ORCHESTRATOR

        # Priority 4: REACT for exploration needs
        if requires_exploration:
            return ExecutionMode.REACT

        # Priority 5: REACT for multi-step reasoning
        if requires_multi_step:
            return ExecutionMode.REACT

        # Priority 6: PROGRAMMATIC for deterministic execution
        if requires_determinism:
            return ExecutionMode.PROGRAMMATIC

        # Priority 7: PROGRAMMATIC for batch processing
        if requires_batch_processing and not requires_exploration:
            return ExecutionMode.PROGRAMMATIC

        # Priority 8: TOOL_CALLING when tools or skills are present
        if tool_count > 0 or skill_count > 0:
            return ExecutionMode.TOOL_CALLING

        # Default: PURE_LLM when no tools or special requirements
        return ExecutionMode.PURE_LLM
