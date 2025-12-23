"""
TDD Tests for LLM Factory Hook Integration

Tests for wiring BEFORE_MODEL and AFTER_MODEL hooks into the LLM factory call path.
Written FIRST before implementation (RED phase) per TDD methodology.

Reference: ADR-0080 LLM-Level Callback System
"""

import gc
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="llm_factory_hooks")
class TestHookDispatcherConvenienceMethods:
    """Test suite for HookDispatcher convenience methods for LLM hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_before_model_convenience_method(self):
        """GIVEN a HookDispatcher
        WHEN dispatch_before_model is called
        THEN it dispatches BEFORE_MODEL event with BeforeModelInput"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry

        hook_called_with = []

        async def capture_hook(input_data, tool_use_id, context):
            hook_called_with.append(input_data)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[capture_hook]))
        dispatcher = HookDispatcher(registry)

        context = HookContext(session_id="sess_123", user_id="user_456")
        messages = [{"role": "user", "content": "Hello"}]

        result = await dispatcher.dispatch_before_model(
            messages=messages,
            model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
            context=context,
        )

        assert len(hook_called_with) == 1
        assert hook_called_with[0].messages == messages
        assert hook_called_with[0].model == "gpt-4"
        assert result.should_proceed

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_after_model_convenience_method(self):
        """GIVEN a HookDispatcher
        WHEN dispatch_after_model is called
        THEN it dispatches AFTER_MODEL event with AfterModelInput"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
            TokenUsage,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry

        hook_called_with = []

        async def capture_hook(input_data, tool_use_id, context):
            hook_called_with.append(input_data)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.AFTER_MODEL, HookMatcher(hooks=[capture_hook]))
        dispatcher = HookDispatcher(registry)

        context = HookContext(session_id="sess_123", user_id="user_456")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        result = await dispatcher.dispatch_after_model(
            content="Response text",
            model="gpt-4",
            finish_reason="stop",
            usage=usage,
            latency_ms=250.5,
            context=context,
        )

        assert len(hook_called_with) == 1
        assert hook_called_with[0].content == "Response text"
        assert hook_called_with[0].usage.total_tokens == 150
        assert result.should_proceed


@pytest.mark.xdist_group(name="llm_factory_hooks")
class TestLLMFactoryHookIntegration:
    """Test suite for LLMFactory hook integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_factory_dispatches_before_model_hook(self):
        """GIVEN an LLMFactory with hook dispatcher
        WHEN ainvoke is called
        THEN BEFORE_MODEL hook is dispatched before LLM call"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        hook_called = []

        async def before_model_hook(input_data, tool_use_id, context):
            hook_called.append("before_model")
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[before_model_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        # Mock the actual LLM call
        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            context = HookContext(session_id="sess_123")
            messages = [{"role": "user", "content": "Hello"}]

            await factory.ainvoke(messages, hook_context=context)

        assert "before_model" in hook_called

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_factory_dispatches_after_model_hook(self):
        """GIVEN an LLMFactory with hook dispatcher
        WHEN ainvoke completes
        THEN AFTER_MODEL hook is dispatched after LLM call"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        hook_called = []
        captured_content = []

        async def after_model_hook(input_data, tool_use_id, context):
            hook_called.append("after_model")
            captured_content.append(input_data.content)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.AFTER_MODEL, HookMatcher(hooks=[after_model_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="LLM Response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            context = HookContext(session_id="sess_123")
            messages = [{"role": "user", "content": "Hello"}]

            await factory.ainvoke(messages, hook_context=context)

        assert "after_model" in hook_called
        assert "LLM Response" in captured_content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_before_model_hook_can_skip_llm_call(self):
        """GIVEN a BEFORE_MODEL hook that returns early
        WHEN ainvoke is called
        THEN LLM call is skipped and cached response is returned"""
        from langchain_core.messages import AIMessage
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        async def cache_hook(input_data, tool_use_id, context):
            return HookResult(
                behavior="skip",
                early_return="Cached: This is a cached response",
            )

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[cache_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            context = HookContext(session_id="sess_123")
            messages = [{"role": "user", "content": "Hello"}]

            result = await factory.ainvoke(messages, hook_context=context)

            # LLM should NOT be called
            mock_acompletion.assert_not_called()

            # Should return cached response
            assert isinstance(result, AIMessage)
            assert "Cached: This is a cached response" in result.content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_after_model_hook_can_modify_output(self):
        """GIVEN an AFTER_MODEL hook that modifies output
        WHEN ainvoke completes
        THEN the modified output is returned"""
        from langchain_core.messages import AIMessage
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        async def disclaimer_hook(input_data, tool_use_id, context):
            return HookResult(
                behavior="allow",
                modified_output=f"[AI Generated] {input_data.content}",
            )

        registry = HookRegistry()
        registry.register(HookEvent.AFTER_MODEL, HookMatcher(hooks=[disclaimer_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Original response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            context = HookContext(session_id="sess_123")
            messages = [{"role": "user", "content": "Hello"}]

            result = await factory.ainvoke(messages, hook_context=context)

            assert isinstance(result, AIMessage)
            assert result.content == "[AI Generated] Original response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_before_model_hook_can_deny_request(self):
        """GIVEN a BEFORE_MODEL hook that denies the request
        WHEN ainvoke is called
        THEN an error is raised and LLM is not called"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        async def block_hook(input_data, tool_use_id, context):
            return HookResult(
                behavior="deny",
                message="Request blocked: contains forbidden content",
            )

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[block_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            context = HookContext(session_id="sess_123")
            messages = [{"role": "user", "content": "Forbidden content"}]

            with pytest.raises(Exception) as exc_info:
                await factory.ainvoke(messages, hook_context=context)

            # LLM should NOT be called
            mock_acompletion.assert_not_called()

            # Error message should mention the hook's denial reason
            assert "blocked" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()


@pytest.mark.xdist_group(name="llm_factory_hooks")
class TestLLMFactoryHookFeatureFlag:
    """Test suite for feature flag control of LLM hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hooks_skipped_when_feature_flag_disabled(self):
        """GIVEN enable_llm_hooks=False
        WHEN ainvoke is called
        THEN hooks are skipped and LLM is called directly"""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        hook_called = []

        async def track_hook(input_data, tool_use_id, context):
            hook_called.append(True)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[track_hook]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            # Patch where feature_flags is used (factory.py), not where it's defined
            with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags:
                mock_flags.enable_llm_hooks = False
                mock_flags.enable_sdk_hooks = True  # SDK hooks still enabled

                context = HookContext(session_id="sess_123")
                messages = [{"role": "user", "content": "Hello"}]

                await factory.ainvoke(messages, hook_context=context)

        # Hook should NOT be called when feature flag is disabled
        assert len(hook_called) == 0
        # But LLM should still be called
        mock_acompletion.assert_called_once()


@pytest.mark.xdist_group(name="llm_factory_hooks")
class TestLLMFactoryBackwardCompatibility:
    """Test suite for backward compatibility without hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_factory_works_without_hook_dispatcher(self):
        """GIVEN an LLMFactory without hook_dispatcher
        WHEN ainvoke is called
        THEN it works normally without hooks"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            # No hook_dispatcher passed
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]

            result = await factory.ainvoke(messages)

            assert result.content == "Response"
            mock_acompletion.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_factory_works_without_hook_context(self):
        """GIVEN an LLMFactory with hook_dispatcher but no context
        WHEN ainvoke is called without hook_context
        THEN it creates a default context"""
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry
        from mcp_server_langgraph.llm.factory import LLMFactory

        hook_context_received = []

        async def capture_context(input_data, tool_use_id, context):
            hook_context_received.append(context)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[capture_context]))
        dispatcher = HookDispatcher(registry)

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            hook_dispatcher=dispatcher,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]

            # Call without hook_context
            await factory.ainvoke(messages)

        # Hook should receive a default context
        assert len(hook_context_received) == 1
        assert hook_context_received[0] is not None
        assert hasattr(hook_context_received[0], "session_id")
