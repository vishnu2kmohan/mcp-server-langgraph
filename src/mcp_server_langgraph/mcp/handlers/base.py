"""
Base Tool Handler Protocol

Defines the interface for MCP tool handlers.
Handlers encapsulate specific domains of functionality.

Includes hook system integration following Claude Agent SDK patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.hook_registry import (
    HookDispatcher,
    HookRegistry,
    get_hook_registry,
)
from mcp_server_langgraph.core.hooks import HookContext, HookResult
from mcp_server_langgraph.observability.telemetry import tracer


@runtime_checkable
class BaseToolHandler(Protocol):
    """Protocol defining the interface for tool handlers."""

    @abstractmethod
    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle a tool invocation.

        Args:
            arguments: Tool arguments from the request
            span: OpenTelemetry span for tracing
            user_id: Authenticated user ID

        Returns:
            List of TextContent responses
        """
        ...


class HookMixin:
    """
    Mixin providing hook dispatch capabilities for handlers.

    Enables PreToolUse and PostToolUse hook integration following
    Claude Agent SDK patterns.
    """

    def __init__(self, hook_registry: HookRegistry | None = None) -> None:
        """
        Initialize hook mixin with registry.

        Args:
            hook_registry: Optional hook registry (uses global if not provided)
        """
        self._hook_registry = hook_registry or get_hook_registry()
        self._hook_dispatcher = HookDispatcher(self._hook_registry)

    def get_hook_context(
        self,
        session_id: str,
        user_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HookContext:
        """
        Create a HookContext for hook dispatch.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier
            request_id: Optional request identifier
            metadata: Optional additional metadata

        Returns:
            HookContext instance
        """
        return HookContext(
            session_id=session_id,
            user_id=user_id,
            request_id=request_id,
            metadata=metadata or {},
        )

    async def dispatch_pre_handler_hook(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: HookContext,
        tool_use_id: str | None = None,
    ) -> HookResult:
        """
        Dispatch PreToolUse hooks before handler execution.

        Args:
            tool_name: Name of the tool/handler being invoked
            tool_input: Input arguments for the tool
            context: Hook context
            tool_use_id: Optional tool use identifier

        Returns:
            HookResult indicating whether to proceed
        """
        return await self._hook_dispatcher.dispatch_pre_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            context=context,
        )

    async def dispatch_post_handler_hook(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: str,
        is_error: bool,
        context: HookContext,
        tool_use_id: str | None = None,
    ) -> HookResult:
        """
        Dispatch PostToolUse hooks after handler execution.

        Args:
            tool_name: Name of the tool/handler that was invoked
            tool_input: Input arguments that were passed
            tool_output: Output from the tool
            is_error: Whether the tool returned an error
            context: Hook context
            tool_use_id: Optional tool use identifier

        Returns:
            HookResult from post-execution hooks
        """
        return await self._hook_dispatcher.dispatch_post_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            tool_use_id=tool_use_id,
            is_error=is_error,
            context=context,
        )


class AbstractToolHandler(HookMixin, ABC):
    """
    Abstract base class for tool handlers.

    Provides common dependencies and utilities for handlers,
    including hook dispatch capabilities.
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        """
        Initialize handler with dependencies.

        Args:
            auth: Authentication/authorization middleware
            agent_graph: LangGraph agent instance
            hook_registry: Optional hook registry (uses global if not provided)
        """
        HookMixin.__init__(self, hook_registry=hook_registry)
        self.auth = auth
        self.agent_graph = agent_graph
        self.tracer = tracer

    @abstractmethod
    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Handle tool invocation."""
        ...
