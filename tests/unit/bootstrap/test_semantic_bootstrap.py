"""
Tests for Semantic Index Bootstrap Module.

TDD tests for:
1. SemanticIndexManager instantiation during bootstrap
2. set_semantic_index_manager() invocation
3. warm_semantic_cache() integration
4. Feature flag guard

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will create bootstrap/semantic.py.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.bootstrap, pytest.mark.adr0099]


@pytest.mark.xdist_group(name="semantic_bootstrap")
class TestSemanticBootstrapModule:
    """Tests for semantic bootstrap module existence and interface."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_bootstrap_module_exists(self) -> None:
        """bootstrap.semantic module should exist."""
        from mcp_server_langgraph.bootstrap import semantic

        assert semantic is not None

    def test_init_semantic_function_exists(self) -> None:
        """init_semantic function should exist in bootstrap.semantic."""
        from mcp_server_langgraph.bootstrap.semantic import init_semantic

        assert callable(init_semantic)

    def test_semantic_state_dataclass_exists(self) -> None:
        """SemanticState dataclass should exist in bootstrap.semantic."""
        from mcp_server_langgraph.bootstrap.semantic import SemanticState

        assert SemanticState is not None

    def test_semantic_state_has_manager_field(self) -> None:
        """SemanticState should have manager field."""
        from mcp_server_langgraph.bootstrap.semantic import SemanticState

        state = SemanticState()
        assert hasattr(state, "manager")

    def test_semantic_state_has_cleanup_method(self) -> None:
        """SemanticState should have async cleanup method."""
        from mcp_server_langgraph.bootstrap.semantic import SemanticState

        state = SemanticState()
        assert hasattr(state, "cleanup")
        # Verify it's callable (async method)
        import inspect
        assert inspect.iscoroutinefunction(state.cleanup)


@pytest.mark.xdist_group(name="semantic_bootstrap")
class TestSemanticBootstrapInitialization:
    """Tests for semantic bootstrap initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_semantic_returns_none_when_disabled(self) -> None:
        """init_semantic should return None when semantic search is disabled."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)

        # Disable all semantic search feature flags
        with patch(
            "mcp_server_langgraph.bootstrap.semantic.feature_flags"
        ) as mock_ff:
            mock_ff.enable_semantic_tool_search = False
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            result = await init_semantic(mock_settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_init_semantic_creates_manager_when_enabled(self) -> None:
        """init_semantic should create SemanticIndexManager when enabled."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)
        mock_qdrant = AsyncMock(return_value=None)
        mock_embedder = MagicMock()

        with patch(
            "mcp_server_langgraph.bootstrap.semantic.feature_flags"
        ) as mock_ff, patch(
            "qdrant_client.AsyncQdrantClient",
            return_value=mock_qdrant,
        ), patch(
            "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            return_value=mock_embedder,
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
            return_value=mock_manager,
        ), patch(
            "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            result = await init_semantic(mock_settings)

            assert result is not None
            assert result.manager is mock_manager


@pytest.mark.xdist_group(name="semantic_bootstrap")
class TestSemanticBootstrapSingletonWiring:
    """Tests for singleton wiring during bootstrap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_semantic_calls_set_semantic_index_manager(self) -> None:
        """init_semantic should call set_semantic_index_manager() with manager."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.ensure_collection = AsyncMock(return_value=None)

        with patch(
            "mcp_server_langgraph.bootstrap.semantic.feature_flags"
        ) as mock_ff, patch(
            "qdrant_client.AsyncQdrantClient",
        ), patch(
            "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
            return_value=mock_manager,
        ), patch(
            "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"
        ) as mock_setter:
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            mock_setter.assert_called_once_with(mock_manager)


@pytest.mark.xdist_group(name="semantic_bootstrap")
class TestSemanticBootstrapCacheWarming:
    """Tests for cache warming during bootstrap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_semantic_calls_warm_cache_when_entries_configured(self) -> None:
        """init_semantic should warm cache when entries are configured."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = [
            {"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"},
        ]

        mock_manager = AsyncMock(return_value=None)
        mock_manager.warm_cache = AsyncMock(return_value=1)

        with patch(
            "mcp_server_langgraph.bootstrap.semantic.feature_flags"
        ) as mock_ff, patch(
            "qdrant_client.AsyncQdrantClient",
        ), patch(
            "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
            return_value=mock_manager,
        ), patch(
            "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            mock_manager.warm_cache.assert_called_once_with(
                mock_settings.auth_cache_warm_entries
            )

    @pytest.mark.asyncio
    async def test_init_semantic_skips_warm_cache_when_no_entries(self) -> None:
        """init_semantic should skip cache warming when no entries configured."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []  # Empty

        mock_manager = AsyncMock(return_value=None)
        mock_manager.warm_cache = AsyncMock(return_value=0)

        with patch(
            "mcp_server_langgraph.bootstrap.semantic.feature_flags"
        ) as mock_ff, patch(
            "qdrant_client.AsyncQdrantClient",
        ), patch(
            "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
        ), patch(
            "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
            return_value=mock_manager,
        ), patch(
            "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            # warm_cache should NOT be called with empty list
            mock_manager.warm_cache.assert_not_called()


@pytest.mark.xdist_group(name="semantic_bootstrap")
class TestSemanticBootstrapIntegration:
    """Tests for integration with bootstrap_all()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_semantic_state_in_app_state(self) -> None:
        """AppState should have semantic field."""
        from mcp_server_langgraph.bootstrap import AppState

        app_state = AppState()
        assert hasattr(app_state, "semantic")

    def test_init_semantic_exported_from_bootstrap(self) -> None:
        """init_semantic should be exported from bootstrap package."""
        from mcp_server_langgraph.bootstrap import init_semantic

        assert callable(init_semantic)

    def test_semantic_state_exported_from_bootstrap(self) -> None:
        """SemanticState should be exported from bootstrap package."""
        from mcp_server_langgraph.bootstrap import SemanticState

        assert SemanticState is not None
