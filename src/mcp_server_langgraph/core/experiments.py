"""
A/B Experiment Framework for Feature Comparison.

This module provides infrastructure for running A/B experiments to compare
different implementations (e.g., semantic vs static tool selection).

Key Components:
- ExperimentConfig: Defines an experiment with variants and traffic split
- ExperimentVariant: A specific variant (control/treatment) in an experiment
- ExperimentMetrics: Collects metrics for experiment analysis
- get_variant_for_user: Deterministic variant assignment using consistent hashing

Example Usage:
    from mcp_server_langgraph.core.experiments import (
        SEMANTIC_TOOL_EXPERIMENT,
        get_variant_for_user,
        should_use_semantic_selection,
    )

    # Get user's assigned variant
    variant = get_variant_for_user(SEMANTIC_TOOL_EXPERIMENT, user_id)

    # Check if semantic selection should be used
    if should_use_semantic_selection(user_id):
        # Use semantic tool selection
        ...
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

from mcp_server_langgraph.core import feature_flags

if TYPE_CHECKING:
    pass

logger = logging.getLogger("mcp-server-langgraph")

# ==============================================================================
# Prometheus Metrics for Experiments
# ==============================================================================

EXPERIMENT_ASSIGNMENT_TOTAL = Counter(
    "experiment_assignment_total",
    "Total experiment variant assignments",
    ["experiment_name", "variant"],
)

EXPERIMENT_TOOL_SELECTION_TOTAL = Counter(
    "experiment_tool_selection_total",
    "Tool selection events by experiment variant",
    ["experiment_name", "variant", "manual_override"],
)

EXPERIMENT_TOOL_UTILIZATION = Histogram(
    "experiment_tool_utilization_ratio",
    "Ratio of selected tools that were actually used",
    ["experiment_name", "variant"],
    buckets=[0.0, 0.25, 0.5, 0.75, 1.0],
)

EXPERIMENT_RESPONSE_LATENCY = Histogram(
    "experiment_response_latency_ms",
    "Response latency in milliseconds by variant",
    ["experiment_name", "variant"],
    buckets=[50, 100, 200, 500, 1000, 2000, 5000],
)

EXPERIMENT_USER_SATISFACTION = Counter(
    "experiment_user_satisfaction_total",
    "User satisfaction events (thumbs up/down)",
    ["experiment_name", "variant", "satisfied"],
)


# ==============================================================================
# Data Classes
# ==============================================================================


@dataclass(frozen=True)
class ExperimentVariant:
    """A variant in an A/B experiment.

    Attributes:
        name: Unique name for the variant (e.g., "control", "semantic")
        description: Human-readable description
        traffic_percentage: Percentage of traffic to route to this variant (0-100)
    """

    name: str
    description: str
    traffic_percentage: int


@dataclass
class ExperimentConfig:
    """Configuration for an A/B experiment.

    Attributes:
        name: Unique experiment identifier
        description: Human-readable description
        variants: List of variants with traffic percentages (must sum to 100)
        enabled: Whether the experiment is currently active
        start_date: Optional start date for the experiment
        end_date: Optional end date for the experiment
    """

    name: str
    description: str
    variants: list[ExperimentVariant]
    enabled: bool = True
    start_date: str | None = None
    end_date: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        total_traffic = sum(v.traffic_percentage for v in self.variants)
        if total_traffic != 100:
            raise ValueError(f"Variant traffic percentages must sum to 100, got {total_traffic}")


# ==============================================================================
# Experiment Definitions
# ==============================================================================

SEMANTIC_TOOL_EXPERIMENT = ExperimentConfig(
    name="semantic_tool_selection",
    description="Compare semantic search tool selection vs static tool binding",
    variants=[
        ExperimentVariant(
            name="control",
            description="Static tool binding (all tools available)",
            traffic_percentage=50,
        ),
        ExperimentVariant(
            name="semantic",
            description="Semantic search tool selection",
            traffic_percentage=50,
        ),
    ],
    enabled=True,
)


# ==============================================================================
# Variant Assignment
# ==============================================================================


def get_variant_for_user(
    experiment: ExperimentConfig,
    user_id: str,
) -> ExperimentVariant:
    """Get deterministic variant assignment for a user.

    Uses consistent hashing to ensure the same user always gets the same variant.
    This enables reproducible experiment analysis.

    Args:
        experiment: The experiment configuration
        user_id: User identifier (e.g., "user:alice")

    Returns:
        The assigned ExperimentVariant
    """
    # Create a hash of experiment name + user_id for deterministic assignment
    hash_input = f"{experiment.name}:{user_id}"
    # MD5 used for consistent hashing (not security), safe for A/B bucket assignment
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)  # noqa: S324

    # Map hash to 0-99 range
    bucket = hash_value % 100

    # Find which variant this bucket falls into
    cumulative = 0
    for variant in experiment.variants:
        cumulative += variant.traffic_percentage
        if bucket < cumulative:
            EXPERIMENT_ASSIGNMENT_TOTAL.labels(
                experiment_name=experiment.name,
                variant=variant.name,
            ).inc()
            return variant

    # Fallback to last variant (shouldn't happen with valid config)
    return experiment.variants[-1]


def should_use_semantic_selection(user_id: str) -> bool:
    """Check if semantic tool selection should be used for a user.

    This function integrates with the A/B experiment to determine whether
    to use semantic search for tool selection.

    When the experiment is enabled:
        - Returns True if user is in "semantic" variant
        - Returns False if user is in "control" variant

    When the experiment is disabled:
        - Falls back to the enable_semantic_tool_search feature flag

    Args:
        user_id: User identifier

    Returns:
        True if semantic selection should be used
    """
    if SEMANTIC_TOOL_EXPERIMENT.enabled:
        variant = get_variant_for_user(SEMANTIC_TOOL_EXPERIMENT, user_id)
        return variant.name == "semantic"

    # Fall back to feature flag when experiment is disabled
    return feature_flags.enable_semantic_tool_search


# ==============================================================================
# Metrics Collection
# ==============================================================================


class ExperimentMetrics:
    """Collects and exports experiment metrics.

    This class provides methods to record various experiment-related metrics
    that can be used to compare variant performance.

    Metrics are exported to Prometheus for monitoring and analysis.
    """

    def record_tool_selection(
        self,
        experiment_name: str,
        variant: str,
        user_id: str,
        session_id: str,
        selected_tools: list[str],
        used_tools: list[str],
        manual_override: bool,
    ) -> None:
        """Record a tool selection event.

        Args:
            experiment_name: Name of the experiment
            variant: Variant the user is in
            user_id: User identifier
            session_id: Session identifier
            selected_tools: Tools selected by the system
            used_tools: Tools actually used in the response
            manual_override: Whether user manually changed tool selection
        """
        EXPERIMENT_TOOL_SELECTION_TOTAL.labels(
            experiment_name=experiment_name,
            variant=variant,
            manual_override=str(manual_override).lower(),
        ).inc()

        # Calculate utilization ratio
        if selected_tools:
            utilization = len(set(used_tools) & set(selected_tools)) / len(selected_tools)
            EXPERIMENT_TOOL_UTILIZATION.labels(
                experiment_name=experiment_name,
                variant=variant,
            ).observe(utilization)

        logger.debug(
            f"Recorded tool selection: experiment={experiment_name}, "
            f"variant={variant}, user={user_id}, session={session_id}, "
            f"selected={len(selected_tools)}, used={len(used_tools)}, "
            f"override={manual_override}"
        )

    def record_response_latency(
        self,
        experiment_name: str,
        variant: str,
        user_id: str,
        latency_ms: float,
    ) -> None:
        """Record response latency for a variant.

        Args:
            experiment_name: Name of the experiment
            variant: Variant the user is in
            user_id: User identifier
            latency_ms: Response latency in milliseconds
        """
        EXPERIMENT_RESPONSE_LATENCY.labels(
            experiment_name=experiment_name,
            variant=variant,
        ).observe(latency_ms)

        logger.debug(
            f"Recorded latency: experiment={experiment_name}, variant={variant}, user={user_id}, latency={latency_ms}ms"
        )

    def record_user_satisfaction(
        self,
        experiment_name: str,
        variant: str,
        user_id: str,
        message_id: str,
        satisfied: bool,
    ) -> None:
        """Record user satisfaction (thumbs up/down).

        Args:
            experiment_name: Name of the experiment
            variant: Variant the user is in
            user_id: User identifier
            message_id: Message identifier
            satisfied: True for thumbs up, False for thumbs down
        """
        EXPERIMENT_USER_SATISFACTION.labels(
            experiment_name=experiment_name,
            variant=variant,
            satisfied=str(satisfied).lower(),
        ).inc()

        logger.debug(
            f"Recorded satisfaction: experiment={experiment_name}, "
            f"variant={variant}, user={user_id}, message={message_id}, "
            f"satisfied={satisfied}"
        )


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "ExperimentConfig",
    "ExperimentMetrics",
    "ExperimentVariant",
    "SEMANTIC_TOOL_EXPERIMENT",
    "get_variant_for_user",
    "should_use_semantic_selection",
]
