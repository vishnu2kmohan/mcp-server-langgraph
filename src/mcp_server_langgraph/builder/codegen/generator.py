"""
Code Generator for Visual Workflow Builder

Unique Feature: Export visual workflows to production-ready Python code.

This is what differentiates us from OpenAI AgentKit - they have visual builder
but NO code export! We provide:
- Full Python code generation
- Production-ready patterns
- Type-safe code with Pydantic
- Black-formatted output
- Import/export round-trip capability

Example:
    from mcp_server_langgraph.builder.codegen import CodeGenerator, WorkflowDefinition

    # Define workflow
    workflow = WorkflowDefinition(
        name="research_agent",
        nodes=[
            {"id": "search", "type": "tool", "config": {"tool": "web_search"}},
            {"id": "summarize", "type": "llm", "config": {"model": "gemini-flash"}}
        ],
        edges=[{"from": "search", "to": "summarize"}]
    )

    # Generate Python code
    generator = CodeGenerator()
    python_code = generator.generate(workflow)

    # Result: Production-ready Python code
    print(python_code)
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Optional black formatter - gracefully degrade if not available
try:
    import black

    BLACK_AVAILABLE = True
except ImportError:
    BLACK_AVAILABLE = False


class NodeDefinition(BaseModel):
    """Definition of a workflow node."""

    id: str = Field(description="Unique node ID")
    type: str = Field(description="Node type: tool, llm, conditional, approval, custom")
    label: str = Field(default="", description="Display label")
    config: dict[str, Any] = Field(default_factory=dict, description="Node configuration")
    position: dict[str, float] = Field(default_factory=dict, description="Canvas position {x, y}")


class EdgeDefinition(BaseModel):
    """Definition of a workflow edge."""

    from_node: str = Field(description="Source node ID", alias="from")
    to_node: str = Field(description="Target node ID", alias="to")
    condition: str | None = Field(default=None, description="Optional condition for edge")
    label: str = Field(default="", description="Edge label")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowDefinition(BaseModel):
    """Complete workflow definition from visual builder."""

    name: str = Field(description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    nodes: list[NodeDefinition] = Field(description="List of nodes")
    edges: list[EdgeDefinition] = Field(description="List of edges")
    entry_point: str = Field(description="Entry node ID")
    state_schema: dict[str, str] = Field(default_factory=dict, description="State field definitions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CodeGenerator:
    """
    Generate production-ready Python code from visual workflows.

    This is our unique differentiator vs OpenAI AgentKit!
    """

    # Code generation template
    AGENT_TEMPLATE = '''"""
{description}

Auto-generated from Visual Workflow Builder.
"""

from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


# ==============================================================================
# State Definition
# ==============================================================================


class {class_name}State(TypedDict):
    """State for {workflow_name} workflow."""
{state_fields}


# ==============================================================================
# Node Functions
# ==============================================================================

{node_functions}

# ==============================================================================
# Routing Functions
# ==============================================================================

{routing_functions}

# ==============================================================================
# Graph Construction
# ==============================================================================


def create_{workflow_name}() -> StateGraph:
    """
    Create {workflow_name} workflow.

    Returns:
        Compiled LangGraph application

    Example:
        >>> agent = create_{workflow_name}()
        >>> result = agent.invoke({{"query": "test"}})
    """
    # Create graph
    graph = StateGraph({class_name}State)

{graph_construction}

    return graph


# ==============================================================================
# Execution
# ==============================================================================


def run_{workflow_name}(input_data: Dict[str, Any], config: Dict[str, Any] = None):
    """
    Execute {workflow_name} workflow.

    Args:
        input_data: Input state
        config: Optional configuration

    Returns:
        Final state
    """
    graph = create_{workflow_name}()
    app = graph.compile()

    result = app.invoke(input_data, config=config or {{}})

    return result


if __name__ == "__main__":
    # Test the generated workflow
    result = run_{workflow_name}({{"query": "test input"}})
    print(result)
'''

    def __init__(self) -> None:
        """Initialize code generator."""
        self.templates: dict[str, str] = {}

    def _generate_state_fields(self, state_schema: dict[str, str]) -> str:
        """
        Generate state field definitions.

        Args:
            state_schema: Dict of {field_name: field_type}

        Returns:
            Formatted state fields
        """
        if not state_schema:
            # Default state
            return "    query: str\n    result: str\n    metadata: Dict[str, Any]"

        fields = []
        for field_name, field_type in state_schema.items():
            fields.append(f"    {field_name}: {field_type}")

        return "\n".join(fields)

    def _generate_node_function(self, node: NodeDefinition) -> str:
        """
        Generate node function code.

        Args:
            node: Node definition

        Returns:
            Python function code
        """
        function_name = f"node_{node.id.replace('-', '_')}"

        if node.type == "tool":
            # Tool node
            tool_name = node.config.get("tool", "unknown_tool")
            return f'''def {function_name}(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute {node.label or node.id} - tool: {tool_name}."""
    # TODO: Implement {tool_name} integration
    result = call_tool("{tool_name}", state)
    state["result"] = result
    return state
'''

        if node.type == "llm":
            # LLM node
            model = node.config.get("model", "gemini-flash")
            return f'''def {function_name}(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute {node.label or node.id} - LLM: {model}."""
    # TODO: Implement LLM call
    from litellm import completion

    response = completion(
        model="{model}",
        messages=[{{"role": "user", "content": state["query"]}}]
    )
    state["llm_response"] = response.choices[0].message.content
    return state
'''

        if node.type == "conditional":
            # Conditional node
            return f'''def {function_name}(state: Dict[str, Any]) -> Dict[str, Any]:
    """Conditional: {node.label or node.id}."""
    # TODO: Implement conditional logic
    return state
'''

        if node.type == "approval":
            # Approval node (human-in-the-loop)
            return f'''def {function_name}(state: Dict[str, Any]) -> Dict[str, Any]:
    """Approval checkpoint: {node.label or node.id}."""
    from mcp_server_langgraph.core.interrupts import ApprovalNode

    approval = ApprovalNode("{node.id}", description="{node.label}")
    return approval(state)
'''

        # Custom node
        return f'''def {function_name}(state: Dict[str, Any]) -> Dict[str, Any]:
    """Custom node: {node.label or node.id}."""
    # TODO: Implement custom logic for {node.id}
    return state
'''

    def _generate_routing_function(self, node: NodeDefinition, edges: list[EdgeDefinition]) -> str | None:
        """
        Generate routing function for conditional edges.

        Args:
            node: Node with conditional outgoing edges
            edges: All edges from this node

        Returns:
            Routing function code or None
        """
        outgoing_edges = [e for e in edges if e.from_node == node.id]

        if not outgoing_edges or len(outgoing_edges) <= 1:
            return None  # No routing needed for single edge

        # Check if any edges have conditions
        conditional_edges = [e for e in outgoing_edges if e.condition]

        if not conditional_edges:
            return None  # No conditions, no routing needed

        function_name = f"route_from_{node.id.replace('-', '_')}"

        # Generate routing function
        code = f'''def {function_name}(state: Dict[str, Any]) -> str:
    """Route from {node.label or node.id}."""
'''

        for edge in conditional_edges:
            condition = edge.condition or "True"
            code += f"""    if {condition}:
        return "{edge.to_node}"
"""

        # Default route (last edge without condition or first edge)
        default_edge = outgoing_edges[0]
        code += f"""    return "{default_edge.to_node}"
"""

        return code

    def _generate_graph_construction(self, workflow: WorkflowDefinition) -> str:
        """
        Generate graph construction code.

        Args:
            workflow: Workflow definition

        Returns:
            Graph construction code
        """
        lines = []

        # Add nodes
        lines.append("    # Add nodes")
        for node in workflow.nodes:
            function_name = f"node_{node.id.replace('-', '_')}"
            lines.append(f'    graph.add_node("{node.id}", {function_name})')

        # Add edges
        lines.append("\n    # Add edges")

        # Group edges by source node
        edges_by_source: dict[str, list[EdgeDefinition]] = {}
        for edge in workflow.edges:
            if edge.from_node not in edges_by_source:
                edges_by_source[edge.from_node] = []
            edges_by_source[edge.from_node].append(edge)

        # Generate edges
        for source, edges in edges_by_source.items():
            if len(edges) == 1 and not edges[0].condition:
                # Simple edge
                lines.append(f'    graph.add_edge("{source}", "{edges[0].to_node}")')
            else:
                # Conditional edges
                routing_func = f"route_from_{source.replace('-', '_')}"
                lines.append(f'    graph.add_conditional_edges("{source}", {routing_func})')

        # Set entry and exit
        lines.append("\n    # Set entry point")
        lines.append(f'    graph.set_entry_point("{workflow.entry_point}")')

        # Find terminal nodes (nodes with no outgoing edges)
        terminal_nodes = []
        all_sources = {e.from_node for e in workflow.edges}
        all_nodes = {n.id for n in workflow.nodes}
        terminal_nodes = list(all_nodes - all_sources)

        if terminal_nodes:
            lines.append("\n    # Set finish points")
            for terminal in terminal_nodes:
                lines.append(f'    graph.set_finish_point("{terminal}")')

        return "\n".join(lines)

    def _sanitize_workflow_name(self, name: str) -> str:
        """
        Sanitize workflow name to prevent code injection.

        SECURITY: Prevents code injection via malicious workflow names.
        Only allows alphanumeric characters and underscores.

        Args:
            name: Raw workflow name from user input

        Returns:
            Sanitized workflow name safe for code generation
        """
        import re

        # Remove all non-alphanumeric characters except underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "workflow_" + sanitized
        # Fallback if completely empty
        if not sanitized:
            sanitized = "workflow"
        return sanitized

    def generate(self, workflow: WorkflowDefinition) -> str:
        """
        Generate production-ready Python code from workflow.

        Args:
            workflow: Workflow definition from visual builder

        Returns:
            Formatted Python code

        Example:
            >>> workflow = WorkflowDefinition(name="my_agent", nodes=[...], edges=[...])
            >>> code = generator.generate(workflow)
            >>> print(code)
        """
        # SECURITY: Sanitize workflow name to prevent code injection
        sanitized_name = self._sanitize_workflow_name(workflow.name)

        # Generate components
        class_name = "".join(word.capitalize() for word in sanitized_name.split("_"))
        state_fields = self._generate_state_fields(workflow.state_schema)

        # Generate node functions
        node_functions = []
        for node in workflow.nodes:
            node_func = self._generate_node_function(node)
            node_functions.append(node_func)

        node_functions_code = "\n".join(node_functions)

        # Generate routing functions
        routing_functions = []
        for node in workflow.nodes:
            routing_func = self._generate_routing_function(node, workflow.edges)
            if routing_func:
                routing_functions.append(routing_func)

        routing_functions_code = "\n".join(routing_functions) if routing_functions else "# No routing functions needed"

        # Generate graph construction
        graph_construction = self._generate_graph_construction(workflow)

        # Fill template (use sanitized name)
        code = self.AGENT_TEMPLATE.format(
            description=workflow.description or f"{sanitized_name} workflow",
            class_name=class_name,
            workflow_name=sanitized_name,
            state_fields=state_fields,
            node_functions=node_functions_code,
            routing_functions=routing_functions_code,
            graph_construction=graph_construction,
        )

        # Format with black (if available)
        if BLACK_AVAILABLE:
            try:
                formatted_code = black.format_str(code, mode=black.FileMode())
                return formatted_code
            except Exception:
                # If black formatting fails, return unformatted
                return code
        else:
            # Black not available, return unformatted code
            return code

    def generate_to_file(self, workflow: WorkflowDefinition, output_path: str) -> None:
        """
        Generate code and save to file.

        Args:
            workflow: Workflow definition
            output_path: Output file path

        Example:
            >>> generator.generate_to_file(workflow, "src/agents/my_agent.py")
        """
        code = self.generate(workflow)

        with Path(output_path).open("w") as f:
            f.write(code)


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example workflow: Simple research agent
    workflow = WorkflowDefinition(
        name="research_agent",
        description="Research agent that searches and summarizes",
        nodes=[
            NodeDefinition(id="search", type="tool", label="Web Search", config={"tool": "tavily_search"}),
            NodeDefinition(id="summarize", type="llm", label="Summarize", config={"model": "gemini-2.5-flash-preview-001"}),
            NodeDefinition(id="validate", type="conditional", label="Validate Quality"),
        ],
        edges=[
            EdgeDefinition(from_node="search", to_node="summarize"),  # type: ignore
            EdgeDefinition(from_node="summarize", to_node="validate"),  # type: ignore
        ],
        entry_point="search",
        state_schema={"query": "str", "search_results": "List[str]", "summary": "str", "validated": "bool"},
    )

    # Generate code
    generator = CodeGenerator()
    code = generator.generate(workflow)

    print("=" * 80)
    print("GENERATED PYTHON CODE")
    print("=" * 80)
    print(code)
    print("=" * 80)
