"""
Unit tests for LangGraphExecutionTrace SQLAlchemy model.

TDD RED Phase: Tests for the database model that stores LangGraph node execution traces.

This model captures:
- Node execution events (running → completed/failed)
- Timing information (start_time, end_time, duration_ms)
- Context (session_id, run_id, workflow_id)
- GDPR compliance (user_id, organization_id)
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_models")
class TestLangGraphExecutionTraceModel:
    """Tests for LangGraphExecutionTrace SQLAlchemy model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langgraph_execution_trace_model_class_is_importable(self) -> None:
        """LangGraphExecutionTrace model should exist and be importable."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert LangGraphExecutionTrace is not None

    def test_model_has_trace_id_primary_key(self) -> None:
        """Model should have trace_id as primary key."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "trace_id")

    def test_model_has_session_id(self) -> None:
        """Model should have session_id for session correlation."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "session_id")

    def test_model_has_run_id(self) -> None:
        """Model should have run_id for LangGraph run correlation."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "run_id")

    def test_model_has_workflow_id(self) -> None:
        """Model should have optional workflow_id."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "workflow_id")

    def test_model_has_user_id(self) -> None:
        """Model should have user_id for GDPR compliance."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "user_id")

    def test_model_has_organization_id(self) -> None:
        """Model should have organization_id for analytics."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "organization_id")

    def test_model_has_node_name(self) -> None:
        """Model should have node_name (e.g., router, planner)."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "node_name")

    def test_model_has_node_id(self) -> None:
        """Model should have optional node_id."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "node_id")

    def test_model_has_node_type(self) -> None:
        """Model should have optional node_type."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "node_type")

    def test_model_has_status(self) -> None:
        """Model should have status (running, completed, failed, skipped)."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "status")

    def test_model_has_start_time(self) -> None:
        """Model should have start_time (epoch ms)."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "start_time")

    def test_model_has_end_time(self) -> None:
        """Model should have optional end_time (epoch ms)."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "end_time")

    def test_model_has_duration_ms(self) -> None:
        """Model should have optional duration_ms."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "duration_ms")

    def test_model_has_sequence_number(self) -> None:
        """Model should have sequence_number for ordering."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "sequence_number")

    def test_model_has_attributes(self) -> None:
        """Model should have optional attributes (JSONB)."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "attributes")

    def test_model_has_error_message(self) -> None:
        """Model should have optional error_message."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "error_message")

    def test_model_has_created_at(self) -> None:
        """Model should have created_at timestamp."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "created_at")

    def test_model_table_name(self) -> None:
        """Model should use langgraph_execution_traces table."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert LangGraphExecutionTrace.__tablename__ == "langgraph_execution_traces"

    def test_model_inherits_from_base(self) -> None:
        """Model should inherit from SQLAlchemy Base."""
        from mcp_server_langgraph.database.models import Base, LangGraphExecutionTrace

        assert issubclass(LangGraphExecutionTrace, Base)

    def test_model_has_to_dict_method(self) -> None:
        """Model should have to_dict() method for GDPR export."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        assert hasattr(LangGraphExecutionTrace, "to_dict")
        assert callable(LangGraphExecutionTrace.to_dict)

    def test_to_dict_returns_expected_keys(self) -> None:
        """to_dict() should return expected keys."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        trace = LangGraphExecutionTrace(
            trace_id="trace-123",
            session_id="session-456",
            run_id="run-xyz",
            user_id="user:alice",
            organization_id="org:acme",
            node_name="router",
            status="completed",
            start_time=1704720000000,
            sequence_number=0,
            created_at=datetime.now(UTC),
        )

        result = trace.to_dict()

        assert isinstance(result, dict)
        assert "trace_id" in result
        assert "session_id" in result
        assert "user_id" in result
        assert "node_name" in result
        assert "status" in result
        assert result["trace_id"] == "trace-123"

    def test_langgraph_execution_trace_repr_contains_trace_id(self) -> None:
        """Model __repr__ should be informative and contain trace_id."""
        from mcp_server_langgraph.database.models import LangGraphExecutionTrace

        trace = LangGraphExecutionTrace(
            trace_id="trace-123",
            session_id="session-456",
            run_id="run-xyz",
            user_id="user:alice",
            organization_id="org:acme",
            node_name="router",
            status="completed",
            start_time=1704720000000,
            sequence_number=0,
            created_at=datetime.now(UTC),
        )

        repr_str = repr(trace)
        assert "LangGraphExecutionTrace" in repr_str
        assert "trace-123" in repr_str
