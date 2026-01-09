"""
Unit tests for Context Graph Pydantic Models.

Tests the enums and request/response models for decision traces.
"""

import gc
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_trace_pydantic")
class TestDecisionEnums:
    """Tests for decision type and stage enums."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_type_enum_values(self) -> None:
        """Test DecisionType enum has expected values."""
        from mcp_server_langgraph.storage.models import DecisionType

        assert DecisionType.ROUTING.value == "routing"
        assert DecisionType.TOOL_SELECTION.value == "tool_selection"
        assert DecisionType.SKILL_SELECTION.value == "skill_selection"
        assert DecisionType.MODEL_SELECTION.value == "model_selection"
        assert DecisionType.RESPONSE.value == "response"
        assert DecisionType.APPROVAL.value == "approval"
        assert DecisionType.EXCEPTION.value == "exception"

    def test_decision_type_is_string_enum(self) -> None:
        """Test DecisionType is a string enum for JSON serialization."""
        from mcp_server_langgraph.storage.models import DecisionType

        # str enums are equal to their value when compared
        assert DecisionType.ROUTING == "routing"
        assert DecisionType.ROUTING.value == "routing"
        # They serialize to their value in JSON (via Pydantic)
        assert isinstance(DecisionType.ROUTING, str)

    def test_decision_stage_enum_values(self) -> None:
        """Test DecisionStage enum has expected values."""
        from mcp_server_langgraph.storage.models import DecisionStage

        assert DecisionStage.CONTEXT_GATHERING.value == "context_gathering"
        assert DecisionStage.POLICY_CHECK.value == "policy_check"
        assert DecisionStage.ACTION.value == "action"
        assert DecisionStage.WRITE.value == "write"

    def test_decision_outcome_enum_values(self) -> None:
        """Test DecisionOutcome enum has expected values."""
        from mcp_server_langgraph.storage.models import DecisionOutcome

        assert DecisionOutcome.SUCCESS.value == "success"
        assert DecisionOutcome.FAILURE.value == "failure"
        assert DecisionOutcome.PARTIAL.value == "partial"
        assert DecisionOutcome.PENDING.value == "pending"


@pytest.mark.xdist_group(name="test_decision_trace_pydantic")
class TestDecisionTraceCreate:
    """Tests for DecisionTraceCreate request model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_create_valid(self) -> None:
        """Test creating a valid DecisionTraceCreate."""
        from mcp_server_langgraph.storage.models import (
            DecisionStage,
            DecisionTraceCreate,
            DecisionType,
        )

        trace = DecisionTraceCreate(
            run_id="run-abc123",
            session_id="session-456",
            decision_type=DecisionType.ROUTING,
            decision_stage=DecisionStage.ACTION,
            query_text="How do I deploy?",
            chosen_action="call_deploy_tool",
            confidence=0.95,
            rationale="User wants to deploy their application",
        )

        assert trace.run_id == "run-abc123"
        assert trace.session_id == "session-456"
        assert trace.decision_type == DecisionType.ROUTING
        assert trace.decision_stage == DecisionStage.ACTION
        assert trace.chosen_action == "call_deploy_tool"
        assert trace.confidence == 0.95

    def test_decision_trace_create_optional_fields(self) -> None:
        """Test DecisionTraceCreate with optional fields."""
        from mcp_server_langgraph.storage.models import (
            DecisionStage,
            DecisionTraceCreate,
            DecisionType,
        )

        trace = DecisionTraceCreate(
            run_id="run-abc123",
            session_id="session-456",
            workflow_id="workflow-789",
            project_id="project:backend",
            decision_type=DecisionType.TOOL_SELECTION,
            decision_stage=DecisionStage.ACTION,
            query_text="Calculate the sum",
            chosen_action="call_calculator",
            confidence=0.85,
            rationale="Math operation needed",
            available_options=["calculator", "code_runner", "search"],
            selected_items=["calculator"],
            policy_version="v2.1.0",
        )

        assert trace.workflow_id == "workflow-789"
        assert trace.project_id == "project:backend"
        assert trace.available_options == ["calculator", "code_runner", "search"]
        assert trace.selected_items == ["calculator"]
        assert trace.policy_version == "v2.1.0"

    def test_decision_trace_create_confidence_validation(self) -> None:
        """Test DecisionTraceCreate validates confidence range."""
        from mcp_server_langgraph.storage.models import (
            DecisionStage,
            DecisionTraceCreate,
            DecisionType,
        )

        # Valid range: 0.0-1.0
        with pytest.raises(ValidationError) as exc_info:
            DecisionTraceCreate(
                run_id="run-abc123",
                session_id="session-456",
                decision_type=DecisionType.ROUTING,
                decision_stage=DecisionStage.ACTION,
                query_text="Test",
                chosen_action="test_action",
                confidence=1.5,  # Invalid: > 1.0
                rationale="Test rationale",
            )

        assert "confidence" in str(exc_info.value)

    def test_decision_trace_create_query_max_length(self) -> None:
        """Test DecisionTraceCreate enforces query_text max length."""
        from mcp_server_langgraph.storage.models import (
            DecisionStage,
            DecisionTraceCreate,
            DecisionType,
        )

        # Should truncate or validate at 500 chars
        long_query = "x" * 600

        with pytest.raises(ValidationError) as exc_info:
            DecisionTraceCreate(
                run_id="run-abc123",
                session_id="session-456",
                decision_type=DecisionType.ROUTING,
                decision_stage=DecisionStage.ACTION,
                query_text=long_query,
                chosen_action="test_action",
                confidence=0.9,
                rationale="Test rationale",
            )

        assert "query_text" in str(exc_info.value)


@pytest.mark.xdist_group(name="test_decision_trace_pydantic")
class TestDecisionTraceRead:
    """Tests for DecisionTraceRead response model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_read_from_dict(self) -> None:
        """Test DecisionTraceRead can be created from dict."""
        from mcp_server_langgraph.storage.models import DecisionTraceRead

        data = {
            "trace_id": "trace-abc123",
            "run_id": "run-xyz",
            "session_id": "session-456",
            "timestamp": datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            "decision_type": "routing",
            "decision_stage": "action",
            "chosen_action": "call_deploy_tool",
            "confidence": 0.95,
            "rationale": "User wants deployment",
        }

        trace = DecisionTraceRead(**data)

        assert trace.trace_id == "trace-abc123"
        assert trace.run_id == "run-xyz"
        assert trace.decision_type == "routing"
        assert trace.confidence == 0.95

    def test_decision_trace_read_optional_fields(self) -> None:
        """Test DecisionTraceRead with optional fields."""
        from mcp_server_langgraph.storage.models import DecisionTraceRead

        trace = DecisionTraceRead(
            trace_id="trace-abc123",
            run_id="run-xyz",
            session_id="session-456",
            workflow_id="workflow-789",
            project_id="project:backend",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            decision_type="tool_selection",
            decision_stage="action",
            chosen_action="calculator",
            confidence=0.85,
            rationale="Math needed",
            outcome="success",
            requires_approval=True,
            approval_status="approved",
        )

        assert trace.workflow_id == "workflow-789"
        assert trace.outcome == "success"
        assert trace.requires_approval is True
        assert trace.approval_status == "approved"

    def test_decision_trace_read_from_attributes(self) -> None:
        """Test DecisionTraceRead works with from_attributes config."""
        from mcp_server_langgraph.storage.models import DecisionTraceRead

        # Simulate ORM model-like object
        class MockTrace:
            trace_id = "trace-mock"
            run_id = "run-mock"
            session_id = "session-mock"
            workflow_id = None
            project_id = None
            timestamp = datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC)
            decision_type = "routing"
            decision_stage = "action"
            chosen_action = "mock_action"
            confidence = 0.9
            rationale = "Mock rationale"
            outcome = None
            requires_approval = False
            approval_status = None

        trace = DecisionTraceRead.model_validate(MockTrace())

        assert trace.trace_id == "trace-mock"
        assert trace.decision_type == "routing"


@pytest.mark.xdist_group(name="test_decision_trace_pydantic")
class TestDecisionTraceSummary:
    """Tests for DecisionTraceSummary list response model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_trace_summary_creation(self) -> None:
        """Test DecisionTraceSummary can be created."""
        from mcp_server_langgraph.storage.models import DecisionTraceSummary

        summary = DecisionTraceSummary(
            trace_id="trace-abc123",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            decision_type="routing",
            chosen_action="deploy_tool",
            confidence=0.95,
            outcome="success",
        )

        assert summary.trace_id == "trace-abc123"
        assert summary.decision_type == "routing"
        assert summary.outcome == "success"

    def test_decision_trace_summary_optional_outcome(self) -> None:
        """Test DecisionTraceSummary with optional outcome."""
        from mcp_server_langgraph.storage.models import DecisionTraceSummary

        summary = DecisionTraceSummary(
            trace_id="trace-abc123",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            decision_type="routing",
            chosen_action="deploy_tool",
            confidence=0.95,
        )

        assert summary.outcome is None


@pytest.mark.xdist_group(name="test_decision_trace_pydantic")
class TestPrecedentSearchModels:
    """Tests for precedent search request/response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_precedent_search_request_valid(self) -> None:
        """Test PrecedentSearchRequest with valid data."""
        from mcp_server_langgraph.storage.models import (
            DecisionType,
            PrecedentSearchRequest,
        )

        request = PrecedentSearchRequest(
            query="How do I handle authentication errors?",
            decision_type=DecisionType.ROUTING,
            limit=10,
        )

        assert "authentication" in request.query
        assert request.decision_type == DecisionType.ROUTING
        assert request.limit == 10

    def test_precedent_search_request_query_min_length(self) -> None:
        """Test PrecedentSearchRequest validates query min length."""
        from mcp_server_langgraph.storage.models import PrecedentSearchRequest

        with pytest.raises(ValidationError) as exc_info:
            PrecedentSearchRequest(query="ab", limit=10)  # Too short

        assert "query" in str(exc_info.value)

    def test_precedent_search_request_limit_range(self) -> None:
        """Test PrecedentSearchRequest validates limit range."""
        from mcp_server_langgraph.storage.models import PrecedentSearchRequest

        with pytest.raises(ValidationError):
            PrecedentSearchRequest(query="valid query", limit=0)  # Too low

        with pytest.raises(ValidationError):
            PrecedentSearchRequest(query="valid query", limit=200)  # Too high

    def test_precedent_search_result_valid(self) -> None:
        """Test PrecedentSearchResult with valid data."""
        from mcp_server_langgraph.storage.models import (
            DecisionTraceRead,
            PrecedentSearchResult,
        )

        trace = DecisionTraceRead(
            trace_id="trace-abc123",
            run_id="run-xyz",
            session_id="session-456",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            decision_type="routing",
            decision_stage="action",
            chosen_action="deploy_tool",
            confidence=0.95,
            rationale="User wanted deployment",
        )

        result = PrecedentSearchResult(trace=trace, similarity_score=0.87)

        assert result.trace.trace_id == "trace-abc123"
        assert result.similarity_score == 0.87

    def test_precedent_search_result_score_validation(self) -> None:
        """Test PrecedentSearchResult validates similarity score."""
        from mcp_server_langgraph.storage.models import (
            DecisionTraceRead,
            PrecedentSearchResult,
        )

        trace = DecisionTraceRead(
            trace_id="trace-abc123",
            run_id="run-xyz",
            session_id="session-456",
            timestamp=datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC),
            decision_type="routing",
            decision_stage="action",
            chosen_action="deploy_tool",
            confidence=0.95,
            rationale="User wanted deployment",
        )

        with pytest.raises(ValidationError):
            PrecedentSearchResult(trace=trace, similarity_score=1.5)  # > 1.0
