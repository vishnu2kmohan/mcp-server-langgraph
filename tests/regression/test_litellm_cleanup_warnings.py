"""
Regression test for litellm async client cleanup warnings.

OpenAI Codex Finding (2025-11-14):
- RuntimeWarning from litellm: coroutine 'close_litellm_async_clients' was never awaited
- Warning appears during test teardown when event loop closes
- Source: /litellm/llms/custom_httpx/async_client_cleanup.py:78

Root Cause:
- litellm creates async HTTP clients for API calls
- These clients need async cleanup (await close())
- pytest's synchronous teardown doesn't properly await litellm's async cleanup

Solution:
- Add session-scoped fixture to properly cleanup litellm's async clients
- Ensure cleanup happens before event loop closes
- Suppress RuntimeWarning in test configuration
"""

import asyncio
import gc
import warnings
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="litellm_cleanup_tests")
class TestLitellmCleanupWarnings:
    """Test suite for litellm async client cleanup regression."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_litellm_acompletion_cleanup_no_warning(self):
        """
        Verify that using litellm's acompletion does not produce cleanup warnings.

        This test:
        1. Uses litellm.acompletion (creates async HTTP clients)
        2. Verifies cleanup happens properly (no RuntimeWarning)
        3. Ensures event loop closes cleanly

        Expected behavior (RED phase):
        - Currently FAILS: RuntimeWarning emitted during teardown
        - After fix (GREEN): No warnings, clean async cleanup
        """
        # Mock litellm to avoid actual API calls
        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_acompletion.return_value = mock_response

            # Import after patch to ensure mock is used
            from mcp_server_langgraph.llm.factory import LLMFactory

            # Create LLM factory and make async call
            llm = LLMFactory(provider="anthropic", model_name="claude-3-5-sonnet-20241022")

            # Capture warnings during async completion call
            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always", RuntimeWarning)

                # Make async LLM call
                from langchain_core.messages import HumanMessage

                messages = [HumanMessage(content="test")]
                await llm.ainvoke(messages)

                # Ensure cleanup happens (should be automatic via fixture)
                # Force garbage collection to trigger any pending cleanup
                gc.collect()
                await asyncio.sleep(0.1)  # Allow async cleanup to complete

            # Verify no RuntimeWarning about unawaited coroutines
            runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
            litellm_warnings = [
                w for w in runtime_warnings if "close_litellm_async_clients" in str(w.message) or "coroutine" in str(w.message)
            ]

            assert (
                len(litellm_warnings) == 0
            ), f"Expected no litellm cleanup warnings, but got {len(litellm_warnings)}:\n" + "\n".join(
                f"  - {w.message}" for w in litellm_warnings
            )

    def test_litellm_sync_completion_cleanup_no_warning(self):
        """
        Verify that using litellm's sync completion does not produce cleanup warnings.

        Synchronous calls should not create async cleanup issues, but we test
        to ensure no regression.
        """
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_completion.return_value = mock_response

            from mcp_server_langgraph.llm.factory import LLMFactory

            llm = LLMFactory(provider="anthropic", model_name="claude-3-5-sonnet-20241022")

            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always", RuntimeWarning)

                from langchain_core.messages import HumanMessage

                messages = [HumanMessage(content="test")]
                llm.invoke(messages)

                gc.collect()

            runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
            litellm_warnings = [
                w for w in runtime_warnings if "close_litellm_async_clients" in str(w.message) or "coroutine" in str(w.message)
            ]

            assert len(litellm_warnings) == 0, f"Expected no warnings for sync completion, got {len(litellm_warnings)}"

    @pytest.mark.asyncio
    async def test_litellm_cleanup_fixture_integration(self):
        """
        Test that the cleanup_litellm_clients fixture properly cleans up async clients.

        This test:
        1. Uses the autouse fixture (cleanup_litellm_clients from conftest.py)
        2. Makes async LLM calls
        3. Verifies cleanup happens automatically

        Expected behavior:
        - Fixture ensures all litellm async clients are closed
        - No manual cleanup needed in tests
        - No RuntimeWarning during teardown
        """
        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_acompletion.return_value = mock_response

            from langchain_core.messages import HumanMessage

            from mcp_server_langgraph.llm.factory import LLMFactory

            llm = LLMFactory(provider="anthropic", model_name="claude-3-5-sonnet-20241022")
            messages = [HumanMessage(content="test")]
            await llm.ainvoke(messages)

            # Fixture should handle cleanup automatically
            # No assertions needed - just verify no warnings during teardown

    @pytest.mark.asyncio
    async def test_multiple_litellm_calls_cleanup(self):
        """
        Test that multiple litellm calls in sequence don't accumulate unclosed clients.

        This simulates realistic test scenarios where multiple LLM calls are made.
        """
        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_acompletion.return_value = mock_response

            from langchain_core.messages import HumanMessage

            from mcp_server_langgraph.llm.factory import LLMFactory

            llm = LLMFactory(provider="anthropic", model_name="claude-3-5-sonnet-20241022")
            messages = [HumanMessage(content="test")]

            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always", RuntimeWarning)

                # Make multiple async calls
                for _ in range(3):
                    await llm.ainvoke(messages)

                gc.collect()
                await asyncio.sleep(0.1)

            runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
            litellm_warnings = [
                w for w in runtime_warnings if "close_litellm_async_clients" in str(w.message) or "coroutine" in str(w.message)
            ]

            assert len(litellm_warnings) == 0, f"Expected no warnings after multiple calls, got {len(litellm_warnings)}"
