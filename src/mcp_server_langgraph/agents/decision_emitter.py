"""
Decision Trace Emitter for Context Graphs.

Singleton pattern - one instance per app lifecycle.
Uses async queue for non-blocking persistence.

Key Features:
- Feature flag gating (enable_context_graph)
- Sampling rate support for high-volume production
- Sequence number generation per session
- Async queue for non-blocking persistence
- OTEL correlation (trace_id, span_id)
- Field truncation for storage efficiency

Reference: ADR-0101 Context Graphs, Foundation Capital article
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from opentelemetry import trace

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.decision_trace import (
        DecisionTraceRepositoryBase,
    )

# Truncation limits
MAX_QUERY_LENGTH = 500
MAX_RATIONALE_LENGTH = 1000


@dataclass
class DecisionContext:
    """Context for a decision trace.

    Contains identifiers for correlating decisions with sessions,
    workflows, projects, organizations, and users.
    """

    run_id: str
    session_id: str
    workflow_id: str | None
    project_id: str | None
    organization_id: str
    user_id: str


class DecisionEmitter:
    """Emits decision traces to storage.

    Singleton - created once in bootstrap, accessed via app.state.
    Uses async queue to avoid blocking hot path.

    Example:
        emitter = DecisionEmitter(repository)
        await emitter.start()

        trace_id = await emitter.emit(
            context=DecisionContext(...),
            decision_type="routing",
            decision_stage="action",
            query_text="How do I deploy?",
            chosen_action="call_deploy_tool",
            confidence=0.95,
            rationale="User wants deployment",
        )

        await emitter.stop()
    """

    def __init__(self, repository: "DecisionTraceRepositoryBase") -> None:
        """Initialize emitter with repository.

        Args:
            repository: Repository for persisting traces
        """
        self._repository = repository
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._sequence_counters: dict[str, int] = {}  # session_id -> seq

    async def start(self) -> None:
        """Start background persistence worker."""
        self._worker_task = asyncio.create_task(
            self._persistence_worker(),
            name="decision_trace_worker",
        )
        logger.info("DecisionEmitter started")

    async def stop(self) -> None:
        """Stop worker gracefully, flush pending."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("DecisionEmitter stopped")

    def _should_sample(self) -> bool:
        """Check if this trace should be sampled."""
        rate = feature_flags.context_graph_sampling_rate
        return rate >= 1.0 or random.random() < rate

    def _get_next_sequence(self, session_id: str) -> int:
        """Get next sequence number for session."""
        seq = self._sequence_counters.get(session_id, 0)
        self._sequence_counters[session_id] = seq + 1
        return seq

    async def emit(
        self,
        context: DecisionContext,
        decision_type: str,
        decision_stage: str,
        query_text: str,
        chosen_action: str,
        confidence: float,
        rationale: str,
        *,
        available_options: list[str] | None = None,
        selected_items: list[str] | None = None,
        policy_version: str | None = None,
    ) -> str | None:
        """Emit a decision trace.

        Args:
            context: Decision context with identifiers
            decision_type: Type of decision (routing, tool_selection, etc.)
            decision_stage: Pipeline stage (context_gathering, action, etc.)
            query_text: User query (will be truncated)
            chosen_action: Action/tool that was chosen
            confidence: Confidence score (0.0-1.0)
            rationale: Why this decision (will be truncated)
            available_options: Options considered (max 20)
            selected_items: Items selected (max 20)
            policy_version: Policy version string

        Returns:
            trace_id if emitted, None if disabled/sampled out
        """
        if not feature_flags.enable_context_graph:
            return None

        if not self._should_sample():
            return None

        trace_id = str(uuid4())

        # Get OTEL context for correlation
        current_span = trace.get_current_span()
        span_ctx = current_span.get_span_context()

        # Truncate large fields
        query_truncated = query_text[:MAX_QUERY_LENGTH] if query_text else ""
        rationale_truncated = rationale[:MAX_RATIONALE_LENGTH] if rationale else ""

        trace_data = {
            "trace_id": trace_id,
            "run_id": context.run_id,
            "session_id": context.session_id,
            "workflow_id": context.workflow_id,
            "project_id": context.project_id,
            "organization_id": context.organization_id,
            "user_id": context.user_id,
            "timestamp": datetime.now(UTC),
            "sequence_number": self._get_next_sequence(context.session_id),
            "decision_type": decision_type,
            "decision_stage": decision_stage,
            "query_text": query_truncated,
            "chosen_action": chosen_action,
            "confidence": confidence,
            "rationale": rationale_truncated,
            "available_options": available_options[:20] if available_options else None,
            "selected_items": selected_items[:20] if selected_items else None,
            "policy_version": policy_version,
            "embedding_text": f"{query_truncated} {rationale_truncated}",
            "otel_trace_id": (
                format(span_ctx.trace_id, "032x") if span_ctx.is_valid else None
            ),
            "otel_span_id": (
                format(span_ctx.span_id, "016x") if span_ctx.is_valid else None
            ),
        }

        if feature_flags.context_graph_async_persistence:
            await self._queue.put(trace_data)
        else:
            await self._repository.create(trace_data)

        # Add span attribute for correlation
        current_span.set_attribute("decision.trace_id", trace_id)

        return trace_id

    async def _persistence_worker(self) -> None:
        """Background worker for batched persistence."""
        batch: list[dict] = []
        batch_size = feature_flags.context_graph_batch_size

        while True:
            try:
                # Collect batch with timeout
                while len(batch) < batch_size:
                    try:
                        item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break

                # Persist batch
                if batch:
                    count = await self._repository.create_batch(batch)
                    logger.debug(f"Persisted {count} decision traces")
                    batch = []

            except asyncio.CancelledError:
                # Flush on shutdown
                if batch:
                    await self._repository.create_batch(batch)
                    logger.info(f"Flushed {len(batch)} traces on shutdown")
                raise
            except Exception as e:
                logger.error(f"Decision trace persistence error: {e}")
                batch = []  # Drop batch on error
