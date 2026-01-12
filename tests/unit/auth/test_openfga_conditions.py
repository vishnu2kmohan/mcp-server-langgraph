"""
TDD Tests for OpenFGA Conditions Support.

These tests validate that the OpenFGA model supports conditions for:
1. Time-bound shares (artifact, conversation)
2. Subscription tier checks (tool_index, skill_index)

Reference: OpenFGA Audit Resolution Plan Phase 6 (Conditions)

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
@pytest.mark.xdist_group(name="openfga_conditions")
class TestConditionDefinitions:
    """
    Verify model.json has condition definitions.

    Per Phase 6.2 of OpenFGA Audit Resolution Plan:
    - time_bound_share condition for artifact/conversation sharing
    - subscription_tier condition for search access tiers
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_has_conditions_key(self) -> None:
        """
        [CONDITIONS] Model should have conditions key at top level.

        OpenFGA v1.1+ models can define conditions for contextual authorization.
        """
        model = load_openfga_model()

        assert "conditions" in model, (
            "model.json MUST have 'conditions' key for condition definitions. "
            "Add conditions key with time_bound_share and subscription_tier definitions."
        )

    def test_time_bound_share_condition_exists(self) -> None:
        """
        [CONDITIONS] time_bound_share condition should be defined.

        This condition enables time-limited sharing of artifacts and conversations.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})

        assert "time_bound_share" in conditions, (
            "model.json MUST define 'time_bound_share' condition. This enables time-limited artifact/conversation sharing."
        )

        condition = conditions["time_bound_share"]
        assert "name" in condition, "Condition must have name field"
        assert condition["name"] == "time_bound_share"

    def test_time_bound_share_has_required_parameters(self) -> None:
        """
        [CONDITIONS] time_bound_share must have current_time and expiry_time params.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})
        condition = conditions.get("time_bound_share", {})
        params = condition.get("parameters", {})

        assert "current_time" in params, "time_bound_share must have 'current_time' parameter (TYPE_NAME_TIMESTAMP)"
        assert "expiry_time" in params, "time_bound_share must have 'expiry_time' parameter (TYPE_NAME_TIMESTAMP)"

    def test_subscription_tier_condition_exists(self) -> None:
        """
        [CONDITIONS] subscription_tier condition should be defined.

        This condition enables tier-based access to tool/skill search.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})

        assert "subscription_tier" in conditions, (
            "model.json MUST define 'subscription_tier' condition. This enables tier-based access control for search features."
        )

        condition = conditions["subscription_tier"]
        assert "name" in condition, "Condition must have name field"
        assert condition["name"] == "subscription_tier"

    def test_subscription_tier_has_required_parameters(self) -> None:
        """
        [CONDITIONS] subscription_tier must have user_tier and required_tier params.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})
        condition = conditions.get("subscription_tier", {})
        params = condition.get("parameters", {})

        assert "user_tier" in params, "subscription_tier must have 'user_tier' parameter (TYPE_NAME_STRING)"
        assert "required_tier" in params, "subscription_tier must have 'required_tier' parameter (TYPE_NAME_STRING)"


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_conditions")
class TestConditionsFeatureFlag:
    """
    Verify FF_OPENFGA_CONDITIONS_ENABLED feature flag exists.

    Per Phase 6.4 of OpenFGA Audit Resolution Plan:
    - Feature flag must exist for gradual rollout
    - Default should be False (off)
    - Environment variable: FF_OPENFGA_CONDITIONS_ENABLED (FF_ prefix per convention)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_conditions_feature_flag_exists(self) -> None:
        """
        [CONDITIONS] FF_OPENFGA_CONDITIONS_ENABLED feature flag must exist.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "openfga_conditions_enabled"), (
            "FeatureFlags must have 'openfga_conditions_enabled' field. "
            "Add this field to src/mcp_server_langgraph/core/feature_flags.py"
        )

    def test_conditions_feature_flag_default_off(self) -> None:
        """
        [CONDITIONS] Conditions feature flag should default to False.

        Conditions require code changes to pass context, so off by default.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.openfga_conditions_enabled is False, (
            "openfga_conditions_enabled should default to False for gradual rollout"
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_conditions")
class TestAuthorizationServiceConditions:
    """
    Verify AuthorizationService supports condition context.

    Per Phase 6.3 of OpenFGA Audit Resolution Plan:
    - Authorization service must accept context parameter
    - Context passed to OpenFGA check when conditions enabled
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authorize_method_accepts_context(self) -> None:
        """
        [CONDITIONS] authorize() method should accept context parameter.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        service = AuthorizationService()

        # Check method signature includes context parameter
        import inspect

        sig = inspect.signature(service.authorize)
        assert "context" in sig.parameters, "AuthorizationService.authorize() must accept 'context' parameter"

    @pytest.mark.asyncio
    async def test_context_passed_to_openfga_when_conditions_enabled(self) -> None:
        """
        [CONDITIONS] Context should be passed to OpenFGA when conditions enabled.
        """
        from mcp_server_langgraph.auth.authorization import AuthorizationService

        # Mock OpenFGA client
        mock_openfga = AsyncMock()  # noqa: async-mock-config
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # Mock settings with conditions enabled
        mock_settings = MagicMock()
        mock_settings.openfga_conditions_enabled = True
        mock_settings.openfga_org_context_enforcement = False
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        service = AuthorizationService(
            openfga_client=mock_openfga,
            settings=mock_settings,
        )

        # Call authorize with condition context
        condition_context = {
            "current_time": "2026-01-08T00:00:00Z",
            "user_tier": "premium",
        }

        await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="artifact:doc1",
            context=condition_context,
        )

        # Verify context was passed to OpenFGA
        mock_openfga.check_permission.assert_called_once()
        call_kwargs = mock_openfga.check_permission.call_args
        assert call_kwargs is not None

        # Context should be present in the call
        if call_kwargs.kwargs:
            assert "context" in call_kwargs.kwargs


@pytest.mark.unit
@pytest.mark.xdist_group(name="openfga_conditions")
class TestConditionExpressions:
    """
    Verify condition expressions are valid.

    Conditions use CEL (Common Expression Language) for evaluation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_time_bound_share_has_expression(self) -> None:
        """
        [CONDITIONS] time_bound_share must have valid expression.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})
        condition = conditions.get("time_bound_share", {})

        assert "expression" in condition, "time_bound_share must have 'expression' field with CEL expression"

        expression = condition["expression"]
        # Expression should compare current_time with expiry_time
        assert "current_time" in expression, "Expression should use current_time"
        assert "expiry_time" in expression, "Expression should use expiry_time"

    def test_subscription_tier_has_expression(self) -> None:
        """
        [CONDITIONS] subscription_tier must have valid expression.
        """
        model = load_openfga_model()
        conditions = model.get("conditions", {})
        condition = conditions.get("subscription_tier", {})

        assert "expression" in condition, "subscription_tier must have 'expression' field with CEL expression"

        expression = condition["expression"]
        # Expression should compare user_tier with required_tier
        assert "user_tier" in expression or "tier" in expression.lower(), "Expression should reference tier comparison"
