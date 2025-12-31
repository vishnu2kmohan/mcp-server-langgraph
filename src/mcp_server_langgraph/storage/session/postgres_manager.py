"""
PostgreSQL-backed session manager for the unified Studio frontend.

Provides durable persistence for production use-cases:
- ACID guarantees for session operations
- Full-text search on session names
- Complex queries for analytics
- Message history with ordering
- Chat learning and improvement capabilities

Example:
    from mcp_server_langgraph.storage.session import (
        PostgresSessionManager,
        create_postgres_engine,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/db")
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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Message, Session, SessionConfig
from .postgres_models import MessageModel, SessionModel


async def create_postgres_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 10,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine for session storage.

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
                     Example: postgresql+asyncpg://user:pass@localhost/db
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


async def init_session_database(engine: AsyncEngine) -> None:
    """
    Initialize the session database connection.

    IMPORTANT: This function NO LONGER creates tables via create_all().
    All schema management is handled exclusively by Alembic migrations.

    The sessions and messages tables are created by migrations:
    - b2c3d4e5f6g7: Creates sessions and messages tables with FTS
    - m3n4o5p6q7r8: Adds session status and workflow_id columns

    Args:
        engine: SQLAlchemy async engine

    Note:
        Run 'alembic upgrade head' before using this manager.
    """
    # Verify engine is valid by testing connection
    async with engine.begin():
        pass  # Connection test - schema managed by Alembic


class PostgresSessionManager:
    """
    PostgreSQL-backed session manager for studio sessions.

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
        status: str = "active",
        workflow_id: str | None = None,
    ) -> Session:
        """
        Create a new session and store it in PostgreSQL.

        Args:
            name: Session name
            user_id: Optional user ID for scoping
            config: Optional LLM configuration
            status: Session status (active, archived)
            workflow_id: Optional associated workflow ID

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
            status=status,
            workflow_id=workflow_id,
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
        status: str | None = None,
        workflow_id: str | None = None,
    ) -> Session | None:
        """
        Update session metadata.

        Args:
            session_id: Session ID
            name: Optional new name
            config: Optional new configuration
            status: Optional new status (active, archived)
            workflow_id: Optional new workflow ID

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
            if status is not None:
                session_model.status = status
            if workflow_id is not None:
                session_model.workflow_id = workflow_id

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
        cursor: str | None = None,
        sort_by: str | None = "updated_at",
        sort_order: str | None = "desc",
        status: str | None = None,
        workflow_id: str | None = None,
    ) -> tuple[list[Session], str | None]:
        """
        List sessions with pagination, filtering, search, and sorting.

        Uses PostgreSQL Full-Text Search (FTS) for efficient search when available,
        falling back to ILIKE for databases without FTS triggers configured.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip (deprecated, use cursor)
            search: Optional search term for name (uses FTS)
            cursor: Optional cursor for cursor-based pagination
            sort_by: Field to sort by (title, created_at, updated_at)
            sort_order: Sort order (asc, desc)
            status: Optional status filter (active, archived)
            workflow_id: Optional workflow ID to filter by

        Returns:
            Tuple of (list of sessions without messages, next_cursor)
        """
        async with self._session_maker() as db_session:
            query = select(SessionModel)

            # Filter by user if provided
            if user_id:
                query = query.where(SessionModel.user_id == user_id)

            # Filter by status if provided
            if status:
                query = query.where(SessionModel.status == status)

            # Filter by workflow_id if provided
            if workflow_id:
                query = query.where(SessionModel.workflow_id == workflow_id)

            # Search using Full-Text Search (FTS) for efficiency
            if search:
                # Convert search term to tsquery format
                # plainto_tsquery handles plain text input safely
                search_query = func.plainto_tsquery("english", search)

                # Use FTS if search_vector is populated, fallback to ILIKE
                query = query.where(
                    SessionModel.search_vector.bool_op("@@")(search_query) | SessionModel.name.ilike(f"%{search}%")
                )

            # Apply sorting
            # Use Any type to allow different column types (str, datetime)
            sort_column: Any = SessionModel.updated_at  # Default
            if sort_by == "title" or sort_by == "name":
                sort_column = SessionModel.name
            elif sort_by == "created_at":
                sort_column = SessionModel.created_at

            if sort_order == "asc":
                query = query.order_by(sort_column.asc(), SessionModel.id.asc())
            else:
                query = query.order_by(sort_column.desc(), SessionModel.id.desc())

            # Apply cursor-based pagination
            if cursor:
                # Get the cursor session to compare against
                cursor_result = await db_session.execute(select(SessionModel).where(SessionModel.id == cursor))
                cursor_model = cursor_result.scalar_one_or_none()
                if cursor_model:
                    # Apply cursor condition based on sort column
                    if sort_order == "asc":
                        if sort_by == "title" or sort_by == "name":
                            query = query.where(
                                (SessionModel.name > cursor_model.name)
                                | ((SessionModel.name == cursor_model.name) & (SessionModel.id > cursor_model.id))
                            )
                        elif sort_by == "created_at":
                            query = query.where(
                                (SessionModel.created_at > cursor_model.created_at)
                                | ((SessionModel.created_at == cursor_model.created_at) & (SessionModel.id > cursor_model.id))
                            )
                        else:  # updated_at
                            query = query.where(
                                (SessionModel.updated_at > cursor_model.updated_at)
                                | ((SessionModel.updated_at == cursor_model.updated_at) & (SessionModel.id > cursor_model.id))
                            )
                    else:  # desc
                        if sort_by == "title" or sort_by == "name":
                            query = query.where(
                                (SessionModel.name < cursor_model.name)
                                | ((SessionModel.name == cursor_model.name) & (SessionModel.id < cursor_model.id))
                            )
                        elif sort_by == "created_at":
                            query = query.where(
                                (SessionModel.created_at < cursor_model.created_at)
                                | ((SessionModel.created_at == cursor_model.created_at) & (SessionModel.id < cursor_model.id))
                            )
                        else:  # updated_at
                            query = query.where(
                                (SessionModel.updated_at < cursor_model.updated_at)
                                | ((SessionModel.updated_at == cursor_model.updated_at) & (SessionModel.id < cursor_model.id))
                            )
            elif offset > 0:
                # Fallback to offset pagination for backward compatibility
                query = query.offset(offset)

            # Fetch limit + 1 to check for next page
            query = query.limit(limit + 1)

            result = await db_session.execute(query)
            models = list(result.scalars().all())

            # Determine next cursor
            next_cursor = None
            if len(models) > limit:
                models = models[:limit]
                next_cursor = models[-1].id if models else None

            # Return sessions without loading all messages (performance)
            sessions = [self._model_to_session(m, messages=[]) for m in models]
            return sessions, next_cursor

    async def clear_messages(self, session_id: str) -> bool:
        """
        Clear all messages in a session.

        Args:
            session_id: Session ID to clear messages from

        Returns:
            True if cleared, False if session not found
        """
        async with self._session_maker() as db_session:
            # Check session exists
            result = await db_session.execute(select(SessionModel).where(SessionModel.id == session_id))
            session_model = result.scalar_one_or_none()

            if not session_model:
                return False

            # Delete all messages for this session
            msg_result = await db_session.execute(select(MessageModel).where(MessageModel.session_id == session_id))
            for msg in msg_result.scalars().all():
                await db_session.delete(msg)

            # Update session's updated_at
            session_model.updated_at = datetime.now(UTC)

            await db_session.commit()
            return True

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
            status=model.status,
            workflow_id=model.workflow_id,
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
