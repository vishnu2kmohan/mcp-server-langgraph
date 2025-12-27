"""
MCP Resource Registry for managing resources from external MCP servers.

Provides a registry to track, import, and manage resources from multiple
external MCP servers with qualified namespacing to avoid collisions.

Reference: MCP Protocol Specification 2025-11-25
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class MCPResourceDefinition:
    """Definition of a resource from an external MCP server."""

    server_name: str
    """Name of the MCP server providing this resource."""

    uri: str
    """Resource URI as provided by the server."""

    name: str
    """Human-readable name for the resource."""

    description: str | None = None
    """Optional description of the resource."""

    mime_type: str | None = None
    """MIME type of the resource content."""

    qualified_name: str = field(init=False)
    """Fully qualified name in format 'server_name:uri'."""

    def __post_init__(self) -> None:
        """Set qualified_name after initialization."""
        self.qualified_name = f"{self.server_name}:{self.uri}"


class MCPResourceSessionProtocol(Protocol):
    """Protocol for sessions that can list resources."""

    async def list_resources(self) -> list[dict[str, Any]]:
        """Get available resources from the server."""
        ...


class MCPResourceRegistry:
    """Registry for resources from external MCP servers.

    This class manages a catalog of resources from external MCP servers,
    providing unified access with qualified namespacing.

    Example:
        registry = MCPResourceRegistry()

        # Import resources from a session
        resources = await registry.import_resources("github", session)

        # Get all resources
        all_resources = registry.get_resources()

        # Get resources from specific server
        github_resources = registry.get_resources(server_name="github")

        # Get single resource by qualified name
        resource = registry.get_resource("github:repo://owner/repo")
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._resources: dict[str, MCPResourceDefinition] = {}
        self._server_resources: dict[str, list[str]] = {}

    async def import_resources(
        self,
        server_name: str,
        session: MCPResourceSessionProtocol,
    ) -> list[MCPResourceDefinition]:
        """Import resources from an MCP server session.

        Args:
            server_name: Name to identify this server's resources
            session: Session with list_resources capability

        Returns:
            List of resource definitions imported from the server
        """
        logger.info(
            "Importing resources from MCP server",
            extra={"server_name": server_name},
        )

        # Get raw resources from server
        raw_resources = await session.list_resources()

        # Initialize server tracking if needed
        if server_name not in self._server_resources:
            self._server_resources[server_name] = []

        imported_resources: list[MCPResourceDefinition] = []

        for raw_resource in raw_resources:
            resource = MCPResourceDefinition(
                server_name=server_name,
                uri=raw_resource.get("uri", ""),
                name=raw_resource.get("name", ""),
                description=raw_resource.get("description"),
                mime_type=raw_resource.get("mimeType"),
            )

            # Register resource
            self._resources[resource.qualified_name] = resource
            self._server_resources[server_name].append(resource.qualified_name)
            imported_resources.append(resource)

        logger.info(
            "Resources imported from MCP server",
            extra={
                "server_name": server_name,
                "resource_count": len(imported_resources),
            },
        )

        return imported_resources

    def get_resources(
        self,
        server_name: str | None = None,
    ) -> list[MCPResourceDefinition]:
        """Get all resources or resources from a specific server.

        Args:
            server_name: If provided, only return resources from this server

        Returns:
            List of resource definitions
        """
        if server_name is not None:
            qualified_names = self._server_resources.get(server_name, [])
            return [self._resources[qn] for qn in qualified_names if qn in self._resources]

        return list(self._resources.values())

    def get_resource(self, qualified_name: str) -> MCPResourceDefinition | None:
        """Get a specific resource by qualified name.

        Args:
            qualified_name: Fully qualified name in format 'server:uri'

        Returns:
            Resource definition if found, None otherwise
        """
        return self._resources.get(qualified_name)

    def unregister_server(self, server_name: str) -> None:
        """Remove all resources from a server.

        Args:
            server_name: Name of the server to unregister
        """
        if server_name not in self._server_resources:
            return

        # Remove all resources for this server
        for qualified_name in self._server_resources[server_name]:
            self._resources.pop(qualified_name, None)

        del self._server_resources[server_name]

        logger.info(
            "Resources unregistered for MCP server",
            extra={"server_name": server_name},
        )

    def get_server_names(self) -> list[str]:
        """Get names of all servers with registered resources.

        Returns:
            List of server names
        """
        return list(self._server_resources.keys())

    def clear(self) -> None:
        """Clear all resources from the registry."""
        self._resources.clear()
        self._server_resources.clear()
