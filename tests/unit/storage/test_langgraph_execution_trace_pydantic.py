"""
Unit tests for LangGraph execution trace Pydantic models.

TDD RED Phase: Tests for Pydantic models used in API serialization.

Models:
- LangGraphExecutionTraceCreate: Input model for creating traces
- LangGraphExecutionTraceRead: Output model for API responses
- LangGraphExecutionTraceSummary: Lightweight model for list responses
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_pydantic")
class TestLangGraphExecutionTraceCreate:
    """Tests for LangGraphExecutionTraceCreate Pydantic model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langgraph_execution_trace_create_model_is_importable(self) -> None:
        """LangGraphExecutionTraceCreate model should exist and be importable."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceCreate

        assert LangGraphExecutionTraceCreate is not None

    def test_langgraph_execution_trace_create_accepts_required_fields(self) -> None:
        """Model should accept and validate required fields."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceCreate

        # Required fields - this should work without error
        trace = LangGraphExecutionTraceCreate(
            trace_id="trace-123",
            session_id="session-456",
            run_id="run-xyz",
            user_id="user:alice",
            organization_id="org:acme",
            node_name="router",
            status="running",
            start_time=1704720000000,
            sequence_number=0,
        )

        assert trace.trace_id == "trace-123"
        assert trace.session_id == "session-456"
        assert trace.node_name == "router"
        assert trace.status == "running"

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields should default to None."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceCreate

        trace = LangGraphExecutionTraceCreate(
            trace_id="trace-123",
            session_id="session-456",
            run_id="run-xyz",
            user_id="user:alice",
            organization_id="org:acme",
            node_name="router",
            status="running",
            start_time=1704720000000,
            sequence_number=0,
        )

        assert trace.workflow_id is None
        assert trace.node_id is None
        assert trace.node_type is None
        assert trace.end_time is None
        assert trace.duration_ms is None
        assert trace.attributes is None
        assert trace.error_message is None

    def test_model_validates_status(self) -> None:
        """Status should only accept valid values."""

        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceCreate

        # Valid statuses should work
        for status in ["running", "completed", "failed", "skipped"]:
            trace = LangGraphExecutionTraceCreate(
                trace_id="trace-123",
                session_id="session-456",
                run_id="run-xyz",
                user_id="user:alice",
                organization_id="org:acme",
                node_name="router",
                status=status,
                start_time=1704720000000,
                sequence_number=0,
            )
            assert trace.status == status


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_pydantic")
class TestLangGraphExecutionTraceRead:
    """Tests for LangGraphExecutionTraceRead Pydantic model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langgraph_execution_trace_read_model_is_importable(self) -> None:
        """LangGraphExecutionTraceRead model should exist and be importable."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceRead

        assert LangGraphExecutionTraceRead is not None

    def test_includes_all_fields(self) -> None:
        """Read model should include all fields."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceRead

        trace = LangGraphExecutionTraceRead(
            trace_id="trace-123",
            session_id="session-456",
            run_id="run-xyz",
            user_id="user:alice",
            organization_id="org:acme",
            node_name="router",
            node_id="router-node-1",
            node_type="default",
            status="completed",
            start_time=1704720000000,
            end_time=1704720001000,
            duration_ms=1000,
            sequence_number=0,
            attributes={"key": "value"},
            error_message=None,
            created_at=datetime.now(UTC),
        )

        assert trace.trace_id == "trace-123"
        assert trace.node_id == "router-node-1"
        assert trace.duration_ms == 1000
        assert trace.attributes == {"key": "value"}

    def test_model_validation_from_orm(self) -> None:
        """Read model should support from_attributes (ORM mode)."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceRead

        # Check model config allows from_attributes
        assert LangGraphExecutionTraceRead.model_config.get("from_attributes", False) is True


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_pydantic")
class TestLangGraphExecutionTraceSummary:
    """Tests for LangGraphExecutionTraceSummary Pydantic model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langgraph_execution_trace_summary_model_is_importable(self) -> None:
        """LangGraphExecutionTraceSummary model should exist and be importable."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceSummary

        assert LangGraphExecutionTraceSummary is not None

    def test_contains_minimal_fields(self) -> None:
        """Summary model should contain minimal fields for lists."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceSummary

        summary = LangGraphExecutionTraceSummary(
            trace_id="trace-123",
            node_name="router",
            status="completed",
            start_time=1704720000000,
            end_time=1704720001000,
            duration_ms=1000,
            sequence_number=0,
        )

        assert summary.trace_id == "trace-123"
        assert summary.node_name == "router"
        assert summary.status == "completed"
        assert summary.duration_ms == 1000

    def test_does_not_include_heavy_fields(self) -> None:
        """Summary model should not include heavy fields like attributes."""
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceSummary

        # Get model fields
        fields = LangGraphExecutionTraceSummary.model_fields.keys()

        # Heavy fields should not be included
        assert "attributes" not in fields
        assert "error_message" not in fields
        assert "user_id" not in fields
        assert "organization_id" not in fields


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_pydantic")
class TestLangGraphExecutionTracePydanticExports:
    """Tests for Pydantic model exports from storage.models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_model_exported(self) -> None:
        """LangGraphExecutionTraceCreate should be exported."""
        from mcp_server_langgraph.storage import models

        assert hasattr(models, "LangGraphExecutionTraceCreate")

    def test_read_model_exported(self) -> None:
        """LangGraphExecutionTraceRead should be exported."""
        from mcp_server_langgraph.storage import models

        assert hasattr(models, "LangGraphExecutionTraceRead")

    def test_summary_model_exported(self) -> None:
        """LangGraphExecutionTraceSummary should be exported."""
        from mcp_server_langgraph.storage import models

        assert hasattr(models, "LangGraphExecutionTraceSummary")
