"""
Workflow Validator Service

Centralized validation for workflow graph structure and content.
This is the single source of truth for workflow validation - NO JS DUPLICATION.

The WorkflowValidator:
- Validates workflow graph structure (acyclic, connected)
- Ensures exactly one start node exists
- Ensures at least one reachable end node
- Detects orphan nodes (not connected to the graph)
- Validates edge targets exist
- Provides warnings for unknown node types (non-blocking)

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- Review consensus: Centralized validation endpoint (no JS duplication)
- ADR-0089: Prompt Architecture Centralization
"""

from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Models
# =============================================================================


class ValidationError(BaseModel):
    """A single validation error."""

    code: str = Field(description="Error code (e.g., 'MISSING_START_NODE')")
    message: str = Field(description="Human-readable error message")
    node_id: str | None = Field(default=None, description="Node ID if applicable")


class ValidationWarning(BaseModel):
    """A single validation warning (non-blocking issue)."""

    code: str = Field(description="Warning code (e.g., 'UNKNOWN_NODE_TYPE')")
    message: str = Field(description="Human-readable warning message")
    node_id: str | None = Field(default=None, description="Node ID if applicable")


class ValidationResult(BaseModel):
    """Result of workflow validation."""

    valid: bool = Field(description="Whether the workflow passed validation")
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages (blocking issues)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages (non-blocking issues)",
    )
    error_details: list[ValidationError] = Field(
        default_factory=list,
        description="Detailed error objects with codes",
    )
    warning_details: list[ValidationWarning] = Field(
        default_factory=list,
        description="Detailed warning objects with codes",
    )


# =============================================================================
# Known Node Types
# =============================================================================

KNOWN_NODE_TYPES = frozenset(
    {
        "start",
        "end",
        "llm",
        "tool",
        "router",
        "condition",
        "memory",
        "approval",
        "human",
        "parallel",
        "merge",
    }
)


# =============================================================================
# WorkflowValidator Service
# =============================================================================


class WorkflowValidator:
    """
    Centralized workflow validation service.

    This is the single source of truth for workflow validation.
    Both the API (/validate) and the generator should use this.

    Usage:
        validator = WorkflowValidator()
        result = await validator.validate(workflow_dict)
        if not result.valid:
            print(result.errors)
    """

    async def validate(self, workflow: dict[str, Any]) -> ValidationResult:
        """
        Validate a workflow graph structure and content.

        Args:
            workflow: Workflow dict with 'nodes' and 'edges' lists.

        Returns:
            ValidationResult with valid flag, errors, and warnings.
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationWarning] = []

        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        # Build node lookup
        node_map = {n.get("id"): n for n in nodes if n.get("id")}

        # 1. Check for empty workflow
        if not nodes:
            errors.append(
                ValidationError(
                    code="EMPTY_WORKFLOW",
                    message="Workflow has no nodes",
                )
            )
            return self._build_result(errors, warnings)

        # 2. Validate start node (exactly one)
        start_errors = self._validate_start_node(nodes)
        errors.extend(start_errors)

        # 3. Validate end node (at least one)
        end_errors = self._validate_end_node(nodes)
        errors.extend(end_errors)

        # 4. Validate edge integrity
        edge_errors = self._validate_edges(edges, node_map)
        errors.extend(edge_errors)

        # 5. Validate acyclic (no cycles)
        cycle_errors = self._validate_acyclic(nodes, edges, node_map)
        errors.extend(cycle_errors)

        # 6. Validate no orphan nodes
        orphan_errors = self._validate_no_orphans(nodes, edges)
        errors.extend(orphan_errors)

        # 7. Validate end is reachable from start
        if not start_errors and not end_errors:
            reachable_errors = self._validate_end_reachable(nodes, edges, node_map)
            errors.extend(reachable_errors)

        # 8. Check for unknown node types (warning, not error)
        type_warnings = self._check_unknown_types(nodes)
        warnings.extend(type_warnings)

        return self._build_result(errors, warnings)

    def _build_result(
        self,
        errors: list[ValidationError],
        warnings: list[ValidationWarning],
    ) -> ValidationResult:
        """Build ValidationResult from error and warning lists."""
        return ValidationResult(
            valid=len(errors) == 0,
            errors=[e.message for e in errors],
            warnings=[w.message for w in warnings],
            error_details=errors,
            warning_details=warnings,
        )

    def _validate_start_node(self, nodes: list[dict[str, Any]]) -> list[ValidationError]:
        """Validate exactly one start node exists."""
        errors = []
        start_nodes = [n for n in nodes if n.get("type") == "start"]

        if len(start_nodes) == 0:
            errors.append(
                ValidationError(
                    code="MISSING_START_NODE",
                    message="Workflow must have exactly one start node",
                )
            )
        elif len(start_nodes) > 1:
            errors.append(
                ValidationError(
                    code="MULTIPLE_START_NODES",
                    message=f"Workflow has {len(start_nodes)} start nodes, but must have exactly one",
                )
            )

        return errors

    def _validate_end_node(self, nodes: list[dict[str, Any]]) -> list[ValidationError]:
        """Validate at least one end node exists."""
        errors = []
        end_nodes = [n for n in nodes if n.get("type") == "end"]

        if len(end_nodes) == 0:
            errors.append(
                ValidationError(
                    code="MISSING_END_NODE",
                    message="Workflow must have at least one end node",
                )
            )

        return errors

    def _validate_edges(
        self,
        edges: list[dict[str, Any]],
        node_map: dict[str, dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate all edges reference existing nodes."""
        errors = []

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")

            if source and source not in node_map:
                errors.append(
                    ValidationError(
                        code="INVALID_EDGE_SOURCE",
                        message=f"Edge source '{source}' does not exist in nodes",
                        node_id=source,
                    )
                )

            if target and target not in node_map:
                errors.append(
                    ValidationError(
                        code="INVALID_EDGE_TARGET",
                        message=f"Edge target '{target}' does not exist in nodes",
                        node_id=target,
                    )
                )

        return errors

    def _validate_acyclic(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        node_map: dict[str, dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate the graph has no cycles using DFS."""
        errors = []

        # Build adjacency list
        adj: dict[str, list[str]] = {n.get("id", ""): [] for n in nodes if n.get("id")}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in adj and target:
                adj[source].append(target)

        # Check for self-loops first
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source == target:
                errors.append(
                    ValidationError(
                        code="SELF_LOOP",
                        message=f"Node '{source}' has a self-loop edge",
                        node_id=source,
                    )
                )
                return errors  # Self-loop is a cycle, no need to continue

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(adj, WHITE)

        def dfs(node: str) -> bool:
            """Returns True if cycle found."""
            if node not in color:
                return False
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True  # Back edge = cycle
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for node_id in adj:
            if color.get(node_id) == WHITE:
                if dfs(node_id):
                    errors.append(
                        ValidationError(
                            code="CYCLE_DETECTED",
                            message="Workflow contains a cycle - graphs must be acyclic",
                        )
                    )
                    break  # One cycle error is enough

        return errors

    def _validate_no_orphans(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate all non-start/end nodes are connected to something."""
        errors = []

        # Get all nodes that participate in edges
        connected_nodes: set[str] = set()
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source:
                connected_nodes.add(source)
            if target:
                connected_nodes.add(target)

        # Check each node (except start/end can be terminal)
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type")

            if not node_id:
                continue

            # Start nodes only need outgoing edges
            # End nodes only need incoming edges
            # Other nodes need both
            if node_id not in connected_nodes:
                if node_type == "start":
                    # Start node with no outgoing edges
                    errors.append(
                        ValidationError(
                            code="ORPHAN_START_NODE",
                            message=f"Start node '{node_id}' has no outgoing edges",
                            node_id=node_id,
                        )
                    )
                elif node_type == "end":
                    # End node with no incoming edges
                    errors.append(
                        ValidationError(
                            code="ORPHAN_END_NODE",
                            message=f"End node '{node_id}' has no incoming edges",
                            node_id=node_id,
                        )
                    )
                else:
                    # Regular node not connected
                    errors.append(
                        ValidationError(
                            code="ORPHAN_NODE",
                            message=f"Node '{node_id}' is not connected to any edges",
                            node_id=node_id,
                        )
                    )

        return errors

    def _validate_end_reachable(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        node_map: dict[str, dict[str, Any]],
    ) -> list[ValidationError]:
        """Validate that at least one end node is reachable from start."""
        errors: list[ValidationError] = []

        # Find start node
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        if not start_nodes:
            return errors  # Already handled by _validate_start_node

        start_id = start_nodes[0].get("id")
        if not start_id:
            return errors

        # Build adjacency list
        adj: dict[str, list[str]] = {n.get("id", ""): [] for n in nodes if n.get("id")}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in adj and target:
                adj[source].append(target)

        # BFS from start
        visited: set[str] = set()
        queue: deque[str] = deque([start_id])

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        # Check if any end node is reachable
        end_nodes = [n for n in nodes if n.get("type") == "end"]
        reachable_ends = [n for n in end_nodes if n.get("id") in visited]

        if not reachable_ends:
            errors.append(
                ValidationError(
                    code="END_NOT_REACHABLE",
                    message="No end node is reachable from the start node",
                )
            )

        return errors

    def _check_unknown_types(
        self,
        nodes: list[dict[str, Any]],
    ) -> list[ValidationWarning]:
        """Check for unknown node types (warning, not error)."""
        warnings = []

        for node in nodes:
            node_type = node.get("type")
            node_id = node.get("id")

            if node_type and node_type not in KNOWN_NODE_TYPES:
                warnings.append(
                    ValidationWarning(
                        code="UNKNOWN_NODE_TYPE",
                        message=f"Node '{node_id}' has unknown type '{node_type}'",
                        node_id=node_id,
                    )
                )

        return warnings
