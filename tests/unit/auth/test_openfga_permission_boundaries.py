"""
TDD Tests for OpenFGA Permission Boundaries.

These tests validate that organization membership DOES NOT automatically grant
access to sensitive resources, enforcing proper tenant isolation.

Reference: OpenFGA Audit Resolution Plan Phase 1 (Security Tightening)

RED Phase: These tests should FAIL with the current model where:
- vector_store.viewer has org→member propagation
- artifact.viewer has org→member propagation
- workflow.executor has org→member propagation
- session.viewer has org→member propagation

GREEN Phase: After removing overbroad propagation, these tests should PASS.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
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


def has_org_member_propagation(relation_def: dict[str, Any]) -> bool:
    """
    Check if a relation has organization→member propagation (tupleToUserset).

    This pattern allows any org member to have the relation, which is too broad
    for sensitive resources.

    Returns:
        True if the relation propagates from org membership
    """
    if "union" in relation_def:
        for child in relation_def["union"].get("child", []):
            if "tupleToUserset" in child:
                tupleset = child["tupleToUserset"].get("tupleset", {})
                computed = child["tupleToUserset"].get("computedUserset", {})
                if (
                    tupleset.get("relation") == "organization"
                    and computed.get("relation") == "member"
                ):
                    return True

    # Also check direct tupleToUserset
    if "tupleToUserset" in relation_def:
        tupleset = relation_def["tupleToUserset"].get("tupleset", {})
        computed = relation_def["tupleToUserset"].get("computedUserset", {})
        if (
            tupleset.get("relation") == "organization"
            and computed.get("relation") == "member"
        ):
            return True

    return False


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_permission_boundaries")
class TestOrgPropagationBoundaries:
    """
    Verify org membership doesn't grant access to sensitive resources.

    Per OpenFGA Audit Resolution Plan Phase 1:
    - vector_store.viewer should NOT have org→member propagation
    - artifact.viewer should NOT have org→member propagation
    - workflow.executor should NOT have org→member propagation
    - session.viewer should NOT have org→member propagation
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vector_store_viewer_no_org_propagation(self) -> None:
        """
        [SECURITY] Org membership should NOT grant vector_store viewer access.

        Vector stores may contain sensitive embeddings and should require
        explicit grants, not blanket org membership.
        """
        model = load_openfga_model()
        vector_store = get_type_definition(model, "vector_store")
        assert vector_store is not None, "vector_store type must exist"

        viewer_relation = vector_store["relations"].get("viewer")
        assert viewer_relation is not None, "viewer relation must exist"

        has_propagation = has_org_member_propagation(viewer_relation)
        assert not has_propagation, (
            "vector_store.viewer MUST NOT have org→member propagation. "
            "Access to vector stores should require explicit grants, not org membership."
        )

    def test_artifact_viewer_no_org_propagation(self) -> None:
        """
        [SECURITY] Org membership should NOT grant artifact viewer access.

        Artifacts may contain sensitive generated content and should require
        explicit grants or project-based access, not blanket org membership.
        """
        model = load_openfga_model()
        artifact = get_type_definition(model, "artifact")
        assert artifact is not None, "artifact type must exist"

        viewer_relation = artifact["relations"].get("viewer")
        assert viewer_relation is not None, "viewer relation must exist"

        has_propagation = has_org_member_propagation(viewer_relation)
        assert not has_propagation, (
            "artifact.viewer MUST NOT have org→member propagation. "
            "Artifacts should be accessed via project ownership or explicit grants."
        )

    def test_workflow_executor_no_org_propagation(self) -> None:
        """
        [SECURITY] Org membership should NOT grant workflow executor access.

        Workflow execution is a privileged operation that can trigger actions.
        It should require explicit executor grants, not blanket org membership.
        """
        model = load_openfga_model()
        workflow = get_type_definition(model, "workflow")
        assert workflow is not None, "workflow type must exist"

        executor_relation = workflow["relations"].get("executor")
        assert executor_relation is not None, "executor relation must exist"

        has_propagation = has_org_member_propagation(executor_relation)
        assert not has_propagation, (
            "workflow.executor MUST NOT have org→member propagation. "
            "Workflow execution should require explicit executor grants."
        )

    def test_session_viewer_no_org_propagation(self) -> None:
        """
        [SECURITY] Org membership should NOT grant session viewer access.

        Sessions may contain sensitive conversation history and state.
        They should be accessed via project inheritance or explicit grants.
        """
        model = load_openfga_model()
        session = get_type_definition(model, "session")
        assert session is not None, "session type must exist"

        viewer_relation = session["relations"].get("viewer")
        assert viewer_relation is not None, "viewer relation must exist"

        has_propagation = has_org_member_propagation(viewer_relation)
        assert not has_propagation, (
            "session.viewer MUST NOT have org→member propagation. "
            "Sessions should be accessed via project inheritance or explicit grants."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_permission_boundaries")
class TestAllowedOrgPropagation:
    """
    Verify that org propagation is KEPT for appropriate resources.

    Per OpenFGA Audit Resolution Plan Decision 4:
    - workflow.viewer: KEEP (org can read all workflows)
    - project.viewer: KEEP (projects are org-scoped)
    - project.executor: KEEP (org-wide execution intended)
    - tool.executor: KEEP (org-wide tool access)
    - cost.viewer: KEEP (cost transparency OK)
    - dashboard.viewer: KEEP (operational visibility OK)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_viewer_keeps_org_propagation(self) -> None:
        """
        [POLICY] workflow.viewer SHOULD have org→member propagation.

        Org members should be able to view (but not execute) workflows.
        """
        model = load_openfga_model()
        workflow = get_type_definition(model, "workflow")
        assert workflow is not None

        viewer_relation = workflow["relations"].get("viewer")
        assert viewer_relation is not None

        has_propagation = has_org_member_propagation(viewer_relation)
        assert has_propagation, (
            "workflow.viewer SHOULD have org→member propagation per Decision 4."
        )

    def test_project_viewer_keeps_org_propagation(self) -> None:
        """
        [POLICY] project.viewer SHOULD have org→member propagation.

        Projects are org-scoped and all members should see them.
        """
        model = load_openfga_model()
        project = get_type_definition(model, "project")
        assert project is not None

        viewer_relation = project["relations"].get("viewer")
        assert viewer_relation is not None

        has_propagation = has_org_member_propagation(viewer_relation)
        assert has_propagation, (
            "project.viewer SHOULD have org→member propagation per Decision 4."
        )

    def test_project_executor_keeps_org_propagation(self) -> None:
        """
        [POLICY] project.executor SHOULD have org→member propagation.

        Org-wide project execution is intentional per design.
        """
        model = load_openfga_model()
        project = get_type_definition(model, "project")
        assert project is not None

        executor_relation = project["relations"].get("executor")
        assert executor_relation is not None

        has_propagation = has_org_member_propagation(executor_relation)
        assert has_propagation, (
            "project.executor SHOULD have org→member propagation per Decision 4."
        )

    def test_tool_executor_keeps_org_propagation(self) -> None:
        """
        [POLICY] tool.executor SHOULD have org→member propagation.

        Org members should have access to org-registered tools.
        """
        model = load_openfga_model()
        tool = get_type_definition(model, "tool")
        assert tool is not None

        executor_relation = tool["relations"].get("executor")
        assert executor_relation is not None

        has_propagation = has_org_member_propagation(executor_relation)
        assert has_propagation, (
            "tool.executor SHOULD have org→member propagation per Decision 4."
        )

    def test_cost_viewer_keeps_org_propagation(self) -> None:
        """
        [POLICY] cost.viewer SHOULD have org→member propagation.

        Cost transparency within org is acceptable.
        """
        model = load_openfga_model()
        cost = get_type_definition(model, "cost")
        assert cost is not None

        viewer_relation = cost["relations"].get("viewer")
        assert viewer_relation is not None

        has_propagation = has_org_member_propagation(viewer_relation)
        assert has_propagation, (
            "cost.viewer SHOULD have org→member propagation per Decision 4."
        )

    def test_dashboard_viewer_keeps_org_propagation(self) -> None:
        """
        [POLICY] dashboard.viewer SHOULD have org→member propagation.

        Operational visibility within org is acceptable.
        """
        model = load_openfga_model()
        dashboard = get_type_definition(model, "dashboard")
        assert dashboard is not None

        viewer_relation = dashboard["relations"].get("viewer")
        assert viewer_relation is not None

        has_propagation = has_org_member_propagation(viewer_relation)
        assert has_propagation, (
            "dashboard.viewer SHOULD have org→member propagation per Decision 4."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_permission_boundaries")
class TestObservabilityOpsRelation:
    """
    Verify observability type has ops relation for narrower access.

    Per OpenFGA Audit Resolution Plan Phase 1.3:
    - observability.ops relation should exist
    - observability.viewer should be computed from ops (not just admin)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_observability_has_ops_relation(self) -> None:
        """
        [SECURITY] observability type should have 'ops' relation.

        The ops relation provides narrower access than org membership
        for PII-sensitive observability data.
        """
        model = load_openfga_model()
        observability = get_type_definition(model, "observability")
        assert observability is not None

        relations = observability.get("relations", {})
        assert "ops" in relations, (
            "observability type MUST have 'ops' relation for narrower access control."
        )

    def test_observability_viewer_computed_from_ops(self) -> None:
        """
        [SECURITY] observability.viewer should be computed from ops.

        Viewer access should include ops role, not blanket org membership.
        """
        model = load_openfga_model()
        observability = get_type_definition(model, "observability")
        assert observability is not None

        viewer_relation = observability["relations"].get("viewer")
        assert viewer_relation is not None

        # Check if viewer is computed from ops
        has_ops_computed = False
        if "union" in viewer_relation:
            for child in viewer_relation["union"].get("child", []):
                if "computedUserset" in child:
                    if child["computedUserset"].get("relation") == "ops":
                        has_ops_computed = True
                        break

        assert has_ops_computed, (
            "observability.viewer SHOULD be computed from ops relation."
        )

    def test_observability_no_org_propagation(self) -> None:
        """
        [SECURITY] observability.viewer should NOT have org→member propagation.

        Observability data may contain PII and should not be accessible
        to all org members.
        """
        model = load_openfga_model()
        observability = get_type_definition(model, "observability")
        assert observability is not None

        viewer_relation = observability["relations"].get("viewer")
        assert viewer_relation is not None

        has_propagation = has_org_member_propagation(viewer_relation)
        assert not has_propagation, (
            "observability.viewer MUST NOT have org→member propagation. "
            "Access should be limited to admin and ops roles for PII protection."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_permission_boundaries")
class TestTenantIsolationRelations:
    """
    Verify types have organization relation for tenant isolation.

    Per OpenFGA Audit Resolution Plan Phase 2:
    - api_key should have organization relation
    - skill should have organization relation
    - These are for tenant isolation, NOT viewer propagation
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_api_key_has_organization_relation(self) -> None:
        """
        [TENANT] api_key type should have 'organization' relation.

        API keys need org isolation for per-tenant key management.
        """
        model = load_openfga_model()
        api_key = get_type_definition(model, "api_key")
        assert api_key is not None

        relations = api_key.get("relations", {})
        assert "organization" in relations, (
            "api_key type MUST have 'organization' relation for tenant isolation."
        )

    def test_skill_has_organization_relation(self) -> None:
        """
        [TENANT] skill type should have 'organization' relation.

        Skills need org isolation for per-tenant skill visibility.
        """
        model = load_openfga_model()
        skill = get_type_definition(model, "skill")
        assert skill is not None

        relations = skill.get("relations", {})
        assert "organization" in relations, (
            "skill type MUST have 'organization' relation for tenant isolation."
        )
