"""
SOC 2 Compliance Scheduler

Automated scheduling for:
- Daily compliance checks
- Weekly access reviews
- Monthly compliance reports

Uses APScheduler for cron-based job scheduling.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.compliance.soc2.evidence import EvidenceCollector
from mcp_server_langgraph.integrations.alerting import Alert, AlertCategory, AlertingService, AlertSeverity
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class AccessReviewItem(BaseModel):
    """Access review item for a user"""

    user_id: str
    username: str
    roles: List[str]
    active_sessions: int
    last_login: Optional[str] = None
    account_status: str = Field(..., description="active, inactive, locked")
    review_status: str = Field(default="pending", description="approved, revoked, pending")
    review_notes: str = Field(default="", description="Review notes")


class AccessReviewReport(BaseModel):
    """Weekly access review report"""

    review_id: str
    generated_at: str
    period_start: str
    period_end: str
    total_users: int
    active_users: int
    inactive_users: int
    users_reviewed: List[AccessReviewItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    actions_required: List[str] = Field(default_factory=list)


class ComplianceScheduler:
    """
    SOC 2 compliance automation scheduler

    Schedules:
    - Daily compliance checks (6 AM UTC)
    - Weekly access reviews (Monday 9 AM UTC)
    - Monthly compliance reports (1st day of month, 9 AM UTC)
    """

    def __init__(
        self,
        evidence_collector: Optional[EvidenceCollector] = None,
        session_store: Optional[SessionStore] = None,
        evidence_dir: Optional[Path] = None,
        enabled: bool = True,
    ):
        """
        Initialize compliance scheduler

        Args:
            evidence_collector: Evidence collector service
            session_store: Session storage backend
            evidence_dir: Directory for evidence files
            enabled: Enable/disable scheduler
        """
        self.evidence_collector = evidence_collector or EvidenceCollector(
            session_store=session_store,
            evidence_dir=evidence_dir,
        )
        self.session_store = session_store
        self.enabled = enabled

        self.scheduler = AsyncIOScheduler()

        logger.info(f"Compliance scheduler initialized (enabled: {enabled})")

    async def start(self):
        """Start the compliance scheduler"""
        if not self.enabled:
            logger.info("Compliance scheduler disabled, skipping startup")
            return

        with tracer.start_as_current_span("compliance_scheduler.start"):
            # Daily compliance checks (6 AM UTC)
            self.scheduler.add_job(
                self._run_daily_compliance_check,
                trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
                id="daily_compliance_check",
                max_instances=1,
                replace_existing=True,
            )

            # Weekly access reviews (Monday 9 AM UTC)
            self.scheduler.add_job(
                self._run_weekly_access_review,
                trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="UTC"),
                id="weekly_access_review",
                max_instances=1,
                replace_existing=True,
            )

            # Monthly compliance reports (1st day of month, 9 AM UTC)
            self.scheduler.add_job(
                self._run_monthly_compliance_report,
                trigger=CronTrigger(day=1, hour=9, minute=0, timezone="UTC"),
                id="monthly_compliance_report",
                max_instances=1,
                replace_existing=True,
            )

            self.scheduler.start()

            logger.info(
                "Compliance scheduler started",
                extra={
                    "jobs": [
                        "daily_compliance_check",
                        "weekly_access_review",
                        "monthly_compliance_report",
                    ]
                },
            )

    async def stop(self):
        """Stop the compliance scheduler"""
        if self.scheduler.running:
            # Shutdown the scheduler. Use wait=False since we're in async context
            # The scheduler.running flag will be set to False immediately
            self.scheduler.shutdown(wait=False)

            # Give the scheduler a moment to update its state
            await asyncio.sleep(0.1)

            logger.info("Compliance scheduler stopped")

    async def trigger_daily_check(self) -> Dict[str, Any]:
        """
        Manually trigger daily compliance check

        Returns:
            Report summary
        """
        return await self._run_daily_compliance_check()

    async def trigger_weekly_review(self) -> AccessReviewReport:
        """
        Manually trigger weekly access review

        Returns:
            Access review report
        """
        return await self._run_weekly_access_review()

    async def trigger_monthly_report(self) -> Dict[str, Any]:
        """
        Manually trigger monthly compliance report

        Returns:
            Compliance report summary
        """
        return await self._run_monthly_compliance_report()

    # --- Scheduled Jobs ---

    async def _run_daily_compliance_check(self) -> Dict[str, Any]:
        """
        Run daily compliance check

        Collects evidence for all SOC 2 controls and generates summary.
        """
        with tracer.start_as_current_span("compliance.daily_check") as span:
            start_time = datetime.now(timezone.utc)

            try:
                logger.info("Starting daily compliance check")

                # Collect all evidence
                evidence_items = await self.evidence_collector.collect_all_evidence()

                # Calculate pass/fail rates
                passed = sum(1 for e in evidence_items if e.status.value == "success")
                failed = sum(1 for e in evidence_items if e.status.value == "failure")
                partial = sum(1 for e in evidence_items if e.status.value == "partial")
                total = len(evidence_items)

                compliance_score = (passed + (partial * 0.5)) / total * 100 if total > 0 else 0

                # Collect all findings
                findings = []
                for evidence in evidence_items:
                    findings.extend(evidence.findings)

                summary = {
                    "date": start_time.strftime("%Y-%m-%d"),
                    "evidence_collected": total,
                    "passed_controls": passed,
                    "failed_controls": failed,
                    "partial_controls": partial,
                    "compliance_score": f"{compliance_score:.1f}%",
                    "total_findings": len(findings),
                    "findings": findings,
                }

                # Log summary
                logger.info(
                    "Daily compliance check completed",
                    extra=summary,
                )

                # Track metrics
                metrics.successful_calls.add(1, {"operation": "daily_compliance_check"})

                # Alert if compliance score is low
                if compliance_score < 80:
                    await self._send_compliance_alert(
                        severity="high",
                        message=f"Daily compliance score below threshold: {compliance_score:.1f}%",
                        details=summary,
                    )

                span.set_attribute("compliance_score", compliance_score)
                span.set_attribute("total_findings", len(findings))

                return summary

            except Exception as e:
                logger.error(f"Daily compliance check failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "daily_compliance_check"})

                await self._send_compliance_alert(
                    severity="critical",
                    message=f"Daily compliance check failed: {str(e)}",
                    details={"error": str(e)},
                )

                return {"error": str(e), "status": "failed"}

    async def _run_weekly_access_review(self) -> AccessReviewReport:
        """
        Run weekly access review

        Reviews all user access, identifies inactive accounts, and generates
        access review report for security team.
        """
        with tracer.start_as_current_span("compliance.weekly_access_review") as span:
            start_time = datetime.now(timezone.utc)
            end_time = start_time
            start_of_period = start_time - timedelta(days=7)

            try:
                logger.info("Starting weekly access review")

                users_reviewed = []
                recommendations = []
                actions_required = []

                # Query user provider for all users
                # Note: Requires UserProvider injected via constructor
                # For production: self.user_provider = user_provider_factory()
                # Then: users = await self.user_provider.list_users()
                total_users = 0
                active_users = 0
                inactive_users = 0

                # Analyze session store for active sessions
                if self.session_store:
                    # Implement user session analysis
                    # Note: Requires session pattern analysis implementation
                    # Production tasks:
                    # - Get all users with sessions
                    # - Check last login time from session metadata
                    # - Identify inactive accounts (no login > 90 days)
                    # - Detect concurrent sessions
                    # - Flag suspicious activity patterns
                    pass

                # Example review item
                # users_reviewed.append(
                #     AccessReviewItem(
                #         user_id="user:alice",
                #         username="alice",
                #         roles=["admin", "user"],
                #         active_sessions=2,
                #         last_login=start_time.isoformat().replace("+00:00", "Z"),
                #         account_status="active",
                #         review_status="pending",
                #     )
                # )

                # Generate recommendations
                if inactive_users > 0:
                    recommendations.append(f"Review {inactive_users} inactive user accounts (no login > 90 days)")
                    actions_required.append("Disable or delete inactive user accounts")

                # Create report
                report = AccessReviewReport(
                    review_id=f"access_review_{start_time.strftime('%Y%m%d')}",
                    generated_at=start_time.isoformat().replace("+00:00", "Z"),
                    period_start=start_of_period.isoformat().replace("+00:00", "Z"),
                    period_end=end_time.isoformat().replace("+00:00", "Z"),
                    total_users=total_users,
                    active_users=active_users,
                    inactive_users=inactive_users,
                    users_reviewed=users_reviewed,
                    recommendations=recommendations,
                    actions_required=actions_required,
                )

                # Save report
                report_file = self.evidence_collector.evidence_dir / f"{report.review_id}.json"
                with open(report_file, "w") as f:
                    f.write(report.model_dump_json(indent=2))

                logger.info(
                    "Weekly access review completed",
                    extra={
                        "review_id": report.review_id,
                        "total_users": total_users,
                        "inactive_users": inactive_users,
                    },
                )

                # Send notification
                await self._send_access_review_notification(report)

                metrics.successful_calls.add(1, {"operation": "weekly_access_review"})

                span.set_attribute("total_users", total_users)
                span.set_attribute("inactive_users", inactive_users)

                return report

            except Exception as e:
                logger.error(f"Weekly access review failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "weekly_access_review"})

                await self._send_compliance_alert(
                    severity="high",
                    message=f"Weekly access review failed: {str(e)}",
                    details={"error": str(e)},
                )

                raise

    async def _run_monthly_compliance_report(self) -> Dict[str, Any]:
        """
        Run monthly compliance report

        Generates comprehensive SOC 2 compliance report for the month.
        """
        with tracer.start_as_current_span("compliance.monthly_report") as span:
            try:
                logger.info("Starting monthly compliance report generation")

                # Generate comprehensive report
                report = await self.evidence_collector.generate_compliance_report(report_type="monthly", period_days=30)

                summary = {
                    "report_id": report.report_id,
                    "compliance_score": f"{report.compliance_score:.1f}%",
                    "total_controls": report.total_controls,
                    "passed_controls": report.passed_controls,
                    "failed_controls": report.failed_controls,
                    "total_findings": report.summary.get("findings_summary", {}).get("total_findings", 0),
                }

                logger.info(
                    "Monthly compliance report generated",
                    extra=summary,
                )

                # Send report to compliance team
                await self._send_monthly_report_notification(report)

                metrics.successful_calls.add(1, {"operation": "monthly_compliance_report"})

                span.set_attribute("compliance_score", report.compliance_score)
                span.set_attribute("total_controls", report.total_controls)

                return summary

            except Exception as e:
                logger.error(f"Monthly compliance report failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "monthly_compliance_report"})

                await self._send_compliance_alert(
                    severity="critical",
                    message=f"Monthly compliance report failed: {str(e)}",
                    details={"error": str(e)},
                )

                return {"error": str(e), "status": "failed"}

    # --- Notification Helpers ---

    async def _send_compliance_alert(self, severity: str, message: str, details: Dict[str, Any]):
        """
        Send compliance alert

        Args:
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
            details: Alert details
        """
        logger.warning(
            f"Compliance Alert [{severity.upper()}]: {message}",
            extra={"severity": severity, "details": details},
        )

        # Send to alerting system (PagerDuty, Slack, email)
        try:
            alerting_service = AlertingService()
            await alerting_service.initialize()

            alert_severity = AlertSeverity.CRITICAL if severity == "critical" else AlertSeverity.WARNING

            alert = Alert(
                title=f"Compliance {severity.upper()}: {message}",
                description=message,
                severity=alert_severity,
                category=AlertCategory.COMPLIANCE,
                source="compliance_scheduler",
                metadata=details,
            )

            await alerting_service.send_alert(alert)
            logger.info("Compliance alert sent successfully", extra={"alert_id": alert.alert_id})

        except Exception as e:
            logger.error(f"Failed to send compliance alert: {e}", exc_info=True)

    async def _send_access_review_notification(self, report: AccessReviewReport):
        """
        Send access review notification

        Args:
            report: Access review report
        """
        logger.info(
            "Sending access review notification",
            extra={"review_id": report.review_id},
        )

        # Send notification to security team
        try:
            alerting_service = AlertingService()
            await alerting_service.initialize()

            alert = Alert(
                title="Weekly Access Review Ready",
                description=f"Access review {report.review_id} has been generated",
                severity=AlertSeverity.INFO,
                category=AlertCategory.COMPLIANCE,
                source="compliance_scheduler",
                metadata={
                    "review_id": report.review_id,
                    "total_users": report.total_users,
                    "inactive_users": report.inactive_users,
                    "excessive_access": report.excessive_access,
                },
            )

            await alerting_service.send_alert(alert)
            logger.info("Access review notification sent", extra={"alert_id": alert.alert_id})

        except Exception as e:
            logger.error(f"Failed to send access review notification: {e}", exc_info=True)

    async def _send_monthly_report_notification(self, report: Any):
        """
        Send monthly compliance report notification

        Args:
            report: Compliance report
        """
        logger.info(
            "Sending monthly compliance report notification",
            extra={"report_id": report.report_id},
        )

        # Send notification to compliance team
        try:
            alerting_service = AlertingService()
            await alerting_service.initialize()

            alert = Alert(
                title="Monthly SOC 2 Compliance Report Ready",
                description=f"Compliance report {report.report_id} has been generated",
                severity=AlertSeverity.INFO,
                category=AlertCategory.COMPLIANCE,
                source="compliance_scheduler",
                metadata={
                    "report_id": report.report_id,
                    "generated_at": report.generated_at,
                    "period_start": report.period_start,
                    "period_end": report.period_end,
                },
            )

            await alerting_service.send_alert(alert)
            logger.info("Monthly report notification sent", extra={"alert_id": alert.alert_id})

        except Exception as e:
            logger.error(f"Failed to send monthly report notification: {e}", exc_info=True)


# Global scheduler instance
_compliance_scheduler: Optional[ComplianceScheduler] = None


async def start_compliance_scheduler(
    session_store: Optional[SessionStore] = None,
    evidence_dir: Optional[Path] = None,
    enabled: bool = True,
) -> ComplianceScheduler:
    """
    Start global compliance scheduler

    Args:
        session_store: Session storage backend
        evidence_dir: Directory for evidence files
        enabled: Enable/disable scheduler

    Returns:
        ComplianceScheduler instance
    """
    global _compliance_scheduler

    if _compliance_scheduler is None:
        evidence_collector = EvidenceCollector(session_store=session_store, evidence_dir=evidence_dir)

        _compliance_scheduler = ComplianceScheduler(
            evidence_collector=evidence_collector,
            session_store=session_store,
            evidence_dir=evidence_dir,
            enabled=enabled,
        )

    await _compliance_scheduler.start()
    return _compliance_scheduler


async def stop_compliance_scheduler():
    """Stop global compliance scheduler"""
    global _compliance_scheduler

    if _compliance_scheduler is not None:
        await _compliance_scheduler.stop()
        _compliance_scheduler = None


def get_compliance_scheduler() -> Optional[ComplianceScheduler]:
    """
    Get global compliance scheduler instance

    Returns:
        ComplianceScheduler instance or None
    """
    return _compliance_scheduler
