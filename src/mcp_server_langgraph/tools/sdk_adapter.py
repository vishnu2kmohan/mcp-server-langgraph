"""
SDK Tool Adapter - Adds Claude Agent SDK capabilities to LangChain tools

This module provides an adapter that wraps LangChain BaseTool instances
to add SDK-compatible features like pre/post hooks, tool_use_id tracking,
and structured output format.

Usage:
    from mcp_server_langgraph.tools.sdk_adapter import SDKToolAdapter, adapt_tool
    from langchain_core.tools import tool

    @tool
    def my_tool(x: str) -> str:
        return x.upper()

    adapter = adapt_tool(my_tool)
    result = await adapter.ainvoke(
        args={"x": "hello"},
        context=HookContext(session_id="123"),
    )
    # result: {"content": [{"type": "text", "text": "HELLO"}]}
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from mcp_server_langgraph.core.hook_registry import (
    HookDispatcher,
    HookRegistry,
    get_hook_registry,
)
from mcp_server_langgraph.core.hooks import (
    HookContext,
)

if TYPE_CHECKING:
    pass


@dataclass
class SDKToolAdapter:
    """Adapter to add SDK capabilities to LangChain tools.

    Wraps a LangChain BaseTool to provide:
    - PreToolUse and PostToolUse hook integration
    - tool_use_id tracking
    - SDK-compatible response format
    - Error handling with structured output

    Attributes:
        tool: The wrapped LangChain tool
        registry: Hook registry for dispatching hooks
        dispatcher: Hook dispatcher for executing hooks
    """

    tool: BaseTool
    registry: HookRegistry = field(default_factory=get_hook_registry)
    dispatcher: HookDispatcher = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the dispatcher with the registry."""
        self.dispatcher = HookDispatcher(self.registry)

    @property
    def name(self) -> str:
        """Get the name of the wrapped tool."""
        return self.tool.name

    @property
    def description(self) -> str:
        """Get the description of the wrapped tool."""
        return self.tool.description

    async def ainvoke(
        self,
        args: dict[str, Any],
        context: HookContext | None = None,
        tool_use_id: str | None = None,
    ) -> dict[str, Any]:
        """Invoke the tool with hook support.

        Args:
            args: Tool input arguments
            context: Hook context for this invocation
            tool_use_id: Optional tool use ID (auto-generated if not provided)

        Returns:
            SDK-compatible response dict with format:
            {
                "content": [{"type": "text", "text": "..."}],
                "is_error": bool,
                "system_message": str | None,
            }
        """
        # Use default context if none provided
        if context is None:
            context = HookContext(session_id="default")

        # Auto-generate tool_use_id if not provided
        if tool_use_id is None:
            tool_use_id = f"tu_{uuid.uuid4().hex[:12]}"

        current_args = args.copy()
        system_message: str | None = None

        # Execute PreToolUse hooks
        pre_result = await self.dispatcher.dispatch_pre_tool_use(
            tool_name=self.name,
            tool_input=current_args,
            tool_use_id=tool_use_id,
            context=context,
        )

        # Handle system message from pre-hook
        if pre_result.system_message is not None:
            system_message = pre_result.system_message

        # Check for deny
        if not pre_result.should_proceed:
            return self._format_error_response(
                message=pre_result.message or "Blocked by pre-hook",
                system_message=system_message,
            )

        # Apply input modifications from pre-hook
        if pre_result.updated_input is not None:
            current_args = pre_result.updated_input

        # Execute the tool
        is_error = False
        try:
            # Always use ainvoke for LangChain tools (handles both sync/async)
            output = await self.tool.ainvoke(current_args)
            output_str = str(output)

        except Exception as e:
            is_error = True
            output_str = f"Error: {e}"

        # Execute PostToolUse hooks
        await self.dispatcher.dispatch_post_tool_use(
            tool_name=self.name,
            tool_input=current_args,
            tool_output=output_str,
            tool_use_id=tool_use_id,
            is_error=is_error,
            context=context,
        )

        # Build response
        return self._format_response(
            text=output_str,
            is_error=is_error,
            system_message=system_message,
        )

    def invoke(
        self,
        args: dict[str, Any],
        context: HookContext | None = None,
        tool_use_id: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous invoke - wraps ainvoke.

        Args:
            args: Tool input arguments
            context: Hook context for this invocation
            tool_use_id: Optional tool use ID

        Returns:
            SDK-compatible response dict
        """
        return asyncio.run(self.ainvoke(args, context, tool_use_id))

    def _format_response(
        self,
        text: str,
        is_error: bool = False,
        system_message: str | None = None,
    ) -> dict[str, Any]:
        """Format response in SDK-compatible format.

        Args:
            text: Response text content
            is_error: Whether this is an error response
            system_message: Optional system message to include

        Returns:
            SDK-formatted response dict
        """
        response: dict[str, Any] = {
            "content": [{"type": "text", "text": text}],
        }

        if is_error:
            response["is_error"] = True

        if system_message is not None:
            response["system_message"] = system_message

        return response

    def _format_error_response(
        self,
        message: str,
        system_message: str | None = None,
    ) -> dict[str, Any]:
        """Format an error response.

        Args:
            message: Error message
            system_message: Optional system message

        Returns:
            SDK-formatted error response dict
        """
        return self._format_response(
            text=message,
            is_error=True,
            system_message=system_message,
        )


def adapt_tool(
    tool: BaseTool,
    registry: HookRegistry | None = None,
) -> SDKToolAdapter:
    """Convenience function to adapt a single LangChain tool.

    Args:
        tool: LangChain tool to adapt
        registry: Optional hook registry (uses global if not provided)

    Returns:
        SDKToolAdapter wrapping the tool
    """
    if registry is not None:
        return SDKToolAdapter(tool=tool, registry=registry)
    return SDKToolAdapter(tool=tool)


def adapt_tools(
    tools: list[BaseTool],
    registry: HookRegistry | None = None,
) -> list[SDKToolAdapter]:
    """Convenience function to adapt multiple LangChain tools.

    Args:
        tools: List of LangChain tools to adapt
        registry: Optional hook registry (uses global if not provided)

    Returns:
        List of SDKToolAdapter instances
    """
    return [adapt_tool(tool, registry) for tool in tools]


__all__ = [
    "SDKToolAdapter",
    "adapt_tool",
    "adapt_tools",
]
