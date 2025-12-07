"""
Session management for the Interactive Playground.

Provides Redis-backed session storage with:
- Session persistence with TTL
- Message history tracking
- User-scoped session listing
- Connection pooling

Example:
    from mcp_server_langgraph.playground.session import (
        RedisSessionManager,
        Session,
        Message,
        create_redis_pool,
    )

    redis_pool = await create_redis_pool("redis://localhost:6379/2")
    manager = RedisSessionManager(redis_client=redis_pool)
"""

from .manager import RedisSessionManager, create_redis_pool
from .models import Message, Session, SessionConfig

__all__ = [
    "RedisSessionManager",
    "Session",
    "Message",
    "SessionConfig",
    "create_redis_pool",
]
