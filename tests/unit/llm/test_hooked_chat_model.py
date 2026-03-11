"""
Tests for llm/hooked_chat_model.py module.

TDD: These tests define the expected behavior for the HookedChatModel wrapper
that preserves ADR-0080 hooks semantics while wrapping LangChain ChatModels.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

pytestmark = pytest.mark.unit


def make_chat_result(text: str) -> ChatResult:
    """Helper to create a ChatResult with proper message field."""
    return ChatResult(generations=[ChatGeneration(text=text, message=AIMessage(content=text))])


@pytest.mark.unit
class TestHookedChatModelMessageFormatting:
    """Tests for message formatting between LangChain and hook formats."""

    def test_format_human_message(self) -> None:
        """HumanMessage should format to role=user."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        model = HookedChatModel(inner=mock_inner, model_name="test", provider="test")

        messages = [HumanMessage(content="Hello")]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_ai_message(self) -> None:
        """AIMessage should format to role=assistant."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        model = HookedChatModel(inner=mock_inner, model_name="test", provider="test")

        messages = [AIMessage(content="Hi there")]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "assistant"
        assert formatted[0]["content"] == "Hi there"

    def test_format_system_message(self) -> None:
        """SystemMessage should format to role=system."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        model = HookedChatModel(inner=mock_inner, model_name="test", provider="test")

        messages = [SystemMessage(content="You are helpful")]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are helpful"

    def test_rebuild_messages_from_formatted(self) -> None:
        """Should rebuild LangChain messages from formatted dicts."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        model = HookedChatModel(inner=mock_inner, model_name="test", provider="test")

        formatted = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        rebuilt = model._rebuild_messages(formatted)

        assert len(rebuilt) == 3
        assert isinstance(rebuilt[0], SystemMessage)
        assert isinstance(rebuilt[1], HumanMessage)
        assert isinstance(rebuilt[2], AIMessage)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelBeforeModelHook:
    """Tests for BEFORE_MODEL hook dispatch."""

    @pytest.mark.asyncio
    async def test_before_model_allow_behavior(self) -> None:
        """Allow behavior should proceed with LLM call."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel
        from mcp_server_langgraph.core.hooks import HookResult

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=make_chat_result("Response"))
        mock_inner._llm_type = "test"

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_before_model = AsyncMock(return_value=HookResult(behavior="allow"))
        mock_dispatcher.dispatch_after_model = AsyncMock(return_value=HookResult())

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        # Patch feature flags and resilience
        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = True

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()

                    result = await model._agenerate([HumanMessage(content="Hello")])

        mock_dispatcher.dispatch_before_model.assert_called_once()
        mock_inner._agenerate.assert_called_once()
        assert result.generations[0].text == "Response"

    @pytest.mark.asyncio
    async def test_before_model_deny_behavior_raises(self) -> None:
        """Deny behavior should raise LLMProviderError."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel
        from mcp_server_langgraph.core.hooks import HookResult
        from mcp_server_langgraph.core.exceptions import LLMProviderError

        mock_inner = MagicMock()
        mock_inner._llm_type = "test"

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_before_model = AsyncMock(
            return_value=HookResult(behavior="deny", message="Blocked by policy")
        )

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = True

            with pytest.raises(LLMProviderError) as exc_info:
                await model._agenerate([HumanMessage(content="Hello")])

            assert "Blocked by policy" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_before_model_skip_returns_early(self) -> None:
        """Skip behavior should return early_return without calling LLM."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel
        from mcp_server_langgraph.core.hooks import HookResult

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=None)  # Should NOT be called
        mock_inner._llm_type = "test"

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_before_model = AsyncMock(
            return_value=HookResult(behavior="skip", early_return="Cached response")
        )

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = True

            result = await model._agenerate([HumanMessage(content="Hello")])

        mock_inner._agenerate.assert_not_called()
        assert result.generations[0].text == "Cached response"

    @pytest.mark.asyncio
    async def test_before_model_updated_input_applied(self) -> None:
        """Updated input from hook should be applied to actual LLM call."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel
        from mcp_server_langgraph.core.hooks import HookResult

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=make_chat_result("Response"))
        mock_inner._llm_type = "test"

        # Hook modifies the messages
        updated_messages = [{"role": "user", "content": "Modified input"}]
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_before_model = AsyncMock(
            return_value=HookResult(behavior="allow", updated_input=updated_messages)
        )
        mock_dispatcher.dispatch_after_model = AsyncMock(return_value=HookResult())

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = True

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()

                    await model._agenerate([HumanMessage(content="Original")])

        # Verify the inner model received the MODIFIED messages
        call_args = mock_inner._agenerate.call_args
        messages_sent = call_args[0][0]
        assert len(messages_sent) == 1
        assert isinstance(messages_sent[0], HumanMessage)
        assert messages_sent[0].content == "Modified input"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelAfterModelHook:
    """Tests for AFTER_MODEL hook dispatch."""

    @pytest.mark.asyncio
    async def test_after_model_modified_output_applied(self) -> None:
        """Modified output from hook should be returned."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel
        from mcp_server_langgraph.core.hooks import HookResult

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=make_chat_result("Original output"))
        mock_inner._llm_type = "test"

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_before_model = AsyncMock(return_value=HookResult(behavior="allow"))
        mock_dispatcher.dispatch_after_model = AsyncMock(return_value=HookResult(modified_output="Transformed output"))

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = True

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()

                    result = await model._agenerate([HumanMessage(content="Hello")])

        assert result.generations[0].text == "Transformed output"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelResilience:
    """Tests for resilience patterns (bulkhead, rate limiting)."""

    @pytest.mark.asyncio
    async def test_record_success_on_successful_call(self) -> None:
        """Adaptive bulkhead should record success on successful LLM call."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=make_chat_result("Response"))
        mock_inner._llm_type = "test"

        model = HookedChatModel(inner=mock_inner, hook_dispatcher=None, model_name="test", provider="test")

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = False

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()
                    mock_bulkhead.return_value.record_error = MagicMock()

                    await model._agenerate([HumanMessage(content="Hello")])

                    mock_bulkhead.return_value.record_success.assert_called_once()
                    mock_bulkhead.return_value.record_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_error_on_failed_call(self) -> None:
        """Adaptive bulkhead should record error on failed LLM call."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(side_effect=RuntimeError("LLM failed"))
        mock_inner._llm_type = "test"

        model = HookedChatModel(inner=mock_inner, hook_dispatcher=None, model_name="test", provider="test")

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = False

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    # Return False to not suppress exceptions
                    mock_semaphore.__aexit__ = AsyncMock(return_value=False)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()
                    mock_bulkhead.return_value.record_error = MagicMock()

                    with pytest.raises(RuntimeError):
                        await model._agenerate([HumanMessage(content="Hello")])

                    mock_bulkhead.return_value.record_error.assert_called_once()
                    mock_bulkhead.return_value.record_success.assert_not_called()

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelBindTools:
    """Tests for bind_tools delegation."""

    def test_bind_tools_returns_wrapped_model(self) -> None:
        """bind_tools should return a new HookedChatModel wrapping the bound inner."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        mock_bound_inner = MagicMock()
        mock_inner.bind_tools.return_value = mock_bound_inner
        mock_inner._llm_type = "test"
        mock_bound_inner._llm_type = "test_bound"

        mock_dispatcher = MagicMock()

        model = HookedChatModel(
            inner=mock_inner,
            hook_dispatcher=mock_dispatcher,
            model_name="test-model",
            provider="test",
        )

        tools = [MagicMock()]
        bound_model = model.bind_tools(tools)

        mock_inner.bind_tools.assert_called_once_with(tools)
        assert isinstance(bound_model, HookedChatModel)
        assert bound_model.inner is mock_bound_inner
        assert bound_model.hook_dispatcher is mock_dispatcher
        assert bound_model.model_name == "test-model"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelNativeTools:
    """Tests for native tool config passing via kwargs."""

    @pytest.mark.asyncio
    async def test_native_tools_passed_via_kwargs(self) -> None:
        """Native tool configs should be passed to inner model via kwargs."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        mock_inner._agenerate = AsyncMock(return_value=make_chat_result("Response"))
        mock_inner._llm_type = "test"

        model = HookedChatModel(inner=mock_inner, hook_dispatcher=None, model_name="test", provider="test")

        native_configs = [{"type": "web_search_20250305"}]

        with patch("mcp_server_langgraph.llm.hooked_chat_model.feature_flags") as mock_flags:
            mock_flags.enable_llm_hooks = False

            with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_token_bucket") as mock_bucket:
                mock_bucket.return_value.acquire = AsyncMock(return_value=None)

                with patch("mcp_server_langgraph.llm.hooked_chat_model.get_provider_adaptive_bulkhead") as mock_bulkhead:
                    mock_semaphore = MagicMock()
                    mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                    mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                    mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore
                    mock_bulkhead.return_value.record_success = MagicMock()

                    await model._agenerate([HumanMessage(content="Hello")], native_tools=native_configs)

        # Verify native_tools was passed to inner model
        call_kwargs = mock_inner._agenerate.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == native_configs

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestHookedChatModelLlmType:
    """Tests for _llm_type property."""

    def test_llm_type_prefixes_inner(self) -> None:
        """_llm_type should prefix inner model's type with 'hooked_'."""
        from mcp_server_langgraph.llm.hooked_chat_model import HookedChatModel

        mock_inner = MagicMock()
        mock_inner._llm_type = "anthropic"

        model = HookedChatModel(inner=mock_inner, model_name="test", provider="test")

        assert model._llm_type == "hooked_anthropic"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
