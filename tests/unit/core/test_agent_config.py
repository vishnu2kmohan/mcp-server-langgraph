"""
Tests for AgentConfig - Compile-Time Graph Composition.

TDD tests for the AgentConfig class that replaces runtime feature flag checks
with compile-time graph composition. This follows the Open/Closed Principle
by enabling graph topology changes without modifying node functions.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_config_creation")
class TestAgentConfigCreation:
    """Test AgentConfig instantiation and defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_import_agent_config(self):
        """AgentConfig should be importable from core.agent_config."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        assert AgentConfig is not None

    def test_default_values_are_sensible_for_production(self):
        """AgentConfig should have sensible defaults."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        # Context management defaults
        assert config.enable_context_compaction is True
        assert config.compaction_threshold == 8000
        assert config.target_after_compaction == 4000
        assert config.recent_message_count == 5

        # Verification defaults
        assert config.enable_verification is True
        assert config.verification_quality_threshold == 0.7
        assert config.max_refinement_attempts == 3

        # Dynamic context defaults
        assert config.enable_dynamic_context_loading is False

        # Parallel execution defaults
        assert config.enable_parallel_execution is False
        assert config.max_parallel_tools == 5

        # Checkpointing defaults
        assert config.enable_checkpointing is True

    def test_custom_values_override_defaults_correctly(self):
        """AgentConfig should accept custom values."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_context_compaction=False,
            enable_verification=False,
            enable_dynamic_context_loading=True,
            enable_parallel_execution=True,
            max_refinement_attempts=5,
        )

        assert config.enable_context_compaction is False
        assert config.enable_verification is False
        assert config.enable_dynamic_context_loading is True
        assert config.enable_parallel_execution is True
        assert config.max_refinement_attempts == 5


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_config_immutability")
class TestAgentConfigImmutability:
    """Test that AgentConfig is immutable (frozen dataclass)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_config_is_frozen(self):
        """AgentConfig should be immutable."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError is a subclass
            config.enable_verification = False  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_graph_versioning")
class TestGraphVersioning:
    """Test graph_version property for checkpoint compatibility."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_graph_version_is_string(self):
        """graph_version should return a string hash."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        version = config.graph_version

        assert isinstance(version, str)
        assert len(version) == 8  # Short hash prefix

    def test_graph_version_is_deterministic(self):
        """Same config should produce same graph_version."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config1 = AgentConfig()
        config2 = AgentConfig()

        assert config1.graph_version == config2.graph_version

    def test_graph_version_changes_with_topology(self):
        """Different topology-affecting configs should produce different versions."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config1 = AgentConfig(enable_verification=True)
        config2 = AgentConfig(enable_verification=False)

        assert config1.graph_version != config2.graph_version

    def test_graph_version_ignores_non_topology_fields(self):
        """Non-topology fields shouldn't affect graph_version."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config1 = AgentConfig(max_refinement_attempts=3)
        config2 = AgentConfig(max_refinement_attempts=10)

        # max_refinement_attempts doesn't change graph topology
        # (same nodes, just different behavior within verify node)
        assert config1.graph_version == config2.graph_version

    def test_graph_version_format(self):
        """graph_version should be a valid hex string."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        version = config.graph_version

        # Should be valid hex (no ValueError)
        int(version, 16)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_agent_config_from_settings")
class TestAgentConfigFromSettings:
    """Test creating AgentConfig from Settings object."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_from_settings_basic(self, monkeypatch):
        """AgentConfig.from_settings should extract relevant settings."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            enable_context_compaction=False,
            enable_verification=True,
            max_refinement_attempts=5,
        )

        config = AgentConfig.from_settings(settings)

        assert config.enable_context_compaction is False
        assert config.enable_verification is True
        assert config.max_refinement_attempts == 5

    def test_from_settings_all_fields(self, monkeypatch):
        """All relevant settings fields should be extracted."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            enable_context_compaction=True,
            compaction_threshold=10000,
            target_after_compaction=5000,
            recent_message_count=10,
            enable_verification=True,
            verification_quality_threshold=0.8,
            max_refinement_attempts=5,
            enable_dynamic_context_loading=True,
            enable_parallel_execution=True,
            max_parallel_tools=10,
            enable_checkpointing=False,
        )

        config = AgentConfig.from_settings(settings)

        assert config.compaction_threshold == 10000
        assert config.target_after_compaction == 5000
        assert config.recent_message_count == 10
        assert config.verification_quality_threshold == 0.8
        assert config.enable_dynamic_context_loading is True
        assert config.enable_parallel_execution is True
        assert config.max_parallel_tools == 10
        assert config.enable_checkpointing is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_topology_fields")
class TestTopologyFields:
    """Test that topology-affecting fields are correctly identified."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_topology_fields_property(self):
        """Should expose which fields affect graph topology."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        topology_fields = config.topology_fields

        # These fields affect graph structure (nodes/edges)
        expected_fields = {
            "enable_context_compaction",
            "enable_verification",
            "enable_dynamic_context_loading",
            "enable_checkpointing",
        }

        assert expected_fields.issubset(topology_fields)

    def test_non_topology_fields_excluded(self):
        """Behavior-only fields should not be in topology_fields."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()
        topology_fields = config.topology_fields

        # These fields only affect behavior within nodes, not graph structure
        non_topology_fields = {
            "max_refinement_attempts",
            "compaction_threshold",
            "verification_quality_threshold",
            "max_parallel_tools",
        }

        for field in non_topology_fields:
            assert field not in topology_fields, f"{field} should not affect topology"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_tool_selection_config")
class TestSemanticToolSelectionConfig:
    """Test semantic tool selection configuration fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_semantic_tool_selection_default_false(self):
        """enable_semantic_tool_selection should default to False."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        # Off by default for backwards compatibility
        assert hasattr(config, "enable_semantic_tool_selection")
        assert config.enable_semantic_tool_selection is False

    def test_max_selected_tools_default_value(self):
        """max_selected_tools should default to 10."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        assert hasattr(config, "max_selected_tools")
        assert config.max_selected_tools == 10

    def test_semantic_tool_search_threshold_default_value(self):
        """semantic_tool_search_threshold should default to 0.5."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        assert hasattr(config, "semantic_tool_search_threshold")
        assert config.semantic_tool_search_threshold == 0.5

    def test_enable_semantic_tool_selection_is_topology_field(self):
        """enable_semantic_tool_selection should affect graph topology."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        # Should be in topology fields (adds select_tools node)
        assert "enable_semantic_tool_selection" in config.topology_fields

    def test_semantic_tool_selection_changes_graph_version(self):
        """Enabling semantic tool selection should change graph version."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config_without = AgentConfig(enable_semantic_tool_selection=False)
        config_with = AgentConfig(enable_semantic_tool_selection=True)

        # Different topology = different graph version
        assert config_without.graph_version != config_with.graph_version

    def test_max_selected_tools_does_not_affect_topology(self):
        """max_selected_tools should not affect graph topology."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config1 = AgentConfig(max_selected_tools=5)
        config2 = AgentConfig(max_selected_tools=20)

        # Same topology (behavior-only field)
        assert config1.graph_version == config2.graph_version

    def test_semantic_tool_selection_from_settings(self, monkeypatch):
        """AgentConfig.from_settings should extract semantic tool selection fields."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            enable_semantic_tool_selection=True,
            max_selected_tools=15,
            semantic_tool_search_threshold=0.7,
        )

        config = AgentConfig.from_settings(settings)

        assert config.enable_semantic_tool_selection is True
        assert config.max_selected_tools == 15
        assert config.semantic_tool_search_threshold == 0.7
