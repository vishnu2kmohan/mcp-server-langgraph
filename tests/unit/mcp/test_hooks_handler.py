"""
Tests for MCP Hooks Extension Handler.

Tests the MCP tool handler for hook management:
- List registered hooks
- List available hook events
- Register/unregister webhooks (admin only)

TDD: RED phase - Define expected behavior for hooks tool.

References:
- Plan Section 10.5: Expose Hooks as MCP Extension
- ADR-0077: Claude Agent SDK Hook System
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestHooksToolHandler:
    """Test hooks tool handler setup."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_create_hooks_tool_handler_returns_handler(self) -> None:
        """create_hooks_tool_handler should return a HooksToolHandler."""
        from mcp_server_langgraph.mcp.handlers.hooks import create_hooks_tool_handler

        handler = create_hooks_tool_handler()

        assert handler is not None

    def test_hooks_tool_handler_has_tool_definition(self) -> None:
        """Handler should provide a tool definition."""
        from mcp_server_langgraph.mcp.handlers.hooks import create_hooks_tool_handler

        handler = create_hooks_tool_handler()
        tool_def = handler.get_tool_definition()

        assert tool_def is not None
        assert tool_def["name"] == "hooks"
        assert "description" in tool_def
        assert "inputSchema" in tool_def


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestListHookEvents:
    """Test listing available hook events."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_events_returns_all_hook_events(self) -> None:
        """List events operation should return all HookEvent types."""
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler()
        result = await handler.handle_operation("events", {})

        assert "events" in result
        events = result["events"]

        # Should include all hook event types
        event_names = [e["event"] for e in events]
        assert "PreToolUse" in event_names
        assert "PostToolUse" in event_names
        assert "BeforeModel" in event_names
        assert "AfterModel" in event_names
        assert "SessionStart" in event_names
        assert "SessionEnd" in event_names
        assert "UserPromptSubmit" in event_names
        assert "Stop" in event_names

    @pytest.mark.asyncio
    async def test_list_events_includes_descriptions(self) -> None:
        """Each event should have a description."""
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler()
        result = await handler.handle_operation("events", {})

        events = result["events"]
        for event in events:
            assert "event" in event
            assert "description" in event
            assert len(event["description"]) > 0


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestListRegisteredHooks:
    """Test listing registered hooks."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_hooks_returns_empty_for_no_hooks(self) -> None:
        """List operation should return empty list when no hooks registered."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        registry = HookRegistry()
        handler = HooksToolHandler(hook_registry=registry)
        result = await handler.handle_operation("list", {})

        assert "hooks" in result
        assert result["hooks"] == []

    @pytest.mark.asyncio
    async def test_list_hooks_returns_registered_hooks(self) -> None:
        """List operation should return all registered hooks."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import HookEvent, HookMatcher
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        async def dummy_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(matcher="Bash", hooks=[dummy_hook]),
        )

        handler = HooksToolHandler(hook_registry=registry)
        result = await handler.handle_operation("list", {})

        assert "hooks" in result
        assert len(result["hooks"]) == 1
        assert result["hooks"][0]["event"] == "PreToolUse"
        assert result["hooks"][0]["matcher"] == "Bash"

    @pytest.mark.asyncio
    async def test_list_hooks_filters_by_event(self) -> None:
        """List operation should filter by event type when specified."""
        from mcp_server_langgraph.core.hook_registry import HookRegistry
        from mcp_server_langgraph.core.hooks import HookEvent, HookMatcher
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        async def dummy_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        registry = HookRegistry()
        registry.register(
            HookEvent.PRE_TOOL_USE,
            HookMatcher(matcher="Bash", hooks=[dummy_hook]),
        )
        registry.register(
            HookEvent.POST_TOOL_USE,
            HookMatcher(matcher=".*", hooks=[dummy_hook]),
        )

        handler = HooksToolHandler(hook_registry=registry)
        result = await handler.handle_operation(
            "list", {"event": "PostToolUse"}
        )

        assert "hooks" in result
        assert len(result["hooks"]) == 1
        assert result["hooks"][0]["event"] == "PostToolUse"


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestHooksOperationDispatch:
    """Test operation dispatching."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self) -> None:
        """Unknown operation should return error."""
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler()
        result = await handler.handle_operation("unknown", {})

        assert "error" in result
        assert "unknown" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_operations_are_case_insensitive(self) -> None:
        """Operation names should be case insensitive."""
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler()

        result1 = await handler.handle_operation("EVENTS", {})
        result2 = await handler.handle_operation("events", {})

        assert "events" in result1
        assert "events" in result2


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestHookEventDescriptions:
    """Test that event descriptions are accurate."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_get_event_description_for_known_events(self) -> None:
        """get_event_description should return descriptions for known events."""
        from mcp_server_langgraph.core.hooks import HookEvent
        from mcp_server_langgraph.mcp.handlers.hooks import get_event_description

        # Tool-level hooks
        assert "before" in get_event_description(HookEvent.PRE_TOOL_USE).lower()
        assert "after" in get_event_description(HookEvent.POST_TOOL_USE).lower()

        # LLM-level hooks
        assert "llm" in get_event_description(HookEvent.BEFORE_MODEL).lower()
        assert "response" in get_event_description(HookEvent.AFTER_MODEL).lower()

        # Session hooks
        assert "session" in get_event_description(HookEvent.SESSION_START).lower()
        assert "session" in get_event_description(HookEvent.SESSION_END).lower()

    def test_get_event_description_returns_fallback_for_unknown(self) -> None:
        """get_event_description should return fallback for unknown events."""
        from mcp_server_langgraph.mcp.handlers.hooks import get_event_description

        # Create a mock event (simulating an unknown one)
        class MockEvent:
            value = "UnknownEvent"

        result = get_event_description(MockEvent())

        assert "unknown" in result.lower() or len(result) > 0


@pytest.mark.xdist_group(name="mcp_hooks_handler")
class TestToolInputSchema:
    """Test the tool input schema."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_input_schema_has_operation_enum(self) -> None:
        """Input schema should have operation as enum."""
        from mcp_server_langgraph.mcp.handlers.hooks import create_hooks_tool_handler

        handler = create_hooks_tool_handler()
        schema = handler.get_tool_definition()["inputSchema"]

        assert "properties" in schema
        assert "operation" in schema["properties"]
        assert "enum" in schema["properties"]["operation"]

        operations = schema["properties"]["operation"]["enum"]
        assert "list" in operations
        assert "events" in operations

    def test_input_schema_has_optional_event_filter(self) -> None:
        """Input schema should have optional event filter."""
        from mcp_server_langgraph.mcp.handlers.hooks import create_hooks_tool_handler

        handler = create_hooks_tool_handler()
        schema = handler.get_tool_definition()["inputSchema"]

        assert "event" in schema["properties"]
        assert schema["properties"]["event"]["type"] == "string"
