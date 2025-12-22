"""
MCP Tool Handlers Module

Provides decomposed handlers for MCP server tool operations.
Each handler is responsible for a specific domain of functionality.

Architecture:
- BaseToolHandler: Protocol defining the handler interface
- ChatToolHandler: Handles agent_chat operations
- ConversationToolHandler: Handles get_conversation and search_conversations
- ExecutionToolHandler: Handles execute_python operations
- SkillsToolHandler: Handles skills/list, skills/get, skills/execute
- AgentsToolHandler: Handles agents/orchestrate, agents/decompose, agents/status
- HooksToolHandler: Handles hooks/list, hooks/events operations
"""

from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler
from mcp_server_langgraph.mcp.handlers.base import BaseToolHandler
from mcp_server_langgraph.mcp.handlers.chat import ChatToolHandler
from mcp_server_langgraph.mcp.handlers.conversation import ConversationToolHandler
from mcp_server_langgraph.mcp.handlers.execution import ExecutionToolHandler
from mcp_server_langgraph.mcp.handlers.hooks import (
    HooksToolHandler,
    create_hooks_tool_handler,
)
from mcp_server_langgraph.mcp.handlers.orchestration import (
    OrchestrationToolHandler,
    create_orchestration_tool_handler,
)
from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

__all__ = [
    "BaseToolHandler",
    "ChatToolHandler",
    "ConversationToolHandler",
    "ExecutionToolHandler",
    "SkillsToolHandler",
    "AgentsToolHandler",
    "HooksToolHandler",
    "create_hooks_tool_handler",
    "OrchestrationToolHandler",
    "create_orchestration_tool_handler",
]
