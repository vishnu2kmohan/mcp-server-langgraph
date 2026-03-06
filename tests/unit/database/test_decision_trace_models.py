"""
Unit tests for DecisionTrace and DecisionEdge database models.

Tests SQLAlchemy model definitions for context graph decision tracing.
"""

import gc
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from mcp_server_langgraph.database import Base
from tests.conftest import get_user_id

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_trace_models")
class TestDecisionTrace:
    """Test DecisionTrace model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_table_name(self) -> None:
        """Test DecisionTrace has correct table name."""
        from mcp_server_langgraph.database.models import DecisionTrace

        assert DecisionTrace.__tablename__ == "decision_traces"

    def test_decision_trace_inherits_from_base(self) -> None:
        """Test DecisionTrace inherits from declarative Base."""
        from mcp_server_langgraph.database.models import DecisionTrace

        assert issubclass(DecisionTrace, Base)

    def test_decision_trace_columns_exist(self) -> None:
        """Test DecisionTrace has expected columns."""
        from mcp_server_langgraph.database.models import DecisionTrace

        column_names = [col.name for col in DecisionTrace.__table__.columns]

        expected_columns = [
            # Primary key
            "id",
            "trace_id",
            # Context identifiers
            "run_id",
            "session_id",
            "workflow_id",
            "project_id",
            "organization_id",
            "user_id",
            # Temporal
            "timestamp",
            "sequence_number",
            # Decision classification
            "decision_type",
            "decision_stage",
            # Input context
            "query_text",
            "input_artifacts",
            "available_options",
            "constraints",
            # Decision output
            "chosen_action",
            "selected_items",
            "confidence",
            # Reasoning
            "rationale",
            "reasoning_chain",
            "policy_version",
            "feature_flags_snapshot",
            # Approval (HITL)
            "requires_approval",
            "approver_id",
            "approval_status",
            "approval_rationale",
            # Outcome
            "outcome",
            "outcome_details",
            "user_feedback",
            # Embedding
            "embedding_text",
            # OTEL correlation
            "otel_trace_id",
            "otel_span_id",
        ]

        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_decision_trace_indexes_exist(self) -> None:
        """Test DecisionTrace has expected indexes."""
        from mcp_server_langgraph.database.models import DecisionTrace

        indexes = DecisionTrace.__table__.indexes
        index_names = {idx.name for idx in indexes}

        expected_indexes = [
            "ix_decision_trace_id",
            "ix_decision_session",
            "ix_decision_user",
            "ix_decision_org",
            "ix_decision_type",
            "ix_decision_timestamp",
            "ix_decision_session_seq",
            "ix_decision_org_time",
            "ix_decision_outcome",
        ]

        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"

    def test_decision_trace_repr(self) -> None:
        """Test DecisionTrace __repr__ method."""
        from mcp_server_langgraph.database.models import DecisionTrace

        record = DecisionTrace(
            id=1,
            trace_id="trace-abc123",
            run_id="run-xyz",
            session_id="session-456",
            organization_id="org:acme",
            user_id=get_user_id("alice"),
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            sequence_number=0,
            decision_type="routing",
            decision_stage="action",
            query_text="How do I deploy to production?",
            chosen_action="call_deploy_tool",
            confidence=Decimal("0.950"),
            rationale="User requested deployment assistance",
        )

        repr_str = repr(record)
        assert "DecisionTrace" in repr_str
        assert "trace-abc123" in repr_str
        assert "routing" in repr_str

    def test_decision_trace_to_dict(self) -> None:
        """Test DecisionTrace to_dict method."""
        from mcp_server_langgraph.database.models import DecisionTrace

        timestamp = datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC)
        record = DecisionTrace(
            id=1,
            trace_id="trace-abc123",
            run_id="run-xyz",
            session_id="session-456",
            workflow_id="workflow-789",
            project_id="project:backend",
            organization_id="org:acme",
            user_id=get_user_id("alice"),
            timestamp=timestamp,
            sequence_number=5,
            decision_type="tool_selection",
            decision_stage="action",
            query_text="Calculate the sum",
            chosen_action="call_calculator",
            confidence=Decimal("0.875"),
            rationale="User needs mathematical computation",
            outcome="success",
        )

        result = record.to_dict()

        assert result["trace_id"] == "trace-abc123"
        assert result["run_id"] == "run-xyz"
        assert result["session_id"] == "session-456"
        assert result["workflow_id"] == "workflow-789"
        assert result["project_id"] == "project:backend"
        assert result["organization_id"] == "org:acme"
        assert result["user_id"] == "user:alice"
        assert result["decision_type"] == "tool_selection"
        assert result["decision_stage"] == "action"
        assert result["query_text"] == "Calculate the sum"
        assert result["chosen_action"] == "call_calculator"
        assert result["confidence"] == 0.875
        assert result["rationale"] == "User needs mathematical computation"
        assert result["outcome"] == "success"
        # Verify timestamp is ISO format
        assert "2026-01-08" in result["timestamp"]

    def test_decision_trace_nullable_fields(self) -> None:
        """Test DecisionTrace nullable fields are properly defined."""
        from mcp_server_langgraph.database.models import DecisionTrace

        columns = {col.name: col for col in DecisionTrace.__table__.columns}

        # Required fields (not nullable)
        assert columns["trace_id"].nullable is False
        assert columns["run_id"].nullable is False
        assert columns["session_id"].nullable is False
        assert columns["organization_id"].nullable is False
        assert columns["user_id"].nullable is False
        assert columns["timestamp"].nullable is False
        assert columns["decision_type"].nullable is False
        assert columns["decision_stage"].nullable is False
        assert columns["query_text"].nullable is False
        assert columns["chosen_action"].nullable is False
        assert columns["confidence"].nullable is False
        assert columns["rationale"].nullable is False

        # Optional fields (nullable)
        assert columns["workflow_id"].nullable is True
        assert columns["project_id"].nullable is True
        assert columns["input_artifacts"].nullable is True
        assert columns["available_options"].nullable is True
        assert columns["constraints"].nullable is True
        assert columns["selected_items"].nullable is True
        assert columns["reasoning_chain"].nullable is True
        assert columns["policy_version"].nullable is True
        assert columns["feature_flags_snapshot"].nullable is True
        assert columns["approver_id"].nullable is True
        assert columns["approval_status"].nullable is True
        assert columns["approval_rationale"].nullable is True
        assert columns["outcome"].nullable is True
        assert columns["outcome_details"].nullable is True
        assert columns["user_feedback"].nullable is True
        assert columns["embedding_text"].nullable is True
        assert columns["otel_trace_id"].nullable is True
        assert columns["otel_span_id"].nullable is True


@pytest.mark.xdist_group(name="test_decision_trace_models")
class TestDecisionEdge:
    """Test DecisionEdge model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_edge_table_name(self) -> None:
        """Test DecisionEdge has correct table name."""
        from mcp_server_langgraph.database.models import DecisionEdge

        assert DecisionEdge.__tablename__ == "decision_edges"

    def test_decision_edge_inherits_from_base(self) -> None:
        """Test DecisionEdge inherits from declarative Base."""
        from mcp_server_langgraph.database.models import DecisionEdge

        assert issubclass(DecisionEdge, Base)

    def test_decision_edge_columns_exist(self) -> None:
        """Test DecisionEdge has expected columns."""
        from mcp_server_langgraph.database.models import DecisionEdge

        column_names = [col.name for col in DecisionEdge.__table__.columns]

        expected_columns = [
            "id",
            "edge_id",
            "trace_id",
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relation",
            "weight",
            "edge_metadata",
            "timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_decision_edge_indexes_exist(self) -> None:
        """Test DecisionEdge has expected indexes."""
        from mcp_server_langgraph.database.models import DecisionEdge

        indexes = DecisionEdge.__table__.indexes
        index_names = {idx.name for idx in indexes}

        expected_indexes = [
            "ix_edge_trace_id",
            "ix_edge_source",
            "ix_edge_target",
            "ix_edge_relation",
        ]

        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"

    def test_decision_edge_foreign_key(self) -> None:
        """Test DecisionEdge has FK to decision_traces."""
        from mcp_server_langgraph.database.models import DecisionEdge

        columns = {col.name: col for col in DecisionEdge.__table__.columns}
        trace_id_col = columns["trace_id"]

        # Check FK exists
        assert len(trace_id_col.foreign_keys) == 1
        fk = list(trace_id_col.foreign_keys)[0]
        assert "decision_traces.trace_id" in str(fk.target_fullname)

    def test_decision_edge_repr(self) -> None:
        """Test DecisionEdge __repr__ method."""
        from mcp_server_langgraph.database.models import DecisionEdge

        record = DecisionEdge(
            id=1,
            edge_id="edge-abc123",
            trace_id="trace-xyz",
            source_type="session",
            source_id="session-456",
            target_type="tool",
            target_id="calculator",
            relation="invoked",
            weight=Decimal("1.0"),
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
        )

        repr_str = repr(record)
        assert "DecisionEdge" in repr_str
        assert "edge-abc123" in repr_str
        assert "invoked" in repr_str


@pytest.mark.xdist_group(name="test_decision_trace_models")
class TestDatabaseBaseContainsDecisionTables:
    """Test database Base configuration includes decision tables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_metadata_contains_decision_traces_table(self) -> None:
        """Test Base metadata contains the decision_traces table."""
        # Import to ensure models are registered

        table_names = list(Base.metadata.tables.keys())
        assert "decision_traces" in table_names

    def test_base_metadata_contains_decision_edges_table(self) -> None:
        """Test Base metadata contains the decision_edges table."""
        # Import to ensure models are registered

        table_names = list(Base.metadata.tables.keys())
        assert "decision_edges" in table_names
