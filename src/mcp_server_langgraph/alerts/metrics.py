"""
Alert processing metrics for observability.

Provides OpenTelemetry metrics for alert processing:
- Alert reception and broadcasting
- AI recommendation generation
- Remediation approval workflow
- Rate limiting

These metrics integrate with the existing observability stack.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Alert Reception Metrics
# ==============================================================================

alert_received_counter = meter.create_counter(
    name="alerts.received",
    description="Total alerts received from Alertmanager webhook",
    unit="1",
)

alert_broadcast_counter = meter.create_counter(
    name="alerts.broadcast",
    description="Total alerts broadcast to WebSocket clients",
    unit="1",
)

alert_filtered_counter = meter.create_counter(
    name="alerts.filtered",
    description="Total alerts filtered out (not critical/warning)",
    unit="1",
)


# ==============================================================================
# AI Recommendation Metrics
# ==============================================================================

recommendation_requested_counter = meter.create_counter(
    name="alerts.recommendation.requested",
    description="Total AI recommendation requests",
    unit="1",
)

recommendation_cache_hit_counter = meter.create_counter(
    name="alerts.recommendation.cache_hits",
    description="Total AI recommendation cache hits",
    unit="1",
)

recommendation_cache_miss_counter = meter.create_counter(
    name="alerts.recommendation.cache_misses",
    description="Total AI recommendation cache misses (LLM called)",
    unit="1",
)

recommendation_generated_counter = meter.create_counter(
    name="alerts.recommendation.generated",
    description="Total AI recommendations generated successfully",
    unit="1",
)

recommendation_failed_counter = meter.create_counter(
    name="alerts.recommendation.failed",
    description="Total AI recommendation generation failures",
    unit="1",
)

recommendation_regenerated_counter = meter.create_counter(
    name="alerts.recommendation.regenerated",
    description="Total AI recommendations force-regenerated",
    unit="1",
)

recommendation_duration_histogram = meter.create_histogram(
    name="alerts.recommendation.duration",
    description="AI recommendation generation duration in seconds",
    unit="s",
)

recommendation_cache_size_gauge = meter.create_gauge(
    name="alerts.recommendation.cache_size",
    description="Current number of recommendations in cache",
    unit="1",
)


# ==============================================================================
# Rate Limiting Metrics
# ==============================================================================

rate_limit_exceeded_counter = meter.create_counter(
    name="alerts.rate_limit.exceeded",
    description="Total rate limit exceeded events for recommendation endpoints",
    unit="1",
)

rate_limit_tokens_gauge = meter.create_gauge(
    name="alerts.rate_limit.tokens_available",
    description="Current available tokens in rate limit bucket",
    unit="1",
)


# ==============================================================================
# Remediation Workflow Metrics
# ==============================================================================

remediation_requested_counter = meter.create_counter(
    name="alerts.remediation.requested",
    description="Total remediation requests submitted for approval",
    unit="1",
)

remediation_approved_counter = meter.create_counter(
    name="alerts.remediation.approved",
    description="Total remediations approved",
    unit="1",
)

remediation_rejected_counter = meter.create_counter(
    name="alerts.remediation.rejected",
    description="Total remediations rejected",
    unit="1",
)

remediation_executed_counter = meter.create_counter(
    name="alerts.remediation.executed",
    description="Total remediations executed",
    unit="1",
)

remediation_execution_success_counter = meter.create_counter(
    name="alerts.remediation.execution_success",
    description="Total successful remediation executions",
    unit="1",
)

remediation_execution_failed_counter = meter.create_counter(
    name="alerts.remediation.execution_failed",
    description="Total failed remediation executions",
    unit="1",
)

remediation_execution_duration_histogram = meter.create_histogram(
    name="alerts.remediation.execution_duration",
    description="Remediation execution duration in seconds",
    unit="s",
)

remediation_command_blocked_counter = meter.create_counter(
    name="alerts.remediation.command_blocked",
    description="Total remediation commands blocked by security validation",
    unit="1",
)


# ==============================================================================
# WebSocket Connection Metrics
# ==============================================================================

alert_websocket_connections_gauge = meter.create_gauge(
    name="alerts.websocket.connections",
    description="Current number of active alert WebSocket connections",
    unit="1",
)

alert_websocket_messages_counter = meter.create_counter(
    name="alerts.websocket.messages",
    description="Total messages sent over alert WebSocket connections",
    unit="1",
)


# ==============================================================================
# Helper Functions
# ==============================================================================


def record_alert_received(severity: str, status: str) -> None:
    """Record an alert received from Alertmanager."""
    alert_received_counter.add(1, {"severity": severity, "status": status})


def record_alert_broadcast(severity: str, client_count: int) -> None:
    """Record an alert broadcast to WebSocket clients."""
    alert_broadcast_counter.add(1, {"severity": severity, "client_count": str(client_count)})


def record_alert_filtered(severity: str, reason: str) -> None:
    """Record an alert that was filtered out."""
    alert_filtered_counter.add(1, {"severity": severity, "reason": reason})


def record_recommendation_request(alert_id: str, cached: bool) -> None:
    """Record an AI recommendation request."""
    recommendation_requested_counter.add(1, {"alert_id": alert_id[:8]})
    if cached:
        recommendation_cache_hit_counter.add(1)
    else:
        recommendation_cache_miss_counter.add(1)


def record_recommendation_generated(
    alert_id: str, duration_seconds: float, success: bool
) -> None:
    """Record AI recommendation generation result."""
    if success:
        recommendation_generated_counter.add(1, {"alert_id": alert_id[:8]})
    else:
        recommendation_failed_counter.add(1, {"alert_id": alert_id[:8]})
    recommendation_duration_histogram.record(duration_seconds)


def record_recommendation_regenerated(alert_id: str) -> None:
    """Record a force-regenerated recommendation."""
    recommendation_regenerated_counter.add(1, {"alert_id": alert_id[:8]})


def update_recommendation_cache_size(size: int, cache_type: str = "l1") -> None:
    """Update the current recommendation cache size."""
    recommendation_cache_size_gauge.set(size, {"cache_type": cache_type})


def record_rate_limit_exceeded(endpoint: str) -> None:
    """Record a rate limit exceeded event."""
    rate_limit_exceeded_counter.add(1, {"endpoint": endpoint})


def record_remediation_workflow(
    action: str, remediation_id: str, success: bool = True
) -> None:
    """Record remediation workflow events."""
    labels = {"remediation_id": remediation_id[:8]}
    if action == "requested":
        remediation_requested_counter.add(1, labels)
    elif action == "approved":
        remediation_approved_counter.add(1, labels)
    elif action == "rejected":
        remediation_rejected_counter.add(1, labels)
    elif action == "executed":
        remediation_executed_counter.add(1, labels)
        if success:
            remediation_execution_success_counter.add(1, labels)
        else:
            remediation_execution_failed_counter.add(1, labels)


def record_remediation_execution(
    remediation_id: str, duration_seconds: float, success: bool
) -> None:
    """Record remediation execution result."""
    labels = {"remediation_id": remediation_id[:8], "success": str(success).lower()}
    remediation_execution_duration_histogram.record(duration_seconds, labels)


def record_command_blocked(reason: str) -> None:
    """Record a blocked remediation command."""
    remediation_command_blocked_counter.add(1, {"reason": reason})


def update_websocket_connections(count: int) -> None:
    """Update the current WebSocket connection count."""
    alert_websocket_connections_gauge.set(count)


def record_websocket_message(message_type: str) -> None:
    """Record a WebSocket message sent."""
    alert_websocket_messages_counter.add(1, {"message_type": message_type})


# ==============================================================================
# Alert Correlation Metrics
# ==============================================================================

correlation_requests_counter = meter.create_counter(
    name="alerts.correlation.requests",
    description="Total alert correlation requests",
    unit="1",
)

correlation_groups_gauge = meter.create_gauge(
    name="alerts.correlation.groups",
    description="Number of correlation groups in last request",
    unit="1",
)

correlation_duration_histogram = meter.create_histogram(
    name="alerts.correlation.duration",
    description="Alert correlation processing duration in seconds",
    unit="s",
)

pattern_detection_counter = meter.create_counter(
    name="alerts.correlation.patterns_detected",
    description="Total patterns detected in correlation",
    unit="1",
)

root_cause_identification_counter = meter.create_counter(
    name="alerts.correlation.root_causes_identified",
    description="Total root causes identified in correlation",
    unit="1",
)


def record_correlation_request(
    correlation_type: str,
    alert_count: int,
    group_count: int,
    duration_seconds: float,
) -> None:
    """Record an alert correlation request."""
    labels = {"correlation_type": correlation_type}
    correlation_requests_counter.add(1, labels)
    correlation_groups_gauge.set(group_count, labels)
    correlation_duration_histogram.record(duration_seconds, labels)


def record_pattern_detected(pattern_type: str) -> None:
    """Record a detected correlation pattern."""
    pattern_detection_counter.add(1, {"pattern_type": pattern_type})


def record_root_cause_identified(group_id: str) -> None:
    """Record a root cause identification."""
    root_cause_identification_counter.add(1, {"group_id": group_id[:8]})


# ==============================================================================
# AI Recommendation Quality Metrics
# ==============================================================================

# Approval/Rejection tracking
recommendation_approval_counter = meter.create_counter(
    name="alerts.recommendation.approvals",
    description="Total AI recommendations approved by admins",
    unit="1",
)

recommendation_rejection_counter = meter.create_counter(
    name="alerts.recommendation.rejections",
    description="Total AI recommendations rejected by admins",
    unit="1",
)

recommendation_rejection_reason_counter = meter.create_counter(
    name="alerts.recommendation.rejection_reasons",
    description="AI recommendation rejections by reason category",
    unit="1",
)

# Execution success tracking
recommendation_execution_success_counter = meter.create_counter(
    name="alerts.recommendation.execution_success",
    description="Successfully executed AI-recommended remediations",
    unit="1",
)

recommendation_execution_failure_counter = meter.create_counter(
    name="alerts.recommendation.execution_failure",
    description="Failed AI-recommended remediation executions",
    unit="1",
)

recommendation_execution_time_histogram = meter.create_histogram(
    name="alerts.recommendation.execution_time",
    description="Execution time of approved remediations in seconds",
    unit="s",
)

# Few-shot learning metrics
recommendation_with_fewshot_counter = meter.create_counter(
    name="alerts.recommendation.with_fewshot",
    description="Recommendations generated with few-shot examples",
    unit="1",
)

recommendation_without_fewshot_counter = meter.create_counter(
    name="alerts.recommendation.without_fewshot",
    description="Recommendations generated without few-shot examples",
    unit="1",
)

fewshot_approval_counter = meter.create_counter(
    name="alerts.recommendation.fewshot_approvals",
    description="Approvals of recommendations with few-shot examples",
    unit="1",
)

fewshot_rejection_counter = meter.create_counter(
    name="alerts.recommendation.fewshot_rejections",
    description="Rejections of recommendations with few-shot examples",
    unit="1",
)

# Constraint learning metrics
recommendation_with_constraints_counter = meter.create_counter(
    name="alerts.recommendation.with_constraints",
    description="Recommendations generated with learned constraints",
    unit="1",
)

constraint_patterns_applied_gauge = meter.create_gauge(
    name="alerts.recommendation.constraint_patterns",
    description="Number of constraint patterns currently applied",
    unit="1",
)

# Quality score metrics
recommendation_quality_score_histogram = meter.create_histogram(
    name="alerts.recommendation.quality_score",
    description="Quality score of AI recommendations (0-1 scale)",
    unit="1",
)

recommendation_confidence_histogram = meter.create_histogram(
    name="alerts.recommendation.confidence",
    description="Confidence level of AI recommendations (0-1 scale)",
    unit="1",
)


# ==============================================================================
# AI Recommendation Quality Helper Functions
# ==============================================================================


def record_recommendation_approval(
    alert_type: str,
    had_fewshot: bool = False,
    had_constraints: bool = False,
) -> None:
    """Record an AI recommendation approval."""
    labels = {"alert_type": alert_type[:50]}
    recommendation_approval_counter.add(1, labels)

    if had_fewshot:
        fewshot_approval_counter.add(1, labels)


def record_recommendation_rejection(
    alert_type: str,
    reason: str,
    had_fewshot: bool = False,
    had_constraints: bool = False,
) -> None:
    """Record an AI recommendation rejection with reason."""
    labels = {"alert_type": alert_type[:50]}
    recommendation_rejection_counter.add(1, labels)
    recommendation_rejection_reason_counter.add(1, {"reason": reason})

    if had_fewshot:
        fewshot_rejection_counter.add(1, labels)


def record_recommendation_execution(
    alert_type: str,
    success: bool,
    execution_time_seconds: float,
) -> None:
    """Record the execution result of an approved remediation."""
    labels = {"alert_type": alert_type[:50]}

    if success:
        recommendation_execution_success_counter.add(1, labels)
    else:
        recommendation_execution_failure_counter.add(1, labels)

    recommendation_execution_time_histogram.record(
        execution_time_seconds,
        {"success": str(success).lower()},
    )


def record_fewshot_usage(
    alert_type: str,
    example_count: int,
) -> None:
    """Record few-shot example usage in recommendation generation."""
    if example_count > 0:
        recommendation_with_fewshot_counter.add(
            1, {"alert_type": alert_type[:50], "example_count": str(example_count)}
        )
    else:
        recommendation_without_fewshot_counter.add(
            1, {"alert_type": alert_type[:50]}
        )


def record_constraint_usage(
    alert_type: str,
    constraint_count: int,
) -> None:
    """Record constraint learning usage in recommendation generation."""
    if constraint_count > 0:
        recommendation_with_constraints_counter.add(
            1, {"alert_type": alert_type[:50], "constraint_count": str(constraint_count)}
        )


def update_constraint_patterns_count(count: int) -> None:
    """Update the current count of active constraint patterns."""
    constraint_patterns_applied_gauge.set(count)


def record_recommendation_quality(
    alert_type: str,
    quality_score: float,
    confidence: float,
) -> None:
    """Record quality metrics for a recommendation."""
    labels = {"alert_type": alert_type[:50]}
    recommendation_quality_score_histogram.record(quality_score, labels)
    recommendation_confidence_histogram.record(confidence, labels)
