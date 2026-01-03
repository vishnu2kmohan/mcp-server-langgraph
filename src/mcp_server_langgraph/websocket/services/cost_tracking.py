"""
Cost Tracking Service Adapter for WebSocket.

Adapts the existing CostServiceImpl to the CostServiceProtocol expected
by the WebSocket handler. Provides session-level cost tracking when available,
with database fallback for historical cost data.

Architecture:
    - Wraps CostServiceImpl for aggregate cost data
    - Uses Redis for session-level cost caching (L1+L2 tiered cache)
    - Falls back to in-memory cache when Redis is unavailable
    - Queries TokenUsageRecord from database on cache miss
    - Key pattern: session_cost:{session_id}
    - TTL: 1 hour for active sessions
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from decimal import Decimal
from typing import TYPE_CHECKING, Any, AsyncIterator

from sqlalchemy import func, select

from mcp_server_langgraph.core.feature_flags import get_feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.cost import CostService
    from mcp_server_langgraph.core.cache import CacheService
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Cache key prefix for session costs
SESSION_COST_CACHE_KEY_PREFIX = "session_cost"

# Cache TTL: 1 hour for active sessions
SESSION_COST_CACHE_TTL = 3600  # seconds


@asynccontextmanager
async def get_async_session_context() -> AsyncIterator[AsyncSession]:
    """
    Get async database session context manager.

    Yields an async session for database operations.
    Commits on success, rolls back on exception.
    """
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.database import get_async_session

    async with get_async_session(settings.database_url) as session:
        yield session


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

    def __init__(
        self,
        cost_service: CostService | None = None,
        cache: CacheService | None = None,
    ) -> None:
        """
        Initialize with optional cost service and cache.

        Args:
            cost_service: CostService instance for aggregate data.
                If None, lazily imports the global instance.
            cache: CacheService instance for Redis L1+L2 caching.
                If None, lazily imports the global instance.
        """
        self._cost_service = cost_service
        self._cache: CacheService | None = cache
        self._session_costs: dict[str, dict[str, Any]] = {}
        self._user_budgets: dict[str, dict[str, Any]] = {}

    @property
    def cost_service(self) -> CostService:
        """Get the cost service, lazily initializing if needed."""
        if self._cost_service is None:
            from mcp_server_langgraph.api.v1.cost import get_cost_service

            self._cost_service = get_cost_service()
        return self._cost_service

    @property
    def cache(self) -> CacheService:
        """Get the cache service, lazily initializing if needed."""
        if self._cache is None:
            from mcp_server_langgraph.core.cache import get_cache

            self._cache = get_cache()
        return self._cache

    def _get_cache_key(self, session_id: str) -> str:
        """Generate cache key for session cost."""
        return f"{SESSION_COST_CACHE_KEY_PREFIX}:{session_id}"

    async def get_session_cost(self, session_id: str) -> dict[str, Any]:
        """
        Get current cost for a session.

        Uses a tiered caching strategy:
        1. Check Redis cache (L1 in-memory + L2 Redis)
        2. If cache miss, query cost service for session summary
        3. Cache the result with 1 hour TTL
        4. Fall back to in-memory cache if Redis fails

        Args:
            session_id: Session identifier.

        Returns:
            Dict with session_id, total_cost, token_count, updated_at.
        """
        cache_key = self._get_cache_key(session_id)

        # 1. Try Redis cache first (L1 + L2)
        try:
            cached_data = await self.cache.aget(cache_key)
            if cached_data:
                logger.debug(
                    f"Session cost cache hit for {session_id}",
                    extra={"session_id": session_id},
                )
                # Type assertion: cached_data is dict[str, Any] from our cache
                return dict(cached_data)
        except Exception as e:
            logger.warning(
                f"Redis cache get failed for {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )
            # Fall through to in-memory cache

        # 2. Check in-memory cache (fallback)
        if session_id in self._session_costs:
            return self._session_costs[session_id]

        # 3. Check feature flag
        flags = get_feature_flags()
        if not flags.enable_websocket_enhanced_metrics:
            # Return minimal stub when metrics are disabled
            return {
                "session_id": session_id,
                "total_cost": 0.0,
                "token_count": 0,
            }

        # 4. Query database for historical cost data
        try:
            session_cost = await self._query_session_cost_from_database(session_id)
            if session_cost:
                # Cache the result in Redis for future requests
                try:
                    await self.cache.aset(
                        cache_key, session_cost, ttl=SESSION_COST_CACHE_TTL
                    )
                    logger.debug(
                        f"Cached session cost from database for {session_id}",
                        extra={"session_id": session_id},
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to cache session cost for {session_id}: {e}",
                        extra={"session_id": session_id, "error": str(e)},
                    )
                return session_cost
        except Exception as e:
            logger.warning(
                f"Database query failed for session {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )

        # 5. Return zeros when no data found
        logger.debug(
            f"No cost data for session {session_id}, returning initial values",
            extra={"session_id": session_id},
        )
        return {
            "session_id": session_id,
            "total_cost": 0.0,
            "token_count": 0,
        }

    async def _query_session_cost_from_database(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """
        Query TokenUsageRecord to aggregate costs by session_id.

        Args:
            session_id: Session identifier to query.

        Returns:
            Session cost data dict or None if no records found.
        """
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session_context() as session:
            # Aggregate costs by session_id
            stmt = select(
                func.sum(TokenUsageRecord.estimated_cost_usd).label("total_cost"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            ).where(TokenUsageRecord.session_id == session_id)

            result = await session.execute(stmt)
            row = result.one_or_none()

            if row is None or row[0] is None:
                return None

            total_cost_decimal: Decimal = row[0]
            total_tokens: int = row[1] or 0

            return {
                "session_id": session_id,
                "total_cost": float(total_cost_decimal),
                "token_count": total_tokens,
                "updated_at": datetime.now(UTC).isoformat(),
            }

    async def get_user_budget(self, user_id: str) -> dict[str, Any]:
        """
        Get budget status for a user.

        Queries the budget storage for the user's configured budget limit
        and calculates current usage from the cost storage.

        Args:
            user_id: User identifier.

        Returns:
            Dict with user_id, budget_limit, current_usage, remaining.
        """
        # Check in-memory cache first
        if user_id in self._user_budgets:
            return self._user_budgets[user_id]

        # Default budget limit
        budget_limit = 100.0  # Default $100 budget
        current_usage = 0.0

        # Query real budget from database
        try:
            from mcp_server_langgraph.monitoring.budget_storage import get_budget_storage

            storage = get_budget_storage()
            budget = await storage.get_budget("user", user_id)

            if budget:
                budget_limit = float(budget.monthly_limit_usd)
                logger.debug(
                    f"Found budget for user {user_id}: ${budget_limit}",
                    extra={"user_id": user_id, "budget_limit": budget_limit},
                )
            else:
                logger.debug(
                    f"No budget found for user {user_id}, using default ${budget_limit}",
                    extra={"user_id": user_id},
                )
        except Exception as e:
            logger.warning(
                f"Failed to query budget for user {user_id}: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )

        # Query current usage from cost storage
        try:
            from mcp_server_langgraph.monitoring.litellm_cost_callback import (
                get_current_spend_for_entity,
            )

            current_spend = await get_current_spend_for_entity("user", user_id)
            current_usage = float(current_spend)
            logger.debug(
                f"Current spend for user {user_id}: ${current_usage}",
                extra={"user_id": user_id, "current_usage": current_usage},
            )
        except Exception as e:
            logger.warning(
                f"Failed to query current spend for user {user_id}: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )

        # Calculate remaining
        remaining = max(0.0, budget_limit - current_usage)

        # Build response and cache it
        result = {
            "user_id": user_id,
            "budget_limit": budget_limit,
            "current_usage": current_usage,
            "remaining": remaining,
        }
        self._user_budgets[user_id] = result

        return result

    def update_session_cost(self, session_id: str, cost: float, tokens: int) -> dict[str, Any]:
        """
        Update cached session cost (sync version, in-memory only).

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

    async def update_session_cost_async(self, session_id: str, cost: float, tokens: int) -> dict[str, Any]:
        """
        Update session cost in Redis cache (async version).

        Called when LLM calls complete to update the cached session cost.
        This updates both the Redis cache and the in-memory fallback.

        Args:
            session_id: Session identifier.
            cost: Cost to add (in USD).
            tokens: Token count to add.

        Returns:
            Updated session cost data.
        """
        cache_key = self._get_cache_key(session_id)

        # 1. Get existing cached data or create new entry
        try:
            existing_data = await self.cache.aget(cache_key)
        except Exception as e:
            logger.warning(
                f"Redis cache get failed during update for {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )
            existing_data = None

        # Fall back to in-memory if Redis failed
        if existing_data is None and session_id in self._session_costs:
            existing_data = self._session_costs[session_id]

        # 2. Calculate new totals
        if existing_data:
            new_total_cost = existing_data.get("total_cost", 0.0) + cost
            new_token_count = existing_data.get("token_count", 0) + tokens
        else:
            new_total_cost = cost
            new_token_count = tokens

        # 3. Build updated session cost data
        session_cost = {
            "session_id": session_id,
            "total_cost": new_total_cost,
            "token_count": new_token_count,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # 4. Update Redis cache
        try:
            await self.cache.aset(cache_key, session_cost, ttl=SESSION_COST_CACHE_TTL)
            logger.debug(
                f"Updated session cost cache for {session_id}",
                extra={
                    "session_id": session_id,
                    "added_cost": cost,
                    "added_tokens": tokens,
                    "total_cost": new_total_cost,
                    "total_tokens": new_token_count,
                },
            )
        except Exception as e:
            logger.warning(
                f"Redis cache set failed during update for {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )

        # 5. Also update in-memory cache
        self._session_costs[session_id] = session_cost

        return session_cost

    async def invalidate_session_cost(self, session_id: str) -> None:
        """
        Invalidate session cost cache.

        Called when session is deleted or cost data needs to be refreshed.

        Args:
            session_id: Session identifier.
        """
        cache_key = self._get_cache_key(session_id)

        # Delete from Redis
        try:
            await self.cache.adelete(cache_key)
            logger.debug(
                f"Invalidated session cost cache for {session_id}",
                extra={"session_id": session_id},
            )
        except Exception as e:
            logger.warning(
                f"Redis cache delete failed for {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )

        # Also delete from in-memory cache
        self._session_costs.pop(session_id, None)


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
