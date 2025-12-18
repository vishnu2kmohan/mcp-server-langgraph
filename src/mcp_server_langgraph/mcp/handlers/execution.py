"""
Execution Tool Handler

Handles code execution and tool search operations.
Implements secure sandboxed execution with validation.
"""

import time
from typing import Any

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class ExecutionToolHandler(AbstractToolHandler):
    """
    Handler for execution-related tool operations.

    Implements:
    - execute_python: Secure sandboxed Python execution
    - search_tools: Progressive tool discovery
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
    ) -> None:
        """Initialize execution handler with dependencies."""
        super().__init__(auth, agent_graph)

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle execution tool invocation.

        Dispatches to execute_python or search_tools based on arguments.
        """
        if "code" in arguments:
            return await self.handle_execute_python(arguments, span, user_id)
        return await self.handle_search_tools(arguments, span)

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
        """
        with tracer.start_as_current_span("code.execute"):
            from mcp_server_langgraph.tools.code_execution_tools import execute_python

            code = arguments.get("code", "")
            timeout = arguments.get("timeout")

            logger.info(
                "Executing Python code",
                extra={
                    "user_id": user_id,
                    "code_length": len(code),
                    "timeout": timeout,
                },
            )

            start_time = time.time()
            result = execute_python.invoke({"code": code, "timeout": timeout})
            execution_time = time.time() - start_time

            span.set_attribute("code.length", len(code))
            span.set_attribute("code.execution_time", execution_time)
            span.set_attribute("code.success", "success" in result.lower())

            metrics.code_executions.add(1, {"user_id": user_id, "success": "success" in result.lower()})

            return [TextContent(type="text", text=result)]
