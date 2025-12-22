"""
Claude Agent SDK Integration

SDK-agnostic interface for agent orchestration that can adapt
to future Claude Agent SDK.

Provides:
- LangGraphAgentClient: Unified agent client
- InProcessToolServer: Fast in-process tool execution
- SecurityHookRegistry: Pre-tool-use security hooks
- UnifiedHookRegistry: Unified registry bridging SDK and core hooks
- AgentStateManager: Cross-session state management

Hook Types Supported:
- PreToolUse: Before tool execution (validate, modify input, deny)
- PostToolUse: After tool execution (audit, transform output)
- UserPromptSubmit: When user submits prompt (modify, log)
- Stop: When agent stops (cleanup, logging)

Usage:
    from mcp_server_langgraph.sdk import LangGraphAgentClient

    client = LangGraphAgentClient(model_tier="complex")
    response = await client.query("What is 2 + 2?")
"""

from mcp_server_langgraph.sdk.client import LangGraphAgentClient
from mcp_server_langgraph.sdk.hook_adapter import (
    RegisteredHook,
    UnifiedHookAdapter,
    UnifiedHookRegistry,
)
from mcp_server_langgraph.sdk.hooks import (
    DEFAULT_SECURITY_HOOKS,
    HookResult,
    PreToolUseHook,
    SecurityHookRegistry,
    command_allowlist_hook,
    pii_detection_hook,
    rate_limit_hook,
)
from mcp_server_langgraph.sdk.state import AgentStateManager
from mcp_server_langgraph.sdk.tools import (
    InProcessToolServer,
    ToolDefinition,
    create_default_server,
    search_tools_tool,
    think_tool,
)

__all__ = [
    # Client
    "LangGraphAgentClient",
    # Tools
    "InProcessToolServer",
    "ToolDefinition",
    "create_default_server",
    "think_tool",
    "search_tools_tool",
    # Hooks (legacy SDK)
    "HookResult",
    "PreToolUseHook",
    "SecurityHookRegistry",
    "DEFAULT_SECURITY_HOOKS",
    "pii_detection_hook",
    "command_allowlist_hook",
    "rate_limit_hook",
    # Hooks (unified adapter)
    "UnifiedHookAdapter",
    "UnifiedHookRegistry",
    "RegisteredHook",
    # State
    "AgentStateManager",
]
