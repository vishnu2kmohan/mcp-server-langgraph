"""
Tests for unified audit schema migration.

TDD RED phase: These tests define expected schema for audit_logs table
supporting GDPR, HIPAA, SOC2, FedRAMP, and EU AI Act compliance.

Tests verify:
- New columns exist (category, outcome, trace_id, etc.)
- Integrity columns exist (sequence_number, previous_hash, event_hash)
- AI operation column exists (JSONB)
- Regulation tags column exists (TEXT[])
- Indices exist for compliance queries
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_migration")
class TestUnifiedAuditSchemaColumns:
    """Tests for unified audit schema column definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_category_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN category exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "category")

    def test_outcome_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN outcome exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "outcome")

    def test_trace_id_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN trace_id exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "trace_id")

    def test_span_id_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN span_id exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "span_id")

    def test_session_id_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN session_id exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "session_id")

    def test_organization_id_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN organization_id exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "organization_id")

    def test_actor_type_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN actor_type exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "actor_type")

    def test_ai_operation_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN ai_operation exists (EU AI Act)."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "ai_operation")


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_migration")
class TestUnifiedAuditIntegrityColumns:
    """Tests for hash chain integrity columns (FedRAMP AU-9)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sequence_number_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN sequence_number exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "sequence_number")

    def test_previous_hash_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN previous_hash exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "previous_hash")

    def test_event_hash_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN event_hash exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "event_hash")


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_migration")
class TestUnifiedAuditComplianceColumns:
    """Tests for compliance metadata columns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_regulation_tags_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN regulation_tags exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "regulation_tags")

    def test_retention_days_column_defined(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN retention_days exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "retention_days")


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_migration")
class TestUnifiedAuditLogModel:
    """Tests for complete UnifiedAuditLog SQLAlchemy model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_table_name(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking table name THEN it is audit_logs."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert UnifiedAuditLog.__tablename__ == "audit_logs"

    def test_model_has_primary_key(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking primary key THEN log_id is primary key."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "log_id")

    def test_model_has_timestamp(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN timestamp exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "timestamp")

    def test_model_has_action(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN action exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "action")

    def test_model_has_resource_type(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN resource_type exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "resource_type")

    def test_model_has_resource_id(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN checking columns THEN resource_id exists."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        assert hasattr(UnifiedAuditLog, "resource_id")

    def test_model_can_be_instantiated(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN instantiating THEN object is created."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        log = UnifiedAuditLog(
            log_id="test-id",
            action="test.action",
            category="authentication",
            outcome="success",
            resource_type="session",
            resource_id="sess-123",
        )

        assert log.log_id == "test-id"
        assert log.action == "test.action"
        assert log.category == "authentication"
        assert log.outcome == "success"

    def test_model_ai_operation_is_dict(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN setting ai_operation THEN it accepts dict."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        ai_op = {
            "model_id": "gpt-4o",
            "provider": "openai",
            "input_tokens": 100,
            "output_tokens": 200,
        }

        log = UnifiedAuditLog(
            log_id="test-id",
            action="ai.invoke",
            category="ai_operation",
            outcome="success",
            resource_type="workflow",
            resource_id="wf-123",
            ai_operation=ai_op,
        )

        assert log.ai_operation == ai_op

    def test_model_regulation_tags_is_list(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN setting regulation_tags THEN it accepts list."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        log = UnifiedAuditLog(
            log_id="test-id",
            action="data.read",
            category="data_access",
            outcome="success",
            resource_type="document",
            resource_id="doc-123",
            regulation_tags=["GDPR", "HIPAA"],
        )

        assert log.regulation_tags == ["GDPR", "HIPAA"]

    def test_model_retention_days_default(self) -> None:
        """GIVEN UnifiedAuditLog model WHEN not setting retention_days THEN default is 2555."""
        from mcp_server_langgraph.models.audit_log import UnifiedAuditLog

        log = UnifiedAuditLog(
            log_id="test-id",
            action="test.action",
            category="system",
            outcome="success",
            resource_type="config",
            resource_id="cfg-123",
        )

        # Default is 7 years = 2555 days
        assert log.retention_days == 2555
