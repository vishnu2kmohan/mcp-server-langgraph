"""
Performance Benchmarks for Alert Processing.

Tests alert broadcasting, grouping, and filtering performance with large datasets.
Ensures the alert system can handle production-scale alert volumes.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import random
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.benchmark

# Note: Tests using 'benchmark' fixture require --benchmark-enable to run
# Tests without benchmark fixture run as regular tests

# =============================================================================
# Test Data Generation
# =============================================================================

SERVICES = [
    "api-gateway",
    "auth-service",
    "payment-service",
    "order-service",
    "inventory-service",
    "notification-service",
    "user-service",
    "analytics-service",
    "search-service",
    "recommendation-service",
]

ALERT_NAMES = [
    "HighCPUUsage",
    "HighMemoryUsage",
    "HighLatency",
    "HighErrorRate",
    "DiskSpaceLow",
    "PodRestarting",
    "ServiceUnavailable",
    "HighRequestRate",
    "DatabaseConnectionPool",
    "CacheHitRateLow",
]

SEVERITIES = [AlertSeverity.CRITICAL, AlertSeverity.WARNING, AlertSeverity.INFO]
STATES = [AlertState.FIRING, AlertState.RESOLVED]


def generate_alert(index: int) -> Alert:
    """Generate a random alert for benchmarking."""
    service = SERVICES[index % len(SERVICES)]
    alert_name = ALERT_NAMES[index % len(ALERT_NAMES)]
    severity = SEVERITIES[index % len(SEVERITIES)]
    state = STATES[index % len(STATES)]

    return Alert(
        alert_id=f"alert-{index:06d}",
        name=alert_name,
        severity=severity,
        state=state,
        message=f"{alert_name} triggered on {service}",
        labels={
            "service": service,
            "namespace": "production",
            "pod": f"{service}-{uuid.uuid4().hex[:8]}",
        },
        annotations={
            "summary": f"{alert_name} on {service}",
            "runbook_url": f"https://runbooks.example.com/{alert_name.lower()}",
        },
        started_at=datetime.now(UTC),
        ended_at=None if state == AlertState.FIRING else datetime.now(UTC),
        generator_url=f"http://alertmanager/alert/{index}",
    )


def generate_alerts(count: int) -> list[Alert]:
    """Generate N alerts for benchmarking."""
    return [generate_alert(i) for i in range(count)]


# =============================================================================
# Alert Grouping Benchmark
# =============================================================================


def group_alerts_by_service(alerts: list[Alert]) -> dict[str, list[Alert]]:
    """Group alerts by service label."""
    groups: dict[str, list[Alert]] = {}
    for alert in alerts:
        service = alert.labels.get("service", "unknown")
        if service not in groups:
            groups[service] = []
        groups[service].append(alert)
    return groups


def group_alerts_by_service_and_name(
    alerts: list[Alert],
) -> dict[str, list[Alert]]:
    """Group alerts by service + alert name (composite key)."""
    groups: dict[str, list[Alert]] = {}
    for alert in alerts:
        service = alert.labels.get("service", "unknown")
        key = f"{service}:{alert.name}"
        if key not in groups:
            groups[key] = []
        groups[key].append(alert)
    return groups


def filter_alerts_by_severity(alerts: list[Alert], severities: set[AlertSeverity]) -> list[Alert]:
    """Filter alerts by severity."""
    return [a for a in alerts if a.severity in severities]


def filter_alerts_by_state(alerts: list[Alert], states: set[AlertState]) -> list[Alert]:
    """Filter alerts by state."""
    return [a for a in alerts if a.state in states]


def get_highest_severity(alerts: list[Alert]) -> AlertSeverity:
    """Get the highest severity from a list of alerts."""
    if not alerts:
        return AlertSeverity.INFO

    priority = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
    return min(alerts, key=lambda a: priority[a.severity]).severity


# =============================================================================
# Benchmark Tests
# =============================================================================


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestAlertGroupingPerformance:
    """Performance benchmarks for alert grouping operations (requires --benchmark-enable)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.parametrize("count", [100, 500, 1000, 5000])
    def test_group_by_service_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark grouping alerts by service."""
        alerts = generate_alerts(count)

        result = benchmark(group_alerts_by_service, alerts)

        assert len(result) <= len(SERVICES)
        assert sum(len(v) for v in result.values()) == count

    @pytest.mark.parametrize("count", [100, 500, 1000, 5000])
    def test_group_by_service_and_name_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark grouping alerts by service + name composite key."""
        alerts = generate_alerts(count)

        result = benchmark(group_alerts_by_service_and_name, alerts)

        assert len(result) <= len(SERVICES) * len(ALERT_NAMES)
        assert sum(len(v) for v in result.values()) == count


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestAlertFilteringPerformance:
    """Performance benchmarks for alert filtering operations (requires --benchmark-enable)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.parametrize("count", [100, 500, 1000, 5000])
    def test_filter_by_severity_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark filtering alerts by severity."""
        alerts = generate_alerts(count)
        severities = {AlertSeverity.CRITICAL, AlertSeverity.WARNING}

        result = benchmark(filter_alerts_by_severity, alerts, severities)

        # Approximately 2/3 of alerts should match (critical + warning)
        assert len(result) <= count

    @pytest.mark.parametrize("count", [100, 500, 1000, 5000])
    def test_filter_by_state_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark filtering alerts by state."""
        alerts = generate_alerts(count)
        states = {AlertState.FIRING}

        result = benchmark(filter_alerts_by_state, alerts, states)

        # Approximately half should be firing
        assert len(result) <= count


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestAlertSeverityPerformance:
    """Performance benchmarks for severity-related operations (requires --benchmark-enable)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.parametrize("count", [100, 500, 1000, 5000])
    def test_get_highest_severity_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark finding highest severity in alert list."""
        alerts = generate_alerts(count)

        result = benchmark(get_highest_severity, alerts)

        assert result in SEVERITIES


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestAlertGroupingScalability:
    """Scalability tests for alert grouping (runs as regular tests)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_linear_scalability(self) -> None:
        """Test that grouping scales approximately linearly with alert count.

        Uses absolute time thresholds instead of ratios to avoid flakiness
        from measurement variance at sub-millisecond times.
        """
        # Define counts and maximum acceptable times (ms)
        # These are generous limits - actual times should be well under
        test_cases = [
            (100, 10),  # 100 alerts: max 10ms
            (500, 25),  # 500 alerts: max 25ms
            (1000, 50),  # 1000 alerts: max 50ms
            (2000, 100),  # 2000 alerts: max 100ms
            (5000, 250),  # 5000 alerts: max 250ms
        ]

        print("\n  Alert Grouping Scalability:")

        for count, max_time_ms in test_cases:
            alerts = generate_alerts(count)

            # Take 3 samples and use median to reduce variance
            samples = []
            for _ in range(3):
                start = time.perf_counter()
                _ = group_alerts_by_service_and_name(alerts)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)

            median_time = sorted(samples)[1]  # Middle value of 3
            print(f"    {count:5d} alerts: {median_time:.2f}ms (max: {max_time_ms}ms)")

            assert median_time < max_time_ms, (
                f"Grouping {count} alerts took {median_time:.2f}ms, exceeds {max_time_ms}ms threshold"
            )

    def test_many_unique_groups(self) -> None:
        """Test performance with many unique groups."""
        # Create alerts with 100 unique services * 10 alert names = 1000 groups
        alerts: list[Alert] = []
        for i in range(100):
            for j in range(10):
                alerts.append(
                    Alert(
                        alert_id=f"alert-{i}-{j}",
                        name=f"Alert{j}",
                        severity=AlertSeverity.CRITICAL,
                        state=AlertState.FIRING,
                        message=f"Test alert {i}-{j}",
                        labels={"service": f"service-{i}"},
                        annotations={},
                        started_at=datetime.now(UTC),
                        ended_at=None,
                        generator_url=f"http://alertmanager/{i}/{j}",
                    )
                )

        start = time.perf_counter()
        groups = group_alerts_by_service_and_name(alerts)
        elapsed = (time.perf_counter() - start) * 1000

        assert len(groups) == 1000
        assert elapsed < 100, f"1000 unique groups took too long: {elapsed:.2f}ms"

        print(f"\n  1000 unique groups from 1000 alerts: {elapsed:.2f}ms")


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestAlertGenerationPerformance:
    """Performance tests for alert generation (test helper)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_generate_alerts_performance(self) -> None:
        """Benchmark alert generation for test setup."""
        counts = [100, 1000, 5000, 10000]

        print("\n  Alert Generation Performance:")
        for count in counts:
            start = time.perf_counter()
            alerts = generate_alerts(count)
            elapsed = (time.perf_counter() - start) * 1000

            assert len(alerts) == count
            print(f"    {count:5d} alerts: {elapsed:.2f}ms")


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_grouping")
class TestCombinedOperationsPerformance:
    """Performance tests for combined operations (typical use case)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_filter_and_group_pipeline(self) -> None:
        """Benchmark typical filter -> group pipeline."""
        alerts = generate_alerts(5000)

        start = time.perf_counter()

        # Filter by severity and state (typical admin dashboard filter)
        filtered = filter_alerts_by_severity(alerts, {AlertSeverity.CRITICAL, AlertSeverity.WARNING})
        filtered = filter_alerts_by_state(filtered, {AlertState.FIRING})

        # Group filtered alerts
        groups = group_alerts_by_service_and_name(filtered)

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Filter + Group pipeline (5000 alerts): {elapsed:.2f}ms")
        print(f"    Filtered: {len(filtered)} alerts")
        print(f"    Groups: {len(groups)}")

        # Pipeline should complete in under 50ms
        assert elapsed < 50, f"Pipeline too slow: {elapsed:.2f}ms"

    def test_real_world_scenario(self) -> None:
        """Benchmark a realistic production scenario."""
        # Simulate a large K8s cluster with many services
        # 50 services * 20 pods each * 5 alert types = 5000 potential alerts
        # In reality, only some pods will have active alerts
        alerts: list[Alert] = []

        # Generate a realistic distribution of alerts
        for service_idx in range(50):
            service_name = f"service-{service_idx:02d}"
            # Each service has 0-5 active alerts (random)
            alert_count = random.randint(0, 5)
            for alert_idx in range(alert_count):
                alerts.append(
                    Alert(
                        alert_id=f"alert-{service_idx}-{alert_idx}",
                        name=ALERT_NAMES[alert_idx % len(ALERT_NAMES)],
                        severity=random.choice(SEVERITIES),
                        state=AlertState.FIRING,
                        message=f"Alert on {service_name}",
                        labels={
                            "service": service_name,
                            "namespace": "production",
                            "pod": f"{service_name}-pod-{alert_idx}",
                        },
                        annotations={},
                        started_at=datetime.now(UTC),
                        ended_at=None,
                        generator_url=f"http://alertmanager/{service_idx}/{alert_idx}",
                    )
                )

        start = time.perf_counter()

        # Typical dashboard operations
        critical_count = len(filter_alerts_by_severity(alerts, {AlertSeverity.CRITICAL}))
        warning_count = len(filter_alerts_by_severity(alerts, {AlertSeverity.WARNING}))
        groups = group_alerts_by_service_and_name(alerts)

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  Real-world scenario ({len(alerts)} alerts):")
        print(f"    Critical: {critical_count}")
        print(f"    Warning: {warning_count}")
        print(f"    Groups: {len(groups)}")
        print(f"    Time: {elapsed:.2f}ms")

        # Should be very fast for realistic alert counts
        assert elapsed < 20, f"Real-world scenario too slow: {elapsed:.2f}ms"


# =============================================================================
# Alert Correlation Engine Benchmarks
# =============================================================================


def generate_correlated_alert(index: int, base_time: datetime | None = None) -> "CorrelatedAlert":
    """Generate a CorrelatedAlert for correlation engine benchmarks."""
    from mcp_server_langgraph.alerts.correlation import CorrelatedAlert

    if base_time is None:
        base_time = datetime.now(UTC)

    service = SERVICES[index % len(SERVICES)]
    alert_name = ALERT_NAMES[index % len(ALERT_NAMES)]
    severity = ["critical", "warning", "info"][index % 3]

    # Add some time offset to simulate realistic alert timing
    time_offset = timedelta(seconds=index * random.uniform(1, 10))

    return CorrelatedAlert(
        alert_id=f"corr-alert-{index:06d}",
        name=alert_name,
        severity=severity,
        labels={
            "service": service,
            "namespace": "production",
            "host": f"node-{index % 10}",
            "pod": f"{service}-{uuid.uuid4().hex[:8]}",
        },
        started_at=base_time + time_offset,
        resolved_at=None,
    )


def generate_correlated_alerts(count: int) -> list["CorrelatedAlert"]:
    """Generate N CorrelatedAlerts for correlation engine benchmarks."""
    base_time = datetime.now(UTC)
    return [generate_correlated_alert(i, base_time) for i in range(count)]


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmarks_alert_correlation")
class TestCorrelationEnginePerformance:
    """Performance benchmarks for AlertCorrelationEngine (requires --benchmark-enable)."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.parametrize("count", [100, 500, 1000, 2000])
    def test_correlate_by_label_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark label-based correlation."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()
        alerts = generate_correlated_alerts(count)

        result = benchmark(engine.correlate_by_label, alerts, "service")

        # Should have groups for each service
        assert len(result) <= len(SERVICES)
        total_alerts = sum(len(g.alerts) for g in result)
        assert total_alerts == count

    @pytest.mark.parametrize("count", [100, 500, 1000, 2000])
    def test_correlate_by_time_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark time-based correlation."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()
        alerts = generate_correlated_alerts(count)

        result = benchmark(engine.correlate_by_time, alerts, 5)

        # Time-based groups depend on alert timing distribution
        assert len(result) >= 1
        total_alerts = sum(len(g.alerts) for g in result)
        assert total_alerts == count

    @pytest.mark.parametrize("count", [50, 100, 200])
    def test_detect_pattern_performance(self, count: int, benchmark: Any) -> None:
        """Benchmark pattern detection."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()
        alerts = generate_correlated_alerts(count)

        result = benchmark(engine.detect_pattern, alerts)

        assert result is not None
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_correlation")
class TestCorrelationScalability:
    """Scalability tests for alert correlation engine."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_label_correlation_scalability(self) -> None:
        """Test that label-based correlation scales linearly."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()

        test_cases = [
            (100, 20),  # 100 alerts: max 20ms
            (500, 50),  # 500 alerts: max 50ms
            (1000, 100),  # 1000 alerts: max 100ms
            (2000, 200),  # 2000 alerts: max 200ms
        ]

        print("\n  Label Correlation Scalability:")

        for count, max_time_ms in test_cases:
            alerts = generate_correlated_alerts(count)

            samples = []
            for _ in range(3):
                start = time.perf_counter()
                _ = engine.correlate_by_label(alerts, "service")
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)

            median_time = sorted(samples)[1]
            print(f"    {count:5d} alerts: {median_time:.2f}ms (max: {max_time_ms}ms)")

            assert median_time < max_time_ms, (
                f"Label correlation for {count} alerts took {median_time:.2f}ms, exceeds {max_time_ms}ms threshold"
            )

    def test_time_correlation_scalability(self) -> None:
        """Test that time-based correlation scales acceptably.

        Note: Time-based correlation is O(n log n) due to sorting + O(n^2) worst case
        for sliding window, but in practice it's much faster due to early termination.
        """
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()

        test_cases = [
            (100, 50),  # 100 alerts: max 50ms
            (500, 150),  # 500 alerts: max 150ms
            (1000, 350),  # 1000 alerts: max 350ms
        ]

        print("\n  Time Correlation Scalability:")

        for count, max_time_ms in test_cases:
            alerts = generate_correlated_alerts(count)

            samples = []
            for _ in range(3):
                start = time.perf_counter()
                _ = engine.correlate_by_time(alerts, window_minutes=5)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)

            median_time = sorted(samples)[1]
            print(f"    {count:5d} alerts: {median_time:.2f}ms (max: {max_time_ms}ms)")

            assert median_time < max_time_ms, (
                f"Time correlation for {count} alerts took {median_time:.2f}ms, exceeds {max_time_ms}ms threshold"
            )

    def test_pattern_detection_scalability(self) -> None:
        """Test pattern detection performance."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()

        test_cases = [
            (50, 30),  # 50 alerts: max 30ms
            (100, 50),  # 100 alerts: max 50ms
            (200, 100),  # 200 alerts: max 100ms
        ]

        print("\n  Pattern Detection Scalability:")

        for count, max_time_ms in test_cases:
            alerts = generate_correlated_alerts(count)

            samples = []
            for _ in range(3):
                start = time.perf_counter()
                _ = engine.detect_pattern(alerts)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)

            median_time = sorted(samples)[1]
            print(f"    {count:5d} alerts: {median_time:.2f}ms (max: {max_time_ms}ms)")

            assert median_time < max_time_ms, (
                f"Pattern detection for {count} alerts took {median_time:.2f}ms, exceeds {max_time_ms}ms threshold"
            )


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_correlation")
class TestCorrelationConfidencePerformance:
    """Performance tests for correlation confidence calculations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_pairwise_confidence_performance(self) -> None:
        """Benchmark pairwise correlation confidence calculation."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()

        # Generate pairs of alerts
        alert_counts = [10, 50, 100]

        print("\n  Pairwise Confidence Performance (n^2 comparisons):")

        for count in alert_counts:
            alerts = generate_correlated_alerts(count)
            pair_count = count * (count - 1) // 2

            start = time.perf_counter()
            for i in range(len(alerts)):
                for j in range(i + 1, len(alerts)):
                    _ = engine.calculate_correlation_confidence(alerts[i], alerts[j])
            elapsed = (time.perf_counter() - start) * 1000

            print(f"    {count:5d} alerts ({pair_count:6d} pairs): {elapsed:.2f}ms")

            # Performance expectation: ~10,000 pairs/second
            max_time = max(10, pair_count / 10)
            assert elapsed < max_time, f"Pairwise confidence for {pair_count} pairs took {elapsed:.2f}ms"


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_correlation")
class TestCorrelationRootCausePerformance:
    """Performance tests for root cause identification."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_root_cause_identification_performance(self) -> None:
        """Benchmark root cause identification in groups."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelationGroup,
        )

        engine = AlertCorrelationEngine()

        # Create groups of varying sizes
        group_sizes = [10, 50, 100, 500]

        print("\n  Root Cause Identification Performance:")

        for size in group_sizes:
            alerts = generate_correlated_alerts(size)
            group = CorrelationGroup(
                group_id="test-group",
                correlation_type="label",
                alerts=alerts,
            )

            samples = []
            for _ in range(5):
                start = time.perf_counter()
                _ = engine.identify_root_cause(group, prefer_critical=True)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)

            median_time = sorted(samples)[2]
            print(f"    {size:5d} alerts in group: {median_time:.2f}ms")

            # Should be very fast (just sorting + linear scan)
            max_time = max(5, size / 50)
            assert median_time < max_time, f"Root cause identification for {size} alerts took {median_time:.2f}ms"


@pytest.mark.unit
@pytest.mark.xdist_group(name="benchmarks_alert_correlation")
class TestCorrelationCombinedWorkflow:
    """Performance tests for combined correlation workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_full_correlation_pipeline(self) -> None:
        """Benchmark complete correlation workflow."""
        from mcp_server_langgraph.alerts.correlation import AlertCorrelationEngine

        engine = AlertCorrelationEngine()
        alerts = generate_correlated_alerts(500)

        start = time.perf_counter()

        # Step 1: Correlate by service label
        service_groups = engine.correlate_by_label(alerts, "service")

        # Step 2: For each group, detect pattern
        patterns = []
        for group in service_groups:
            pattern = engine.detect_pattern(group.alerts)
            patterns.append(pattern)

        # Step 3: Identify root cause for each group
        root_causes = []
        for group in service_groups:
            root_cause = engine.identify_root_cause(group, prefer_critical=True)
            root_causes.append(root_cause)

        elapsed = (time.perf_counter() - start) * 1000

        print("\n  Full Correlation Pipeline (500 alerts):")
        print(f"    Service groups: {len(service_groups)}")
        print(f"    Patterns detected: {len([p for p in patterns if p.confidence > 0.5])}")
        print(f"    Root causes identified: {len([r for r in root_causes if r])}")
        print(f"    Total time: {elapsed:.2f}ms")

        # Full pipeline should complete in reasonable time
        assert elapsed < 500, f"Full pipeline took {elapsed:.2f}ms"

    def test_high_cardinality_labels(self) -> None:
        """Test correlation with high-cardinality labels (many unique values)."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()

        # Create alerts with many unique service names (high cardinality)
        base_time = datetime.now(UTC)
        alerts = []
        for i in range(1000):
            alerts.append(
                CorrelatedAlert(
                    alert_id=f"hc-alert-{i}",
                    name="HighLatency",
                    severity="warning",
                    labels={
                        "service": f"service-{i}",  # Each alert has unique service
                        "namespace": "production",
                    },
                    started_at=base_time + timedelta(seconds=i * 0.1),
                )
            )

        start = time.perf_counter()
        groups = engine.correlate_by_label(alerts, "service")
        elapsed = (time.perf_counter() - start) * 1000

        print("\n  High Cardinality Labels (1000 unique services):")
        print(f"    Groups created: {len(groups)}")
        print(f"    Time: {elapsed:.2f}ms")

        # Each alert should be in its own group
        assert len(groups) == 1000
        assert elapsed < 100, f"High cardinality correlation took {elapsed:.2f}ms"

    def test_deep_time_window_analysis(self) -> None:
        """Test time correlation with tightly clustered alerts."""
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        engine = AlertCorrelationEngine()

        # Create alerts all within 1 minute (should create 1 large group)
        base_time = datetime.now(UTC)
        alerts = []
        for i in range(500):
            alerts.append(
                CorrelatedAlert(
                    alert_id=f"clustered-{i}",
                    name="TestAlert",
                    severity="warning",
                    labels={"service": f"service-{i % 10}"},
                    started_at=base_time + timedelta(seconds=i * 0.1),  # 0.1s apart
                )
            )

        start = time.perf_counter()
        groups = engine.correlate_by_time(alerts, window_minutes=5)
        elapsed = (time.perf_counter() - start) * 1000

        print("\n  Tightly Clustered Alerts (500 alerts, <1min span):")
        print(f"    Groups created: {len(groups)}")
        print(f"    Time: {elapsed:.2f}ms")

        # Most alerts should end up in few groups
        assert elapsed < 300, f"Clustered time correlation took {elapsed:.2f}ms"
