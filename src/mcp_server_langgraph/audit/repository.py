"""
Audit Log Repository Implementations.

Provides storage implementations for UnifiedAuditEvent:
- InMemoryUnifiedAuditRepository: For testing and development
- PostgresUnifiedAuditRepository: For production use

These repositories implement the AuditRepositoryProtocol defined
in the service module.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.audit.service import AuditRepositoryProtocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

logger = logging.getLogger(__name__)


class InMemoryUnifiedAuditRepository:
    """
    In-memory implementation of audit repository.

    Stores events in memory for testing and development.
    NOT suitable for production use.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._events: list[UnifiedAuditEvent] = []
        self._sequence_counter: int = 0

    async def create(self, event: UnifiedAuditEvent) -> None:
        """
        Store an audit event.

        Args:
            event: The audit event to store.
        """
        self._events.append(event)
        logger.debug(f"Stored audit event: {event.event_id}")

    async def bulk_create(self, events: list[UnifiedAuditEvent]) -> None:
        """
        Store multiple audit events.

        Args:
            events: List of audit events to store.
        """
        self._events.extend(events)
        logger.debug(f"Stored {len(events)} audit events")

    async def query_by_regulation(
        self,
        regulation: Regulation,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by regulation tag.

        Args:
            regulation: Regulation to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        results = []
        for event in self._events:
            if event.regulation_tags and regulation.value in event.regulation_tags:
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event)
        return results

    async def query_by_category(
        self,
        category: AuditEventCategory,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by category.

        Args:
            category: Category to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        results = []
        for event in self._events:
            if event.category == category:
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event)
        return results

    async def query_by_actor(
        self,
        actor_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by actor ID.

        Args:
            actor_id: Actor ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        results = []
        for event in self._events:
            if event.actor.actor_id == actor_id:
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event)
        return results

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[UnifiedAuditEvent]:
        """
        Get all events in time range for integrity verification.

        Args:
            start_time: Start of range.
            end_time: End of range.

        Returns:
            List of events in range, ordered by sequence number.
        """
        results = [e for e in self._events if start_time <= e.timestamp <= end_time]
        return sorted(results, key=lambda e: e.sequence_number or 0)

    async def get_event_count(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """
        Get count of events in time range.

        Args:
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            Count of matching events.
        """
        count = 0
        for event in self._events:
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            count += 1
        return count

    async def get_latest_sequence_number(self) -> int:
        """
        Get the latest sequence number in the repository.

        Returns:
            Latest sequence number, or 0 if no events.
        """
        if not self._events:
            return 0
        return max(e.sequence_number or 0 for e in self._events)

    def clear(self) -> None:
        """Clear all stored events (for testing)."""
        self._events.clear()
        self._sequence_counter = 0


class PostgresUnifiedAuditRepository:
    """
    PostgreSQL implementation of unified audit repository.

    Stores UnifiedAuditEvent records with full regulatory compliance support.
    Uses the partitioned audit_logs table for efficient retention management.

    Features:
    - Full UnifiedAuditEvent storage with nested models (actor, context, ai_operation)
    - Query by regulation, category, actor with time range filtering
    - Sequence number tracking for hash chain integrity (FedRAMP AU-9)
    - Optimized for partitioned tables (monthly partitions)
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations.
        """
        self._session = session

    async def create(self, event: UnifiedAuditEvent) -> None:
        """
        Store an audit event.

        Serializes the Pydantic model to database record format,
        handling nested models (actor, context, ai_operation).

        Args:
            event: The audit event to store.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        # Convert Pydantic model to SQLAlchemy model
        model = UnifiedAuditModel(
            event_id=event.event_id,
            timestamp=event.timestamp,
            category=event.category.value,
            event_type=event.event_type.value,
            # Actor fields (flattened from nested model)
            actor_id=event.actor.actor_id,
            actor_type=event.actor.actor_type,
            username=event.actor.username,
            email=event.actor.email,
            organization_id=event.actor.organization_id,
            roles=event.actor.roles,
            # Resource fields
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            action=event.action,
            outcome=event.outcome,
            # Context fields (flattened)
            request_id=event.context.request_id,
            trace_id=event.context.trace_id,
            span_id=event.context.span_id,
            session_id=event.context.session_id,
            ip_address=event.context.ip_address,
            user_agent=event.context.user_agent,
            http_method=event.context.http_method,
            http_path=event.context.http_path,
            http_status=event.context.http_status,
            # Details (JSON)
            details=event.details,
            # AI operation (JSON, optional)
            ai_operation=event.ai_operation.model_dump() if event.ai_operation else None,
            # Integrity fields
            sequence_number=event.sequence_number,
            previous_hash=event.previous_hash,
            event_hash=event.event_hash,
            # Compliance
            regulation_tags=event.regulation_tags,
            retention_days=event.retention_days,
        )

        self._session.add(model)
        await self._session.flush()
        logger.debug(f"Stored unified audit event: {event.event_id}")

    async def bulk_create(self, events: list[UnifiedAuditEvent]) -> None:
        """
        Store multiple audit events efficiently.

        Args:
            events: List of audit events to store.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        models = []
        for event in events:
            model = UnifiedAuditModel(
                event_id=event.event_id,
                timestamp=event.timestamp,
                category=event.category.value,
                event_type=event.event_type.value,
                actor_id=event.actor.actor_id,
                actor_type=event.actor.actor_type,
                username=event.actor.username,
                email=event.actor.email,
                organization_id=event.actor.organization_id,
                roles=event.actor.roles,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action=event.action,
                outcome=event.outcome,
                request_id=event.context.request_id,
                trace_id=event.context.trace_id,
                span_id=event.context.span_id,
                session_id=event.context.session_id,
                ip_address=event.context.ip_address,
                user_agent=event.context.user_agent,
                http_method=event.context.http_method,
                http_path=event.context.http_path,
                http_status=event.context.http_status,
                details=event.details,
                ai_operation=event.ai_operation.model_dump() if event.ai_operation else None,
                sequence_number=event.sequence_number,
                previous_hash=event.previous_hash,
                event_hash=event.event_hash,
                regulation_tags=event.regulation_tags,
                retention_days=event.retention_days,
            )
            models.append(model)

        self._session.add_all(models)
        await self._session.flush()
        logger.debug(f"Stored {len(events)} unified audit events")

    def _model_to_event(self, model: Any) -> UnifiedAuditEvent:
        """
        Convert SQLAlchemy model back to Pydantic model.

        Args:
            model: SQLAlchemy UnifiedAuditModel instance.

        Returns:
            UnifiedAuditEvent Pydantic model.
        """
        from mcp_server_langgraph.audit.models import AIOperationDetails

        # Reconstruct nested models
        actor = AuditActor(
            actor_id=model.actor_id,
            actor_type=model.actor_type,
            username=model.username,
            email=model.email,
            organization_id=model.organization_id,
            roles=model.roles or [],
        )

        context = AuditContext(
            request_id=model.request_id,
            trace_id=model.trace_id,
            span_id=model.span_id,
            session_id=model.session_id,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            http_method=model.http_method,
            http_path=model.http_path,
            http_status=model.http_status,
        )

        ai_operation = None
        if model.ai_operation:
            ai_operation = AIOperationDetails(**model.ai_operation)

        return UnifiedAuditEvent(
            event_id=model.event_id,
            timestamp=model.timestamp,
            category=AuditEventCategory(model.category),
            event_type=AuditEventType(model.event_type),
            actor=actor,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            action=model.action,
            outcome=model.outcome,
            context=context,
            details=model.details or {},
            ai_operation=ai_operation,
            sequence_number=model.sequence_number,
            previous_hash=model.previous_hash,
            event_hash=model.event_hash,
            regulation_tags=model.regulation_tags or [],
            retention_days=model.retention_days,
        )

    async def query_by_regulation(
        self,
        regulation: Regulation,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by regulation tag.

        Uses PostgreSQL array contains operator for efficient filtering.

        Args:
            regulation: Regulation to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        conditions = [UnifiedAuditModel.regulation_tags.contains([regulation.value])]

        if start_time:
            conditions.append(UnifiedAuditModel.timestamp >= start_time)
        if end_time:
            conditions.append(UnifiedAuditModel.timestamp <= end_time)

        stmt = select(UnifiedAuditModel).where(and_(*conditions)).order_by(UnifiedAuditModel.sequence_number)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_event(m) for m in models]

    async def query_by_category(
        self,
        category: AuditEventCategory,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by category.

        Args:
            category: Category to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        conditions = [UnifiedAuditModel.category == category.value]

        if start_time:
            conditions.append(UnifiedAuditModel.timestamp >= start_time)
        if end_time:
            conditions.append(UnifiedAuditModel.timestamp <= end_time)

        stmt = select(UnifiedAuditModel).where(and_(*conditions)).order_by(UnifiedAuditModel.sequence_number)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_event(m) for m in models]

    async def query_by_actor(
        self,
        actor_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by actor ID.

        Args:
            actor_id: Actor ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        conditions = [UnifiedAuditModel.actor_id == actor_id]

        if start_time:
            conditions.append(UnifiedAuditModel.timestamp >= start_time)
        if end_time:
            conditions.append(UnifiedAuditModel.timestamp <= end_time)

        stmt = select(UnifiedAuditModel).where(and_(*conditions)).order_by(UnifiedAuditModel.sequence_number)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_event(m) for m in models]

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[UnifiedAuditEvent]:
        """
        Get all events in time range for integrity verification.

        Events are ordered by sequence_number for hash chain verification.

        Args:
            start_time: Start of range.
            end_time: End of range.

        Returns:
            List of events in range, ordered by sequence number.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        stmt = (
            select(UnifiedAuditModel)
            .where(
                and_(
                    UnifiedAuditModel.timestamp >= start_time,
                    UnifiedAuditModel.timestamp <= end_time,
                )
            )
            .order_by(UnifiedAuditModel.sequence_number)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_event(m) for m in models]

    async def get_event_count(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """
        Get count of events in time range.

        Args:
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            Count of matching events.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        stmt = select(func.count(UnifiedAuditModel.event_id))

        conditions = []
        if start_time:
            conditions.append(UnifiedAuditModel.timestamp >= start_time)
        if end_time:
            conditions.append(UnifiedAuditModel.timestamp <= end_time)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self._session.execute(stmt)
        count = result.scalar()

        return count or 0

    async def get_latest_sequence_number(self) -> int:
        """
        Get the latest sequence number in the repository.

        Returns:
            Latest sequence number, or 0 if no events.
        """
        from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

        stmt = select(func.max(UnifiedAuditModel.sequence_number))
        result = await self._session.execute(stmt)
        max_seq = result.scalar()

        return max_seq or 0


class SessionManagedAuditRepository:
    """
    Session-managed wrapper for PostgresUnifiedAuditRepository.

    This wrapper manages database sessions internally, creating a new session
    for each operation and handling commit/rollback automatically. This allows
    the repository to be used without external session management, making it
    suitable for app-level initialization where a long-lived repository is needed.

    Features:
    - Creates a new session for each database operation
    - Automatically commits on success, rolls back on failure
    - Delegates all operations to PostgresUnifiedAuditRepository
    - Suitable for production use with proper connection pooling
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize with database URL.

        Args:
            database_url: PostgreSQL connection URL (asyncpg driver).
        """
        self._database_url = database_url

    async def create(self, event: UnifiedAuditEvent) -> None:
        """
        Store an audit event with automatic session management.

        Args:
            event: The audit event to store.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            try:
                repo = PostgresUnifiedAuditRepository(session)
                await repo.create(event)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def bulk_create(self, events: list[UnifiedAuditEvent]) -> None:
        """
        Store multiple audit events with automatic session management.

        Args:
            events: List of audit events to store.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            try:
                repo = PostgresUnifiedAuditRepository(session)
                await repo.bulk_create(events)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def query_by_regulation(
        self,
        regulation: Regulation,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by regulation tag.

        Args:
            regulation: Regulation to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.query_by_regulation(regulation, start_time, end_time)

    async def query_by_category(
        self,
        category: AuditEventCategory,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by category.

        Args:
            category: Category to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.query_by_category(category, start_time, end_time)

    async def query_by_actor(
        self,
        actor_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query events by actor ID.

        Args:
            actor_id: Actor ID to filter by.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            List of matching events.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.query_by_actor(actor_id, start_time, end_time)

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[UnifiedAuditEvent]:
        """
        Get all events in time range for integrity verification.

        Args:
            start_time: Start of range.
            end_time: End of range.

        Returns:
            List of events in range, ordered by sequence number.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.get_events_in_range(start_time, end_time)

    async def get_event_count(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """
        Get count of events in time range.

        Args:
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            Count of matching events.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.get_event_count(start_time, end_time)

    async def get_latest_sequence_number(self) -> int:
        """
        Get the latest sequence number in the repository.

        Returns:
            Latest sequence number, or 0 if no events.
        """
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(self._database_url)
        async with session_maker() as session:
            repo = PostgresUnifiedAuditRepository(session)
            return await repo.get_latest_sequence_number()


def create_audit_repository(
    database_url: str | None = None,
) -> "AuditRepositoryProtocol":
    """
    Factory function to create the appropriate audit repository.

    Creates:
    - SessionManagedAuditRepository if database_url is provided (production)
    - InMemoryUnifiedAuditRepository if database_url is None (testing/dev)

    Args:
        database_url: Optional PostgreSQL connection URL.

    Returns:
        Audit repository instance.
    """
    repo: AuditRepositoryProtocol
    if database_url:
        logger.info("Creating PostgreSQL audit repository for production")
        repo = SessionManagedAuditRepository(database_url)  # type: ignore[assignment]
    else:
        logger.info("Creating in-memory audit repository for development/testing")
        repo = InMemoryUnifiedAuditRepository()  # type: ignore[assignment]
    return repo
