"""Core functionality for MCP server.

This module uses lazy imports via __getattr__ to avoid loading heavy dependencies
(LangGraph, LLM providers) when only lightweight utilities are needed.
This enables the authz-proxy Docker image to be ~100MB instead of 1.4GB.
"""

from typing import TYPE_CHECKING

# Lightweight imports (no heavy dependencies)
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.core.feature_flags import (
    FeatureFlags,
    feature_flags,
    feature_gated,
)

# TYPE_CHECKING imports for static analysis (mypy, pyright)
# These don't run at runtime, so no heavy deps loaded
if TYPE_CHECKING:
    from mcp_server_langgraph.core.agent import AgentState, create_agent_graph
    from mcp_server_langgraph.core.file_journal import (
        Checkpoint,
        FileChangeRecord,
        FileJournal,
        FileOperation,
        get_file_journal,
        reset_file_journal,
    )
    from mcp_server_langgraph.core.file_rewind import FileRewind, RewindResult
    from mcp_server_langgraph.core.hook_registry import (
        HookDispatcher,
        HookRegistry,
        get_hook_registry,
        reset_hook_registry,
    )
    from mcp_server_langgraph.core.hooks import (
        HookCallbackProtocol,
        HookContext,
        HookEvent,
        HookMatcher,
        HookResult,
        PostToolUseInput,
        PreToolUseInput,
        StopInput,
        UserPromptSubmitInput,
    )
    from mcp_server_langgraph.core.interrupt import (
        InterruptController,
        InterruptedOperationError,
        get_interrupt_controller,
        interrupt_aware_node,
        reset_interrupt_controller,
    )
    from mcp_server_langgraph.core.output_format import (
        OutputFormat,
        OutputFormatType,
        analysis_response_format,
        code_response_format,
        simple_response_format,
    )
    from mcp_server_langgraph.core.schema_validator import SchemaValidator, ValidationResult
    from mcp_server_langgraph.core.session_fork import (
        ForkInfo,
        ForkResult,
        SessionForkManager,
    )
    from mcp_server_langgraph.core import visual_verification_helper
    from mcp_server_langgraph.core.visual_verification_helper import (
        combine_verification_results,
        extract_urls_from_text,
        perform_visual_verification,
        prioritize_urls,
    )

__all__ = [
    # Agent
    "AgentState",
    "create_agent_graph",
    # Config
    "Settings",
    "settings",
    # Feature Flags
    "FeatureFlags",
    "feature_flags",
    "feature_gated",
    # Hooks (SDK Pattern)
    "HookCallbackProtocol",
    "HookContext",
    "HookDispatcher",
    "HookEvent",
    "HookMatcher",
    "HookRegistry",
    "HookResult",
    "PostToolUseInput",
    "PreToolUseInput",
    "StopInput",
    "UserPromptSubmitInput",
    "get_hook_registry",
    "reset_hook_registry",
    # Interrupt (SDK Pattern)
    "InterruptController",
    "InterruptedOperationError",
    "get_interrupt_controller",
    "interrupt_aware_node",
    "reset_interrupt_controller",
    # File Checkpointing (SDK Pattern)
    "Checkpoint",
    "FileChangeRecord",
    "FileJournal",
    "FileOperation",
    "FileRewind",
    "RewindResult",
    "get_file_journal",
    "reset_file_journal",
    # Output Validation (SDK Pattern)
    "OutputFormat",
    "OutputFormatType",
    "SchemaValidator",
    "ValidationResult",
    "analysis_response_format",
    "code_response_format",
    "simple_response_format",
    # Visual Verification Helper
    "visual_verification_helper",
    "combine_verification_results",
    "extract_urls_from_text",
    "perform_visual_verification",
    "prioritize_urls",
    # Session Fork (Claude Agent SDK parity)
    "ForkInfo",
    "ForkResult",
    "SessionForkManager",
]


# =============================================================================
# Lazy Import Handler
# =============================================================================
# Heavy modules (LangGraph, LLM providers) are loaded only when accessed.
# This reduces authz-proxy Docker image from 1.4GB to ~100MB.


def __getattr__(name: str):  # type: ignore[no-untyped-def]  # noqa: C901
    """
    Lazy import handler for heavy dependencies.

    Modules are only loaded when their exports are first accessed.
    This prevents loading LangGraph/LLM providers when only config is needed.
    """
    # Agent module (heavy - imports LangGraph)
    if name in ("AgentState", "create_agent_graph"):
        from mcp_server_langgraph.core import agent

        return getattr(agent, name)

    # File journal (imports msgspec, etc.)
    if name in (
        "Checkpoint",
        "FileChangeRecord",
        "FileJournal",
        "FileOperation",
        "get_file_journal",
        "reset_file_journal",
    ):
        from mcp_server_langgraph.core import file_journal

        return getattr(file_journal, name)

    # File rewind
    if name in ("FileRewind", "RewindResult"):
        from mcp_server_langgraph.core import file_rewind

        return getattr(file_rewind, name)

    # Hook registry
    if name in ("HookDispatcher", "HookRegistry", "get_hook_registry", "reset_hook_registry"):
        from mcp_server_langgraph.core import hook_registry

        return getattr(hook_registry, name)

    # Hooks
    if name in (
        "HookCallbackProtocol",
        "HookContext",
        "HookEvent",
        "HookMatcher",
        "HookResult",
        "PostToolUseInput",
        "PreToolUseInput",
        "StopInput",
        "UserPromptSubmitInput",
    ):
        from mcp_server_langgraph.core import hooks

        return getattr(hooks, name)

    # Interrupt
    if name in (
        "InterruptController",
        "InterruptedOperationError",
        "get_interrupt_controller",
        "interrupt_aware_node",
        "reset_interrupt_controller",
    ):
        from mcp_server_langgraph.core import interrupt

        return getattr(interrupt, name)

    # Output format
    if name in (
        "OutputFormat",
        "OutputFormatType",
        "analysis_response_format",
        "code_response_format",
        "simple_response_format",
    ):
        from mcp_server_langgraph.core import output_format

        return getattr(output_format, name)

    # Schema validator
    if name in ("SchemaValidator", "ValidationResult"):
        from mcp_server_langgraph.core import schema_validator

        return getattr(schema_validator, name)

    # Session fork
    if name in ("ForkInfo", "ForkResult", "SessionForkManager"):
        from mcp_server_langgraph.core import session_fork

        return getattr(session_fork, name)

    # Visual verification helper - use importlib to avoid recursion
    if name == "visual_verification_helper":
        import importlib

        return importlib.import_module("mcp_server_langgraph.core.visual_verification_helper")

    if name in (
        "combine_verification_results",
        "extract_urls_from_text",
        "perform_visual_verification",
        "prioritize_urls",
    ):
        import importlib

        vvh = importlib.import_module("mcp_server_langgraph.core.visual_verification_helper")
        return getattr(vvh, name)

    # Not found
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
