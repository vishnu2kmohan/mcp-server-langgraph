"""
WebSocket Broadcaster Registry.

Centralized management of broadcaster instances for WebSocket endpoints.
Provides getter and setter functions for all broadcasters to enable:
- Singleton instance management
- Dependency injection in tests
- Bootstrap initialization

This module consolidates broadcaster lifecycle management previously
scattered across individual endpoint files.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
    from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster
    from mcp_server_langgraph.hitl.broadcast import AgentRequestBroadcaster
    from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster
    from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
    from mcp_server_langgraph.observability.trace_broadcaster import TraceBroadcaster
    from mcp_server_langgraph.websocket.handlers.devtools import DevToolsBroadcaster
    from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
        MCPAggregatedBroadcaster,
    )
    from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
        OrchestratorStatusBroadcaster,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Notification Broadcaster
# =============================================================================

_notification_broadcaster: NotificationBroadcaster | None = None


def get_notification_broadcaster() -> NotificationBroadcaster:
    """Get the notification broadcaster instance."""
    global _notification_broadcaster
    if _notification_broadcaster is None:
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        _notification_broadcaster = NotificationBroadcaster()
    return _notification_broadcaster


def set_notification_broadcaster(broadcaster: NotificationBroadcaster | None) -> None:
    """Set the notification broadcaster instance (for app initialization or testing)."""
    global _notification_broadcaster
    _notification_broadcaster = broadcaster


# =============================================================================
# Alert Broadcaster
# =============================================================================

_alert_broadcaster: AlertBroadcaster | None = None


def get_alert_broadcaster() -> AlertBroadcaster:
    """Get the alert broadcaster instance."""
    global _alert_broadcaster
    if _alert_broadcaster is None:
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        _alert_broadcaster = AlertBroadcaster()
    return _alert_broadcaster


def set_alert_broadcaster(broadcaster: AlertBroadcaster | None) -> None:
    """Set the alert broadcaster instance (for app initialization or testing)."""
    global _alert_broadcaster
    _alert_broadcaster = broadcaster


# =============================================================================
# Audit Event Broadcaster
# =============================================================================

_audit_broadcaster: AuditEventBroadcaster | None = None


def get_audit_event_broadcaster() -> AuditEventBroadcaster:
    """Get the audit event broadcaster instance."""
    global _audit_broadcaster
    if _audit_broadcaster is None:
        from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster

        _audit_broadcaster = AuditEventBroadcaster()
    return _audit_broadcaster


def set_audit_event_broadcaster(broadcaster: AuditEventBroadcaster | None) -> None:
    """Set the audit event broadcaster instance (for app initialization or testing)."""
    global _audit_broadcaster
    _audit_broadcaster = broadcaster


# =============================================================================
# Agent Request (HITL) Broadcaster
# =============================================================================

_agent_request_broadcaster: AgentRequestBroadcaster | None = None


def get_agent_request_broadcaster() -> AgentRequestBroadcaster:
    """Get the agent request broadcaster instance."""
    global _agent_request_broadcaster
    if _agent_request_broadcaster is None:
        from mcp_server_langgraph.hitl.broadcast import AgentRequestBroadcaster

        _agent_request_broadcaster = AgentRequestBroadcaster()
    return _agent_request_broadcaster


def set_agent_request_broadcaster(broadcaster: AgentRequestBroadcaster | None) -> None:
    """Set the agent request broadcaster instance (for app initialization or testing)."""
    global _agent_request_broadcaster
    _agent_request_broadcaster = broadcaster


# Backward compatibility alias
get_broadcaster = get_agent_request_broadcaster


# =============================================================================
# Trace Broadcaster
# =============================================================================

_trace_broadcaster: TraceBroadcaster | None = None


def get_trace_broadcaster() -> TraceBroadcaster:
    """Get the trace broadcaster instance."""
    global _trace_broadcaster
    if _trace_broadcaster is None:
        from mcp_server_langgraph.observability.trace_broadcaster import TraceBroadcaster

        _trace_broadcaster = TraceBroadcaster()
    return _trace_broadcaster


def set_trace_broadcaster(broadcaster: TraceBroadcaster | None) -> None:
    """Set the trace broadcaster instance (for app initialization or testing)."""
    global _trace_broadcaster
    _trace_broadcaster = broadcaster


# =============================================================================
# MCP Aggregated Broadcaster
# =============================================================================

_mcp_aggregated_broadcaster: MCPAggregatedBroadcaster | None = None


def get_mcp_aggregated_broadcaster() -> MCPAggregatedBroadcaster:
    """Get the MCP aggregated capability broadcaster instance."""
    global _mcp_aggregated_broadcaster
    if _mcp_aggregated_broadcaster is None:
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        _mcp_aggregated_broadcaster = MCPAggregatedBroadcaster()
    return _mcp_aggregated_broadcaster


def set_mcp_aggregated_broadcaster(broadcaster: MCPAggregatedBroadcaster | None) -> None:
    """Set the MCP aggregated broadcaster instance (for app initialization or testing)."""
    global _mcp_aggregated_broadcaster
    _mcp_aggregated_broadcaster = broadcaster


# =============================================================================
# Budget Alert Broadcaster
# =============================================================================

_budget_alert_broadcaster: BudgetAlertBroadcaster | None = None


def get_budget_alert_broadcaster() -> BudgetAlertBroadcaster:
    """Get the budget alert broadcaster instance."""
    global _budget_alert_broadcaster
    if _budget_alert_broadcaster is None:
        from mcp_server_langgraph.monitoring.cost_budget import (
            get_budget_alert_broadcaster as _get,
        )

        _budget_alert_broadcaster = _get()
    return _budget_alert_broadcaster


def set_budget_alert_broadcaster(broadcaster: BudgetAlertBroadcaster | None) -> None:
    """Set the budget alert broadcaster instance (for app initialization or testing)."""
    global _budget_alert_broadcaster
    _budget_alert_broadcaster = broadcaster


# =============================================================================
# DevTools Broadcaster
# =============================================================================

_devtools_broadcaster: DevToolsBroadcaster | None = None


def get_devtools_broadcaster() -> DevToolsBroadcaster:
    """Get the DevTools broadcaster instance."""
    global _devtools_broadcaster
    if _devtools_broadcaster is None:
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsBroadcaster

        _devtools_broadcaster = DevToolsBroadcaster()
    return _devtools_broadcaster


def set_devtools_broadcaster(broadcaster: DevToolsBroadcaster | None) -> None:
    """Set the DevTools broadcaster instance (for app initialization or testing)."""
    global _devtools_broadcaster
    _devtools_broadcaster = broadcaster


# =============================================================================
# Orchestrator Status Broadcaster
# =============================================================================

_orchestrator_status_broadcaster: OrchestratorStatusBroadcaster | None = None


def get_orchestrator_status_broadcaster() -> OrchestratorStatusBroadcaster:
    """Get the orchestrator status broadcaster instance."""
    global _orchestrator_status_broadcaster
    if _orchestrator_status_broadcaster is None:
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
        )

        _orchestrator_status_broadcaster = OrchestratorStatusBroadcaster()
    return _orchestrator_status_broadcaster


def set_orchestrator_status_broadcaster(broadcaster: OrchestratorStatusBroadcaster | None) -> None:
    """Set the orchestrator status broadcaster instance (for app initialization or testing)."""
    global _orchestrator_status_broadcaster
    _orchestrator_status_broadcaster = broadcaster


__all__ = [
    # Notification
    "get_notification_broadcaster",
    "set_notification_broadcaster",
    # Alert
    "get_alert_broadcaster",
    "set_alert_broadcaster",
    # Audit
    "get_audit_event_broadcaster",
    "set_audit_event_broadcaster",
    # Agent Request (HITL)
    "get_agent_request_broadcaster",
    "set_agent_request_broadcaster",
    "get_broadcaster",  # Backward compatibility
    # Trace
    "get_trace_broadcaster",
    "set_trace_broadcaster",
    # MCP Aggregated
    "get_mcp_aggregated_broadcaster",
    "set_mcp_aggregated_broadcaster",
    # Budget Alert
    "get_budget_alert_broadcaster",
    "set_budget_alert_broadcaster",
    # DevTools
    "get_devtools_broadcaster",
    "set_devtools_broadcaster",
    # Orchestrator Status
    "get_orchestrator_status_broadcaster",
    "set_orchestrator_status_broadcaster",
]
