"""
Base Tool Handler Protocol

Defines the interface for MCP tool handlers.
Handlers encapsulate specific domains of functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
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


class AbstractToolHandler(ABC):
    """
    Abstract base class for tool handlers.

    Provides common dependencies and utilities for handlers.
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
    ) -> None:
        """
        Initialize handler with dependencies.

        Args:
            auth: Authentication/authorization middleware
            agent_graph: LangGraph agent instance
        """
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
