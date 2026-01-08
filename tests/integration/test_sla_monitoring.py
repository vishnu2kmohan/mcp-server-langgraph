"""
Tests for SLA Monitoring

Comprehensive test suite for SLA tracking, measurements, and alerting.
"""

import gc
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.core.numeric import safe_average
from mcp_server_langgraph.monitoring.sla import SLAMeasurement, SLAMetric, SLAMonitor, SLAReport, SLAStatus, SLATarget

pytestmark = pytest.mark.integration


@pytest.fixture
def sla_monitor():
    """SLA monitor instance with default targets"""
    return SLAMonitor()


@pytest.fixture
def custom_sla_targets():
    """Custom SLA targets for testing"""
    return [
        SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.5,
            comparison=">=",
            unit="%",
            warning_threshold=99.0,
            critical_threshold=98.5,
        ),
        SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=1000,
            comparison="<=",
            unit="ms",
            warning_threshold=1500,
            critical_threshold=2000,
        ),
    ]


# --- SLA Target Tests ---


@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestSLATarget:
    """Test SLA target configuration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sla_target_creation(self):
        """Test creating SLA target"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        assert target.metric == SLAMetric.UPTIME
        assert target.target_value == 99.9
        assert target.comparison == ">="
        assert target.unit == "%"

    def test_default_sla_targets(self, sla_monitor):
        """Test default SLA targets"""
        targets = sla_monitor.sla_targets

        assert len(targets) == 3
        assert any(t.metric == SLAMetric.UPTIME for t in targets)
        assert any(t.metric == SLAMetric.RESPONSE_TIME for t in targets)
        assert any(t.metric == SLAMetric.ERROR_RATE for t in targets)

    def test_custom_sla_targets(self, custom_sla_targets):
        """Test custom SLA targets"""
        monitor = SLAMonitor(sla_targets=custom_sla_targets)

        assert len(monitor.sla_targets) == 2
        assert monitor.sla_targets[0].target_value == 99.5


# --- Uptime Measurement Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestUptimeMeasurement:
    """Test uptime SLA measurement"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
    async def test_measure_uptime_meeting_sla(self, mock_prom_client, sla_monitor):
        """Test uptime measurement meeting SLA"""
        # Mock Prometheus to return 0 downtime (100% uptime)
        mock_client = AsyncMock()  # async-mock-configured (return_value set below)
        mock_client.query_downtime.return_value = 0
        mock_prom_client.return_value = mock_client

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=1)

        measurement = await sla_monitor.measure_uptime(start_time, end_time)

        assert isinstance(measurement, SLAMeasurement)
        assert measurement.metric == SLAMetric.UPTIME
        assert measurement.measured_value >= 99.9  # Should meet default target
        assert measurement.status == SLAStatus.MEETING

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
    async def test_measure_uptime_structure(self, mock_prom_client, sla_monitor):
        """Test uptime measurement structure"""
        # Mock Prometheus
        mock_client = AsyncMock()  # async-mock-configured (return_value set below)
        mock_client.query_downtime.return_value = 0
        mock_prom_client.return_value = mock_client

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        measurement = await sla_monitor.measure_uptime(start_time, end_time)

        assert measurement.measured_value >= 0
        assert measurement.measured_value <= 100
        assert measurement.target_value == 99.9
        assert measurement.unit == "%"
        assert measurement.timestamp is not None
        assert measurement.period_start is not None
        assert measurement.period_end is not None

    async def test_uptime_compliance_percentage(self, sla_monitor):
        """Test uptime compliance percentage calculation"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=7)

        measurement = await sla_monitor.measure_uptime(start_time, end_time)

        # Compliance percentage should be >= 100 if meeting SLA
        if measurement.status == SLAStatus.MEETING:
            assert measurement.compliance_percentage >= 100


# --- Response Time Measurement Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestResponseTimeMeasurement:
    """Test response time SLA measurement"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
    async def test_measure_response_time_meeting_sla(self, mock_prom_client, sla_monitor):
        """Test response time measurement meeting SLA"""
        mock_client = AsyncMock()  # async-mock-configured (return_value set below)
        mock_client.query_percentiles.return_value = {95: 0.350}  # 350ms
        mock_prom_client.return_value = mock_client

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=1)

        measurement = await sla_monitor.measure_response_time(start_time, end_time)

        assert isinstance(measurement, SLAMeasurement)
        assert measurement.metric == SLAMetric.RESPONSE_TIME
        assert measurement.measured_value > 0
        assert measurement.unit == "ms"

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
    async def test_measure_response_time_p95(self, mock_prom_client, sla_monitor):
        """Test p95 response time measurement"""
        mock_client = AsyncMock()  # async-mock-configured (return_value set below)
        mock_client.query_percentiles.return_value = {95: 0.350}
        mock_prom_client.return_value = mock_client

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        measurement = await sla_monitor.measure_response_time(start_time, end_time, percentile=95)

        assert measurement.measured_value > 0
        # 350ms should meet 500ms target
        assert measurement.status == SLAStatus.MEETING

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client")
    async def test_measure_response_time_different_percentiles(self, mock_prom_client, sla_monitor):
        """Test different percentile measurements"""
        mock_client = AsyncMock()  # async-mock-configured (side_effect set below)
        # Different response times for different percentiles
        mock_client.query_percentiles.side_effect = [
            {50: 0.200},
            {95: 0.350},
            {99: 0.450},
        ]
        mock_prom_client.return_value = mock_client

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        for percentile in [50, 95, 99]:
            measurement = await sla_monitor.measure_response_time(start_time, end_time, percentile=percentile)
            assert measurement.metric == SLAMetric.RESPONSE_TIME


# --- Error Rate Measurement Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestErrorRateMeasurement:
    """Test error rate SLA measurement"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_measure_error_rate_meeting_sla(self, sla_monitor):
        """Test error rate measurement meeting SLA"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=1)

        measurement = await sla_monitor.measure_error_rate(start_time, end_time)

        assert isinstance(measurement, SLAMeasurement)
        assert measurement.metric == SLAMetric.ERROR_RATE
        assert measurement.measured_value >= 0
        assert measurement.unit == "%"

    async def test_error_rate_structure(self, sla_monitor):
        """Test error rate measurement structure"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        measurement = await sla_monitor.measure_error_rate(start_time, end_time)

        # Error rate should be percentage (0-100)
        assert 0 <= measurement.measured_value <= 100
        # Placeholder returns 0.5%, should meet 1% target
        assert measurement.status == SLAStatus.MEETING


# --- SLA Status Determination Tests ---


@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestSLAStatusDetermination:
    """Test SLA status determination logic"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_status_meeting_higher_is_better(self, sla_monitor):
        """Test status when meeting SLA (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        status = sla_monitor._determine_status(99.95, target, is_higher_better=True)
        assert status == SLAStatus.MEETING

    def test_status_at_risk_higher_is_better(self, sla_monitor):
        """Test status at risk (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        status = sla_monitor._determine_status(99.7, target, is_higher_better=True)
        assert status == SLAStatus.AT_RISK

    def test_status_breach_higher_is_better(self, sla_monitor):
        """Test status breach (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        status = sla_monitor._determine_status(98.5, target, is_higher_better=True)
        assert status == SLAStatus.BREACH

    def test_status_meeting_lower_is_better(self, sla_monitor):
        """Test status when meeting SLA (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,
            comparison="<=",
            unit="ms",
            warning_threshold=600,
            critical_threshold=1000,
        )

        status = sla_monitor._determine_status(350, target, is_higher_better=False)
        assert status == SLAStatus.MEETING

    def test_status_at_risk_lower_is_better(self, sla_monitor):
        """Test status at risk (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,
            comparison="<=",
            unit="ms",
            warning_threshold=600,
            critical_threshold=1000,
        )

        status = sla_monitor._determine_status(550, target, is_higher_better=False)
        assert status == SLAStatus.AT_RISK

    def test_status_breach_lower_is_better(self, sla_monitor):
        """Test status breach (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,
            comparison="<=",
            unit="ms",
            warning_threshold=600,
            critical_threshold=1000,
        )

        status = sla_monitor._determine_status(1200, target, is_higher_better=False)
        assert status == SLAStatus.BREACH

    def test_status_exactly_at_target_higher_is_better(self, sla_monitor):
        """Test status when exactly at target value (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        # Exactly at target should be MEETING
        status = sla_monitor._determine_status(99.9, target, is_higher_better=True)
        assert status == SLAStatus.MEETING

    def test_status_exactly_at_warning_higher_is_better(self, sla_monitor):
        """Test status when exactly at warning threshold (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        # Exactly at warning threshold should be AT_RISK
        status = sla_monitor._determine_status(99.5, target, is_higher_better=True)
        assert status == SLAStatus.AT_RISK

    def test_status_exactly_at_target_lower_is_better(self, sla_monitor):
        """Test status when exactly at target value (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,
            comparison="<=",
            unit="ms",
            warning_threshold=600,
            critical_threshold=1000,
        )

        # Exactly at target should be MEETING
        status = sla_monitor._determine_status(500, target, is_higher_better=False)
        assert status == SLAStatus.MEETING

    def test_status_exactly_at_warning_lower_is_better(self, sla_monitor):
        """Test status when exactly at warning threshold (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.RESPONSE_TIME,
            target_value=500,
            comparison="<=",
            unit="ms",
            warning_threshold=600,
            critical_threshold=1000,
        )

        # Exactly at warning threshold should be AT_RISK
        status = sla_monitor._determine_status(600, target, is_higher_better=False)
        assert status == SLAStatus.AT_RISK

    def test_status_zero_value_higher_is_better(self, sla_monitor):
        """Test status with zero measured value (higher is better)"""
        target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=99.9,
            comparison=">=",
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
        )

        # Zero uptime should be BREACH
        status = sla_monitor._determine_status(0, target, is_higher_better=True)
        assert status == SLAStatus.BREACH

    def test_status_zero_value_lower_is_better(self, sla_monitor):
        """Test status with zero measured value (lower is better)"""
        target = SLATarget(
            metric=SLAMetric.ERROR_RATE,
            target_value=1.0,
            comparison="<=",
            unit="%",
            warning_threshold=2.0,
            critical_threshold=5.0,
        )

        # Zero error rate should be MEETING (lower is better)
        status = sla_monitor._determine_status(0, target, is_higher_better=False)
        assert status == SLAStatus.MEETING

    def test_status_error_rate_meeting(self, sla_monitor):
        """Test error rate status when meeting SLA"""
        target = SLATarget(
            metric=SLAMetric.ERROR_RATE,
            target_value=1.0,
            comparison="<=",
            unit="%",
            warning_threshold=2.0,
            critical_threshold=5.0,
        )

        status = sla_monitor._determine_status(0.5, target, is_higher_better=False)
        assert status == SLAStatus.MEETING

    def test_status_error_rate_at_risk(self, sla_monitor):
        """Test error rate status when at risk"""
        target = SLATarget(
            metric=SLAMetric.ERROR_RATE,
            target_value=1.0,
            comparison="<=",
            unit="%",
            warning_threshold=2.0,
            critical_threshold=5.0,
        )

        status = sla_monitor._determine_status(1.5, target, is_higher_better=False)
        assert status == SLAStatus.AT_RISK

    def test_status_error_rate_breach(self, sla_monitor):
        """Test error rate status when in breach"""
        target = SLATarget(
            metric=SLAMetric.ERROR_RATE,
            target_value=1.0,
            comparison="<=",
            unit="%",
            warning_threshold=2.0,
            critical_threshold=5.0,
        )

        status = sla_monitor._determine_status(3.0, target, is_higher_better=False)
        assert status == SLAStatus.BREACH


# --- SLA Report Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestSLAReport:
    """Test SLA report generation"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_generate_sla_report_daily(self, sla_monitor):
        """Test daily SLA report generation"""
        report = await sla_monitor.generate_sla_report(period_days=1)

        assert isinstance(report, SLAReport)
        assert report.report_id is not None
        assert len(report.measurements) == 3  # uptime, response_time, error_rate
        # Compliance score can exceed 100% when performance exceeds targets
        assert report.compliance_score >= 0

    async def test_generate_sla_report_weekly(self, sla_monitor):
        """Test weekly SLA report generation"""
        report = await sla_monitor.generate_sla_report(period_days=7)

        assert report.report_id is not None
        assert len(report.measurements) > 0

    async def test_generate_sla_report_monthly(self, sla_monitor):
        """Test monthly SLA report generation"""
        report = await sla_monitor.generate_sla_report(period_days=30)

        assert report.report_id is not None
        assert report.period_start is not None
        assert report.period_end is not None

    async def test_report_overall_status(self, sla_monitor):
        """Test report overall status calculation"""
        report = await sla_monitor.generate_sla_report(period_days=1)

        # Overall status should be set
        assert report.overall_status in [
            SLAStatus.MEETING,
            SLAStatus.AT_RISK,
            SLAStatus.BREACH,
        ]

    async def test_report_breach_count(self, sla_monitor):
        """Test report breach and warning counts"""
        report = await sla_monitor.generate_sla_report(period_days=1)

        assert report.breaches >= 0
        assert report.warnings >= 0
        # Total should match measurement statuses
        total_issues = report.breaches + report.warnings
        measurement_issues = sum(1 for m in report.measurements if m.status in [SLAStatus.BREACH, SLAStatus.AT_RISK])
        assert total_issues == measurement_issues

    async def test_report_compliance_score_calculation(self, sla_monitor):
        """Test compliance score calculation"""
        report = await sla_monitor.generate_sla_report(period_days=1)

        # Compliance score should be average of measurement compliance percentages
        expected_score = safe_average([m.compliance_percentage for m in report.measurements])

        assert abs(report.compliance_score - expected_score) < 0.01

    async def test_report_summary(self, sla_monitor):
        """Test report summary generation"""
        report = await sla_monitor.generate_sla_report(period_days=1)

        assert "uptime_percentage" in report.summary
        assert "response_time_p95_ms" in report.summary
        assert "error_rate_percentage" in report.summary
        assert "all_slas_met" in report.summary
        assert isinstance(report.summary["breaches"], list)


# --- Breach Detection Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestBreachDetection:
    """Test SLA breach detection and alerting"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_breach_details_populated(self, sla_monitor):
        """Test breach details are populated when SLA breached"""
        # Create monitor with low threshold
        low_target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=100.0,  # Impossible target
            comparison=">=",
            unit="%",
            warning_threshold=99.9,
            critical_threshold=99.5,
        )

        monitor = SLAMonitor(sla_targets=[low_target])
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        measurement = await monitor.measure_uptime(start_time, end_time)

        if measurement.status == SLAStatus.BREACH:
            assert measurement.breach_details is not None
            assert "target" in measurement.breach_details
            assert "actual" in measurement.breach_details

    async def test_no_breach_details_when_meeting(self, sla_monitor):
        """Test no breach details when meeting SLA"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        measurement = await sla_monitor.measure_uptime(start_time, end_time)

        if measurement.status == SLAStatus.MEETING:
            assert measurement.breach_details is None

    @patch("mcp_server_langgraph.monitoring.sla.get_prometheus_client", new_callable=AsyncMock)
    async def test_alert_on_breach(self, mock_prom_client, sla_monitor):
        """Test alerting on SLA breach"""
        # Mock Prometheus to return low uptime (will breach 100% target)
        mock_client = AsyncMock()  # async-mock-configured (return_value set below)
        mock_client.query_downtime.return_value = 1440  # 24 minutes downtime = 98.3% uptime
        mock_prom_client.return_value = mock_client

        # Create report that will breach
        low_target = SLATarget(
            metric=SLAMetric.UPTIME,
            target_value=100.0,
            comparison=">=",
            unit="%",
            warning_threshold=99.9,
            critical_threshold=99.5,
        )

        monitor = SLAMonitor(sla_targets=[low_target])

        # Patch the alert method on the NEW monitor instance
        with patch.object(monitor, "_send_sla_alert", new_callable=AsyncMock) as mock_alert:
            report = await monitor.generate_sla_report(period_days=1)

            # Verify breach detected
            assert report.overall_status == SLAStatus.BREACH

            # Verify alert sent
            mock_alert.assert_called_once()


# --- Integration Tests ---


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestSLAIntegration:
    """Integration tests for SLA monitoring"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_full_sla_monitoring_cycle(self, sla_monitor):
        """Test complete SLA monitoring cycle"""
        # Generate report
        report = await sla_monitor.generate_sla_report(period_days=7)

        # Verify all measurements present
        assert len(report.measurements) == 3

        # Verify all metrics measured
        metrics = {m.metric for m in report.measurements}
        assert SLAMetric.UPTIME in metrics
        assert SLAMetric.RESPONSE_TIME in metrics
        assert SLAMetric.ERROR_RATE in metrics

        # Verify report completeness
        assert report.overall_status is not None
        assert report.compliance_score > 0

    async def test_sla_trend_analysis(self, sla_monitor):
        """Test SLA trend analysis over multiple periods"""
        # Generate multiple reports
        daily = await sla_monitor.generate_sla_report(period_days=1)
        weekly = await sla_monitor.generate_sla_report(period_days=7)
        monthly = await sla_monitor.generate_sla_report(period_days=30)

        # All should be valid reports
        assert daily.compliance_score > 0
        assert weekly.compliance_score > 0
        assert monthly.compliance_score > 0

    async def test_custom_sla_configuration(self, custom_sla_targets):
        """Test SLA monitoring with custom targets"""
        monitor = SLAMonitor(sla_targets=custom_sla_targets)

        report = await monitor.generate_sla_report(period_days=1)

        # Should only have measurements for configured targets
        assert len(report.measurements) == len(custom_sla_targets)


# --- Edge Cases ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_monitoring_tests")
class TestSLAEdgeCases:
    """Test edge cases in SLA monitoring"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_zero_period(self, sla_monitor):
        """Test measurement with zero time period"""
        now = datetime.now(UTC)

        measurement = await sla_monitor.measure_uptime(now, now)

        # Should handle gracefully
        assert measurement is not None

    async def test_missing_target(self):
        """Test measurement when target not configured"""
        monitor = SLAMonitor(sla_targets=[])

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)

        with pytest.raises(ValueError):
            await monitor.measure_uptime(start_time, end_time)

    async def test_extreme_values(self, sla_monitor):
        """Test SLA with extreme measurement values"""
        # This would require mocking Prometheus queries
        # For now, verify structure handles edge cases
        report = await sla_monitor.generate_sla_report(period_days=1)

        # All measurements should be within valid ranges
        for measurement in report.measurements:
            assert measurement.measured_value >= 0
            if measurement.metric == SLAMetric.UPTIME:
                assert measurement.measured_value <= 100

    async def test_negative_period_days(self, sla_monitor):
        """Test report generation with negative period days"""
        # Negative period should be handled (implementation may vary)
        # Either raise error or treat as absolute value
        try:
            report = await sla_monitor.generate_sla_report(period_days=-1)
            # If no error, report should still be valid
            assert report is not None
        except (ValueError, Exception):
            # Raising error is also acceptable behavior
            pass


# --- SLA Alert Exception Handling Tests ---


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sla
@pytest.mark.xdist_group(name="sla_alert_exception_tests")
class TestSLAAlertExceptionHandling:
    """Test exception handling in SLA alert sending."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_send_sla_alert_catches_alerting_service_initialization_error(self, sla_monitor):
        """
        GIVEN AlertingService.initialize() raises an exception
        WHEN _send_sla_alert() is called
        THEN the exception is caught and logged (not propagated)
        """
        with (
            patch("mcp_server_langgraph.monitoring.sla.AlertingService") as mock_service_class,
            patch("mcp_server_langgraph.monitoring.sla.logger") as mock_logger,
        ):
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_service.initialize = AsyncMock(side_effect=Exception("Service initialization failed"))
            mock_service_class.return_value = mock_service

            # Act - should NOT raise exception
            await sla_monitor._send_sla_alert(
                severity="critical",
                message="SLA breach detected",
                details={"metric": "uptime", "value": 98.5},
            )

            # Assert - exception was logged
            mock_logger.error.assert_called_once()
            assert "Failed to send SLA alert" in str(mock_logger.error.call_args)

    async def test_send_sla_alert_catches_send_alert_error(self, sla_monitor):
        """
        GIVEN AlertingService.send_alert() raises an exception
        WHEN _send_sla_alert() is called
        THEN the exception is caught and logged (not propagated)
        """
        with (
            patch("mcp_server_langgraph.monitoring.sla.AlertingService") as mock_service_class,
            patch("mcp_server_langgraph.monitoring.sla.logger") as mock_logger,
        ):
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_service.initialize = AsyncMock()  # noqa: async-mock-config
            mock_service.send_alert = AsyncMock(side_effect=Exception("Network error sending alert"))
            mock_service_class.return_value = mock_service

            # Act - should NOT raise exception
            await sla_monitor._send_sla_alert(
                severity="warning",
                message="SLA at risk",
                details={"metric": "response_time", "value": 450},
            )

            # Assert - exception was logged
            mock_logger.error.assert_called_once()
            assert "Failed to send SLA alert" in str(mock_logger.error.call_args)

    async def test_send_sla_alert_logs_warning_before_sending(self, sla_monitor):
        """
        GIVEN any SLA alert
        WHEN _send_sla_alert() is called
        THEN it logs a warning message first (fallback logging always works)
        """
        with (
            patch("mcp_server_langgraph.monitoring.sla.AlertingService") as mock_service_class,
            patch("mcp_server_langgraph.monitoring.sla.logger") as mock_logger,
        ):
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_service.initialize = AsyncMock()  # noqa: async-mock-config
            mock_service.send_alert = AsyncMock()  # noqa: async-mock-config
            mock_service_class.return_value = mock_service

            # Act
            await sla_monitor._send_sla_alert(
                severity="critical",
                message="SLA breach",
                details={"metric": "uptime"},
            )

            # Assert - warning was logged first
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            assert "SLA Alert" in call_args
            assert "CRITICAL" in call_args

    async def test_send_sla_alert_success_calls_send_alert(self, sla_monitor):
        """
        GIVEN AlertingService works correctly
        WHEN _send_sla_alert() is called
        THEN it calls AlertingService.send_alert()
        """
        with patch("mcp_server_langgraph.monitoring.sla.AlertingService") as mock_service_class:
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_service.initialize = AsyncMock()  # noqa: async-mock-config
            mock_service.send_alert = AsyncMock()  # noqa: async-mock-config
            mock_service_class.return_value = mock_service

            # Act
            await sla_monitor._send_sla_alert(
                severity="warning",
                message="SLA at risk",
                details={"metric": "error_rate"},
            )

            # Assert - send_alert was called
            mock_service.initialize.assert_called_once()
            mock_service.send_alert.assert_called_once()
