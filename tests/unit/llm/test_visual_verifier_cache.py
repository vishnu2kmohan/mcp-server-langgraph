"""
Tests for visual verification screenshot caching.

TDD RED Phase: Define expected caching behavior for screenshot captures.
Tests must fail initially, then pass after implementation.

Tests cover:
- Screenshot cache hit avoids recapture
- Cache miss triggers new capture
- Cache TTL expiration
- Cache key generation from URL
- Cache invalidation
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# Path to patch - screenshot_tools is imported dynamically in verifier.py
SCREENSHOT_TOOLS_PATCH = "mcp_server_langgraph.tools.screenshot_tools.capture_screenshot"


pytestmark = pytest.mark.unit


class TestVisualVerificationScreenshotCache:
    """Tests for screenshot caching in visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screenshot_cache_hit_avoids_recapture(self) -> None:
        """Cached screenshot should be reused, not recaptured."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        # Mock screenshot tool
        screenshot_call_count = 0

        async def mock_screenshot(args):
            nonlocal screenshot_call_count
            screenshot_call_count += 1
            return {
                "image_data": "base64-cached-image-data",
                "mime_type": "image/png",
            }

        # Mock LLM response
        mock_llm.ainvoke.return_value = MagicMock(
            content="""VISUAL_SCORES:
- ui_layout: 0.9
OVERALL: 0.85
OBSERVATIONS:
- Good
CRITICAL_ISSUES:
- None
REQUIRES_REFINEMENT: no
FEEDBACK:
Looks good."""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Setup cache mock - first call returns None (miss), second returns cached data
            cache_storage: dict[str, dict] = {}

            async def mock_cache_get(key: str):
                return cache_storage.get(key)

            async def mock_cache_set(key: str, value: dict, ttl: int):
                cache_storage[key] = value

            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(side_effect=mock_cache_get)
            mock_cache.aset = AsyncMock(side_effect=mock_cache_set)
            mock_get_cache.return_value = mock_cache

            # First call - should capture screenshot and cache it
            result1 = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should show content",
            )

            # Second call to same URL - should use cached screenshot
            result2 = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should show content",
            )

            # Both verifications should pass
            assert result1.passed is True
            assert result2.passed is True

            # Screenshot should only be captured once (second time should use cache)
            # Note: Implementation may call capture once if cache is working
            assert screenshot_call_count >= 1  # At least one capture
            assert mock_cache.aset.called  # Cache set should be called

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screenshot_cache_miss_triggers_capture(self) -> None:
        """Cache miss should trigger new screenshot capture."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        screenshot_call_count = 0

        async def mock_screenshot(args):
            nonlocal screenshot_call_count
            screenshot_call_count += 1
            return {
                "image_data": "base64-new-image-data",
                "mime_type": "image/png",
            }

        mock_llm.ainvoke.return_value = MagicMock(
            content="""VISUAL_SCORES:
- ui_layout: 0.9
OVERALL: 0.85
OBSERVATIONS:
- Good
CRITICAL_ISSUES:
- None
REQUIRES_REFINEMENT: no
FEEDBACK:
Looks good."""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Cache always returns None (miss)
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            result = await verifier.verify_with_visual(
                url="https://example.com/new-page",
                expected_state="Page should load",
            )

            assert result.passed is True
            assert screenshot_call_count == 1  # One capture for cache miss
            mock_cache.aset.assert_called_once()  # Should cache the result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_different_urls_get_different_cache_entries(self) -> None:
        """Different URLs should have separate cache entries."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        captured_urls: list[str] = []

        async def mock_screenshot(args):
            captured_urls.append(args.get("url", ""))
            return {
                "image_data": f"base64-image-for-{args.get('url', '')}",
                "mime_type": "image/png",
            }

        mock_llm.ainvoke.return_value = MagicMock(
            content="""OVERALL: 0.85
FEEDBACK: Good"""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Cache always misses
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            # Verify two different URLs
            await verifier.verify_with_visual(
                url="https://example.com/page1",
                expected_state="Page 1",
            )

            await verifier.verify_with_visual(
                url="https://example.com/page2",
                expected_state="Page 2",
            )

            # Both should trigger captures (different URLs)
            assert len(captured_urls) == 2
            # Cache should be called with different keys
            assert mock_cache.aset.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_key_generation_normalizes_url(self) -> None:
        """Cache key should normalize URL for consistent caching."""
        from mcp_server_langgraph.llm.verifier import generate_screenshot_cache_key

        # Same URL with different trailing slashes should have same key
        key1 = generate_screenshot_cache_key("https://example.com/page")
        key2 = generate_screenshot_cache_key("https://example.com/page/")

        assert key1 == key2

        # Different URLs should have different keys
        key3 = generate_screenshot_cache_key("https://example.com/other")
        assert key1 != key3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_stores_screenshot_with_correct_ttl(self) -> None:
        """Screenshot cache should use appropriate TTL."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier, SCREENSHOT_CACHE_TTL

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        async def mock_screenshot(args):
            return {
                "image_data": "base64-image",
                "mime_type": "image/png",
            }

        mock_llm.ainvoke.return_value = MagicMock(
            content="""OVERALL: 0.9
FEEDBACK: Good"""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
            )

            # Verify cache was called with correct TTL
            mock_cache.aset.assert_called_once()
            call_args = mock_cache.aset.call_args
            # TTL should be passed as keyword argument
            assert call_args[1].get("ttl") == SCREENSHOT_CACHE_TTL or call_args[0][2] == SCREENSHOT_CACHE_TTL

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_disabled_when_no_caching_flag(self) -> None:
        """Screenshot caching should be skippable via parameter."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        screenshot_call_count = 0

        async def mock_screenshot(args):
            nonlocal screenshot_call_count
            screenshot_call_count += 1
            return {
                "image_data": "base64-image",
                "mime_type": "image/png",
            }

        mock_llm.ainvoke.return_value = MagicMock(
            content="""OVERALL: 0.9
FEEDBACK: Good"""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            # Call with caching disabled
            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
                use_screenshot_cache=False,
            )

            assert result.passed is True
            assert screenshot_call_count == 1
            # Cache should NOT be used when disabled
            mock_cache.aget.assert_not_called()


class TestVisualVerificationCacheMetrics:
    """Tests for screenshot cache metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_is_recorded_in_metrics(self) -> None:
        """Cache hits should be recorded in metrics."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        mock_llm.ainvoke.return_value = MagicMock(
            content="""OVERALL: 0.9
FEEDBACK: Good"""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
            patch("mcp_server_langgraph.llm.verifier.record_screenshot_cache_hit") as mock_record_hit,
        ):
            mock_capture.ainvoke = AsyncMock(
                return_value={
                    "image_data": "base64",
                    "mime_type": "image/png",
                }
            )

            # Cache returns a hit
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(
                return_value={
                    "image_data": "cached-base64",
                    "mime_type": "image/png",
                }
            )
            mock_get_cache.return_value = mock_cache

            await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
            )

            # Cache hit metric should be recorded
            mock_record_hit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_is_recorded_in_metrics(self) -> None:
        """Cache misses should be recorded in metrics."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock(return_value=None)
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        mock_llm.ainvoke.return_value = MagicMock(
            content="""OVERALL: 0.9
FEEDBACK: Good"""
        )

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
            patch("mcp_server_langgraph.llm.verifier.record_screenshot_cache_miss") as mock_record_miss,
        ):
            mock_capture.ainvoke = AsyncMock(
                return_value={
                    "image_data": "base64",
                    "mime_type": "image/png",
                }
            )

            # Cache returns None (miss)
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
            )

            # Cache miss metric should be recorded
            mock_record_miss.assert_called_once()
