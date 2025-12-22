"""
WebSocket Connections Service Adapter.

Wraps ConnectionRepository to provide the interface expected by
ConnectionsRealtimeHandler and ConnectionHealthHandler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.connections import ConnectionRepository


class ConnectionsServiceAdapter:
    """
    Adapts ConnectionRepository for WebSocket handler use.

    Implements the ConnectionServiceProtocol expected by ConnectionsRealtimeHandler.
    """

    def __init__(self, repository: ConnectionRepository, owner_id: str = "") -> None:
        """
        Initialize the adapter.

        Args:
            repository: The connection repository to wrap.
            owner_id: The owner ID for filtering connections.
        """
        self._repository = repository
        self._owner_id = owner_id

    async def list_connections(self) -> list[dict[str, Any]]:
        """
        List all connections for the owner.

        Returns:
            List of connection data as dictionaries.
        """
        connections, _cursor = await self._repository.list(
            owner_id=self._owner_id,
            limit=1000,
        )
        return [
            {
                "id": conn.id,
                "name": conn.name,
                "status": conn.status,
                "server_type": getattr(conn, "server_type", "unknown"),
                "last_connected": getattr(conn, "last_connected", None),
            }
            for conn in connections
        ]

    async def get_connection(self, connection_id: str) -> dict[str, Any] | None:
        """
        Get a specific connection by ID.

        Args:
            connection_id: The connection ID.

        Returns:
            Connection data as dictionary or None if not found.
        """
        connection = await self._repository.get(connection_id)
        if connection is None:
            return None
        return {
            "id": connection.id,
            "name": connection.name,
            "status": connection.status,
            "server_type": getattr(connection, "server_type", "unknown"),
            "url": getattr(connection, "url", None),
            "last_connected": getattr(connection, "last_connected", None),
        }

    async def get_connection_health(self, connection_id: str) -> dict[str, Any]:
        """
        Get health status for a connection.

        Args:
            connection_id: The connection ID.

        Returns:
            Health status data.
        """
        connection = await self._repository.get(connection_id)
        if connection is None:
            return {
                "connection_id": connection_id,
                "healthy": False,
                "error": "Connection not found",
            }

        # Basic health check based on connection status
        is_healthy = connection.status in ("active", "connected")
        return {
            "connection_id": connection_id,
            "healthy": is_healthy,
            "status": connection.status,
            "last_checked": None,  # Could be enhanced with actual health check
        }


# Singleton instance
_connections_service: ConnectionsServiceAdapter | None = None


def get_websocket_connections_service(
    owner_id: str = "",
) -> ConnectionsServiceAdapter:
    """
    Get or create the connections service adapter.

    Args:
        owner_id: The owner ID for filtering connections.

    Returns:
        ConnectionsServiceAdapter instance.
    """
    global _connections_service
    if _connections_service is None:
        from mcp_server_langgraph.core.dependencies import get_connection_repository

        _connections_service = ConnectionsServiceAdapter(
            repository=get_connection_repository(),
            owner_id=owner_id,
        )
    return _connections_service


def reset_websocket_connections_service() -> None:
    """Reset the connections service (for testing)."""
    global _connections_service
    _connections_service = None
