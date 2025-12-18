"""
Connection Factory for Test Data Generation.

Provides factory functions for creating test MCP connection objects.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4


AuthType = Literal["none", "api_key", "oauth2"]
ConnectionStatus = Literal["disconnected", "connecting", "connected", "error", "auth_required"]
TransportProtocol = Literal["streamable_http", "stdio"]


class ConnectionFactory:
    """Factory for creating test MCP connection objects."""

    @staticmethod
    def create(
        connection_id: str | None = None,
        name: str = "Test Connection",
        description: str | None = "A test MCP connection",
        url: str = "https://mcp.example.com/api",
        transport: TransportProtocol = "streamable_http",
        auth_type: AuthType = "none",
        status: ConnectionStatus = "connected",
        owner_id: str = "alice",
        organization_id: str | None = None,
        project_id: str | None = None,
        server_name: str | None = "Test MCP Server",
        server_version: str | None = "1.0.0",
        tool_count: int = 5,
        resource_count: int = 3,
        prompt_count: int = 2,
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a test MCP connection dictionary.

        Args:
            connection_id: Connection ID (auto-generated if not provided)
            name: Display name
            description: Connection description
            url: MCP server URL
            transport: Transport protocol (streamable_http or stdio)
            auth_type: Authentication method (none, api_key, oauth2)
            status: Connection status
            owner_id: Owner user ID
            organization_id: Organization ID
            project_id: Project ID
            server_name: MCP server name (from server info)
            server_version: MCP server version
            tool_count: Number of tools available
            resource_count: Number of resources available
            prompt_count: Number of prompts available
            created_at: Creation timestamp

        Returns:
            Dictionary with connection data matching MCPConnection model
        """
        now = created_at or datetime.now(UTC)
        return {
            "id": connection_id or f"conn-{uuid4().hex[:8]}",
            "name": name,
            "description": description,
            "url": url,
            "transport": transport,
            "auth_type": auth_type,
            "oauth2_config": None,
            "command": None,
            "args": None,
            "env": None,
            "status": status,
            "last_error": None,
            "last_connected_at": now if status == "connected" else None,
            "server_name": server_name,
            "server_version": server_version,
            "server_capabilities": {"tools": True, "resources": True, "prompts": True},
            "tool_count": tool_count,
            "resource_count": resource_count,
            "prompt_count": prompt_count,
            "owner_id": owner_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def create_with_oauth2(
        name: str = "OAuth2 Connection",
        client_id: str = "test-client-id",
        authorization_url: str = "https://auth.example.com/authorize",
        token_url: str = "https://auth.example.com/token",
        scopes: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a connection with OAuth2 authentication.

        Args:
            name: Display name
            client_id: OAuth2 client ID
            authorization_url: Authorization endpoint URL
            token_url: Token endpoint URL
            scopes: OAuth2 scopes
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with OAuth2-configured connection
        """
        connection = ConnectionFactory.create(
            name=name,
            auth_type="oauth2",
            **kwargs,
        )
        connection["oauth2_config"] = {
            "client_id": client_id,
            "authorization_url": authorization_url,
            "token_url": token_url,
            "scopes": scopes or ["read", "write"],
        }
        return connection

    @staticmethod
    def create_with_api_key(
        name: str = "API Key Connection",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a connection with API key authentication.

        Args:
            name: Display name
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with API key-configured connection
        """
        return ConnectionFactory.create(
            name=name,
            auth_type="api_key",
            **kwargs,
        )

    @staticmethod
    def create_stdio(
        name: str = "Stdio Connection",
        command: str = "/usr/bin/mcp-server",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a stdio transport connection.

        Args:
            name: Display name
            command: Command to execute
            args: Command arguments
            env: Environment variables
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with stdio-configured connection
        """
        connection = ConnectionFactory.create(
            name=name,
            transport="stdio",
            url="stdio://local",
            **kwargs,
        )
        connection["command"] = command
        connection["args"] = args or ["--server"]
        connection["env"] = env or {"MCP_MODE": "server"}
        return connection

    @staticmethod
    def create_disconnected(
        name: str = "Disconnected Connection",
        last_error: str = "Connection refused",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a disconnected connection with error state.

        Args:
            name: Display name
            last_error: Error message
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with disconnected connection
        """
        connection = ConnectionFactory.create(
            name=name,
            status="disconnected",
            server_name=None,
            server_version=None,
            tool_count=0,
            resource_count=0,
            prompt_count=0,
            **kwargs,
        )
        connection["last_error"] = last_error
        connection["last_connected_at"] = None
        connection["server_capabilities"] = None
        return connection

    @staticmethod
    def create_summary(
        connection_id: str | None = None,
        name: str = "Test Connection",
        url: str = "https://mcp.example.com/api",
        transport: TransportProtocol = "streamable_http",
        auth_type: AuthType = "none",
        status: ConnectionStatus = "connected",
        server_name: str | None = "Test MCP Server",
        tool_count: int = 5,
        resource_count: int = 3,
        prompt_count: int = 2,
    ) -> dict[str, Any]:
        """
        Create a connection summary dictionary.

        Returns:
            Dictionary matching MCPConnectionSummary model
        """
        now = datetime.now(UTC)
        return {
            "id": connection_id or f"conn-{uuid4().hex[:8]}",
            "name": name,
            "url": url,
            "transport": transport,
            "auth_type": auth_type,
            "status": status,
            "server_name": server_name,
            "tool_count": tool_count,
            "resource_count": resource_count,
            "prompt_count": prompt_count,
            "last_connected_at": now if status == "connected" else None,
            "created_at": now,
        }


# Convenience instances for common test scenarios
mcp_streamable_connection = ConnectionFactory.create(
    name="Streamable HTTP Connection",
    url="https://api.example.com/mcp",
    transport="streamable_http",
)

mcp_stdio_connection = ConnectionFactory.create_stdio(
    name="Local MCP Server",
    command="/usr/local/bin/mcp-server",
)

mcp_oauth2_connection = ConnectionFactory.create_with_oauth2(
    name="OAuth2 Protected Server",
    client_id="test-client",
)

mcp_disconnected_connection = ConnectionFactory.create_disconnected(
    name="Failing Connection",
    last_error="ECONNREFUSED",
)
