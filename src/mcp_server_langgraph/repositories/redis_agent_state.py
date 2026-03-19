"""
Redis Implementation of Agent State Repository.

Uses redis.asyncio for async operations with TTL-based expiry.
Includes circuit breaker integration with InMemory fallback.

Key pattern: agent_state:{session_id}
Session index: agent_state:_index (Redis SET for O(N) list_sessions)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import pybreaker
import redis.asyncio as aioredis

from mcp_server_langgraph.repositories.agent_state import (
    AgentStateRepository,
    InMemoryAgentStateRepository,
)

logger = logging.getLogger(__name__)

KEY_PREFIX = "agent_state:"
INDEX_KEY = "agent_state:_index"
_NOT_FOUND = object()  # Sentinel to distinguish "key missing" from "operation failed"


class RedisAgentStateRepository(AgentStateRepository):
    """Redis implementation of agent state repository.

    Features:
    - TTL-based automatic expiry (default 24h)
    - Session index via Redis SET for O(N) list_sessions
    - Circuit breaker with InMemory fallback on open
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        *,
        session_ttl_seconds: int = 86400,
        circuit_breaker: pybreaker.CircuitBreaker | None = None,
    ) -> None:
        self._redis = redis_client
        self._ttl = session_ttl_seconds
        self._breaker = circuit_breaker
        self._fallback = InMemoryAgentStateRepository()

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    async def _execute(self, operation):
        """Execute a Redis operation with optional circuit breaker."""
        if self._breaker is None:
            return await operation()

        # Check breaker state before calling — avoids pybreaker call_async issues
        if self._breaker.current_state == "open":
            logger.warning(
                "Redis circuit breaker open, falling back to in-memory. "
                "State saved during fallback will not survive pod restarts."
            )
            return None

        try:
            return await operation()
        except Exception as exc:
            # Record the failure via pybreaker's public interface
            try:
                self._breaker.call(self._raise, exc)
            except (pybreaker.CircuitBreakerError, type(exc)):
                pass
            logger.warning("Redis operation failed: %s", exc)
            return None

    @staticmethod
    def _raise(exc: Exception) -> None:
        """Re-raise an exception for pybreaker failure tracking."""
        raise exc

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        data = json.dumps(state, default=str)

        async def _op():
            pipe = self._redis.pipeline()
            pipe.set(self._key(session_id), data, ex=self._ttl)
            pipe.sadd(INDEX_KEY, session_id)
            await pipe.execute()
            return True

        result = await self._execute(_op)
        if result is None:
            await self._fallback.save(session_id, state)

    async def get(self, session_id: str) -> dict[str, Any] | None:
        async def _op():
            data = await self._redis.get(self._key(session_id))
            if data is None:
                return _NOT_FOUND  # Key missing, distinct from operation failure
            return json.loads(data)

        result = await self._execute(_op)
        if result is None:
            # Circuit open or error — try fallback
            return await self._fallback.get(session_id)
        if result is _NOT_FOUND:
            return None
        return result

    async def checkpoint(self, session_id: str, phase: str, summary: str) -> None:
        state = await self.get(session_id) or {}

        if "checkpoints" not in state:
            state["checkpoints"] = []

        state["checkpoints"].append(
            {
                "phase": phase,
                "summary": summary,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        await self.save(session_id, state)

    async def list_sessions(self) -> list[str]:
        async def _op():
            members = await self._redis.smembers(INDEX_KEY)
            return [m.decode() if isinstance(m, bytes) else m for m in members]

        result = await self._execute(_op)
        if result is None:
            return await self._fallback.list_sessions()
        return result

    async def delete(self, session_id: str) -> None:
        async def _op():
            pipe = self._redis.pipeline()
            pipe.delete(self._key(session_id))
            pipe.srem(INDEX_KEY, session_id)
            await pipe.execute()
            return True

        result = await self._execute(_op)
        if result is None:
            await self._fallback.delete(session_id)
