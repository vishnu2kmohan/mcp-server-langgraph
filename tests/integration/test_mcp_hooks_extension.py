"""
Integration tests for MCP Hooks Extension.

Tests the hooks tool exposed via MCP:
- hooks/list - List registered hooks
- hooks/events - List available hook events
- hooks/register - Register webhooks (admin only)
- hooks/unregister - Unregister webhooks (admin only)

TDD: Tests written FIRST.
"""

from __future__ import annotations

import gc
import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.hook_registry import (
    HookMatcher,
    HookRegistry,
    reset_hook_registry,
)
from mcp_server_langgraph.core.hooks import HookEvent

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mcp,
    pytest.mark.hooks,
]


@pytest.fixture
def enable_hooks_extension():
    """Enable hooks MCP extension feature flag."""
    original = os.environ.get("FF_ENABLE_HOOKS_MCP_EXTENSION")
    os.environ["FF_ENABLE_HOOKS_MCP_EXTENSION"] = "true"
    yield
    if original is None:
        os.environ.pop("FF_ENABLE_HOOKS_MCP_EXTENSION", None)
    else:
        os.environ["FF_ENABLE_HOOKS_MCP_EXTENSION"] = original


@pytest.fixture
def mock_auth_admin():
    """Create mock auth middleware that grants admin access."""
    auth = MagicMock()
    auth.authorize = AsyncMock(return_value=True)
    return auth


@pytest.fixture
def mock_auth_non_admin():
    """Create mock auth middleware that denies admin access."""
    auth = MagicMock()
    auth.authorize = AsyncMock(return_value=False)
    return auth


@pytest.fixture
def mock_agent_graph():
    """Create mock agent graph."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"messages": []})
    return graph


@pytest.fixture
def fresh_registry():
    """Create a fresh hook registry for each test."""
    reset_hook_registry()
    registry = HookRegistry()
    yield registry
    reset_hook_registry()
    gc.collect()


@pytest.mark.xdist_group(name="mcp_hooks_extension")
class TestHooksExtensionListOperation:
    """Integration tests for hooks/list operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_returns_empty_when_no_hooks_registered(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN no hooks are registered
        WHEN calling hooks tool with operation=list
        THEN should return empty list.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="user@test.com",
        )

        assert len(result) == 1
        hooks = json.loads(result[0].text)
        assert hooks == []

    @pytest.mark.asyncio
    async def test_list_returns_registered_hooks(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN hooks are registered in registry
        WHEN calling hooks tool with operation=list
        THEN should return all registered hooks.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        # Register a hook
        async def test_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        fresh_registry.register(
            event=HookEvent.PRE_TOOL_USE,
            matcher=HookMatcher(hooks=[test_hook], matcher="test_*", timeout=30.0),
        )

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="user@test.com",
        )

        hooks = json.loads(result[0].text)
        assert len(hooks) == 1
        assert hooks[0]["event"] == "PRE_TOOL_USE"
        assert hooks[0]["matcher"] == "test_*"
        assert hooks[0]["hook_count"] == 1

    @pytest.mark.asyncio
    async def test_list_filters_by_event_type(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN hooks registered for multiple events
        WHEN calling list with event filter
        THEN should only return matching hooks.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        async def test_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        # Register hooks for multiple events
        fresh_registry.register(
            event=HookEvent.PRE_TOOL_USE,
            matcher=HookMatcher(hooks=[test_hook]),
        )
        fresh_registry.register(
            event=HookEvent.POST_TOOL_USE,
            matcher=HookMatcher(hooks=[test_hook]),
        )

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={"operation": "list", "event": "PRE_TOOL_USE"},
            span=MagicMock(),
            user_id="user@test.com",
        )

        hooks = json.loads(result[0].text)
        assert len(hooks) == 1
        assert hooks[0]["event"] == "PRE_TOOL_USE"


@pytest.mark.xdist_group(name="mcp_hooks_extension")
class TestHooksExtensionEventsOperation:
    """Integration tests for hooks/events operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_events_returns_all_hook_events(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN hooks tool handler
        WHEN calling operation=events
        THEN should return all 10 hook event types.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={"operation": "events"},
            span=MagicMock(),
            user_id="user@test.com",
        )

        events = json.loads(result[0].text)

        # Should have all 10 hook events
        event_names = {e["event"] for e in events}
        expected_events = {
            "PRE_TOOL_USE",
            "POST_TOOL_USE",
            "BEFORE_MODEL",
            "AFTER_MODEL",
            "SESSION_START",
            "SESSION_END",
            "USER_PROMPT_SUBMIT",
            "STOP",
            "SUBAGENT_STOP",
            "PRE_COMPACT",
        }
        assert event_names == expected_events

    @pytest.mark.asyncio
    async def test_events_include_descriptions(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN hooks tool handler
        WHEN calling operation=events
        THEN each event should have a non-empty description.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={"operation": "events"},
            span=MagicMock(),
            user_id="user@test.com",
        )

        events = json.loads(result[0].text)

        for event in events:
            assert "event" in event
            assert "description" in event
            assert len(event["description"]) > 10  # Meaningful description


@pytest.mark.xdist_group(name="mcp_hooks_extension")
class TestHooksExtensionRegisterOperation:
    """Integration tests for hooks/register operation (admin only)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_register_requires_admin_authorization(
        self, mock_auth_non_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN a non-admin user
        WHEN calling hooks/register
        THEN should return unauthorized error.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_non_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "PRE_TOOL_USE",
                "webhook_url": "https://example.com/webhook",
            },
            span=MagicMock(),
            user_id="user@test.com",
        )

        assert "Unauthorized" in result[0].text
        mock_auth_non_admin.authorize.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_succeeds_for_admin(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN an admin user
        WHEN calling hooks/register with valid params
        THEN should register the hook and return success.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "PRE_TOOL_USE",
                "webhook_url": "https://example.com/webhook",
            },
            span=MagicMock(),
            user_id="admin@test.com",
        )

        assert "registered" in result[0].text.lower()

        # Verify hook was actually registered
        matchers = fresh_registry.get_matchers(HookEvent.PRE_TOOL_USE)
        assert len(matchers) >= 1

    @pytest.mark.asyncio
    async def test_register_validates_event_name(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN an admin user
        WHEN calling hooks/register with invalid event name
        THEN should return error.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "INVALID_EVENT",
                "webhook_url": "https://example.com/webhook",
            },
            span=MagicMock(),
            user_id="admin@test.com",
        )

        assert "error" in result[0].text.lower() or "unknown" in result[0].text.lower()


@pytest.mark.xdist_group(name="mcp_hooks_extension")
class TestHooksExtensionUnregisterOperation:
    """Integration tests for hooks/unregister operation (admin only)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unregister_requires_admin_authorization(
        self, mock_auth_non_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN a non-admin user
        WHEN calling hooks/unregister
        THEN should return unauthorized error.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_non_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "unregister",
                "event": "PRE_TOOL_USE",
            },
            span=MagicMock(),
            user_id="user@test.com",
        )

        assert "Unauthorized" in result[0].text

    @pytest.mark.asyncio
    async def test_unregister_removes_hooks_for_event(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN hooks registered for an event
        WHEN admin calls hooks/unregister
        THEN should remove all hooks for that event.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        # Register a hook first
        async def test_hook(input_data, tool_use_id, context):
            from mcp_server_langgraph.core.hooks import HookResult

            return HookResult(behavior="allow")

        fresh_registry.register(
            event=HookEvent.PRE_TOOL_USE,
            matcher=HookMatcher(hooks=[test_hook]),
        )

        # Verify hook is registered
        assert len(fresh_registry.get_matchers(HookEvent.PRE_TOOL_USE)) >= 1

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        result = await handler.handle(
            arguments={
                "operation": "unregister",
                "event": "PRE_TOOL_USE",
            },
            span=MagicMock(),
            user_id="admin@test.com",
        )

        assert "unregistered" in result[0].text.lower()

        # Verify hooks were removed
        assert len(fresh_registry.get_matchers(HookEvent.PRE_TOOL_USE)) == 0


@pytest.mark.xdist_group(name="mcp_hooks_extension")
class TestHooksExtensionEndToEnd:
    """End-to-end integration tests for hooks extension."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_lifecycle_register_list_unregister(
        self, mock_auth_admin, mock_agent_graph, fresh_registry
    ) -> None:
        """
        GIVEN an admin user
        WHEN registering, listing, then unregistering a hook
        THEN the full lifecycle should work correctly.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import HooksToolHandler

        handler = HooksToolHandler(
            auth=mock_auth_admin,
            agent_graph=mock_agent_graph,
            hook_registry=fresh_registry,
        )

        # Step 1: Verify empty initially
        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="admin@test.com",
        )
        hooks = json.loads(result[0].text)
        assert len(hooks) == 0

        # Step 2: Register a hook
        result = await handler.handle(
            arguments={
                "operation": "register",
                "event": "BEFORE_MODEL",
                "webhook_url": "https://hooks.example.com/model",
            },
            span=MagicMock(),
            user_id="admin@test.com",
        )
        assert "registered" in result[0].text.lower()

        # Step 3: List should show the hook
        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="admin@test.com",
        )
        hooks = json.loads(result[0].text)
        assert len(hooks) == 1
        assert hooks[0]["event"] == "BEFORE_MODEL"

        # Step 4: Unregister
        result = await handler.handle(
            arguments={
                "operation": "unregister",
                "event": "BEFORE_MODEL",
            },
            span=MagicMock(),
            user_id="admin@test.com",
        )
        assert "unregistered" in result[0].text.lower()

        # Step 5: List should be empty again
        result = await handler.handle(
            arguments={"operation": "list"},
            span=MagicMock(),
            user_id="admin@test.com",
        )
        hooks = json.loads(result[0].text)
        assert len(hooks) == 0
