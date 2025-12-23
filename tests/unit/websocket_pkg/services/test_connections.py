"""Unit tests for WebSocket ConnectionsServiceAdapter.

Tests the ConnectionsServiceAdapter that wraps ConnectionRepository
for WebSocket handler use.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_connections")
class TestConnectionsServiceAdapter:
    """Test suite for ConnectionsServiceAdapter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_with_repository_and_owner_id(self) -> None:
        """Test adapter initialization with repository and owner_id."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_repo = MagicMock()
        adapter = ConnectionsServiceAdapter(repository=mock_repo, owner_id="user-123")

        assert adapter._repository is mock_repo
        assert adapter._owner_id == "user-123"

    @pytest.mark.asyncio
    async def test_init_with_empty_owner_id(self) -> None:
        """Test adapter initialization with empty owner_id (default)."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_repo = MagicMock()
        adapter = ConnectionsServiceAdapter(repository=mock_repo)

        assert adapter._owner_id == ""

    @pytest.mark.asyncio
    async def test_list_connections_returns_formatted_list(self) -> None:
        """Test list_connections returns properly formatted connection list."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        # Create mock connection objects
        mock_conn1 = MagicMock()
        mock_conn1.id = "conn-1"
        mock_conn1.name = "Connection 1"
        mock_conn1.status = "active"
        mock_conn1.server_type = "mcp"
        mock_conn1.last_connected = "2025-12-22T12:00:00Z"

        mock_conn2 = MagicMock()
        mock_conn2.id = "conn-2"
        mock_conn2.name = "Connection 2"
        mock_conn2.status = "disconnected"
        mock_conn2.server_type = "langgraph"
        mock_conn2.last_connected = None

        mock_repo = AsyncMock()
        mock_repo.list = AsyncMock(return_value=([mock_conn1, mock_conn2], None))

        adapter = ConnectionsServiceAdapter(repository=mock_repo, owner_id="user-1")
        result = await adapter.list_connections()

        assert len(result) == 2
        assert result[0]["id"] == "conn-1"
        assert result[0]["name"] == "Connection 1"
        assert result[0]["status"] == "active"
        assert result[0]["server_type"] == "mcp"
        assert result[0]["last_connected"] == "2025-12-22T12:00:00Z"

        assert result[1]["id"] == "conn-2"
        assert result[1]["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_list_connections_handles_missing_attributes(self) -> None:
        """Test list_connections handles connections without optional attributes."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        # Create mock connection without server_type and last_connected
        mock_conn = MagicMock(spec=["id", "name", "status"])
        mock_conn.id = "conn-1"
        mock_conn.name = "Basic Connection"
        mock_conn.status = "active"
        # server_type and last_connected will be accessed via getattr with defaults

        mock_repo = AsyncMock()
        mock_repo.list = AsyncMock(return_value=([mock_conn], None))

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.list_connections()

        assert len(result) == 1
        assert result[0]["server_type"] == "unknown"
        assert result[0]["last_connected"] is None

    @pytest.mark.asyncio
    async def test_list_connections_empty_result(self) -> None:
        """Test list_connections with no connections."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_repo = AsyncMock()
        mock_repo.list = AsyncMock(return_value=([], None))

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.list_connections()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_connection_returns_formatted_dict(self) -> None:
        """Test get_connection returns properly formatted connection data."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_conn = MagicMock()
        mock_conn.id = "conn-123"
        mock_conn.name = "Test Connection"
        mock_conn.status = "connected"
        mock_conn.server_type = "mcp"
        mock_conn.url = "http://localhost:8080"
        mock_conn.last_connected = "2025-12-22T10:00:00Z"

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_conn)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection("conn-123")

        assert result is not None
        assert result["id"] == "conn-123"
        assert result["name"] == "Test Connection"
        assert result["status"] == "connected"
        assert result["server_type"] == "mcp"
        assert result["url"] == "http://localhost:8080"
        assert result["last_connected"] == "2025-12-22T10:00:00Z"

    @pytest.mark.asyncio
    async def test_get_connection_returns_none_when_not_found(self) -> None:
        """Test get_connection returns None for non-existent connection."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=None)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_connection_health_healthy_connection(self) -> None:
        """Test get_connection_health for healthy (active) connection."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_conn = MagicMock()
        mock_conn.status = "active"

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_conn)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection_health("conn-1")

        assert result["connection_id"] == "conn-1"
        assert result["healthy"] is True
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_connection_health_connected_status(self) -> None:
        """Test get_connection_health for 'connected' status."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_conn = MagicMock()
        mock_conn.status = "connected"

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_conn)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection_health("conn-2")

        assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_connection_health_unhealthy_connection(self) -> None:
        """Test get_connection_health for unhealthy (disconnected) connection."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_conn = MagicMock()
        mock_conn.status = "disconnected"

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_conn)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection_health("conn-3")

        assert result["connection_id"] == "conn-3"
        assert result["healthy"] is False
        assert result["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_get_connection_health_not_found(self) -> None:
        """Test get_connection_health for non-existent connection."""
        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
        )

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=None)

        adapter = ConnectionsServiceAdapter(repository=mock_repo)
        result = await adapter.get_connection_health("missing-conn")

        assert result["connection_id"] == "missing-conn"
        assert result["healthy"] is False
        assert result["error"] == "Connection not found"


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_connections")
class TestConnectionsServiceSingleton:
    """Test suite for connections service singleton functions."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.connections import (
            reset_websocket_connections_service,
        )
        reset_websocket_connections_service()
        gc.collect()

    def test_reset_websocket_connections_service(self) -> None:
        """Test reset_websocket_connections_service clears singleton."""
        from mcp_server_langgraph.websocket.services.connections import (
            reset_websocket_connections_service,
        )
        import mcp_server_langgraph.websocket.services.connections as connections_module

        # Set the singleton to a mock value
        connections_module._connections_service = MagicMock()

        # Reset should clear it
        reset_websocket_connections_service()

        assert connections_module._connections_service is None

    def test_get_websocket_connections_service_creates_instance(self) -> None:
        """Test get_websocket_connections_service creates new adapter when None."""
        from unittest.mock import patch

        from mcp_server_langgraph.websocket.services.connections import (
            ConnectionsServiceAdapter,
            get_websocket_connections_service,
            reset_websocket_connections_service,
        )

        # Ensure starting from clean state
        reset_websocket_connections_service()

        mock_repo = MagicMock()

        # Patch in core.dependencies where get_connection_repository is defined
        with patch(
            "mcp_server_langgraph.core.dependencies.get_connection_repository",
            return_value=mock_repo,
        ):
            service = get_websocket_connections_service(owner_id="test-owner")

            assert service is not None
            assert isinstance(service, ConnectionsServiceAdapter)
            assert service._owner_id == "test-owner"
            assert service._repository is mock_repo

    def test_get_websocket_connections_service_returns_cached_instance(self) -> None:
        """Test get_websocket_connections_service returns cached instance."""
        from unittest.mock import patch

        from mcp_server_langgraph.websocket.services.connections import (
            get_websocket_connections_service,
            reset_websocket_connections_service,
        )

        # Ensure starting from clean state
        reset_websocket_connections_service()

        mock_repo = MagicMock()

        # Patch in core.dependencies where get_connection_repository is defined
        with patch(
            "mcp_server_langgraph.core.dependencies.get_connection_repository",
            return_value=mock_repo,
        ):
            # First call creates instance
            service1 = get_websocket_connections_service()
            # Second call returns same instance
            service2 = get_websocket_connections_service(owner_id="different-owner")

            # Both should be the same instance (singleton)
            assert service1 is service2
