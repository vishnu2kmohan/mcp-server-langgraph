"""
PostgreSQL-backed session manager for the Interactive Playground.

Provides durable persistence for production use-cases:
- ACID guarantees for session operations
- Full-text search on session names
- Complex queries for analytics
- Message history with ordering
- Chat learning and improvement capabilities

Example:
    from mcp_server_langgraph.playground.session.postgres_manager import (
        PostgresSessionManager,
        create_postgres_engine,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/playground")
    manager = PostgresSessionManager(engine=engine)

    # Create session
    session = await manager.create_session(
        name="My Chat",
        user_id="user-123",
    )

    # Add message
    await manager.add_message(session.session_id, role="user", content="Hello!")
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Message, Session, SessionConfig
from .postgres_models import MessageModel, PlaygroundBase, SessionModel


async def create_postgres_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 10,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine for session storage.

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
                     Example: postgresql+asyncpg://user:pass@localhost/playground
        echo: Whether to echo SQL statements (for debugging)
        pool_size: Connection pool size

    Returns:
        Configured AsyncEngine
    """
    engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    return engine


async def init_playground_database(engine: AsyncEngine) -> None:
    """
    Initialize the playground database schema.

    Creates all tables defined in PlaygroundBase if they don't exist.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(PlaygroundBase.metadata.create_all)


class PostgresSessionManager:
    """
    PostgreSQL-backed session manager for playground sessions.

    Provides durable storage with ACID guarantees for production use.
    Messages are stored in a separate table for better query performance.
    """

    def __init__(
        self,
        engine: AsyncEngine,
    ) -> None:
        """
        Initialize the session manager.

        Args:
            engine: SQLAlchemy async engine
        """
        self._engine = engine
        self._session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def create_session(
        self,
        name: str,
        user_id: str | None = None,
        config: SessionConfig | None = None,
    ) -> Session:
        """
        Create a new session and store it in PostgreSQL.

        Args:
            name: Session name
            user_id: Optional user ID for scoping
            config: Optional LLM configuration

        Returns:
            Created session
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        cfg = config or SessionConfig()

        session_model = SessionModel(
            id=session_id,
            name=name,
            user_id=user_id,
            config_model=cfg.model,
            config_temperature=cfg.temperature,
            config_max_tokens=cfg.max_tokens,
            created_at=now,
            updated_at=now,
        )

        async with self._session_maker() as db_session:
            db_session.add(session_model)
            await db_session.commit()
            await db_session.refresh(session_model)

        return self._model_to_session(session_model, messages=[])

    async def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session from PostgreSQL with all messages.

        Args:
            session_id: Session ID

        Returns:
            Session if found, None otherwise
        """
        async with self._session_maker() as db_session:
            # Get session
            result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_model = result.scalar_one_or_none()

            if not session_model:
                return None

            # Get messages ordered by order_index
            msg_result = await db_session.execute(
                select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.order_index)
            )
            message_models = msg_result.scalars().all()

            messages = [self._model_to_message(m) for m in message_models]
            return self._model_to_session(session_model, messages=messages)

    async def update_session(
        self,
        session_id: str,
        name: str | None = None,
        config: SessionConfig | None = None,
    ) -> Session | None:
        """
        Update session metadata.

        Args:
            session_id: Session ID
            name: Optional new name
            config: Optional new configuration

        Returns:
            Updated session if found, None otherwise
        """
        async with self._session_maker() as db_session:
            result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_model = result.scalar_one_or_none()

            if not session_model:
                return None

            # Update fields
            if name is not None:
                session_model.name = name
            if config is not None:
                session_model.config_model = config.model
                session_model.config_temperature = config.temperature
                session_model.config_max_tokens = config.max_tokens

            session_model.updated_at = datetime.now(UTC)

            await db_session.commit()
            await db_session.refresh(session_model)

            # Get messages
            msg_result = await db_session.execute(
                select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.order_index)
            )
            message_models = msg_result.scalars().all()

            messages = [self._model_to_message(m) for m in message_models]
            return self._model_to_session(session_model, messages=messages)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages from PostgreSQL.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        async with self._session_maker() as db_session:
            result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_model = result.scalar_one_or_none()

            if not session_model:
                return False

            # Delete messages first
            msg_result = await db_session.execute(select(MessageModel).where(MessageModel.session_id == session_id))
            for msg in msg_result.scalars().all():
                await db_session.delete(msg)

            # Delete session
            await db_session.delete(session_model)
            await db_session.commit()

            return True

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message | None:
        """
        Add a message to session history.

        Args:
            session_id: Session ID to add message to
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional message metadata

        Returns:
            Created message if session found, None otherwise
        """
        async with self._session_maker() as db_session:
            # Check session exists
            result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_model = result.scalar_one_or_none()

            if not session_model:
                return None

            # Get current message count for order_index
            count_result = await db_session.execute(select(MessageModel).where(MessageModel.session_id == session_id))
            order_index = len(count_result.scalars().all())

            # Create message
            message_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            message_model = MessageModel(
                id=message_id,
                session_id=session_id,
                role=role,
                content=content,
                metadata_json=metadata or {},
                timestamp=now,
                order_index=order_index,
            )

            db_session.add(message_model)

            # Update session's updated_at
            session_model.updated_at = now

            await db_session.commit()
            await db_session.refresh(message_model)

            return self._model_to_message(message_model)

    async def list_sessions(
        self,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> list[Session]:
        """
        List sessions, optionally filtered by user and search term.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            search: Optional search term for name

        Returns:
            List of sessions (without messages for performance)
        """
        async with self._session_maker() as db_session:
            query = select(SessionModel)

            # Filter by user if provided
            if user_id:
                query = query.where(SessionModel.user_id == user_id)

            # Search by name if provided
            if search:
                search_term = f"%{search}%"
                query = query.where(SessionModel.name.ilike(search_term))

            # Order by most recently updated
            query = query.order_by(SessionModel.updated_at.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await db_session.execute(query)
            models = result.scalars().all()

            # Return sessions without loading all messages (performance)
            return [self._model_to_session(m, messages=[]) for m in models]

    async def close(self) -> None:
        """Close the database engine."""
        await self._engine.dispose()

    def _model_to_session(self, model: SessionModel, messages: list[Message]) -> Session:
        """Convert SQLAlchemy model to Pydantic model."""
        return Session(
            session_id=model.id,
            name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
            messages=messages,
            config=SessionConfig(
                model=model.config_model,
                temperature=model.config_temperature,
                max_tokens=model.config_max_tokens,
            ),
            user_id=model.user_id,
        )

    def _model_to_message(self, model: MessageModel) -> Message:
        """Convert SQLAlchemy message model to Pydantic model."""
        return Message(
            message_id=model.id,
            role=model.role,
            content=model.content,
            timestamp=model.timestamp,
            metadata=model.metadata_json,
        )
