"""
Skill Execution Metrics

OpenTelemetry metrics for skill execution observability:
- Execution counts and durations
- Error rates by skill and script
- Marketplace fetch operations
- Cache hit rates

These metrics integrate with the existing observability stack.

Usage:
    from mcp_server_langgraph.skills.metrics import record_skill_execution

    record_skill_execution(
        skill_name="web-research",
        script_name="search.py",
        success=True,
        duration_ms=150.5,
    )
"""

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Label Constants
# ==============================================================================

SKILL_EXECUTION_LABELS = [
    "skill_name",
    "script_name",
    "success",
]

SKILL_LOAD_LABELS = [
    "skill_name",
    "source",
    "success",
]

MARKETPLACE_LABELS = [
    "marketplace_name",
    "operation",
    "success",
    "cached",
]


# ==============================================================================
# Skill Execution Metrics
# ==============================================================================

skill_execution_counter = meter.create_counter(
    name="skill.execution.count",
    description="Total skill executions",
    unit="1",
)

skill_execution_duration_histogram = meter.create_histogram(
    name="skill.execution.duration",
    description="Skill execution duration in milliseconds",
    unit="ms",
)

skill_execution_error_counter = meter.create_counter(
    name="skill.execution.errors",
    description="Total skill execution errors",
    unit="1",
)


# ==============================================================================
# Skill Loading Metrics
# ==============================================================================

skill_load_counter = meter.create_counter(
    name="skill.load.count",
    description="Total skill load operations",
    unit="1",
)


# ==============================================================================
# Marketplace Metrics
# ==============================================================================

marketplace_fetch_counter = meter.create_counter(
    name="skill.marketplace.fetch",
    description="Total marketplace fetch operations",
    unit="1",
)


# ==============================================================================
# Recording Functions
# ==============================================================================


def record_skill_execution(
    skill_name: str,
    script_name: str,
    success: bool,
    duration_ms: float,
    error_type: str | None = None,
) -> None:
    """Record skill execution metrics.

    Args:
        skill_name: Name of the skill
        script_name: Name of the script executed
        success: Whether execution succeeded
        duration_ms: Execution duration in milliseconds
        error_type: Type of error (if failed)
    """
    labels = {
        "skill_name": skill_name,
        "script_name": script_name,
        "success": str(success).lower(),
    }

    # Record execution count
    skill_execution_counter.add(1, labels)

    # Record duration
    skill_execution_duration_histogram.record(duration_ms, labels)

    # Record error if failed
    if not success:
        error_labels = {
            **labels,
            "error_type": error_type or "unknown",
        }
        skill_execution_error_counter.add(1, error_labels)


def record_skill_load(
    skill_name: str,
    source: str,
    success: bool,
) -> None:
    """Record skill load metrics.

    Args:
        skill_name: Name of the skill
        source: Source of the skill (local, marketplace)
        success: Whether load succeeded
    """
    labels = {
        "skill_name": skill_name,
        "source": source,
        "success": str(success).lower(),
    }

    skill_load_counter.add(1, labels)


def record_marketplace_fetch(
    marketplace_name: str,
    operation: str,
    success: bool,
    cached: bool = False,
) -> None:
    """Record marketplace fetch metrics.

    Args:
        marketplace_name: Name of the marketplace
        operation: Operation type (list_skills, fetch_skill)
        success: Whether fetch succeeded
        cached: Whether result was from cache
    """
    labels = {
        "marketplace_name": marketplace_name,
        "operation": operation,
        "success": str(success).lower(),
        "cached": str(cached).lower(),
    }

    marketplace_fetch_counter.add(1, labels)
