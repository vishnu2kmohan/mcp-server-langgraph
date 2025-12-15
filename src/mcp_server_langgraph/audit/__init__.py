"""
Unified Audit Logging Facility.

Provides system-wide audit logging for compliance with:
- GDPR - EU General Data Protection Regulation
- HIPAA - Health Insurance Portability and Accountability Act (45 C.F.R. § 164.312(b))
- SOC 2 Type II - Service Organization Controls (CC6.x, CC7.x)
- FedRAMP - Federal Risk and Authorization Management (NIST 800-53 AU controls)
- EU AI Act - Articles 12, 19, 72 for high-risk AI systems

This module answers: WHO did WHAT, WHEN, and WHERE.
"""

from mcp_server_langgraph.audit.constants import Regulation, RetentionDays
from mcp_server_langgraph.audit.decorators import (
    audit_action,
    audit_ai_operation,
    audit_data_access,
)
from mcp_server_langgraph.audit.context import (
    create_context_from_request,
    create_context_for_service,
    enrich_context_with_trace,
    get_trace_context,
)
from mcp_server_langgraph.audit.integrity import (
    ChainVerificationResult,
    HashChainBuilder,
    compute_event_hash,
    verify_chain,
)
from mcp_server_langgraph.audit.models import (
    AIOperationDetails,
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.audit.compliance_service import ComplianceService
from mcp_server_langgraph.audit.alerts import (
    AuditAlert,
    AuditAlertDetector,
    AuditAlertManager,
)
from mcp_server_langgraph.audit.metrics import AuditMetrics
from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler
from mcp_server_langgraph.audit.notifications import (
    AlertNotifier,
    NotificationRouter,
    PagerDutyNotifier,
    SlackNotifier,
    create_notification_callback,
)
from mcp_server_langgraph.audit.exceptions import (
    AuditAlertError,
    AuditAuthorizationError,
    AuditChainBrokenError,
    AuditConfigurationError,
    AuditError,
    AuditExportError,
    AuditIntegrityError,
    AuditRepositoryError,
    AuditRetentionError,
    AuditSequenceGapError,
    AuditServiceError,
)
from mcp_server_langgraph.audit.config import (
    AlertingConfig,
    SlackConfig,
    PagerDutyConfig,
    DetectionConfig,
    load_alerting_config,
    create_notifiers_from_config,
    create_notification_router,
    clear_config_cache,
)
from mcp_server_langgraph.audit.factory import create_audit_scheduler
from mcp_server_langgraph.audit.retention_scheduler import (
    PartitionRetentionScheduler,
    PartitionRetentionExecutor,
    RetentionCleanupResult,
    create_retention_scheduler,
)
from mcp_server_langgraph.audit.compression import (
    AuditCompressionScheduler,
    CompressionResult,
)
from mcp_server_langgraph.audit.broadcast import (
    AuditEventBroadcaster,
    AuditEventFilter,
)
from mcp_server_langgraph.audit.repository import (
    InMemoryUnifiedAuditRepository,
    PostgresUnifiedAuditRepository,
)

__all__ = [
    # Constants
    "Regulation",
    "RetentionDays",
    # Models
    "AuditEventCategory",
    "AuditEventType",
    "AuditActor",
    "AuditContext",
    "AIOperationDetails",
    "UnifiedAuditEvent",
    # Decorators
    "audit_action",
    "audit_ai_operation",
    "audit_data_access",
    # Context
    "get_trace_context",
    "enrich_context_with_trace",
    "create_context_from_request",
    "create_context_for_service",
    # Integrity
    "compute_event_hash",
    "HashChainBuilder",
    "ChainVerificationResult",
    "verify_chain",
    # Service
    "UnifiedAuditService",
    "ComplianceService",
    # Alerts
    "AuditAlert",
    "AuditAlertDetector",
    "AuditAlertManager",
    # Metrics
    "AuditMetrics",
    # Scheduler
    "AuditIntegrityScheduler",
    # Notifications
    "AlertNotifier",
    "SlackNotifier",
    "PagerDutyNotifier",
    "NotificationRouter",
    "create_notification_callback",
    # Exceptions
    "AuditError",
    "AuditConfigurationError",
    "AuditIntegrityError",
    "AuditChainBrokenError",
    "AuditSequenceGapError",
    "AuditRetentionError",
    "AuditServiceError",
    "AuditRepositoryError",
    "AuditExportError",
    "AuditAlertError",
    "AuditAuthorizationError",
    # Configuration
    "AlertingConfig",
    "SlackConfig",
    "PagerDutyConfig",
    "DetectionConfig",
    "load_alerting_config",
    "create_notifiers_from_config",
    "create_notification_router",
    "clear_config_cache",
    # Factory
    "create_audit_scheduler",
    # Retention Scheduler
    "PartitionRetentionScheduler",
    "PartitionRetentionExecutor",
    "RetentionCleanupResult",
    "create_retention_scheduler",
    # Compression Scheduler
    "AuditCompressionScheduler",
    "CompressionResult",
    # Broadcast
    "AuditEventBroadcaster",
    "AuditEventFilter",
    # Repository
    "InMemoryUnifiedAuditRepository",
    "PostgresUnifiedAuditRepository",
]
