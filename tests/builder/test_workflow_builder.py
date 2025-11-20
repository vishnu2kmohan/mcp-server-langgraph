"""
Tests for Workflow Builder API

Comprehensive test suite for the WorkflowBuilder fluent API that provides
a programmatic interface for building agent workflows.

Tests cover:
- Workflow initialization
- Node addition with fluent interface
- Edge addition with conditions
- State schema management
- Entry point configuration
- Workflow building and validation
- Code export functionality
- File writing
- JSON serialization/deserialization
- Method chaining
- Edge cases and error handling
"""

import json
import tempfile
from pathlib import Path

import pytest

from mcp_server_langgraph.builder.workflow import WorkflowBuilder

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit
# ==============================================================================
# Test Initialization
# ==============================================================================


def test_workflow_builder_init_with_name_creates_instance():
    """Test WorkflowBuilder initialization with name."""
    # Act
    builder = WorkflowBuilder("test_workflow")

    # Assert
    assert builder.name == "test_workflow"
    assert builder.description == ""
    assert len(builder.nodes) == 0
    assert len(builder.edges) == 0
    assert builder.entry_point is None
    assert len(builder.state_schema) == 0


def test_workflow_builder_init_with_description_stores_description():
    """Test WorkflowBuilder initialization with description."""
    # Act
    builder = WorkflowBuilder("test", "This is a test workflow")

    # Assert
    assert builder.name == "test"
    assert builder.description == "This is a test workflow"


# ==============================================================================
# Test add_node()
# ==============================================================================


def test_add_node_with_id_and_type_adds_node():
    """Test add_node() adds node to workflow."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("search", "tool", {"tool": "web_search"})

    # Assert
    assert len(builder.nodes) == 1
    assert builder.nodes[0].id == "search"
    assert builder.nodes[0].type == "tool"
    assert builder.nodes[0].config == {"tool": "web_search"}


def test_add_node_returns_self_for_chaining():
    """Test add_node() returns self for method chaining."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    result = builder.add_node("node1", "tool")

    # Assert
    assert result is builder  # Same instance for chaining


def test_add_node_with_label_stores_label():
    """Test add_node() with label stores label."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("search", "tool", {}, "Web Search")

    # Assert
    assert builder.nodes[0].label == "Web Search"


def test_add_node_without_label_uses_node_id_as_label():
    """Test add_node() without label uses node_id as label."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("search", "tool", {})

    # Assert
    assert builder.nodes[0].label == "search"


def test_add_node_sets_first_node_as_entry_point():
    """Test add_node() sets first node as entry point automatically."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("first_node", "tool")

    # Assert
    assert builder.entry_point == "first_node"


def test_add_node_second_node_does_not_change_entry_point():
    """Test add_node() does not change entry point for subsequent nodes."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("first", "tool")
    builder.add_node("second", "tool")

    # Assert
    assert builder.entry_point == "first"  # Still the first node


def test_add_node_with_no_config_uses_empty_dict():
    """Test add_node() without config uses empty dict."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("node1", "custom")

    # Assert
    assert builder.nodes[0].config == {}


def test_add_node_supports_method_chaining():
    """Test add_node() supports fluent interface chaining."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_node("node1", "tool").add_node("node2", "llm").add_node("node3", "custom")

    # Assert
    assert len(builder.nodes) == 3
    assert builder.nodes[0].id == "node1"
    assert builder.nodes[1].id == "node2"
    assert builder.nodes[2].id == "node3"


# ==============================================================================
# Test add_edge()
# ==============================================================================


def test_add_edge_with_source_and_target_adds_edge():
    """Test add_edge() adds edge to workflow."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.add_node("node2", "tool")

    # Act
    builder.add_edge("node1", "node2")

    # Assert
    assert len(builder.edges) == 1
    assert builder.edges[0].from_node == "node1"
    assert builder.edges[0].to_node == "node2"


def test_add_edge_returns_self_for_chaining():
    """Test add_edge() returns self for method chaining."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.add_node("node2", "tool")

    # Act
    result = builder.add_edge("node1", "node2")

    # Assert
    assert result is builder


def test_add_edge_with_condition_stores_condition():
    """Test add_edge() with condition stores condition expression."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("decision", "conditional")
    builder.add_node("path_a", "tool")

    # Act
    builder.add_edge("decision", "path_a", condition='state["score"] > 0.8')

    # Assert
    assert builder.edges[0].condition == 'state["score"] > 0.8'


def test_add_edge_with_label_stores_label():
    """Test add_edge() with label stores label."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.add_node("node2", "tool")

    # Act
    builder.add_edge("node1", "node2", label="Success Path")

    # Assert
    assert builder.edges[0].label == "Success Path"


def test_add_edge_supports_method_chaining():
    """Test add_edge() supports fluent interface chaining."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("n1", "tool")
    builder.add_node("n2", "tool")
    builder.add_node("n3", "tool")

    # Act
    builder.add_edge("n1", "n2").add_edge("n2", "n3")

    # Assert
    assert len(builder.edges) == 2


# ==============================================================================
# Test set_entry_point()
# ==============================================================================


def test_set_entry_point_changes_entry_point():
    """Test set_entry_point() changes the entry point."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("first", "tool")
    builder.add_node("second", "tool")

    # Act
    builder.set_entry_point("second")

    # Assert
    assert builder.entry_point == "second"


def test_set_entry_point_returns_self_for_chaining():
    """Test set_entry_point() returns self for chaining."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")

    # Act
    result = builder.set_entry_point("node1")

    # Assert
    assert result is builder


# ==============================================================================
# Test add_state_field()
# ==============================================================================


def test_add_state_field_with_name_and_type_adds_field():
    """Test add_state_field() adds field to state schema."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_state_field("query", "str")

    # Assert
    assert "query" in builder.state_schema
    assert builder.state_schema["query"] == "str"


def test_add_state_field_with_complex_type_stores_type():
    """Test add_state_field() with complex type annotation."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_state_field("results", "List[Dict[str, Any]]")

    # Assert
    assert builder.state_schema["results"] == "List[Dict[str, Any]]"


def test_add_state_field_without_type_defaults_to_str():
    """Test add_state_field() without type defaults to str."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_state_field("field_name")

    # Assert
    assert builder.state_schema["field_name"] == "str"


def test_add_state_field_returns_self_for_chaining():
    """Test add_state_field() returns self for chaining."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    result = builder.add_state_field("field1")

    # Assert
    assert result is builder


def test_add_state_field_supports_method_chaining():
    """Test add_state_field() supports fluent interface."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act
    builder.add_state_field("query", "str").add_state_field("results", "List[str]").add_state_field("count", "int")

    # Assert
    assert len(builder.state_schema) == 3


# ==============================================================================
# Test build()
# ==============================================================================


def test_build_with_valid_workflow_returns_workflow_definition():
    """Test build() with valid workflow returns WorkflowDefinition."""
    # Arrange
    builder = WorkflowBuilder("test", "Test workflow")
    builder.add_node("node1", "tool")

    # Act
    workflow = builder.build()

    # Assert
    assert workflow.name == "test"
    assert workflow.description == "Test workflow"
    assert len(workflow.nodes) == 1
    assert workflow.entry_point == "node1"


def test_build_with_no_nodes_raises_value_error():
    """Test build() with no nodes raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")

    # Act & Assert
    with pytest.raises(ValueError, match="at least one node"):
        builder.build()


def test_build_with_invalid_entry_point_raises_value_error():
    """Test build() with invalid entry point raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.set_entry_point("nonexistent")

    # Act & Assert
    with pytest.raises(ValueError, match="Entry point .* not found"):
        builder.build()


def test_build_with_edge_to_nonexistent_source_raises_value_error():
    """Test build() with edge from nonexistent node raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.add_node("node2", "tool")
    builder.add_edge("invalid_source", "node2")

    # Act & Assert
    with pytest.raises(ValueError, match="Edge references non-existent node: invalid_source"):
        builder.build()


def test_build_with_edge_to_nonexistent_target_raises_value_error():
    """Test build() with edge to nonexistent node raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    builder.add_edge("node1", "invalid_target")

    # Act & Assert
    with pytest.raises(ValueError, match="Edge references non-existent node: invalid_target"):
        builder.build()


# ==============================================================================
# Test export_code()
# ==============================================================================


def test_export_code_returns_python_code():
    """Test export_code() returns valid Python code."""
    # Arrange
    builder = WorkflowBuilder("test_agent", "Test agent")
    builder.add_node("search", "tool", {"tool": "web_search"})
    builder.add_node("summarize", "llm", {"model": "gemini-flash"})
    builder.add_edge("search", "summarize")

    # Act
    code = builder.export_code()

    # Assert
    assert isinstance(code, str)
    assert "def create_test_agent()" in code
    assert "StateGraph" in code
    assert "node_search" in code
    assert "node_summarize" in code


def test_export_code_with_invalid_workflow_raises_value_error():
    """Test export_code() with invalid workflow raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")
    # No nodes added

    # Act & Assert
    with pytest.raises(ValueError):
        builder.export_code()


# ==============================================================================
# Test save_code()
# ==============================================================================


def test_save_code_writes_code_to_file():
    """Test save_code() writes generated code to file."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_agent.py"

        # Act
        builder.save_code(str(output_path))

        # Assert
        assert output_path.exists()
        content = output_path.read_text()
        assert "def create_test()" in content


def test_save_code_with_invalid_path_raises_exception():
    """Test save_code() with invalid path raises exception."""
    # Arrange
    builder = WorkflowBuilder("test")
    builder.add_node("node1", "tool")
    invalid_path = "/invalid/nonexistent/path/file.py"

    # Act & Assert
    with pytest.raises(Exception):
        builder.save_code(invalid_path)


# ==============================================================================
# Test to_json()
# ==============================================================================


def test_to_json_returns_json_serializable_dict():
    """Test to_json() returns JSON-serializable dictionary."""
    # Arrange
    builder = WorkflowBuilder("test", "Test description")
    builder.add_node("node1", "tool", {"tool": "search"}, "Search Node")
    builder.add_node("node2", "llm", {"model": "gemini"}, "LLM Node")
    builder.add_edge("node1", "node2")
    builder.add_state_field("query", "str")

    # Act
    data = builder.to_json()

    # Assert
    assert isinstance(data, dict)
    assert data["name"] == "test"
    assert data["description"] == "Test description"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["entry_point"] == "node1"
    assert data["state_schema"] == {"query": "str"}

    # Verify it's JSON serializable
    json_str = json.dumps(data)
    assert isinstance(json_str, str)


def test_to_json_with_invalid_workflow_raises_value_error():
    """Test to_json() with invalid workflow raises ValueError."""
    # Arrange
    builder = WorkflowBuilder("test")
    # No nodes

    # Act & Assert
    with pytest.raises(ValueError):
        builder.to_json()


# ==============================================================================
# Test from_json()
# ==============================================================================


def test_from_json_creates_builder_from_json_data():
    """Test from_json() creates WorkflowBuilder from JSON data."""
    # Arrange
    json_data = {
        "name": "imported_workflow",
        "description": "Imported from JSON",
        "nodes": [
            {"id": "node1", "type": "tool", "label": "Node 1", "config": {"tool": "search"}},
            {"id": "node2", "type": "llm", "label": "Node 2", "config": {"model": "gemini"}},
        ],
        "edges": [{"from": "node1", "to": "node2"}],
        "entry_point": "node1",
        "state_schema": {"query": "str", "result": "str"},
    }

    # Act
    builder = WorkflowBuilder.from_json(json_data)

    # Assert
    assert builder.name == "imported_workflow"
    assert builder.description == "Imported from JSON"
    assert len(builder.nodes) == 2
    assert len(builder.edges) == 1
    assert builder.entry_point == "node1"
    assert builder.state_schema == {"query": "str", "result": "str"}


def test_from_json_round_trip_preserves_data():
    """Test from_json() round-trip preserves workflow data."""
    # Arrange
    original = WorkflowBuilder("test", "Test workflow")
    original.add_node("node1", "tool", {"tool": "search"}, "Search")
    original.add_node("node2", "llm", {"model": "gemini"}, "LLM")
    original.add_edge("node1", "node2", condition="state['valid']", label="Success")
    original.add_state_field("query", "str")

    # Act - Export to JSON and import back
    json_data = original.to_json()
    restored = WorkflowBuilder.from_json(json_data)

    # Assert - Restored workflow should match original
    assert restored.name == original.name
    assert restored.description == original.description
    assert len(restored.nodes) == len(original.nodes)
    assert len(restored.edges) == len(original.edges)
    assert restored.entry_point == original.entry_point
    assert restored.state_schema == original.state_schema


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_fluent_interface_chaining_builds_complete_workflow():
    """Test fluent interface allows complete workflow construction via chaining."""
    # Act - Build entire workflow using method chaining
    builder = (
        WorkflowBuilder("research_agent", "Research and summarize topics")
        .add_state_field("query", "str")
        .add_state_field("results", "List[str]")
        .add_state_field("summary", "str")
        .add_node("search", "tool", {"tool": "tavily"}, "Search Web")
        .add_node("filter", "custom", {}, "Filter Results")
        .add_node("summarize", "llm", {"model": "gemini-flash"}, "Summarize")
        .add_edge("search", "filter")
        .add_edge("filter", "summarize")
        .set_entry_point("search")
    )

    # Assert
    workflow = builder.build()
    assert workflow.name == "research_agent"
    assert len(workflow.nodes) == 3
    assert len(workflow.edges) == 2
    assert len(workflow.state_schema) == 3


def test_build_export_save_workflow_integration():
    """Test complete workflow: build -> export -> save."""
    # Arrange
    builder = WorkflowBuilder("integration_test", "Integration test workflow")
    builder.add_node("start", "tool", {"tool": "input"})
    builder.add_node("process", "llm", {"model": "gemini"})
    builder.add_node("end", "custom")
    builder.add_edge("start", "process")
    builder.add_edge("process", "end")

    # Act - Build, export, and save
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "integration_test.py"
        builder.save_code(str(output_path))

        # Assert
        assert output_path.exists()
        content = output_path.read_text()
        assert "def create_integration_test()" in content
        assert "node_start" in content
        assert "node_process" in content
        assert "node_end" in content


def test_json_export_and_code_generation_integration():
    """Test workflow can be exported to JSON and code."""
    # Arrange
    builder = WorkflowBuilder("dual_export")
    builder.add_node("node1", "tool")
    builder.add_node("node2", "llm")
    builder.add_edge("node1", "node2")

    # Act
    json_data = builder.to_json()
    code = builder.export_code()

    # Assert - Both exports should work
    assert isinstance(json_data, dict)
    assert "dual_export" in json_data["name"]
    assert isinstance(code, str)
    assert "def create_dual_export()" in code


# ==============================================================================
# Edge Cases
# ==============================================================================


def test_workflow_with_single_node_builds_successfully():
    """Test workflow with single node builds successfully."""
    # Arrange
    builder = WorkflowBuilder("single_node")
    builder.add_node("only_node", "custom")

    # Act
    workflow = builder.build()

    # Assert
    assert len(workflow.nodes) == 1
    assert workflow.entry_point == "only_node"


def test_workflow_with_multiple_edges_from_same_node():
    """Test workflow with multiple outgoing edges from one node."""
    # Arrange
    builder = WorkflowBuilder("multi_edge")
    builder.add_node("decision", "conditional")
    builder.add_node("path_a", "tool")
    builder.add_node("path_b", "tool")
    builder.add_edge("decision", "path_a", condition="state['score'] > 0.5")
    builder.add_edge("decision", "path_b", condition="state['score'] <= 0.5")

    # Act
    workflow = builder.build()

    # Assert
    assert len(workflow.edges) == 2
    decision_edges = [e for e in workflow.edges if e.from_node == "decision"]
    assert len(decision_edges) == 2


def test_workflow_with_complex_state_schema():
    """Test workflow with complex state schema types."""
    # Arrange
    builder = WorkflowBuilder("complex_state")
    builder.add_node("node1", "tool")
    builder.add_state_field("simple", "str")
    builder.add_state_field("list_field", "List[str]")
    builder.add_state_field("dict_field", "Dict[str, Any]")
    builder.add_state_field("optional", "Optional[int]")
    builder.add_state_field("nested", "List[Dict[str, List[int]]]")

    # Act
    workflow = builder.build()

    # Assert
    assert len(workflow.state_schema) == 5
    assert workflow.state_schema["nested"] == "List[Dict[str, List[int]]]"


def test_workflow_with_no_edges_builds_successfully():
    """Test workflow with no edges (single terminal node) builds."""
    # Arrange
    builder = WorkflowBuilder("no_edges")
    builder.add_node("standalone", "tool")

    # Act
    workflow = builder.build()

    # Assert
    assert len(workflow.edges) == 0
    assert len(workflow.nodes) == 1


def test_builder_can_be_reused_after_build():
    """Test builder can add more nodes/edges after build()."""
    # Arrange
    builder = WorkflowBuilder("reusable")
    builder.add_node("node1", "tool")
    first_workflow = builder.build()

    # Act - Add more to the builder
    builder.add_node("node2", "llm")
    builder.add_edge("node1", "node2")
    second_workflow = builder.build()

    # Assert
    assert len(first_workflow.nodes) == 1
    assert len(second_workflow.nodes) == 2
    assert len(second_workflow.edges) == 1
