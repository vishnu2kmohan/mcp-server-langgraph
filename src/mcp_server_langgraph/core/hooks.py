"""
Hook system for tool execution lifecycle (Claude Agent SDK pattern)

This module implements an LLM-agnostic hook system inspired by the Claude Agent SDK.
Hooks provide lifecycle interception points for tool execution and agent operations.

Hook Types:
- PreToolUse: Before tool execution (validate, modify input, deny)
- PostToolUse: After tool execution (audit, transform output)
- UserPromptSubmit: When user submits prompt (modify, log)
- Stop: When agent stops (cleanup, logging)
- SubagentStop: When a subagent stops
- PreCompact: Before message compaction

Usage:
    from mcp_server_langgraph.core.hooks import (
        HookEvent,
        HookContext,
        HookResult,
        HookMatcher,
        PreToolUseInput,
    )

    async def validate_command(
        input_data: PreToolUseInput,
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookResult:
        if "rm -rf /" in input_data.tool_input.get("command", ""):
            return HookResult(behavior="deny", message="Dangerous command blocked")
        return HookResult(behavior="allow")

    matcher = HookMatcher(matcher="Bash", hooks=[validate_command])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Awaitable


class HookEvent(Enum):
    """Hook event types matching Claude Agent SDK.

    Tool-level hooks:
        PRE_TOOL_USE: Before tool execution
        POST_TOOL_USE: After tool execution

    LLM-level hooks (ADR-0080):
        BEFORE_MODEL: Before LLM call (can modify prompt, cache, skip)
        AFTER_MODEL: After LLM response (can filter output, add disclaimers)

    Session-level hooks:
        SESSION_START: Session begins
        SESSION_END: Session ends

    Agent-level hooks:
        USER_PROMPT_SUBMIT: When user submits prompt
        STOP: When agent stops
        SUBAGENT_STOP: When a subagent stops
        PRE_COMPACT: Before message compaction
    """

    # Tool-level hooks
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"

    # LLM-level hooks (ADR-0080)
    BEFORE_MODEL = "BeforeModel"
    AFTER_MODEL = "AfterModel"

    # Session-level hooks (ADR-0080)
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"

    # Agent-level hooks
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"


@dataclass(frozen=True)
class HookContext:
    """Context information passed to hook callbacks.

    Provides session and request context for hooks to make informed decisions.
    """

    session_id: str
    user_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """Result returned from hook callbacks.

    Determines whether to proceed with the operation and any modifications.

    Attributes:
        behavior: "allow" to proceed, "deny" to block, "skip" to bypass operation
        message: Reason for deny/skip (displayed to user)
        updated_input: Modified input args (for PreToolUse/BeforeModel)
        system_message: Message to add to transcript
        early_return: Cached/predefined response to return (skips LLM call)
        modified_output: Transformed output content (for AfterModel)
    """

    behavior: Literal["allow", "deny", "skip"] = "allow"
    message: str | None = None
    updated_input: dict[str, Any] | None = None
    system_message: str | None = None
    early_return: Any | None = None
    modified_output: str | None = None

    @property
    def should_proceed(self) -> bool:
        """Whether the operation should proceed."""
        return self.behavior == "allow"

    @property
    def should_skip(self) -> bool:
        """Whether to skip the operation and use early_return."""
        return self.behavior == "skip" and self.early_return is not None


@dataclass
class PreToolUseInput:
    """Input data for PreToolUse hooks.

    Provides tool name and arguments before execution.
    """

    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str | None = None


@dataclass
class PostToolUseInput:
    """Input data for PostToolUse hooks.

    Provides tool name, arguments, and output after execution.
    """

    tool_name: str
    tool_input: dict[str, Any]
    tool_output: str
    tool_use_id: str | None = None
    is_error: bool = False


@dataclass
class UserPromptSubmitInput:
    """Input data for UserPromptSubmit hooks.

    Provides the user's prompt before processing.
    """

    prompt: str
    timestamp: datetime | None = None


@dataclass
class StopInput:
    """Input data for Stop hooks.

    Provides information about why the agent stopped.
    """

    reason: str
    is_error: bool = False
    result: str | None = None


@dataclass
class TokenUsage:
    """Token usage information for LLM calls.

    Tracks prompt and completion token counts for cost tracking and monitoring.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class BeforeModelInput:
    """Input data for BeforeModel hooks (ADR-0080).

    Provides LLM request details before execution. Hooks can:
    - Modify the request (prompt injection, context addition)
    - Return cached response (skip LLM call entirely)
    - Block forbidden content before token spend
    """

    messages: list[dict[str, Any]]
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AfterModelInput:
    """Input data for AfterModel hooks (ADR-0080).

    Provides LLM response details after execution. Hooks can:
    - Filter or redact output content
    - Add disclaimers or formatting
    - Transform response structure
    """

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: TokenUsage | None = None
    model: str = ""
    finish_reason: str = ""
    latency_ms: float = 0.0


@dataclass
class SessionStartInput:
    """Input data for SessionStart hooks (ADR-0080).

    Provides session initialization context. Hooks can:
    - Validate session parameters
    - Initialize session-specific resources
    - Set up monitoring/logging
    """

    session_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None


@dataclass
class SessionEndInput:
    """Input data for SessionEnd hooks (ADR-0080).

    Provides session completion context. Hooks can:
    - Clean up session resources
    - Record session metrics
    - Persist session state
    """

    session_id: str
    user_id: str | None = None
    duration_ms: float = 0.0
    message_count: int = 0
    token_usage: TokenUsage | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Type alias for hook input types
HookInput: TypeAlias = (
    PreToolUseInput
    | PostToolUseInput
    | UserPromptSubmitInput
    | StopInput
    | BeforeModelInput
    | AfterModelInput
    | SessionStartInput
    | SessionEndInput
)


class HookCallbackProtocol(Protocol):
    """Protocol for hook callback functions."""

    async def __call__(
        self,
        input_data: HookInput,
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookResult: ...


# Type alias for hook callbacks
HookCallback: TypeAlias = Callable[
    [Any, str | None, HookContext],
    "Awaitable[HookResult]",
]


@dataclass
class HookMatcher:
    """Configuration for matching hooks to specific events or tools.

    Attributes:
        matcher: Tool name pattern (regex) or None to match all
        hooks: List of hook callbacks to execute
        timeout: Timeout in seconds for all hooks in this matcher
    """

    hooks: list[HookCallback]
    matcher: str | None = None
    timeout: float = 60.0

    _compiled_pattern: re.Pattern[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Compile the matcher pattern if provided."""
        if self.matcher is not None:
            self._compiled_pattern = re.compile(f"^({self.matcher})$")

    def matches(self, tool_name: str) -> bool:
        """Check if this matcher applies to the given tool.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the hook should be applied to this tool
        """
        if self.matcher is None:
            # No pattern means match all tools
            return True

        if self._compiled_pattern is None:
            # Compile pattern if not already done
            self._compiled_pattern = re.compile(f"^({self.matcher})$")

        return bool(self._compiled_pattern.match(tool_name))


__all__ = [
    "AfterModelInput",
    "BeforeModelInput",
    "HookCallback",
    "HookCallbackProtocol",
    "HookContext",
    "HookEvent",
    "HookInput",
    "HookMatcher",
    "HookResult",
    "PostToolUseInput",
    "PreToolUseInput",
    "SessionEndInput",
    "SessionStartInput",
    "StopInput",
    "TokenUsage",
    "UserPromptSubmitInput",
]
