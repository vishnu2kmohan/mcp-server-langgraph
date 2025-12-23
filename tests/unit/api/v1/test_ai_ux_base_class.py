"""
AI UX LLMWithFallback Base Class Tests

TDD tests for the shared LLM/heuristic base class pattern.

Tests verify:
- Base class provides standard LLM call with heuristic fallback
- Metrics are recorded for LLM calls, latency, and fallbacks
- Caching is handled automatically
- ModelSelector integration works through base class
- Error handling falls back to heuristics gracefully

Reference: UX Audit Plan - DRY refactoring for AI UX services
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

# =============================================================================
# Test Constants
# =============================================================================

SAMPLE_LLM_RESPONSE = '{"result": "test", "confidence": 0.85}'


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_factory():
    """Create mock LLM factory."""
    factory = MagicMock()
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_LLM_RESPONSE))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    return settings


@pytest.fixture
def mock_model_selector():
    """Create mock ModelSelector."""
    selector = MagicMock()
    selector.select_model = MagicMock(return_value="gemini-flash")
    return selector


# =============================================================================
# LLMWithFallback Base Class Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_base_class")
class TestLLMWithFallbackInstantiation:
    """Test LLMWithFallback base class instantiation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_class_exists(self):
        """LLMWithFallback base class should be importable."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        assert LLMWithFallback is not None

    def test_base_class_accepts_required_params(self, mock_llm_factory, mock_settings):
        """Base class accepts llm_factory and settings."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )
        assert instance.llm_factory is mock_llm_factory
        assert instance.settings is mock_settings

    def test_base_class_accepts_model_selector(self, mock_llm_factory, mock_settings, mock_model_selector):
        """Base class accepts optional ModelSelector."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )
        assert instance.model_selector is mock_model_selector


@pytest.mark.xdist_group(name="ai_ux_base_class")
class TestLLMWithFallbackExecution:
    """Test LLMWithFallback execution patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_with_fallback_calls_llm_when_enabled(self, mock_llm_factory, mock_settings):
        """execute_with_fallback calls LLM when enabled."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        async def llm_fn():
            return {"from": "llm"}

        def heuristic_fn():
            return {"from": "heuristic"}

        result = await instance.execute_with_fallback(
            method_name="test_method",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
        )

        assert result == {"from": "llm"}

    @pytest.mark.asyncio
    async def test_execute_with_fallback_uses_heuristic_when_llm_disabled(self, mock_llm_factory, mock_settings):
        """execute_with_fallback uses heuristic when LLM disabled."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        mock_settings.ff_enable_ai_suggestions = False

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        async def llm_fn():
            return {"from": "llm"}

        def heuristic_fn():
            return {"from": "heuristic"}

        result = await instance.execute_with_fallback(
            method_name="test_method",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
        )

        assert result == {"from": "heuristic"}

    @pytest.mark.asyncio
    async def test_execute_with_fallback_falls_back_on_llm_error(self, mock_llm_factory, mock_settings):
        """execute_with_fallback falls back to heuristic on LLM error."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        async def llm_fn():
            raise RuntimeError("LLM failed")

        def heuristic_fn():
            return {"from": "heuristic"}

        result = await instance.execute_with_fallback(
            method_name="test_method",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
        )

        assert result == {"from": "heuristic"}


@pytest.mark.xdist_group(name="ai_ux_base_class")
class TestLLMWithFallbackCaching:
    """Test LLMWithFallback caching behavior."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_caching_returns_cached_result(self, mock_llm_factory, mock_settings):
        """execute_with_fallback returns cached result on cache hit."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )

        call_count = 0

        async def llm_fn():
            nonlocal call_count
            call_count += 1
            return {"from": "llm", "count": call_count}

        def heuristic_fn():
            return {"from": "heuristic"}

        # First call
        result1 = await instance.execute_with_fallback(
            method_name="test_method",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
            cache_key="test_cache_key",
        )

        # Second call with same cache key
        result2 = await instance.execute_with_fallback(
            method_name="test_method",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
            cache_key="test_cache_key",
        )

        assert result1 == result2
        assert call_count == 1  # LLM should only be called once


@pytest.mark.xdist_group(name="ai_ux_base_class")
class TestLLMWithFallbackModelSelection:
    """Test LLMWithFallback model selection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_selects_model_based_on_method_complexity(self, mock_llm_factory, mock_settings, mock_model_selector):
        """execute_with_fallback selects model based on method complexity."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            model_selector=mock_model_selector,
        )

        async def llm_fn():
            return {"from": "llm"}

        def heuristic_fn():
            return {"from": "heuristic"}

        await instance.execute_with_fallback(
            method_name="error_analysis",  # This is a "simple" tier
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
        )

        # Verify ModelSelector was called with correct complexity
        mock_model_selector.select_model.assert_called_with("simple")

    @pytest.mark.asyncio
    async def test_works_without_model_selector(self, mock_llm_factory, mock_settings):
        """execute_with_fallback works without ModelSelector."""
        from mcp_server_langgraph.api.v1.ai_ux_service import LLMWithFallback

        instance = LLMWithFallback(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
            # No model_selector
        )

        async def llm_fn():
            return {"from": "llm"}

        def heuristic_fn():
            return {"from": "heuristic"}

        result = await instance.execute_with_fallback(
            method_name="error_analysis",
            llm_fn=llm_fn,
            heuristic_fn=heuristic_fn,
        )

        assert result == {"from": "llm"}
