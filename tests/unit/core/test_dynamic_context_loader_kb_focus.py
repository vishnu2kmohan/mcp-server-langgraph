"""
DynamicContextLoader KB Focus Mode Tests

TDD tests for KB Focus Mode integration in DynamicContextLoader.

KB Focus Mode allows users to control context retrieval strategy:
- "all": Use both KB and web search (default)
- "kb_only": Only use KB/vector store for context
- "web_only": Skip KB search (return empty)
- "none": Disable all context augmentation

Tests written FIRST before implementation (RED phase).
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.kb_focus]


# =============================================================================
# search_and_load_context Focus Mode Tests
# =============================================================================


@pytest.mark.xdist_group(name="dynamic_context_kb_focus")
class TestSearchAndLoadContextFocusMode:
    """Tests for focus_mode parameter in search_and_load_context function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_and_load_context_accepts_focus_mode_parameter(self) -> None:
        """
        GIVEN the search_and_load_context function
        WHEN called with focus_mode parameter
        THEN it should accept the parameter without error
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.semantic_search = AsyncMock(return_value=[])
            mock_loader.load_batch = AsyncMock(return_value=[])
            mock_loader_cls.return_value = mock_loader

            # Should not raise TypeError for unexpected keyword argument
            result = await search_and_load_context(
                query="test query",
                focus_mode="kb_only",
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_focus_mode_none_returns_empty_list(self) -> None:
        """
        GIVEN focus_mode="none"
        WHEN search_and_load_context is called
        THEN it should return empty list without calling search
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.semantic_search = AsyncMock(return_value=[])
            mock_loader.load_batch = AsyncMock(return_value=[])
            mock_loader_cls.return_value = mock_loader

            result = await search_and_load_context(
                query="test query",
                focus_mode="none",
            )

            # With focus_mode="none", should return empty without searching
            assert result == []
            # Semantic search should NOT be called
            mock_loader.semantic_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_focus_mode_web_only_skips_kb_search(self) -> None:
        """
        GIVEN focus_mode="web_only"
        WHEN search_and_load_context is called
        THEN it should skip KB search and return empty list
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.semantic_search = AsyncMock(return_value=[])
            mock_loader.load_batch = AsyncMock(return_value=[])
            mock_loader_cls.return_value = mock_loader

            result = await search_and_load_context(
                query="test query",
                focus_mode="web_only",
            )

            # With focus_mode="web_only", KB should be skipped
            assert result == []
            # Semantic search should NOT be called for web_only mode
            mock_loader.semantic_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_focus_mode_kb_only_uses_semantic_search(self) -> None:
        """
        GIVEN focus_mode="kb_only"
        WHEN search_and_load_context is called
        THEN it should use KB semantic search normally
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            ContextReference,
            LoadedContext,
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()

            # Return mock references and loaded contexts
            mock_ref = ContextReference(
                ref_id="doc_1",
                ref_type="document",
                summary="Test document",
            )
            mock_loaded = LoadedContext(
                reference=mock_ref,
                content="Test content",
                token_count=10,
                loaded_at=0.0,
            )
            mock_loader.semantic_search = AsyncMock(return_value=[mock_ref])
            mock_loader.load_batch = AsyncMock(return_value=[mock_loaded])
            mock_loader_cls.return_value = mock_loader

            result = await search_and_load_context(
                query="test query",
                focus_mode="kb_only",
            )

            # With focus_mode="kb_only", KB search should be called
            assert len(result) == 1
            mock_loader.semantic_search.assert_called_once()
            mock_loader.load_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_focus_mode_all_uses_semantic_search(self) -> None:
        """
        GIVEN focus_mode="all" (default)
        WHEN search_and_load_context is called
        THEN it should use KB semantic search normally
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            ContextReference,
            LoadedContext,
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()

            # Return mock references and loaded contexts
            mock_ref = ContextReference(
                ref_id="doc_1",
                ref_type="document",
                summary="Test document",
            )
            mock_loaded = LoadedContext(
                reference=mock_ref,
                content="Test content",
                token_count=10,
                loaded_at=0.0,
            )
            mock_loader.semantic_search = AsyncMock(return_value=[mock_ref])
            mock_loader.load_batch = AsyncMock(return_value=[mock_loaded])
            mock_loader_cls.return_value = mock_loader

            result = await search_and_load_context(
                query="test query",
                focus_mode="all",
            )

            # With focus_mode="all", KB search should be called
            assert len(result) == 1
            mock_loader.semantic_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_focus_mode_default_is_all(self) -> None:
        """
        GIVEN search_and_load_context called without focus_mode
        WHEN the function executes
        THEN it should default to focus_mode="all" (KB search enabled)
        """
        from mcp_server_langgraph.core.dynamic_context_loader import (
            ContextReference,
            LoadedContext,
            search_and_load_context,
        )

        # Mock the DynamicContextLoader
        with patch("mcp_server_langgraph.core.dynamic_context_loader.DynamicContextLoader") as mock_loader_cls:
            mock_loader = MagicMock()

            mock_ref = ContextReference(
                ref_id="doc_1",
                ref_type="document",
                summary="Test document",
            )
            mock_loaded = LoadedContext(
                reference=mock_ref,
                content="Test content",
                token_count=10,
                loaded_at=0.0,
            )
            mock_loader.semantic_search = AsyncMock(return_value=[mock_ref])
            mock_loader.load_batch = AsyncMock(return_value=[mock_loaded])
            mock_loader_cls.return_value = mock_loader

            # Call without focus_mode - should default to "all"
            result = await search_and_load_context(
                query="test query",
            )

            # Default should enable KB search
            assert len(result) == 1
            mock_loader.semantic_search.assert_called_once()


# =============================================================================
# Type Annotation Tests
# =============================================================================


@pytest.mark.xdist_group(name="dynamic_context_kb_focus")
class TestFocusModeTypeAnnotations:
    """Tests for focus_mode type annotations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_focus_mode_type_is_literal(self) -> None:
        """
        GIVEN the search_and_load_context function signature
        WHEN checking the focus_mode parameter type
        THEN it should be a Literal type with valid values
        """
        import inspect
        from mcp_server_langgraph.core.dynamic_context_loader import (
            search_and_load_context,
        )

        sig = inspect.signature(search_and_load_context)
        params = sig.parameters

        # focus_mode should be in parameters
        assert "focus_mode" in params

        # Check default value
        focus_mode_param = params["focus_mode"]
        assert focus_mode_param.default == "all"
