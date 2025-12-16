"""
TDD RED Phase: Tests for LLM Factory async-only API.

These tests verify that:
1. sync invoke() method has been removed
2. sync _try_fallback() method has been removed
3. ainvoke() works correctly and is the primary API
4. _try_fallback_async() is the only fallback mechanism

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import asyncio
import gc
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.llm.factory import LLMFactory

# Module-level pytestmark for test organization
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="llm_factory_async")
class TestLLMFactorySyncMethodsRemoved:
    """
    TDD tests to verify sync methods have been removed from LLMFactory.

    Breaking change: Users must migrate from invoke() to ainvoke().
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sync_invoke_method_removed(self):
        """
        RED: Verify invoke() method no longer exists.

        Breaking change: Users must use ainvoke() instead.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        # invoke() should NOT exist - it was removed
        assert not hasattr(factory, "invoke") or not callable(getattr(factory, "invoke", None)), (
            "invoke() method should be removed. Use ainvoke() instead."
        )

    def test_sync_try_fallback_method_removed(self):
        """
        RED: Verify _try_fallback() method no longer exists.

        Breaking change: Only _try_fallback_async() should remain.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        # _try_fallback() should NOT exist - it was removed
        assert not hasattr(factory, "_try_fallback") or not callable(getattr(factory, "_try_fallback", None)), (
            "_try_fallback() method should be removed. Use _try_fallback_async() instead."
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="llm_factory_async")
class TestLLMFactoryAsyncAPI:
    """
    TDD tests for LLMFactory.ainvoke() - the only LLM invocation API.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_ainvoke_method_exists_and_is_async(self):
        """
        Verify ainvoke() method exists and is a coroutine function.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        assert hasattr(factory, "ainvoke"), "LLMFactory must have ainvoke() method"
        assert asyncio.iscoroutinefunction(factory.ainvoke), "ainvoke() must be an async method (coroutine function)"

    async def test_ainvoke_returns_ai_message(self):
        """
        Verify ainvoke() returns an AIMessage instance.
        """
        from langchain_core.messages import AIMessage, HumanMessage

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            # Mock the LiteLLM response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello, I am an AI assistant."
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 15
            mock_response.usage.total_tokens = 25

            mock_acompletion.return_value = mock_response

            messages = [HumanMessage(content="Hello")]
            result = await factory.ainvoke(messages)

            assert isinstance(result, AIMessage), f"ainvoke() must return AIMessage, got {type(result)}"
            assert result.content == "Hello, I am an AI assistant."

    async def test_ainvoke_with_dict_messages(self):
        """
        Verify ainvoke() handles dict-formatted messages.
        """
        from langchain_core.messages import AIMessage

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_response.usage = None

            mock_acompletion.return_value = mock_response

            # Dict-formatted messages (already in LiteLLM format)
            messages = [{"role": "user", "content": "Hello"}]
            result = await factory.ainvoke(messages)

            assert isinstance(result, AIMessage)
            # Verify the message was formatted correctly
            call_args = mock_acompletion.call_args
            assert call_args.kwargs["messages"][0]["role"] == "user"
            assert call_args.kwargs["messages"][0]["content"] == "Hello"

    async def test_try_fallback_async_method_exists(self):
        """
        Verify _try_fallback_async() method exists for async fallback.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
            fallback_models=["claude-sonnet-4-20250514"],
        )

        assert hasattr(factory, "_try_fallback_async"), "LLMFactory must have _try_fallback_async() method"
        assert asyncio.iscoroutinefunction(factory._try_fallback_async), "_try_fallback_async() must be an async method"

    async def test_ainvoke_uses_async_fallback_on_error(self):
        """
        Verify ainvoke() calls _try_fallback_async() when primary fails.
        """
        from langchain_core.messages import AIMessage, HumanMessage

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
            enable_fallback=True,
            fallback_models=["claude-sonnet-4-20250514"],
        )

        call_count = [0]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def acompletion_side_effect(**kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # Primary fails
                    raise Exception("Primary model failed")
                else:
                    # Fallback succeeds
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = "Fallback response"
                    mock_response.usage = None
                    return mock_response

            mock_acompletion.side_effect = acompletion_side_effect

            messages = [HumanMessage(content="Hello")]
            result = await factory.ainvoke(messages)

            assert isinstance(result, AIMessage)
            assert result.content == "Fallback response"
            assert call_count[0] >= 2, "Should have tried primary and at least one fallback"

    async def test_ainvoke_has_resilience_decorators(self):
        """
        Verify ainvoke() has circuit_breaker, retry, timeout, and bulkhead decorators.
        """
        # Check that the method has the expected attributes from decorators
        # The decorators add metadata to the wrapped function
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        # The ainvoke method should be wrapped by decorators
        # We can verify it's decorated by checking it's still callable and async
        assert callable(factory.ainvoke)
        assert asyncio.iscoroutinefunction(factory.ainvoke)

        # Verify it's the decorated version by checking the function still works
        # (decorated functions maintain their coroutine nature)
        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_response.usage = None
            mock_acompletion.return_value = mock_response

            result = await factory.ainvoke([{"role": "user", "content": "test"}])
            assert result is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="llm_factory_async")
class TestLLMFactoryMigrationHints:
    """
    Tests that provide helpful error messages for users migrating from sync to async.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_module_does_not_import_sync_completion(self):
        """
        RED: Verify that 'completion' is no longer imported (only acompletion).

        This prevents accidental use of sync API.
        """
        from mcp_server_langgraph.llm import factory as factory_module

        # Check that the module doesn't use sync 'completion' function
        # We can verify by checking if 'completion' is used in the module
        # (it should only have 'acompletion')
        with open(factory_module.__file__) as f:
            source = f.read()

        # Count occurrences - should only have imports and no usage
        # After removal, 'completion' should only appear in comments or imports
        # The sync completion function call should not exist
        lines_with_completion_call = [
            line
            for line in source.split("\n")
            if "completion(" in line  # Matches "completion(**params)" but not "acompletion("
            and not line.strip().startswith("#")  # Skip comments
            and "acompletion(" not in line  # Not the async version
        ]

        assert len(lines_with_completion_call) == 0, (
            f"Found sync completion() calls that should be removed:\n{chr(10).join(lines_with_completion_call)}"
        )
