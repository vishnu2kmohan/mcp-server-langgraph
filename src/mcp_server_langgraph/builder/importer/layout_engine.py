"""
Layout Engine for Auto-Arranging Workflow Nodes

Automatically positions nodes on the visual canvas using graph layout algorithms.

Algorithms:
- Hierarchical (top-down, layered)
- Force-directed (organic, balanced)
- Grid (simple, aligned)

Example:
    from mcp_server_langgraph.builder.importer import LayoutEngine

    engine = LayoutEngine()
    positioned_nodes = engine.layout(nodes, edges, algorithm="hierarchical")
"""

import math
from typing import Any, Literal


class LayoutEngine:
    """
    Auto-layout engine for workflow nodes.

    Positions nodes on canvas using graph layout algorithms.
    """

    def __init__(
        self,
        canvas_width: int = 1200,
        canvas_height: int = 800,
        node_width: int = 180,
        node_height: int = 60,
        spacing_x: int = 250,
        spacing_y: int = 150,
    ):
        """
        Initialize layout engine.

        Args:
            canvas_width: Canvas width in pixels
            canvas_height: Canvas height in pixels
            node_width: Node width
            node_height: Node height
            spacing_x: Horizontal spacing between nodes
            spacing_y: Vertical spacing between nodes
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.node_width = node_width
        self.node_height = node_height
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y

    def layout(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, str]],
        algorithm: Literal["hierarchical", "force", "grid"] = "hierarchical",
        entry_point: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Layout nodes using specified algorithm.

        Args:
            nodes: List of node definitions
            edges: List of edge definitions
            algorithm: Layout algorithm to use
            entry_point: Entry point node (for hierarchical)

        Returns:
            Nodes with updated positions

        Example:
            >>> positioned = engine.layout(nodes, edges, "hierarchical")
            >>> positioned[0]["position"]
            {'x': 250, 'y': 50}
        """
        if algorithm == "hierarchical":
            return self._hierarchical_layout(nodes, edges, entry_point)
        elif algorithm == "force":
            return self._force_directed_layout(nodes, edges)
        elif algorithm == "grid":
            return self._grid_layout(nodes)
        else:
            raise ValueError(f"Unknown layout algorithm: {algorithm}")  # noqa: EM102, TRY003

    def _hierarchical_layout(
        self, nodes: list[dict[str, Any]], edges: list[dict[str, str]], entry_point: str | None
    ) -> list[dict[str, Any]]:
        """
        Hierarchical top-down layout.

        Arranges nodes in layers based on graph depth.

        Args:
            nodes: Nodes to layout
            edges: Edges defining connections
            entry_point: Starting node

        Returns:
            Positioned nodes
        """
        # Build adjacency list
        adjacency: dict[str, list[str]] = {node["id"]: [] for node in nodes}
        for edge in edges:
            if edge["from"] in adjacency:
                adjacency[edge["from"]].append(edge["to"])

        # Calculate depth for each node (BFS from entry point)
        depths: dict[str, int] = {}
        if entry_point:
            queue = [(entry_point, 0)]
            visited = set()

            while queue:
                node_id, depth = queue.pop(0)
                if node_id in visited:
                    continue

                visited.add(node_id)
                depths[node_id] = depth

                # Add children to queue
                for child in adjacency.get(node_id, []):
                    if child not in visited:
                        queue.append((child, depth + 1))

        # Assign remaining nodes (not reachable from entry)
        max_depth = max(depths.values()) if depths else 0
        for node in nodes:
            if node["id"] not in depths:
                depths[node["id"]] = max_depth + 1

        # Group nodes by depth (layer)
        layers: dict[int, list[str]] = {}
        for node_id, depth in depths.items():
            if depth not in layers:
                layers[depth] = []
            layers[depth].append(node_id)

        # Position nodes by layer
        positioned_nodes = []
        for node in nodes:
            node_id = node["id"]
            depth = depths.get(node_id, 0)
            layer_nodes = layers[depth]
            position_in_layer = layer_nodes.index(node_id)

            # Calculate position
            y = 50 + depth * self.spacing_y
            x = self._center_nodes_in_layer(len(layer_nodes), position_in_layer)

            # Update node with position
            node["position"] = {"x": x, "y": y}
            positioned_nodes.append(node)

        return positioned_nodes

    def _center_nodes_in_layer(self, num_nodes: int, position: int) -> int:
        """
        Calculate x position to center nodes in layer.

        Args:
            num_nodes: Number of nodes in layer
            position: Position index in layer

        Returns:
            X coordinate
        """
        total_width = num_nodes * self.spacing_x
        start_x = (self.canvas_width - total_width) / 2

        return int(start_x + position * self.spacing_x)

    def _force_directed_layout(self, nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> list[dict[str, Any]]:
        """
        Force-directed layout (Fruchterman-Reingold algorithm).

        Uses physics simulation to create organic layout.

        Args:
            nodes: Nodes to layout
            edges: Edges

        Returns:
            Positioned nodes
        """
        # Initialize random positions
        import random

        for node in nodes:
            node["position"] = {
                "x": random.randint(100, self.canvas_width - 100),
                "y": random.randint(100, self.canvas_height - 100),
            }

        # Physics simulation parameters
        iterations = 50
        k = math.sqrt((self.canvas_width * self.canvas_height) / len(nodes))  # Optimal distance
        temperature = self.canvas_width / 10

        # Simulation
        for iteration in range(iterations):
            # Calculate repulsive forces (all pairs)
            forces = {node["id"]: {"x": 0.0, "y": 0.0} for node in nodes}

            for i, node1 in enumerate(nodes):
                for node2 in nodes[i + 1 :]:
                    dx = node1["position"]["x"] - node2["position"]["x"]
                    dy = node1["position"]["y"] - node2["position"]["y"]
                    distance = math.sqrt(dx * dx + dy * dy) or 1

                    # Repulsive force (nodes repel)
                    force = k * k / distance
                    fx = (dx / distance) * force
                    fy = (dy / distance) * force

                    forces[node1["id"]]["x"] += fx
                    forces[node1["id"]]["y"] += fy
                    forces[node2["id"]]["x"] -= fx
                    forces[node2["id"]]["y"] -= fy

            # Calculate attractive forces (connected pairs)
            for edge in edges:
                node1_result = next((n for n in nodes if n["id"] == edge["from"]), {})
                node2_result = next((n for n in nodes if n["id"] == edge["to"]), {})

                if not node1_result or not node2_result:
                    continue

                node1 = node1_result
                node2 = node2_result

                dx = node1["position"]["x"] - node2["position"]["x"]
                dy = node1["position"]["y"] - node2["position"]["y"]
                distance = math.sqrt(dx * dx + dy * dy) or 1

                # Attractive force (edges pull)
                force = distance * distance / k
                fx = (dx / distance) * force
                fy = (dy / distance) * force

                forces[node1["id"]]["x"] -= fx
                forces[node1["id"]]["y"] -= fy
                forces[node2["id"]]["x"] += fx
                forces[node2["id"]]["y"] += fy

            # Apply forces with temperature cooling
            temp = temperature * (1 - iteration / iterations)

            for node in nodes:
                force_vec = forces[node["id"]]
                displacement = math.sqrt(force_vec["x"] ** 2 + force_vec["y"] ** 2) or 1

                # Limit displacement by temperature
                node["position"]["x"] += (force_vec["x"] / displacement) * min(displacement, temp)
                node["position"]["y"] += (force_vec["y"] / displacement) * min(displacement, temp)

                # Keep within canvas bounds
                node["position"]["x"] = max(50, min(self.canvas_width - 50, node["position"]["x"]))
                node["position"]["y"] = max(50, min(self.canvas_height - 50, node["position"]["y"]))

        return nodes

    def _grid_layout(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Simple grid layout.

        Args:
            nodes: Nodes to layout

        Returns:
            Positioned nodes in grid
        """
        # Calculate grid dimensions
        num_nodes = len(nodes)
        cols = math.ceil(math.sqrt(num_nodes))

        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols

            node["position"] = {"x": 100 + col * self.spacing_x, "y": 100 + row * self.spacing_y}

        return nodes


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Sample nodes and edges
    nodes = [
        {"id": "search", "type": "tool", "label": "Search"},
        {"id": "filter", "type": "custom", "label": "Filter"},
        {"id": "summarize", "type": "llm", "label": "Summarize"},
        {"id": "validate", "type": "conditional", "label": "Validate"},
        {"id": "respond", "type": "custom", "label": "Respond"},
    ]

    edges = [
        {"from": "search", "to": "filter"},
        {"from": "filter", "to": "summarize"},
        {"from": "summarize", "to": "validate"},
        {"from": "validate", "to": "respond"},
    ]

    engine = LayoutEngine()

    print("=" * 80)
    print("LAYOUT ENGINE - TEST RUN")
    print("=" * 80)

    for algorithm in ["hierarchical", "force", "grid"]:
        print(f"\n{algorithm.upper()} LAYOUT:")
        positioned = engine.layout(nodes.copy(), edges, algorithm=algorithm, entry_point="search")  # type: ignore

        for node in positioned:
            print(f"  {node['id']:15} @ ({node['position']['x']:6.1f}, {node['position']['y']:6.1f})")

    print("\n" + "=" * 80)
