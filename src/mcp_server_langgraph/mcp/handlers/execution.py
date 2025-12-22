"""
Execution Tool Handler

Handles code execution and tool search operations.
Implements secure sandboxed execution with validation.

Claude Agent SDK Integration:
- File checkpointing for rollback capability (when enabled)
- Creates checkpoints before code execution
- Clears checkpoints after successful execution
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.hook_registry import HookRegistry
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer

if TYPE_CHECKING:
    from mcp_server_langgraph.core.file_rewind import FileRewind

# Tool names for hook matching
EXECUTE_PYTHON_TOOL_NAME = "execute_python"
SEARCH_TOOLS_TOOL_NAME = "search_tools"


class ExecutionToolHandler(AbstractToolHandler):
    """
    Handler for execution-related tool operations.

    Implements:
    - execute_python: Secure sandboxed Python execution
    - search_tools: Progressive tool discovery

    Claude Agent SDK Integration:
    - Optional file checkpointing for rollback capability
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
        file_rewind: FileRewind | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        """
        Initialize execution handler with dependencies.

        Args:
            auth: Authentication middleware
            agent_graph: The agent graph for execution
            file_rewind: Optional FileRewind for checkpointing (SDK pattern)
            hook_registry: Optional hook registry for SDK hook integration
        """
        super().__init__(auth, agent_graph, hook_registry=hook_registry)
        self._file_rewind = file_rewind

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle execution tool invocation.

        Dispatches to execute_python or search_tools based on arguments.
        Includes hook dispatch for PreToolUse and PostToolUse.
        """
        # Determine tool name based on arguments
        tool_name = EXECUTE_PYTHON_TOOL_NAME if "code" in arguments else SEARCH_TOOLS_TOOL_NAME

        # Create hook context
        request_id = str(span.get_span_context().trace_id) if span.get_span_context() else None
        hook_context = self.get_hook_context(
            session_id=arguments.get("execution_id", "default"),
            user_id=user_id,
            request_id=request_id,
        )

        # Dispatch PreToolUse hook
        pre_result = await self.dispatch_pre_handler_hook(
            tool_name=tool_name,
            tool_input=arguments,
            context=hook_context,
        )

        # Check for deny from pre-hook
        if not pre_result.should_proceed:
            deny_message = pre_result.message or "Execution blocked by policy"
            logger.warning(
                "Execution blocked by pre-hook",
                extra={"user_id": user_id, "tool": tool_name, "reason": deny_message},
            )
            return [TextContent(type="text", text=f"Request denied: {deny_message}")]

        try:
            if "code" in arguments:
                result = await self.handle_execute_python(arguments, span, user_id)
            else:
                result = await self.handle_search_tools(arguments, span)

            # Dispatch PostToolUse hook (success case)
            result_text = result[0].text if result else ""
            await self.dispatch_post_handler_hook(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=result_text,
                is_error=False,
                context=hook_context,
            )

            return result

        except Exception as e:
            # Dispatch PostToolUse hook (error case)
            await self.dispatch_post_handler_hook(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=f"Error: {e!s}",
                is_error=True,
                context=hook_context,
            )
            raise

    async def handle_search_tools(
        self,
        arguments: dict[str, Any],
        span: Any,
    ) -> list[TextContent]:
        """
        Handle search_tools invocation for progressive tool discovery.

        Implements Anthropic best practice for token-efficient tool discovery.
        """
        with tracer.start_as_current_span("tools.search"):
            from mcp_server_langgraph.tools.tool_discovery import search_tools

            query = arguments.get("query")
            category = arguments.get("category")
            detail_level = arguments.get("detail_level", "minimal")

            logger.info(
                "Searching tools",
                extra={"query": query, "category": category, "detail_level": detail_level},
            )

            result = search_tools.invoke(
                {
                    "query": query,
                    "category": category,
                    "detail_level": detail_level,
                }
            )

            span.set_attribute("tools.query", query or "")
            span.set_attribute("tools.category", category or "")
            span.set_attribute("tools.detail_level", detail_level)

            return [TextContent(type="text", text=result)]

    async def handle_execute_python(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle execute_python invocation for secure code execution.

        Implements sandboxed Python execution with validation and resource limits.

        Claude Agent SDK Integration:
        - Creates checkpoint before execution when file checkpointing is enabled
        - Clears checkpoint after successful execution
        - Records checkpoint_id in span for observability
        """
        with tracer.start_as_current_span("code.execute"):
            from mcp_server_langgraph.tools.code_execution_tools import execute_python

            code = arguments.get("code", "")
            timeout = arguments.get("timeout")
            execution_id = arguments.get("execution_id", "unknown")

            # Create checkpoint if file checkpointing is enabled (Claude Agent SDK pattern)
            checkpoint_id: str | None = None
            if self._file_rewind and feature_flags.enable_sdk_file_checkpointing:
                checkpoint_id = await self._file_rewind.checkpoint(execution_id)
                span.set_attribute("code.checkpoint_id", checkpoint_id)
                logger.debug(
                    "Created file checkpoint for code execution",
                    extra={"checkpoint_id": checkpoint_id, "execution_id": execution_id},
                )

            logger.info(
                "Executing Python code",
                extra={
                    "user_id": user_id,
                    "code_length": len(code),
                    "timeout": timeout,
                    "checkpoint_id": checkpoint_id,
                },
            )

            start_time = time.time()
            result = execute_python.invoke({"code": code, "timeout": timeout})
            execution_time = time.time() - start_time

            span.set_attribute("code.length", len(code))
            span.set_attribute("code.execution_time", execution_time)
            span.set_attribute("code.success", "success" in result.lower())

            metrics.code_executions.add(1, {"user_id": user_id, "success": "success" in result.lower()})

            # Clear checkpoint after successful execution (SDK pattern)
            if checkpoint_id and self._file_rewind:
                from mcp_server_langgraph.core.file_journal import get_file_journal

                journal = get_file_journal()
                await journal.clear_checkpoint(checkpoint_id)
                logger.debug(
                    "Cleared file checkpoint after execution",
                    extra={"checkpoint_id": checkpoint_id},
                )

            return [TextContent(type="text", text=result)]
