"""Core functionality for MCP server."""

from mcp_server_langgraph.core.agent import AgentState, create_agent_graph
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.core.feature_flags import (
    FeatureFlags,
    feature_flags,
    feature_gated,
)
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
