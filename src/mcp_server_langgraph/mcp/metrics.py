"""
MCP Prometheus Metrics.

Provides Prometheus metrics for MCP features including tasks,
sampling, elicitation, and tool execution.

Integrates with the project's existing observability stack.
"""

from prometheus_client import Counter, Histogram

# =============================================================================
# Task Metrics
# =============================================================================

mcp_task_created_total = Counter(
    "mcp_task_created_total",
    "Total number of MCP tasks created",
    ["operation"],
)

mcp_task_duration_seconds = Histogram(
    "mcp_task_duration_seconds",
    "Duration of MCP tasks in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

mcp_task_status_changes_total = Counter(
    "mcp_task_status_changes_total",
    "Total number of MCP task status changes",
    ["from_status", "to_status"],
)

# =============================================================================
# Sampling Metrics
# =============================================================================

mcp_sampling_requests_total = Counter(
    "mcp_sampling_requests_total",
    "Total number of MCP sampling requests",
    ["status"],
)

mcp_sampling_latency_seconds = Histogram(
    "mcp_sampling_latency_seconds",
    "Latency of MCP sampling requests in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# =============================================================================
# Elicitation Metrics
# =============================================================================

mcp_elicitation_requests_total = Counter(
    "mcp_elicitation_requests_total",
    "Total number of MCP elicitation requests",
    ["action"],
)

mcp_elicitation_response_time_seconds = Histogram(
    "mcp_elicitation_response_time_seconds",
    "Time for users to respond to elicitation requests",
    buckets=[1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0],
)

# =============================================================================
# Tool Metrics
# =============================================================================

mcp_tool_validation_errors_total = Counter(
    "mcp_tool_validation_errors_total",
    "Total number of MCP tool validation errors",
    ["tool_name"],
)

mcp_tool_executions_total = Counter(
    "mcp_tool_executions_total",
    "Total number of MCP tool executions",
    ["tool_name", "status"],
)

# =============================================================================
# Helper Functions
# =============================================================================


def record_task_created(operation: str) -> None:
    """Record a task creation.

    Args:
        operation: Name of the operation being performed
    """
    mcp_task_created_total.labels(operation=operation).inc()


def record_task_duration(duration_seconds: float) -> None:
    """Record task duration.

    Args:
        duration_seconds: Duration in seconds
    """
    mcp_task_duration_seconds.observe(duration_seconds)


def record_sampling_request(status: str) -> None:
    """Record a sampling request.

    Args:
        status: Request status (success, rejected, error)
    """
    mcp_sampling_requests_total.labels(status=status).inc()


def record_sampling_latency(latency_seconds: float) -> None:
    """Record sampling request latency.

    Args:
        latency_seconds: Latency in seconds
    """
    mcp_sampling_latency_seconds.observe(latency_seconds)


def record_elicitation(action: str) -> None:
    """Record an elicitation response.

    Args:
        action: User action (accept, decline, cancel)
    """
    mcp_elicitation_requests_total.labels(action=action).inc()


def record_elicitation_response_time(response_time_seconds: float) -> None:
    """Record elicitation response time.

    Args:
        response_time_seconds: Time for user to respond
    """
    mcp_elicitation_response_time_seconds.observe(response_time_seconds)


def record_tool_validation_error(tool_name: str) -> None:
    """Record a tool validation error.

    Args:
        tool_name: Name of the tool that had validation error
    """
    mcp_tool_validation_errors_total.labels(tool_name=tool_name).inc()


def record_tool_execution(tool_name: str, status: str) -> None:
    """Record a tool execution.

    Args:
        tool_name: Name of the executed tool
        status: Execution status (success, error)
    """
    mcp_tool_executions_total.labels(tool_name=tool_name, status=status).inc()
