"""
Cost Tracking Service Adapter for WebSocket.

Adapts the existing CostServiceImpl to the CostServiceProtocol expected
by the WebSocket handler. Provides session-level cost tracking when available,
with stub fallbacks for features under development.

Architecture:
    - Wraps CostServiceImpl for aggregate cost data
    - Uses Redis for session-level cost caching (when available)
    - Falls back to stub data for unimplemented features
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.core.feature_flags import get_feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.cost import CostService

logger = logging.getLogger(__name__)


class CostTrackingServiceAdapter:
    """
    Adapter that bridges CostServiceImpl with WebSocket cost tracking needs.

    The WebSocket handler needs:
    - get_session_cost(session_id) -> Per-session cost
    - get_user_budget(user_id) -> User budget status

    Currently provides:
    - Stub session costs (TODO: integrate with cost storage per-session)
    - Stub user budgets (TODO: implement budget management system)

    When real implementations are available, this adapter will be updated
    to use them while maintaining backward compatibility.
    """

    def __init__(self, cost_service: CostService | None = None) -> None:
        """
        Initialize with optional cost service.

        Args:
            cost_service: CostService instance for aggregate data.
                If None, lazily imports the global instance.
        """
        self._cost_service = cost_service
        self._session_costs: dict[str, dict[str, Any]] = {}
        self._user_budgets: dict[str, dict[str, Any]] = {}

    @property
    def cost_service(self) -> CostService:
        """Get the cost service, lazily initializing if needed."""
        if self._cost_service is None:
            from mcp_server_langgraph.api.v1.cost import get_cost_service

            self._cost_service = get_cost_service()
        return self._cost_service

    async def get_session_cost(self, session_id: str) -> dict[str, Any]:
        """
        Get current cost for a session.

        Currently returns cached/stub data. When Redis cost tracking is
        implemented, this will query real session costs.

        Args:
            session_id: Session identifier.

        Returns:
            Dict with session_id, total_cost, token_count.
        """
        # Check cache first
        if session_id in self._session_costs:
            return self._session_costs[session_id]

        # TODO: When Redis session cost tracking is implemented:
        # - Query Redis for session:{session_id}:cost
        # - Aggregate cost events for the session

        # Stub response for now
        flags = get_feature_flags()
        if not flags.enable_websocket_enhanced_metrics:
            # Return minimal stub when metrics are disabled
            return {
                "session_id": session_id,
                "total_cost": 0.0,
                "token_count": 0,
            }

        # Return default stub
        logger.debug(
            f"Session cost not found for {session_id}, returning stub",
            extra={"session_id": session_id},
        )
        return {
            "session_id": session_id,
            "total_cost": 0.0,
            "token_count": 0,
        }

    async def get_user_budget(self, user_id: str) -> dict[str, Any]:
        """
        Get budget status for a user.

        Currently returns stub data. When user budget management is
        implemented, this will query the budget system.

        Args:
            user_id: User identifier.

        Returns:
            Dict with user_id, budget_limit, current_usage, remaining.
        """
        # Check cache first
        if user_id in self._user_budgets:
            return self._user_budgets[user_id]

        # TODO: When budget management is implemented:
        # - Query user budget configuration from database
        # - Calculate current usage from cost storage
        # - Return real budget status

        # Stub response for now
        logger.debug(
            f"User budget not found for {user_id}, returning stub",
            extra={"user_id": user_id},
        )
        return {
            "user_id": user_id,
            "budget_limit": 100.0,  # Default $100 budget
            "current_usage": 0.0,
            "remaining": 100.0,
        }

    def update_session_cost(self, session_id: str, cost: float, tokens: int) -> dict[str, Any]:
        """
        Update cached session cost.

        Called when cost events are received to update the local cache.

        Args:
            session_id: Session identifier.
            cost: Cost to add.
            tokens: Tokens to add.

        Returns:
            Updated session cost data.
        """
        if session_id not in self._session_costs:
            self._session_costs[session_id] = {
                "session_id": session_id,
                "total_cost": 0.0,
                "token_count": 0,
            }

        self._session_costs[session_id]["total_cost"] += cost
        self._session_costs[session_id]["token_count"] += tokens

        return self._session_costs[session_id]


# Service singleton
_websocket_cost_service: CostTrackingServiceAdapter | None = None


def get_websocket_cost_service() -> CostTrackingServiceAdapter:
    """Get the WebSocket cost service adapter instance."""
    global _websocket_cost_service
    if _websocket_cost_service is None:
        _websocket_cost_service = CostTrackingServiceAdapter()
    return _websocket_cost_service


def reset_websocket_cost_service() -> None:
    """Reset the WebSocket cost service singleton (for testing)."""
    global _websocket_cost_service
    _websocket_cost_service = None
