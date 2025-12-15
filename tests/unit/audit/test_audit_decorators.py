"""
Tests for audit decorators.

TDD RED phase: These tests define expected behavior for service-level auditing.

Decorators should:
- @audit_action: Audit any action with category/event_type
- @audit_ai_operation: Capture AI operation details (EU AI Act)
- @audit_data_access: Track data access (HIPAA, GDPR)
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_decorators")
class TestAuditActionDecorator:
    """Tests for @audit_action decorator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_audit_action_logs_event(self) -> None:
        """GIVEN decorated function WHEN called THEN audit event is logged."""
        from mcp_server_langgraph.audit.decorators import audit_action
        from mcp_server_langgraph.audit.models import AuditEventCategory, AuditEventType

        mock_service = AsyncMock()  # async-mock-configured

        @audit_action(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_CREATE,
            resource_type="workflow",
            audit_service=mock_service,
        )
        async def create_workflow(workflow_id: str) -> dict:
            return {"id": workflow_id, "status": "created"}

        result = await create_workflow("wf-123")

        assert result == {"id": "wf-123", "status": "created"}
        mock_service.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_action_captures_resource_id(self) -> None:
        """GIVEN decorated function WHEN called THEN resource_id is captured."""
        from mcp_server_langgraph.audit.decorators import audit_action
        from mcp_server_langgraph.audit.models import AuditEventCategory, AuditEventType

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_action(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            resource_type="session",
            resource_id_param="session_id",
            audit_service=mock_service,
        )
        async def get_session(session_id: str) -> dict:
            return {"id": session_id}

        await get_session("sess-456")

        assert captured_event is not None
        assert captured_event.resource_id == "sess-456"

    @pytest.mark.asyncio
    async def test_audit_action_handles_failure(self) -> None:
        """GIVEN decorated function that fails WHEN called THEN outcome is failure."""
        from mcp_server_langgraph.audit.decorators import audit_action
        from mcp_server_langgraph.audit.models import AuditEventCategory, AuditEventType

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_action(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_DELETE,
            resource_type="connection",
            audit_service=mock_service,
        )
        async def delete_connection(conn_id: str) -> None:
            raise ValueError("Connection not found")

        with pytest.raises(ValueError):
            await delete_connection("conn-789")

        assert captured_event is not None
        assert captured_event.outcome == "error"

    @pytest.mark.asyncio
    async def test_audit_action_with_regulations(self) -> None:
        """GIVEN decorator with regulations WHEN called THEN regulation_tags set."""
        from mcp_server_langgraph.audit.decorators import audit_action
        from mcp_server_langgraph.audit.models import AuditEventCategory, AuditEventType

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_action(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.PHI_ACCESS,
            resource_type="patient_record",
            regulations=["HIPAA", "GDPR"],
            audit_service=mock_service,
        )
        async def access_patient_data(patient_id: str) -> dict:
            return {"id": patient_id, "name": "John Doe"}

        await access_patient_data("patient-001")

        assert captured_event is not None
        assert "HIPAA" in captured_event.regulation_tags
        assert "GDPR" in captured_event.regulation_tags


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_decorators")
class TestAuditAIOperationDecorator:
    """Tests for @audit_ai_operation decorator (EU AI Act)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_audit_ai_operation_captures_details(self) -> None:
        """GIVEN AI operation WHEN executed THEN ai_operation details captured."""
        from mcp_server_langgraph.audit.decorators import audit_ai_operation

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_ai_operation(
            model_id="gpt-4o",
            provider="openai",
            decision_type="generation",
            audit_service=mock_service,
        )
        async def generate_text(prompt: str) -> str:
            return "Generated response"

        result = await generate_text("Hello, AI!")

        assert result == "Generated response"
        assert captured_event is not None
        assert captured_event.ai_operation is not None
        assert captured_event.ai_operation.model_id == "gpt-4o"
        assert captured_event.ai_operation.provider == "openai"
        assert captured_event.ai_operation.decision_type == "generation"

    @pytest.mark.asyncio
    async def test_audit_ai_operation_includes_eu_ai_act_tag(self) -> None:
        """GIVEN AI operation WHEN executed THEN EU_AI_ACT regulation tag set."""
        from mcp_server_langgraph.audit.decorators import audit_ai_operation

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_ai_operation(
            model_id="claude-3-opus",
            provider="anthropic",
            audit_service=mock_service,
        )
        async def call_anthropic() -> str:
            return "Response from Claude"

        await call_anthropic()

        assert captured_event is not None
        assert "EU_AI_ACT" in captured_event.regulation_tags


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_decorators")
class TestAuditDataAccessDecorator:
    """Tests for @audit_data_access decorator (HIPAA, GDPR)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_audit_data_access_logs_read(self) -> None:
        """GIVEN data access WHEN reading THEN DATA_READ event logged."""
        from mcp_server_langgraph.audit.decorators import audit_data_access
        from mcp_server_langgraph.audit.models import AuditEventType

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_data_access(
            resource_type="document",
            sensitivity="high",
            audit_service=mock_service,
        )
        async def read_document(doc_id: str) -> dict:
            return {"id": doc_id, "content": "Secret data"}

        await read_document("doc-sensitive")

        assert captured_event is not None
        assert captured_event.event_type == AuditEventType.DATA_READ
        assert captured_event.details.get("sensitivity") == "high"

    @pytest.mark.asyncio
    async def test_audit_data_access_for_phi(self) -> None:
        """GIVEN PHI access WHEN reading THEN HIPAA tag included."""
        from mcp_server_langgraph.audit.decorators import audit_data_access

        captured_event = None

        async def mock_log_event(event):
            nonlocal captured_event
            captured_event = event

        mock_service = MagicMock()
        mock_service.log_event = mock_log_event

        @audit_data_access(
            resource_type="patient_record",
            sensitivity="phi",
            regulations=["HIPAA"],
            audit_service=mock_service,
        )
        async def read_phi(record_id: str) -> dict:
            return {"id": record_id, "diagnosis": "Healthy"}

        await read_phi("rec-001")

        assert captured_event is not None
        assert "HIPAA" in captured_event.regulation_tags
