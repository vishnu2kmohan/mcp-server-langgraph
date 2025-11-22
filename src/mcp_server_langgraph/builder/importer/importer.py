"""
Main Importer Module

High-level API for importing Python code into visual builder.

Combines:
- AST parsing
- Graph extraction
- Auto-layout
- Type inference

Example:
    from mcp_server_langgraph.builder.importer import import_from_file

    # Import existing agent code
    workflow = import_from_file("src/agents/research_agent.py")

    # Use in visual builder
    # - workflow["nodes"] has positions for canvas
    # - workflow["edges"] ready for React Flow
    # - workflow["state_schema"] for configuration

    # Or import code string
    workflow = import_from_code(python_code_string)
"""

from typing import Any, Literal

from .graph_extractor import GraphExtractor
from .layout_engine import LayoutEngine


def import_from_code(code: str, layout_algorithm: Literal["hierarchical", "force", "grid"] = "hierarchical") -> dict[str, Any]:
    """
    Import workflow from Python code string.

    Args:
        code: Python source code
        layout_algorithm: Layout algorithm for positioning

    Returns:
        Complete workflow definition ready for visual builder

    Example:
        >>> workflow = import_from_code(python_code)
        >>> len(workflow["nodes"])
        5
        >>> workflow["nodes"][0]["position"]
        {'x': 250, 'y': 50}
    """
    # Extract workflow structure
    extractor = GraphExtractor()
    workflow = extractor.extract_from_code(code)

    # Auto-layout nodes
    layout_engine = LayoutEngine()
    positioned_nodes = layout_engine.layout(
        workflow["nodes"], workflow["edges"], algorithm=layout_algorithm, entry_point=workflow.get("entry_point")
    )

    # Update workflow with positioned nodes
    workflow["nodes"] = positioned_nodes

    return workflow


def import_from_file(
    file_path: str, layout_algorithm: Literal["hierarchical", "force", "grid"] = "hierarchical"
) -> dict[str, Any]:
    """
    Import workflow from Python file.

    Args:
        file_path: Path to Python file
        layout_algorithm: Layout algorithm

    Returns:
        Workflow definition

    Example:
        >>> workflow = import_from_file("src/agents/my_agent.py")
        >>> # Load into visual builder
        >>> builder.load_workflow(workflow)
    """
    with open(file_path) as f:
        code = f.read()

    return import_from_code(code, layout_algorithm)


def validate_import(workflow: dict[str, Any]) -> dict[str, Any]:
    """
    Validate imported workflow.

    Args:
        workflow: Imported workflow

    Returns:
        Validation results

    Example:
        >>> workflow = import_from_file("agent.py")
        >>> validation = validate_import(workflow)
        >>> validation["valid"]
        True
    """
    errors = []
    warnings = []

    # Check required fields
    required = ["name", "nodes", "edges"]
    for field in required:
        if field not in workflow:
            errors.append(f"Missing required field: {field}")

    # Check nodes have positions
    for node in workflow.get("nodes", []):
        if "position" not in node:
            errors.append(f"Node {node['id']} missing position")

    # Warn about empty state schema
    if not workflow.get("state_schema"):
        warnings.append("No state schema extracted - may need manual configuration")

    # Warn about unknown node types
    known_types = ["tool", "llm", "conditional", "approval", "custom"]
    for node in workflow.get("nodes", []):
        if node.get("type") not in known_types:
            warnings.append(f"Node {node['id']} has unknown type: {node.get('type')}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Sample LangGraph code
    sample_code = '''
from typing import TypedDict, List
from langgraph.graph import StateGraph


class ResearchState(TypedDict):
    """Research agent state."""
    query: str
    search_results: List[str]
    summary: str
    confidence: float


def search_web(state):
    """Search web for information."""
    return state


def filter_results(state):
    """Filter search results."""
    return state


def summarize(state):
    """Summarize findings."""
    return state


def create_research_agent():
    """Create research agent."""
    graph = StateGraph(ResearchState)

    graph.add_node("search", search_web)
    graph.add_node("filter", filter_results)
    graph.add_node("summarize", summarize)

    graph.add_edge("search", "filter")
    graph.add_edge("filter", "summarize")

    graph.set_entry_point("search")
    graph.set_finish_point("summarize")

    return graph.compile()
'''

    print("=" * 80)
    print("CODE IMPORTER - TEST RUN")
    print("=" * 80)

    # Import and layout
    workflow = import_from_code(sample_code, layout_algorithm="hierarchical")

    print(f"\nWorkflow: {workflow['name']}")
    print(f"Nodes: {len(workflow['nodes'])}")
    print(f"Edges: {len(workflow['edges'])}")

    print("\nNode Positions (Hierarchical Layout):")
    for node in workflow["nodes"]:
        print(f"  {node['id']:15} → ({node['position']['x']:6.1f}, {node['position']['y']:6.1f}) [{node['type']}]")

    # Validate
    validation = validate_import(workflow)
    print(f"\nValidation: {'✅ PASSED' if validation['valid'] else '❌ FAILED'}")
    if validation["warnings"]:
        print("Warnings:")
        for warning in validation["warnings"]:
            print(f"  ⚠️  {warning}")

    # Try different layouts
    print("\n" + "=" * 80)
    print("LAYOUT COMPARISON")
    print("=" * 80)

    for layout_alg in ["hierarchical", "force", "grid"]:
        workflow_variant = import_from_code(sample_code, layout_algorithm=layout_alg)  # type: ignore
        print(f"\n{layout_alg.upper()} layout:")
        for node in workflow_variant["nodes"][:3]:  # Show first 3
            print(f"  {node['id']:15} @ ({node['position']['x']:6.1f}, {node['position']['y']:6.1f})")

    print("\n" + "=" * 80)
