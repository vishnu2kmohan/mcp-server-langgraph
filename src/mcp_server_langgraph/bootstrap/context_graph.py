"""
Context Graph Bootstrap Module.

Provides initialization for context graph components:
- DecisionEmitter singleton
- PostgresDecisionTraceRepository
- Decision retention scheduler

Follows existing pattern from bootstrap/storage.py, bootstrap/skills.py.

Reference: ADR-0101 Context Graphs
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.repositories.decision_trace import (
        DecisionTraceRepositoryBase,
    )


@dataclass
class ContextGraphState:
    """Context graph component state.

    Holds references to all initialized context graph components
    and provides cleanup method for graceful shutdown.
    """

    emitter: "DecisionEmitter | None" = None
    repository: "DecisionTraceRepositoryBase | None" = None
    retention_task: asyncio.Task[None] | None = None

    async def cleanup(self) -> None:
        """Cleanup in reverse order.

        1. Cancel retention scheduler
        2. Stop emitter (flushes pending traces)
        """
        if self.retention_task:
            self.retention_task.cancel()
            try:
                await self.retention_task
            except asyncio.CancelledError:
                pass
            logger.debug("Decision retention task cancelled")

        if self.emitter:
            await self.emitter.stop()


async def init_context_graph(settings: "Settings") -> ContextGraphState | None:
    """Initialize context graph if enabled.

    Creates and wires all context graph components:
    - Repository with async session factory
    - Emitter with background persistence
    - Retention scheduler for cleanup

    Args:
        settings: Application settings

    Returns:
        ContextGraphState if enabled, None if disabled
    """
    if not feature_flags.enable_context_graph:
        logger.debug("Context graph disabled")
        return None

    from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter
    from mcp_server_langgraph.core.dependencies import (
        get_async_session,
        set_decision_trace_repository,
    )
    from mcp_server_langgraph.repositories.decision_trace import (
        PostgresDecisionTraceRepository,
    )
    from mcp_server_langgraph.schedulers.decision_retention import (
        start_retention_scheduler,
    )

    # Create decision trace repository with DI session factory
    repository = PostgresDecisionTraceRepository(session_factory=get_async_session)

    # Register repository singleton for GDPR access (ADR-0101 Phase 11)
    set_decision_trace_repository(repository)

    # NOTE: LangGraph Execution Trace repository is now initialized separately
    # in bootstrap/agent_execution_tracing.py with its own feature flag
    # (FF_ENABLE_AGENT_EXECUTION_TRACING). This separation ensures:
    # 1. Agent execution traces can be enabled independently of context graph
    # 2. Clear terminology: Decision Traces (here) vs Agent Execution Traces
    # See: Triple-AI Diagnosis Plan - Fix 3

    # Create and start emitter
    emitter = DecisionEmitter(repository)
    await emitter.start()

    # Start retention scheduler
    retention_task = await start_retention_scheduler(repository)

    logger.info("Context graph initialized")
    return ContextGraphState(
        emitter=emitter,
        repository=repository,
        retention_task=retention_task,
    )
