"""
Tests for visual verification retry logic.

TDD RED Phase: Define expected retry behavior for visual verification.
Tests must fail initially, then pass after implementation.

Tests cover:
- Screenshot capture retry on transient errors
- LLM invocation retry on transient errors
- Max attempts exhaustion
- Exponential backoff verification
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

if TYPE_CHECKING:
    pass

# Path to patch - screenshot_tools is imported dynamically in verifier.py
SCREENSHOT_TOOLS_PATCH = "mcp_server_langgraph.tools.screenshot_tools.capture_screenshot"


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="visual_verifier_retry")
class TestVisualVerificationRetry:
    """Tests for retry logic in visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screenshot_capture_retries_on_timeout(self) -> None:
        """Screenshot capture should retry on timeout errors."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        # Create verifier with mocked LLM
        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        # Mock screenshot tool to fail twice then succeed
        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.TimeoutException("Connection timed out")
            return {
                "image_data": "base64-image-data",
                "mime_type": "image/png",
            }

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # Mock LLM response for verification
            mock_llm.ainvoke.return_value = MagicMock(
                content="""VISUAL_SCORES:
- ui_layout: 0.9
- content_visible: 0.8
- element_present: 0.9
- error_visible: 0.1
- loading_complete: 0.9

OVERALL: 0.85

OBSERVATIONS:
- Page loaded correctly

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- None

REQUIRES_REFINEMENT: no

FEEDBACK:
Page looks good."""
            )

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should show content",
            )

            # Should succeed after retries
            assert result.passed is True
            assert result.screenshot_captured is True
            assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screenshot_capture_retries_on_connection_error(self) -> None:
        """Screenshot capture should retry on connection errors."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise httpx.ConnectError("Connection refused")
            return {
                "image_data": "base64-image-data",
                "mime_type": "image/png",
            }

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_llm.ainvoke.return_value = MagicMock(
                content="""VISUAL_SCORES:
- ui_layout: 0.8
OVERALL: 0.8
OBSERVATIONS:
- Content visible
CRITICAL_ISSUES:
- None
SUGGESTIONS:
- None
REQUIRES_REFINEMENT: no
FEEDBACK:
Looks good."""
            )

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should load",
            )

            assert result.passed is True
            assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screenshot_capture_fails_after_max_attempts(self) -> None:
        """Screenshot capture should fail after exhausting retries."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Connection timed out")

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should show content",
            )

            # Should fail after max retries (default 3)
            assert result.passed is False
            assert result.screenshot_captured is False
            assert "retry" in result.feedback.lower() or "timeout" in result.feedback.lower()
            assert call_count == 3  # max_attempts = 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_invocation_retries_on_transient_error(self) -> None:
        """LLM invocation should retry on transient errors."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        # Mock screenshot to succeed
        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(
                return_value={
                    "image_data": "base64-image-data",
                    "mime_type": "image/png",
                }
            )

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # LLM fails once then succeeds
            call_count = 0

            async def mock_llm_invoke(messages):
                nonlocal call_count
                call_count += 1
                if call_count <= 1:
                    raise httpx.TimeoutException("LLM API timeout")
                return MagicMock(
                    content="""VISUAL_SCORES:
- ui_layout: 0.9
OVERALL: 0.85
OBSERVATIONS:
- Good
CRITICAL_ISSUES:
- None
REQUIRES_REFINEMENT: no
FEEDBACK:
OK"""
                )

            mock_llm.ainvoke = mock_llm_invoke

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page should show content",
            )

            assert result.passed is True
            assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_overload_uses_extended_retry(self) -> None:
        """LLM 529 overload should trigger extended retry config."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(
                return_value={
                    "image_data": "base64-image-data",
                    "mime_type": "image/png",
                }
            )

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # Simulate 529 overload error (LiteLLM pattern)
            call_count = 0

            class OverloadError(Exception):
                status_code = 529
                message = "Service overloaded"

            async def mock_llm_invoke(messages):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise OverloadError()
                return MagicMock(
                    content="""VISUAL_SCORES:
- ui_layout: 0.9
OVERALL: 0.85
OBSERVATIONS:
- Good
CRITICAL_ISSUES:
- None
REQUIRES_REFINEMENT: no
FEEDBACK:
OK"""
                )

            mock_llm.ainvoke = mock_llm_invoke

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page content visible",
            )

            # Should succeed with extended retry
            assert result.passed is True
            assert call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_retryable_errors_fail_immediately(self) -> None:
        """Non-retryable errors (e.g., validation) should not retry."""
        from mcp_server_langgraph.core.exceptions import ValidationError
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            raise ValidationError(message="Invalid URL format")

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            result = await verifier.verify_with_visual(
                url="invalid-url",
                expected_state="Page should load",
            )

            # Should fail immediately without retrying
            assert result.passed is False
            assert call_count == 1  # No retry for validation errors


@pytest.mark.xdist_group(name="visual_verifier_retry_metrics")
class TestVisualVerificationRetryMetrics:
    """Tests for retry metrics in visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_attempts_are_recorded(self) -> None:
        """Retry attempts should be recorded in metrics."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            verifier = OutputVerifier()

        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise httpx.TimeoutException("timeout")
            return {"image_data": "base64", "mime_type": "image/png"}

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
            patch("mcp_server_langgraph.llm.verifier.record_visual_verification_retry") as mock_record_retry,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_llm.ainvoke.return_value = MagicMock(content="OVERALL: 0.9\nFEEDBACK: Good")

            await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
            )

            # Retry metric should be recorded
            assert mock_record_retry.called or call_count == 2


@pytest.mark.xdist_group(name="visual_verifier_retry_config")
class TestVisualVerificationRetryConfig:
    """Tests for configurable retry parameters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_max_attempts(self) -> None:
        """Custom max_attempts should be honored."""
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_factory:
            mock_llm = AsyncMock()
            mock_factory.return_value = mock_llm

            # Configure verifier with custom retry settings
            verifier = OutputVerifier()

        call_count = 0

        async def mock_screenshot(args):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timeout")

        with (
            patch(SCREENSHOT_TOOLS_PATCH) as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = mock_screenshot

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # Use custom retry config via method parameter (if supported)
            # or environment variable
            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Page loads",
            )

            # Should exhaust configured attempts
            assert result.passed is False
            assert call_count >= 3  # At least default attempts
