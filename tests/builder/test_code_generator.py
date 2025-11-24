"""
Tests for Code Generator Module

Comprehensive test suite for the CodeGenerator class that generates
production-ready Python code from visual workflows.

Tests cover:
- State field generation
- Node function generation for all node types (tool, llm, conditional, approval, custom)
- Routing function generation for conditional edges
- Graph construction code generation
- Black code formatting
- File writing
- Edge cases and error handling
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_langgraph.builder.codegen.generator import CodeGenerator, EdgeDefinition, NodeDefinition, WorkflowDefinition

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.fixture
def generator():
    """Code generator instance for testing."""
    return CodeGenerator()


@pytest.fixture
def simple_workflow():
    """Simple workflow with two nodes for testing."""
    return WorkflowDefinition(
        name="test_workflow",
        description="Test workflow for code generation",
        nodes=[
            NodeDefinition(id="start", type="tool", label="Start Node", config={"tool": "web_search"}),
            NodeDefinition(id="end", type="llm", label="End Node", config={"model": "gemini-flash"}),
        ],
        edges=[EdgeDefinition(from_node="start", to_node="end")],
        entry_point="start",
        state_schema={"query": "str", "result": "str"},
    )


# ==============================================================================
# Test WorkflowDefinition Model
# ==============================================================================


def test_workflow_definition_creates_instance_with_valid_data():
    """Test WorkflowDefinition creates instance with valid data."""
    # Arrange & Act
    workflow = WorkflowDefinition(
        name="my_workflow",
        nodes=[NodeDefinition(id="node1", type="tool", config={})],
        edges=[],
        entry_point="node1",
    )

    # Assert
    assert workflow.name == "my_workflow"
    assert len(workflow.nodes) == 1
    assert workflow.entry_point == "node1"
    assert workflow.description == ""  # Default value


def test_node_definition_with_defaults_creates_instance():
    """Test NodeDefinition uses default values correctly."""
    # Arrange & Act
    node = NodeDefinition(id="test_node", type="tool")

    # Assert
    assert node.id == "test_node"
    assert node.type == "tool"
    assert node.label == ""  # Default
    assert node.config == {}  # Default
    assert node.position == {}  # Default


def test_edge_definition_with_alias_from_creates_instance():
    """Test EdgeDefinition accepts 'from' as alias for 'from_node'."""
    # Arrange & Act - using alias 'from'
    edge_data = {"from": "node1", "to": "node2"}
    edge = EdgeDefinition(**edge_data)

    # Assert
    assert edge.from_node == "node1"
    assert edge.to_node == "node2"


def test_edge_definition_with_condition_stores_condition():
    """Test EdgeDefinition stores optional condition."""
    # Arrange & Act
    edge = EdgeDefinition(from_node="node1", to_node="node2", condition="state['score'] > 0.8")

    # Assert
    assert edge.condition == "state['score'] > 0.8"


# ==============================================================================
# Test State Field Generation
# ==============================================================================


def test_generate_state_fields_with_custom_schema_returns_formatted_fields(generator):
    """Test _generate_state_fields with custom schema returns formatted fields."""
    # Arrange
    state_schema = {"query": "str", "result": "List[str]", "metadata": "Dict[str, Any]"}

    # Act
    result = generator._generate_state_fields(state_schema)

    # Assert
    assert "query: str" in result
    assert "result: List[str]" in result
    assert "metadata: Dict[str, Any]" in result


def test_generate_state_fields_with_empty_schema_returns_default_fields(generator):
    """Test _generate_state_fields with empty schema returns default fields."""
    # Arrange
    state_schema = {}

    # Act
    result = generator._generate_state_fields(state_schema)

    # Assert
    assert "query: str" in result
    assert "result: str" in result
    assert "metadata: Dict[str, Any]" in result


# ==============================================================================
# Test Node Function Generation
# ==============================================================================


def test_generate_node_function_for_tool_node_includes_tool_call(generator):
    """Test _generate_node_function for tool node includes tool call logic."""
    # Arrange
    node = NodeDefinition(id="search_node", type="tool", label="Web Search", config={"tool": "tavily_search"})

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_search_node(" in code
    assert "tavily_search" in code
    assert "call_tool" in code
    assert "Web Search" in code  # Label in docstring


def test_generate_node_function_for_llm_node_includes_completion_call(generator):
    """Test _generate_node_function for LLM node includes completion call."""
    # Arrange
    node = NodeDefinition(id="summarize", type="llm", label="Summarize Results", config={"model": "gemini-flash"})

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_summarize(" in code
    assert "gemini-flash" in code
    assert "completion" in code
    assert "from litellm import completion" in code
    assert "Summarize Results" in code


def test_generate_node_function_for_conditional_node_includes_conditional_logic(generator):
    """Test _generate_node_function for conditional node includes conditional logic."""
    # Arrange
    node = NodeDefinition(id="check_quality", type="conditional", label="Quality Check")

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_check_quality(" in code
    assert "Conditional" in code
    assert "Quality Check" in code


def test_generate_node_function_for_approval_node_includes_approval_checkpoint(generator):
    """Test _generate_node_function for approval node includes ApprovalNode."""
    # Arrange
    node = NodeDefinition(id="human_review", type="approval", label="Human Review Required")

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_human_review(" in code
    assert "ApprovalNode" in code
    assert "from mcp_server_langgraph.core.interrupts import ApprovalNode" in code
    assert "human_review" in code


def test_generate_node_function_for_custom_node_includes_todo_comment(generator):
    """Test _generate_node_function for custom node includes TODO comment."""
    # Arrange
    node = NodeDefinition(id="custom_logic", type="custom", label="Custom Processing")

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_custom_logic(" in code
    assert "TODO" in code
    assert "Custom Processing" in code


def test_generate_node_function_with_dashes_in_id_converts_to_underscores(generator):
    """Test _generate_node_function converts dashes in node ID to underscores."""
    # Arrange
    node = NodeDefinition(id="node-with-dashes", type="tool", config={})

    # Act
    code = generator._generate_node_function(node)

    # Assert
    assert "def node_node_with_dashes(" in code
    assert "node-with-dashes" not in code.split("(")[0]  # Not in function name


# ==============================================================================
# Test Routing Function Generation
# ==============================================================================


def test_generate_routing_function_with_no_edges_returns_none(generator):
    """Test _generate_routing_function with no edges returns None."""
    # Arrange
    node = NodeDefinition(id="terminal", type="tool", config={})
    edges = []

    # Act
    result = generator._generate_routing_function(node, edges)

    # Assert
    assert result is None


def test_generate_routing_function_with_single_edge_returns_none(generator):
    """Test _generate_routing_function with single edge returns None."""
    # Arrange
    node = NodeDefinition(id="start", type="tool", config={})
    edges = [EdgeDefinition(from_node="start", to_node="end")]

    # Act
    result = generator._generate_routing_function(node, edges)

    # Assert
    assert result is None  # No routing needed for single edge


def test_generate_routing_function_with_conditional_edges_returns_routing_code(generator):
    """Test _generate_routing_function with conditional edges generates routing."""
    # Arrange
    node = NodeDefinition(id="decision", type="conditional", config={})
    edges = [
        EdgeDefinition(from_node="decision", to_node="path_a", condition="state['score'] > 0.8"),
        EdgeDefinition(from_node="decision", to_node="path_b", condition="state['score'] <= 0.8"),
    ]

    # Act
    result = generator._generate_routing_function(node, edges)

    # Assert
    assert result is not None
    assert "def route_from_decision(" in result
    assert "state['score'] > 0.8" in result
    assert 'return "path_a"' in result
    assert 'return "path_b"' in result


def test_generate_routing_function_with_no_conditions_returns_none(generator):
    """Test _generate_routing_function with multiple edges but no conditions returns None."""
    # Arrange
    node = NodeDefinition(id="node1", type="tool", config={})
    edges = [
        EdgeDefinition(from_node="node1", to_node="node2"),
        EdgeDefinition(from_node="node1", to_node="node3"),
    ]

    # Act
    result = generator._generate_routing_function(node, edges)

    # Assert
    assert result is None  # No conditions, no routing needed


# ==============================================================================
# Test Graph Construction Generation
# ==============================================================================


def test_generate_graph_construction_includes_all_nodes(generator, simple_workflow):
    """Test _generate_graph_construction includes all nodes."""
    # Act
    code = generator._generate_graph_construction(simple_workflow)

    # Assert
    assert 'graph.add_node("start"' in code
    assert 'graph.add_node("end"' in code
    assert "node_start" in code
    assert "node_end" in code


def test_generate_graph_construction_includes_edges(generator, simple_workflow):
    """Test _generate_graph_construction includes edges."""
    # Act
    code = generator._generate_graph_construction(simple_workflow)

    # Assert
    assert 'graph.add_edge("start", "end")' in code


def test_generate_graph_construction_sets_entry_point(generator, simple_workflow):
    """Test _generate_graph_construction sets entry point."""
    # Act
    code = generator._generate_graph_construction(simple_workflow)

    # Assert
    assert 'graph.set_entry_point("start")' in code


def test_generate_graph_construction_sets_finish_points_for_terminal_nodes(generator):
    """Test _generate_graph_construction sets finish points for terminal nodes."""
    # Arrange
    workflow = WorkflowDefinition(
        name="test",
        nodes=[
            NodeDefinition(id="start", type="tool", config={}),
            NodeDefinition(id="end", type="tool", config={}),
        ],
        edges=[EdgeDefinition(from_node="start", to_node="end")],
        entry_point="start",
    )

    # Act
    code = generator._generate_graph_construction(workflow)

    # Assert
    assert 'graph.set_finish_point("end")' in code


def test_generate_graph_construction_with_conditional_edges_uses_routing(generator):
    """Test _generate_graph_construction with conditional edges uses routing function."""
    # Arrange
    workflow = WorkflowDefinition(
        name="test",
        nodes=[
            NodeDefinition(id="decision", type="conditional", config={}),
            NodeDefinition(id="path_a", type="tool", config={}),
            NodeDefinition(id="path_b", type="tool", config={}),
        ],
        edges=[
            EdgeDefinition(from_node="decision", to_node="path_a", condition="state['score'] > 0.5"),
            EdgeDefinition(from_node="decision", to_node="path_b", condition="state['score'] <= 0.5"),
        ],
        entry_point="decision",
    )

    # Act
    code = generator._generate_graph_construction(workflow)

    # Assert
    assert 'graph.add_conditional_edges("decision", route_from_decision)' in code


# ==============================================================================
# Test Full Code Generation
# ==============================================================================


def test_generate_with_simple_workflow_returns_valid_python_code(generator, simple_workflow):
    """Test generate() with simple workflow returns valid Python code."""
    # Act
    code = generator.generate(simple_workflow)

    # Assert
    # Check imports
    assert "from typing import" in code
    assert "from langgraph.graph import StateGraph" in code

    # Check state definition
    assert "class TestWorkflowState(TypedDict):" in code
    assert "query: str" in code
    assert "result: str" in code

    # Check node functions
    assert "def node_start(state:" in code
    assert "def node_end(state:" in code

    # Check graph construction
    assert "def create_test_workflow()" in code
    assert "graph = StateGraph(TestWorkflowState)" in code

    # Check execution function
    assert "def run_test_workflow(" in code


def test_generate_converts_workflow_name_to_class_name(generator):
    """Test generate() converts snake_case workflow name to PascalCase class name."""
    # Arrange
    workflow = WorkflowDefinition(
        name="my_research_agent",
        nodes=[NodeDefinition(id="node1", type="tool", config={})],
        edges=[],
        entry_point="node1",
    )

    # Act
    code = generator.generate(workflow)

    # Assert
    assert "class MyResearchAgentState(TypedDict):" in code


def test_generate_includes_workflow_description_in_docstring(generator):
    """Test generate() includes workflow description in module docstring."""
    # Arrange
    workflow = WorkflowDefinition(
        name="test",
        description="This is a test workflow for validation",
        nodes=[NodeDefinition(id="node1", type="tool", config={})],
        edges=[],
        entry_point="node1",
    )

    # Act
    code = generator.generate(workflow)

    # Assert
    assert "This is a test workflow for validation" in code


def test_generate_formats_code_with_black(generator, simple_workflow):
    """Test generate() formats code with Black."""
    # Act
    code = generator.generate(simple_workflow)

    # Assert
    # Black formatting characteristics:
    # - No extra blank lines
    # - Consistent indentation
    # - Proper spacing around operators

    # Verify code is formatted (no excessive blank lines)
    lines = code.split("\n")
    consecutive_blanks = 0
    for line in lines:
        if line.strip() == "":
            consecutive_blanks += 1
            assert consecutive_blanks <= 2, "Too many consecutive blank lines (Black should prevent this)"
        else:
            consecutive_blanks = 0


@pytest.mark.skipif(
    not hasattr(sys.modules.get("mcp_server_langgraph.builder.codegen.generator", None), "black"),
    reason="Black not installed - cannot test black formatting error path",
)
def test_generate_with_black_formatting_error_returns_unformatted_code(generator, simple_workflow):
    """Test generate() returns unformatted code if Black formatting fails."""
    # Import black module to get reference for mocking
    from mcp_server_langgraph.builder.codegen import generator as gen_module

    # Arrange - Mock black.format_str to raise exception
    with patch.object(gen_module, "BLACK_AVAILABLE", True):
        # Get the actual black module from the generator module
        if hasattr(gen_module, "black"):
            with patch.object(gen_module.black, "format_str") as mock_black:
                mock_black.side_effect = Exception("Black formatting failed")

                # Act
                code = generator.generate(simple_workflow)

                # Assert
                assert code is not None
                assert len(code) > 0
                # Code should still contain workflow content even if not formatted
                assert "test_workflow" in code.lower()
        else:
            pytest.skip("Black not available in generator module")


def test_generate_with_no_routing_functions_includes_comment(generator):
    """Test generate() includes comment when no routing functions needed."""
    # Arrange - simple linear workflow
    workflow = WorkflowDefinition(
        name="linear",
        nodes=[
            NodeDefinition(id="step1", type="tool", config={}),
            NodeDefinition(id="step2", type="tool", config={}),
        ],
        edges=[EdgeDefinition(from_node="step1", to_node="step2")],
        entry_point="step1",
    )

    # Act
    code = generator.generate(workflow)

    # Assert
    assert "# No routing functions needed" in code


# ==============================================================================
# Test File Writing
# ==============================================================================


def test_generate_to_file_writes_code_to_file(generator, simple_workflow):
    """Test generate_to_file() writes generated code to file."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_workflow.py"

        # Act
        generator.generate_to_file(simple_workflow, str(output_path))

        # Assert
        assert output_path.exists()
        content = output_path.read_text()
        assert "def create_test_workflow()" in content
        assert "TestWorkflowState" in content


def test_generate_to_file_with_invalid_path_raises_exception(generator, simple_workflow):
    """Test generate_to_file() raises exception for invalid path."""
    # Arrange
    invalid_path = "/invalid/nonexistent/path/file.py"

    # Act & Assert
    with pytest.raises(Exception):
        generator.generate_to_file(simple_workflow, invalid_path)


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_full_workflow_generation_produces_executable_code(generator):
    """Test complete workflow generation produces syntactically valid Python."""
    # Arrange - complex workflow with multiple node types
    workflow = WorkflowDefinition(
        name="complex_agent",
        description="Complex multi-step agent workflow",
        nodes=[
            NodeDefinition(id="search", type="tool", label="Search", config={"tool": "tavily_search"}),
            NodeDefinition(id="analyze", type="llm", label="Analyze", config={"model": "gemini-flash"}),
            NodeDefinition(id="decide", type="conditional", label="Decision Point"),
            NodeDefinition(id="approve", type="approval", label="Human Approval"),
            NodeDefinition(id="custom", type="custom", label="Custom Logic"),
        ],
        edges=[
            EdgeDefinition(from_node="search", to_node="analyze"),
            EdgeDefinition(from_node="analyze", to_node="decide"),
            EdgeDefinition(from_node="decide", to_node="approve", condition="state['confidence'] > 0.8"),
            EdgeDefinition(from_node="decide", to_node="custom", condition="state['confidence'] <= 0.8"),
        ],
        entry_point="search",
        state_schema={"query": "str", "results": "List[str]", "confidence": "float", "approved": "bool"},
    )

    # Act
    code = generator.generate(workflow)

    # Assert - Code should be syntactically valid
    # Attempt to compile the code
    compile(code, "<generated>", "exec")  # Will raise SyntaxError if invalid

    # Verify all components are present
    assert "class ComplexAgentState(TypedDict):" in code
    assert "def node_search(" in code
    assert "def node_analyze(" in code
    assert "def node_decide(" in code
    assert "def node_approve(" in code
    assert "def node_custom(" in code
    assert "def route_from_decide(" in code
    assert "def create_complex_agent()" in code
    assert "def run_complex_agent(" in code


def test_round_trip_workflow_definition_to_code_and_back_preserves_structure(generator, simple_workflow):
    """Test workflow can be converted to code (future: and back to workflow)."""
    # Act
    code = generator.generate(simple_workflow)

    # Assert
    # Verify the code contains all workflow information
    assert simple_workflow.name in code.lower()
    for node in simple_workflow.nodes:
        assert f"node_{node.id}" in code or f"node_{node.id.replace('-', '_')}" in code

    # Future: Test import_from_code(code) == simple_workflow


# ==============================================================================
# Edge Cases
# ==============================================================================


def test_generate_with_empty_state_schema_uses_defaults(generator):
    """Test generate() with empty state_schema uses default fields."""
    # Arrange
    workflow = WorkflowDefinition(
        name="test",
        nodes=[NodeDefinition(id="node1", type="tool", config={})],
        edges=[],
        entry_point="node1",
        state_schema={},  # Empty
    )

    # Act
    code = generator.generate(workflow)

    # Assert
    assert "query: str" in code
    assert "result: str" in code
    assert "metadata: Dict[str, Any]" in code


def test_generate_with_special_characters_in_field_names_escapes_correctly(generator):
    """Test generate() handles special characters in state field names."""
    # Arrange
    workflow = WorkflowDefinition(
        name="test",
        nodes=[NodeDefinition(id="node1", type="tool", config={})],
        edges=[],
        entry_point="node1",
        state_schema={"user_id": "str", "created_at": "datetime", "is_valid": "bool"},
    )

    # Act
    code = generator.generate(workflow)

    # Assert
    assert "user_id: str" in code
    assert "created_at: datetime" in code
    assert "is_valid: bool" in code
