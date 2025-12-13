"""
Workflow Repository Unit Tests

Tests for workflow storage operations per TDD methodology.
Tests written FIRST before implementation (RED phase).
"""

import gc
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mcp_server_langgraph.storage.models import Workflow, WorkflowSummary


pytestmark = [
    pytest.mark.unit,
]


@pytest.mark.xdist_group(name="test_workflow_repository")
class TestWorkflowModel:
    """Tests for Workflow model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_create_with_required_fields(self) -> None:
        """
        GIVEN valid workflow data
        WHEN Workflow is created
        THEN model should have all required fields
        """
        workflow = Workflow(
            id=str(uuid4()),
            name="Test Workflow",
        )

        assert workflow.id is not None
        assert workflow.name == "Test Workflow"
        assert workflow.description == ""
        assert workflow.nodes == []
        assert workflow.edges == []
        assert workflow.created_at is not None
        assert workflow.updated_at is not None

    def test_workflow_create_with_all_fields(self) -> None:
        """
        GIVEN complete workflow data
        WHEN Workflow is created
        THEN model should have all fields set
        """
        now = datetime.now(UTC)
        workflow = Workflow(
            id=str(uuid4()),
            name="Complete Workflow",
            description="A complete workflow",
            nodes=[{"id": "node1", "type": "start"}],
            edges=[{"source": "node1", "target": "node2"}],
            user_id="user123",
            created_at=now,
            updated_at=now,
        )

        assert workflow.name == "Complete Workflow"
        assert workflow.description == "A complete workflow"
        assert len(workflow.nodes) == 1
        assert len(workflow.edges) == 1
        assert workflow.user_id == "user123"

    def test_workflow_to_dict(self) -> None:
        """
        GIVEN a Workflow model
        WHEN model_dump is called
        THEN should return serializable dict
        """
        workflow = Workflow(
            id=str(uuid4()),
            name="Test Workflow",
        )

        data = workflow.model_dump()

        assert isinstance(data, dict)
        assert "id" in data
        assert "name" in data
        assert "nodes" in data
        assert "edges" in data

    def test_workflow_to_summary(self) -> None:
        """
        GIVEN a Workflow model
        WHEN to_summary is called
        THEN should return WorkflowSummary
        """
        workflow = Workflow(
            id=str(uuid4()),
            name="Test Workflow",
            description="Test description",
            nodes=[{"id": "1"}, {"id": "2"}],
            edges=[{"source": "1", "target": "2"}],
        )

        summary = workflow.to_summary()

        assert isinstance(summary, WorkflowSummary)
        assert summary.id == workflow.id
        assert summary.name == workflow.name
        assert summary.description == workflow.description
        assert summary.node_count == 2
        assert summary.edge_count == 1


@pytest.mark.xdist_group(name="test_workflow_repository")
class TestWorkflowSummaryModel:
    """Tests for WorkflowSummary model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_summary_create_with_valid_data_has_all_fields(self) -> None:
        """
        GIVEN valid summary data
        WHEN WorkflowSummary is created
        THEN model should have all fields
        """
        now = datetime.now(UTC)
        summary = WorkflowSummary(
            id=str(uuid4()),
            name="Test Workflow",
            description="A test workflow",
            node_count=5,
            edge_count=4,
            created_at=now,
            updated_at=now,
        )

        assert summary.name == "Test Workflow"
        assert summary.node_count == 5
        assert summary.edge_count == 4
