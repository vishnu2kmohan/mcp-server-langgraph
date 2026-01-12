"""
TDD Tests for Artifact-Project Hierarchy.

These tests validate that artifact type has project relation for parent-child
hierarchies, enabling tuple reduction via project-based inheritance.

Reference: OpenFGA Audit Resolution Plan Phase 4 (Parent-Child Hierarchies)

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


def has_project_inheritance(relation_def: dict[str, Any]) -> bool:
    """
    Check if a relation has project-based inheritance (tupleToUserset).

    This pattern allows permissions to flow from project to child resources.

    Returns:
        True if the relation inherits from project
    """
    if "union" in relation_def:
        for child in relation_def["union"].get("child", []):
            if "tupleToUserset" in child:
                tupleset = child["tupleToUserset"].get("tupleset", {})
                # computedUserset is part of the relation but not needed for this check
                if tupleset.get("relation") == "project":
                    return True

    # Also check direct tupleToUserset
    if "tupleToUserset" in relation_def:
        tupleset = relation_def["tupleToUserset"].get("tupleset", {})
        if tupleset.get("relation") == "project":
            return True

    return False


@pytest.mark.unit
@pytest.mark.xdist_group(name="artifact_project_hierarchy")
class TestArtifactProjectRelation:
    """
    Verify artifact type has project relation for parent-child hierarchy.

    Per Phase 4.1 of OpenFGA Audit Resolution Plan:
    - artifact type should have project relation
    - editor/viewer should inherit from project
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_artifact_has_project_relation(self) -> None:
        """
        [HIERARCHY] Artifact type should have 'project' relation.

        The project relation enables parent-child hierarchy where
        artifact permissions can be inherited from project permissions.
        """
        model = load_openfga_model()
        artifact = get_type_definition(model, "artifact")
        assert artifact is not None, "artifact type must exist"

        relations = artifact.get("relations", {})
        assert "project" in relations, (
            "artifact type MUST have 'project' relation for parent-child hierarchy. "
            "This enables tuple reduction via project-based inheritance."
        )

    def test_artifact_project_accepts_project_type(self) -> None:
        """
        [HIERARCHY] artifact.project relation must accept project type directly.

        This allows tuples like: project:default -> project -> artifact:default
        """
        model = load_openfga_model()
        artifact = get_type_definition(model, "artifact")
        assert artifact is not None

        metadata = artifact.get("metadata", {}).get("relations", {})
        project_metadata = metadata.get("project", {})

        # Check if project type is in directly_related_user_types
        related_types = project_metadata.get("directly_related_user_types", [])
        project_type_present = any(t.get("type") == "project" for t in related_types)

        assert project_type_present, (
            "artifact.project relation must accept 'project' type directly. "
            'directly_related_user_types must include {"type": "project"}'
        )

    def test_artifact_editor_inherits_from_project(self) -> None:
        """
        [HIERARCHY] artifact.editor should inherit from project.editor.

        This allows project editors to automatically be artifact editors.
        """
        model = load_openfga_model()
        artifact = get_type_definition(model, "artifact")
        assert artifact is not None

        editor_relation = artifact["relations"].get("editor")
        assert editor_relation is not None, "editor relation must exist"

        has_inheritance = has_project_inheritance(editor_relation)
        assert has_inheritance, (
            "artifact.editor SHOULD inherit from project.editor via tupleToUserset. "
            "This enables project-based permission inheritance."
        )

    def test_artifact_viewer_inherits_from_project(self) -> None:
        """
        [HIERARCHY] artifact.viewer should inherit from project.viewer.

        This allows project viewers to automatically be artifact viewers.
        """
        model = load_openfga_model()
        artifact = get_type_definition(model, "artifact")
        assert artifact is not None

        viewer_relation = artifact["relations"].get("viewer")
        assert viewer_relation is not None, "viewer relation must exist"

        has_inheritance = has_project_inheritance(viewer_relation)
        assert has_inheritance, (
            "artifact.viewer SHOULD inherit from project.viewer via tupleToUserset. "
            "This enables project-based permission inheritance."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="artifact_project_hierarchy")
class TestArtifactProjectTuples:
    """
    Verify sample-tuples.json has artifact-project relationship tuples.

    Per Phase 4.2 of OpenFGA Audit Resolution Plan:
    - sample-tuples.json should include project -> artifact tuples
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sample_tuples_has_artifact_project_tuple(self) -> None:
        """
        [HIERARCHY] Sample tuples should include artifact-project relationship.
        """
        tuples_data = load_sample_tuples()
        tuples = tuples_data.get("tuples", [])

        # Look for artifact:default -> project relation
        has_artifact_project_tuple = any(
            t.get("relation") == "project" and t.get("object", "").startswith("artifact:") for t in tuples
        )

        assert has_artifact_project_tuple, (
            "sample-tuples.json MUST include artifact-project relationship tuples. "
            "Expected tuple: project:default -> project -> artifact:default"
        )
