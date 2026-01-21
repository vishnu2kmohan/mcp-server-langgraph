"""
Tests for feature flags migrated from settings.

TDD: These tests define expected behavior for settings that should be
feature flags (gradual rollout, kill switches, A/B testing).
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestVerificationFeatureFlags:
    """Tests for verification-related feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verification_enabled_flag_exists(self) -> None:
        """Verification enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "verification_enabled")

    def test_verification_enabled_default_true(self) -> None:
        """Verification should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.verification_enabled is True

    def test_visual_verification_enabled_flag_exists(self) -> None:
        """Visual verification enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "visual_verification_enabled")

    def test_visual_verification_disabled_by_default(self) -> None:
        """Visual verification should be disabled by default (experimental)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.visual_verification_enabled is False


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestContextFeatureFlags:
    """Tests for context-related feature flags."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_checkpointing_enabled_flag_exists(self) -> None:
        """Checkpointing enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "checkpointing_enabled")

    def test_checkpointing_enabled_by_default(self) -> None:
        """Checkpointing should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.checkpointing_enabled is True

    def test_context_compaction_enabled_flag_exists(self) -> None:
        """Context compaction enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "context_compaction_enabled")

    def test_context_compaction_enabled_by_default(self) -> None:
        """Context compaction should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_compaction_enabled is True

    def test_dynamic_context_loading_flag_exists(self) -> None:
        """Dynamic context loading should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "dynamic_context_loading_enabled")

    def test_dynamic_context_loading_disabled_by_default(self) -> None:
        """Dynamic context loading should be disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.dynamic_context_loading_enabled is False


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestExecutionFeatureFlags:
    """Tests for execution-related feature flags."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_parallel_tool_execution_flag_exists(self) -> None:
        """Parallel tool execution should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "parallel_tool_execution_enabled")

    def test_parallel_tool_execution_disabled_by_default(self) -> None:
        """Parallel tool execution should be disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.parallel_tool_execution_enabled is False

    def test_code_execution_enabled_flag_exists(self) -> None:
        """Code execution enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "code_execution_enabled")

    def test_code_execution_disabled_by_default(self) -> None:
        """Code execution should be disabled by default (security)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.code_execution_enabled is False

    def test_sandbox_tools_enabled_flag_exists(self) -> None:
        """Sandbox tools enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "sandbox_tools_enabled")

    def test_sandbox_tools_disabled_by_default(self) -> None:
        """Sandbox tools should be disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.sandbox_tools_enabled is False


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestModelFeatureFlags:
    """Tests for model-related feature flags."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_dedicated_summarization_model_flag_exists(self) -> None:
        """Dedicated summarization model should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "dedicated_summarization_model_enabled")

    def test_dedicated_summarization_model_enabled_by_default(self) -> None:
        """Dedicated summarization model should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.dedicated_summarization_model_enabled is True

    def test_dedicated_verification_model_flag_exists(self) -> None:
        """Dedicated verification model should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "dedicated_verification_model_enabled")

    def test_dedicated_verification_model_enabled_by_default(self) -> None:
        """Dedicated verification model should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.dedicated_verification_model_enabled is True

    def test_llm_extraction_flag_exists(self) -> None:
        """LLM extraction should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "llm_extraction_enabled")

    def test_llm_extraction_disabled_by_default(self) -> None:
        """LLM extraction should be disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.llm_extraction_enabled is False


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestStreamingFeatureFlags:
    """Tests for streaming-related feature flags.

    Note: streaming_enabled is ALSO in Settings for WebSocket bootstrap.
    Both locations are valid - Settings for infrastructure, FeatureFlags for feature control.
    """

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_streaming_enabled_flag_exists(self) -> None:
        """Streaming enabled should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "streaming_enabled")

    def test_streaming_enabled_by_default(self) -> None:
        """Streaming should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.streaming_enabled is True


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestArtifactsFeatureFlags:
    """Tests for artifacts-related feature flags."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_artifacts_semantic_search_flag_exists(self) -> None:
        """Artifacts semantic search should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "artifacts_semantic_search_enabled")

    def test_artifacts_semantic_search_enabled_by_default(self) -> None:
        """Artifacts semantic search should be enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.artifacts_semantic_search_enabled is True

    def test_artifacts_cloud_storage_flag_exists(self) -> None:
        """Artifacts cloud storage should be a feature flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "artifacts_cloud_storage_enabled")

    def test_artifacts_cloud_storage_disabled_by_default(self) -> None:
        """Artifacts cloud storage should be disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.artifacts_cloud_storage_enabled is False


@pytest.mark.xdist_group(name="feature_flags_migration")
class TestDuplicateSettingsRemoved:
    """Tests that duplicate settings are removed from Settings class."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_semantic_tool_search_not_in_settings(self) -> None:
        """enable_semantic_tool_search should only be in FeatureFlags."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        # This setting was duplicated - it should be removed from Settings
        # and only exist in FeatureFlags
        assert not hasattr(settings, "enable_semantic_tool_search")

    def test_semantic_skill_search_not_in_settings(self) -> None:
        """enable_semantic_skill_search should only be in FeatureFlags."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert not hasattr(settings, "enable_semantic_skill_search")

    def test_semantic_memory_search_not_in_settings(self) -> None:
        """enable_semantic_memory_search should only be in FeatureFlags."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert not hasattr(settings, "enable_semantic_memory_search")
