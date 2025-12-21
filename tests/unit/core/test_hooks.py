"""
Tests for hook protocol and types (Phase 1.1)

Following TDD: Write tests FIRST, then implementation.

This module tests the Claude Agent SDK-inspired hook system that provides
lifecycle hooks for tool execution and agent operations.

Hook Types:
- PreToolUse: Before tool execution (validate, modify input, deny)
- PostToolUse: After tool execution (audit, transform output)
- UserPromptSubmit: When user submits prompt (modify, log)
- Stop: When agent stops (cleanup, logging)
"""

from __future__ import annotations

import gc
from datetime import UTC
from typing import Any

import pytest

# pytestmark placed after all imports
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="hooks")
class TestHookEvent:
    """Test HookEvent enum and types."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_event_enum_has_pre_tool_use(self) -> None:
        """PreToolUse event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.PRE_TOOL_USE is not None
        assert HookEvent.PRE_TOOL_USE.value == "PreToolUse"

    def test_hook_event_enum_has_post_tool_use(self) -> None:
        """PostToolUse event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.POST_TOOL_USE is not None
        assert HookEvent.POST_TOOL_USE.value == "PostToolUse"

    def test_hook_event_enum_has_user_prompt_submit(self) -> None:
        """UserPromptSubmit event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.USER_PROMPT_SUBMIT is not None
        assert HookEvent.USER_PROMPT_SUBMIT.value == "UserPromptSubmit"

    def test_hook_event_enum_has_stop(self) -> None:
        """Stop event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.STOP is not None
        assert HookEvent.STOP.value == "Stop"

    def test_hook_event_enum_has_subagent_stop(self) -> None:
        """SubagentStop event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.SUBAGENT_STOP is not None
        assert HookEvent.SUBAGENT_STOP.value == "SubagentStop"

    def test_hook_event_enum_has_pre_compact(self) -> None:
        """PreCompact event should be defined."""
        from mcp_server_langgraph.core.hooks import HookEvent

        assert HookEvent.PRE_COMPACT is not None
        assert HookEvent.PRE_COMPACT.value == "PreCompact"


@pytest.mark.xdist_group(name="hooks")
class TestHookContext:
    """Test HookContext dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_context_has_session_id(self) -> None:
        """HookContext should have session_id field."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test-session-123")
        assert ctx.session_id == "test-session-123"

    def test_hook_context_has_user_id(self) -> None:
        """HookContext should have optional user_id field."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test", user_id="user:alice")
        assert ctx.user_id == "user:alice"

    def test_hook_context_user_id_defaults_to_none(self) -> None:
        """HookContext user_id should default to None."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test")
        assert ctx.user_id is None

    def test_hook_context_has_request_id(self) -> None:
        """HookContext should have optional request_id for tracing."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test", request_id="req-456")
        assert ctx.request_id == "req-456"

    def test_hook_context_has_metadata(self) -> None:
        """HookContext should have optional metadata dict."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test", metadata={"key": "value"})
        assert ctx.metadata == {"key": "value"}

    def test_hook_context_metadata_defaults_to_empty_dict(self) -> None:
        """HookContext metadata should default to empty dict."""
        from mcp_server_langgraph.core.hooks import HookContext

        ctx = HookContext(session_id="test")
        assert ctx.metadata == {}


@pytest.mark.xdist_group(name="hooks")
class TestHookResult:
    """Test HookResult for hook return values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_result_allow_behavior(self) -> None:
        """HookResult should support 'allow' behavior."""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(behavior="allow")
        assert result.behavior == "allow"
        assert result.should_proceed is True

    def test_hook_result_deny_behavior(self) -> None:
        """HookResult should support 'deny' behavior."""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(behavior="deny", message="Not allowed")
        assert result.behavior == "deny"
        assert result.should_proceed is False
        assert result.message == "Not allowed"

    def test_hook_result_updated_input(self) -> None:
        """HookResult should support updatedInput for modifying tool args."""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(behavior="allow", updated_input={"path": "/safe/path"})
        assert result.updated_input == {"path": "/safe/path"}

    def test_hook_result_system_message(self) -> None:
        """HookResult should support adding system message to transcript."""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult(behavior="allow", system_message="Proceeding with caution")
        assert result.system_message == "Proceeding with caution"

    def test_hook_result_default_behavior_is_allow(self) -> None:
        """HookResult should default to 'allow' behavior."""
        from mcp_server_langgraph.core.hooks import HookResult

        result = HookResult()
        assert result.behavior == "allow"
        assert result.should_proceed is True


@pytest.mark.xdist_group(name="hooks")
class TestPreToolUseInput:
    """Test PreToolUseInput for pre-tool hook data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_pre_tool_use_input_has_tool_name(self) -> None:
        """PreToolUseInput should have tool_name."""
        from mcp_server_langgraph.core.hooks import PreToolUseInput

        input_data = PreToolUseInput(tool_name="Bash", tool_input={"command": "ls"})
        assert input_data.tool_name == "Bash"

    def test_pre_tool_use_input_has_tool_input(self) -> None:
        """PreToolUseInput should have tool_input dict."""
        from mcp_server_langgraph.core.hooks import PreToolUseInput

        input_data = PreToolUseInput(tool_name="Write", tool_input={"file_path": "/test.txt", "content": "hello"})
        assert input_data.tool_input == {"file_path": "/test.txt", "content": "hello"}

    def test_pre_tool_use_input_has_tool_use_id(self) -> None:
        """PreToolUseInput should have optional tool_use_id."""
        from mcp_server_langgraph.core.hooks import PreToolUseInput

        input_data = PreToolUseInput(
            tool_name="Read",
            tool_input={"file_path": "/test.txt"},
            tool_use_id="tool-123",
        )
        assert input_data.tool_use_id == "tool-123"


@pytest.mark.xdist_group(name="hooks")
class TestPostToolUseInput:
    """Test PostToolUseInput for post-tool hook data."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_post_tool_use_input_has_tool_name(self) -> None:
        """PostToolUseInput should have tool_name."""
        from mcp_server_langgraph.core.hooks import PostToolUseInput

        input_data = PostToolUseInput(
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_output="file1.txt\nfile2.txt",
        )
        assert input_data.tool_name == "Bash"

    def test_post_tool_use_input_has_tool_output(self) -> None:
        """PostToolUseInput should have tool_output."""
        from mcp_server_langgraph.core.hooks import PostToolUseInput

        input_data = PostToolUseInput(
            tool_name="calculator",
            tool_input={"expression": "2+2"},
            tool_output="4",
        )
        assert input_data.tool_output == "4"

    def test_post_tool_use_input_has_is_error(self) -> None:
        """PostToolUseInput should have is_error flag."""
        from mcp_server_langgraph.core.hooks import PostToolUseInput

        input_data = PostToolUseInput(
            tool_name="Bash",
            tool_input={"command": "invalid"},
            tool_output="Error: command not found",
            is_error=True,
        )
        assert input_data.is_error is True

    def test_post_tool_use_input_is_error_defaults_false(self) -> None:
        """PostToolUseInput is_error should default to False."""
        from mcp_server_langgraph.core.hooks import PostToolUseInput

        input_data = PostToolUseInput(
            tool_name="Read",
            tool_input={"file_path": "/test.txt"},
            tool_output="content",
        )
        assert input_data.is_error is False


@pytest.mark.xdist_group(name="hooks")
class TestUserPromptSubmitInput:
    """Test UserPromptSubmitInput for prompt submission hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_prompt_submit_input_has_prompt(self) -> None:
        """UserPromptSubmitInput should have prompt."""
        from mcp_server_langgraph.core.hooks import UserPromptSubmitInput

        input_data = UserPromptSubmitInput(prompt="Hello, Claude!")
        assert input_data.prompt == "Hello, Claude!"

    def test_user_prompt_submit_input_has_timestamp(self) -> None:
        """UserPromptSubmitInput should have optional timestamp."""
        from datetime import datetime

        from mcp_server_langgraph.core.hooks import UserPromptSubmitInput

        now = datetime.now(UTC)
        input_data = UserPromptSubmitInput(prompt="Test", timestamp=now)
        assert input_data.timestamp == now


@pytest.mark.xdist_group(name="hooks")
class TestStopInput:
    """Test StopInput for stop event hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_stop_input_has_reason(self) -> None:
        """StopInput should have reason."""
        from mcp_server_langgraph.core.hooks import StopInput

        input_data = StopInput(reason="completed")
        assert input_data.reason == "completed"

    def test_stop_input_has_is_error(self) -> None:
        """StopInput should have is_error flag."""
        from mcp_server_langgraph.core.hooks import StopInput

        input_data = StopInput(reason="error", is_error=True)
        assert input_data.is_error is True

    def test_stop_input_has_result(self) -> None:
        """StopInput should have optional result."""
        from mcp_server_langgraph.core.hooks import StopInput

        input_data = StopInput(reason="completed", result="Task finished successfully")
        assert input_data.result == "Task finished successfully"


@pytest.mark.xdist_group(name="hooks")
class TestHookCallback:
    """Test HookCallback type and protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hook_callback_signature(self) -> None:
        """HookCallback should accept input_data, tool_use_id, context."""
        from mcp_server_langgraph.core.hooks import (
            HookCallback,
            HookContext,
            HookResult,
            PreToolUseInput,
        )

        # Define a callback matching the expected signature
        async def my_hook(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            return HookResult(behavior="allow")

        # Verify it can be used as HookCallback
        callback: HookCallback = my_hook

        # Call it
        result = await callback(
            PreToolUseInput(tool_name="Test", tool_input={}),
            "tool-123",
            HookContext(session_id="session-1"),
        )
        assert result.behavior == "allow"

    @pytest.mark.asyncio
    async def test_hook_callback_can_modify_input(self) -> None:
        """HookCallback should be able to return modified input."""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookResult,
            PreToolUseInput,
        )

        async def sanitize_path(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            # Redirect writes to sandbox
            tool_input = input_data.tool_input.copy()
            if "file_path" in tool_input:
                tool_input["file_path"] = f"/sandbox{tool_input['file_path']}"
            return HookResult(behavior="allow", updated_input=tool_input)

        result = await sanitize_path(
            PreToolUseInput(
                tool_name="Write",
                tool_input={"file_path": "/etc/passwd", "content": "bad"},
            ),
            None,
            HookContext(session_id="test"),
        )

        assert result.updated_input == {"file_path": "/sandbox/etc/passwd", "content": "bad"}

    @pytest.mark.asyncio
    async def test_hook_callback_can_deny(self) -> None:
        """HookCallback should be able to deny tool execution."""
        from mcp_server_langgraph.core.hooks import (
            HookContext,
            HookResult,
            PreToolUseInput,
        )

        async def block_rm_rf(
            input_data: PreToolUseInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookResult:
            if input_data.tool_name == "Bash":
                command = input_data.tool_input.get("command", "")
                if "rm -rf /" in command:
                    return HookResult(
                        behavior="deny",
                        message="Dangerous command blocked",
                    )
            return HookResult(behavior="allow")

        # Test blocking
        result = await block_rm_rf(
            PreToolUseInput(
                tool_name="Bash",
                tool_input={"command": "rm -rf /"},
            ),
            None,
            HookContext(session_id="test"),
        )
        assert result.behavior == "deny"
        assert result.should_proceed is False
        assert result.message == "Dangerous command blocked"

        # Test allowing
        result = await block_rm_rf(
            PreToolUseInput(
                tool_name="Bash",
                tool_input={"command": "ls -la"},
            ),
            None,
            HookContext(session_id="test"),
        )
        assert result.behavior == "allow"
        assert result.should_proceed is True


@pytest.mark.xdist_group(name="hooks")
class TestHookMatcher:
    """Test HookMatcher for matching hooks to tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hook_matcher_with_no_pattern_matches_all(self) -> None:
        """HookMatcher with no pattern should match all tools."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        matcher = HookMatcher(hooks=[])
        assert matcher.matches("Bash") is True
        assert matcher.matches("Write") is True
        assert matcher.matches("Read") is True

    def test_hook_matcher_with_exact_pattern(self) -> None:
        """HookMatcher should match exact tool name."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        matcher = HookMatcher(matcher="Bash", hooks=[])
        assert matcher.matches("Bash") is True
        assert matcher.matches("Write") is False

    def test_hook_matcher_with_regex_pattern(self) -> None:
        """HookMatcher should support regex patterns."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        matcher = HookMatcher(matcher="Write|Edit", hooks=[])
        assert matcher.matches("Write") is True
        assert matcher.matches("Edit") is True
        assert matcher.matches("Read") is False

    def test_hook_matcher_has_timeout(self) -> None:
        """HookMatcher should have configurable timeout."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        matcher = HookMatcher(hooks=[], timeout=120.0)
        assert matcher.timeout == 120.0

    def test_hook_matcher_timeout_defaults_to_60(self) -> None:
        """HookMatcher timeout should default to 60 seconds."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        matcher = HookMatcher(hooks=[])
        assert matcher.timeout == 60.0

    def test_hook_matcher_has_hooks_list(self) -> None:
        """HookMatcher should contain list of hook callbacks."""
        from mcp_server_langgraph.core.hooks import HookMatcher

        async def hook1(input_data: Any, tool_use_id: str | None, context: Any) -> Any:
            return {}

        async def hook2(input_data: Any, tool_use_id: str | None, context: Any) -> Any:
            return {}

        matcher = HookMatcher(matcher="Bash", hooks=[hook1, hook2])
        assert len(matcher.hooks) == 2
