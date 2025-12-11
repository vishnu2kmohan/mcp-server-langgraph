"""
Session management for the Interactive Playground.

Provides persistent session storage with multiple backends:
- PostgreSQL: Durable persistence for production (ACID guarantees, analytics)
- Redis: Session-like storage with optional TTL
- Message history tracking with ordering
- User-scoped session listing with search and pagination
- Connection pooling

Example (PostgreSQL - recommended for production):
    from mcp_server_langgraph.playground.session import (
        PostgresSessionManager,
        create_postgres_engine,
        init_playground_database,
        Session,
        Message,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/playground")
    await init_playground_database(engine)
    manager = PostgresSessionManager(engine=engine)

    session = await manager.create_session(name="My Chat", user_id="user-123")

Example (Redis):
    from mcp_server_langgraph.playground.session import (
        RedisSessionManager,
        create_redis_pool,
    )

    redis_pool = await create_redis_pool("redis://localhost:6379/2")
    manager = RedisSessionManager(redis_client=redis_pool)
"""

from .manager import RedisSessionManager, create_redis_pool
from .models import Message, Session, SessionConfig
from .postgres_manager import (
    PostgresSessionManager,
    create_postgres_engine,
    init_playground_database,
)
from .postgres_models import MessageModel, PlaygroundBase, SessionModel

__all__ = [
    # Postgres storage (recommended for production)
    "PostgresSessionManager",
    "create_postgres_engine",
    "init_playground_database",
    "PlaygroundBase",
    "SessionModel",
    "MessageModel",
    # Redis storage
    "RedisSessionManager",
    "create_redis_pool",
    # Shared models
    "Session",
    "Message",
    "SessionConfig",
]
