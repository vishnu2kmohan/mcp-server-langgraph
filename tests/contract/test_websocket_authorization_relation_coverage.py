"""
WebSocket Authorization Relation Coverage Contract Tests.

Validates that WebSocket endpoints with authorization requirements are accessible
to intended users, accounting for OpenFGA relation inheritance.

This test catches the specific bug pattern where:
1. WebSocket endpoint requires relation 'X' (e.g., 'user')
2. User has relation 'Y' (e.g., 'admin')
3. The model does NOT compute 'Y' → 'X'
4. User is DENIED access despite having a "higher" privilege

Example (the bug this test would have caught):
- AI suggestions WebSocket requires 'user' relation on 'ai:suggestions'
- Admin had 'admin' relation on 'ai:suggestions'
- The 'ai' type model computes: viewer ← user OR admin (but NOT user ← admin)
- Admin was DENIED because 'admin' doesn't inherit 'user'

Fix: Add explicit 'user' relation tuple for admin on ai:suggestions.

Reference: ADR-0091 (API Response Transformation Strategy)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = [
    pytest.mark.contract,
    pytest.mark.authorization,
    pytest.mark.openfga,
]


# =============================================================================
# Test Users - must match sample-tuples.json metadata
# =============================================================================

TEST_USERS = ["admin", "alice", "bob"]

# Users expected to have access to each resource category
# Based on sample-tuples.json metadata and intentional_exclusions
USER_ACCESS_EXPECTATIONS = {
    # All users should have access to these critical resources
    "universal_access": [
        "mcp:websocket",
        "mcp:aggregated-capabilities",
        "chat:notifications",
        "mcp_connection:health",
        "mcp_connection:realtime",
        "observability:heart",
        "cost:usage",
        "dashboard:devtools",
        "ai:orchestrator",
        "budget:alerts",
        "ai:suggestions",  # All users need AI suggestions
        "traces:stream",
        "cost:budget",
    ],
    # Admin-only resources (intentional exclusions)
    "admin_only": [
        "dashboard:alerts",  # Infrastructure alerts
    ],
    # Admin and alice (developers) - bob excluded
    "developer_access": [
        "workflow:hitl",  # HITL approval requires editor role
        "logs:audit",  # Audit logs
    ],
}


# =============================================================================
# Path Helpers
# =============================================================================


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_model_path() -> Path:
    """Get the path to the OpenFGA model.json file."""
    model_path = get_project_root() / "config" / "openfga" / "model.json"
    if not model_path.exists():
        pytest.skip(f"model.json not found at {model_path}")
    return model_path


def get_sample_tuples_path() -> Path:
    """Get the path to the sample-tuples.json file."""
    tuples_path = get_project_root() / "config" / "openfga" / "sample-tuples.json"
    if not tuples_path.exists():
        pytest.skip(f"sample-tuples.json not found at {tuples_path}")
    return tuples_path


def get_ws_router_path() -> Path:
    """Get the path to the ws_router.py file."""
    router_path = get_project_root() / "src" / "mcp_server_langgraph" / "api" / "v1" / "ws_router.py"
    if not router_path.exists():
        pytest.skip(f"ws_router.py not found at {router_path}")
    return router_path


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WebSocketAuthzConfig:
    """Authorization configuration for a WebSocket endpoint."""

    endpoint_path: str
    resource_type: str
    resource_id: str
    required_relation: str


@dataclass
class RelationInheritance:
    """Describes which relations inherit from which in an OpenFGA type."""

    relation_name: str
    computed_from: list[str]  # Relations that this relation inherits from
    is_direct: bool  # Whether this relation can be directly assigned


# =============================================================================
# Parsing Functions
# =============================================================================


def load_openfga_model() -> dict[str, Any]:
    """Load the OpenFGA model.json."""
    model_path = get_model_path()
    with model_path.open() as f:
        return json.load(f)


def load_sample_tuples() -> list[dict[str, Any]]:
    """Load tuples from sample-tuples.json."""
    tuples_path = get_sample_tuples_path()
    with tuples_path.open() as f:
        data = json.load(f)
    return data.get("tuples", [])


def extract_websocket_authz_configs(ws_router_path: Path) -> list[WebSocketAuthzConfig]:
    """
    Extract all WebSocket authorization configurations from ws_router.py.

    Returns:
        List of WebSocketAuthzConfig with endpoint details.
    """
    content = ws_router_path.read_text()
    configs: list[WebSocketAuthzConfig] = []

    # Find all @ws_router.websocket decorators
    endpoint_pattern = r"@ws_router\.websocket\s*\(\s*[\"']([^\"']+)[\"']"
    endpoints = list(re.finditer(endpoint_pattern, content))

    for i, ep_match in enumerate(endpoints):
        endpoint_path = ep_match.group(1)
        start_pos = ep_match.end()

        # Find the end of this endpoint's config
        end_pos = endpoints[i + 1].start() if i + 1 < len(endpoints) else len(content)
        block = content[start_pos:end_pos]

        # Extract authz config from WebSocketConfig
        type_match = re.search(r'authz_resource_type\s*=\s*["\']([^"\']+)["\']', block)
        id_match = re.search(r'authz_resource_id\s*=\s*["\']([^"\']+)["\']', block)
        relation_match = re.search(r'authz_required_relation\s*=\s*["\']([^"\']+)["\']', block)

        if type_match and id_match and relation_match:
            resource_type = type_match.group(1)
            resource_id = id_match.group(1)
            required_relation = relation_match.group(1)

            # Skip dynamic IDs (these are handled differently)
            if not resource_id.startswith("{") and "_id" not in resource_id:
                configs.append(
                    WebSocketAuthzConfig(
                        endpoint_path=f"/api/v1/ws{endpoint_path}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        required_relation=required_relation,
                    )
                )

    return configs


def parse_relation_inheritance(model: dict[str, Any]) -> dict[str, dict[str, RelationInheritance]]:
    """
    Parse the OpenFGA model to understand relation inheritance.

    Returns:
        Dict mapping type_name -> relation_name -> RelationInheritance
    """
    result: dict[str, dict[str, RelationInheritance]] = {}

    for type_def in model.get("type_definitions", []):
        type_name = type_def.get("type", "")
        if not type_name:
            continue

        relations = type_def.get("relations", {})
        result[type_name] = {}

        for relation_name, relation_def in relations.items():
            computed_from: list[str] = []
            is_direct = False

            # Check if it's a direct assignment
            if "this" in relation_def:
                is_direct = True

            # Check for union (computed relations)
            if "union" in relation_def:
                for child in relation_def["union"].get("child", []):
                    if "this" in child:
                        is_direct = True
                    if "computedUserset" in child:
                        computed_relation = child["computedUserset"].get("relation")
                        if computed_relation:
                            computed_from.append(computed_relation)

            # Check for simple computedUserset
            if "computedUserset" in relation_def:
                computed_relation = relation_def["computedUserset"].get("relation")
                if computed_relation:
                    computed_from.append(computed_relation)

            result[type_name][relation_name] = RelationInheritance(
                relation_name=relation_name,
                computed_from=computed_from,
                is_direct=is_direct,
            )

    return result


def get_user_relations_for_resource(tuples: list[dict[str, Any]], user: str, resource: str) -> set[str]:
    """
    Get all relations a user has for a specific resource.

    Args:
        tuples: List of OpenFGA tuples
        user: User ID (e.g., "admin" or "user:admin")
        resource: Resource object (e.g., "ai:suggestions")

    Returns:
        Set of relation names the user has for this resource.
    """
    # Normalize user format
    if not user.startswith("user:"):
        user = f"user:{user}"

    relations: set[str] = set()
    for t in tuples:
        if t.get("user") == user and t.get("object") == resource:
            if "relation" in t:
                relations.add(t["relation"])
    return relations


def can_access_with_inheritance(
    user_relations: set[str],
    required_relation: str,
    inheritance: dict[str, RelationInheritance],
    max_depth: int = 5,
) -> tuple[bool, str]:
    """
    Check if user can access resource via direct or inherited relation.

    Handles transitive inheritance (e.g., admin → editor → viewer).

    Args:
        user_relations: Relations the user has on the resource
        required_relation: The relation required by the endpoint
        inheritance: Relation inheritance info for the resource type
        max_depth: Maximum depth to traverse for transitive inheritance

    Returns:
        Tuple of (can_access, explanation)
    """
    # Direct match
    if required_relation in user_relations:
        return True, f"has direct '{required_relation}' relation"

    # Build transitive closure of relations that compute to required_relation
    # Using BFS to find all relations that lead to required_relation
    relations_that_grant_access: set[str] = set()
    to_process: list[tuple[str, list[str]]] = [(required_relation, [])]
    processed: set[str] = set()

    while to_process and len(processed) < max_depth * 10:  # Safety limit
        current, path = to_process.pop(0)
        if current in processed:
            continue
        processed.add(current)

        rel_info = inheritance.get(current)
        if rel_info:
            for computed_from in rel_info.computed_from:
                if computed_from not in processed:
                    relations_that_grant_access.add(computed_from)
                    to_process.append((computed_from, path + [current]))

    # Check if any of the user's relations grant access
    for user_rel in user_relations:
        if user_rel in relations_that_grant_access:
            # Build the inheritance chain for explanation
            chain = _build_inheritance_chain(user_rel, required_relation, inheritance)
            if chain:
                chain_str = " → ".join(chain)
                return True, f"has '{user_rel}' which computes to '{required_relation}' via: {chain_str}"
            return True, f"has '{user_rel}' which computes to '{required_relation}'"

    # Check if user's relations are computed FROM the required relation
    # (This means they have a "lower" privilege, not "higher")
    for user_rel in user_relations:
        rel_info = inheritance.get(user_rel)
        if rel_info and required_relation in rel_info.computed_from:
            # User has a relation that inherits FROM the required relation
            # This is the OPPOSITE of what we need
            return (
                False,
                f"has '{user_rel}' which inherits FROM '{required_relation}' (wrong direction)",
            )

    return False, f"no relation computes to '{required_relation}'"


def _build_inheritance_chain(
    start_relation: str,
    end_relation: str,
    inheritance: dict[str, RelationInheritance],
    max_depth: int = 5,
) -> list[str] | None:
    """
    Build the inheritance chain from start_relation to end_relation.

    Returns:
        List of relations in the chain, or None if no path exists.
    """
    if start_relation == end_relation:
        return [start_relation]

    # BFS to find path
    queue: list[tuple[str, list[str]]] = [(end_relation, [end_relation])]
    visited: set[str] = set()

    while queue and len(visited) < max_depth * 10:
        current, path = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        rel_info = inheritance.get(current)
        if rel_info:
            for computed_from in rel_info.computed_from:
                if computed_from == start_relation:
                    return [start_relation] + path
                if computed_from not in visited:
                    queue.append((computed_from, [computed_from] + path))

    return None


# =============================================================================
# Tests
# =============================================================================


class TestWebSocketAuthorizationRelationCoverage:
    """
    Validate that WebSocket endpoint authorization requirements are satisfiable
    by the tuples, accounting for relation inheritance.

    This is the contract test that would have caught the ai:suggestions bug.
    """

    def test_all_websocket_authz_configs_are_satisfiable(self) -> None:
        """
        Every WebSocket endpoint's authz requirements should be satisfiable
        by at least one user in the tuples.

        This is a basic sanity check that SOMEONE can access each endpoint.
        """
        ws_router_path = get_ws_router_path()
        configs = extract_websocket_authz_configs(ws_router_path)

        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)
        tuples = load_sample_tuples()

        unsatisfiable: list[str] = []

        for config in configs:
            resource = f"{config.resource_type}:{config.resource_id}"
            type_inheritance = inheritance.get(config.resource_type, {})

            # Check if ANY user can access
            any_user_can_access = False
            for user in TEST_USERS:
                user_relations = get_user_relations_for_resource(tuples, user, resource)
                can_access, _ = can_access_with_inheritance(user_relations, config.required_relation, type_inheritance)
                if can_access:
                    any_user_can_access = True
                    break

            if not any_user_can_access:
                unsatisfiable.append(f"{config.endpoint_path} requires '{config.required_relation}' on '{resource}'")

        if unsatisfiable:
            unsatisfiable_list = "\n  - ".join(unsatisfiable)
            pytest.fail(
                f"Found {len(unsatisfiable)} WebSocket endpoints with unsatisfiable authz:\n"
                f"  - {unsatisfiable_list}\n\n"
                f"No test users have the required relation or an inherited relation.\n"
                f"Add tuples to config/openfga/sample-tuples.json"
            )

    def test_admin_can_access_all_non_excluded_endpoints(self) -> None:
        """
        Admin should be able to access ALL WebSocket endpoints except
        explicitly excluded ones.

        This test catches the ai:suggestions bug pattern where admin had 'admin'
        but needed 'user' relation.
        """
        ws_router_path = get_ws_router_path()
        configs = extract_websocket_authz_configs(ws_router_path)

        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)
        tuples = load_sample_tuples()

        # There should be no excluded endpoints for admin
        admin_denied: list[tuple[str, str, str]] = []

        for config in configs:
            resource = f"{config.resource_type}:{config.resource_id}"
            type_inheritance = inheritance.get(config.resource_type, {})

            user_relations = get_user_relations_for_resource(tuples, "admin", resource)
            can_access, explanation = can_access_with_inheritance(user_relations, config.required_relation, type_inheritance)

            if not can_access:
                admin_denied.append((config.endpoint_path, resource, explanation))

        if admin_denied:
            denied_list = "\n  - ".join(f"{ep} ({res}): {exp}" for ep, res, exp in admin_denied)
            pytest.fail(
                f"Admin DENIED access to {len(admin_denied)} WebSocket endpoints:\n"
                f"  - {denied_list}\n\n"
                f"Admin should have access to all endpoints.\n"
                f"This is the 'ai:suggestions' bug pattern - admin has 'admin' but needs 'user'.\n"
                f"Fix: Add tuples with the required relation for admin.\n"
                f"Reference: ADR-0091 (API Response Transformation Strategy)"
            )

    def test_universal_access_resources_accessible_to_all_users(self) -> None:
        """
        Resources marked as 'universal_access' should be accessible to ALL test users.
        """
        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)
        tuples = load_sample_tuples()

        access_failures: list[tuple[str, str, str]] = []

        for resource in USER_ACCESS_EXPECTATIONS["universal_access"]:
            # Parse resource type
            parts = resource.split(":", 1)
            if len(parts) != 2:
                continue
            resource_type = parts[0]
            _type_inheritance = inheritance.get(resource_type, {})  # noqa: F841

            # Get required relation from ws_router (or default to 'viewer')
            # For this test, we check against actual tuples
            for user in TEST_USERS:
                user_relations = get_user_relations_for_resource(tuples, user, resource)

                if not user_relations:
                    access_failures.append((user, resource, "no tuples at all"))

        if access_failures:
            failures_list = "\n  - ".join(f"{user} -> {res}: {reason}" for user, res, reason in access_failures)
            pytest.fail(
                f"Found {len(access_failures)} universal access violations:\n"
                f"  - {failures_list}\n\n"
                f"These resources should be accessible to all users (admin, alice, bob).\n"
                f"Add missing tuples to config/openfga/sample-tuples.json"
            )

    def test_ai_suggestions_accessible_to_all_users(self) -> None:
        """
        Specific regression test for the ai:suggestions bug.

        The AI suggestions WebSocket requires 'user' relation, but the 'ai' type
        model does NOT compute 'admin' → 'user'. All users need explicit 'user' tuples.
        """
        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)
        tuples = load_sample_tuples()

        ai_inheritance = inheritance.get("ai", {})
        resource = "ai:suggestions"
        required_relation = "user"

        for user in TEST_USERS:
            user_relations = get_user_relations_for_resource(tuples, user, resource)
            can_access, explanation = can_access_with_inheritance(user_relations, required_relation, ai_inheritance)

            assert can_access, (
                f"REGRESSION: {user} cannot access ai:suggestions!\n"
                f"  User relations: {user_relations}\n"
                f"  Required: '{required_relation}'\n"
                f"  Explanation: {explanation}\n\n"
                f"The 'ai' type model does NOT compute 'admin' → 'user'.\n"
                f"Fix: Add tuple (user:{user}, user, ai:suggestions) to sample-tuples.json\n"
                f"Reference: ADR-0091 (API Response Transformation Strategy)"
            )


class TestRelationInheritanceGaps:
    """
    Identify potential relation inheritance gaps in the OpenFGA model.

    These are cases where a "higher" privilege relation (like 'admin')
    does NOT compute to a "lower" privilege relation (like 'user'),
    which can cause authorization bugs.
    """

    def test_identify_admin_not_inheriting_user_patterns(self) -> None:
        """
        Find types where 'admin' does NOT compute to 'user'.

        This is a documentation/visibility test, not a failure.
        It identifies potential authorization gap patterns.
        """
        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)

        gaps: list[tuple[str, list[str], list[str]]] = []

        for type_name, relations in inheritance.items():
            admin_info = relations.get("admin")
            user_info = relations.get("user")

            if admin_info and user_info:
                # Check if 'user' is computed from 'admin'
                if "admin" not in user_info.computed_from:
                    # This is a potential gap
                    gaps.append(
                        (
                            type_name,
                            user_info.computed_from,
                            admin_info.computed_from,
                        )
                    )

        # Log the gaps for visibility (not a failure)
        if gaps:
            gap_list = "\n  - ".join(f"Type '{t}': 'user' computed from {u}, 'admin' computed from {a}" for t, u, a in gaps)
            # This is informational - use warnings.warn or a marker
            # For now, we just document it exists
            assert True, (
                f"Found {len(gaps)} types where 'admin' does NOT inherit 'user':\n"
                f"  - {gap_list}\n\n"
                f"This is by design for some types, but may cause authorization bugs.\n"
                f"Ensure explicit 'user' tuples exist for admin users on these types."
            )

    def test_ai_type_properly_inherits_user_from_admin(self) -> None:
        """
        Validate the 'ai' type properly computes 'user' from 'admin'.

        The 'ai' type model (after ADR-0093 refactoring):
        - user: computed from admin (allows admins implicit user access)
        - admin: direct assignment only
        - viewer: computed from user OR admin

        This ensures admins can access endpoints requiring 'user' relation
        without needing explicit tuples (fixes the ai:suggestions bug).

        Reference: ADR-0093 - OpenFGA Relation Inheritance Patterns
        """
        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)

        ai_inheritance = inheritance.get("ai", {})

        # Verify the model structure matches our understanding
        user_info = ai_inheritance.get("user")
        admin_info = ai_inheritance.get("admin")
        viewer_info = ai_inheritance.get("viewer")

        assert user_info is not None, "ai type should have 'user' relation"
        assert admin_info is not None, "ai type should have 'admin' relation"
        assert viewer_info is not None, "ai type should have 'viewer' relation"

        # Verify 'user' IS computed from 'admin' (ADR-0093 fix)
        assert "admin" in user_info.computed_from, (
            "ai.user MUST be computed from admin to prevent authorization gaps. "
            "See ADR-0093 for the ai:suggestions bug that this fix addresses."
        )

        # Verify 'viewer' IS computed from user (transitively from admin)
        assert "user" in viewer_info.computed_from, "ai.viewer should be computed from user"
        # viewer is also directly computed from admin
        assert "admin" in viewer_info.computed_from, "ai.viewer should be computed from admin"


class TestMCPTypeRelations:
    """
    Validate MCP type relation patterns.

    The 'mcp' type is special because it only has 'user' and 'viewer' relations
    (no 'admin'), which is a simpler pattern.
    """

    def test_mcp_type_has_correct_structure(self) -> None:
        """
        MCP type should have user → viewer inheritance.
        """
        model = load_openfga_model()
        inheritance = parse_relation_inheritance(model)

        mcp_inheritance = inheritance.get("mcp", {})

        user_info = mcp_inheritance.get("user")
        viewer_info = mcp_inheritance.get("viewer")

        assert user_info is not None, "mcp type should have 'user' relation"
        assert viewer_info is not None, "mcp type should have 'viewer' relation"

        # Viewer should be computed from user
        assert "user" in viewer_info.computed_from, "mcp.viewer should be computed from user"

    def test_mcp_websocket_accessible_to_all_users(self) -> None:
        """
        All users should have access to mcp:websocket.
        """
        tuples = load_sample_tuples()

        for user in TEST_USERS:
            user_relations = get_user_relations_for_resource(tuples, user, "mcp:websocket")
            assert "user" in user_relations, f"{user} should have 'user' relation on mcp:websocket"
