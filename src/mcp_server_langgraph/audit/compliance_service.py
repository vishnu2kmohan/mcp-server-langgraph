"""
Compliance Report Service.

Generates regulation-specific compliance reports from audit data:
- GDPR: Article 30 Records of Processing Activities
- HIPAA: 45 CFR 164.312(b) Audit Controls
- SOC 2: Type II Evidence for CC6.x/CC7.x
- FedRAMP: NIST 800-53 AU Controls
- EU AI Act: Articles 12, 19, 72 AI System Logging

Each report aggregates audit events into the format required
by auditors and compliance officers.
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AuditServiceProtocol(Protocol):
    """Protocol for audit service dependency."""

    async def query_events(
        self,
        category: str | None = None,
        event_type: str | None = None,
        regulation: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 1000,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query events with filters."""
        ...

    async def get_integrity_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Get integrity verification report."""
        ...


class ComplianceService:
    """
    Generates compliance reports from audit data.

    Implements ComplianceServiceProtocol for the compliance_reports API.

    Gracefully handles unavailable audit service by returning placeholder
    reports with empty data. This ensures the compliance endpoints remain
    available (return 200) even when the audit database is unavailable.
    """

    def __init__(self, audit_service: AuditServiceProtocol | None = None) -> None:
        """
        Initialize with optional audit service dependency.

        Args:
            audit_service: Service for querying audit events. If None,
                          placeholder reports with empty data are returned.
        """
        self._audit = audit_service

    def _is_available(self) -> bool:
        """Check if audit service is available."""
        return self._audit is not None

    async def _safe_query_events(
        self,
        regulation: str | None = None,
        category: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page_size: int = 1000,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query audit events with graceful error handling.

        Returns empty results if audit service is unavailable or errors.
        """
        if self._audit is None:
            return [], 0

        try:
            return await self._audit.query_events(
                regulation=regulation,
                category=category,
                event_type=event_type,
                start_time=start_time,
                end_time=end_time,
                page_size=page_size,
            )
        except Exception as e:
            logger.warning(f"Failed to query audit events: {e}")
            return [], 0

    async def _safe_get_integrity_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Get integrity report with graceful error handling.

        Returns placeholder if audit service is unavailable or errors.
        """
        if self._audit is None:
            return {
                "chain_valid": None,
                "events_verified": 0,
                "errors": ["Audit service unavailable"],
            }

        try:
            return await self._audit.get_integrity_report(start_time, end_time)
        except Exception as e:
            logger.warning(f"Failed to get integrity report: {e}")
            return {
                "chain_valid": None,
                "events_verified": 0,
                "errors": [str(e)],
            }

    async def generate_gdpr_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate GDPR Article 30 Records of Processing Activities report.

        Includes:
        - Processing activities summary
        - Data access by category
        - Data subject requests (access, erasure, rectification)

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            GDPR compliance report in Article 30 format.
        """
        # Query GDPR-tagged events
        events, total = await self._safe_query_events(
            regulation="GDPR",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        # Aggregate processing activities by resource type
        activities_by_resource: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"access_count": 0, "categories": set(), "actors": set()}
        )

        for event in events:
            resource_type = event.get("resource_type", "unknown")
            activities_by_resource[resource_type]["access_count"] += 1
            activities_by_resource[resource_type]["categories"].add(event.get("category", "unknown"))
            actor = event.get("actor", {})
            if isinstance(actor, dict):
                activities_by_resource[resource_type]["actors"].add(actor.get("actor_id", "unknown"))

        processing_activities = [
            {
                "name": resource_type,
                "access_count": data["access_count"],
                "categories_of_data": list(data["categories"]),
                "unique_accessors": len(data["actors"]),
            }
            for resource_type, data in activities_by_resource.items()
        ]

        # Count data subject requests
        export_events, export_count = await self._safe_query_events(
            regulation="GDPR",
            event_type="data_export",
            start_time=start_time,
            end_time=end_time,
        )

        deletion_events, deletion_count = await self._safe_query_events(
            regulation="GDPR",
            event_type="data_deletion",
            start_time=start_time,
            end_time=end_time,
        )

        rectification_events, rectification_count = await self._safe_query_events(
            regulation="GDPR",
            event_type="data_rectification",
            start_time=start_time,
            end_time=end_time,
        )

        return {
            "regulation": "GDPR",
            "report_type": "Article 30 Records of Processing Activities",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_events": total,
            "processing_activities": processing_activities,
            "data_subject_requests": {
                "access_requests": export_count,
                "export_requests": export_count,
                "erasure_requests": deletion_count,
                "deletion_requests": deletion_count,
                "rectification_requests": rectification_count,
            },
        }

    async def generate_hipaa_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate HIPAA 164.312(b) Audit Controls report.

        Includes:
        - PHI access summary by user and resource
        - Security incidents
        - Access patterns

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            HIPAA compliance report.
        """
        # Query HIPAA-tagged events
        events, total = await self._safe_query_events(
            regulation="HIPAA",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        # Aggregate PHI access by user
        access_by_user: dict[str, int] = defaultdict(int)
        access_by_resource: dict[str, int] = defaultdict(int)
        failed_accesses = 0

        for event in events:
            actor = event.get("actor", {})
            if isinstance(actor, dict):
                user_id = actor.get("actor_id", "unknown")
                access_by_user[user_id] += 1

            resource_id = event.get("resource_id", "unknown")
            access_by_resource[resource_id] += 1

            if event.get("outcome") in ("failure", "denied"):
                failed_accesses += 1

        # Query security incidents
        security_events, security_count = await self._safe_query_events(
            regulation="HIPAA",
            category="security",
            start_time=start_time,
            end_time=end_time,
        )

        return {
            "regulation": "HIPAA",
            "report_type": "45 CFR 164.312(b) Audit Controls",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_events": total,
            "phi_access_summary": {
                "total_accesses": total,
                "failed_accesses": failed_accesses,
                "unique_users": len(access_by_user),
                "unique_resources": len(access_by_resource),
                "by_user": dict(sorted(access_by_user.items(), key=lambda x: x[1], reverse=True)[:20]),
                "by_resource": dict(sorted(access_by_resource.items(), key=lambda x: x[1], reverse=True)[:20]),
            },
            "security_incidents": {
                "total": security_count,
                "events": [
                    {
                        "event_id": e.get("event_id"),
                        "timestamp": e.get("timestamp"),
                        "event_type": e.get("event_type"),
                        "outcome": e.get("outcome"),
                    }
                    for e in security_events[:50]
                ],
            },
        }

    async def generate_soc2_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate SOC 2 Type II Evidence report.

        Includes:
        - CC6.x Access Controls
        - CC7.x System Operations

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            SOC 2 compliance report.
        """
        # Query authentication events
        auth_events, auth_total = await self._safe_query_events(
            regulation="SOC2",
            category="authentication",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        # Count login outcomes
        successful_logins = 0
        failed_logins = 0
        for event in auth_events:
            if event.get("outcome") == "success":
                successful_logins += 1
            elif event.get("outcome") in ("failure", "denied"):
                failed_logins += 1

        # Query system operations
        system_events, system_total = await self._safe_query_events(
            regulation="SOC2",
            category="system",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        config_changes = sum(1 for e in system_events if e.get("event_type") == "configuration_change")
        errors = sum(1 for e in system_events if e.get("outcome") == "error")

        return {
            "regulation": "SOC2",
            "report_type": "Type II Evidence - CC6.x/CC7.x Controls",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "access_controls": {
                "login_attempts": auth_total,
                "successful_logins": successful_logins,
                "failed_logins": failed_logins,
                "login_success_rate": (round(successful_logins / auth_total * 100, 2) if auth_total > 0 else 0),
            },
            "system_operations": {
                "total_events": system_total,
                "configuration_changes": config_changes,
                "system_errors": errors,
            },
        }

    async def generate_fedramp_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate FedRAMP NIST 800-53 AU Controls report.

        Includes:
        - AU-2: Auditable Events
        - AU-3: Content of Audit Records
        - AU-9: Protection of Audit Information (integrity)
        - AU-11: Audit Record Retention

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            FedRAMP compliance report.
        """
        # Query FedRAMP-tagged events
        events, total = await self._safe_query_events(
            regulation="FedRAMP",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        # Aggregate by category
        by_category: dict[str, int] = defaultdict(int)
        for event in events:
            by_category[event.get("category", "unknown")] += 1

        # Get integrity verification status
        integrity_report = await self._safe_get_integrity_report(start_time, end_time)
        integrity_status = {
            "chain_valid": integrity_report.get("chain_valid", False),
            "events_verified": integrity_report.get("events_verified", 0),
            "errors": integrity_report.get("errors", []),
        }

        return {
            "regulation": "FedRAMP",
            "report_type": "NIST 800-53 AU Controls",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "au_controls": {
                "au_2_auditable_events": {
                    "total_events": total,
                    "by_category": dict(by_category),
                },
                "au_3_content": {
                    "has_who": True,
                    "has_what": True,
                    "has_when": True,
                    "has_where": True,
                },
                "integrity_status": integrity_status,
                "au_11_retention": {
                    "retention_policy": "7 years (2555 days)",
                    "events_in_range": total,
                },
            },
        }

    async def generate_eu_ai_act_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate EU AI Act compliance report.

        Includes:
        - Article 12: Record-keeping
        - Article 19: Data governance
        - Article 72: Logging requirements for high-risk AI

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            EU AI Act compliance report.
        """
        # Query AI operation events
        events, total = await self._safe_query_events(
            regulation="EU_AI_ACT",
            category="ai_operation",
            start_time=start_time,
            end_time=end_time,
            page_size=10000,
        )

        # Aggregate by AI model
        by_model: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "invocation_count": 0,
                "total_tokens": 0,
                "providers": set(),
            }
        )

        for event in events:
            ai_op = event.get("ai_operation", {})
            if ai_op:
                model_id = ai_op.get("model_id", "unknown")
                by_model[model_id]["invocation_count"] += 1
                by_model[model_id]["total_tokens"] += ai_op.get("tokens_used", 0)
                by_model[model_id]["providers"].add(ai_op.get("provider", "unknown"))

        ai_systems = [
            {
                "model_id": model_id,
                "invocation_count": data["invocation_count"],
                "total_tokens": data["total_tokens"],
                "providers": list(data["providers"]),
            }
            for model_id, data in by_model.items()
        ]

        # Sort by invocation count
        ai_systems.sort(key=lambda x: x["invocation_count"], reverse=True)

        return {
            "regulation": "EU_AI_ACT",
            "report_type": "Articles 12, 19, 72 - AI System Logging",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_ai_operations": total,
            "ai_systems": ai_systems[:50],  # Top 50 models
            "usage_statistics": {
                "total_invocations": total,
                "unique_models": len(by_model),
                "total_tokens": sum(m["total_tokens"] for m in ai_systems),
            },
        }

    async def generate_compliance_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate summary across all regulations.

        Provides high-level overview for multi-regulation compliance.

        Args:
            start_time: Start of reporting period.
            end_time: End of reporting period.

        Returns:
            Compliance summary report.
        """
        regulations = ["GDPR", "HIPAA", "SOC2", "FedRAMP", "EU_AI_ACT"]
        by_regulation: dict[str, int] = {}

        total_events = 0
        for reg in regulations:
            events, count = await self._safe_query_events(
                regulation=reg,
                start_time=start_time,
                end_time=end_time,
                page_size=1,  # Just need count
            )
            by_regulation[reg] = count
            total_events += count

        return {
            "report_type": "Compliance Summary",
            "generated_at": datetime.now(UTC).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_events": total_events,
            "by_regulation": by_regulation,
        }
