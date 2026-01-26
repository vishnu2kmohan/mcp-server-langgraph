"""
TDD Tests for Organization Context Enforcement.

These tests validate that organization context is properly enforced
in authorization checks when the feature flag is enabled.

Reference: OpenFGA Audit Resolution Plan Phase 3 (Org Context Enforcement)

RED Phase: These tests should FAIL initially before implementation.
GREEN Phase: After implementation, these tests should PASS.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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


def get_type_definition(model: dict[str, Any], type_name: str) -> dict[str, Any] | None:
    """Get a type definition by name from the model."""
    for type_def in model.get("type_definitions", []):
        if type_def.get("type") == type_name:
            return type_def
    return None


@pytest.mark.unit
@pytest.mark.xdist_group(name="org_context_enforcement")
class TestOrganizationUserInContextRelation:
    """
    Verify organization type has user_in_context relation for contextual tuples.

    Per Phase 3.1 of OpenFGA Audit Resolution Plan:
    - organization type should have user_in_context relation
    - This enables contextual tuple injection for org-scoped authorization
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_organization_has_user_in_context_relation(self) -> None:
        """
        [SECURITY] Organization type should have 'user_in_context' relation.

        The user_in_context relation allows injecting contextual tuples
        to enforce org-scoped authorization without persisting them.
        """
        model = load_openfga_model()
        organization = get_type_definition(model, "organization")
        assert organization is not None, "organization type must exist"

        relations = organization.get("relations", {})
        assert "user_in_context" in relations, (
            "organization type MUST have 'user_in_context' relation for org context enforcement. "
            "This enables contextual tuple injection for org-scoped authorization checks."
        )

    def test_user_in_context_accepts_user_type(self) -> None:
        """
        [SECURITY] user_in_context relation must accept user type directly.

        This allows tuples like: user:alice -> user_in_context -> organization:acme
        """
        model = load_openfga_model()
        organization = get_type_definition(model, "organization")
        assert organization is not None

        metadata = organization.get("metadata", {}).get("relations", {})
        user_in_context_metadata = metadata.get("user_in_context", {})

        # Check if user type is in directly_related_user_types
        related_types = user_in_context_metadata.get("directly_related_user_types", [])
        user_type_present = any(t.get("type") == "user" for t in related_types)

        assert user_type_present, (
            "user_in_context relation must accept 'user' type directly. "
            'directly_related_user_types must include {"type": "user"}'
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="org_context_enforcement")
class TestOrgContextFeatureFlag:
    """
    Verify FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT feature flag exists.

    Per Phase 3.4 of OpenFGA Audit Resolution Plan:
    - Feature flag should exist with default=False for gradual rollout
    - Flag should control org context enforcement behavior
    - Environment variable: FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT (FF_ prefix per convention)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_org_context_enforcement_flag_exists(self) -> None:
        """
        [SECURITY] FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT flag must exist in feature flags.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Check if the field exists in the model
        field_names = list(FeatureFlags.model_fields.keys())
        assert "openfga_org_context_enforcement" in field_names, (
            "FeatureFlags must have 'openfga_org_context_enforcement' field for org context enforcement. "
            "This flag gates the org context enforcement feature."
        )

    def test_org_context_enforcement_flag_default_false(self) -> None:
        """
        [SECURITY] FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT flag must default to False.

        This ensures gradual rollout - feature is opt-in, not opt-out.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Get the default value from the field definition
        field = FeatureFlags.model_fields.get("openfga_org_context_enforcement")
        assert field is not None, "openfga_org_context_enforcement field must exist"

        # Check default is False
        assert field.default is False, (
            "openfga_org_context_enforcement must default to False for gradual rollout. "
            "Enable explicitly when ready to enforce org context."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="org_context_enforcement")
class TestAuthorizationServiceOrgContext:
    """
    Verify AuthorizationService handles org context.

    Per Phase 3.2 of OpenFGA Audit Resolution Plan:
    - AuthorizationService should accept org_context parameter
    - When flag enabled, should inject contextual tuples
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_accepts_org_context_parameter(self) -> None:
        """
        [SECURITY] AuthorizationService.authorize() must accept org_context in context dict.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Should accept org_context in context parameter
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context={"org_context": "acme"},
        )

        # Verify it was called
        assert result is True
        mock_openfga.check_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorize_passes_contextual_tuples_when_flag_enabled(self) -> None:
        """
        [SECURITY] When org context enforcement is enabled, contextual tuples should be passed.

        Contextual tuple should be: user:alice -> user_in_context -> organization:acme
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # Create mock settings with flag enabled
        mock_settings = MagicMock()
        mock_settings.openfga_org_context_enforcement = True

        service = AuthorizationService(openfga_client=mock_openfga, settings=mock_settings)

        # Call authorize with org context
        await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context={"org_context": "acme"},
        )

        # Verify contextual tuples were passed
        call_kwargs = mock_openfga.check_permission.call_args[1]
        context = call_kwargs.get("context", {})

        # Check for contextual_tuples in context
        contextual_tuples = context.get("contextual_tuples", [])
        assert len(contextual_tuples) > 0, (
            "When org context enforcement is enabled, contextual tuples must be passed. "
            "Expected contextual tuple: user:alice -> user_in_context -> organization:acme"
        )

        # Verify the contextual tuple structure
        expected_tuple = {
            "user": "user:alice",
            "relation": "user_in_context",
            "object": "organization:acme",
        }
        assert expected_tuple in contextual_tuples, (
            f"Expected contextual tuple not found. Expected: {expected_tuple}, Got: {contextual_tuples}"
        )

    @pytest.mark.asyncio
    async def test_authorize_skips_contextual_tuples_when_flag_disabled(self) -> None:
        """
        [SECURITY] When org context enforcement is disabled, no contextual tuples should be passed.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # Create mock settings with flag disabled
        mock_settings = MagicMock()
        mock_settings.openfga_org_context_enforcement = False

        service = AuthorizationService(openfga_client=mock_openfga, settings=mock_settings)

        # Call authorize with org context
        await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context={"org_context": "acme"},
        )

        # Verify no contextual tuples were passed
        call_kwargs = mock_openfga.check_permission.call_args[1]
        context = call_kwargs.get("context", {})
        contextual_tuples = context.get("contextual_tuples", [])

        assert len(contextual_tuples) == 0, (
            f"When org context enforcement is disabled, no contextual tuples should be passed. Got: {contextual_tuples}"
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="org_context_enforcement")
class TestMultiOrgUserContext:
    """
    Verify multi-org user scenarios work correctly.

    Per Phase 3.5 of OpenFGA Audit Resolution Plan:
    - User in multiple orgs should only access resources in current org context
    - Missing org context should fail closed when flag enabled
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_user_in_multiple_orgs_respects_context(self) -> None:
        """
        [SECURITY] User with access to org1 and org2 can only access org1 resources in org1 context.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client that checks contextual tuples
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config

        async def check_permission_side_effect(
            user: str, relation: str, object: str, context: dict | None = None, **kwargs: Any
        ) -> bool:
            # Only allow if contextual tuple matches expected org
            if context and "contextual_tuples" in context:
                tuples = context["contextual_tuples"]
                for t in tuples:
                    if t.get("relation") == "user_in_context" and t.get("object") == "organization:acme":
                        return True
            return False

        mock_openfga.check_permission = AsyncMock(side_effect=check_permission_side_effect)

        # Create mock settings with flag enabled
        mock_settings = MagicMock()
        mock_settings.openfga_org_context_enforcement = True

        service = AuthorizationService(openfga_client=mock_openfga, settings=mock_settings)

        # Access in correct org context should succeed
        result_acme = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context={"org_context": "acme"},
        )
        assert result_acme is True, "Access should be allowed in correct org context"

        # Access in wrong org context should fail
        result_other = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context={"org_context": "other_org"},
        )
        assert result_other is False, "Access should be denied in wrong org context"

    @pytest.mark.asyncio
    async def test_missing_context_fails_closed_when_flag_enabled(self) -> None:
        """
        [SECURITY] Missing org context should fail closed when flag enabled.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # Create mock settings with flag enabled AND fail_closed_on_missing_context
        mock_settings = MagicMock()
        mock_settings.openfga_org_context_enforcement = True
        mock_settings.openfga_org_context_fail_closed = True

        service = AuthorizationService(openfga_client=mock_openfga, settings=mock_settings)

        # Access without org context should fail closed
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context=None,  # No context provided
        )

        assert result is False, (
            "Missing org context should fail closed when flag enabled. This prevents accidental permission bypass."
        )

    @pytest.mark.asyncio
    async def test_context_not_required_when_flag_off(self) -> None:
        """
        [SECURITY] Context not required when feature flag disabled.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Create mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # Create mock settings with flag disabled
        mock_settings = MagicMock()
        mock_settings.openfga_org_context_enforcement = False
        mock_settings.openfga_org_context_fail_closed = True  # Even if fail_closed is set

        service = AuthorizationService(openfga_client=mock_openfga, settings=mock_settings)

        # Access without context should still work when flag off
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:default",
            context=None,
        )

        assert result is True, (
            "Access should be allowed without context when flag is disabled. Feature flag must gate all org context behavior."
        )
