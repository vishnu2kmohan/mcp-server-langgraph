"""
TDD Tests for Service Principal Parity.

These tests validate that service_principal type is properly included
in all user-accepting metadata fields, enabling SP-based authorization.

Reference: OpenFGA Audit Resolution Plan Phase 5 (Service Principal Parity)

RED Phase: These tests should FAIL initially before implementation.
GREEN Phase: After implementation, these tests should PASS.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def load_openfga_model() -> dict[str, Any]:
    """Load the OpenFGA model.json."""
    model_path = get_project_root() / "config" / "openfga" / "model.json"
    with model_path.open() as f:
        return json.load(f)


def load_sample_tuples() -> dict[str, Any]:
    """Load the OpenFGA sample-tuples.json."""
    tuples_path = get_project_root() / "config" / "openfga" / "sample-tuples.json"
    with tuples_path.open() as f:
        return json.load(f)


def get_type_definition(model: dict[str, Any], type_name: str) -> dict[str, Any] | None:
    """Get a type definition by name from the model."""
    for type_def in model.get("type_definitions", []):
        if type_def.get("type") == type_name:
            return type_def
    return None


def get_user_accepting_relations(type_def: dict[str, Any]) -> list[str]:
    """
    Get relations that accept user type directly.

    Returns list of relation names that have user in directly_related_user_types.
    """
    user_relations: list[str] = []
    metadata = type_def.get("metadata", {}).get("relations", {})

    for relation_name, relation_meta in metadata.items():
        related_types = relation_meta.get("directly_related_user_types", [])
        for t in related_types:
            if t.get("type") == "user":
                user_relations.append(relation_name)
                break

    return user_relations


def relation_accepts_service_principal(type_def: dict[str, Any], relation_name: str) -> bool:
    """
    Check if a relation accepts service_principal type directly.
    """
    metadata = type_def.get("metadata", {}).get("relations", {})
    relation_meta = metadata.get(relation_name, {})
    related_types = relation_meta.get("directly_related_user_types", [])

    for t in related_types:
        if t.get("type") == "service_principal":
            return True

    return False


# Types that should have service_principal support for user-accepting relations
TYPES_REQUIRING_SP_SUPPORT = [
    "tool",
    "workflow",
    "session",
    "artifact",
    "project",
    "agent",
    "skill",
    "vector_store",
    "dashboard",
    "cost",
    "observability",
    "execution",
    "chat",
    "connection",
]


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_parity")
class TestServicePrincipalMetadataParity:
    """
    Verify user-accepting relations also accept service_principal.

    Per Phase 5.1 of OpenFGA Audit Resolution Plan:
    - All relations that accept user type should also accept service_principal
    - This enables SP-based authorization for batch jobs, integrations, etc.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize("type_name", TYPES_REQUIRING_SP_SUPPORT)
    def test_user_relations_accept_service_principal(self, type_name: str) -> None:
        """
        [SP PARITY] User-accepting relations must also accept service_principal.

        This enables batch jobs, integrations, and automation to use
        fine-grained authorization like users.
        """
        model = load_openfga_model()
        type_def = get_type_definition(model, type_name)
        assert type_def is not None, f"{type_name} type must exist"

        user_relations = get_user_accepting_relations(type_def)
        missing_sp_relations: list[str] = []

        for relation in user_relations:
            if not relation_accepts_service_principal(type_def, relation):
                missing_sp_relations.append(relation)

        assert len(missing_sp_relations) == 0, (
            f"{type_name} has user-accepting relations that don't accept service_principal: "
            f"{missing_sp_relations}. "
            f"Add service_principal to directly_related_user_types for these relations."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_parity")
class TestServicePrincipalActsAsTuples:
    """
    Verify sample-tuples.json has acts_as tuples for service principals.

    Per Phase 5.2 of OpenFGA Audit Resolution Plan:
    - Sample tuples should include acts_as tuples
    - This links service principals to users for permission inheritance
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sample_tuples_has_acts_as_tuple(self) -> None:
        """
        [SP PARITY] Sample tuples should include service_principal acts_as tuple.
        """
        tuples_data = load_sample_tuples()
        tuples = tuples_data.get("tuples", [])

        # Look for acts_as relation on service_principal
        has_acts_as_tuple = any(
            t.get("relation") == "acts_as" and t.get("object", "").startswith("service_principal:") for t in tuples
        )

        assert has_acts_as_tuple, (
            "sample-tuples.json MUST include service_principal acts_as tuples. "
            "Expected: user:admin -> acts_as -> service_principal:batch-etl-job"
        )
