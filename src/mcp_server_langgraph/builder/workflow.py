"""
Workflow Builder API

Programmatic API for building agent workflows.

Provides fluent interface for:
- Adding nodes and edges
- Exporting to Python code
- Importing from existing code
- Validating workflow structure

Example:
    from mcp_server_langgraph.builder import WorkflowBuilder

    # Create builder
    builder = WorkflowBuilder("customer_support")

    # Add nodes
    builder.add_node("classify", "llm", {"model": "gemini-flash"})
    builder.add_node("search_kb", "tool", {"tool": "knowledge_base"})
    builder.add_node("respond", "llm", {"model": "gemini-flash"})

    # Add edges
    builder.add_edge("classify", "search_kb")
    builder.add_edge("search_kb", "respond")

    # Export to code
    code = builder.export_code()
    builder.save_code("agent.py")
"""

from typing import Any, Dict, List, Optional

from .codegen import CodeGenerator, EdgeDefinition, NodeDefinition, WorkflowDefinition


class WorkflowBuilder:
    """
    Fluent API for building agent workflows.

    Provides convenient methods for programmatic workflow construction.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize workflow builder.

        Args:
            name: Workflow name
            description: Workflow description
        """
        self.name = name
        self.description = description
        self.nodes: List[NodeDefinition] = []
        self.edges: List[EdgeDefinition] = []
        self.entry_point: Optional[str] = None
        self.state_schema: Dict[str, str] = {}

    def add_node(
        self, node_id: str, node_type: str = "custom", config: Optional[Dict[str, Any]] = None, label: str = ""
    ) -> "WorkflowBuilder":
        """
        Add a node to the workflow.

        Args:
            node_id: Unique node identifier
            node_type: Type of node (tool, llm, conditional, approval, custom)
            config: Node configuration
            label: Display label

        Returns:
            Self for chaining

        Example:
            >>> builder.add_node("search", "tool", {"tool": "web_search"})
        """
        node = NodeDefinition(id=node_id, type=node_type, label=label or node_id, config=config or {})

        self.nodes.append(node)

        # Set first node as entry point if not set
        if self.entry_point is None:
            self.entry_point = node_id

        return self

    def add_edge(self, from_node: str, to_node: str, condition: Optional[str] = None, label: str = "") -> "WorkflowBuilder":
        """
        Add an edge between nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            condition: Optional condition expression
            label: Edge label

        Returns:
            Self for chaining

        Example:
            >>> builder.add_edge("search", "summarize")
            >>> builder.add_edge("validate", "approved", condition='state["score"] > 0.8')
        """
        edge = EdgeDefinition(from_node=from_node, to_node=to_node, condition=condition, label=label)  # type: ignore

        self.edges.append(edge)

        return self

    def set_entry_point(self, node_id: str) -> "WorkflowBuilder":
        """
        Set the entry point node.

        Args:
            node_id: Node to use as entry point

        Returns:
            Self for chaining
        """
        self.entry_point = node_id
        return self

    def add_state_field(self, field_name: str, field_type: str = "str") -> "WorkflowBuilder":
        """
        Add a field to the state schema.

        Args:
            field_name: Name of the field
            field_type: Python type annotation (default: str)

        Returns:
            Self for chaining

        Example:
            >>> builder.add_state_field("query", "str")
            >>> builder.add_state_field("results", "List[str]")
        """
        self.state_schema[field_name] = field_type
        return self

    def build(self) -> WorkflowDefinition:
        """
        Build the workflow definition.

        Returns:
            WorkflowDefinition ready for code generation

        Raises:
            ValueError: If workflow is invalid
        """
        if not self.nodes:
            raise ValueError("Workflow must have at least one node")

        if not self.entry_point:
            raise ValueError("Workflow must have an entry point")

        # Validate entry point exists
        node_ids = {n.id for n in self.nodes}
        if self.entry_point not in node_ids:
            raise ValueError(f"Entry point '{self.entry_point}' not found in nodes")

        # Validate all edges reference existing nodes
        for edge in self.edges:
            if edge.from_node not in node_ids:
                raise ValueError(f"Edge references non-existent node: {edge.from_node}")
            if edge.to_node not in node_ids:
                raise ValueError(f"Edge references non-existent node: {edge.to_node}")

        return WorkflowDefinition(
            name=self.name,
            description=self.description,
            nodes=self.nodes,
            edges=self.edges,
            entry_point=self.entry_point,
            state_schema=self.state_schema,
        )

    def export_code(self) -> str:
        """
        Export workflow to Python code.

        Returns:
            Production-ready Python code

        Example:
            >>> code = builder.export_code()
            >>> print(code)
        """
        workflow = self.build()
        generator = CodeGenerator()

        return generator.generate(workflow)

    def save_code(self, output_path: str) -> None:
        """
        Export workflow to Python file.

        Args:
            output_path: Output file path

        Example:
            >>> builder.save_code("src/agents/my_agent.py")
        """
        code = self.export_code()

        with open(output_path, "w") as f:
            f.write(code)

    def to_json(self) -> Dict[str, Any]:
        """
        Export workflow to JSON for visual builder.

        Returns:
            JSON-serializable workflow definition

        Example:
            >>> json_data = builder.to_json()
            >>> # Send to frontend visual builder
        """
        workflow = self.build()
        return workflow.model_dump()

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "WorkflowBuilder":
        """
        Create builder from JSON (from visual builder).

        Args:
            data: JSON workflow data

        Returns:
            WorkflowBuilder instance

        Example:
            >>> builder = WorkflowBuilder.from_json(visual_builder_data)
            >>> code = builder.export_code()
        """
        workflow = WorkflowDefinition(**data)

        builder = cls(workflow.name, workflow.description)
        builder.nodes = workflow.nodes
        builder.edges = workflow.edges
        builder.entry_point = workflow.entry_point
        builder.state_schema = workflow.state_schema

        return builder


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Build workflow programmatically
    builder = WorkflowBuilder("research_assistant", "Agent that researches and summarizes topics")

    # Define state
    builder.add_state_field("query", "str")
    builder.add_state_field("search_results", "List[str]")
    builder.add_state_field("summary", "str")

    # Add nodes
    builder.add_node("search", "tool", {"tool": "tavily_search"}, "Search Web")
    builder.add_node("summarize", "llm", {"model": "gemini-2.5-flash-preview-001"}, "Summarize Results")
    builder.add_node("validate", "conditional", {}, "Validate Quality")

    # Add edges
    builder.add_edge("search", "summarize")
    builder.add_edge("summarize", "validate")

    # Set entry
    builder.set_entry_point("search")

    # Export to code
    code = builder.export_code()

    print("=" * 80)
    print("WORKFLOW BUILDER - GENERATED CODE")
    print("=" * 80)
    print(code)
    print("=" * 80)

    # Also show JSON representation
    print("\nJSON REPRESENTATION:")
    import json

    print(json.dumps(builder.to_json(), indent=2))
