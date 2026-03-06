"""
Tests for Multi-Tenant Alert Isolation in Broadcaster.

Verifies that:
- Alerts are only sent to subscribers in the correct tenant
- Router integration filters alerts properly
- Tenant isolation is maintained during broadcast

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def create_test_alert(tenant: str = "default"):
    """Create a test alert for a specific tenant."""
    from mcp_server_langgraph.observability.query.interfaces import (
        Alert,
        AlertSeverity,
        AlertState,
    )

    return Alert(
        alert_id=f"test-alert-{tenant}",
        name="HighCPUUsage",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message=f"CPU usage above 90% for {tenant}",
        labels={"service": "api-gateway", "tenant": tenant},
        annotations={"summary": f"High CPU on api-gateway for {tenant}"},
        started_at=datetime.now(UTC),
    )


class TestBroadcasterTenantIsolation:
    """Tests for tenant isolation in alert broadcasting."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_router_filters_subscribers_by_tenant(self) -> None:
        """
        GIVEN a broadcaster with router and subscribers from different tenants
        WHEN broadcasting an alert
        THEN only subscribers in the routed tenant should receive it.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            RoutingResult,
        )

        # Create mock router that returns specific users
        mock_router = MagicMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-a",
                routed=True,
                subscribed_users=["user-a1", "user-a2"],  # Only tenant-a users
            )
        )

        # Patch metrics to avoid import issues
        with patch("mcp_server_langgraph.alerts.broadcaster.record_websocket_message"):
            with patch("mcp_server_langgraph.alerts.broadcaster.update_websocket_connections"):
                broadcaster = AlertBroadcaster(router=mock_router)

                # Add subscribers from different tenants
                mock_ws_a1 = AsyncMock(return_value=None)
                mock_ws_a2 = AsyncMock(return_value=None)
                mock_ws_b1 = AsyncMock(return_value=None)  # Different tenant

                await broadcaster.subscribe(mock_ws_a1, "user-a1")
                await broadcaster.subscribe(mock_ws_a2, "user-a2")
                await broadcaster.subscribe(mock_ws_b1, "user-b1")  # Not in subscribed_users

                # Broadcast alert for tenant-a
                alert = create_test_alert(tenant="tenant-a")
                await broadcaster.broadcast_alert(alert)

                # Only tenant-a subscribers should receive the alert
                mock_ws_a1.send_json.assert_called_once()
                mock_ws_a2.send_json.assert_called_once()
                mock_ws_b1.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_router_filtered_alert_not_broadcast(self) -> None:
        """
        GIVEN a router that filters out the alert
        WHEN broadcasting
        THEN no subscribers should receive it.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        # Router returns filtered=True
        mock_router = MagicMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-a",
                routed=False,  # Filtered out
            )
        )

        with patch("mcp_server_langgraph.alerts.broadcaster.record_websocket_message"):
            with patch("mcp_server_langgraph.alerts.broadcaster.update_websocket_connections"):
                broadcaster = AlertBroadcaster(router=mock_router)

                mock_ws = AsyncMock(return_value=None)
                await broadcaster.subscribe(mock_ws, "user-a1")

                alert = create_test_alert(tenant="tenant-a")
                await broadcaster.broadcast_alert(alert)

                # No one should receive the filtered alert
                mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_without_router_sends_to_all(self) -> None:
        """
        GIVEN a broadcaster without a router
        WHEN broadcasting an alert
        THEN all subscribers should receive it.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        with patch("mcp_server_langgraph.alerts.broadcaster.record_websocket_message"):
            with patch("mcp_server_langgraph.alerts.broadcaster.update_websocket_connections"):
                broadcaster = AlertBroadcaster()  # No router

                mock_ws_a = AsyncMock(return_value=None)
                mock_ws_b = AsyncMock(return_value=None)

                await broadcaster.subscribe(mock_ws_a, "user-a")
                await broadcaster.subscribe(mock_ws_b, "user-b")

                alert = create_test_alert(tenant="any")
                await broadcaster.broadcast_alert(alert)

                # All subscribers receive without filtering
                mock_ws_a.send_json.assert_called_once()
                mock_ws_b.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_includes_tenant_id_when_routed(self) -> None:
        """
        GIVEN a broadcaster with router
        WHEN broadcasting an alert
        THEN the message should include the tenant_id.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        mock_router = MagicMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="acme-corp",
                routed=True,
                subscribed_users=["admin-user"],
            )
        )

        with patch("mcp_server_langgraph.alerts.broadcaster.record_websocket_message"):
            with patch("mcp_server_langgraph.alerts.broadcaster.update_websocket_connections"):
                broadcaster = AlertBroadcaster(router=mock_router)

                mock_ws = AsyncMock(return_value=None)
                await broadcaster.subscribe(mock_ws, "admin-user")

                alert = create_test_alert(tenant="acme-corp")
                await broadcaster.broadcast_alert(alert)

                # Check the message includes tenant_id
                call_args = mock_ws.send_json.call_args
                message = call_args[0][0]
                assert message["payload"]["tenant_id"] == "acme-corp"

    @pytest.mark.asyncio
    async def test_router_error_falls_back_to_all_subscribers(self) -> None:
        """
        GIVEN a router that raises an exception
        WHEN broadcasting an alert
        THEN should fall back to sending to all subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
        from mcp_server_langgraph.alerts.routing import AlertRouter

        # Router raises an exception
        mock_router = MagicMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(side_effect=RuntimeError("Router failure"))

        with patch("mcp_server_langgraph.alerts.broadcaster.record_websocket_message"):
            with patch("mcp_server_langgraph.alerts.broadcaster.update_websocket_connections"):
                broadcaster = AlertBroadcaster(router=mock_router)

                mock_ws_a = AsyncMock(return_value=None)
                mock_ws_b = AsyncMock(return_value=None)

                await broadcaster.subscribe(mock_ws_a, "user-a")
                await broadcaster.subscribe(mock_ws_b, "user-b")

                alert = create_test_alert(tenant="any")
                await broadcaster.broadcast_alert(alert)

                # All subscribers should receive (fallback behavior)
                mock_ws_a.send_json.assert_called_once()
                mock_ws_b.send_json.assert_called_once()
