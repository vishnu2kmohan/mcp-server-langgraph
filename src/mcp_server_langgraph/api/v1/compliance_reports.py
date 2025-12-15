"""
Compliance Report API endpoints.

Provides regulation-specific compliance reports for:
- GDPR - EU General Data Protection Regulation (Article 30)
- HIPAA - Health Insurance Portability and Accountability Act (164.312(b))
- SOC 2 Type II - Service Organization Controls (CC6.x, CC7.x)
- FedRAMP - Federal Risk and Authorization Management (NIST 800-53 AU)
- EU AI Act - Articles 12, 19, 72 for high-risk AI systems
"""

import logging
from datetime import datetime
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance"])


class ComplianceServiceProtocol(Protocol):
    """Protocol for compliance report service."""

    async def generate_gdpr_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate GDPR Article 30 report."""
        ...

    async def generate_hipaa_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate HIPAA 164.312(b) report."""
        ...

    async def generate_soc2_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate SOC 2 Type II report."""
        ...

    async def generate_fedramp_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate FedRAMP NIST 800-53 AU report."""
        ...

    async def generate_eu_ai_act_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate EU AI Act compliance report."""
        ...

    async def generate_compliance_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Generate summary across all regulations."""
        ...


# Dependency for compliance service
_compliance_service: ComplianceServiceProtocol | None = None


def get_compliance_service() -> ComplianceServiceProtocol:
    """Get the compliance service instance."""
    global _compliance_service
    if _compliance_service is None:
        raise HTTPException(
            status_code=503,
            detail="Compliance service not initialized",
        )
    return _compliance_service


def set_compliance_service(service: ComplianceServiceProtocol | None) -> None:
    """Set the compliance service instance (for app initialization)."""
    global _compliance_service
    _compliance_service = service


@router.get("/reports/gdpr")
async def get_gdpr_report(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate GDPR Article 30 Records of Processing Activities.

    Returns a report containing:
    - Processing activities summary
    - Categories of data processed
    - Recipients of data
    - Retention periods
    - Data subject request statistics

    This report supports GDPR Article 30 compliance requirements
    for maintaining records of processing activities.
    """
    return await service.generate_gdpr_report(start_time, end_time)


@router.get("/reports/hipaa")
async def get_hipaa_report(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate HIPAA 164.312(b) Audit Controls report.

    Returns a report containing:
    - PHI access summary
    - Access by user breakdown
    - Emergency access events
    - Failed access attempts
    - Audit trail verification

    This report supports HIPAA 45 C.F.R. § 164.312(b) compliance
    for implementing hardware, software, and procedural mechanisms
    to record and examine activity in systems containing PHI.
    """
    return await service.generate_hipaa_report(start_time, end_time)


@router.get("/reports/soc2")
async def get_soc2_report(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate SOC 2 Type II Evidence report.

    Returns a report containing:
    - Common Criteria (CC) coverage
    - CC6.x: Logical and Physical Access Controls
    - CC7.x: System Operations
    - Evidence counts per criteria
    - Integrity verification status

    This report supports SOC 2 Type II audits by providing
    evidence of control effectiveness over a period of time.
    """
    return await service.generate_soc2_report(start_time, end_time)


@router.get("/reports/fedramp")
async def get_fedramp_report(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate FedRAMP NIST 800-53 AU Controls report.

    Returns a report containing:
    - AU-2: Audit Events (event types logged)
    - AU-3: Content of Audit Records (fields captured)
    - AU-9: Protection of Audit Information (integrity)
    - AU-11: Audit Record Retention (policy compliance)

    This report supports FedRAMP authorization by demonstrating
    compliance with NIST 800-53 audit-related controls.
    """
    return await service.generate_fedramp_report(start_time, end_time)


@router.get("/reports/eu-ai-act")
async def get_eu_ai_act_report(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate EU AI Act Articles 12, 19, 72 Compliance report.

    Returns a report containing:
    - AI operations summary (total, by model, by provider)
    - Decision types and their counts
    - Model performance metrics
    - High-risk decision flags
    - Logging completeness percentage

    This report supports EU AI Act compliance for high-risk AI systems
    requiring automatic logging of events (Article 12), quality management
    (Article 19), and post-market monitoring (Article 72).
    """
    return await service.generate_eu_ai_act_report(start_time, end_time)


@router.get("/reports/summary")
async def get_compliance_summary(
    service: Annotated[ComplianceServiceProtocol, Depends(get_compliance_service)],
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
) -> dict[str, Any]:
    """
    Generate compliance summary across all regulations.

    Returns a summary containing:
    - Per-regulation status (compliant/non-compliant)
    - Event counts by regulation
    - Overall compliance status
    - Recommendations for improvement

    This report provides a high-level overview of compliance
    status across all supported regulatory frameworks.
    """
    return await service.generate_compliance_summary(start_time, end_time)
