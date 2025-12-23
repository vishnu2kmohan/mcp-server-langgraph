"""
Tests for Claude Agent SDK feature flags.

Verifies that SDK-specific feature flags are properly defined
and can be used to control SDK functionality.
"""

import pytest

from mcp_server_langgraph.core.feature_flags import FeatureFlags, feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


class TestSDKFeatureFlags:
    """Tests for Claude Agent SDK feature flags."""

    def test_sdk_hooks_flag_exists(self) -> None:
        """enable_sdk_hooks flag should exist with default True."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_hooks")
        assert flags.enable_sdk_hooks is True

    def test_sdk_interrupt_flag_exists(self) -> None:
        """enable_sdk_interrupt flag should exist with default True."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_interrupt")
        assert flags.enable_sdk_interrupt is True

    def test_sdk_file_checkpointing_flag_exists(self) -> None:
        """enable_sdk_file_checkpointing flag should exist with default False (experimental)."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_file_checkpointing")
        assert flags.enable_sdk_file_checkpointing is False

    def test_sdk_structured_output_flag_exists(self) -> None:
        """enable_sdk_structured_output flag should exist with default True."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_structured_output")
        assert flags.enable_sdk_structured_output is True

    def test_sdk_can_use_tool_flag_exists(self) -> None:
        """enable_sdk_can_use_tool flag should exist with default False (experimental)."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_can_use_tool")
        assert flags.enable_sdk_can_use_tool is False

    def test_sdk_agent_definition_flag_exists(self) -> None:
        """enable_sdk_agent_definition flag should exist with default True (production-ready)."""
        flags = FeatureFlags()
        assert hasattr(flags, "enable_sdk_agent_definition")
        assert flags.enable_sdk_agent_definition is True

    def test_global_feature_flags_has_sdk_flags(self) -> None:
        """Global feature_flags instance should have SDK flags."""
        assert hasattr(feature_flags, "enable_sdk_hooks")
        assert hasattr(feature_flags, "enable_sdk_interrupt")
        assert hasattr(feature_flags, "enable_sdk_structured_output")

    def test_is_feature_enabled_for_sdk_flags(self) -> None:
        """is_feature_enabled should work for SDK flags."""
        flags = FeatureFlags()

        # Default enabled (production-ready)
        assert flags.is_feature_enabled("enable_sdk_hooks") is True
        assert flags.is_feature_enabled("enable_sdk_interrupt") is True
        assert flags.is_feature_enabled("enable_sdk_structured_output") is True
        assert flags.is_feature_enabled("enable_sdk_agent_definition") is True

        # Default disabled (experimental, requires explicit opt-in)
        assert flags.is_feature_enabled("enable_sdk_file_checkpointing") is False
        assert flags.is_feature_enabled("enable_sdk_can_use_tool") is False

    def test_sdk_flags_have_descriptions(self) -> None:
        """SDK flags should have proper descriptions in schema."""
        schema = FeatureFlags.model_json_schema()
        properties = schema.get("properties", {})

        sdk_flags = [
            "enable_sdk_hooks",
            "enable_sdk_interrupt",
            "enable_sdk_file_checkpointing",
            "enable_sdk_structured_output",
            "enable_sdk_can_use_tool",
            "enable_sdk_agent_definition",
        ]

        for flag_name in sdk_flags:
            assert flag_name in properties, f"Missing flag: {flag_name}"
            assert "description" in properties[flag_name], f"Missing description for {flag_name}"
            # Description should mention Claude Agent SDK
            assert "SDK" in properties[flag_name]["description"], f"Description for {flag_name} should mention SDK"
