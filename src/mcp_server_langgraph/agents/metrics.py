"""
Agents Metrics

OpenTelemetry metrics for multi-agent orchestration operations.

Tracks:
- Orchestrator execution (task decomposition, synthesis)
- Subagent execution (per task, per model)
- Model selection (tier, vendor, fallback)
- Cross-vendor verification
- Artifact storage operations

Usage:
    from mcp_server_langgraph.agents.metrics import (
        record_orchestrator_execution,
        record_subagent_execution,
        record_model_selection,
    )

    record_orchestrator_execution(task_count=3, successful_count=3, duration_ms=1500)
"""

from __future__ import annotations

import logging

from opentelemetry import metrics

logger = logging.getLogger(__name__)

# Get OpenTelemetry meter
meter = metrics.get_meter("mcp_server_langgraph.agents")

# Orchestrator metrics
orchestrator_execution_counter = meter.create_counter(
    name="agent.orchestrator.execution.count",
    description="Total orchestrator executions",
    unit="1",
)

orchestrator_execution_duration_histogram = meter.create_histogram(
    name="agent.orchestrator.execution.duration",
    description="Orchestrator execution duration in milliseconds",
    unit="ms",
)

orchestrator_task_counter = meter.create_counter(
    name="agent.orchestrator.tasks.count",
    description="Total tasks processed by orchestrator",
    unit="1",
)

# Subagent metrics
subagent_execution_counter = meter.create_counter(
    name="agent.subagent.execution.count",
    description="Total subagent executions",
    unit="1",
)

subagent_execution_duration_histogram = meter.create_histogram(
    name="agent.subagent.execution.duration",
    description="Subagent execution duration in milliseconds",
    unit="ms",
)

subagent_error_counter = meter.create_counter(
    name="agent.subagent.errors.count",
    description="Total subagent execution errors",
    unit="1",
)

# Model selection metrics
model_selection_counter = meter.create_counter(
    name="agent.model.selection.count",
    description="Total model selections",
    unit="1",
)

model_fallback_counter = meter.create_counter(
    name="agent.model.fallback.count",
    description="Total model fallback selections",
    unit="1",
)

# Cross-vendor verification metrics
verification_counter = meter.create_counter(
    name="agent.verification.count",
    description="Total cross-vendor verifications",
    unit="1",
)

verification_same_vendor_counter = meter.create_counter(
    name="agent.verification.same_vendor.count",
    description="Total same-vendor verification fallbacks",
    unit="1",
)

# Artifact storage metrics
artifact_operation_counter = meter.create_counter(
    name="agent.artifact.operation.count",
    description="Total artifact storage operations",
    unit="1",
)

artifact_size_histogram = meter.create_histogram(
    name="agent.artifact.size",
    description="Artifact size in bytes",
    unit="By",
)

# Synthesis metrics
synthesis_counter = meter.create_counter(
    name="agent.synthesis.count",
    description="Total synthesis operations",
    unit="1",
)

synthesis_duration_histogram = meter.create_histogram(
    name="agent.synthesis.duration",
    description="Synthesis duration in milliseconds",
    unit="ms",
)

synthesis_error_counter = meter.create_counter(
    name="agent.synthesis.errors.count",
    description="Total synthesis errors",
    unit="1",
)


def record_orchestrator_execution(
    task_count: int,
    successful_count: int,
    duration_ms: float,
    success: bool,
) -> None:
    """Record orchestrator execution metrics.

    Args:
        task_count: Number of tasks in decomposition
        successful_count: Number of successfully completed tasks
        duration_ms: Total execution duration in milliseconds
        success: Whether overall execution succeeded
    """
    attributes = {
        "success": str(success).lower(),
    }

    orchestrator_execution_counter.add(1, attributes)
    orchestrator_execution_duration_histogram.record(duration_ms, attributes)

    # Track task counts
    orchestrator_task_counter.add(
        task_count,
        {"status": "total"},
    )
    orchestrator_task_counter.add(
        successful_count,
        {"status": "successful"},
    )
    if task_count > successful_count:
        orchestrator_task_counter.add(
            task_count - successful_count,
            {"status": "failed"},
        )

    logger.debug(
        "Recorded orchestrator execution",
        extra={
            "task_count": task_count,
            "successful_count": successful_count,
            "duration_ms": duration_ms,
            "success": success,
        },
    )


def record_subagent_execution(
    task_id: str,
    model: str,
    duration_ms: float,
    success: bool,
    error_type: str | None = None,
) -> None:
    """Record subagent execution metrics.

    Args:
        task_id: Unique task identifier
        model: Model used for execution
        duration_ms: Execution duration in milliseconds
        success: Whether execution succeeded
        error_type: Optional error type if failed
    """
    # Extract vendor from model name
    if model.startswith("gemini"):
        vendor = "google"
    elif model.startswith("claude"):
        vendor = "anthropic"
    elif model.startswith("gpt") or model.startswith("o3"):
        vendor = "openai"
    else:
        vendor = "unknown"

    attributes = {
        "model": model,
        "vendor": vendor,
        "success": str(success).lower(),
    }

    subagent_execution_counter.add(1, attributes)
    subagent_execution_duration_histogram.record(duration_ms, attributes)

    if not success and error_type:
        subagent_error_counter.add(
            1,
            {
                "error_type": error_type,
                "model": model,
                "vendor": vendor,
            },
        )

    logger.debug(
        "Recorded subagent execution",
        extra={
            "task_id": task_id,
            "model": model,
            "duration_ms": duration_ms,
            "success": success,
            "error_type": error_type,
        },
    )


def record_model_selection(
    tier: str,
    vendor: str,
    model: str,
    is_fallback: bool = False,
) -> None:
    """Record model selection metrics.

    Args:
        tier: Complexity tier (simple, complicated, complex)
        vendor: Vendor name (google, anthropic, openai)
        model: Selected model identifier
        is_fallback: Whether this is a fallback selection
    """
    attributes = {
        "tier": tier,
        "vendor": vendor,
        "model": model,
    }

    model_selection_counter.add(1, attributes)

    if is_fallback:
        model_fallback_counter.add(
            1,
            {
                "tier": tier,
                "fallback_vendor": vendor,
            },
        )

    logger.debug(
        "Recorded model selection",
        extra={
            "tier": tier,
            "vendor": vendor,
            "model": model,
            "is_fallback": is_fallback,
        },
    )


def record_cross_vendor_verification(
    primary_vendor: str,
    verifier_vendor: str,
    primary_model: str,
    verifier_model: str,
    success: bool,
    same_vendor_fallback: bool = False,
) -> None:
    """Record cross-vendor verification metrics.

    Args:
        primary_vendor: Vendor of primary execution
        verifier_vendor: Vendor of verifier
        primary_model: Model used for primary execution
        verifier_model: Model used for verification
        success: Whether verification succeeded
        same_vendor_fallback: Whether same-vendor fallback was used
    """
    attributes = {
        "primary_vendor": primary_vendor,
        "verifier_vendor": verifier_vendor,
        "success": str(success).lower(),
    }

    verification_counter.add(1, attributes)

    if same_vendor_fallback:
        verification_same_vendor_counter.add(
            1,
            {
                "vendor": primary_vendor,
            },
        )

    logger.debug(
        "Recorded cross-vendor verification",
        extra={
            "primary_vendor": primary_vendor,
            "verifier_vendor": verifier_vendor,
            "primary_model": primary_model,
            "verifier_model": verifier_model,
            "success": success,
            "same_vendor_fallback": same_vendor_fallback,
        },
    )


def record_artifact_storage(
    task_id: str,
    artifact_name: str,
    size_bytes: int,
    operation: str,
) -> None:
    """Record artifact storage operation metrics.

    Args:
        task_id: Task that owns the artifact
        artifact_name: Name of the artifact
        size_bytes: Size of artifact in bytes
        operation: Operation type (store, retrieve)
    """
    attributes = {
        "operation": operation,
    }

    artifact_operation_counter.add(1, attributes)
    artifact_size_histogram.record(size_bytes, attributes)

    logger.debug(
        "Recorded artifact operation",
        extra={
            "task_id": task_id,
            "artifact_name": artifact_name,
            "size_bytes": size_bytes,
            "operation": operation,
        },
    )


def record_synthesis_operation(
    input_count: int,
    successful_inputs: int,
    duration_ms: float,
    success: bool,
    error_type: str | None = None,
) -> None:
    """Record synthesis operation metrics.

    Args:
        input_count: Number of inputs to synthesize
        successful_inputs: Number of successful inputs
        duration_ms: Synthesis duration in milliseconds
        success: Whether synthesis succeeded
        error_type: Optional error type if failed
    """
    attributes = {
        "success": str(success).lower(),
    }

    synthesis_counter.add(1, attributes)
    synthesis_duration_histogram.record(duration_ms, attributes)

    if not success and error_type:
        synthesis_error_counter.add(
            1,
            {
                "error_type": error_type,
            },
        )

    logger.debug(
        "Recorded synthesis operation",
        extra={
            "input_count": input_count,
            "successful_inputs": successful_inputs,
            "duration_ms": duration_ms,
            "success": success,
            "error_type": error_type,
        },
    )


# Cost tracking metrics (Phase 5)
cost_usage_counter = meter.create_counter(
    name="agent.cost.usage.total",
    description="Total cost in dollars",
    unit="$",
)

cost_tokens_counter = meter.create_counter(
    name="agent.cost.tokens.total",
    description="Total tokens processed",
    unit="1",
)

cost_session_gauge = meter.create_up_down_counter(
    name="agent.cost.session.current",
    description="Current session cost in dollars",
    unit="$",
)


def record_cost_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
    session_id: str | None = None,
) -> None:
    """Record cost tracking metrics.

    Args:
        model: Model used for the call
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        total_cost: Total cost in dollars
        session_id: Optional session identifier
    """
    # Extract vendor from model name
    if model.startswith("gemini"):
        vendor = "google"
    elif model.startswith("claude"):
        vendor = "anthropic"
    elif model.startswith("gpt") or model.startswith("o3"):
        vendor = "openai"
    else:
        vendor = "unknown"

    token_attributes = {
        "model": model,
        "vendor": vendor,
    }

    cost_attributes = {
        "model": model,
        "vendor": vendor,
    }
    if session_id:
        cost_attributes["session_id"] = session_id

    # Record token counts
    cost_tokens_counter.add(input_tokens, {"type": "input", **token_attributes})
    cost_tokens_counter.add(output_tokens, {"type": "output", **token_attributes})

    # Record cost (multiply by 10000 to get millicents for precision)
    cost_usage_counter.add(1, cost_attributes)  # Count of calls

    # Record session cost
    if session_id:
        cost_session_gauge.add(total_cost, {"session_id": session_id})

    logger.debug(
        "Recorded cost usage",
        extra={
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": total_cost,
            "session_id": session_id,
        },
    )


# Agent Task metrics (for HITL intervention rate calculation)
# This metric is referenced in alert rules as `agent_task_total` after OTel->Prometheus conversion
agent_task_counter = meter.create_counter(
    name="agent.task",
    description="Total agent tasks processed",
    unit="1",
)

agent_task_duration_histogram = meter.create_histogram(
    name="agent.task.duration",
    description="Agent task duration in milliseconds",
    unit="ms",
)


def record_agent_task(
    agent_name: str,
    task_type: str,
    success: bool,
    duration_ms: float | None = None,
    error_type: str | None = None,
) -> None:
    """Record an agent task execution.

    This metric is used to calculate HITL intervention rate:
        intervention_rate = hitl_requests / agent_tasks

    The OTel counter `agent.task` exports as Prometheus `agent_task_total`.

    Args:
        agent_name: Name of the agent processing the task
        task_type: Type of task (analysis, export, review, synthesis, query)
        success: Whether the task completed successfully
        duration_ms: Optional task duration in milliseconds
        error_type: Optional error type if the task failed
    """
    attributes = {
        "agent_name": agent_name,
        "task_type": task_type,
        "success": str(success).lower(),
    }

    agent_task_counter.add(1, attributes)

    if duration_ms is not None:
        agent_task_duration_histogram.record(
            duration_ms,
            {
                "agent_name": agent_name,
                "task_type": task_type,
                "success": str(success).lower(),
            },
        )

    if not success and error_type:
        # Record error in subagent_error_counter for consistency with existing patterns
        subagent_error_counter.add(
            1,
            {
                "error_type": error_type,
                "agent_name": agent_name,
                "task_type": task_type,
            },
        )

    logger.debug(
        "Recorded agent task",
        extra={
            "agent_name": agent_name,
            "task_type": task_type,
            "success": success,
            "duration_ms": duration_ms,
            "error_type": error_type,
        },
    )


# HITL (Human-in-the-Loop) metrics
hitl_request_counter = meter.create_counter(
    name="agent.hitl.request.count",
    description="Total HITL requests",
    unit="1",
)

hitl_decision_counter = meter.create_counter(
    name="agent.hitl.decision.count",
    description="Total HITL decisions by outcome",
    unit="1",
)

hitl_response_latency_histogram = meter.create_histogram(
    name="agent.hitl.response.latency",
    description="Time from request to user response in seconds",
    unit="s",
)

hitl_confidence_histogram = meter.create_histogram(
    name="agent.hitl.trigger.confidence",
    description="Confidence score that triggered HITL",
    unit="1",
)

hitl_pending_gauge = meter.create_up_down_counter(
    name="agent.hitl.pending.count",
    description="Current pending HITL requests",
    unit="1",
)


def record_hitl_request(
    request_type: str,
    agent_name: str,
    confidence: float,
    trigger_reason: str,
) -> None:
    """Record a new HITL request.

    Args:
        request_type: Type of request (approval, clarification)
        agent_name: Name of the agent requesting HITL
        confidence: Confidence score that triggered the request
        trigger_reason: Reason for HITL (low_confidence, destructive_action, etc.)
    """
    attributes = {
        "request_type": request_type,
        "agent_name": agent_name,
        "trigger_reason": trigger_reason,
    }

    hitl_request_counter.add(1, attributes)
    hitl_confidence_histogram.record(
        confidence,
        {
            "agent_name": agent_name,
            "trigger_reason": trigger_reason,
        },
    )
    hitl_pending_gauge.add(1, {"request_type": request_type})

    logger.debug(
        "Recorded HITL request",
        extra={
            "request_type": request_type,
            "agent_name": agent_name,
            "confidence": confidence,
            "trigger_reason": trigger_reason,
        },
    )


def record_hitl_decision(
    request_type: str,
    agent_name: str,
    decision: str,
    latency_seconds: float,
) -> None:
    """Record user's HITL decision.

    Args:
        request_type: Type of request (approval, clarification)
        agent_name: Name of the agent that requested HITL
        decision: Decision outcome (approved, rejected, timeout)
        latency_seconds: Time from request to decision in seconds
    """
    attributes = {
        "request_type": request_type,
        "decision": decision,
        "agent_name": agent_name,
    }

    hitl_decision_counter.add(1, attributes)
    hitl_response_latency_histogram.record(
        latency_seconds,
        {
            "request_type": request_type,
            "agent_name": agent_name,
        },
    )
    hitl_pending_gauge.add(-1, {"request_type": request_type})

    logger.debug(
        "Recorded HITL decision",
        extra={
            "request_type": request_type,
            "agent_name": agent_name,
            "decision": decision,
            "latency_seconds": latency_seconds,
        },
    )


def increment_hitl_pending(request_type: str) -> None:
    """Increment pending HITL request count.

    Args:
        request_type: Type of request (approval, clarification)
    """
    hitl_pending_gauge.add(1, {"request_type": request_type})
    logger.debug("Incremented HITL pending count", extra={"request_type": request_type})


def decrement_hitl_pending(request_type: str) -> None:
    """Decrement pending HITL request count.

    Args:
        request_type: Type of request (approval, clarification)
    """
    hitl_pending_gauge.add(-1, {"request_type": request_type})
    logger.debug("Decremented HITL pending count", extra={"request_type": request_type})


# HITL Tracing helpers
from contextlib import contextmanager
from typing import Generator

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

# Get tracer for HITL operations
hitl_tracer = trace.get_tracer("mcp_server_langgraph.agents.hitl")


@contextmanager
def hitl_request_span(
    request_type: str,
    request_id: str,
    agent_name: str,
    confidence: float,
    trigger_reason: str,
) -> Generator[Span, None, None]:
    """Create a trace span for HITL request lifecycle.

    Use this context manager to wrap the entire HITL request workflow:
    from request creation to user decision.

    Args:
        request_type: Type of request (approval, clarification)
        request_id: Unique request identifier
        agent_name: Name of the agent requesting HITL
        confidence: Confidence score that triggered the request
        trigger_reason: Reason for HITL

    Yields:
        The active span for additional attribute updates

    Example:
        with hitl_request_span("approval", "req-123", "Research Assistant", 0.65, "low_confidence") as span:
            # ... wait for user decision ...
            add_hitl_decision_to_span(span, "approved", 30.5)
    """
    with hitl_tracer.start_as_current_span("hitl.request") as span:
        span.set_attributes({
            "hitl.request_type": request_type,
            "hitl.request_id": request_id,
            "hitl.agent_name": agent_name,
            "hitl.confidence": confidence,
            "hitl.trigger_reason": trigger_reason,
        })
        yield span


def add_hitl_decision_to_span(
    span: Span,
    decision: str,
    latency_seconds: float,
    reason: str | None = None,
) -> None:
    """Add decision info to the HITL span.

    Args:
        span: The HITL span to update
        decision: Decision outcome (approved, rejected, timeout)
        latency_seconds: Time from request to decision in seconds
        reason: Optional reason for the decision
    """
    span.set_attributes({
        "hitl.decision": decision,
        "hitl.latency_seconds": latency_seconds,
        "hitl.reason": reason or "",
    })

    if decision == "rejected":
        span.set_status(Status(StatusCode.OK, "User rejected"))
    elif decision == "timeout":
        span.set_status(Status(StatusCode.ERROR, "Request timed out"))
    else:
        span.set_status(Status(StatusCode.OK))

    logger.debug(
        "Added HITL decision to span",
        extra={
            "decision": decision,
            "latency_seconds": latency_seconds,
            "reason": reason,
        },
    )


def create_hitl_span(
    request_type: str,
    request_id: str,
    agent_name: str,
    confidence: float,
    trigger_reason: str,
) -> Span:
    """Create a standalone HITL span (non-context manager version).

    Use this when you need to manage span lifecycle manually across
    async boundaries or when the request/response cycle is complex.

    Args:
        request_type: Type of request (approval, clarification)
        request_id: Unique request identifier
        agent_name: Name of the agent requesting HITL
        confidence: Confidence score that triggered the request
        trigger_reason: Reason for HITL

    Returns:
        The created span (caller must call span.end() when done)

    Example:
        span = create_hitl_span("approval", "req-123", "Agent", 0.65, "low_confidence")
        try:
            # ... async operation ...
            add_hitl_decision_to_span(span, "approved", 30.5)
        finally:
            span.end()
    """
    span = hitl_tracer.start_span("hitl.request")
    span.set_attributes({
        "hitl.request_type": request_type,
        "hitl.request_id": request_id,
        "hitl.agent_name": agent_name,
        "hitl.confidence": confidence,
        "hitl.trigger_reason": trigger_reason,
    })
    return span


# =============================================================================
# UX and Alert Orchestrator Metrics (REFACTOR phase)
# =============================================================================

# UX Orchestration metrics
ux_orchestration_counter = meter.create_counter(
    name="agent.ux_orchestration.count",
    description="Total UX orchestration executions",
    unit="1",
)

ux_orchestration_duration_histogram = meter.create_histogram(
    name="agent.ux_orchestration.duration",
    description="UX orchestration duration in milliseconds",
    unit="ms",
)

# Alert Orchestration metrics
alert_orchestration_counter = meter.create_counter(
    name="agent.alert_orchestration.count",
    description="Total alert orchestration executions",
    unit="1",
)

alert_orchestration_duration_histogram = meter.create_histogram(
    name="agent.alert_orchestration.duration",
    description="Alert orchestration duration in milliseconds",
    unit="ms",
)

# Parallel execution metrics
parallel_speedup_histogram = meter.create_histogram(
    name="agent.orchestration.parallel_speedup",
    description="Speedup ratio from parallel execution (sequential/parallel)",
    unit="1",
)

orchestrator_parallel_tasks_histogram = meter.create_histogram(
    name="agent.orchestration.parallel_tasks",
    description="Number of tasks executed in parallel",
    unit="1",
)

# Synthesis metrics (UX-specific)
ux_synthesis_counter = meter.create_counter(
    name="agent.ux_synthesis.count",
    description="Total UX synthesis operations",
    unit="1",
)

ux_cross_insights_histogram = meter.create_histogram(
    name="agent.ux_synthesis.cross_insights",
    description="Number of cross-insights generated",
    unit="1",
)

# Synthesis metrics (Alert-specific)
alert_synthesis_counter = meter.create_counter(
    name="agent.alert_synthesis.count",
    description="Total alert synthesis operations",
    unit="1",
)

alert_correlation_groups_histogram = meter.create_histogram(
    name="agent.alert_synthesis.correlation_groups",
    description="Number of correlation groups found",
    unit="1",
)

# Feature flag check metrics
orchestrator_feature_flag_counter = meter.create_counter(
    name="agent.orchestration.feature_flag_check",
    description="Feature flag checks for orchestrators",
    unit="1",
)


def record_ux_orchestration(
    task_count: int,
    successful_count: int,
    duration_ms: float,
    success: bool,
    analysis_types: list[str] | None = None,
    error_type: str | None = None,
) -> None:
    """Record UX orchestration metrics.

    Args:
        task_count: Number of tasks in the orchestration
        successful_count: Number of successfully completed tasks
        duration_ms: Total execution duration in milliseconds
        success: Whether overall execution succeeded
        analysis_types: List of analysis types performed
        error_type: Optional error type if failed
    """
    attributes = {
        "success": str(success).lower(),
    }

    ux_orchestration_counter.add(1, attributes)
    ux_orchestration_duration_histogram.record(duration_ms, attributes)

    # Track parallel tasks
    orchestrator_parallel_tasks_histogram.record(
        task_count,
        {"orchestrator_type": "ux"},
    )

    if not success and error_type:
        ux_orchestration_counter.add(
            1,
            {
                "success": "false",
                "error_type": error_type,
            },
        )

    logger.debug(
        "Recorded UX orchestration",
        extra={
            "task_count": task_count,
            "successful_count": successful_count,
            "duration_ms": duration_ms,
            "success": success,
            "analysis_types": analysis_types,
            "error_type": error_type,
        },
    )


def record_alert_orchestration(
    alert_count: int,
    task_count: int,
    successful_count: int,
    duration_ms: float,
    success: bool,
    analysis_types: list[str] | None = None,
    correlation_groups: int | None = None,
    error_type: str | None = None,
) -> None:
    """Record alert orchestration metrics.

    Args:
        alert_count: Number of alerts being analyzed
        task_count: Number of analysis tasks
        successful_count: Number of successfully completed tasks
        duration_ms: Total execution duration in milliseconds
        success: Whether overall execution succeeded
        analysis_types: List of analysis types performed
        correlation_groups: Number of correlation groups found
        error_type: Optional error type if failed
    """
    attributes = {
        "success": str(success).lower(),
    }

    alert_orchestration_counter.add(1, attributes)
    alert_orchestration_duration_histogram.record(duration_ms, attributes)

    # Track parallel tasks
    orchestrator_parallel_tasks_histogram.record(
        task_count,
        {"orchestrator_type": "alert"},
    )

    if correlation_groups is not None:
        alert_correlation_groups_histogram.record(
            correlation_groups,
            {"success": str(success).lower()},
        )

    logger.debug(
        "Recorded alert orchestration",
        extra={
            "alert_count": alert_count,
            "task_count": task_count,
            "successful_count": successful_count,
            "duration_ms": duration_ms,
            "success": success,
            "analysis_types": analysis_types,
            "correlation_groups": correlation_groups,
            "error_type": error_type,
        },
    )


def record_parallel_speedup(
    orchestrator_type: str,
    task_count: int,
    parallel_duration_ms: float,
    estimated_sequential_ms: float,
) -> None:
    """Record parallel execution speedup metrics.

    Args:
        orchestrator_type: Type of orchestrator (ux, alert)
        task_count: Number of tasks executed in parallel
        parallel_duration_ms: Actual parallel execution duration
        estimated_sequential_ms: Estimated sequential duration
    """
    if parallel_duration_ms > 0:
        speedup_ratio = estimated_sequential_ms / parallel_duration_ms
    else:
        speedup_ratio = 1.0

    parallel_speedup_histogram.record(
        speedup_ratio,
        {
            "orchestrator_type": orchestrator_type,
            "task_count": str(task_count),
        },
    )

    logger.debug(
        "Recorded parallel speedup",
        extra={
            "orchestrator_type": orchestrator_type,
            "task_count": task_count,
            "parallel_duration_ms": parallel_duration_ms,
            "estimated_sequential_ms": estimated_sequential_ms,
            "speedup_ratio": speedup_ratio,
        },
    )


def record_ux_synthesis(
    input_count: int,
    cross_insights_count: int,
    duration_ms: float,
) -> None:
    """Record UX synthesis metrics.

    Args:
        input_count: Number of analysis results synthesized
        cross_insights_count: Number of cross-insights generated
        duration_ms: Synthesis duration in milliseconds
    """
    ux_synthesis_counter.add(1, {"input_count": str(input_count)})
    ux_cross_insights_histogram.record(cross_insights_count)

    logger.debug(
        "Recorded UX synthesis",
        extra={
            "input_count": input_count,
            "cross_insights_count": cross_insights_count,
            "duration_ms": duration_ms,
        },
    )


def record_alert_synthesis(
    input_count: int,
    correlation_groups: int,
    patterns_detected: int,
    duration_ms: float,
) -> None:
    """Record alert synthesis metrics.

    Args:
        input_count: Number of analysis results synthesized
        correlation_groups: Number of correlation groups
        patterns_detected: Number of patterns detected
        duration_ms: Synthesis duration in milliseconds
    """
    alert_synthesis_counter.add(1, {"input_count": str(input_count)})
    alert_correlation_groups_histogram.record(correlation_groups)

    logger.debug(
        "Recorded alert synthesis",
        extra={
            "input_count": input_count,
            "correlation_groups": correlation_groups,
            "patterns_detected": patterns_detected,
            "duration_ms": duration_ms,
        },
    )


def record_orchestrator_feature_flag_check(
    orchestrator_type: str,
    flag_name: str,
    enabled: bool,
) -> None:
    """Record feature flag check for orchestrators.

    Args:
        orchestrator_type: Type of orchestrator (ux, alert)
        flag_name: Name of the feature flag checked
        enabled: Whether the flag was enabled
    """
    orchestrator_feature_flag_counter.add(
        1,
        {
            "orchestrator_type": orchestrator_type,
            "flag_name": flag_name,
            "enabled": str(enabled).lower(),
        },
    )

    logger.debug(
        "Recorded orchestrator feature flag check",
        extra={
            "orchestrator_type": orchestrator_type,
            "flag_name": flag_name,
            "enabled": enabled,
        },
    )


# =============================================================================
# AI Explanation Metrics (Plan Section 10.2)
# =============================================================================

# Explanation generation metrics
explanation_generation_counter = meter.create_counter(
    name="agent.explanation.generation.count",
    description="Total AI explanation generations",
    unit="1",
)

explanation_latency_histogram = meter.create_histogram(
    name="agent.explanation.generation.latency",
    description="Explanation generation latency in milliseconds",
    unit="ms",
)

explanation_cache_counter = meter.create_counter(
    name="agent.explanation.cache.count",
    description="Explanation cache hits and misses",
    unit="1",
)

explanation_error_counter = meter.create_counter(
    name="agent.explanation.errors.count",
    description="Explanation generation errors",
    unit="1",
)

# Per-analysis metrics
explanation_analysis_counter = meter.create_counter(
    name="agent.explanation.analysis.count",
    description="Per-analysis type execution count",
    unit="1",
)

explanation_analysis_duration_histogram = meter.create_histogram(
    name="agent.explanation.analysis.duration",
    description="Per-analysis type duration in milliseconds",
    unit="ms",
)

# Orchestrator-level metrics
explanation_orchestration_counter = meter.create_counter(
    name="agent.explanation.orchestration.count",
    description="Explanation orchestration executions",
    unit="1",
)

explanation_orchestration_duration_histogram = meter.create_histogram(
    name="agent.explanation.orchestration.duration",
    description="Explanation orchestration duration in milliseconds",
    unit="ms",
)


def record_explanation_generation(
    approval_id: str,
    duration_ms: float,
    success: bool,
    cached: bool,
    analysis_types: list[str] | None = None,
    error_type: str | None = None,
) -> None:
    """Record explanation generation metrics.

    Args:
        approval_id: ID of the approval request
        duration_ms: Generation duration in milliseconds
        success: Whether generation succeeded
        cached: Whether result was from cache
        analysis_types: Types of analyses performed
        error_type: Error type if failed
    """
    attributes = {
        "success": str(success).lower(),
        "cached": str(cached).lower(),
    }

    explanation_generation_counter.add(1, attributes)
    explanation_latency_histogram.record(duration_ms, attributes)

    # Record cache hit/miss
    cache_result = "hit" if cached else "miss"
    explanation_cache_counter.add(1, {"cache_result": cache_result})

    # Record error if failed
    if not success and error_type:
        explanation_error_counter.add(1, {"error_type": error_type})

    logger.debug(
        "Recorded explanation generation",
        extra={
            "approval_id": approval_id,
            "duration_ms": duration_ms,
            "success": success,
            "cached": cached,
            "analysis_types": analysis_types,
            "error_type": error_type,
        },
    )


def record_explanation_analysis_task(
    analysis_type: str,
    duration_ms: float,
    success: bool,
) -> None:
    """Record individual analysis task metrics.

    Args:
        analysis_type: Type of analysis (uncertainty, risk, alternatives, evidence)
        duration_ms: Analysis duration in milliseconds
        success: Whether analysis succeeded
    """
    attributes = {
        "analysis_type": analysis_type,
        "success": str(success).lower(),
    }

    explanation_analysis_counter.add(1, attributes)
    explanation_analysis_duration_histogram.record(duration_ms, attributes)

    logger.debug(
        "Recorded explanation analysis task",
        extra={
            "analysis_type": analysis_type,
            "duration_ms": duration_ms,
            "success": success,
        },
    )


def record_explanation_orchestration(
    task_count: int,
    successful_count: int,
    duration_ms: float,
    success: bool,
) -> None:
    """Record explanation orchestration metrics.

    Args:
        task_count: Total number of analysis tasks
        successful_count: Number of successfully completed tasks
        duration_ms: Total orchestration duration in milliseconds
        success: Whether overall orchestration succeeded
    """
    attributes = {
        "success": str(success).lower(),
    }

    explanation_orchestration_counter.add(1, attributes)
    explanation_orchestration_duration_histogram.record(duration_ms, attributes)

    # Record task counts
    explanation_orchestration_counter.add(
        task_count,
        {"task_status": "total"},
    )
    explanation_orchestration_counter.add(
        successful_count,
        {"task_status": "successful"},
    )
    if task_count > successful_count:
        explanation_orchestration_counter.add(
            task_count - successful_count,
            {"task_status": "failed"},
        )

    logger.debug(
        "Recorded explanation orchestration",
        extra={
            "task_count": task_count,
            "successful_count": successful_count,
            "duration_ms": duration_ms,
            "success": success,
        },
    )
