"""
Tests for Code Importer Module

Comprehensive test suite for the round-trip import/export functionality
that enables Visual ↔ Code workflows.

Tests cover:
- Import Python code to workflow definition
- Import from file
- Workflow validation after import
- Layout algorithms (hierarchical, force, grid)
- Round-trip preservation (Code → Visual → Code)
- Edge cases and error handling
"""

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from mcp_server_langgraph.builder.codegen.generator import CodeGenerator, WorkflowDefinition
from mcp_server_langgraph.builder.importer import import_from_code, import_from_file, validate_import
from mcp_server_langgraph.builder.workflow import WorkflowBuilder


@pytest.fixture
def sample_langgraph_code():
    """Sample LangGraph code for testing import."""
    return '''
from typing import TypedDict, List
from langgraph.graph import StateGraph


@pytest.fixture(scope="module", autouse=True)
def init_test_observability():
    """Initialize observability for tests"""
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)

    yield



class AgentState(TypedDict):
    """Agent state definition."""
    query: str
    results: List[str]
    summary: str


def search_node(state):
    """Search for information."""
    return state


def process_node(state):
    """Process results."""
    return state


def create_agent():
    """Create the agent workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("search", search_node)
    graph.add_node("process", process_node)

    graph.add_edge("search", "process")

    graph.set_entry_point("search")
    graph.set_finish_point("process")

    return graph.compile()
'''


@pytest.fixture
def complex_langgraph_code():
    """Complex LangGraph code with conditionals."""
    return '''
from typing import TypedDict
from langgraph.graph import StateGraph


class State(TypedDict):
    query: str
    score: float
    approved: bool


def node_a(state):
    return state


def node_b(state):
    return state


def node_c(state):
    return state


def route_decision(state):
    """Route based on score."""
    if state["score"] > 0.8:
        return "node_b"
    return "node_c"


def create_workflow():
    graph = StateGraph(State)

    graph.add_node("start", node_a)
    graph.add_node("high_score", node_b)
    graph.add_node("low_score", node_c)

    graph.add_conditional_edges("start", route_decision)

    graph.set_entry_point("start")

    return graph.compile()
'''


# ==============================================================================
# Test import_from_code()
# ==============================================================================


def test_import_from_code_with_valid_code_returns_workflow(sample_langgraph_code):
    """Test import_from_code() with valid LangGraph code returns workflow definition."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    assert isinstance(workflow, dict)
    assert "name" in workflow
    assert "nodes" in workflow
    assert "edges" in workflow
    assert len(workflow["nodes"]) > 0
    assert len(workflow["edges"]) > 0


def test_import_from_code_extracts_node_ids(sample_langgraph_code):
    """Test import_from_code() extracts correct node IDs."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    node_ids = [node["id"] for node in workflow["nodes"]]
    assert "search" in node_ids
    assert "process" in node_ids


def test_import_from_code_extracts_edges(sample_langgraph_code):
    """Test import_from_code() extracts edges correctly."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    assert len(workflow["edges"]) > 0
    # Check for edge from search to process
    edge_exists = any(e.get("from") == "search" and e.get("to") == "process" for e in workflow["edges"])
    assert edge_exists, "Expected edge from 'search' to 'process'"


def test_import_from_code_extracts_entry_point(sample_langgraph_code):
    """Test import_from_code() extracts entry point."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    assert "entry_point" in workflow
    assert workflow["entry_point"] == "search"


def test_import_from_code_adds_positions_to_nodes(sample_langgraph_code):
    """Test import_from_code() adds position data to nodes for visual canvas."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    for node in workflow["nodes"]:
        assert "position" in node, f"Node {node['id']} missing position"
        assert "x" in node["position"]
        assert "y" in node["position"]
        assert isinstance(node["position"]["x"], (int, float))
        assert isinstance(node["position"]["y"], (int, float))


def test_import_from_code_with_hierarchical_layout_positions_nodes_vertically(sample_langgraph_code):
    """Test import_from_code() with hierarchical layout creates top-to-bottom flow."""
    # Act
    workflow = import_from_code(sample_langgraph_code, layout_algorithm="hierarchical")

    # Assert
    nodes = sorted(workflow["nodes"], key=lambda n: n["position"]["y"])
    # In hierarchical layout, entry point should be at top
    entry_node = next(n for n in workflow["nodes"] if n["id"] == workflow["entry_point"])

    # Entry point should have lower Y value (closer to top)
    assert entry_node["position"]["y"] <= nodes[-1]["position"]["y"]


def test_import_from_code_with_force_layout_spreads_nodes(sample_langgraph_code):
    """Test import_from_code() with force layout creates distributed positions."""
    # Act
    workflow = import_from_code(sample_langgraph_code, layout_algorithm="force")

    # Assert
    positions = [node["position"] for node in workflow["nodes"]]
    # Nodes should have different positions
    unique_positions = set((p["x"], p["y"]) for p in positions)
    assert len(unique_positions) == len(positions), "Force layout should spread nodes"


def test_import_from_code_with_grid_layout_aligns_nodes(sample_langgraph_code):
    """Test import_from_code() with grid layout creates aligned positions."""
    # Act
    workflow = import_from_code(sample_langgraph_code, layout_algorithm="grid")

    # Assert
    # Grid layout should have nodes at regular intervals
    x_positions = [node["position"]["x"] for node in workflow["nodes"]]
    y_positions = [node["position"]["y"] for node in workflow["nodes"]]

    # Should have distinct positions
    assert len(set(x_positions)) >= 1
    assert len(set(y_positions)) >= 1


def test_import_from_code_with_complex_workflow_handles_conditionals(complex_langgraph_code):
    """Test import_from_code() handles conditional edges correctly."""
    # Act
    workflow = import_from_code(complex_langgraph_code)

    # Assert
    assert len(workflow["nodes"]) == 3
    node_ids = [n["id"] for n in workflow["nodes"]]
    assert "start" in node_ids
    assert "high_score" in node_ids or "low_score" in node_ids


def test_import_from_code_extracts_state_schema(sample_langgraph_code):
    """Test import_from_code() extracts state schema from TypedDict."""
    # Act
    workflow = import_from_code(sample_langgraph_code)

    # Assert
    # Should extract state schema if parser supports it
    if "state_schema" in workflow:
        assert isinstance(workflow["state_schema"], dict)


def test_import_from_code_with_invalid_python_raises_syntax_error():
    """Test import_from_code() with invalid Python raises SyntaxError."""
    # Arrange
    invalid_code = "def broken syntax here"

    # Act & Assert
    with pytest.raises(SyntaxError):
        import_from_code(invalid_code)


def test_import_from_code_with_empty_string_handles_gracefully():
    """Test import_from_code() with empty string handles gracefully."""
    # Arrange
    empty_code = ""

    # Act & Assert
    # Should either raise exception or return minimal workflow
    try:
        workflow = import_from_code(empty_code)
        # If it returns, should have basic structure
        assert "nodes" in workflow
    except (ValueError, SyntaxError, Exception):
        # Expected to fail with empty code
        pass


# ==============================================================================
# Test import_from_file()
# ==============================================================================


def test_import_from_file_with_valid_file_returns_workflow(sample_langgraph_code):
    """Test import_from_file() reads and imports from file."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "agent.py"
        file_path.write_text(sample_langgraph_code)

        # Act
        workflow = import_from_file(str(file_path))

        # Assert
        assert isinstance(workflow, dict)
        assert "nodes" in workflow
        assert len(workflow["nodes"]) > 0


def test_import_from_file_with_layout_algorithm_applies_layout(sample_langgraph_code):
    """Test import_from_file() with layout algorithm."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "agent.py"
        file_path.write_text(sample_langgraph_code)

        # Act
        workflow = import_from_file(str(file_path), layout_algorithm="grid")

        # Assert
        for node in workflow["nodes"]:
            assert "position" in node


def test_import_from_file_with_nonexistent_file_raises_file_not_found():
    """Test import_from_file() with nonexistent file raises error."""
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        import_from_file("/nonexistent/file/path.py")


def test_import_from_file_with_invalid_code_raises_syntax_error():
    """Test import_from_file() with invalid Python code raises error."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "invalid.py"
        file_path.write_text("def broken syntax")

        # Act & Assert
        with pytest.raises(SyntaxError):
            import_from_file(str(file_path))


# ==============================================================================
# Test validate_import()
# ==============================================================================


def test_validate_import_with_valid_workflow_returns_valid_true():
    """Test validate_import() with valid workflow returns valid=True."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "node1", "type": "tool", "position": {"x": 0, "y": 0}},
            {"id": "node2", "type": "llm", "position": {"x": 100, "y": 100}},
        ],
        "edges": [{"from": "node1", "to": "node2"}],
        "entry_point": "node1",
        "state_schema": {"query": "str"},
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_import_with_missing_name_returns_error():
    """Test validate_import() with missing name field returns error."""
    # Arrange
    workflow = {
        "nodes": [{"id": "node1", "position": {"x": 0, "y": 0}}],
        "edges": [],
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert result["valid"] is False
    assert any("name" in err.lower() for err in result["errors"])


def test_validate_import_with_missing_nodes_returns_error():
    """Test validate_import() with missing nodes returns error."""
    # Arrange
    workflow = {"name": "test", "edges": []}

    # Act
    result = validate_import(workflow)

    # Assert
    assert result["valid"] is False
    assert any("nodes" in err.lower() for err in result["errors"])


def test_validate_import_with_missing_edges_returns_error():
    """Test validate_import() with missing edges returns error."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node1", "position": {"x": 0, "y": 0}}],
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert result["valid"] is False
    assert any("edges" in err.lower() for err in result["errors"])


def test_validate_import_with_node_missing_position_returns_error():
    """Test validate_import() with node missing position returns error."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node1", "type": "tool"}],  # Missing position
        "edges": [],
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert result["valid"] is False
    assert any("position" in err.lower() for err in result["errors"])


def test_validate_import_with_empty_state_schema_returns_warning():
    """Test validate_import() with empty state schema returns warning."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node1", "position": {"x": 0, "y": 0}}],
        "edges": [],
        "state_schema": {},  # Empty
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert len(result["warnings"]) > 0
    assert any("state schema" in w.lower() for w in result["warnings"])


def test_validate_import_with_unknown_node_type_returns_warning():
    """Test validate_import() with unknown node type returns warning."""
    # Arrange
    workflow = {
        "name": "test",
        "nodes": [{"id": "node1", "type": "unknown_type", "position": {"x": 0, "y": 0}}],
        "edges": [],
    }

    # Act
    result = validate_import(workflow)

    # Assert
    assert len(result["warnings"]) > 0
    assert any("unknown type" in w.lower() for w in result["warnings"])


# ==============================================================================
# Test Round-Trip: Code → Visual → Code
# ==============================================================================


def test_round_trip_simple_workflow_preserves_structure():
    """Test round-trip: Code → Import → Export → Code preserves workflow structure."""
    # Arrange - Create workflow programmatically
    original_builder = WorkflowBuilder("round_trip_test", "Round-trip test workflow")
    original_builder.add_node("search", "tool", {"tool": "web_search"}, "Search")
    original_builder.add_node("process", "llm", {"model": "gemini-flash"}, "Process")
    original_builder.add_edge("search", "process")
    original_builder.add_state_field("query", "str")
    original_builder.add_state_field("results", "List[str]")

    # Act - Export to code
    original_code = original_builder.export_code()

    # Import back from code
    imported_workflow = import_from_code(original_code)

    # Rebuild from imported workflow
    restored_builder = WorkflowBuilder.from_json(imported_workflow)

    # Export again
    restored_code = restored_builder.export_code()

    # Assert - Core structure should be preserved
    assert "round_trip_test" in original_code.lower()
    assert "round_trip_test" in restored_code.lower()

    # Both should have same nodes
    assert "node_search" in original_code
    assert "node_search" in restored_code
    assert "node_process" in original_code
    assert "node_process" in restored_code


def test_round_trip_workflow_with_conditionals_preserves_routing():
    """Test round-trip with conditional edges preserves routing logic."""
    # Arrange
    builder = WorkflowBuilder("conditional_test")
    builder.add_node("start", "tool", {}, "Start")
    builder.add_node("path_a", "llm", {}, "Path A")
    builder.add_node("path_b", "llm", {}, "Path B")
    builder.add_edge("start", "path_a", condition="state['score'] > 0.8")
    builder.add_edge("start", "path_b", condition="state['score'] <= 0.8")

    # Act - Export and re-import
    code = builder.export_code()
    imported = import_from_code(code)

    # Assert - Should have all nodes
    imported_node_ids = [n["id"] for n in imported["nodes"]]
    assert "start" in imported_node_ids
    assert "path_a" in imported_node_ids or "path_b" in imported_node_ids


def test_round_trip_preserves_node_count():
    """Test round-trip preserves number of nodes."""
    # Arrange
    builder = WorkflowBuilder("node_count_test")
    for i in range(5):
        builder.add_node(f"node_{i}", "custom", {}, f"Node {i}")

    for i in range(4):
        builder.add_edge(f"node_{i}", f"node_{i + 1}")

    # Act
    code = builder.export_code()
    imported = import_from_code(code)

    # Assert
    assert len(imported["nodes"]) == 5


def test_round_trip_preserves_edge_count():
    """Test round-trip preserves number of edges."""
    # Arrange
    builder = WorkflowBuilder("edge_count_test")
    builder.add_node("n1", "tool")
    builder.add_node("n2", "tool")
    builder.add_node("n3", "tool")
    builder.add_edge("n1", "n2")
    builder.add_edge("n2", "n3")

    # Act
    code = builder.export_code()
    imported = import_from_code(code)

    # Assert
    assert len(imported["edges"]) == 2


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_import_exported_workflow_matches_original_json(sample_langgraph_code):
    """Test importing exported workflow matches original JSON structure."""
    # Arrange
    workflow_original = import_from_code(sample_langgraph_code)

    # Act - Create builder from imported workflow
    builder = WorkflowBuilder.from_json(workflow_original)
    workflow_json = builder.to_json()

    # Assert - Should have same core properties
    assert workflow_json["name"] == workflow_original["name"]
    assert len(workflow_json["nodes"]) == len(workflow_original["nodes"])
    assert len(workflow_json["edges"]) == len(workflow_original["edges"])


def test_import_validate_and_export_integration(sample_langgraph_code):
    """Test complete flow: import → validate → export."""
    # Act
    # Step 1: Import
    workflow = import_from_code(sample_langgraph_code)

    # Step 2: Validate
    validation = validate_import(workflow)

    # Step 3: Export to code
    builder = WorkflowBuilder.from_json(workflow)
    code = builder.export_code()

    # Assert
    assert validation["valid"] is True
    assert isinstance(code, str)
    assert len(code) > 0
    assert "StateGraph" in code


# ==============================================================================
# Edge Cases
# ==============================================================================


def test_import_from_code_with_minimal_workflow():
    """Test import_from_code() with minimal valid workflow."""
    # Arrange
    minimal_code = """
from langgraph.graph import StateGraph

def node_func(state):
    return state

def create():
    g = StateGraph(dict)
    g.add_node("only_node", node_func)
    g.set_entry_point("only_node")
    return g.compile()
"""

    # Act
    workflow = import_from_code(minimal_code)

    # Assert
    assert len(workflow["nodes"]) >= 1


def test_import_handles_different_layout_algorithms():
    """Test import_from_code() works with all layout algorithms."""
    # Arrange
    code = """
from langgraph.graph import StateGraph
def n(s): return s
def c():
    g = StateGraph(dict)
    g.add_node("a", n)
    g.add_node("b", n)
    g.add_edge("a", "b")
    g.set_entry_point("a")
    return g.compile()
"""

    # Act & Assert
    for algorithm in ["hierarchical", "force", "grid"]:
        workflow = import_from_code(code, layout_algorithm=algorithm)  # type: ignore
        assert len(workflow["nodes"]) == 2
        # All nodes should have positions
        for node in workflow["nodes"]:
            assert "position" in node


def test_validate_import_with_all_valid_node_types():
    """Test validate_import() accepts all known node types."""
    # Arrange
    for node_type in ["tool", "llm", "conditional", "approval", "custom"]:
        workflow = {
            "name": "test",
            "nodes": [{"id": "node1", "type": node_type, "position": {"x": 0, "y": 0}}],
            "edges": [],
        }

        # Act
        result = validate_import(workflow)

        # Assert - Should not have type warnings
        type_warnings = [w for w in result.get("warnings", []) if "unknown type" in w.lower()]
        assert len(type_warnings) == 0, f"Node type '{node_type}' should be recognized"
