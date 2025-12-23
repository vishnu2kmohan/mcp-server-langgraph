"""
Subagent

Worker agents with isolated context windows for parallel task execution.

Each subagent has its own clean context to prevent cross-contamination
of information between parallel tasks.

Usage:
    from mcp_server_langgraph.agents.subagent import Subagent

    subagent = Subagent(task_id="task-1", instructions="Analyze...")
    result = await subagent.execute()

    # With LLM integration:
    from mcp_server_langgraph.llm.factory import LLMFactory
    llm = LLMFactory()
    subagent = Subagent(task_id="task-1", instructions="...", llm_factory=llm)
    result = await subagent.execute()
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from mcp_server_langgraph.agents.metrics import record_subagent_execution

from mcp_server_langgraph.core.feature_flags import feature_gated

# HITL Confidence Thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.7  # Require approval below this
AUTO_APPROVE_THRESHOLD = 0.9  # Auto-approve at or above this

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage, BaseMessage


@runtime_checkable
class LLMProtocol(Protocol):
    """Protocol for LLM factories that support ainvoke."""

    async def ainvoke(
        self,
        messages: list[BaseMessage | dict[str, Any]],
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM with messages."""
        ...


class SubagentStatus(str, Enum):
    """Status of a subagent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubagentResult(BaseModel):
    """Result from a subagent execution."""

    task_id: str = Field(description="ID of the task")
    success: bool = Field(description="Whether execution succeeded")
    output: Any | None = Field(default=None, description="Execution output")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")
    artifacts: list[str] = Field(
        default_factory=list,
        description="List of artifact names produced",
    )
    # HITL Confidence Tracking Fields
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) for the result",
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether human approval is required before proceeding",
    )
    approval_reason: str | None = Field(
        default=None,
        description="Reason why approval is required (if applicable)",
    )
    # Cost Tracking Fields (Phase 5)
    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of input tokens consumed",
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of output tokens generated",
    )
    model: str | None = Field(
        default=None,
        description="Model used for execution (for cost calculation)",
    )


class Subagent:
    """Worker agent with isolated context window.

    Subagents execute delegated tasks in parallel with their own
    clean context, preventing context pollution between tasks.
    """

    def __init__(
        self,
        task_id: str,
        instructions: str,
        model: str | None = None,
        llm_factory: LLMProtocol | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize a subagent.

        Args:
            task_id: Unique identifier for this task
            instructions: Detailed instructions for the task
            model: Optional model override (uses tier default if not set)
            llm_factory: Optional LLM factory for execution
            system_prompt: Optional system prompt for LLM context
        """
        self.task_id = task_id
        self.instructions = instructions
        self.model = model
        self.llm_factory = llm_factory
        self.system_prompt = system_prompt
        self.status = SubagentStatus.PENDING
        self.context_window: list[BaseMessage | dict[str, Any]] = []  # Clean context
        self.created_at = datetime.now(UTC)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

    def add_to_context(self, message: dict[str, Any]) -> None:
        """Add a message to the context window.

        Args:
            message: Message to add to context
        """
        self.context_window.append(message)

    def clear_context(self) -> None:
        """Clear the context window."""
        self.context_window.clear()

    @feature_gated("enable_multi_agent_orchestration", "Multi-Agent Orchestration")
    async def execute(self) -> SubagentResult:
        """Execute the subagent task.

        Returns:
            SubagentResult with execution outcome

        Raises:
            FeatureDisabledError: If multi-agent orchestration is disabled

        If an LLM factory is provided, the task will be executed using the LLM.
        Otherwise, a placeholder result is returned.
        """
        import time

        start_time = time.perf_counter()
        self.status = SubagentStatus.RUNNING
        self.started_at = datetime.now(UTC)
        error_type = None

        try:
            # Add system prompt to context if provided
            if self.system_prompt:
                self.add_to_context(
                    {
                        "role": "system",
                        "content": self.system_prompt,
                    }
                )

            # Add instructions to context
            self.add_to_context(
                {
                    "role": "user",
                    "content": self.instructions,
                }
            )

            # Execute with LLM if factory is provided
            if self.llm_factory is not None:
                response = await self.llm_factory.ainvoke(self.context_window)
                output = response.content
            else:
                # Placeholder result when no LLM is configured
                output = f"Executed task: {self.task_id}"

            duration_ms = (time.perf_counter() - start_time) * 1000

            self.status = SubagentStatus.COMPLETED
            self.completed_at = datetime.now(UTC)

            # Record success metrics
            record_subagent_execution(
                task_id=self.task_id,
                model=self.model or "unknown",
                duration_ms=duration_ms,
                success=True,
            )

            return SubagentResult(
                task_id=self.task_id,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.status = SubagentStatus.FAILED
            self.completed_at = datetime.now(UTC)
            error_type = type(e).__name__

            # Record failure metrics
            record_subagent_execution(
                task_id=self.task_id,
                model=self.model or "unknown",
                duration_ms=duration_ms,
                success=False,
                error_type=error_type,
            )

            return SubagentResult(
                task_id=self.task_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def cancel(self) -> None:
        """Cancel the subagent execution."""
        if self.status == SubagentStatus.RUNNING:
            self.status = SubagentStatus.CANCELLED
            self.completed_at = datetime.now(UTC)
