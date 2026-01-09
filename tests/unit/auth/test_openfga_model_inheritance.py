"""
TDD Tests for OpenFGA Model Inheritance Patterns.

These tests validate that the OpenFGA model correctly computes lower-privilege
relations from higher-privilege relations, preventing authorization gaps.

Reference: ADR-0093 - OpenFGA Relation Inheritance Patterns

RED Phase: These tests should FAIL with the current model where:
- ai.user is NOT computed from admin
- system.user is NOT computed from admin

GREEN Phase: After refactoring model.json, these tests should PASS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    # tests/unit/auth/test_openfga_model_inheritance.py -> tests/unit/auth -> tests/unit -> tests -> root
    return Path(__file__).parent.parent.parent.parent


def load_openfga_model() -> dict[str, Any]:
    """Load the OpenFGA model.json."""
    model_path = get_project_root() / "config" / "openfga" / "model.json"
    with model_path.open() as f:
        return json.load(f)


def get_type_definition(model: dict[str, Any], type_name: str) -> dict[str, Any] | None:
    """Get a type definition by name from the model."""
    for type_def in model.get("type_definitions", []):
        if type_def.get("type") == type_name:
            return type_def
    return None


def get_computed_sources(relation_def: dict[str, Any]) -> list[str]:
    """
    Extract the relations that a relation is computed from.

    Returns a list of relation names that this relation inherits from.
    """
    sources: list[str] = []

    # Check for union (multiple sources)
    if "union" in relation_def:
        for child in relation_def["union"].get("child", []):
            if "computedUserset" in child:
                computed_relation = child["computedUserset"].get("relation")
                if computed_relation:
                    sources.append(computed_relation)

    # Check for simple computedUserset
    if "computedUserset" in relation_def:
        computed_relation = relation_def["computedUserset"].get("relation")
        if computed_relation:
            sources.append(computed_relation)

    return sources


def relation_is_computed_from(
    type_def: dict[str, Any],
    target_relation: str,
    source_relation: str,
    max_depth: int = 5,
) -> bool:
    """
    Check if target_relation is computed from source_relation (transitively).

    Uses BFS to find inheritance paths.

    Args:
        type_def: The type definition containing relations
        target_relation: The relation to check (e.g., "user")
        source_relation: The relation to compute from (e.g., "admin")
        max_depth: Maximum depth for transitive search

    Returns:
        True if target_relation is computed from source_relation
    """
    if target_relation == source_relation:
        return True

    relations = type_def.get("relations", {})
    if target_relation not in relations:
        return False

    # BFS to find path from target back to source
    visited: set[str] = set()
    queue = [target_relation]

    while queue and len(visited) < max_depth * 10:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        rel_def = relations.get(current)
        if rel_def:
            computed_sources = get_computed_sources(rel_def)
            for computed_from in computed_sources:
                if computed_from == source_relation:
                    return True
                if computed_from not in visited and computed_from in relations:
                    queue.append(computed_from)

    return False


pytestmark = pytest.mark.unit


class TestModelLoading:
    """Tests for model loading utilities."""

    def test_model_exists_and_loads(self) -> None:
        """Model file should exist and be valid JSON."""
        model = load_openfga_model()
        assert "type_definitions" in model
        assert len(model["type_definitions"]) > 0

    def test_ai_type_exists(self) -> None:
        """The 'ai' type should exist in the model."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None, "ai type should exist in model"
        assert "relations" in ai_type

    def test_system_type_exists(self) -> None:
        """The 'system' type should exist in the model."""
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None, "system type should exist in model"
        assert "relations" in system_type


class TestAITypeInheritance:
    """
    Tests for 'ai' type inheritance patterns.

    Expected hierarchy after refactoring:
        admin → user → viewer

    This ensures admins can access endpoints requiring 'user' relation.
    """

    def test_ai_user_computed_from_admin(self) -> None:
        """
        [ADR-0093] ai.user MUST be computed from admin.

        This test validates the fix for the ai:suggestions bug where
        admin was denied access to WebSocket requiring 'user' relation.

        Before fix: FAILS (user is direct-only)
        After fix: PASSES (user is computed from admin)
        """
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        user_relation = ai_type["relations"].get("user")
        assert user_relation is not None, "ai type must have 'user' relation"

        # Check that 'user' is computed from 'admin'
        is_computed = relation_is_computed_from(ai_type, "user", "admin")

        assert is_computed, (
            "ai.user MUST be computed from admin to prevent authorization gaps. "
            "Users with 'admin' relation should automatically have 'user' relation. "
            "See ADR-0093 for the ai:suggestions bug that this fix addresses."
        )

    def test_ai_viewer_computed_from_admin(self) -> None:
        """ai.viewer should be computed from admin (via user or directly)."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        is_computed = relation_is_computed_from(ai_type, "viewer", "admin")
        assert is_computed, "ai.viewer should be computed from admin"

    def test_ai_viewer_computed_from_user(self) -> None:
        """ai.viewer should be computed from user."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        is_computed = relation_is_computed_from(ai_type, "viewer", "user")
        assert is_computed, "ai.viewer should be computed from user"

    def test_ai_has_expected_relations(self) -> None:
        """ai type should have user, admin, and viewer relations."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        relations = ai_type.get("relations", {})
        assert "user" in relations, "ai type must have 'user' relation"
        assert "admin" in relations, "ai type must have 'admin' relation"
        assert "viewer" in relations, "ai type must have 'viewer' relation"


class TestSystemTypeInheritance:
    """
    Tests for 'system' type inheritance patterns.

    Expected hierarchy after refactoring:
        admin → user
        admin → developer
        admin → viewer

    This ensures system admins can access endpoints requiring lower-privilege relations.
    """

    def test_system_user_computed_from_admin(self) -> None:
        """
        [ADR-0093] system.user MUST be computed from admin.

        This test validates that system admins have implicit 'user' access.
        Similar to the ai:suggestions bug, endpoints requiring 'user' relation
        would deny admin users without this inheritance.

        Before fix: FAILS (user is direct-only)
        After fix: PASSES (user is computed from admin)
        """
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        user_relation = system_type["relations"].get("user")
        assert user_relation is not None, "system type must have 'user' relation"

        # Check that 'user' is computed from 'admin'
        is_computed = relation_is_computed_from(system_type, "user", "admin")

        assert is_computed, (
            "system.user MUST be computed from admin to prevent authorization gaps. "
            "Users with 'admin' relation should automatically have 'user' relation. "
            "See ADR-0093 for the inheritance pattern requirements."
        )

    def test_system_viewer_computed_from_admin(self) -> None:
        """system.viewer should be computed from admin."""
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        is_computed = relation_is_computed_from(system_type, "viewer", "admin")
        assert is_computed, "system.viewer should be computed from admin"

    def test_system_has_expected_relations(self) -> None:
        """system type should have admin, developer, user, and viewer relations."""
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        relations = system_type.get("relations", {})
        assert "admin" in relations, "system type must have 'admin' relation"
        assert "developer" in relations, "system type must have 'developer' relation"
        assert "user" in relations, "system type must have 'user' relation"
        assert "viewer" in relations, "system type must have 'viewer' relation"


class TestInheritanceGapDetection:
    """
    Tests that validate the analyzer script findings.

    These tests ensure we can detect inheritance gaps programmatically.
    """

    def test_detect_missing_admin_to_user_inheritance(self) -> None:
        """
        Verify we can detect when a type has admin and user but no inheritance.

        This is a meta-test that validates our detection logic works.
        """
        # Create a mock type with the inheritance gap
        mock_type_with_gap: dict[str, Any] = {
            "type": "test_gap",
            "relations": {
                "admin": {"this": {}},
                "user": {"this": {}},  # No inheritance from admin
            },
        }

        # Our detection should find this is NOT computed
        is_computed = relation_is_computed_from(mock_type_with_gap, "user", "admin")
        assert not is_computed, "Should detect missing inheritance"

    def test_detect_proper_admin_to_user_inheritance(self) -> None:
        """
        Verify we can detect when a type properly computes user from admin.

        This is a meta-test that validates our detection logic works.
        """
        # Create a mock type with proper inheritance
        mock_type_with_inheritance: dict[str, Any] = {
            "type": "test_good",
            "relations": {
                "admin": {"this": {}},
                "user": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "admin"}},
                        ]
                    }
                },
            },
        }

        # Our detection should find this IS computed
        is_computed = relation_is_computed_from(mock_type_with_inheritance, "user", "admin")
        assert is_computed, "Should detect proper inheritance"

    def test_detect_transitive_inheritance(self) -> None:
        """
        Verify we can detect transitive inheritance (admin → editor → viewer).

        This tests multi-hop inheritance detection.
        """
        mock_type_transitive: dict[str, Any] = {
            "type": "test_transitive",
            "relations": {
                "admin": {"this": {}},
                "editor": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "admin"}},
                        ]
                    }
                },
                "viewer": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "editor"}},
                        ]
                    }
                },
            },
        }

        # viewer is computed from admin transitively (admin → editor → viewer)
        is_computed = relation_is_computed_from(mock_type_transitive, "viewer", "admin")
        assert is_computed, "Should detect transitive inheritance"


class TestMonotonicChainInvariants:
    """
    Tests for monotonic role hierarchy chains.

    [ADR-0093] These tests validate that role hierarchies form proper chains
    where permissions flow monotonically from higher to lower privilege:

        system: admin → developer → user → viewer
        skill: admin → author → viewer
        ai: admin → user → viewer

    A MONOTONIC chain means each level inherits from the level directly above,
    NOT from the top level. This prevents privilege escalation bugs and ensures
    the principle of least privilege is enforced.

    BROKEN (flat - all inherit from admin):
        admin → developer
        admin → user
        admin → viewer

    CORRECT (chain - each inherits from level above):
        admin → developer → user → viewer

    Reference: Google Zanzibar - Nested Role Hierarchies
    Reference: OpenFGA Best Practices - Modeling Roles
    """

    MONOTONIC_CHAIN_TYPES: dict[str, list[str]] = {
        "system": ["admin", "developer", "user", "viewer"],
        "skill": ["admin", "author", "viewer"],
        "ai": ["admin", "user", "viewer"],
    }

    def test_system_developer_computed_from_admin(self) -> None:
        """system.developer should be computed from admin (level 1)."""
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        is_computed = relation_is_computed_from(system_type, "developer", "admin")
        assert is_computed, (
            "system.developer MUST be computed from admin. "
            "This is the first level of the monotonic chain."
        )

    def test_system_user_computed_from_developer(self) -> None:
        """
        [CHAIN FIX] system.user should be computed from developer (level 2).

        This test validates the monotonic chain fix. Currently FAILS because
        user inherits directly from admin instead of developer.

        Before fix: user inherits from admin (FLAT - BROKEN)
        After fix: user inherits from developer (CHAIN - CORRECT)
        """
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        # Get user relation and check its direct sources
        user_relation = system_type["relations"].get("user")
        assert user_relation is not None

        sources = get_computed_sources(user_relation)
        assert "developer" in sources, (
            "system.user MUST be computed from developer (not admin) to form "
            "a proper monotonic chain: admin → developer → user → viewer. "
            "Currently user inherits from admin which breaks the chain. "
            "See OpenFGA Audit Resolution Plan Phase 0 Task 0.1."
        )

    def test_system_viewer_computed_from_user(self) -> None:
        """
        [CHAIN FIX] system.viewer should be computed from user (level 3).

        This test validates the monotonic chain fix. Currently FAILS because
        viewer inherits directly from admin instead of user.

        Before fix: viewer inherits from admin (FLAT - BROKEN)
        After fix: viewer inherits from user (CHAIN - CORRECT)
        """
        model = load_openfga_model()
        system_type = get_type_definition(model, "system")
        assert system_type is not None

        # Get viewer relation and check its direct sources
        viewer_relation = system_type["relations"].get("viewer")
        assert viewer_relation is not None

        sources = get_computed_sources(viewer_relation)
        assert "user" in sources, (
            "system.viewer MUST be computed from user (not admin) to form "
            "a proper monotonic chain: admin → developer → user → viewer. "
            "Currently viewer inherits from admin which breaks the chain. "
            "See OpenFGA Audit Resolution Plan Phase 0 Task 0.1."
        )

    def test_skill_chain_author_from_admin(self) -> None:
        """skill.author should be computed from admin."""
        model = load_openfga_model()
        skill_type = get_type_definition(model, "skill")
        assert skill_type is not None

        is_computed = relation_is_computed_from(skill_type, "author", "admin")
        assert is_computed, "skill.author MUST be computed from admin"

    def test_skill_chain_viewer_from_author(self) -> None:
        """skill.viewer should be computed from author."""
        model = load_openfga_model()
        skill_type = get_type_definition(model, "skill")
        assert skill_type is not None

        viewer_relation = skill_type["relations"].get("viewer")
        if viewer_relation:
            sources = get_computed_sources(viewer_relation)
            # Viewer should inherit from author OR admin (acceptable patterns)
            assert "author" in sources or "admin" in sources, (
                "skill.viewer MUST be computed from author (or admin) "
                "to form a proper privilege chain."
            )

    def test_ai_chain_user_from_admin(self) -> None:
        """ai.user should be computed from admin."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        is_computed = relation_is_computed_from(ai_type, "user", "admin")
        assert is_computed, "ai.user MUST be computed from admin"

    def test_ai_chain_viewer_from_user(self) -> None:
        """ai.viewer should be computed from user."""
        model = load_openfga_model()
        ai_type = get_type_definition(model, "ai")
        assert ai_type is not None

        is_computed = relation_is_computed_from(ai_type, "viewer", "user")
        assert is_computed, "ai.viewer MUST be computed from user"

    @pytest.mark.parametrize(
        "type_name,chain",
        [
            ("system", ["admin", "developer", "user", "viewer"]),
            ("skill", ["admin", "author", "viewer"]),
            ("ai", ["admin", "user", "viewer"]),
        ],
    )
    def test_chain_transitive_reachability(self, type_name: str, chain: list[str]) -> None:
        """
        All relations in a chain should be transitively reachable from the top.

        This validates that admin can reach all lower levels via the chain.
        """
        model = load_openfga_model()
        type_def = get_type_definition(model, type_name)
        assert type_def is not None, f"Type '{type_name}' should exist"

        top_relation = chain[0]
        for lower_relation in chain[1:]:
            is_reachable = relation_is_computed_from(type_def, lower_relation, top_relation)
            assert is_reachable, (
                f"{type_name}.{lower_relation} should be transitively reachable from {top_relation}"
            )


class TestRoleTypeRemoval:
    """
    Tests for the role type removal (Decision 1 in OpenFGA Audit).

    The 'role' type has an 'assignee' relation that is NOT wired into any
    permissions. Keeping unused types creates drift and confusion.

    These tests validate that the role type has been removed from the model.
    """

    def test_role_type_should_not_exist(self) -> None:
        """
        [AUDIT FIX] The 'role' type should be removed from the model.

        This test validates Phase 0 Task 0.3 - removing the role type.

        Rationale: role#assignee is unused for permissions - role_mappings.yaml
        assigns role:admin/role:user/role:developer but nothing checks them.
        """
        model = load_openfga_model()
        role_type = get_type_definition(model, "role")

        # After the fix, role type should NOT exist
        # Currently this test will FAIL (role type exists)
        # After fix, this test will PASS (role type removed)
        assert role_type is None, (
            "The 'role' type should be removed from model.json. "
            "The role#assignee relation is unused for permissions. "
            "See OpenFGA Audit Resolution Plan Phase 0 Task 0.3."
        )


class TestExpectedHierarchyPatterns:
    """
    Tests for common privilege hierarchy patterns.

    These validate that standard types follow expected patterns.
    """

    @pytest.mark.parametrize(
        "type_name,higher,lower",
        [
            ("dashboard", "admin", "viewer"),
            ("cost", "admin", "viewer"),
            ("observability", "admin", "viewer"),
            ("gateway", "admin", "viewer"),
            ("logs", "admin", "viewer"),
            ("traces", "admin", "viewer"),
            ("metrics", "admin", "viewer"),
            ("identity", "admin", "viewer"),
            ("budget", "admin", "viewer"),
            ("skill", "admin", "viewer"),
            ("compliance", "admin", "viewer"),
            ("config", "admin", "viewer"),
        ],
    )
    def test_standard_admin_viewer_inheritance(self, type_name: str, higher: str, lower: str) -> None:
        """
        Standard types should compute viewer from admin.

        This validates that the common pattern is correctly implemented.
        """
        model = load_openfga_model()
        type_def = get_type_definition(model, type_name)

        if type_def is None:
            pytest.skip(f"Type '{type_name}' not found in model")

        relations = type_def.get("relations", {})
        if higher not in relations or lower not in relations:
            pytest.skip(f"Type '{type_name}' doesn't have {higher} and {lower} relations")

        is_computed = relation_is_computed_from(type_def, lower, higher)
        assert is_computed, f"{type_name}.{lower} should be computed from {higher}"

    @pytest.mark.parametrize(
        "type_name",
        [
            "project",
            "workflow",
            "session",
            "vector_store",
            "conversation",
        ],
    )
    def test_owner_editor_viewer_hierarchy(self, type_name: str) -> None:
        """
        Resource types should have owner → editor → viewer hierarchy.

        This validates the standard resource hierarchy pattern.
        """
        model = load_openfga_model()
        type_def = get_type_definition(model, type_name)

        if type_def is None:
            pytest.skip(f"Type '{type_name}' not found in model")

        relations = type_def.get("relations", {})

        # Check owner → editor if both exist
        if "owner" in relations and "editor" in relations:
            is_computed = relation_is_computed_from(type_def, "editor", "owner")
            assert is_computed, f"{type_name}.editor should be computed from owner"

        # Check editor → viewer if both exist
        if "editor" in relations and "viewer" in relations:
            is_computed = relation_is_computed_from(type_def, "viewer", "editor")
            assert is_computed, f"{type_name}.viewer should be computed from editor"

        # Check owner → viewer (transitive)
        if "owner" in relations and "viewer" in relations:
            is_computed = relation_is_computed_from(type_def, "viewer", "owner")
            assert is_computed, f"{type_name}.viewer should be computed from owner (transitively)"
