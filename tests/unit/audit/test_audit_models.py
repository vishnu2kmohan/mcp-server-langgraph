"""
Tests for unified audit event models.

TDD RED phase: These tests define expected behavior for audit models
supporting GDPR, HIPAA, SOC2, FedRAMP, and EU AI Act compliance.

Tests cover:
- Event categories and types (constants)
- Actor identification (who)
- Request context (where)
- AI operation details (EU AI Act)
- Unified audit event (complete model)
- Hash chain integrity fields
"""

import gc
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestAuditEventCategory:
    """Tests for AuditEventCategory enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authentication_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing AUTHENTICATION THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.AUTHENTICATION == "authentication"

    def test_authorization_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing AUTHORIZATION THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.AUTHORIZATION == "authorization"

    def test_data_access_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing DATA_ACCESS THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.DATA_ACCESS == "data_access"

    def test_data_modification_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing DATA_MODIFICATION THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.DATA_MODIFICATION == "data_modification"

    def test_ai_operation_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing AI_OPERATION THEN it exists (EU AI Act)."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.AI_OPERATION == "ai_operation"

    def test_system_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing SYSTEM THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.SYSTEM == "system"

    def test_security_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing SECURITY THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.SECURITY == "security"

    def test_compliance_category_exists(self) -> None:
        """GIVEN AuditEventCategory enum WHEN accessing COMPLIANCE THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventCategory

        assert AuditEventCategory.COMPLIANCE == "compliance"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestAuditEventType:
    """Tests for AuditEventType enum - FedRAMP AU-2 auditable events."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # Authentication events (FedRAMP AU-2)
    def test_login_success_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing LOGIN_SUCCESS THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.LOGIN_SUCCESS == "login.success"

    def test_login_failed_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing LOGIN_FAILED THEN it exists (FedRAMP AU-2)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.LOGIN_FAILED == "login.failed"

    def test_password_change_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing PASSWORD_CHANGE THEN it exists (FedRAMP AU-2)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.PASSWORD_CHANGE == "password.change"

    # AI operation events (EU AI Act)
    def test_ai_invoke_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing AI_INVOKE THEN it exists (EU AI Act)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.AI_INVOKE == "ai.invoke"

    def test_ai_decision_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing AI_DECISION THEN it exists (EU AI Act)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.AI_DECISION == "ai.decision"

    # Data access events (HIPAA, GDPR)
    def test_data_read_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing DATA_READ THEN it exists."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.DATA_READ == "data.read"

    def test_phi_access_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing PHI_ACCESS THEN it exists (HIPAA)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.PHI_ACCESS == "phi.access"

    # GDPR events
    def test_gdpr_access_request_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing GDPR_ACCESS_REQUEST THEN it exists (Art. 15)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.GDPR_ACCESS_REQUEST == "gdpr.access_request"

    def test_gdpr_deletion_request_event_type(self) -> None:
        """GIVEN AuditEventType WHEN accessing GDPR_DELETION_REQUEST THEN it exists (Art. 17)."""
        from mcp_server_langgraph.audit.models import AuditEventType

        assert AuditEventType.GDPR_DELETION_REQUEST == "gdpr.deletion_request"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestAuditActor:
    """Tests for AuditActor model - identifying WHO performed the action."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_user_actor(self) -> None:
        """GIVEN user details WHEN creating AuditActor THEN it has correct fields."""
        from mcp_server_langgraph.audit.models import AuditActor

        actor = AuditActor(
            actor_id="user:alice",
            actor_type="user",
            username="alice",
            email="alice@example.com",
            organization_id="org:acme",
            roles=["editor", "viewer"],
        )

        assert actor.actor_id == "user:alice"
        assert actor.actor_type == "user"
        assert actor.username == "alice"
        assert actor.email == "alice@example.com"
        assert actor.organization_id == "org:acme"
        assert actor.roles == ["editor", "viewer"]

    def test_create_service_actor(self) -> None:
        """GIVEN service account WHEN creating AuditActor THEN actor_type is service."""
        from mcp_server_langgraph.audit.models import AuditActor

        actor = AuditActor(
            actor_id="service:mcp-gateway",
            actor_type="service",
        )

        assert actor.actor_id == "service:mcp-gateway"
        assert actor.actor_type == "service"

    def test_create_system_actor(self) -> None:
        """GIVEN system action WHEN creating AuditActor THEN actor_type is system."""
        from mcp_server_langgraph.audit.models import AuditActor

        actor = AuditActor(
            actor_id="system",
            actor_type="system",
        )

        assert actor.actor_id == "system"
        assert actor.actor_type == "system"

    def test_actor_type_validation(self) -> None:
        """GIVEN invalid actor_type WHEN creating AuditActor THEN validation fails."""
        from mcp_server_langgraph.audit.models import AuditActor

        with pytest.raises(ValidationError):
            AuditActor(
                actor_id="invalid",
                actor_type="invalid_type",  # Not user/service/system
            )

    def test_actor_requires_id(self) -> None:
        """GIVEN missing actor_id WHEN creating AuditActor THEN validation fails."""
        from mcp_server_langgraph.audit.models import AuditActor

        with pytest.raises(ValidationError):
            AuditActor(actor_type="user")  # Missing actor_id

    def test_actor_with_minimal_fields_applies_defaults(self) -> None:
        """GIVEN minimal actor WHEN creating AuditActor THEN defaults are applied."""
        from mcp_server_langgraph.audit.models import AuditActor

        actor = AuditActor(
            actor_id="user:bob",
            actor_type="user",
        )

        assert actor.username is None
        assert actor.email is None
        assert actor.organization_id is None
        assert actor.roles == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestAuditContext:
    """Tests for AuditContext model - identifying WHERE the action occurred."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_full_context(self) -> None:
        """GIVEN full request context WHEN creating AuditContext THEN all fields set."""
        from mcp_server_langgraph.audit.models import AuditContext

        context = AuditContext(
            request_id="req-12345",
            trace_id="trace-abc123",
            span_id="span-xyz789",
            session_id="sess-user-001",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            http_method="POST",
            http_path="/api/v1/workflows",
            http_status=201,
        )

        assert context.request_id == "req-12345"
        assert context.trace_id == "trace-abc123"
        assert context.span_id == "span-xyz789"
        assert context.session_id == "sess-user-001"
        assert context.ip_address == "192.168.1.100"
        assert context.user_agent == "Mozilla/5.0"
        assert context.http_method == "POST"
        assert context.http_path == "/api/v1/workflows"
        assert context.http_status == 201

    def test_context_requires_request_id(self) -> None:
        """GIVEN missing request_id WHEN creating AuditContext THEN validation fails."""
        from mcp_server_langgraph.audit.models import AuditContext

        with pytest.raises(ValidationError):
            AuditContext()  # Missing required request_id

    def test_context_optional_fields(self) -> None:
        """GIVEN only request_id WHEN creating AuditContext THEN optional fields are None."""
        from mcp_server_langgraph.audit.models import AuditContext

        context = AuditContext(request_id="req-minimal")

        assert context.request_id == "req-minimal"
        assert context.trace_id is None
        assert context.span_id is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent is None
        assert context.http_method is None
        assert context.http_path is None
        assert context.http_status is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestAIOperationDetails:
    """Tests for AIOperationDetails model - EU AI Act Articles 12, 19, 72 compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_ai_operation_details(self) -> None:
        """GIVEN AI operation data WHEN creating AIOperationDetails THEN all fields set."""
        from mcp_server_langgraph.audit.models import AIOperationDetails

        ai_details = AIOperationDetails(
            model_id="gpt-4o",
            model_version="2024-05-13",
            provider="openai",
            input_tokens=150,
            output_tokens=300,
            latency_ms=1250.5,
            cost_usd=0.0045,
            decision_type="generation",
            confidence_score=0.95,
        )

        assert ai_details.model_id == "gpt-4o"
        assert ai_details.model_version == "2024-05-13"
        assert ai_details.provider == "openai"
        assert ai_details.input_tokens == 150
        assert ai_details.output_tokens == 300
        assert ai_details.latency_ms == 1250.5
        assert ai_details.cost_usd == 0.0045
        assert ai_details.decision_type == "generation"
        assert ai_details.confidence_score == 0.95

    def test_ai_operation_requires_model_id(self) -> None:
        """GIVEN missing model_id WHEN creating AIOperationDetails THEN validation fails."""
        from mcp_server_langgraph.audit.models import AIOperationDetails

        with pytest.raises(ValidationError):
            AIOperationDetails(provider="openai")  # Missing model_id

    def test_ai_operation_requires_provider(self) -> None:
        """GIVEN missing provider WHEN creating AIOperationDetails THEN validation fails."""
        from mcp_server_langgraph.audit.models import AIOperationDetails

        with pytest.raises(ValidationError):
            AIOperationDetails(model_id="gpt-4o")  # Missing provider

    def test_ai_operation_minimal(self) -> None:
        """GIVEN minimal AI details WHEN creating AIOperationDetails THEN optional fields are None."""
        from mcp_server_langgraph.audit.models import AIOperationDetails

        ai_details = AIOperationDetails(
            model_id="claude-3-opus",
            provider="anthropic",
        )

        assert ai_details.model_id == "claude-3-opus"
        assert ai_details.provider == "anthropic"
        assert ai_details.model_version is None
        assert ai_details.input_tokens is None
        assert ai_details.output_tokens is None
        assert ai_details.latency_ms is None
        assert ai_details.cost_usd is None
        assert ai_details.decision_type is None
        assert ai_details.confidence_score is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestUnifiedAuditEvent:
    """Tests for UnifiedAuditEvent model - complete audit event schema."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_complete_audit_event(self) -> None:
        """GIVEN full event data WHEN creating UnifiedAuditEvent THEN all fields set."""
        from mcp_server_langgraph.audit.models import (
            AIOperationDetails,
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        actor = AuditActor(
            actor_id="user:alice",
            actor_type="user",
            username="alice",
        )
        context = AuditContext(
            request_id="req-123",
            ip_address="10.0.0.1",
        )
        ai_details = AIOperationDetails(
            model_id="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=200,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=actor,
            resource_type="workflow",
            resource_id="wf-12345",
            action="Invoked AI model for chat completion",
            outcome="success",
            context=context,
            details={"prompt_length": 100},
            ai_operation=ai_details,
            regulation_tags=["EU_AI_ACT", "SOC2"],
            retention_days=2555,
        )

        assert event.category == AuditEventCategory.AI_OPERATION
        assert event.event_type == AuditEventType.AI_INVOKE
        assert event.actor.actor_id == "user:alice"
        assert event.resource_type == "workflow"
        assert event.resource_id == "wf-12345"
        assert event.action == "Invoked AI model for chat completion"
        assert event.outcome == "success"
        assert event.context.request_id == "req-123"
        assert event.details == {"prompt_length": 100}
        assert event.ai_operation is not None
        assert event.ai_operation.model_id == "gpt-4o"
        assert event.regulation_tags == ["EU_AI_ACT", "SOC2"]
        assert event.retention_days == 2555

    def test_audit_event_generates_uuid(self) -> None:
        """GIVEN no event_id WHEN creating UnifiedAuditEvent THEN UUID is generated."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:bob", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User logged in",
            outcome="success",
            context=AuditContext(request_id="req-456"),
        )

        # Verify event_id is a valid UUID
        uuid_obj = UUID(event.event_id)
        assert uuid_obj.version == 4

    def test_audit_event_generates_timestamp(self) -> None:
        """GIVEN no timestamp WHEN creating UnifiedAuditEvent THEN UTC timestamp is generated."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        before = datetime.now(UTC)
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:charlie", actor_type="user"),
            resource_type="document",
            resource_id="doc-789",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-789"),
        )
        after = datetime.now(UTC)

        assert before <= event.timestamp <= after
        assert event.timestamp.tzinfo is not None  # Must be timezone-aware

    def test_audit_event_outcome_validation(self) -> None:
        """GIVEN invalid outcome WHEN creating UnifiedAuditEvent THEN validation fails."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        with pytest.raises(ValidationError):
            UnifiedAuditEvent(
                category=AuditEventCategory.AUTHENTICATION,
                event_type=AuditEventType.LOGIN_FAILED,
                actor=AuditActor(actor_id="user:eve", actor_type="user"),
                resource_type="session",
                resource_id="sess-bad",
                action="Login attempt",
                outcome="invalid_outcome",  # Not success/failure/denied/error
                context=AuditContext(request_id="req-bad"),
            )

    def test_audit_event_defaults(self) -> None:
        """GIVEN minimal event WHEN creating UnifiedAuditEvent THEN defaults applied."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="system", actor_type="system"),
            resource_type="config",
            resource_id="app-settings",
            action="Updated configuration",
            outcome="success",
            context=AuditContext(request_id="req-sys"),
        )

        assert event.details == {}
        assert event.ai_operation is None
        assert event.sequence_number is None
        assert event.previous_hash is None
        assert event.event_hash is None
        assert event.regulation_tags == []
        assert event.retention_days == 2555  # Default 7 years

    def test_audit_event_integrity_fields(self) -> None:
        """GIVEN integrity data WHEN creating UnifiedAuditEvent THEN hash fields set."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.SECURITY,
            event_type=AuditEventType.THREAT_DETECTED,
            actor=AuditActor(actor_id="system", actor_type="system"),
            resource_type="network",
            resource_id="firewall",
            action="Detected suspicious traffic",
            outcome="success",
            context=AuditContext(request_id="req-sec"),
            sequence_number=12345,
            previous_hash="abc123def456",
            event_hash="xyz789ghi012",
        )

        assert event.sequence_number == 12345
        assert event.previous_hash == "abc123def456"
        assert event.event_hash == "xyz789ghi012"

    def test_audit_event_serialization(self) -> None:
        """GIVEN UnifiedAuditEvent WHEN serializing to dict THEN all fields present."""
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_CREATE,
            actor=AuditActor(actor_id="user:dave", actor_type="user"),
            resource_type="workflow",
            resource_id="wf-new",
            action="Created workflow",
            outcome="success",
            context=AuditContext(request_id="req-create"),
            regulation_tags=["GDPR", "SOC2"],
        )

        data = event.model_dump()

        assert "event_id" in data
        assert "timestamp" in data
        assert data["category"] == "data_modification"
        assert data["event_type"] == "data.create"
        assert data["actor"]["actor_id"] == "user:dave"
        assert data["resource_type"] == "workflow"
        assert data["regulation_tags"] == ["GDPR", "SOC2"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_models")
class TestRegulationConstants:
    """Tests for regulation tag constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_regulation_constants_exist(self) -> None:
        """GIVEN regulation constants WHEN accessing THEN all regulations present."""
        from mcp_server_langgraph.audit.constants import Regulation

        assert Regulation.GDPR == "GDPR"
        assert Regulation.HIPAA == "HIPAA"
        assert Regulation.SOC2 == "SOC2"
        assert Regulation.FEDRAMP == "FedRAMP"
        assert Regulation.EU_AI_ACT == "EU_AI_ACT"

    def test_default_retention_days(self) -> None:
        """GIVEN retention constants WHEN accessing THEN correct values."""
        from mcp_server_langgraph.audit.constants import RetentionDays

        assert RetentionDays.DEFAULT == 2555  # 7 years
        assert RetentionDays.GDPR == 2555  # 7 years
        assert RetentionDays.HIPAA == 2190  # 6 years
        assert RetentionDays.FEDRAMP == 2555  # 7 years
        assert RetentionDays.EU_AI_ACT == 180  # 6 months minimum
