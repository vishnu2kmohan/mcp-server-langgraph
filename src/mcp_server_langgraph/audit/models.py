"""
Unified audit event models for regulatory compliance.

Supports GDPR, HIPAA, SOC 2, FedRAMP, and EU AI Act requirements.

Models:
- AuditEventCategory: High-level event classification
- AuditEventType: Specific event types (FedRAMP AU-2 auditable events)
- AuditActor: WHO performed the action
- AuditContext: WHERE the action occurred (request context)
- AIOperationDetails: AI-specific details (EU AI Act Articles 12, 19, 72)
- UnifiedAuditEvent: Complete audit event with integrity fields
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from mcp_server_langgraph.audit.constants import RetentionDays


class AuditEventCategory(StrEnum):
    """
    High-level event categories for audit classification.

    Categories align with compliance framework requirements:
    - Authentication/Authorization: SOC 2 CC6.x, FedRAMP AU-2
    - Data Access/Modification: GDPR, HIPAA 164.312(b)
    - AI Operation: EU AI Act Articles 12, 19, 72
    - System/Security: SOC 2 CC7.x, FedRAMP AU-2
    - Compliance: GDPR Articles 15, 17, 20
    """

    AUTHENTICATION = "authentication"
    """Login, logout, MFA, password changes (FedRAMP AU-2)."""

    AUTHORIZATION = "authorization"
    """Access granted/denied, permission checks (SOC 2 CC6.x)."""

    DATA_ACCESS = "data_access"
    """Read operations on sensitive data (HIPAA, GDPR)."""

    DATA_MODIFICATION = "data_modification"
    """Create, update, delete operations (GDPR, SOC 2)."""

    AI_OPERATION = "ai_operation"
    """AI model invocations, outputs, decisions (EU AI Act)."""

    SYSTEM = "system"
    """Configuration changes, admin actions (SOC 2 CC7.x)."""

    SECURITY = "security"
    """Failed login, suspicious activity, threats (FedRAMP AU-2)."""

    COMPLIANCE = "compliance"
    """GDPR requests, data exports, consent changes."""


class AuditEventType(StrEnum):
    """
    Specific event types aligned with FedRAMP AU-2 auditable events.

    Organized by category with regulatory requirement references.
    """

    # Authentication events (FedRAMP AU-2, SOC 2 CC6.1)
    LOGIN_SUCCESS = "login.success"
    """Successful user login."""

    LOGIN_FAILED = "login.failed"
    """Failed login attempt (FedRAMP AU-2 required)."""

    LOGOUT = "logout"
    """User logout."""

    PASSWORD_CHANGE = "password.change"  # noqa: S105 - enum value, not a password
    """Password change (FedRAMP AU-2 required)."""

    MFA_ENABLED = "mfa.enabled"
    """Multi-factor authentication enabled."""

    SESSION_EXPIRED = "session.expired"
    """Session timeout (HIPAA 164.312(a)(2)(iii))."""

    # OAuth2 PKCE events (RFC 9700, ADR-0071)
    OAUTH2_LOGIN_INITIATED = "oauth2.login.initiated"
    """OAuth2 Authorization Code + PKCE flow started."""

    OAUTH2_CALLBACK_SUCCESS = "oauth2.callback.success"
    """OAuth2 authorization callback completed successfully."""

    OAUTH2_CALLBACK_FAILED = "oauth2.callback.failed"
    """OAuth2 authorization callback failed (invalid code, state mismatch, etc.)."""

    TOKEN_REFRESH_SUCCESS = "token.refresh.success"  # noqa: S105 - enum value, not a password
    """Access token refresh completed successfully."""

    TOKEN_REFRESH_FAILED = "token.refresh.failed"  # noqa: S105 - enum value, not a password
    """Access token refresh failed (expired/invalid refresh token)."""

    TOKEN_REVOKED = "token.revoked"  # noqa: S105 - enum value, not a password
    """Token added to denylist on logout."""

    # Authorization events (SOC 2 CC6.1, FedRAMP AU-2)
    ACCESS_GRANTED = "access.granted"
    """Access to resource granted."""

    ACCESS_DENIED = "access.denied"
    """Access to resource denied."""

    PERMISSION_CHECK = "permission.check"
    """Authorization check performed."""

    ROLE_ASSIGNED = "role.assigned"
    """Role assigned to user (FedRAMP AU-2 privilege changes)."""

    # Data access events (HIPAA 164.312(b), GDPR)
    DATA_READ = "data.read"
    """Data read operation."""

    DATA_SEARCH = "data.search"
    """Data search/query operation."""

    DATA_EXPORT = "data.export"
    """Data export operation (GDPR Art. 20)."""

    PHI_ACCESS = "phi.access"
    """Protected Health Information access (HIPAA)."""

    # Data modification events (GDPR, SOC 2)
    DATA_CREATE = "data.create"
    """Data creation."""

    DATA_UPDATE = "data.update"
    """Data update/modification."""

    DATA_DELETE = "data.delete"
    """Data deletion."""

    DATA_ANONYMIZE = "data.anonymize"
    """Data anonymization (GDPR Art. 17)."""

    # Artifact events (Hybrid Canvas - SOC 2, GDPR)
    ARTIFACT_CREATED = "artifact.created"
    """Artifact created in canvas."""

    ARTIFACT_UPDATED = "artifact.updated"
    """Artifact content or metadata updated."""

    ARTIFACT_DELETED = "artifact.deleted"
    """Artifact deleted."""

    ARTIFACT_FORKED = "artifact.forked"
    """Artifact forked to new version tree."""

    ARTIFACT_VERSION_CREATED = "artifact.version.created"
    """New version of artifact created."""

    ARTIFACT_VERSION_CLEANUP = "artifact.version.cleanup"
    """Old artifact versions cleaned up."""

    ARTIFACT_SEARCH = "artifact.search"
    """Semantic search performed on artifacts."""

    ARTIFACT_SIMILAR_SEARCH = "artifact.similar.search"
    """Similar artifacts search performed."""

    ARTIFACT_CLOUD_UPLOAD = "artifact.cloud.upload"
    """Large artifact uploaded to cloud storage."""

    ARTIFACT_CLOUD_DOWNLOAD = "artifact.cloud.download"
    """Large artifact downloaded from cloud storage."""

    # AI operation events (EU AI Act Articles 12, 19, 72)
    AI_INVOKE = "ai.invoke"
    """AI model invocation."""

    AI_OUTPUT = "ai.output"
    """AI model output generated."""

    AI_DECISION = "ai.decision"
    """AI-assisted decision made."""

    AI_ERROR = "ai.error"
    """AI model error occurred."""

    # System events (SOC 2 CC7.x, FedRAMP AU-2)
    CONFIG_CHANGE = "config.change"
    """System configuration change."""

    ADMIN_ACTION = "admin.action"
    """Administrative action (FedRAMP AU-2 required)."""

    # Remediation events (ADR-0026 - Alert remediation workflow)
    REMEDIATION_APPROVED = "remediation.approved"
    """Alert remediation action approved by admin."""

    REMEDIATION_REJECTED = "remediation.rejected"
    """Alert remediation action rejected by admin."""

    REMEDIATION_EXECUTED = "remediation.executed"
    """Alert remediation action executed."""

    REMEDIATION_FAILED = "remediation.failed"
    """Alert remediation action execution failed."""

    # Agent HITL (Human-in-the-Loop) events
    AGENT_REQUEST_APPROVED = "agent_request.approved"
    """Agent HITL request approved by reviewer."""

    AGENT_REQUEST_REJECTED = "agent_request.rejected"
    """Agent HITL request rejected by reviewer."""

    AGENT_REQUEST_RESPONDED = "agent_request.responded"
    """Agent clarification request responded to."""

    SERVICE_START = "service.start"
    """Service startup."""

    SERVICE_STOP = "service.stop"
    """Service shutdown."""

    # Security events (FedRAMP AU-2, SOC 2 CC7.2)
    THREAT_DETECTED = "threat.detected"
    """Security threat detected."""

    ANOMALY_DETECTED = "anomaly.detected"
    """Anomalous activity detected."""

    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    """Rate limit exceeded."""

    # Compliance events (GDPR Articles 15, 17, 20)
    GDPR_ACCESS_REQUEST = "gdpr.access_request"
    """GDPR Article 15 - Right of access request."""

    GDPR_DELETION_REQUEST = "gdpr.deletion_request"
    """GDPR Article 17 - Right to erasure request."""

    GDPR_EXPORT_REQUEST = "gdpr.export_request"
    """GDPR Article 20 - Data portability request."""


class AuditActor(BaseModel):
    """
    Identifies WHO performed the action.

    Supports three actor types:
    - user: Human user with credentials
    - service: Service account/API client
    - system: Automated system action
    """

    actor_id: str = Field(
        ...,
        description="Unique identifier for the actor (e.g., 'user:alice', 'service:mcp-gateway')",
    )

    actor_type: Literal["user", "service", "system"] = Field(
        ...,
        description="Type of actor: user (human), service (API client), or system (automated)",
    )

    username: str | None = Field(
        default=None,
        description="Human-readable username if available",
    )

    email: str | None = Field(
        default=None,
        description="Email address if available",
    )

    organization_id: str | None = Field(
        default=None,
        description="Organization/tenant ID for multi-tenancy isolation",
    )

    roles: list[str] = Field(
        default_factory=list,
        description="Roles assigned to the actor at time of action",
    )


class AuditContext(BaseModel):
    """
    Identifies WHERE the action occurred.

    Captures request context for traceability:
    - Request identifiers (request_id, trace_id, span_id)
    - Session information
    - Network context (IP, user agent)
    - HTTP details (method, path, status)
    """

    request_id: str = Field(
        ...,
        description="Unique request identifier for correlation",
    )

    trace_id: str | None = Field(
        default=None,
        description="OpenTelemetry trace ID for distributed tracing",
    )

    span_id: str | None = Field(
        default=None,
        description="OpenTelemetry span ID within trace",
    )

    session_id: str | None = Field(
        default=None,
        description="User session ID",
    )

    ip_address: str | None = Field(
        default=None,
        description="Client IP address (supports IPv4 and IPv6)",
    )

    user_agent: str | None = Field(
        default=None,
        description="HTTP User-Agent header",
    )

    http_method: str | None = Field(
        default=None,
        description="HTTP method (GET, POST, PUT, DELETE, etc.)",
    )

    http_path: str | None = Field(
        default=None,
        description="HTTP request path",
    )

    http_status: int | None = Field(
        default=None,
        description="HTTP response status code",
    )


class AIOperationDetails(BaseModel):
    """
    AI operation details for EU AI Act compliance (Articles 12, 19, 72).

    Captures information required for high-risk AI system logging:
    - Model identification and version
    - Performance metrics
    - Token usage and cost
    - Decision metadata
    """

    model_id: str = Field(
        ...,
        description="AI model identifier (e.g., 'gpt-4o', 'claude-3-opus')",
    )

    model_version: str | None = Field(
        default=None,
        description="Specific model version if available",
    )

    provider: str = Field(
        ...,
        description="AI provider (e.g., 'openai', 'anthropic', 'google')",
    )

    input_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Number of input tokens processed",
    )

    output_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Number of output tokens generated",
    )

    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Model invocation latency in milliseconds",
    )

    cost_usd: float | None = Field(
        default=None,
        ge=0,
        description="Estimated cost in USD",
    )

    decision_type: str | None = Field(
        default=None,
        description="Type of AI decision (e.g., 'classification', 'generation', 'embedding')",
    )

    confidence_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Model confidence score if applicable (0.0 to 1.0)",
    )


class UnifiedAuditEvent(BaseModel):
    """
    Complete unified audit event for all regulatory requirements.

    Answers WHO did WHAT, WHEN, and WHERE with integrity verification.

    Fields organized by purpose:
    - Identification: event_id, timestamp
    - Classification: category, event_type
    - Actor: who performed the action
    - Resource: what was affected
    - Action: what was done and outcome
    - Context: where it occurred
    - Details: additional metadata
    - AI: EU AI Act specific details
    - Integrity: hash chain for tamper-evidence (FedRAMP AU-9)
    - Compliance: regulation tags and retention
    """

    # Core identifiers
    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier (UUID v4)",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp in UTC (NTP-synchronized)",
    )

    # Event classification
    category: AuditEventCategory = Field(
        ...,
        description="High-level event category",
    )

    event_type: AuditEventType = Field(
        ...,
        description="Specific event type",
    )

    # Actor information (WHO)
    actor: AuditActor = Field(
        ...,
        description="Who performed the action",
    )

    # Resource information (WHAT was affected)
    resource_type: str = Field(
        ...,
        description="Type of resource (e.g., 'workflow', 'session', 'connection')",
    )

    resource_id: str = Field(
        ...,
        description="Unique identifier of the affected resource",
    )

    # Action details
    action: str = Field(
        ...,
        description="Human-readable description of the action",
    )

    outcome: Literal["success", "failure", "denied", "error"] = Field(
        ...,
        description="Result of the action",
    )

    # Context (WHERE)
    context: AuditContext = Field(
        ...,
        description="Request context (IP, trace, session, etc.)",
    )

    # Optional structured data
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional action-specific metadata",
    )

    # AI-specific (EU AI Act)
    ai_operation: AIOperationDetails | None = Field(
        default=None,
        description="AI operation details for EU AI Act compliance",
    )

    # Integrity fields (FedRAMP AU-9)
    sequence_number: int | None = Field(
        default=None,
        ge=1,
        description="Sequential number for ordering (populated after persistence)",
    )

    previous_hash: str | None = Field(
        default=None,
        description="Hash of previous event in chain (tamper-evidence)",
    )

    event_hash: str | None = Field(
        default=None,
        description="HMAC-SHA256 hash of this event (populated after persistence)",
    )

    # Compliance metadata
    regulation_tags: list[str] = Field(
        default_factory=list,
        description="Applicable regulations (e.g., ['GDPR', 'HIPAA', 'SOC2'])",
    )

    retention_days: int = Field(
        default=RetentionDays.DEFAULT,
        ge=1,
        description="Retention period in days (default: 7 years)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "category": "ai_operation",
                    "event_type": "ai.invoke",
                    "actor": {
                        "actor_id": "user:alice",
                        "actor_type": "user",
                        "username": "alice",
                    },
                    "resource_type": "workflow",
                    "resource_id": "wf-12345",
                    "action": "Invoked AI model for chat completion",
                    "outcome": "success",
                    "context": {
                        "request_id": "req-abc123",
                        "ip_address": "192.168.1.100",
                    },
                    "ai_operation": {
                        "model_id": "gpt-4o",
                        "provider": "openai",
                        "input_tokens": 150,
                        "output_tokens": 300,
                    },
                    "regulation_tags": ["EU_AI_ACT", "SOC2"],
                    "retention_days": 2555,
                }
            ]
        }
    }
