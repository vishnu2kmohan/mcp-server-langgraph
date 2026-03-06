"""Tests for ADR-0092 Hierarchical Capability Architecture feature flags.

TDD: These tests define the contract for the 9 new ADR-0092 feature flags
that control phased rollout of hierarchical capability resolution.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="adr0092_flags_core")
class TestADR0092CoreFeatureFlags:
    """Tests for ADR-0092 core feature flags (P0/P1 priority)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_enhanced_router_output_exists(self) -> None:
        """Test enable_enhanced_router_output flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_enhanced_router_output")
        assert flags.enable_enhanced_router_output is False

    def test_enable_enhanced_router_output_can_be_enabled(self) -> None:
        """Test enable_enhanced_router_output can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_enhanced_router_output=True)

        assert flags.enable_enhanced_router_output is True

    def test_enable_enhanced_router_output_env_override(self) -> None:
        """Test enable_enhanced_router_output respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_ENHANCED_ROUTER_OUTPUT": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_enhanced_router_output is True

    def test_enable_capability_resolution_exists(self) -> None:
        """Test enable_capability_resolution flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_capability_resolution")
        assert flags.enable_capability_resolution is False

    def test_enable_capability_resolution_can_be_enabled(self) -> None:
        """Test enable_capability_resolution can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_capability_resolution=True)

        assert flags.enable_capability_resolution is True

    def test_enable_capability_resolution_env_override(self) -> None:
        """Test enable_capability_resolution respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_CAPABILITY_RESOLUTION": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_capability_resolution is True

    def test_enable_studio_md_loading_exists(self) -> None:
        """Test enable_studio_md_loading flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_studio_md_loading")
        assert flags.enable_studio_md_loading is False

    def test_enable_studio_md_loading_can_be_enabled(self) -> None:
        """Test enable_studio_md_loading can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_studio_md_loading=True)

        assert flags.enable_studio_md_loading is True

    def test_enable_studio_md_loading_env_override(self) -> None:
        """Test enable_studio_md_loading respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_STUDIO_MD_LOADING": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_studio_md_loading is True

    def test_enable_multi_pattern_execution_exists(self) -> None:
        """Test enable_multi_pattern_execution flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_multi_pattern_execution")
        assert flags.enable_multi_pattern_execution is False

    def test_enable_multi_pattern_execution_can_be_enabled(self) -> None:
        """Test enable_multi_pattern_execution can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_multi_pattern_execution=True)

        assert flags.enable_multi_pattern_execution is True

    def test_enable_multi_pattern_execution_env_override(self) -> None:
        """Test enable_multi_pattern_execution respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_MULTI_PATTERN_EXECUTION": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_multi_pattern_execution is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="adr0092_flags_optional")
class TestADR0092OptionalFeatureFlags:
    """Tests for ADR-0092 optional feature flags (P2/P3 priority)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_user_capability_selection_exists(self) -> None:
        """Test enable_user_capability_selection flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_user_capability_selection")
        assert flags.enable_user_capability_selection is False

    def test_enable_user_capability_selection_can_be_enabled(self) -> None:
        """Test enable_user_capability_selection can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_user_capability_selection=True)

        assert flags.enable_user_capability_selection is True

    def test_enable_user_capability_selection_env_override(self) -> None:
        """Test enable_user_capability_selection respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_USER_CAPABILITY_SELECTION": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_user_capability_selection is True

    def test_enable_progressive_skill_loading_exists(self) -> None:
        """Test enable_progressive_skill_loading flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_progressive_skill_loading")
        assert flags.enable_progressive_skill_loading is False

    def test_enable_progressive_skill_loading_can_be_enabled(self) -> None:
        """Test enable_progressive_skill_loading can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_progressive_skill_loading=True)

        assert flags.enable_progressive_skill_loading is True

    def test_enable_progressive_skill_loading_env_override(self) -> None:
        """Test enable_progressive_skill_loading respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_PROGRESSIVE_SKILL_LOADING": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_progressive_skill_loading is True

    def test_enable_semantic_skill_search_exists(self) -> None:
        """Test enable_semantic_skill_search flag exists with default True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_semantic_skill_search")
        assert flags.enable_semantic_skill_search is True

    def test_enable_semantic_skill_search_can_be_enabled(self) -> None:
        """Test enable_semantic_skill_search can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_semantic_skill_search=True)

        assert flags.enable_semantic_skill_search is True

    def test_enable_semantic_skill_search_env_override(self) -> None:
        """Test enable_semantic_skill_search respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_SEMANTIC_SKILL_SEARCH": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_semantic_skill_search is True

    def test_enable_semantic_memory_search_exists(self) -> None:
        """Test enable_semantic_memory_search flag exists with default True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_semantic_memory_search")
        assert flags.enable_semantic_memory_search is True

    def test_enable_semantic_memory_search_can_be_enabled(self) -> None:
        """Test enable_semantic_memory_search can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_semantic_memory_search=True)

        assert flags.enable_semantic_memory_search is True

    def test_enable_semantic_memory_search_env_override(self) -> None:
        """Test enable_semantic_memory_search respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_SEMANTIC_MEMORY_SEARCH": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_semantic_memory_search is True

    def test_enable_hitl_undo_rollback_exists(self) -> None:
        """Test enable_hitl_undo_rollback flag exists with default False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_hitl_undo_rollback")
        assert flags.enable_hitl_undo_rollback is False

    def test_enable_hitl_undo_rollback_can_be_enabled(self) -> None:
        """Test enable_hitl_undo_rollback can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_hitl_undo_rollback=True)

        assert flags.enable_hitl_undo_rollback is True

    def test_enable_hitl_undo_rollback_env_override(self) -> None:
        """Test enable_hitl_undo_rollback respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_HITL_UNDO_ROLLBACK": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_hitl_undo_rollback is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="adr0092_flags_integration")
class TestADR0092FeatureFlagIntegration:
    """Tests for ADR-0092 feature flag integration with existing patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_feature_enabled_works_for_adr0092_flags(self) -> None:
        """Test is_feature_enabled helper works for ADR-0092 flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_enhanced_router_output=True,
            enable_capability_resolution=False,
        )

        assert flags.is_feature_enabled("enable_enhanced_router_output") is True
        assert flags.is_feature_enabled("enable_capability_resolution") is False

    def test_require_feature_raises_for_disabled_adr0092_flags(self) -> None:
        """Test require_feature raises for disabled ADR-0092 flags."""
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_enhanced_router_output=False)

        # Ensure FF_TEST_MODE is not set (it bypasses require_feature checks)
        with patch.dict(os.environ, {"FF_TEST_MODE": ""}, clear=False):
            with pytest.raises(FeatureDisabledError):
                flags.require_feature("enable_enhanced_router_output", "Enhanced Router Output")

    def test_require_feature_passes_for_enabled_adr0092_flags(self) -> None:
        """Test require_feature passes for enabled ADR-0092 flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_capability_resolution=True)

        # Should not raise
        flags.require_feature("enable_capability_resolution", "Capability Resolution")

    def test_all_adr0092_flags_default_to_expected_values(self) -> None:
        """Test all ADR-0092 flags default to expected values."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Core flags (default False)
        assert flags.enable_enhanced_router_output is False
        assert flags.enable_capability_resolution is False
        assert flags.enable_studio_md_loading is False
        assert flags.enable_multi_pattern_execution is False

        # Optional flags (promoted to True after stabilization)
        assert flags.enable_user_capability_selection is False
        assert flags.enable_progressive_skill_loading is False
        assert flags.enable_semantic_skill_search is True
        assert flags.enable_semantic_memory_search is True
        assert flags.enable_hitl_undo_rollback is False

    def test_adr0092_flags_can_be_enabled_together(self) -> None:
        """Test multiple ADR-0092 flags can be enabled together."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_enhanced_router_output=True,
            enable_capability_resolution=True,
            enable_studio_md_loading=True,
            enable_multi_pattern_execution=True,
        )

        assert flags.enable_enhanced_router_output is True
        assert flags.enable_capability_resolution is True
        assert flags.enable_studio_md_loading is True
        assert flags.enable_multi_pattern_execution is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="adr0092_master_flag")
class TestHierarchicalCapabilityProviderMasterFlag:
    """Tests for enable_hierarchical_capability_provider master flag.

    This master flag enables the entire ADR-0092 Hierarchical Capability
    Architecture with a single toggle for convenience.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_hierarchical_capability_provider_exists(self) -> None:
        """Test enable_hierarchical_capability_provider flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_hierarchical_capability_provider")

    def test_enable_hierarchical_capability_provider_defaults_false(self) -> None:
        """Test enable_hierarchical_capability_provider defaults to False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_hierarchical_capability_provider is False

    def test_enable_hierarchical_capability_provider_can_be_enabled(self) -> None:
        """Test enable_hierarchical_capability_provider can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_hierarchical_capability_provider=True)
        assert flags.enable_hierarchical_capability_provider is True

    def test_enable_hierarchical_capability_provider_env_override(self) -> None:
        """Test enable_hierarchical_capability_provider can be set via environment."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_ENABLE_HIERARCHICAL_CAPABILITY_PROVIDER": "true"}):
            flags = FeatureFlags()
            assert flags.enable_hierarchical_capability_provider is True

    def test_master_flag_enables_all_core_adr0092_flags(self) -> None:
        """Test that is_hierarchical_capability_enabled property checks all core flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # When master flag is enabled, is_hierarchical_capability_enabled should be True
        flags = FeatureFlags(enable_hierarchical_capability_provider=True)
        assert flags.is_hierarchical_capability_enabled is True

        # When master flag is disabled, should be False
        flags = FeatureFlags(enable_hierarchical_capability_provider=False)
        assert flags.is_hierarchical_capability_enabled is False

    def test_individual_flags_also_enable_capability(self) -> None:
        """Test that individual core flags also enable capability when set."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # When capability_resolution is enabled (without master), should also work
        flags = FeatureFlags(enable_capability_resolution=True)
        assert flags.is_hierarchical_capability_enabled is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="ui_shell_feature_flags")
class TestUIShellFeatureFlags:
    """Tests for UI shell feature flags (model selector, URL fetch in shell).

    Sprint 4: Chat Input Feature Gap - feature flags for shell-specific features.
    Reference: Plan Part 1 - Chat Input Gap Fix.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_model_selector_in_shell_exists(self) -> None:
        """Test enable_model_selector_in_shell flag exists with default True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_model_selector_in_shell")
        assert flags.enable_model_selector_in_shell is True

    def test_enable_model_selector_in_shell_can_be_enabled(self) -> None:
        """Test enable_model_selector_in_shell can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_model_selector_in_shell=True)

        assert flags.enable_model_selector_in_shell is True

    def test_enable_model_selector_in_shell_env_override(self) -> None:
        """Test enable_model_selector_in_shell respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_MODEL_SELECTOR_IN_SHELL": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_model_selector_in_shell is True

    def test_enable_url_fetch_in_shell_exists(self) -> None:
        """Test enable_url_fetch_in_shell flag exists with default True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert hasattr(flags, "enable_url_fetch_in_shell")
        assert flags.enable_url_fetch_in_shell is True

    def test_enable_url_fetch_in_shell_can_be_enabled(self) -> None:
        """Test enable_url_fetch_in_shell can be set to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_url_fetch_in_shell=True)

        assert flags.enable_url_fetch_in_shell is True

    def test_enable_url_fetch_in_shell_env_override(self) -> None:
        """Test enable_url_fetch_in_shell respects environment variable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {"FF_ENABLE_URL_FETCH_IN_SHELL": "true"},
        ):
            flags = FeatureFlags()

            assert flags.enable_url_fetch_in_shell is True
