"""
Audit metrics for Prometheus.

Provides metrics for monitoring audit system health:
- audit_events_total: Counter by category, event_type, outcome
- audit_events_latency_seconds: Histogram of processing time
- audit_integrity_verified_total: Counter of successful verifications
- audit_integrity_failures_total: Counter of failed verifications
- audit_chain_length: Gauge of current hash chain length

These metrics support operational monitoring and compliance
dashboards for audit system health.
"""

import logging
from collections import defaultdict

from mcp_server_langgraph.audit.models import UnifiedAuditEvent

logger = logging.getLogger(__name__)


class AuditMetrics:
    """
    Prometheus-compatible metrics for audit system.

    Provides counters, histograms, and gauges for monitoring
    audit event processing, integrity verification, and system health.

    Example:
        metrics = AuditMetrics()

        # Record an event
        metrics.record_event(audit_event)

        # Record latency
        metrics.record_event_latency("authentication", 0.05)

        # Export for Prometheus
        output = metrics.export_prometheus_format()
    """

    def __init__(self) -> None:
        """Initialize metrics collectors."""
        # Counters with labels
        self._event_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        self._latency_observations: dict[str, int] = defaultdict(int)
        self._latency_sums: dict[str, float] = defaultdict(float)

        # Simple counters
        self._integrity_verified_count = 0
        self._integrity_failure_count = 0

        # Gauges
        self._chain_length = 0

    def record_event(self, event: UnifiedAuditEvent) -> None:
        """
        Record an audit event for metrics.

        Increments the audit_events_total counter with labels
        for category, event_type, and outcome.

        Args:
            event: The audit event to record.
        """
        labels = (
            event.category.value if hasattr(event.category, "value") else str(event.category),
            event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            event.outcome,
        )
        self._event_counts[labels] += 1

    def get_event_count(
        self,
        category: str,
        event_type: str,
        outcome: str,
    ) -> int:
        """
        Get event count for specific labels.

        Args:
            category: Event category.
            event_type: Event type.
            outcome: Event outcome.

        Returns:
            Count of events matching the labels.
        """
        labels = (category, event_type, outcome)
        return self._event_counts[labels]

    def record_event_latency(
        self,
        category: str,
        latency_seconds: float,
    ) -> None:
        """
        Record event processing latency.

        Args:
            category: Event category.
            latency_seconds: Processing time in seconds.
        """
        self._latency_observations[category] += 1
        self._latency_sums[category] += latency_seconds

    def get_latency_observations(self, category: str) -> int:
        """
        Get number of latency observations for a category.

        Args:
            category: Event category.

        Returns:
            Number of observations.
        """
        return self._latency_observations[category]

    def record_integrity_verification(
        self,
        success: bool,
        events_verified: int,
    ) -> None:
        """
        Record an integrity verification result.

        Args:
            success: Whether verification succeeded.
            events_verified: Number of events verified.
        """
        if success:
            self._integrity_verified_count += 1
        else:
            self._integrity_failure_count += 1

    def get_integrity_verified_count(self) -> int:
        """Get count of successful integrity verifications."""
        return self._integrity_verified_count

    def get_integrity_failure_count(self) -> int:
        """Get count of failed integrity verifications."""
        return self._integrity_failure_count

    def set_chain_length(self, length: int) -> None:
        """
        Set the current hash chain length.

        Args:
            length: Current chain length.
        """
        self._chain_length = length

    def get_chain_length(self) -> int:
        """Get current hash chain length."""
        return self._chain_length

    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-compatible text format string.
        """
        lines = []

        # audit_events_total
        lines.append("# HELP audit_events_total Total number of audit events")
        lines.append("# TYPE audit_events_total counter")
        for (category, event_type, outcome), count in self._event_counts.items():
            lines.append(f'audit_events_total{{category="{category}",event_type="{event_type}",outcome="{outcome}"}} {count}')

        # audit_events_latency_seconds (simplified sum/count)
        lines.append("# HELP audit_events_latency_seconds Audit event processing latency")
        lines.append("# TYPE audit_events_latency_seconds summary")
        for category, count in self._latency_observations.items():
            total = self._latency_sums[category]
            lines.append(f'audit_events_latency_seconds_count{{category="{category}"}} {count}')
            lines.append(f'audit_events_latency_seconds_sum{{category="{category}"}} {total}')

        # audit_integrity_verified_total
        lines.append("# HELP audit_integrity_verified_total Successful integrity verifications")
        lines.append("# TYPE audit_integrity_verified_total counter")
        lines.append(f"audit_integrity_verified_total {self._integrity_verified_count}")

        # audit_integrity_failures_total
        lines.append("# HELP audit_integrity_failures_total Failed integrity verifications")
        lines.append("# TYPE audit_integrity_failures_total counter")
        lines.append(f"audit_integrity_failures_total {self._integrity_failure_count}")

        # audit_chain_length
        lines.append("# HELP audit_chain_length Current hash chain length")
        lines.append("# TYPE audit_chain_length gauge")
        lines.append(f"audit_chain_length {self._chain_length}")

        return "\n".join(lines)

    def get_registered_metrics(self) -> list[str]:
        """
        Get list of registered metric names.

        Returns:
            List of metric names.
        """
        return [
            "audit_events_total",
            "audit_events_latency_seconds",
            "audit_integrity_verified_total",
            "audit_integrity_failures_total",
            "audit_chain_length",
        ]

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self._event_counts.clear()
        self._latency_observations.clear()
        self._latency_sums.clear()
        self._integrity_verified_count = 0
        self._integrity_failure_count = 0
        self._chain_length = 0
