"""
Alert Correlation Engine Tests.

TDD tests for correlating related alerts and identifying patterns.

Features:
- Group alerts by common labels (service, host, tenant)
- Detect time-based correlations
- Identify root cause vs symptom alerts
- Calculate correlation confidence scores

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestAlertCorrelation:
    """Tests for alert correlation detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_correlate_alerts_by_service(self) -> None:
        """Test correlating alerts from the same service."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
            CorrelationGroup,
        )

        engine = AlertCorrelationEngine()
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="HighCPU",
                severity="warning",
                labels={"service": "api-gateway", "host": "host-1"},
                started_at=datetime.now(UTC) - timedelta(minutes=5),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="HighMemory",
                severity="warning",
                labels={"service": "api-gateway", "host": "host-2"},
                started_at=datetime.now(UTC) - timedelta(minutes=4),
            ),
            CorrelatedAlert(
                alert_id="alert-003",
                name="HighLatency",
                severity="critical",
                labels={"service": "api-gateway", "host": "host-1"},
                started_at=datetime.now(UTC) - timedelta(minutes=3),
            ),
        ]

        groups = engine.correlate_by_label(alerts, label_key="service")

        assert len(groups) == 1
        assert groups[0].label_key == "service"
        assert groups[0].label_value == "api-gateway"
        assert len(groups[0].alerts) == 3

    def test_correlate_alerts_by_host(self) -> None:
        """Test correlating alerts from the same host."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="HighCPU",
                severity="critical",
                labels={"service": "api", "host": "host-1"},
                started_at=datetime.now(UTC),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="DiskFull",
                severity="warning",
                labels={"service": "db", "host": "host-1"},
                started_at=datetime.now(UTC),
            ),
            CorrelatedAlert(
                alert_id="alert-003",
                name="HighMemory",
                severity="warning",
                labels={"service": "cache", "host": "host-2"},
                started_at=datetime.now(UTC),
            ),
        ]

        groups = engine.correlate_by_label(alerts, label_key="host")

        assert len(groups) == 2
        host1_group = next(g for g in groups if g.label_value == "host-1")
        host2_group = next(g for g in groups if g.label_value == "host-2")
        assert len(host1_group.alerts) == 2
        assert len(host2_group.alerts) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestTimeBasedCorrelation:
    """Tests for time-based alert correlation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_correlate_alerts_within_time_window(self) -> None:
        """Test correlating alerts that occur within a time window."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="HighCPU",
                severity="critical",
                labels={"service": "api"},
                started_at=now - timedelta(minutes=10),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="HighMemory",
                severity="warning",
                labels={"service": "api"},
                started_at=now - timedelta(minutes=9),
            ),
            CorrelatedAlert(
                alert_id="alert-003",
                name="HighLatency",
                severity="warning",
                labels={"service": "api"},
                started_at=now - timedelta(minutes=2),
            ),
        ]

        # 5-minute window should group first two alerts
        groups = engine.correlate_by_time(
            alerts, window_minutes=5, reference_time=now - timedelta(minutes=10)
        )

        # Find the group containing the first alert
        first_group = next(
            (g for g in groups if any(a.alert_id == "alert-001" for a in g.alerts)),
            None,
        )
        assert first_group is not None
        assert len(first_group.alerts) == 2
        assert any(a.alert_id == "alert-002" for a in first_group.alerts)

    def test_no_correlation_outside_time_window(self) -> None:
        """Test alerts outside time window are not correlated."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="HighCPU",
                severity="critical",
                labels={"service": "api"},
                started_at=now - timedelta(hours=2),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="HighMemory",
                severity="warning",
                labels={"service": "api"},
                started_at=now,
            ),
        ]

        # 5-minute window should not group alerts 2 hours apart
        groups = engine.correlate_by_time(
            alerts, window_minutes=5, reference_time=now - timedelta(hours=2)
        )

        assert len(groups) >= 1
        first_group = next(
            g for g in groups if any(a.alert_id == "alert-001" for a in g.alerts)
        )
        assert len(first_group.alerts) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestRootCauseAnalysis:
    """Tests for identifying root cause alerts."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_identify_root_cause_by_timing(self) -> None:
        """Test identifying root cause as earliest alert in correlated group."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
            CorrelationGroup,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        group = CorrelationGroup(
            group_id="group-001",
            correlation_type="service",
            label_key="service",
            label_value="api-gateway",
            alerts=[
                CorrelatedAlert(
                    alert_id="alert-003",
                    name="HighLatency",
                    severity="warning",
                    labels={"service": "api-gateway"},
                    started_at=now - timedelta(minutes=1),
                ),
                CorrelatedAlert(
                    alert_id="alert-001",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api-gateway"},
                    started_at=now - timedelta(minutes=5),  # Earliest
                ),
                CorrelatedAlert(
                    alert_id="alert-002",
                    name="HighMemory",
                    severity="warning",
                    labels={"service": "api-gateway"},
                    started_at=now - timedelta(minutes=3),
                ),
            ],
        )

        root_cause = engine.identify_root_cause(group)

        assert root_cause is not None
        assert root_cause.alert_id == "alert-001"  # Earliest alert

    def test_root_cause_prefers_critical_severity(self) -> None:
        """Test root cause prefers critical alerts when timing is close."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
            CorrelationGroup,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        group = CorrelationGroup(
            group_id="group-001",
            correlation_type="service",
            label_key="service",
            label_value="api",
            alerts=[
                CorrelatedAlert(
                    alert_id="alert-001",
                    name="HighMemory",
                    severity="warning",
                    labels={"service": "api"},
                    started_at=now - timedelta(seconds=30),  # Slightly earlier
                ),
                CorrelatedAlert(
                    alert_id="alert-002",
                    name="ServiceDown",
                    severity="critical",
                    labels={"service": "api"},
                    started_at=now,  # Within 1 minute
                ),
            ],
        )

        root_cause = engine.identify_root_cause(group, prefer_critical=True)

        # Should prefer critical when within threshold
        assert root_cause is not None
        assert root_cause.alert_id == "alert-002"


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestCorrelationConfidence:
    """Tests for correlation confidence scoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_high_confidence_for_same_labels(self) -> None:
        """Test high confidence when alerts share multiple labels."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()
        alert1 = CorrelatedAlert(
            alert_id="alert-001",
            name="HighCPU",
            severity="critical",
            labels={"service": "api", "host": "host-1", "env": "prod"},
            started_at=datetime.now(UTC),
        )
        alert2 = CorrelatedAlert(
            alert_id="alert-002",
            name="HighMemory",
            severity="warning",
            labels={"service": "api", "host": "host-1", "env": "prod"},
            started_at=datetime.now(UTC),
        )

        confidence = engine.calculate_correlation_confidence(alert1, alert2)

        assert confidence >= 0.8  # High confidence for matching labels

    def test_low_confidence_for_different_labels(self) -> None:
        """Test low confidence when alerts share few labels."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()
        alert1 = CorrelatedAlert(
            alert_id="alert-001",
            name="HighCPU",
            severity="critical",
            labels={"service": "api", "host": "host-1", "env": "prod"},
            started_at=datetime.now(UTC),
        )
        alert2 = CorrelatedAlert(
            alert_id="alert-002",
            name="DiskFull",
            severity="warning",
            labels={"service": "db", "host": "host-2", "env": "staging"},
            started_at=datetime.now(UTC),
        )

        confidence = engine.calculate_correlation_confidence(alert1, alert2)

        assert confidence < 0.3  # Low confidence for non-matching labels


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestCorrelationPatterns:
    """Tests for detecting correlation patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_detect_cascading_failure_pattern(self) -> None:
        """Test detecting cascading failure pattern."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
            PatternType,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="DatabaseDown",
                severity="critical",
                labels={"service": "database", "tier": "backend"},
                started_at=now - timedelta(minutes=5),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="APIErrors",
                severity="warning",
                labels={"service": "api", "tier": "backend"},
                started_at=now - timedelta(minutes=4),
            ),
            CorrelatedAlert(
                alert_id="alert-003",
                name="WebsiteDown",
                severity="critical",
                labels={"service": "frontend", "tier": "frontend"},
                started_at=now - timedelta(minutes=3),
            ),
        ]

        pattern = engine.detect_pattern(alerts)

        assert pattern.pattern_type == PatternType.CASCADING_FAILURE
        assert pattern.confidence >= 0.6

    def test_detect_resource_exhaustion_pattern(self) -> None:
        """Test detecting resource exhaustion pattern."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
            PatternType,
        )

        engine = AlertCorrelationEngine()
        now = datetime.now(UTC)
        alerts = [
            CorrelatedAlert(
                alert_id="alert-001",
                name="HighCPU",
                severity="warning",
                labels={"service": "api", "host": "host-1"},
                started_at=now - timedelta(minutes=10),
            ),
            CorrelatedAlert(
                alert_id="alert-002",
                name="HighMemory",
                severity="warning",
                labels={"service": "api", "host": "host-1"},
                started_at=now - timedelta(minutes=8),
            ),
            CorrelatedAlert(
                alert_id="alert-003",
                name="HighDisk",
                severity="critical",
                labels={"service": "api", "host": "host-1"},
                started_at=now - timedelta(minutes=5),
            ),
        ]

        pattern = engine.detect_pattern(alerts)

        assert pattern.pattern_type == PatternType.RESOURCE_EXHAUSTION
        assert pattern.confidence >= 0.7


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_correlation")
class TestCorrelationModels:
    """Tests for correlation data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_correlated_alert_model(self) -> None:
        """Test CorrelatedAlert model."""
        from mcp_server_langgraph.alerts.correlation import CorrelatedAlert

        alert = CorrelatedAlert(
            alert_id="alert-001",
            name="TestAlert",
            severity="warning",
            labels={"env": "test"},
            started_at=datetime.now(UTC),
        )

        assert alert.alert_id == "alert-001"
        assert alert.name == "TestAlert"
        assert alert.severity == "warning"

    def test_correlation_group_model(self) -> None:
        """Test CorrelationGroup model."""
        from mcp_server_langgraph.alerts.correlation import (
            CorrelatedAlert,
            CorrelationGroup,
        )

        group = CorrelationGroup(
            group_id="group-001",
            correlation_type="service",
            label_key="service",
            label_value="api",
            alerts=[
                CorrelatedAlert(
                    alert_id="alert-001",
                    name="Test",
                    severity="warning",
                    labels={},
                    started_at=datetime.now(UTC),
                )
            ],
        )

        assert group.group_id == "group-001"
        assert group.correlation_type == "service"
        assert len(group.alerts) == 1

    def test_pattern_result_model(self) -> None:
        """Test PatternResult model."""
        from mcp_server_langgraph.alerts.correlation import (
            PatternResult,
            PatternType,
        )

        result = PatternResult(
            pattern_type=PatternType.CASCADING_FAILURE,
            confidence=0.85,
            description="Cascading failure detected",
        )

        assert result.pattern_type == PatternType.CASCADING_FAILURE
        assert result.confidence == 0.85
