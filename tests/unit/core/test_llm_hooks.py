"""
TDD Tests for LLM-Level Hooks (ADR-0080)

Tests for BEFORE_MODEL and AFTER_MODEL hooks that enable:
- LLM request interception (prompt modification, caching, blocking)
- LLM response interception (output filtering, disclaimer injection)

Written FIRST before implementation (RED phase).
"""

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


MCP_PROTOCOL_VERSION = "2025-11-25"



pytestmark = pytest.mark.unit

@pytest.mark.xdist_group(name="llm_hooks")
class TestLLMHookEvents:
    """Test suite for LLM-level hook event types."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_before_model_event_exists(self):
        """GIVEN HookEvent enum
        WHEN accessing BEFORE_MODEL
        THEN it is defined with correct value"""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert hasattr(HookEvent, "BEFORE_MODEL")
        assert HookEvent.BEFORE_MODEL.value == "BeforeModel"

    @pytest.mark.unit
    def test_after_model_event_exists(self):
        """GIVEN HookEvent enum
        WHEN accessing AFTER_MODEL
        THEN it is defined with correct value"""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert hasattr(HookEvent, "AFTER_MODEL")
        assert HookEvent.AFTER_MODEL.value == "AfterModel"

    @pytest.mark.unit
    def test_session_start_event_exists(self):
        """GIVEN HookEvent enum
        WHEN accessing SESSION_START
        THEN it is defined with correct value"""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert hasattr(HookEvent, "SESSION_START")
        assert HookEvent.SESSION_START.value == "SessionStart"

    @pytest.mark.unit
    def test_session_end_event_exists(self):
        """GIVEN HookEvent enum
        WHEN accessing SESSION_END
        THEN it is defined with correct value"""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert hasattr(HookEvent, "SESSION_END")
        assert HookEvent.SESSION_END.value == "SessionEnd"


@pytest.mark.xdist_group(name="llm_hooks")
class TestBeforeModelInput:
    """Test suite for BeforeModelInput data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_before_model_input_has_messages(self):
        """GIVEN BeforeModelInput
        WHEN created with messages
        THEN messages are accessible"""
        from mcp_server_langgraph.core.hooks import BeforeModelInput

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        input_data = BeforeModelInput(
            messages=messages,
            model="gpt-4",
        )

        assert input_data.messages == messages
        assert input_data.model == "gpt-4"

    @pytest.mark.unit
    def test_before_model_input_has_config(self):
        """GIVEN BeforeModelInput
        WHEN created with config options
        THEN config is accessible"""
        from mcp_server_langgraph.core.hooks import BeforeModelInput

        input_data = BeforeModelInput(
            messages=[{"role": "user", "content": "Test"}],
            model="claude-3-opus",
            temperature=0.7,
            max_tokens=1000,
            config={"stream": True},
        )

        assert input_data.temperature == 0.7
        assert input_data.max_tokens == 1000
        assert input_data.config == {"stream": True}

    @pytest.mark.unit
    def test_before_model_input_optional_tools(self):
        """GIVEN BeforeModelInput
        WHEN created with tools
        THEN tools are accessible"""
        from mcp_server_langgraph.core.hooks import BeforeModelInput

        tools = [{"name": "search", "description": "Search the web"}]

        input_data = BeforeModelInput(
            messages=[{"role": "user", "content": "Search for Python"}],
            model="gpt-4",
            tools=tools,
        )

        assert input_data.tools == tools

    @pytest.mark.unit
    def test_before_model_input_defaults(self):
        """GIVEN BeforeModelInput
        WHEN created with minimal args
        THEN defaults are set correctly"""
        from mcp_server_langgraph.core.hooks import BeforeModelInput

        input_data = BeforeModelInput(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
        )

        assert input_data.temperature is None
        assert input_data.max_tokens is None
        assert input_data.tools is None
        assert input_data.config == {}


@pytest.mark.xdist_group(name="llm_hooks")
class TestAfterModelInput:
    """Test suite for AfterModelInput data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_after_model_input_has_response(self):
        """GIVEN AfterModelInput
        WHEN created with response
        THEN response content is accessible"""
        from mcp_server_langgraph.core.hooks import AfterModelInput

        input_data = AfterModelInput(
            content="Hello! How can I help you?",
            model="gpt-4",
            finish_reason="stop",
        )

        assert input_data.content == "Hello! How can I help you?"
        assert input_data.model == "gpt-4"
        assert input_data.finish_reason == "stop"

    @pytest.mark.unit
    def test_after_model_input_has_usage(self):
        """GIVEN AfterModelInput
        WHEN created with token usage
        THEN usage is accessible"""
        from mcp_server_langgraph.core.hooks import AfterModelInput, TokenUsage

        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        input_data = AfterModelInput(
            content="Response text",
            model="claude-3-opus",
            finish_reason="stop",
            usage=usage,
        )

        assert input_data.usage.prompt_tokens == 100
        assert input_data.usage.completion_tokens == 50
        assert input_data.usage.total_tokens == 150

    @pytest.mark.unit
    def test_after_model_input_has_tool_calls(self):
        """GIVEN AfterModelInput
        WHEN response contains tool calls
        THEN tool calls are accessible"""
        from mcp_server_langgraph.core.hooks import AfterModelInput

        tool_calls = [
            {"id": "call_1", "name": "search", "arguments": {"query": "Python"}}
        ]

        input_data = AfterModelInput(
            content="",
            model="gpt-4",
            finish_reason="tool_calls",
            tool_calls=tool_calls,
        )

        assert input_data.tool_calls == tool_calls

    @pytest.mark.unit
    def test_after_model_input_has_latency(self):
        """GIVEN AfterModelInput
        WHEN created with latency info
        THEN latency is accessible"""
        from mcp_server_langgraph.core.hooks import AfterModelInput

        input_data = AfterModelInput(
            content="Response",
            model="gpt-4",
            finish_reason="stop",
            latency_ms=523.5,
        )

        assert input_data.latency_ms == 523.5


@pytest.mark.xdist_group(name="llm_hooks")
class TestTokenUsage:
    """Test suite for TokenUsage data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_token_usage_fields(self):
        """GIVEN TokenUsage
        WHEN created with token counts
        THEN all fields are accessible"""
        from mcp_server_langgraph.core.hooks import TokenUsage

        usage = TokenUsage(
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
        )

        assert usage.prompt_tokens == 500
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 700


@pytest.mark.xdist_group(name="llm_hooks")
class TestSessionStartInput:
    """Test suite for SessionStartInput data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_start_input_has_session_info(self):
        """GIVEN SessionStartInput
        WHEN created with session info
        THEN session ID and user ID are accessible"""
        from mcp_server_langgraph.core.hooks import SessionStartInput

        input_data = SessionStartInput(
            session_id="sess_abc123",
            user_id="user_456",
        )

        assert input_data.session_id == "sess_abc123"
        assert input_data.user_id == "user_456"

    @pytest.mark.unit
    def test_session_start_input_has_metadata(self):
        """GIVEN SessionStartInput
        WHEN created with metadata
        THEN metadata is accessible"""
        from mcp_server_langgraph.core.hooks import SessionStartInput

        metadata = {"client": "web", "version": "1.0.0"}

        input_data = SessionStartInput(
            session_id="sess_abc123",
            user_id="user_456",
            metadata=metadata,
        )

        assert input_data.metadata == metadata

    @pytest.mark.unit
    def test_session_start_input_has_timestamp(self):
        """GIVEN SessionStartInput
        WHEN created with timestamp
        THEN timestamp is accessible"""
        from mcp_server_langgraph.core.hooks import SessionStartInput

        now = datetime.now(UTC)

        input_data = SessionStartInput(
            session_id="sess_abc123",
            user_id="user_456",
            timestamp=now,
        )

        assert input_data.timestamp == now


@pytest.mark.xdist_group(name="llm_hooks")
class TestSessionEndInput:
    """Test suite for SessionEndInput data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_session_end_input_has_session_info(self):
        """GIVEN SessionEndInput
        WHEN created with session info
        THEN session ID and user ID are accessible"""
        from mcp_server_langgraph.core.hooks import SessionEndInput

        input_data = SessionEndInput(
            session_id="sess_abc123",
            user_id="user_456",
        )

        assert input_data.session_id == "sess_abc123"
        assert input_data.user_id == "user_456"

    @pytest.mark.unit
    def test_session_end_input_has_metrics(self):
        """GIVEN SessionEndInput
        WHEN created with session metrics
        THEN metrics are accessible"""
        from mcp_server_langgraph.core.hooks import SessionEndInput, TokenUsage

        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )

        input_data = SessionEndInput(
            session_id="sess_abc123",
            user_id="user_456",
            duration_ms=45000.0,
            message_count=10,
            token_usage=usage,
        )

        assert input_data.duration_ms == 45000.0
        assert input_data.message_count == 10
        assert input_data.token_usage.total_tokens == 1500

    @pytest.mark.unit
    def test_session_end_input_has_reason(self):
        """GIVEN SessionEndInput
        WHEN created with end reason
        THEN reason is accessible"""
        from mcp_server_langgraph.core.hooks import SessionEndInput

        input_data = SessionEndInput(
            session_id="sess_abc123",
            user_id="user_456",
            reason="user_closed",
        )

        assert input_data.reason == "user_closed"


@pytest.mark.xdist_group(name="llm_hooks")
class TestBeforeModelHookResult:
    """Test suite for hook results with LLM-specific behaviors."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_hook_result_can_skip_llm(self):
        """GIVEN a BeforeModel hook result
        WHEN behavior is 'skip'
        THEN early_return can be set for cached response"""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(
            behavior="skip",
            early_return="Cached response from previous call",
        )

        assert result.behavior == "skip"
        assert result.early_return == "Cached response from previous call"

    @pytest.mark.unit
    def test_hook_result_can_modify_messages(self):
        """GIVEN a BeforeModel hook result
        WHEN updated_input contains modified messages
        THEN modified messages are accessible"""
        from mcp_server_langgraph.core.hooks import HookResult

        modified_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello with extra context"},
        ]

        result = HookResult(
            behavior="allow",
            updated_input={"messages": modified_messages},
        )

        assert result.updated_input["messages"] == modified_messages


@pytest.mark.xdist_group(name="llm_hooks")
class TestAfterModelHookResult:
    """Test suite for AfterModel hook result behaviors."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_hook_result_can_modify_output(self):
        """GIVEN an AfterModel hook result
        WHEN modified_output is set
        THEN the modified output replaces original"""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(
            behavior="allow",
            modified_output="[AI Generated] Original response with disclaimer",
        )

        assert result.modified_output == "[AI Generated] Original response with disclaimer"

    @pytest.mark.unit
    def test_hook_result_can_block_output(self):
        """GIVEN an AfterModel hook result
        WHEN output contains blocked content
        THEN behavior is deny with reason"""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(
            behavior="deny",
            message="Output blocked: contains inappropriate content",
        )

        assert result.behavior == "deny"
        assert "blocked" in result.message.lower()


@pytest.mark.xdist_group(name="llm_hooks")
class TestHookRegistryLLMSupport:
    """Test suite for HookRegistry supporting LLM hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_registry_accepts_before_model_hooks(self):
        """GIVEN a HookRegistry
        WHEN registering a BEFORE_MODEL hook
        THEN the hook is stored correctly"""
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
        )
        from mcp_server_langgraph.core.hook_registry import HookRegistry

        async def my_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult
            return HookResult(behavior="allow")

        registry = HookRegistry()
        matcher = HookMatcher(hooks=[my_hook])

        registry.register(HookEvent.BEFORE_MODEL, matcher)

        matchers = registry.get_matchers(HookEvent.BEFORE_MODEL)
        assert len(matchers) == 1
        assert my_hook in matchers[0].hooks

    @pytest.mark.unit
    def test_registry_accepts_after_model_hooks(self):
        """GIVEN a HookRegistry
        WHEN registering an AFTER_MODEL hook
        THEN the hook is stored correctly"""
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
        )
        from mcp_server_langgraph.core.hook_registry import HookRegistry

        async def my_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult
            return HookResult(behavior="allow")

        registry = HookRegistry()
        matcher = HookMatcher(hooks=[my_hook])

        registry.register(HookEvent.AFTER_MODEL, matcher)

        matchers = registry.get_matchers(HookEvent.AFTER_MODEL)
        assert len(matchers) == 1

    @pytest.mark.unit
    def test_registry_accepts_session_hooks(self):
        """GIVEN a HookRegistry
        WHEN registering SESSION_START and SESSION_END hooks
        THEN the hooks are stored correctly"""
        from mcp_server_langgraph.core.hooks import (
            HookEvent,
            HookMatcher,
        )
        from mcp_server_langgraph.core.hook_registry import HookRegistry

        async def start_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult
            return HookResult(behavior="allow")

        async def end_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.SESSION_START, HookMatcher(hooks=[start_hook]))
        registry.register(HookEvent.SESSION_END, HookMatcher(hooks=[end_hook]))

        assert len(registry.get_matchers(HookEvent.SESSION_START)) == 1
        assert len(registry.get_matchers(HookEvent.SESSION_END)) == 1


@pytest.mark.xdist_group(name="llm_hooks")
class TestHookDispatcherLLMSupport:
    """Test suite for HookDispatcher executing LLM hooks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_before_model_hook(self):
        """GIVEN a registered BEFORE_MODEL hook
        WHEN dispatching the event
        THEN the hook is executed"""
        from mcp_server_langgraph.core.hooks import (
            BeforeModelInput,
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry

        hook_called = []

        async def track_hook(input_data, tool_use_id, context):
            hook_called.append(True)
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[track_hook]))

        dispatcher = HookDispatcher(registry)
        context = HookContext(session_id="sess_123", user_id="user_456")

        input_data = BeforeModelInput(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
        )

        result = await dispatcher.dispatch(
            event=HookEvent.BEFORE_MODEL,
            tool_name="llm",
            input_data=input_data,
            context=context,
        )

        assert len(hook_called) == 1
        assert result.should_proceed

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_after_model_hook(self):
        """GIVEN a registered AFTER_MODEL hook
        WHEN dispatching the event
        THEN the hook is executed and can modify output"""
        from mcp_server_langgraph.core.hooks import (
            AfterModelInput,
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry

        async def add_disclaimer(input_data, tool_use_id, context):
            modified = f"[AI] {input_data.content}"
            return HookResult(behavior="allow", modified_output=modified)

        registry = HookRegistry()
        registry.register(HookEvent.AFTER_MODEL, HookMatcher(hooks=[add_disclaimer]))

        dispatcher = HookDispatcher(registry)
        context = HookContext(session_id="sess_123", user_id="user_456")

        input_data = AfterModelInput(
            content="Original response",
            model="gpt-4",
            finish_reason="stop",
        )

        result = await dispatcher.dispatch(
            event=HookEvent.AFTER_MODEL,
            tool_name="llm",
            input_data=input_data,
            context=context,
        )

        assert result.should_proceed
        assert result.modified_output == "[AI] Original response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_before_model_hook_can_skip_llm(self):
        """GIVEN a BEFORE_MODEL hook that returns cached response
        WHEN dispatching the event
        THEN early_return is set and LLM can be skipped"""
        from mcp_server_langgraph.core.hooks import (
            BeforeModelInput,
            HookContext,
            HookEvent,
            HookMatcher,
            HookResult,
        )
        from mcp_server_langgraph.core.hook_registry import HookDispatcher, HookRegistry

        async def cache_hook(input_data, tool_use_id, context):
            # Simulate cache hit
            if "cached query" in input_data.messages[0].get("content", ""):
                return HookResult(
                    behavior="skip",
                    early_return="Cached: This is the cached response",
                )
            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(HookEvent.BEFORE_MODEL, HookMatcher(hooks=[cache_hook]))

        dispatcher = HookDispatcher(registry)
        context = HookContext(session_id="sess_123", user_id="user_456")

        input_data = BeforeModelInput(
            messages=[{"role": "user", "content": "This is a cached query"}],
            model="gpt-4",
        )

        result = await dispatcher.dispatch(
            event=HookEvent.BEFORE_MODEL,
            tool_name="llm",
            input_data=input_data,
            context=context,
        )

        assert result.behavior == "skip"
        assert result.early_return == "Cached: This is the cached response"


@pytest.mark.xdist_group(name="llm_hooks")
class TestHookInputTypeAlias:
    """Test suite for HookInput type alias including LLM types."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_hook_input_includes_llm_types(self):
        """GIVEN HookInput type alias
        WHEN checking included types
        THEN BeforeModelInput and AfterModelInput are included"""
        from mcp_server_langgraph.core.hooks import (
            BeforeModelInput,
            AfterModelInput,
            SessionStartInput,
            SessionEndInput,
            HookInput,
        )
        from typing import get_args

        # Get the types in the HookInput union
        hook_input_types = get_args(HookInput)

        assert BeforeModelInput in hook_input_types
        assert AfterModelInput in hook_input_types
        assert SessionStartInput in hook_input_types
        assert SessionEndInput in hook_input_types


@pytest.mark.xdist_group(name="llm_hooks")
class TestExportsComplete:
    """Test suite for module exports."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_all_llm_types_exported(self):
        """GIVEN hooks module
        WHEN checking __all__
        THEN all LLM types are exported"""
        from mcp_server_langgraph.core import hooks

        required_exports = [
            "BeforeModelInput",
            "AfterModelInput",
            "SessionStartInput",
            "SessionEndInput",
            "TokenUsage",
        ]

        for export in required_exports:
            assert export in hooks.__all__, f"{export} not in __all__"
            assert hasattr(hooks, export), f"{export} not accessible from module"
