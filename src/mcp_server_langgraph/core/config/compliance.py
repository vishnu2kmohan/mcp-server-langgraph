"""
Compliance Configuration Module.

Settings for GDPR, HIPAA, SOC2, FedRAMP compliance requirements.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class ComplianceSettings(DomainSettings):
    """
    Regulatory compliance settings.

    Covers:
    - GDPR (data retention, encryption, deletion)
    - HIPAA (PHI protection, integrity verification)
    - SOC2 (audit logging, access controls)
    - FedRAMP (audit integrity, partition retention)
    - Data security and multi-tenant isolation
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # HIPAA Compliance
    hipaa_integrity_secret: str | None = None

    # GDPR/HIPAA/SOC2/FedRAMP Compliance Storage
    # NOTE: Renamed from gdpr_* to compliance_* in v2.8 for clarity (supports multiple frameworks)
    compliance_storage_backend: str = Field(
        default="memory",  # "postgres" (production), "memory" (dev)
        validation_alias=AliasChoices(
            "compliance_storage_backend",
            "COMPLIANCE_STORAGE_BACKEND",
            "GDPR_STORAGE_BACKEND",
            "gdpr_storage_backend",
        ),
    )
    compliance_postgres_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/compliance",
        validation_alias=AliasChoices(
            "compliance_postgres_url",
            "COMPLIANCE_POSTGRES_URL",
            "GDPR_POSTGRES_URL",
            "gdpr_postgres_url",
        ),
    )

    # Data Security & Compliance (for regulated workloads)
    enable_context_encryption: bool = False
    context_encryption_key: str | None = None
    context_retention_days: int = 90
    enable_auto_deletion: bool = True
    enable_multi_tenant_isolation: bool = False

    # Audit Log Cold Storage (for long-term compliance archival)
    audit_log_cold_storage_backend: str | None = None  # None, "s3", "gcs", "azure", "local"
    audit_log_cold_storage_path: str | None = None

    # Audit Integrity (FedRAMP AU-9 compliance)
    audit_integrity_secret: str = "default-audit-secret-change-in-production"  # noqa: S105

    # Audit Integrity Scheduler (FedRAMP AU-9 compliance)
    audit_scheduler_enabled: bool = False
    audit_scheduler_hours: int = 24

    # Partition Retention Scheduler (FedRAMP AU-11 compliance)
    partition_retention_enabled: bool = False
    partition_retention_months: int = 84  # 7 years default (FedRAMP)
    partition_retention_hours: int = 24


__all__ = ["ComplianceSettings"]
