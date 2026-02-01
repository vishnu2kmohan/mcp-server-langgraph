"""
Tests for Semantic Search Feature Flags (ADR-0099).

TDD RED Phase: These tests verify the feature flag naming and wiring
for semantic search across tools, skills, and memories.

Feature Flags:
- FF_ENABLE_SEMANTIC_TOOL_SEARCH / enable_semantic_tool_search
- FF_ENABLE_SEMANTIC_SKILL_SEARCH / enable_semantic_skill_search
- FF_ENABLE_SEMANTIC_MEMORY_SEARCH / enable_semantic_memory_search
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_search_flags")
class TestSemanticSearchFeatureFlags:
    """Tests for semantic search feature flag naming and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flags_has_enable_semantic_tool_search(self) -> None:
        """FeatureFlags should have enable_semantic_tool_search attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_semantic_tool_search")
        assert isinstance(flags.enable_semantic_tool_search, bool)

    def test_feature_flags_has_enable_semantic_skill_search(self) -> None:
        """FeatureFlags should have enable_semantic_skill_search attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_semantic_skill_search")
        assert isinstance(flags.enable_semantic_skill_search, bool)

    def test_feature_flags_has_enable_semantic_memory_search(self) -> None:
        """FeatureFlags should have enable_semantic_memory_search attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_semantic_memory_search")
        assert isinstance(flags.enable_semantic_memory_search, bool)

    def test_env_var_ff_enable_semantic_tool_search(self, monkeypatch) -> None:
        """FF_ENABLE_SEMANTIC_TOOL_SEARCH env var should set flag."""
        monkeypatch.setenv("FF_ENABLE_SEMANTIC_TOOL_SEARCH", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_semantic_tool_search is True

    def test_env_var_ff_enable_semantic_skill_search(self, monkeypatch) -> None:
        """FF_ENABLE_SEMANTIC_SKILL_SEARCH env var should set flag."""
        monkeypatch.setenv("FF_ENABLE_SEMANTIC_SKILL_SEARCH", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_semantic_skill_search is True

    def test_env_var_ff_enable_semantic_memory_search(self, monkeypatch) -> None:
        """FF_ENABLE_SEMANTIC_MEMORY_SEARCH env var should set flag."""
        monkeypatch.setenv("FF_ENABLE_SEMANTIC_MEMORY_SEARCH", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_semantic_memory_search is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_config_semantic_flags")
class TestAgentConfigSemanticSearchFlags:
    """Tests for AgentConfig semantic search flag wiring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_config_has_enable_semantic_tool_search(self) -> None:
        """AgentConfig should have enable_semantic_tool_search attribute."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "enable_semantic_tool_search")
        assert isinstance(config.enable_semantic_tool_search, bool)

    def test_agent_config_has_enable_semantic_skill_search(self) -> None:
        """AgentConfig should have enable_semantic_skill_search attribute."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "enable_semantic_skill_search")
        assert isinstance(config.enable_semantic_skill_search, bool)

    def test_agent_config_has_enable_semantic_memory_search(self) -> None:
        """AgentConfig should have enable_semantic_memory_search attribute."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert hasattr(config, "enable_semantic_memory_search")
        assert isinstance(config.enable_semantic_memory_search, bool)

    def test_agent_config_semantic_tool_search_in_topology_fields(self) -> None:
        """enable_semantic_tool_search should be in topology fields."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert "enable_semantic_tool_search" in config.topology_fields

    def test_agent_config_semantic_skill_search_in_topology_fields(self) -> None:
        """enable_semantic_skill_search should be in topology fields."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert "enable_semantic_skill_search" in config.topology_fields

    def test_agent_config_semantic_memory_search_in_topology_fields(self) -> None:
        """enable_semantic_memory_search should be in topology fields."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        assert "enable_semantic_memory_search" in config.topology_fields

    def test_agent_config_graph_version_includes_all_semantic_flags(self) -> None:
        """graph_version should change when any semantic flag changes."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        # All disabled
        config_none = AgentConfig(
            enable_semantic_tool_search=False,
            enable_semantic_skill_search=False,
            enable_semantic_memory_search=False,
        )

        # Tool search enabled
        config_tool = AgentConfig(
            enable_semantic_tool_search=True,
            enable_semantic_skill_search=False,
            enable_semantic_memory_search=False,
        )

        # Skill search enabled
        config_skill = AgentConfig(
            enable_semantic_tool_search=False,
            enable_semantic_skill_search=True,
            enable_semantic_memory_search=False,
        )

        # Memory search enabled
        config_memory = AgentConfig(
            enable_semantic_tool_search=False,
            enable_semantic_skill_search=False,
            enable_semantic_memory_search=True,
        )

        # All versions should be different
        versions = {
            config_none.graph_version,
            config_tool.graph_version,
            config_skill.graph_version,
            config_memory.graph_version,
        }
        assert len(versions) == 4, "Each config should have a unique graph_version"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_semantic_flags")
class TestSettingsSemanticSearchFlags:
    """Tests for Settings semantic search configuration.

    NOTE: enable_semantic_*_search FEATURE TOGGLES have been migrated to FeatureFlags
    to eliminate duplication. Settings retains operational config like thresholds and limits.
    See test_feature_flags_settings_migration.py::TestDuplicateSettingsRemoved for validation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_semantic_tool_search_threshold(self, monkeypatch) -> None:
        """Settings should have semantic_tool_search_threshold (operational config)."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "semantic_tool_search_threshold")
        assert isinstance(settings.semantic_tool_search_threshold, float)

    def test_settings_has_max_selected_tools(self, monkeypatch) -> None:
        """Settings should have max_selected_tools (operational config)."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "max_selected_tools")
        assert isinstance(settings.max_selected_tools, int)

    def test_settings_has_max_selected_skills(self, monkeypatch) -> None:
        """Settings should have max_selected_skills (operational config)."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "max_selected_skills")
        assert isinstance(settings.max_selected_skills, int)
