"""
Graph Extractor for LangGraph Code

Extracts workflow structure from LangGraph Python code:
- Identifies StateGraph creation
- Extracts nodes and their functions
- Extracts edges and conditions
- Identifies entry/finish points
- Infers state schema

Example:
    from mcp_server_langgraph.builder.importer import GraphExtractor

    extractor = GraphExtractor()
    workflow = extractor.extract_from_file("agent.py")

    print(f"Nodes: {len(workflow['nodes'])}")
    print(f"Edges: {len(workflow['edges'])}")
"""

import ast
from typing import Any, Dict, List

from .ast_parser import PythonCodeParser


class GraphExtractor:
    """
    Extract LangGraph workflow structure from Python code.

    Uses AST analysis to identify graph construction patterns.
    """

    def __init__(self) -> None:
        """Initialize extractor."""
        self.parser = PythonCodeParser()

    def extract_from_code(self, code: str) -> Dict[str, Any]:
        """
        Extract workflow from Python code string.

        Args:
            code: Python source code

        Returns:
            Workflow definition dict

        Example:
            >>> workflow = extractor.extract_from_code(python_code)
            >>> workflow["name"]
            'my_agent'
        """
        # Parse code
        tree = self.parser.parse_code(code)

        # Extract components
        workflow_name = self._extract_workflow_name(tree, code)
        state_schema = self._extract_state_schema(tree)
        nodes = self._extract_nodes(tree)
        edges = self._extract_edges(tree)
        entry_point = self._extract_entry_point(tree)

        return {
            "name": workflow_name,
            "description": self._extract_description(tree),
            "nodes": nodes,
            "edges": edges,
            "entry_point": entry_point,
            "state_schema": state_schema,
            "metadata": {"source": "imported", "parser_version": "1.0"},
        }

    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract workflow from Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Workflow definition

        Example:
            >>> workflow = extractor.extract_from_file("agent.py")
        """
        with open(file_path, "r") as f:
            code = f.read()

        return self.extract_from_code(code)

    def _extract_workflow_name(self, tree: ast.Module, code: str) -> str:
        """
        Extract workflow name from code.

        Tries multiple strategies:
        1. Function name (create_xxx_agent or create_xxx)
        2. Variable name (xxx_agent =)
        3. File name
        4. Default to "imported_workflow"

        Args:
            tree: AST tree
            code: Original source code

        Returns:
            Workflow name
        """
        # Strategy 1: Find create_xxx functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("create_"):
                    # Extract name after create_ prefix
                    name = node.name.replace("create_", "")
                    # Remove _agent or _workflow suffix if present
                    name = name.replace("_agent", "").replace("_workflow", "")
                    # Skip generic names like "create_graph"
                    if name and name not in ["graph", "agent", "workflow"]:
                        return name

        # Strategy 2: Find xxx_agent variables
        assignments = self.parser.find_variable_assignments(tree)
        for assignment in assignments:
            var_name = assignment["variable"]
            if var_name.endswith("_agent") or var_name.endswith("_workflow") or var_name == "graph":
                if var_name in ["graph", "agent", "workflow"]:
                    continue  # Too generic
                result = var_name.replace("_agent", "").replace("_workflow", "")
                return str(result)

        # Default
        return "imported_workflow"

    def _extract_description(self, tree: ast.Module) -> str:
        """
        Extract module docstring as description.

        Args:
            tree: AST tree

        Returns:
            Description string
        """
        docstring = ast.get_docstring(tree)
        return docstring or "Imported workflow"

    def _extract_state_schema(self, tree: ast.Module) -> Dict[str, str]:
        """
        Extract state schema from TypedDict or Pydantic model.

        Args:
            tree: AST tree

        Returns:
            State schema dict {field_name: type}

        Example:
            >>> schema = extractor._extract_state_schema(tree)
            >>> schema
            {'query': 'str', 'result': 'str'}
        """
        classes = self.parser.find_class_definitions(tree)

        # Look for State classes
        for cls in classes:
            if "State" in cls["name"] or "TypedDict" in cls["bases"] or "BaseModel" in cls["bases"]:
                # Found state class - extract fields
                return self._extract_class_fields(tree, cls["name"])

        return {}

    def _extract_class_fields(self, tree: ast.Module, class_name: str) -> Dict[str, str]:
        """
        Extract fields from a class definition.

        Args:
            tree: AST tree
            class_name: Name of class

        Returns:
            Fields dict
        """
        fields = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Extract annotated assignments
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        field_type = ast.unparse(item.annotation) if hasattr(ast, "unparse") else "Any"
                        fields[field_name] = field_type

        return fields

    def _extract_nodes(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract nodes from add_node() calls.

        Args:
            tree: AST tree

        Returns:
            List of node definitions

        Example:
            >>> nodes = extractor._extract_nodes(tree)
            >>> nodes[0]
            {'id': 'search', 'type': 'custom', 'label': 'search', 'config': {}}
        """
        add_node_calls = self.parser.find_function_calls(tree, "add_node")

        nodes = []
        for call in add_node_calls:
            # add_node(node_id, function) or add_node(node_id, function, **kwargs)
            if len(call["args"]) >= 1:
                node_id = call["args"][0]
                function_name = call["args"][1] if len(call["args"]) > 1 else "unknown"

                # Infer node type from function name or kwargs
                node_type = self._infer_node_type(function_name, call["kwargs"])

                nodes.append(
                    {
                        "id": node_id,
                        "type": node_type,
                        "label": node_id,
                        "config": call["kwargs"],
                        "position": {"x": 0, "y": 0},  # Will be set by layout engine
                    }
                )

        return nodes

    def _infer_node_type(self, function_name: Any, kwargs: Dict[str, Any]) -> str:
        """
        Infer node type from function name and configuration.

        Args:
            function_name: Function name or reference
            kwargs: Keyword arguments

        Returns:
            Node type (tool, llm, conditional, approval, custom)
        """
        func_str = str(function_name).lower()

        # Check for keywords in function name
        if "tool" in func_str or "call_tool" in func_str:
            return "tool"
        elif "llm" in func_str or "completion" in func_str or "chat" in func_str:
            return "llm"
        elif "condition" in func_str or "route" in func_str or "decide" in func_str:
            return "conditional"
        elif "approval" in func_str or "approve" in func_str or "review" in func_str:
            return "approval"
        else:
            return "custom"

    def _extract_edges(self, tree: ast.Module) -> List[Dict[str, str]]:
        """
        Extract edges from add_edge() and add_conditional_edges() calls.

        Args:
            tree: AST tree

        Returns:
            List of edge definitions

        Example:
            >>> edges = extractor._extract_edges(tree)
            >>> edges[0]
            {'from': 'search', 'to': 'summarize'}
        """
        edges = []

        # Extract add_edge calls
        add_edge_calls = self.parser.find_function_calls(tree, "add_edge")
        for call in add_edge_calls:
            if len(call["args"]) >= 2:
                edges.append({"from": call["args"][0], "to": call["args"][1], "condition": None})

        # Extract add_conditional_edges calls
        conditional_calls = self.parser.find_function_calls(tree, "add_conditional_edges")
        for call in conditional_calls:
            if len(call["args"]) >= 2:
                # add_conditional_edges(source, routing_function)
                source = call["args"][0]
                routing_func = call["args"][1]

                # Create edge with condition placeholder
                edges.append({"from": source, "to": "conditional", "condition": f"route_via_{routing_func}"})

        return edges

    def _extract_entry_point(self, tree: ast.Module) -> str:
        """
        Extract entry point from set_entry_point() call.

        Args:
            tree: AST tree

        Returns:
            Entry point node ID
        """
        entry_calls = self.parser.find_function_calls(tree, "set_entry_point")

        if entry_calls and entry_calls[0]["args"]:
            result = entry_calls[0]["args"][0]
            return str(result)

        return "start"  # Default


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Sample LangGraph code
    sample_code = '''
"""
Research Agent

Searches and summarizes information.
"""

from typing import TypedDict
from langgraph.graph import StateGraph


class ResearchState(TypedDict):
    """State for research agent."""
    query: str
    search_results: List[str]
    summary: str


def search_web(state: ResearchState) -> ResearchState:
    """Search the web."""
    # Implementation
    return state


def summarize_results(state: ResearchState) -> ResearchState:
    """Summarize search results."""
    # Implementation
    return state


def create_research_agent():
    """Create research agent."""
    graph = StateGraph(ResearchState)

    graph.add_node("search", search_web)
    graph.add_node("summarize", summarize_results)

    graph.add_edge("search", "summarize")

    graph.set_entry_point("search")
    graph.set_finish_point("summarize")

    return graph.compile()
'''

    # Extract workflow
    extractor = GraphExtractor()
    workflow = extractor.extract_from_code(sample_code)

    print("=" * 80)
    print("GRAPH EXTRACTOR - TEST RUN")
    print("=" * 80)

    print(f"\nWorkflow Name: {workflow['name']}")
    print(f"Description: {workflow['description']}")
    print(f"Entry Point: {workflow['entry_point']}")

    print("\nState Schema:")
    for field, type_annotation in workflow["state_schema"].items():
        print(f"  - {field}: {type_annotation}")

    print(f"\nNodes ({len(workflow['nodes'])}):")
    for node in workflow["nodes"]:
        print(f"  - {node['id']} (type: {node['type']})")

    print(f"\nEdges ({len(workflow['edges'])}):")
    for edge in workflow["edges"]:
        print(f"  - {edge['from']} → {edge['to']}")

    print("\n" + "=" * 80)
