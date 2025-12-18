"""
Workflow Factory for Test Data Generation.

Provides factory functions for creating test workflow objects.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class WorkflowFactory:
    """Factory for creating test workflow objects."""

    @staticmethod
    def create(
        workflow_id: str | None = None,
        name: str = "Test Workflow",
        description: str = "A test workflow",
        user_id: str = "alice",
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a test workflow dictionary.

        Args:
            workflow_id: Workflow ID (auto-generated if not provided)
            name: Workflow name
            description: Workflow description
            user_id: Owner user ID
            nodes: List of workflow nodes (creates default if None)
            edges: List of workflow edges (creates default if None)
            created_at: Creation timestamp

        Returns:
            Dictionary with workflow data matching Workflow model
        """
        now = created_at or datetime.now(UTC)
        return {
            "id": workflow_id or str(uuid4()),
            "name": name,
            "description": description,
            "user_id": user_id,
            "nodes": nodes if nodes is not None else [],
            "edges": edges if edges is not None else [],
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def create_with_nodes(
        node_count: int = 3,
        name: str = "Multi-Node Workflow",
        user_id: str = "alice",
    ) -> dict[str, Any]:
        """
        Create a workflow with a specified number of connected nodes.

        Args:
            node_count: Number of nodes to create
            name: Workflow name
            user_id: Owner user ID

        Returns:
            Dictionary with workflow data including nodes and edges
        """
        nodes = []
        edges = []

        for i in range(node_count):
            node = NodeFactory.create(
                node_id=f"node-{i}",
                label=f"Node {i + 1}",
                node_type="agent" if i > 0 else "start",
                position_x=100 + (i * 200),
                position_y=100,
            )
            nodes.append(node)

            # Create edge to next node
            if i < node_count - 1:
                edge = EdgeFactory.create(
                    source=f"node-{i}",
                    target=f"node-{i + 1}",
                )
                edges.append(edge)

        return WorkflowFactory.create(
            name=name,
            user_id=user_id,
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def create_summary(
        workflow_id: str | None = None,
        name: str = "Test Workflow",
        description: str = "A test workflow",
        node_count: int = 0,
        edge_count: int = 0,
    ) -> dict[str, Any]:
        """
        Create a workflow summary dictionary.

        Args:
            workflow_id: Workflow ID
            name: Workflow name
            description: Workflow description
            node_count: Number of nodes
            edge_count: Number of edges

        Returns:
            Dictionary matching WorkflowSummary model
        """
        now = datetime.now(UTC)
        return {
            "id": workflow_id or str(uuid4()),
            "name": name,
            "description": description,
            "node_count": node_count,
            "edge_count": edge_count,
            "created_at": now,
            "updated_at": now,
        }


class NodeFactory:
    """Factory for creating test workflow node objects."""

    @staticmethod
    def create(
        node_id: str | None = None,
        label: str = "Test Node",
        node_type: str = "agent",
        position_x: float = 100.0,
        position_y: float = 100.0,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a test workflow node dictionary.

        Args:
            node_id: Node ID (auto-generated if not provided)
            label: Display label for the node
            node_type: Node type (start, agent, tool, end, conditional)
            position_x: X position in canvas
            position_y: Y position in canvas
            config: Node configuration

        Returns:
            Dictionary with node data
        """
        return {
            "id": node_id or str(uuid4()),
            "type": node_type,
            "label": label,
            "position": {"x": position_x, "y": position_y},
            "config": config or {},
        }

    @staticmethod
    def create_start() -> dict[str, Any]:
        """Create a start node."""
        return NodeFactory.create(
            node_id="start",
            label="Start",
            node_type="start",
            position_x=50,
            position_y=100,
        )

    @staticmethod
    def create_end() -> dict[str, Any]:
        """Create an end node."""
        return NodeFactory.create(
            node_id="end",
            label="End",
            node_type="end",
            position_x=500,
            position_y=100,
        )

    @staticmethod
    def create_agent(
        node_id: str = "agent",
        label: str = "Agent",
        model: str = "gpt-4o-mini",
    ) -> dict[str, Any]:
        """Create an agent node with LLM config."""
        return NodeFactory.create(
            node_id=node_id,
            label=label,
            node_type="agent",
            config={"model": model},
        )

    @staticmethod
    def create_tool(
        node_id: str = "tool",
        label: str = "Tool",
        tool_name: str = "search",
    ) -> dict[str, Any]:
        """Create a tool node."""
        return NodeFactory.create(
            node_id=node_id,
            label=label,
            node_type="tool",
            config={"tool_name": tool_name},
        )

    @staticmethod
    def create_conditional(
        node_id: str = "conditional",
        label: str = "Conditional",
        condition: str = "state.needs_tool",
    ) -> dict[str, Any]:
        """Create a conditional branching node."""
        return NodeFactory.create(
            node_id=node_id,
            label=label,
            node_type="conditional",
            config={"condition": condition},
        )


class EdgeFactory:
    """Factory for creating test workflow edge objects."""

    @staticmethod
    def create(
        source: str = "node-0",
        target: str = "node-1",
        edge_id: str | None = None,
        label: str | None = None,
        condition: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a test workflow edge dictionary.

        Args:
            source: Source node ID
            target: Target node ID
            edge_id: Edge ID (auto-generated if not provided)
            label: Optional display label
            condition: Optional condition for conditional edges

        Returns:
            Dictionary with edge data
        """
        edge = {
            "id": edge_id or f"{source}->{target}",
            "source": source,
            "target": target,
        }
        if label:
            edge["label"] = label
        if condition:
            edge["condition"] = condition
        return edge

    @staticmethod
    def create_conditional(
        source: str,
        true_target: str,
        false_target: str,
        condition: str = "state.condition",
    ) -> list[dict[str, Any]]:
        """
        Create conditional edges (true/false branches).

        Args:
            source: Source conditional node ID
            true_target: Target node for true condition
            false_target: Target node for false condition
            condition: Condition expression

        Returns:
            List of two edge dictionaries (true and false branches)
        """
        return [
            EdgeFactory.create(
                source=source,
                target=true_target,
                label="True",
                condition=f"{condition} == True",
            ),
            EdgeFactory.create(
                source=source,
                target=false_target,
                label="False",
                condition=f"{condition} == False",
            ),
        ]


# Convenience instances for common test scenarios
simple_workflow = WorkflowFactory.create(
    name="Simple Workflow",
    description="A simple test workflow",
    nodes=[
        NodeFactory.create_start(),
        NodeFactory.create_agent(),
        NodeFactory.create_end(),
    ],
    edges=[
        EdgeFactory.create(source="start", target="agent"),
        EdgeFactory.create(source="agent", target="end"),
    ],
)

agent_with_tools_workflow = WorkflowFactory.create(
    name="Agent with Tools",
    description="Agent workflow with tool calling",
    nodes=[
        NodeFactory.create_start(),
        NodeFactory.create_agent(node_id="agent", label="Main Agent"),
        NodeFactory.create_tool(node_id="search", label="Search Tool"),
        NodeFactory.create_end(),
    ],
    edges=[
        EdgeFactory.create(source="start", target="agent"),
        EdgeFactory.create(source="agent", target="search"),
        EdgeFactory.create(source="search", target="agent"),
        EdgeFactory.create(source="agent", target="end"),
    ],
)
