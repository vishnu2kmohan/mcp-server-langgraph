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

pytestmark = [pytest.mark.unit, pytest.mark.bootstrap]


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
        with patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff:
            mock_ff.enable_semantic_tool_search = False
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False
            mock_ff.enable_message_embedding = False  # v8: Added for session similarity

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
        mock_manager.ensure_collection = AsyncMock(side_effect=lambda *a, **kw: None)
        mock_qdrant = AsyncMock(return_value=None)
        mock_embedder = MagicMock()

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
                side_effect=lambda *a, **kw: mock_qdrant,
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
                side_effect=lambda *a, **kw: mock_embedder,
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager",
            ),
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
        mock_manager.ensure_collection = AsyncMock(side_effect=lambda *a, **kw: None)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager") as mock_setter,
        ):
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
        mock_manager.warm_cache = AsyncMock(side_effect=lambda *a, **kw: 1)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"),
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic

            await init_semantic(mock_settings)

            mock_manager.warm_cache.assert_called_once_with(mock_settings.auth_cache_warm_entries)

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
        mock_manager.warm_cache = AsyncMock(side_effect=lambda *a, **kw: 0)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"),
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


class TestSemanticBootstrapSplit:
    """Tests for split init_semantic_manager() and index_all_tools() (v26)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_semantic_manager_exists(self) -> None:
        """init_semantic_manager function should exist."""
        from mcp_server_langgraph.bootstrap.semantic import init_semantic_manager

        assert callable(init_semantic_manager)

    def test_index_all_tools_exists(self) -> None:
        """index_all_tools function should exist."""
        from mcp_server_langgraph.bootstrap.semantic import index_all_tools

        assert callable(index_all_tools)

    @pytest.mark.asyncio
    async def test_init_semantic_manager_creates_manager_without_indexing(self) -> None:
        """init_semantic_manager should create manager but NOT index tools."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.qdrant_url = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_provider = "local"
        mock_settings.embedding_model_name = "all-MiniLM-L6-v2"
        mock_settings.embedding_dimensions = 384
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.ensure_collection = AsyncMock(side_effect=lambda *a, **kw: None)
        mock_manager.index_tools_batch = AsyncMock(side_effect=lambda *a, **kw: None)

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "qdrant_client.AsyncQdrantClient",
            ),
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader._create_embeddings",
            ),
            patch(
                "mcp_server_langgraph.core.semantic_index_manager.SemanticIndexManager",
                side_effect=lambda *a, **kw: mock_manager,
            ),
            patch("mcp_server_langgraph.bootstrap.semantic.set_semantic_index_manager"),
        ):
            mock_ff.enable_semantic_tool_search = True
            mock_ff.enable_semantic_skill_search = False
            mock_ff.enable_semantic_memory_search = False
            mock_ff.enable_message_embedding = False

            from mcp_server_langgraph.bootstrap.semantic import init_semantic_manager

            result = await init_semantic_manager(mock_settings)

            assert result is not None
            assert result.manager is mock_manager
            # index_tools_batch should NOT be called during init_semantic_manager
            mock_manager.index_tools_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_all_tools_uses_registry(self) -> None:
        """index_all_tools should use get_tool_registry().get_all()."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.index_tools_batch = AsyncMock(side_effect=lambda *a, **kw: None)

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.args_schema = None

        mock_reg = RegisteredTool(
            tool_id="builtin:test_tool",
            name="test_tool",
            qualified_name="test_tool",
            source="builtin",
            display_name="Test Tool",
            description="Test tool",
            category="test",
            tool=mock_tool,
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_reg]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda: mock_registry,
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            await index_all_tools()

            mock_registry.get_all.assert_called_once()
            mock_manager.index_tools_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_all_tools_skips_native_tools(self) -> None:
        """index_all_tools should skip native tools (source='native')."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.index_tools_batch = AsyncMock(side_effect=lambda *a, **kw: None)

        # Native tool (should be skipped)
        native_reg = RegisteredTool(
            tool_id=None,  # Native tools have None tool_id
            name="code_execution",
            qualified_name="code_execution",
            source="native",
            display_name="Code Execution",
            description="Native code execution",
            category="execution",
            tool=None,  # Native tools have None tool
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [native_reg]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda: mock_registry,
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            await index_all_tools()

            # index_tools_batch should NOT be called (empty list)
            mock_manager.index_tools_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_all_tools_raises_for_non_native_missing_tool_id(self) -> None:
        """index_all_tools should raise ValueError for non-native tools with tool_id=None."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        mock_manager = AsyncMock()  # noqa: async-mock-config

        mock_tool = MagicMock()
        mock_tool.name = "bad_tool"

        # Non-native tool with missing tool_id (v26: should raise)
        bad_reg = RegisteredTool(
            tool_id=None,  # BUG: non-native shouldn't have None
            name="bad_tool",
            qualified_name="bad_tool",
            source="builtin",  # Non-native
            display_name="Bad Tool",
            description="Bad tool",
            category="test",
            tool=mock_tool,
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [bad_reg]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda: mock_registry,
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            with pytest.raises(ValueError, match="has tool_id=None"):
                await index_all_tools()

    @pytest.mark.asyncio
    async def test_index_all_tools_raises_for_non_native_missing_tool(self) -> None:
        """index_all_tools should raise ValueError for non-native tools with tool=None."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        mock_manager = AsyncMock()  # noqa: async-mock-config

        # Non-native tool with missing BaseTool (v26: should raise)
        bad_reg = RegisteredTool(
            tool_id="builtin:bad_tool",
            name="bad_tool",
            qualified_name="bad_tool",
            source="builtin",  # Non-native
            display_name="Bad Tool",
            description="Bad tool",
            category="test",
            tool=None,  # BUG: non-native shouldn't have None
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [bad_reg]

        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda: mock_manager,
            ),
            patch(
                "mcp_server_langgraph.tools.unified_registry.get_tool_registry",
                side_effect=lambda: mock_registry,
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            with pytest.raises(ValueError, match="has tool=None"):
                await index_all_tools()

    @pytest.mark.asyncio
    async def test_index_all_tools_handles_no_manager_gracefully(self) -> None:
        """index_all_tools should return early if no manager."""
        with (
            patch("mcp_server_langgraph.bootstrap.semantic.feature_flags") as mock_ff,
            patch(
                "mcp_server_langgraph.bootstrap.semantic.get_semantic_index_manager",
                side_effect=lambda: None,
            ),
        ):
            mock_ff.enable_semantic_tool_search = True

            from mcp_server_langgraph.bootstrap.semantic import index_all_tools

            # Should not raise, just return early
            await index_all_tools()
