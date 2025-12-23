"""
Alert Correlation Engine.

Service for correlating related alerts and identifying patterns.

Features:
- Group alerts by common labels (service, host, tenant)
- Detect time-based correlations
- Identify root cause vs symptom alerts
- Calculate correlation confidence scores

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from opentelemetry import trace

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# =============================================================================
# Enums
# =============================================================================


class PatternType(str, Enum):
    """Types of alert patterns."""

    CASCADING_FAILURE = "cascading_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DEPLOYMENT_ISSUE = "deployment_issue"
    UNKNOWN = "unknown"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CorrelatedAlert:
    """
    Alert data for correlation analysis.

    Attributes:
        alert_id: Unique alert identifier.
        name: Alert name/type.
        severity: Alert severity (critical, warning, info).
        labels: Key-value labels for correlation.
        started_at: When the alert started.
        resolved_at: When the alert resolved (if resolved).
    """

    alert_id: str
    name: str
    severity: str
    labels: dict[str, str]
    started_at: datetime
    resolved_at: datetime | None = None


@dataclass
class CorrelationGroup:
    """
    Group of correlated alerts.

    Attributes:
        group_id: Unique group identifier.
        correlation_type: How alerts were correlated (label, time, etc.).
        label_key: Label key used for correlation (if label-based).
        label_value: Label value for the group.
        alerts: Alerts in this group.
        root_cause_id: Identified root cause alert ID.
        confidence: Correlation confidence score (0-1).
    """

    group_id: str
    correlation_type: str
    label_key: str | None = None
    label_value: str | None = None
    alerts: list[CorrelatedAlert] = field(default_factory=list)
    root_cause_id: str | None = None
    confidence: float = 0.0


@dataclass
class PatternResult:
    """
    Result of pattern detection.

    Attributes:
        pattern_type: Type of detected pattern.
        confidence: Confidence in the pattern (0-1).
        description: Human-readable description.
        affected_services: Services affected by the pattern.
    """

    pattern_type: PatternType
    confidence: float
    description: str = ""
    affected_services: list[str] = field(default_factory=list)


# =============================================================================
# Alert Correlation Engine
# =============================================================================


# Resource-related alert names for pattern detection
RESOURCE_ALERT_NAMES = frozenset(
    {
        "highcpu",
        "highmemory",
        "highdisk",
        "lowmemory",
        "lowdisk",
        "cpuexhaustion",
        "memoryexhaustion",
        "diskexhaustion",
        "oomkiller",
        "outofmemory",
    }
)


class AlertCorrelationEngine:
    """
    Engine for correlating alerts and detecting patterns.

    Provides methods to group related alerts and identify root causes.
    """

    # Time threshold for considering alerts as "close" in timing
    TIMING_THRESHOLD_SECONDS = 60

    # Minimum confidence for pattern detection
    MIN_PATTERN_CONFIDENCE = 0.5

    def correlate_by_label(
        self,
        alerts: list[CorrelatedAlert],
        label_key: str,
    ) -> list[CorrelationGroup]:
        """
        Correlate alerts by a common label.

        Args:
            alerts: List of alerts to correlate.
            label_key: Label key to group by.

        Returns:
            List of correlation groups.
        """
        with tracer.start_as_current_span(
            "alert.correlate_by_label",
            attributes={
                "correlation.alert_count": len(alerts),
                "correlation.method": "label",
                "correlation.label_key": label_key,
            },
        ) as span:
            groups: dict[str, list[CorrelatedAlert]] = {}

            for alert in alerts:
                label_value = alert.labels.get(label_key)
                if label_value:
                    if label_value not in groups:
                        groups[label_value] = []
                    groups[label_value].append(alert)

            result = [
                CorrelationGroup(
                    group_id=str(uuid.uuid4()),
                    correlation_type="label",
                    label_key=label_key,
                    label_value=label_value,
                    alerts=group_alerts,
                    confidence=self._calculate_group_confidence(group_alerts),
                )
                for label_value, group_alerts in groups.items()
            ]

            span.set_attribute("correlation.group_count", len(result))
            return result

    def correlate_by_time(
        self,
        alerts: list[CorrelatedAlert],
        window_minutes: int = 5,
        reference_time: datetime | None = None,
    ) -> list[CorrelationGroup]:
        """
        Correlate alerts that occur within a time window.

        Args:
            alerts: List of alerts to correlate.
            window_minutes: Time window in minutes.
            reference_time: Reference time for the window start.

        Returns:
            List of correlation groups.
        """
        with tracer.start_as_current_span(
            "alert.correlate_by_time",
            attributes={
                "correlation.alert_count": len(alerts),
                "correlation.method": "time",
                "correlation.window_minutes": window_minutes,
            },
        ) as span:
            if not alerts:
                span.set_attribute("correlation.group_count", 0)
                return []

            # Sort by start time
            sorted_alerts = sorted(alerts, key=lambda a: a.started_at)

            groups: list[CorrelationGroup] = []
            window = timedelta(minutes=window_minutes)

            # Use sliding window approach
            used_alert_ids: set[str] = set()

            for i, anchor in enumerate(sorted_alerts):
                if anchor.alert_id in used_alert_ids:
                    continue

                group_alerts = [anchor]
                used_alert_ids.add(anchor.alert_id)

                for other in sorted_alerts[i + 1 :]:
                    if other.alert_id in used_alert_ids:
                        continue

                    time_diff = other.started_at - anchor.started_at
                    if time_diff <= window:
                        group_alerts.append(other)
                        used_alert_ids.add(other.alert_id)

                groups.append(
                    CorrelationGroup(
                        group_id=str(uuid.uuid4()),
                        correlation_type="time",
                        alerts=group_alerts,
                        confidence=self._calculate_time_confidence(group_alerts, window),
                    )
                )

            span.set_attribute("correlation.group_count", len(groups))
            return groups

    def identify_root_cause(
        self,
        group: CorrelationGroup,
        prefer_critical: bool = False,
    ) -> CorrelatedAlert | None:
        """
        Identify the root cause alert in a group.

        Args:
            group: Correlation group to analyze.
            prefer_critical: Prefer critical severity within timing threshold.

        Returns:
            The root cause alert, or None if group is empty.
        """
        if not group.alerts:
            return None

        # Sort by start time
        sorted_alerts = sorted(group.alerts, key=lambda a: a.started_at)
        earliest = sorted_alerts[0]

        if not prefer_critical:
            return earliest

        # Check if there's a critical alert within threshold of earliest
        threshold = timedelta(seconds=self.TIMING_THRESHOLD_SECONDS)

        for alert in sorted_alerts:
            time_diff = alert.started_at - earliest.started_at
            if time_diff > threshold:
                break

            if alert.severity == "critical":
                return alert

        return earliest

    def calculate_correlation_confidence(
        self,
        alert1: CorrelatedAlert,
        alert2: CorrelatedAlert,
    ) -> float:
        """
        Calculate correlation confidence between two alerts.

        Args:
            alert1: First alert.
            alert2: Second alert.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # Count matching labels
        matching_labels = 0
        total_labels = len(set(alert1.labels.keys()) | set(alert2.labels.keys()))

        if total_labels == 0:
            return 0.0

        for key in alert1.labels:
            if key in alert2.labels and alert1.labels[key] == alert2.labels[key]:
                matching_labels += 1

        label_score = matching_labels / total_labels

        # Factor in time proximity
        time_diff = abs((alert1.started_at - alert2.started_at).total_seconds())
        time_score = max(0.0, 1.0 - (time_diff / 3600))  # Decay over 1 hour

        # Combine scores (labels weighted more heavily)
        confidence = 0.7 * label_score + 0.3 * time_score

        return min(1.0, max(0.0, confidence))

    def detect_pattern(
        self,
        alerts: list[CorrelatedAlert],
    ) -> PatternResult:
        """
        Detect patterns in a group of alerts.

        Args:
            alerts: List of alerts to analyze.

        Returns:
            PatternResult with detected pattern type.
        """
        with tracer.start_as_current_span(
            "alert.detect_pattern",
            attributes={
                "pattern.alert_count": len(alerts),
            },
        ) as span:
            if not alerts:
                span.set_attribute("pattern.type", "unknown")
                span.set_attribute("pattern.reason", "no_alerts")
                return PatternResult(
                    pattern_type=PatternType.UNKNOWN,
                    confidence=0.0,
                    description="No alerts to analyze",
                )

            # Check for resource exhaustion pattern
            resource_pattern = self._check_resource_exhaustion(alerts)
            if resource_pattern.confidence >= self.MIN_PATTERN_CONFIDENCE:
                span.set_attribute("pattern.type", resource_pattern.pattern_type.value)
                span.set_attribute("pattern.confidence", resource_pattern.confidence)
                return resource_pattern

            # Check for cascading failure pattern
            cascading_pattern = self._check_cascading_failure(alerts)
            if cascading_pattern.confidence >= self.MIN_PATTERN_CONFIDENCE:
                span.set_attribute("pattern.type", cascading_pattern.pattern_type.value)
                span.set_attribute("pattern.confidence", cascading_pattern.confidence)
                return cascading_pattern

            span.set_attribute("pattern.type", "unknown")
            span.set_attribute("pattern.confidence", 0.3)
            return PatternResult(
                pattern_type=PatternType.UNKNOWN,
                confidence=0.3,
                description="No clear pattern detected",
            )

    def _calculate_group_confidence(
        self,
        alerts: list[CorrelatedAlert],
    ) -> float:
        """Calculate confidence for a correlation group."""
        if len(alerts) <= 1:
            return 0.5

        # Higher confidence with more alerts
        size_factor = min(1.0, len(alerts) / 5)

        # Higher confidence when alerts are closer in time
        sorted_alerts = sorted(alerts, key=lambda a: a.started_at)
        time_span = (sorted_alerts[-1].started_at - sorted_alerts[0].started_at).total_seconds()
        time_factor = max(0.0, 1.0 - (time_span / 3600))  # Decay over 1 hour

        return 0.5 * size_factor + 0.5 * time_factor

    def _calculate_time_confidence(
        self,
        alerts: list[CorrelatedAlert],
        window: timedelta,
    ) -> float:
        """Calculate confidence for time-based correlation."""
        if len(alerts) <= 1:
            return 0.5

        # More alerts in window = higher confidence
        return min(1.0, 0.5 + 0.1 * len(alerts))

    def _check_resource_exhaustion(
        self,
        alerts: list[CorrelatedAlert],
    ) -> PatternResult:
        """Check for resource exhaustion pattern."""
        resource_alerts = [a for a in alerts if a.name.lower() in RESOURCE_ALERT_NAMES]

        if len(resource_alerts) < 2:
            return PatternResult(
                pattern_type=PatternType.RESOURCE_EXHAUSTION,
                confidence=0.0,
            )

        # Check if alerts are from the same host
        hosts = {a.labels.get("host") for a in resource_alerts if a.labels.get("host")}
        same_host = len(hosts) == 1

        # Calculate confidence
        confidence = 0.5 + (0.2 if same_host else 0.0)
        confidence += min(0.3, 0.1 * len(resource_alerts))

        return PatternResult(
            pattern_type=PatternType.RESOURCE_EXHAUSTION,
            confidence=confidence,
            description="Multiple resource alerts from same host",
            affected_services=[a.labels.get("service", "unknown") for a in resource_alerts],
        )

    def _check_cascading_failure(
        self,
        alerts: list[CorrelatedAlert],
    ) -> PatternResult:
        """Check for cascading failure pattern."""
        if len(alerts) < 2:
            return PatternResult(
                pattern_type=PatternType.CASCADING_FAILURE,
                confidence=0.0,
            )

        # Sort by time
        sorted_alerts = sorted(alerts, key=lambda a: a.started_at)

        # Check for different services with increasing time
        services = [a.labels.get("service") for a in sorted_alerts]
        unique_services = set(s for s in services if s)

        if len(unique_services) < 2:
            return PatternResult(
                pattern_type=PatternType.CASCADING_FAILURE,
                confidence=0.0,
            )

        # Check if alerts have sequential timing
        time_diffs = []
        for i in range(1, len(sorted_alerts)):
            diff = (sorted_alerts[i].started_at - sorted_alerts[i - 1].started_at).total_seconds()
            time_diffs.append(diff)

        # Cascading failures typically have similar time gaps
        if time_diffs:
            avg_diff = sum(time_diffs) / len(time_diffs)
            if avg_diff < 600:  # Within 10 minutes between alerts
                confidence = 0.6 + min(0.3, 0.1 * len(unique_services))
            else:
                confidence = 0.4
        else:
            confidence = 0.3

        return PatternResult(
            pattern_type=PatternType.CASCADING_FAILURE,
            confidence=confidence,
            description="Sequential failures across multiple services",
            affected_services=list(unique_services),
        )
