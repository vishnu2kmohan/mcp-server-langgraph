"""
Resilience metrics for observability.

Provides OpenTelemetry metrics for all resilience patterns:
- Circuit breaker state changes and failures
- Retry attempts and exhaustion
- Timeout violations
- Bulkhead rejections and active operations
- Fallback usage

These metrics integrate with the existing observability stack.
"""

from typing import Any, Dict, Optional

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Circuit Breaker Metrics
# ==============================================================================

circuit_breaker_state_gauge = meter.create_gauge(
    name="circuit_breaker.state",
    description="Circuit breaker state (0=closed, 1=open, 0.5=half-open)",
    unit="1",
)

circuit_breaker_failure_counter = meter.create_counter(
    name="circuit_breaker.failures",
    description="Total circuit breaker failures",
    unit="1",
)

circuit_breaker_success_counter = meter.create_counter(
    name="circuit_breaker.successes",
    description="Total circuit breaker successes",
    unit="1",
)

circuit_breaker_state_change_counter = meter.create_counter(
    name="circuit_breaker.state_changes",
    description="Total circuit breaker state changes",
    unit="1",
)


# ==============================================================================
# Retry Metrics
# ==============================================================================

retry_attempt_counter = meter.create_counter(
    name="retry.attempts",
    description="Total retry attempts",
    unit="1",
)

retry_exhausted_counter = meter.create_counter(
    name="retry.exhausted",
    description="Total retry exhaustion events (all attempts failed)",
    unit="1",
)

retry_success_after_retry_counter = meter.create_counter(
    name="retry.success_after_retry",
    description="Total successful retries (succeeded on attempt > 1)",
    unit="1",
)


# ==============================================================================
# Timeout Metrics
# ==============================================================================

timeout_exceeded_counter = meter.create_counter(
    name="timeout.exceeded",
    description="Total timeout violations",
    unit="1",
)

timeout_duration_histogram = meter.create_histogram(
    name="timeout.duration",
    description="Timeout duration in seconds",
    unit="s",
)


# ==============================================================================
# Bulkhead Metrics
# ==============================================================================

bulkhead_rejected_counter = meter.create_counter(
    name="bulkhead.rejections",
    description="Total bulkhead rejections (no available slots)",
    unit="1",
)

bulkhead_active_operations_gauge = meter.create_gauge(
    name="bulkhead.active_operations",
    description="Current number of active operations in bulkhead",
    unit="1",
)

bulkhead_queue_depth_gauge = meter.create_gauge(
    name="bulkhead.queue_depth",
    description="Current number of operations waiting for bulkhead slot",
    unit="1",
)


# ==============================================================================
# Fallback Metrics
# ==============================================================================

fallback_used_counter = meter.create_counter(
    name="fallback.used",
    description="Total fallback invocations",
    unit="1",
)

fallback_cache_hits_counter = meter.create_counter(
    name="fallback.cache_hits",
    description="Total fallback cache hits (stale data returned)",
    unit="1",
)


# ==============================================================================
# Aggregate Resilience Metrics
# ==============================================================================

resilience_pattern_invocations_counter = meter.create_counter(
    name="resilience.pattern_invocations",
    description="Total resilience pattern invocations",
    unit="1",
)

resilience_pattern_effectiveness_gauge = meter.create_gauge(
    name="resilience.pattern_effectiveness",
    description="Resilience pattern effectiveness (0-1, 1=all requests succeeded)",
    unit="1",
)


# ==============================================================================
# Helper Functions
# ==============================================================================


def record_circuit_breaker_event(
    service: str,
    event_type: str,
    exception_type: Optional[str] = None,
) -> None:
    """
    Record a circuit breaker event.

    Args:
        service: Service name (llm, openfga, redis, etc.)
        event_type: Event type (success, failure, state_change)
        exception_type: Exception type (if failure)
    """
    attributes = {"service": service}

    if event_type == "success":
        circuit_breaker_success_counter.add(1, attributes)
    elif event_type == "failure":
        if exception_type:
            attributes["exception_type"] = exception_type
        circuit_breaker_failure_counter.add(1, attributes)
    elif event_type == "state_change":
        circuit_breaker_state_change_counter.add(1, attributes)


def record_retry_event(
    function: str,
    event_type: str,
    attempt_number: Optional[int] = None,
    exception_type: Optional[str] = None,
) -> None:
    """
    Record a retry event.

    Args:
        function: Function name
        event_type: Event type (attempt, exhausted, success_after_retry)
        attempt_number: Retry attempt number
        exception_type: Exception type
    """
    attributes = {"function": function}

    if attempt_number:
        attributes["attempt_number"] = str(attempt_number)
    if exception_type:
        attributes["exception_type"] = exception_type

    if event_type == "attempt":
        retry_attempt_counter.add(1, attributes)
    elif event_type == "exhausted":
        retry_exhausted_counter.add(1, attributes)
    elif event_type == "success_after_retry":
        retry_success_after_retry_counter.add(1, attributes)


def record_timeout_event(
    function: str,
    operation_type: str,
    timeout_seconds: int,
) -> None:
    """
    Record a timeout violation.

    Args:
        function: Function name
        operation_type: Operation type (llm, auth, db, http, default)
        timeout_seconds: Timeout value in seconds
    """
    attributes = {
        "function": function,
        "operation_type": operation_type,
        "timeout_seconds": str(timeout_seconds),
    }

    timeout_exceeded_counter.add(1, attributes)
    timeout_duration_histogram.record(timeout_seconds, attributes)


def record_bulkhead_event(
    resource_type: str,
    event_type: str,
    active_count: Optional[int] = None,
    queue_depth: Optional[int] = None,
) -> None:
    """
    Record a bulkhead event.

    Args:
        resource_type: Resource type (llm, openfga, redis, db)
        event_type: Event type (rejection, active, queued)
        active_count: Number of active operations
        queue_depth: Number of queued operations
    """
    attributes = {"resource_type": resource_type}

    if event_type == "rejection":
        bulkhead_rejected_counter.add(1, attributes)
    elif event_type == "active" and active_count is not None:
        bulkhead_active_operations_gauge.set(active_count, attributes)
    elif event_type == "queued" and queue_depth is not None:
        bulkhead_queue_depth_gauge.set(queue_depth, attributes)


def record_fallback_event(
    function: str,
    exception_type: str,
    fallback_type: str = "default",
) -> None:
    """
    Record a fallback usage event.

    Args:
        function: Function name
        exception_type: Exception type that triggered fallback
        fallback_type: Type of fallback (default, function, strategy, cache)
    """
    attributes = {
        "function": function,
        "exception_type": exception_type,
        "fallback_type": fallback_type,
    }

    fallback_used_counter.add(1, attributes)

    if fallback_type == "cache":
        fallback_cache_hits_counter.add(1, attributes)


# ==============================================================================
# Metrics Export Functions
# ==============================================================================


def get_resilience_metrics_summary() -> Dict[str, Any]:
    """
    Get summary of resilience metrics (for health checks, debugging).

    Returns:
        Dictionary with metric summaries

    Note: This is a snapshot, not real-time metrics.
    Use Prometheus/Grafana for real-time monitoring.
    """
    # This is a placeholder - in production, you'd query the metrics backend
    # For now, return a structure that shows what's available
    return {
        "circuit_breakers": {
            "total_failures": "circuit_breaker.failures (counter)",
            "total_successes": "circuit_breaker.successes (counter)",
            "state_changes": "circuit_breaker.state_changes (counter)",
            "current_state": "circuit_breaker.state (gauge)",
        },
        "retries": {
            "total_attempts": "retry.attempts (counter)",
            "exhausted": "retry.exhausted (counter)",
            "successes": "retry.success_after_retry (counter)",
        },
        "timeouts": {
            "total_exceeded": "timeout.exceeded (counter)",
            "duration_histogram": "timeout.duration (histogram)",
        },
        "bulkheads": {
            "total_rejections": "bulkhead.rejections (counter)",
            "active_operations": "bulkhead.active_operations (gauge)",
            "queue_depth": "bulkhead.queue_depth (gauge)",
        },
        "fallbacks": {
            "total_used": "fallback.used (counter)",
            "cache_hits": "fallback.cache_hits (counter)",
        },
    }


def export_resilience_metrics_for_prometheus() -> str:
    """
    Export metrics in Prometheus exposition format.

    Returns:
        Prometheus-formatted metrics

    Note: This is typically handled by the OpenTelemetry exporter.
    This function is for manual export/debugging.
    """
    # Placeholder - in production, use OpenTelemetry Prometheus exporter
    return """
# HELP circuit_breaker_failures Total circuit breaker failures
# TYPE circuit_breaker_failures counter
circuit_breaker_failures{service="llm"} 5
circuit_breaker_failures{service="openfga"} 2

# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open)
# TYPE circuit_breaker_state gauge
circuit_breaker_state{service="llm"} 0
circuit_breaker_state{service="openfga"} 0

# HELP retry_attempts Total retry attempts
# TYPE retry_attempts counter
retry_attempts{function="call_llm",attempt_number="1"} 10
retry_attempts{function="call_llm",attempt_number="2"} 5

# HELP timeout_exceeded Total timeout violations
# TYPE timeout_exceeded counter
timeout_exceeded{function="call_llm",operation_type="llm"} 3

# HELP bulkhead_rejections Total bulkhead rejections
# TYPE bulkhead_rejections counter
bulkhead_rejections{resource_type="llm"} 2

# HELP fallback_used Total fallback invocations
# TYPE fallback_used counter
fallback_used{function="check_permission",exception_type="OpenFGAError"} 1
"""
