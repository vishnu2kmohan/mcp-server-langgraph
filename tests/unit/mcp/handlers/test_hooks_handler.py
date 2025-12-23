"""
Tests for MCP Hooks Tool Handler.

Tests for exposing hooks as an MCP tool extension:
- hooks/list - List registered hooks
- hooks/events - List available hook events
- hooks/register - Register a webhook (admin only)
- hooks/unregister - Unregister a webhook (admin only)

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
    pytest.mark.hooks,
]


@pytest.mark.xdist_group(name="hooks_handler")
class TestHooksToolHandlerExists:
    """Tests for hooks tool handler existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hooks_tool_handler_exists(self) -> None:
        """
        GIVEN the handlers module
        WHEN importing HooksToolHandler
        THEN should be available.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        assert HooksToolHandler is not None

    def test_hooks_tool_handler_has_handle_method(self) -> None:
        """
        GIVEN a HooksToolHandler instance
        WHEN checking methods
        THEN should have handle method.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            hook_registry=MagicMock(),
        )

        assert hasattr(handler, "handle")


@pytest.mark.xdist_group(name="hooks_handler")
class TestHooksListOperation:
    """Tests for hooks/list operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_hooks_returns_registered_hooks(self) -> None:
        """
        GIVEN hooks are registered
        WHEN calling hooks/list
        THEN should return list of hooks.
        """
        from mcp_server_langgraph.core.hook_registry import HookEvent, HookMatcher
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        # Mock hook registry
        mock_registry = MagicMock()
        mock_registry._hooks = {
            HookEvent.PRE_TOOL_USE: [HookMatcher(hooks=[MagicMock()], matcher="file_*", timeout=30.0)],
            HookEvent.POST_TOOL_USE: [HookMatcher(hooks=[MagicMock(), MagicMock()], matcher=None, timeout=60.0)],
        }

        handler = HooksToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            hook_registry=mock_registry,
        )

        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="user@example.com",
        )

        # Parse result content
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"

        hooks = json.loads(content.text)
        assert len(hooks) == 2
        # Find PRE_TOOL_USE hook
        pre_hook = next(h for h in hooks if h["event"] == "PRE_TOOL_USE")
        assert pre_hook["matcher"] == "file_*"
        assert pre_hook["hook_count"] == 1

    @pytest.mark.asyncio
    async def test_list_hooks_filters_by_event(self) -> None:
        """
        GIVEN hooks are registered for multiple events
        WHEN calling hooks/list with event filter
        THEN should return only matching hooks.
        """
        from mcp_server_langgraph.core.hook_registry import HookEvent, HookMatcher
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        mock_registry = MagicMock()
        mock_registry._hooks = {
            HookEvent.PRE_TOOL_USE: [HookMatcher(hooks=[MagicMock()], matcher=None)],
            HookEvent.POST_TOOL_USE: [HookMatcher(hooks=[MagicMock()], matcher=None)],
        }

        handler = HooksToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            hook_registry=mock_registry,
        )

        result = await handler.handle(
            arguments={"operation": "list", "event": "PRE_TOOL_USE"},
            span=MagicMock(),
            user_id="user@example.com",
        )

        hooks = json.loads(result[0].text)
        assert len(hooks) == 1
        assert hooks[0]["event"] == "PRE_TOOL_USE"


@pytest.mark.xdist_group(name="hooks_handler")
class TestHooksEventsOperation:
    """Tests for hooks/events operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_events_returns_all_hook_events(self) -> None:
        """
        GIVEN HooksToolHandler
        WHEN calling hooks/events
        THEN should return list of all available hook events.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            hook_registry=MagicMock(),
        )

        result = await handler.handle(
            arguments={"operation": "events"},
            span=MagicMock(),
            user_id="user@example.com",
        )

        events = json.loads(result[0].text)

        # Should include core events
        event_names = [e["event"] for e in events]
        assert "PRE_TOOL_USE" in event_names
        assert "POST_TOOL_USE" in event_names
        assert "BEFORE_MODEL" in event_names
        assert "AFTER_MODEL" in event_names

    @pytest.mark.asyncio
    async def test_events_includes_descriptions(self) -> None:
        """
        GIVEN HooksToolHandler
        WHEN calling hooks/events
        THEN each event should have a description.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            hook_registry=MagicMock(),
        )

        result = await handler.handle(
            arguments={"operation": "events"},
            span=MagicMock(),
            user_id="user@example.com",
        )

        events = json.loads(result[0].text)

        for event in events:
            assert "event" in event
            assert "description" in event
            assert len(event["description"]) > 0


@pytest.mark.xdist_group(name="hooks_handler")
class TestHooksRegisterOperation:
    """Tests for hooks/register operation (admin only)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_register_requires_admin_role(self) -> None:
        """
        GIVEN a non-admin user
        WHEN calling hooks/register
        THEN should return unauthorized error.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        mock_auth = MagicMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        handler = HooksToolHandler(
            auth=mock_auth,
            agent_graph=MagicMock(),
            hook_registry=MagicMock(),
        )

        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "PRE_TOOL_USE",
                "webhook_url": "https://example.com/webhook",
            },
            span=MagicMock(),
            user_id="user@example.com",
        )

        assert "Unauthorized" in result[0].text

    @pytest.mark.asyncio
    async def test_register_succeeds_for_admin(self) -> None:
        """
        GIVEN an admin user
        WHEN calling hooks/register
        THEN should register webhook and return success.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        mock_auth = MagicMock()
        mock_auth.authorize = AsyncMock(return_value=True)

        mock_registry = MagicMock()
        mock_registry.register = MagicMock()
        mock_registry._hooks = {}

        handler = HooksToolHandler(
            auth=mock_auth,
            agent_graph=MagicMock(),
            hook_registry=mock_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "PRE_TOOL_USE",
                "webhook_url": "https://example.com/webhook",
            },
            span=MagicMock(),
            user_id="admin@example.com",
        )

        assert "registered" in result[0].text.lower()
        # Verify register was called
        mock_registry.register.assert_called_once()


@pytest.mark.xdist_group(name="hooks_handler")
class TestHooksUnregisterOperation:
    """Tests for hooks/unregister operation (admin only)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unregister_requires_admin_role(self) -> None:
        """
        GIVEN a non-admin user
        WHEN calling hooks/unregister
        THEN should return unauthorized error.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        mock_auth = MagicMock()
        mock_auth.authorize = AsyncMock(return_value=False)

        handler = HooksToolHandler(
            auth=mock_auth,
            agent_graph=MagicMock(),
            hook_registry=MagicMock(),
        )

        result = await handler.handle(
            arguments={
                "operation": "unregister",
                "event": "PRE_TOOL_USE",
            },
            span=MagicMock(),
            user_id="user@example.com",
        )

        assert "Unauthorized" in result[0].text
