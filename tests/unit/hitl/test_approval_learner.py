"""Tests for ApprovalLearner.

TDD: These tests define the contract for the ApprovalLearner that
learns user approval preferences to predict future approvals.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_learner_basic")
class TestApprovalLearnerBasic:
    """Tests for ApprovalLearner basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_learner_exists(self) -> None:
        """Test ApprovalLearner class exists."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        assert ApprovalLearner is not None

    def test_approval_learner_has_record_decision_method(self) -> None:
        """Test ApprovalLearner has record_decision method."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        learner = ApprovalLearner()

        assert hasattr(learner, "record_decision")

    def test_approval_learner_has_predict_method(self) -> None:
        """Test ApprovalLearner has predict method."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        learner = ApprovalLearner()

        assert hasattr(learner, "predict")

    def test_approval_learner_has_get_history_method(self) -> None:
        """Test ApprovalLearner has get_history method."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        learner = ApprovalLearner()

        assert hasattr(learner, "get_history")


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_decision")
class TestApprovalDecision:
    """Tests for ApprovalDecision dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_decision_exists(self) -> None:
        """Test ApprovalDecision dataclass exists."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        assert ApprovalDecision is not None

    def test_approval_decision_has_action_type(self) -> None:
        """Test ApprovalDecision has action_type field."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=True,
            user_id="user-123",
        )

        assert decision.action_type == "file_write"

    def test_approval_decision_has_action_description(self) -> None:
        """Test ApprovalDecision has action_description field."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=True,
            user_id="user-123",
        )

        assert decision.action_description == "Write to config.yaml"

    def test_approval_decision_has_approved(self) -> None:
        """Test ApprovalDecision has approved field."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=True,
            user_id="user-123",
        )

        assert decision.approved is True

    def test_approval_decision_has_user_id(self) -> None:
        """Test ApprovalDecision has user_id field."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=True,
            user_id="user-123",
        )

        assert decision.user_id == "user-123"

    def test_approval_decision_has_optional_reason(self) -> None:
        """Test ApprovalDecision has optional reason field."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision

        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=False,
            user_id="user-123",
            reason="File already exists",
        )

        assert decision.reason == "File already exists"


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_prediction")
class TestApprovalPrediction:
    """Tests for ApprovalPrediction dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_prediction_exists(self) -> None:
        """Test ApprovalPrediction dataclass exists."""
        from mcp_server_langgraph.hitl.learning import ApprovalPrediction

        assert ApprovalPrediction is not None

    def test_approval_prediction_has_likely_approved(self) -> None:
        """Test ApprovalPrediction has likely_approved field."""
        from mcp_server_langgraph.hitl.learning import ApprovalPrediction

        prediction = ApprovalPrediction(
            likely_approved=True,
            confidence=0.85,
            similar_decisions=3,
        )

        assert prediction.likely_approved is True

    def test_approval_prediction_has_confidence(self) -> None:
        """Test ApprovalPrediction has confidence field."""
        from mcp_server_langgraph.hitl.learning import ApprovalPrediction

        prediction = ApprovalPrediction(
            likely_approved=True,
            confidence=0.85,
            similar_decisions=3,
        )

        assert prediction.confidence == 0.85

    def test_approval_prediction_has_similar_decisions(self) -> None:
        """Test ApprovalPrediction has similar_decisions count."""
        from mcp_server_langgraph.hitl.learning import ApprovalPrediction

        prediction = ApprovalPrediction(
            likely_approved=True,
            confidence=0.85,
            similar_decisions=3,
        )

        assert prediction.similar_decisions == 3


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_learner_record")
class TestApprovalLearnerRecord:
    """Tests for ApprovalLearner.record_decision()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_decision_stores_decision(self) -> None:
        """Test record_decision stores the decision."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()
        decision = ApprovalDecision(
            action_type="file_write",
            action_description="Write to config.yaml",
            approved=True,
            user_id="user-123",
        )

        learner.record_decision(decision)

        history = learner.get_history(user_id="user-123")
        assert len(history) == 1
        assert history[0] is decision

    def test_record_decision_stores_multiple(self) -> None:
        """Test record_decision stores multiple decisions."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()

        decision1 = ApprovalDecision(
            action_type="file_write",
            action_description="Write file 1",
            approved=True,
            user_id="user-123",
        )
        decision2 = ApprovalDecision(
            action_type="file_write",
            action_description="Write file 2",
            approved=False,
            user_id="user-123",
        )

        learner.record_decision(decision1)
        learner.record_decision(decision2)

        history = learner.get_history(user_id="user-123")
        assert len(history) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_learner_predict")
class TestApprovalLearnerPredict:
    """Tests for ApprovalLearner.predict()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_predict_returns_prediction(self) -> None:
        """Test predict returns ApprovalPrediction."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner, ApprovalPrediction

        learner = ApprovalLearner()

        prediction = learner.predict(
            action_type="file_write",
            action_description="Write to config.yaml",
            user_id="user-123",
        )

        assert isinstance(prediction, ApprovalPrediction)

    def test_predict_low_confidence_without_history(self) -> None:
        """Test predict returns low confidence without history."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        learner = ApprovalLearner()

        prediction = learner.predict(
            action_type="file_write",
            action_description="Write to config.yaml",
            user_id="user-123",
        )

        assert prediction.confidence < 0.5
        assert prediction.similar_decisions == 0

    def test_predict_higher_confidence_with_history(self) -> None:
        """Test predict returns higher confidence with history."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()

        # Record multiple approvals for file_write
        for i in range(3):
            decision = ApprovalDecision(
                action_type="file_write",
                action_description=f"Write to file {i}",
                approved=True,
                user_id="user-123",
            )
            learner.record_decision(decision)

        prediction = learner.predict(
            action_type="file_write",
            action_description="Write to another file",
            user_id="user-123",
        )

        assert prediction.likely_approved is True
        assert prediction.confidence >= 0.5
        assert prediction.similar_decisions >= 1

    def test_predict_based_on_action_type_pattern(self) -> None:
        """Test predict uses action_type to find similar decisions."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()

        # Approve file_write actions
        learner.record_decision(
            ApprovalDecision(
                action_type="file_write",
                action_description="Write file A",
                approved=True,
                user_id="user-123",
            )
        )

        # Reject database_delete actions
        learner.record_decision(
            ApprovalDecision(
                action_type="database_delete",
                action_description="Delete record",
                approved=False,
                user_id="user-123",
            )
        )

        file_write_prediction = learner.predict(
            action_type="file_write",
            action_description="Write file B",
            user_id="user-123",
        )

        db_delete_prediction = learner.predict(
            action_type="database_delete",
            action_description="Delete another record",
            user_id="user-123",
        )

        assert file_write_prediction.likely_approved is True
        assert db_delete_prediction.likely_approved is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="approval_learner_history")
class TestApprovalLearnerHistory:
    """Tests for ApprovalLearner.get_history()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_history_filters_by_user(self) -> None:
        """Test get_history filters by user_id."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()

        learner.record_decision(
            ApprovalDecision(
                action_type="file_write",
                action_description="User A file",
                approved=True,
                user_id="user-A",
            )
        )
        learner.record_decision(
            ApprovalDecision(
                action_type="file_write",
                action_description="User B file",
                approved=True,
                user_id="user-B",
            )
        )

        history_a = learner.get_history(user_id="user-A")
        history_b = learner.get_history(user_id="user-B")

        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0].action_description == "User A file"
        assert history_b[0].action_description == "User B file"

    def test_get_history_returns_empty_for_unknown_user(self) -> None:
        """Test get_history returns empty for unknown user."""
        from mcp_server_langgraph.hitl.learning import ApprovalLearner

        learner = ApprovalLearner()

        history = learner.get_history(user_id="unknown-user")

        assert history == []

    def test_get_history_filters_by_action_type(self) -> None:
        """Test get_history can filter by action_type."""
        from mcp_server_langgraph.hitl.learning import ApprovalDecision, ApprovalLearner

        learner = ApprovalLearner()

        learner.record_decision(
            ApprovalDecision(
                action_type="file_write",
                action_description="Write file",
                approved=True,
                user_id="user-123",
            )
        )
        learner.record_decision(
            ApprovalDecision(
                action_type="database_query",
                action_description="Query database",
                approved=True,
                user_id="user-123",
            )
        )

        file_history = learner.get_history(user_id="user-123", action_type="file_write")

        assert len(file_history) == 1
        assert file_history[0].action_type == "file_write"
