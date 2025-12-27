"""
MCP Prompt Registry for managing prompts from external MCP servers.

Provides a registry to track, import, and manage prompts from multiple
external MCP servers with qualified namespacing to avoid collisions.

Reference: MCP Protocol Specification 2025-11-25
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class MCPPromptDefinition:
    """Definition of a prompt from an external MCP server."""

    server_name: str
    """Name of the MCP server providing this prompt."""

    name: str
    """Prompt name as provided by the server."""

    description: str | None = None
    """Human-readable description of the prompt."""

    arguments: list[dict[str, Any]] = field(default_factory=list)
    """List of argument definitions for the prompt."""

    qualified_name: str = field(init=False)
    """Fully qualified name in format 'server_name:name'."""

    def __post_init__(self) -> None:
        """Set qualified_name after initialization."""
        self.qualified_name = f"{self.server_name}:{self.name}"


class MCPPromptSessionProtocol(Protocol):
    """Protocol for sessions that can list prompts."""

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Get available prompts from the server."""
        ...


class MCPPromptRegistry:
    """Registry for prompts from external MCP servers.

    This class manages a catalog of prompts from external MCP servers,
    providing unified access with qualified namespacing.

    Example:
        registry = MCPPromptRegistry()

        # Import prompts from a session
        prompts = await registry.import_prompts("code-assistant", session)

        # Get all prompts
        all_prompts = registry.get_prompts()

        # Get prompts from specific server
        assistant_prompts = registry.get_prompts(server_name="code-assistant")

        # Get single prompt by qualified name
        prompt = registry.get_prompt("code-assistant:code_review")
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._prompts: dict[str, MCPPromptDefinition] = {}
        self._server_prompts: dict[str, list[str]] = {}

    async def import_prompts(
        self,
        server_name: str,
        session: MCPPromptSessionProtocol,
    ) -> list[MCPPromptDefinition]:
        """Import prompts from an MCP server session.

        Args:
            server_name: Name to identify this server's prompts
            session: Session with list_prompts capability

        Returns:
            List of prompt definitions imported from the server
        """
        logger.info(
            "Importing prompts from MCP server",
            extra={"server_name": server_name},
        )

        # Get raw prompts from server
        raw_prompts = await session.list_prompts()

        # Initialize server tracking if needed
        if server_name not in self._server_prompts:
            self._server_prompts[server_name] = []

        imported_prompts: list[MCPPromptDefinition] = []

        for raw_prompt in raw_prompts:
            prompt = MCPPromptDefinition(
                server_name=server_name,
                name=raw_prompt.get("name", ""),
                description=raw_prompt.get("description"),
                arguments=raw_prompt.get("arguments", []),
            )

            # Register prompt
            self._prompts[prompt.qualified_name] = prompt
            self._server_prompts[server_name].append(prompt.qualified_name)
            imported_prompts.append(prompt)

        logger.info(
            "Prompts imported from MCP server",
            extra={
                "server_name": server_name,
                "prompt_count": len(imported_prompts),
            },
        )

        return imported_prompts

    def get_prompts(
        self,
        server_name: str | None = None,
    ) -> list[MCPPromptDefinition]:
        """Get all prompts or prompts from a specific server.

        Args:
            server_name: If provided, only return prompts from this server

        Returns:
            List of prompt definitions
        """
        if server_name is not None:
            qualified_names = self._server_prompts.get(server_name, [])
            return [self._prompts[qn] for qn in qualified_names if qn in self._prompts]

        return list(self._prompts.values())

    def get_prompt(self, qualified_name: str) -> MCPPromptDefinition | None:
        """Get a specific prompt by qualified name.

        Args:
            qualified_name: Fully qualified name in format 'server:name'

        Returns:
            Prompt definition if found, None otherwise
        """
        return self._prompts.get(qualified_name)

    def unregister_server(self, server_name: str) -> None:
        """Remove all prompts from a server.

        Args:
            server_name: Name of the server to unregister
        """
        if server_name not in self._server_prompts:
            return

        # Remove all prompts for this server
        for qualified_name in self._server_prompts[server_name]:
            self._prompts.pop(qualified_name, None)

        del self._server_prompts[server_name]

        logger.info(
            "Prompts unregistered for MCP server",
            extra={"server_name": server_name},
        )

    def get_server_names(self) -> list[str]:
        """Get names of all servers with registered prompts.

        Returns:
            List of server names
        """
        return list(self._server_prompts.keys())

    def clear(self) -> None:
        """Clear all prompts from the registry."""
        self._prompts.clear()
        self._server_prompts.clear()
