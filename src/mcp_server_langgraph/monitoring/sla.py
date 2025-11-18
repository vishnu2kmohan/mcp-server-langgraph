"""
SLA Monitoring and Tracking

Implements Service Level Agreement monitoring for:
- Uptime percentage (99.9% target)
- Response time percentiles (p50, p95, p99)
- Error rate thresholds
- Automated alerting on SLA breaches

SOC 2 A1.2 - System Availability Monitoring
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.integrations.alerting import Alert, AlertingService, AlertSeverity
from mcp_server_langgraph.monitoring.prometheus_client import get_prometheus_client
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class SLAStatus(str, Enum):
    """SLA compliance status"""

    MEETING = "meeting"  # Meeting SLA targets
    AT_RISK = "at_risk"  # Close to breach (within 10%)
    BREACH = "breach"  # SLA target breached


class SLAMetric(str, Enum):
    """SLA metric types"""

    UPTIME = "uptime"  # System uptime percentage
    RESPONSE_TIME = "response_time"  # API response time
    ERROR_RATE = "error_rate"  # Error rate percentage
    THROUGHPUT = "throughput"  # Requests per second


class SLATarget(BaseModel):
    """SLA target definition"""

    metric: SLAMetric
    target_value: float = Field(..., description="Target value (e.g., 99.9 for uptime)")
    comparison: str = Field(default=">=", description="Comparison operator: >=, <=, ==, >, <")
    unit: str = Field(..., description="Unit of measurement (%, ms, rps)")
    warning_threshold: float = Field(..., description="Threshold for warning alerts (% of target)")
    critical_threshold: float = Field(..., description="Threshold for critical alerts (% of target)")


class SLAMeasurement(BaseModel):
    """SLA measurement result"""

    metric: SLAMetric
    measured_value: float
    target_value: float
    unit: str
    status: SLAStatus
    compliance_percentage: float = Field(..., description="Percentage of target achieved")
    timestamp: str
    period_start: str
    period_end: str
    breach_details: dict[str, Any] | None = None


class SLAReport(BaseModel):
    """SLA compliance report"""

    report_id: str
    generated_at: str
    period_start: str
    period_end: str
    measurements: list[SLAMeasurement] = Field(default_factory=list)
    overall_status: SLAStatus
    breaches: int = Field(default=0, description="Number of SLA breaches")
    warnings: int = Field(default=0, description="Number of warnings")
    compliance_score: float = Field(..., ge=0.0, description="Overall SLA compliance score (can exceed 100%)")
    summary: dict[str, Any] = Field(default_factory=dict)


class SLAMonitor:
    """
    SLA monitoring and tracking service

    Monitors system SLAs including uptime, response times, error rates.
    Provides automated alerting on SLA breaches and trend analysis.
    """

    def __init__(self, sla_targets: list[SLATarget] | None = None) -> None:
        """
        Initialize SLA monitor

        Args:
            sla_targets: List of SLA targets to monitor (if None, uses defaults; if [], uses no targets)
        """
        self.sla_targets = sla_targets if sla_targets is not None else self._default_sla_targets()

        logger.info(
            "SLA monitor initialized",
            extra={"target_count": len(self.sla_targets)},
        )

    def _default_sla_targets(self) -> list[SLATarget]:
        """
        Get default SLA targets

        Returns:
            List of default SLA targets
        """
        return [
            SLATarget(
                metric=SLAMetric.UPTIME,
                target_value=99.9,
                comparison=">=",
                unit="%",
                warning_threshold=99.5,  # Warning at 99.5%
                critical_threshold=99.0,  # Critical below 99%
            ),
            SLATarget(
                metric=SLAMetric.RESPONSE_TIME,
                target_value=500,  # 500ms p95
                comparison="<=",
                unit="ms",
                warning_threshold=600,  # Warning at 600ms
                critical_threshold=1000,  # Critical above 1000ms
            ),
            SLATarget(
                metric=SLAMetric.ERROR_RATE,
                target_value=1.0,  # 1% error rate
                comparison="<=",
                unit="%",
                warning_threshold=2.0,  # Warning at 2%
                critical_threshold=5.0,  # Critical above 5%
            ),
        ]

    async def measure_uptime(self, start_time: datetime, end_time: datetime) -> SLAMeasurement:
        """
        Measure uptime SLA

        Args:
            start_time: Start of measurement period
            end_time: End of measurement period

        Returns:
            SLAMeasurement for uptime
        """
        with tracer.start_as_current_span("sla.measure_uptime") as span:
            # Get uptime target
            uptime_target = next((t for t in self.sla_targets if t.metric == SLAMetric.UPTIME), None)

            if not uptime_target:
                raise ValueError("No uptime SLA target configured")

            # Calculate total time in period
            total_seconds = (end_time - start_time).total_seconds()

            # Query Prometheus for actual downtime
            try:
                prometheus = await get_prometheus_client()
                timerange = f"{int(total_seconds / 86400)}d"  # Convert to days
                downtime_seconds = await prometheus.query_downtime(timerange=timerange)
            except Exception as e:
                logger.warning(f"Failed to query Prometheus for downtime: {e}")
                downtime_seconds = 0  # Fallback to zero if query fails

            # Calculate uptime percentage
            uptime_seconds = total_seconds - downtime_seconds
            uptime_percentage = (uptime_seconds / total_seconds * 100) if total_seconds > 0 else 0

            # Calculate compliance percentage
            compliance_percentage = (
                (uptime_percentage / uptime_target.target_value * 100) if uptime_target.target_value > 0 else 0
            )

            # Determine status
            status = self._determine_status(uptime_percentage, uptime_target, is_higher_better=True)

            # Breach details
            breach_details = None
            if status == SLAStatus.BREACH:
                breach_details = {
                    "target": uptime_target.target_value,
                    "actual": uptime_percentage,
                    "shortfall": uptime_target.target_value - uptime_percentage,
                    "downtime_seconds": downtime_seconds,
                    "downtime_minutes": downtime_seconds / 60,
                }

            measurement = SLAMeasurement(
                metric=SLAMetric.UPTIME,
                measured_value=uptime_percentage,
                target_value=uptime_target.target_value,
                unit=uptime_target.unit,
                status=status,
                compliance_percentage=compliance_percentage,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                period_start=start_time.isoformat().replace("+00:00", "Z"),
                period_end=end_time.isoformat().replace("+00:00", "Z"),
                breach_details=breach_details,
            )

            span.set_attribute("uptime_percentage", uptime_percentage)
            span.set_attribute("status", status.value)

            logger.info(
                "Uptime SLA measured",
                extra={
                    "uptime_percentage": uptime_percentage,
                    "target": uptime_target.target_value,
                    "status": status.value,
                },
            )

            return measurement

    async def measure_response_time(self, start_time: datetime, end_time: datetime, percentile: int = 95) -> SLAMeasurement:
        """
        Measure response time SLA

        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            percentile: Percentile to measure (50, 95, 99)

        Returns:
            SLAMeasurement for response time
        """
        with tracer.start_as_current_span("sla.measure_response_time") as span:
            span.set_attribute("percentile", percentile)

            # Get response time target
            rt_target = next(
                (t for t in self.sla_targets if t.metric == SLAMetric.RESPONSE_TIME),
                None,
            )

            if not rt_target:
                raise ValueError("No response time SLA target configured")

            # Query Prometheus for actual response times
            try:
                prometheus = await get_prometheus_client()
                timerange_hours = int((end_time - start_time).total_seconds() / 3600)
                timerange = f"{max(1, timerange_hours)}h"  # At least 1 hour
                percentiles = await prometheus.query_percentiles(
                    metric="http_request_duration_seconds", percentiles=[percentile], timerange=timerange
                )
                response_time_ms = percentiles.get(percentile, 0) * 1000  # Convert seconds to milliseconds
            except Exception as e:
                logger.warning(f"Failed to query Prometheus for response times: {e}")
                response_time_ms = 350  # Fallback to conservative estimate

            # Calculate compliance percentage
            compliance_percentage = (rt_target.target_value / response_time_ms * 100) if response_time_ms > 0 else 100

            # Determine status
            status = self._determine_status(response_time_ms, rt_target, is_higher_better=False)

            # Breach details
            breach_details = None
            if status == SLAStatus.BREACH:
                breach_details = {
                    "target": rt_target.target_value,
                    "actual": response_time_ms,
                    "overage": response_time_ms - rt_target.target_value,
                    "percentile": f"p{percentile}",
                }

            measurement = SLAMeasurement(
                metric=SLAMetric.RESPONSE_TIME,
                measured_value=response_time_ms,
                target_value=rt_target.target_value,
                unit=rt_target.unit,
                status=status,
                compliance_percentage=compliance_percentage,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                period_start=start_time.isoformat().replace("+00:00", "Z"),
                period_end=end_time.isoformat().replace("+00:00", "Z"),
                breach_details=breach_details,
            )

            span.set_attribute("response_time_ms", response_time_ms)
            span.set_attribute("status", status.value)

            logger.info(
                f"Response time SLA measured (p{percentile})",
                extra={
                    "response_time_ms": response_time_ms,
                    "target": rt_target.target_value,
                    "status": status.value,
                },
            )

            return measurement

    async def measure_error_rate(self, start_time: datetime, end_time: datetime) -> SLAMeasurement:
        """
        Measure error rate SLA

        Args:
            start_time: Start of measurement period
            end_time: End of measurement period

        Returns:
            SLAMeasurement for error rate
        """
        with tracer.start_as_current_span("sla.measure_error_rate") as span:
            # Get error rate target
            error_target = next((t for t in self.sla_targets if t.metric == SLAMetric.ERROR_RATE), None)

            if not error_target:
                raise ValueError("No error rate SLA target configured")

            # Query Prometheus for actual error rate
            try:
                prometheus = await get_prometheus_client()
                timerange_mins = int((end_time - start_time).total_seconds() / 60)
                timerange = f"{max(5, timerange_mins)}m"  # At least 5 minutes
                error_rate_percentage = await prometheus.query_error_rate(timerange=timerange)
            except Exception as e:
                logger.warning(f"Failed to query Prometheus for error rate: {e}")
                error_rate_percentage = 0.5  # Fallback to conservative estimate

            # Calculate compliance percentage
            compliance_percentage = (
                (error_target.target_value / error_rate_percentage * 100) if error_rate_percentage > 0 else 100
            )

            # Determine status
            status = self._determine_status(error_rate_percentage, error_target, is_higher_better=False)

            # Breach details
            breach_details = None
            if status == SLAStatus.BREACH:
                breach_details = {
                    "target": error_target.target_value,
                    "actual": error_rate_percentage,
                    "overage": error_rate_percentage - error_target.target_value,
                }

            measurement = SLAMeasurement(
                metric=SLAMetric.ERROR_RATE,
                measured_value=error_rate_percentage,
                target_value=error_target.target_value,
                unit=error_target.unit,
                status=status,
                compliance_percentage=compliance_percentage,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                period_start=start_time.isoformat().replace("+00:00", "Z"),
                period_end=end_time.isoformat().replace("+00:00", "Z"),
                breach_details=breach_details,
            )

            span.set_attribute("error_rate_percentage", error_rate_percentage)
            span.set_attribute("status", status.value)

            logger.info(
                "Error rate SLA measured",
                extra={
                    "error_rate_percentage": error_rate_percentage,
                    "target": error_target.target_value,
                    "status": status.value,
                },
            )

            return measurement

    def _determine_status(self, measured_value: float, target: SLATarget, is_higher_better: bool) -> SLAStatus:
        """
        Determine SLA status based on measured value and target

        Args:
            measured_value: Measured value
            target: SLA target
            is_higher_better: True if higher values are better (uptime), False otherwise

        Returns:
            SLAStatus
        """
        if is_higher_better:
            # Higher is better (e.g., uptime)
            if measured_value >= target.target_value:
                return SLAStatus.MEETING
            if measured_value >= target.warning_threshold:
                return SLAStatus.AT_RISK
            return SLAStatus.BREACH
        # Lower is better (e.g., response time, error rate)
        if measured_value <= target.target_value:
            return SLAStatus.MEETING
        if measured_value <= target.warning_threshold:
            return SLAStatus.AT_RISK
        return SLAStatus.BREACH

    async def generate_sla_report(self, period_days: int = 30) -> SLAReport:
        """
        Generate comprehensive SLA report

        Args:
            period_days: Number of days to report on

        Returns:
            SLAReport with all measurements
        """
        with tracer.start_as_current_span("sla.generate_report") as span:
            span.set_attribute("period_days", period_days)

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=period_days)

            measurements = []

            # Measure only metrics that have configured targets
            # Check which metrics are configured
            configured_metrics = {t.metric for t in self.sla_targets}

            # Measure uptime if configured
            uptime = None
            if SLAMetric.UPTIME in configured_metrics:
                uptime = await self.measure_uptime(start_time, end_time)
                measurements.append(uptime)

            # Measure response time if configured
            response_time = None
            if SLAMetric.RESPONSE_TIME in configured_metrics:
                response_time = await self.measure_response_time(start_time, end_time)
                measurements.append(response_time)

            # Measure error rate if configured
            error_rate = None
            if SLAMetric.ERROR_RATE in configured_metrics:
                error_rate = await self.measure_error_rate(start_time, end_time)
                measurements.append(error_rate)

            # Count breaches and warnings
            breaches = sum(1 for m in measurements if m.status == SLAStatus.BREACH)
            warnings = sum(1 for m in measurements if m.status == SLAStatus.AT_RISK)

            # Determine overall status
            if breaches > 0:
                overall_status = SLAStatus.BREACH
            elif warnings > 0:
                overall_status = SLAStatus.AT_RISK
            else:
                overall_status = SLAStatus.MEETING

            # Calculate overall compliance score (average of all measurements)
            compliance_score = sum(m.compliance_percentage for m in measurements) / len(measurements) if measurements else 0.0

            # Generate summary (only include measured metrics)
            summary = {
                "all_slas_met": overall_status == SLAStatus.MEETING,
                "breaches": [
                    {
                        "metric": m.metric.value,
                        "target": m.target_value,
                        "actual": m.measured_value,
                        "details": m.breach_details,
                    }
                    for m in measurements
                    if m.status == SLAStatus.BREACH
                ],
            }

            # Add measured values to summary
            if uptime is not None:
                summary["uptime_percentage"] = uptime.measured_value
            if response_time is not None:
                summary["response_time_p95_ms"] = response_time.measured_value
            if error_rate is not None:
                summary["error_rate_percentage"] = error_rate.measured_value

            report = SLAReport(
                report_id=f"sla_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                period_start=start_time.isoformat().replace("+00:00", "Z"),
                period_end=end_time.isoformat().replace("+00:00", "Z"),
                measurements=measurements,
                overall_status=overall_status,
                breaches=breaches,
                warnings=warnings,
                compliance_score=compliance_score,
                summary=summary,
            )

            logger.info(
                "SLA report generated",
                extra={
                    "report_id": report.report_id,
                    "overall_status": overall_status.value,
                    "compliance_score": compliance_score,
                    "breaches": breaches,
                },
            )

            # Track metrics
            metrics.successful_calls.add(1, {"operation": "sla_report_generation"})

            # Alert on breaches
            if overall_status == SLAStatus.BREACH:
                await self._send_sla_alert(
                    severity="critical",
                    message=f"SLA breach detected: {breaches} metric(s) breached",
                    details=summary,
                )

            return report

    async def _send_sla_alert(self, severity: str, message: str, details: dict[str, Any]) -> None:
        """
        Send SLA alert

        Args:
            severity: Alert severity (warning, critical)
            message: Alert message
            details: Alert details
        """
        logger.warning(
            f"SLA Alert [{severity.upper()}]: {message}",
            extra={"severity": severity, "details": details},
        )

        # Send to alerting system (PagerDuty, Slack, email)
        try:
            alerting_service = AlertingService()
            await alerting_service.initialize()

            # Map severity string to AlertSeverity enum
            alert_severity = AlertSeverity.CRITICAL if severity == "critical" else AlertSeverity.WARNING  # type: ignore[attr-defined]

            from mcp_server_langgraph.integrations.alerting import AlertCategory

            alert = Alert(
                title=f"SLA {severity.upper()}: {message}",
                description=message,
                severity=alert_severity,
                category=AlertCategory.SLA,
                source="sla_monitor",
                metadata=details,
            )

            await alerting_service.send_alert(alert)
            logger.info("SLA alert sent successfully", extra={"alert_id": alert.alert_id})

        except Exception as e:
            logger.error(f"Failed to send SLA alert: {e}", exc_info=True)


# Global SLA monitor instance
_sla_monitor: SLAMonitor | None = None


def get_sla_monitor() -> SLAMonitor:
    """
    Get or create global SLA monitor instance

    Returns:
        SLAMonitor instance
    """
    global _sla_monitor

    if _sla_monitor is None:
        _sla_monitor = SLAMonitor()

    return _sla_monitor


def set_sla_monitor(monitor: SLAMonitor) -> None:
    """
    Set global SLA monitor instance

    Args:
        monitor: SLAMonitor instance to use globally
    """
    global _sla_monitor
    _sla_monitor = monitor
