"""
REST API Authorization Tuple Parity Contract Tests.

Validates that all REST API endpoints with authorization requirements
have corresponding tuples in sample-tuples.json.

This test catches the bug where:
1. REST API endpoint requires authorization (e.g., require_cost_viewer)
2. No tuple exists for that resource in sample-tuples.json
3. All users get 403 Forbidden at runtime

Similar pattern to test_websocket_endpoint_parity.py but for REST APIs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.authorization]


def get_project_root() -> Path:
    """Get the project root directory."""
    # tests/contract/test_file.py -> tests/contract -> tests -> project_root
    return Path(__file__).parent.parent.parent


def get_dependencies_path() -> Path:
    """Get the path to the auth/dependencies.py file."""
    deps_path = get_project_root() / "src" / "mcp_server_langgraph" / "auth" / "dependencies.py"
    if not deps_path.exists():
        pytest.skip(f"dependencies.py not found at {deps_path}")
    return deps_path


def get_sample_tuples_path() -> Path:
    """Get the path to the sample-tuples.json file."""
    tuples_path = get_project_root() / "config" / "openfga" / "sample-tuples.json"
    if not tuples_path.exists():
        pytest.skip(f"sample-tuples.json not found at {tuples_path}")
    return tuples_path


def load_sample_tuples() -> list[dict]:
    """Load tuples from sample-tuples.json."""
    tuples_path = get_sample_tuples_path()
    with tuples_path.open() as f:
        data = json.load(f)
    return data.get("tuples", [])


def extract_tuple_objects(tuples: list[dict]) -> set[str]:
    """Extract all unique object values from tuples (e.g., 'cost:default')."""
    objects: set[str] = set()
    for t in tuples:
        if "object" in t:
            objects.add(t["object"])
    return objects


def extract_static_authz_resources(dependencies_path: Path) -> list[tuple[str, str, str]]:
    """
    Extract static authorization resources from dependencies.py.

    These are resources like 'observability:default', 'cost:default' that
    don't have dynamic resource IDs - they use fixed identifiers.

    Returns:
        List of tuples (function_name, resource_type, resource_id).
    """
    content = dependencies_path.read_text()
    results: list[tuple[str, str, str]] = []

    # Find all static resource assignments like: resource = "type:id"
    # Pattern: resource = "type:id"
    pattern = r'def (require_\w+)\([^)]*\).*?resource\s*=\s*["\']([a-z_]+):([a-z_]+)["\']'
    matches = re.findall(pattern, content, re.DOTALL)

    for func_name, resource_type, resource_id in matches:
        results.append((func_name, resource_type, resource_id))

    return results


def extract_dynamic_authz_resources(dependencies_path: Path) -> list[tuple[str, str]]:
    """
    Extract dynamic authorization resources from dependencies.py.

    These are resources like 'project:{project_id}' where the ID comes from
    the URL path parameter.

    Returns:
        List of tuples (function_name, resource_type).
    """
    content = dependencies_path.read_text()
    results: list[tuple[str, str]] = []

    # Find _create_resource_auth_dependency calls
    # Pattern: _create_resource_auth_dependency("type", "relation", "id_param")
    pattern = r'def (require_\w+)\([^)]*\).*?_create_resource_auth_dependency\s*\(\s*["\']([a-z_]+)["\']'
    matches = re.findall(pattern, content, re.DOTALL)

    for func_name, resource_type in matches:
        results.append((func_name, resource_type))

    return results


class TestRestApiAuthorizationTupleParity:
    """
    Validate that REST API endpoints with static authorization requirements
    have corresponding tuples in sample-tuples.json.
    """

    def test_all_static_authz_resources_have_tuples(self) -> None:
        """Every static authorization resource should have at least one tuple."""
        deps_path = get_dependencies_path()
        static_resources = extract_static_authz_resources(deps_path)

        tuples = load_sample_tuples()
        tuple_objects = extract_tuple_objects(tuples)

        missing: list[tuple[str, str]] = []
        for func_name, resource_type, resource_id in static_resources:
            expected_object = f"{resource_type}:{resource_id}"

            if expected_object not in tuple_objects:
                missing.append((func_name, expected_object))

        if missing:
            missing_list = "\n  - ".join(f"{fn} requires {obj}" for fn, obj in missing)
            pytest.fail(
                f"Found {len(missing)} REST API dependencies without authorization tuples:\n"
                f"  - {missing_list}\n\n"
                f"These endpoints will return 403 Forbidden for ALL users.\n"
                f"Add the missing tuples to config/openfga/sample-tuples.json"
            )

    def test_dynamic_resource_types_in_model(self) -> None:
        """
        Dynamic resource types should have sample tuples for test fixtures.

        While dynamic resources (project:{id}, connection:{id}) are created at runtime,
        we should have at least one sample tuple per type for testing.
        """
        deps_path = get_dependencies_path()
        dynamic_resources = extract_dynamic_authz_resources(deps_path)

        tuples = load_sample_tuples()
        tuple_objects = extract_tuple_objects(tuples)

        # Extract unique resource types from tuples
        tuple_types = {obj.split(":")[0] for obj in tuple_objects if ":" in obj}

        missing_types: list[str] = []
        for func_name, resource_type in dynamic_resources:
            if resource_type not in tuple_types:
                missing_types.append(f"{func_name} -> {resource_type}")

        if missing_types:
            missing_list = "\n  - ".join(missing_types)
            pytest.fail(
                f"Found {len(missing_types)} dynamic resource types without any tuples:\n"
                f"  - {missing_list}\n\n"
                f"Add at least one sample tuple per type for testing."
            )

    def test_static_resources_have_tuples_for_all_users(self) -> None:
        """
        Static authorization resources should have tuples for test users.

        For testing, admin/alice/bob should have appropriate access levels.
        """
        tuples = load_sample_tuples()

        # Resources that all users should be able to view
        viewer_accessible = [
            "observability:default",
            "cost:default",
        ]

        # Resources that only admin/alice should access (compliance, config)
        restricted_resources = [
            "compliance:default",
            "config:default",
        ]

        # Admin-only resources
        admin_only = [
            "marketplace:default",
        ]

        required_viewers = ["user:admin", "user:alice", "user:bob"]

        # Check viewer-accessible resources
        for resource in viewer_accessible:
            users_with_access = {
                t["user"] for t in tuples if t.get("object") == resource and t.get("user", "").startswith("user:")
            }

            missing = set(required_viewers) - users_with_access
            if missing:
                pytest.fail(f"Resource '{resource}' missing tuples for: {missing}\nAll test users should have viewer access.")

        # Check restricted resources (admin + alice)
        for resource in restricted_resources:
            users_with_access = {
                t["user"] for t in tuples if t.get("object") == resource and t.get("user", "").startswith("user:")
            }

            # At minimum, admin should have access
            if "user:admin" not in users_with_access:
                pytest.fail(f"Admin must have access to restricted resource: {resource}")

        # Check admin-only resources
        for resource in admin_only:
            admin_tuples = [t for t in tuples if t.get("object") == resource and t.get("user") == "user:admin"]
            assert len(admin_tuples) >= 1, f"Admin-only resource '{resource}' missing admin tuple"

    def test_cost_endpoints_have_viewer_tuples(self) -> None:
        """Cost viewing endpoints should be accessible to all users."""
        tuples = load_sample_tuples()
        cost_tuples = [t for t in tuples if t.get("object") == "cost:default"]

        # Should have tuples for admin, alice, bob
        users = {t["user"] for t in cost_tuples if t.get("user", "").startswith("user:")}
        required = {"user:admin", "user:alice", "user:bob"}

        missing = required - users
        if missing:
            pytest.fail(f"cost:default missing tuples for: {missing}\nAll users should be able to view cost data.")

    def test_compliance_endpoints_have_viewer_tuples(self) -> None:
        """Compliance viewing should be accessible to admin and alice (compliance-officer)."""
        tuples = load_sample_tuples()
        compliance_tuples = [t for t in tuples if t.get("object") == "compliance:default"]

        users = {t["user"] for t in compliance_tuples if t.get("user", "").startswith("user:")}

        # Admin must have access
        assert "user:admin" in users, "Admin must have compliance access"

        # Alice (as compliance-officer sub-persona) should have access
        assert "user:alice" in users, "Alice (compliance-officer) should have compliance access"


class TestRestApiDynamicResources:
    """Validate dynamic resource authorization patterns."""

    def test_project_resource_has_sample_tuples(self) -> None:
        """Project resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        project_tuples = [t for t in tuples if t.get("object", "").startswith("project:")]

        assert len(project_tuples) >= 3, (
            f"Expected at least 3 project tuples (admin owner, alice editor, bob viewer), found {len(project_tuples)}"
        )

    def test_connection_resource_has_sample_tuples(self) -> None:
        """Connection resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        connection_tuples = [t for t in tuples if t.get("object", "").startswith("connection:")]

        assert len(connection_tuples) >= 1, f"Expected at least 1 connection tuple, found {len(connection_tuples)}"

    def test_workflow_resource_has_sample_tuples(self) -> None:
        """Workflow resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        workflow_tuples = [t for t in tuples if t.get("object", "").startswith("workflow:")]

        assert len(workflow_tuples) >= 3, f"Expected at least 3 workflow tuples, found {len(workflow_tuples)}"

    def test_execution_resource_has_sample_tuples(self) -> None:
        """Execution resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        execution_tuples = [t for t in tuples if t.get("object", "").startswith("execution:")]

        assert len(execution_tuples) >= 1, f"Expected at least 1 execution tuple, found {len(execution_tuples)}"

    def test_agent_resource_has_sample_tuples(self) -> None:
        """Agent resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        agent_tuples = [t for t in tuples if t.get("object", "").startswith("agent:")]

        assert len(agent_tuples) >= 1, f"Expected at least 1 agent tuple, found {len(agent_tuples)}"

    def test_skill_resource_has_sample_tuples(self) -> None:
        """Skill resources should have sample tuples for testing."""
        tuples = load_sample_tuples()
        skill_tuples = [t for t in tuples if t.get("object", "").startswith("skill:")]

        assert len(skill_tuples) >= 1, f"Expected at least 1 skill tuple, found {len(skill_tuples)}"
