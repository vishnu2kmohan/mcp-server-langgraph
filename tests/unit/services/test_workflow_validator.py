"""
Workflow Validator Service Tests (TDD Red Phase)

These tests define the expected behavior of the WorkflowValidator service.
Written FIRST per TDD methodology - they should fail until implementation.

The WorkflowValidator service:
- Validates workflow graph structure (acyclic, connected)
- Ensures exactly one start node exists
- Ensures at least one reachable end node
- Detects orphan nodes (not connected to the graph)
- Validates edge targets exist
- Provides warnings for tool availability (optional)

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- Key principle: NO JS VALIDATION DUPLICATION - this is the single source of truth
"""

from __future__ import annotations

import gc
from typing import Any

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# Test Fixtures
# =============================================================================


def make_workflow(
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a workflow dict for testing."""
    return {
        "name": "test-workflow",
        "description": "Test workflow",
        "nodes": nodes or [],
        "edges": edges or [],
    }


def make_node(
    id: str,
    type: str,
    label: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a node dict for testing."""
    return {
        "id": id,
        "type": type,
        "label": label or f"Node {id}",
        "config": config or {},
    }


def make_edge(source: str, target: str, condition: str | None = None) -> dict[str, Any]:
    """Create an edge dict for testing."""
    return {"source": source, "target": target, "condition": condition}


# =============================================================================
# Test: WorkflowValidator Class Exists
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestWorkflowValidatorExists:
    """Tests that WorkflowValidator class and methods exist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_validator_class_exists(self) -> None:
        """WorkflowValidator class should exist in services module."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        assert WorkflowValidator is not None

    def test_workflow_validator_has_validate_method(self) -> None:
        """WorkflowValidator should have async validate method."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        assert hasattr(WorkflowValidator, "validate")
        # Check it's callable
        validator = WorkflowValidator()
        assert callable(validator.validate)

    def test_validation_result_class_exists(self) -> None:
        """ValidationResult model should exist."""
        from mcp_server_langgraph.services.workflow_validator import ValidationResult

        assert ValidationResult is not None

    def test_validation_result_has_required_fields(self) -> None:
        """ValidationResult should have valid, errors, warnings fields."""
        from mcp_server_langgraph.services.workflow_validator import ValidationResult

        # Check schema has required fields
        schema = ValidationResult.model_json_schema()
        properties = schema.get("properties", {})

        assert "valid" in properties
        assert "errors" in properties
        assert "warnings" in properties


# =============================================================================
# Test: Valid Workflow Passes
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestValidWorkflowPasses:
    """Tests that valid workflows pass validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_minimal_valid_workflow_passes(self) -> None:
        """A minimal valid workflow (start -> end) should pass validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_complex_valid_workflow_passes(self) -> None:
        """A complex valid workflow with LLM, router, tool nodes should pass."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("llm1", "llm", config={"model": "gpt-4"}),
                make_node("router", "router"),
                make_node("tool1", "tool", config={"tool_name": "search"}),
                make_node("tool2", "tool", config={"tool_name": "calculate"}),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "llm1"),
                make_edge("llm1", "router"),
                make_edge("router", "tool1", condition="search"),
                make_edge("router", "tool2", condition="calculate"),
                make_edge("tool1", "end"),
                make_edge("tool2", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is True
        assert len(result.errors) == 0


# =============================================================================
# Test: Start Node Validation
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestStartNodeValidation:
    """Tests for start node validation rules."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_missing_start_node_fails(self) -> None:
        """Workflow without a start node should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("llm1", "llm"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("llm1", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("start" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_multiple_start_nodes_fails(self) -> None:
        """Workflow with multiple start nodes should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start1", "start"),
                make_node("start2", "start"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start1", "end"),
                make_edge("start2", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("start" in e.lower() for e in result.errors)


# =============================================================================
# Test: End Node Validation
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestEndNodeValidation:
    """Tests for end node validation rules."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_missing_end_node_fails(self) -> None:
        """Workflow without an end node should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("llm1", "llm"),
            ],
            edges=[
                make_edge("start", "llm1"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("end" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_unreachable_end_node_fails(self) -> None:
        """End node not reachable from start should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("llm1", "llm"),
                make_node("end", "end"),  # Not connected to the graph
            ],
            edges=[
                make_edge("start", "llm1"),
                # No edge to end node
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("end" in e.lower() or "reachable" in e.lower() for e in result.errors)


# =============================================================================
# Test: Acyclic Graph Validation
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestAcyclicValidation:
    """Tests for acyclic graph validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_simple_cycle_fails(self) -> None:
        """Workflow with a simple cycle (A -> B -> A) should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("a", "llm"),
                make_node("b", "llm"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("b", "a"),  # Cycle!
                make_edge("b", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("cycle" in e.lower() or "acyclic" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_self_loop_fails(self) -> None:
        """Workflow with a self-loop (A -> A) should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("loop", "llm"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "loop"),
                make_edge("loop", "loop"),  # Self-loop!
                make_edge("loop", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("cycle" in e.lower() or "loop" in e.lower() for e in result.errors)


# =============================================================================
# Test: Edge Validation
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestEdgeValidation:
    """Tests for edge validation rules."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_edge_to_nonexistent_target_fails(self) -> None:
        """Edge pointing to non-existent node should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "nonexistent"),  # Target doesn't exist!
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("nonexistent" in e.lower() or "target" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_edge_from_nonexistent_source_fails(self) -> None:
        """Edge from non-existent node should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("end", "end"),
            ],
            edges=[
                make_edge("nonexistent", "end"),  # Source doesn't exist!
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("nonexistent" in e.lower() or "source" in e.lower() for e in result.errors)


# =============================================================================
# Test: Orphan Node Detection
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestOrphanNodeDetection:
    """Tests for orphan node detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_orphan_node_fails(self) -> None:
        """Node not connected to any edges should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("orphan", "llm"),  # Not connected!
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "end"),
                # No edges to/from orphan
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert any("orphan" in e.lower() or "connected" in e.lower() for e in result.errors)


# =============================================================================
# Test: Empty Workflow Handling
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestEmptyWorkflowHandling:
    """Tests for empty/minimal workflow handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_empty_workflow_fails(self) -> None:
        """Empty workflow (no nodes) should fail validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(nodes=[], edges=[])

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        assert result.valid is False
        assert len(result.errors) > 0


# =============================================================================
# Test: Warnings (Non-Blocking)
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestValidationWarnings:
    """Tests for validation warnings (non-blocking issues)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unknown_node_type_warns(self) -> None:
        """Unknown node type should produce warning but pass validation."""
        from mcp_server_langgraph.services.workflow_validator import WorkflowValidator

        workflow = make_workflow(
            nodes=[
                make_node("start", "start"),
                make_node("custom", "custom_unknown_type"),  # Unknown type
                make_node("end", "end"),
            ],
            edges=[
                make_edge("start", "custom"),
                make_edge("custom", "end"),
            ],
        )

        validator = WorkflowValidator()
        result = await validator.validate(workflow)

        # Should pass but with warnings
        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("unknown" in w.lower() or "type" in w.lower() for w in result.warnings)


# =============================================================================
# Test: ValidationError Model
# =============================================================================


@pytest.mark.xdist_group(name="test_workflow_validator")
class TestValidationErrorModel:
    """Tests for ValidationError model structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_error_class_exists(self) -> None:
        """ValidationError model should exist."""
        from mcp_server_langgraph.services.workflow_validator import ValidationError

        assert ValidationError is not None

    def test_validation_error_has_required_fields(self) -> None:
        """ValidationError should have code, message, node_id fields."""
        from mcp_server_langgraph.services.workflow_validator import ValidationError

        schema = ValidationError.model_json_schema()
        properties = schema.get("properties", {})

        assert "code" in properties
        assert "message" in properties
        # node_id is optional (may not apply to all errors)
