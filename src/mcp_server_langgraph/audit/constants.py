"""
Audit logging constants for regulatory compliance.

Defines:
- Regulation tags for compliance categorization
- Retention periods per regulation
- Default values for audit configuration
"""

from enum import IntEnum, StrEnum


class Regulation(StrEnum):
    """
    Regulatory framework tags for audit events.

    These tags identify which compliance frameworks apply to an audit event,
    enabling regulation-specific queries and retention policies.
    """

    GDPR = "GDPR"
    """EU General Data Protection Regulation - Data protection and privacy."""

    HIPAA = "HIPAA"
    """Health Insurance Portability and Accountability Act - Healthcare data."""

    SOC2 = "SOC2"
    """Service Organization Controls Type 2 - Security, availability, confidentiality."""

    FEDRAMP = "FedRAMP"
    """Federal Risk and Authorization Management Program - US Government cloud."""

    EU_AI_ACT = "EU_AI_ACT"
    """EU Artificial Intelligence Act - AI system transparency and accountability."""


class RetentionDays(IntEnum):
    """
    Retention periods in days for audit logs by regulation.

    Based on regulatory requirements:
    - GDPR: 7 years (Article 17, storage limitation)
    - HIPAA: 6 years (45 CFR 164.530(j))
    - FedRAMP: 7 years (NIST 800-53 AU-11, NARA requirements)
    - EU AI Act: 6 months minimum (Article 12)
    """

    DEFAULT = 2555
    """Default retention: 7 years (2555 days)."""

    GDPR = 2555
    """GDPR retention: 7 years to support data subject requests."""

    HIPAA = 2190
    """HIPAA retention: 6 years per 45 CFR 164.530(j)."""

    FEDRAMP = 2555
    """FedRAMP retention: 7 years per NARA requirements."""

    EU_AI_ACT = 180
    """EU AI Act minimum: 6 months (180 days) for AI operation logs."""

    SOC2 = 1095
    """SOC 2 typical: 3 years for audit evidence."""
