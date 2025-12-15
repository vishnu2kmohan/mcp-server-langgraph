"""
Audit Log Repository Implementation

Provides storage and retrieval of audit log entries for connection operations.

Supports:
- Event logging with metadata
- Query with filtering
- Retention policy management
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.models.audit_log import AuditLogModel


class AuditLogRepository(ABC):
    """Abstract base class for audit log repository."""

    @abstractmethod
    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        action: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Log an audit event."""
        pass

    @abstractmethod
    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query audit logs with filtering."""
        pass

    @abstractmethod
    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get audit logs for a specific resource."""
        pass

    @abstractmethod
    async def delete_older_than(self, days: int) -> int:
        """Delete logs older than specified days."""
        pass


class PostgresAuditLogRepository(AuditLogRepository):
    """PostgreSQL implementation of AuditLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async database session."""
        self._session = session

    def _model_to_dict(self, model: AuditLogModel) -> dict[str, Any]:
        """Convert SQLAlchemy model to dictionary."""
        return {
            "id": str(model.id),
            "event_type": model.event_type,
            "resource_type": model.resource_type,
            "resource_id": model.resource_id,
            "actor_id": model.actor_id,
            "action": model.action,
            "details": model.details or {},
            "ip_address": model.ip_address,
            "user_agent": model.user_agent,
            "timestamp": model.timestamp,
        }

    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        action: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Log an audit event."""
        log_id = str(uuid4())
        now = datetime.now(UTC)

        model = AuditLogModel(
            id=log_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=now,
        )

        self._session.add(model)
        await self._session.flush()

        return self._model_to_dict(model)

    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query audit logs with filtering."""
        # Build base query
        stmt = select(AuditLogModel)
        conditions = []

        if resource_type:
            conditions.append(AuditLogModel.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLogModel.resource_id == resource_id)
        if actor_id:
            conditions.append(AuditLogModel.actor_id == actor_id)
        if event_type:
            conditions.append(AuditLogModel.event_type == event_type)
        if start_time:
            conditions.append(AuditLogModel.timestamp >= start_time)
        if end_time:
            conditions.append(AuditLogModel.timestamp <= end_time)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Get total count
        count_stmt = select(AuditLogModel.id)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self._session.execute(count_stmt)
        total = len(count_result.scalars().all())

        # Apply pagination and ordering
        stmt = stmt.order_by(AuditLogModel.timestamp.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_dict(m) for m in models], total

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get audit logs for a specific resource."""
        stmt = (
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.resource_type == resource_type,
                    AuditLogModel.resource_id == resource_id,
                )
            )
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_dict(m) for m in models]

    async def delete_older_than(self, days: int) -> int:
        """Delete logs older than specified days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        stmt = delete(AuditLogModel).where(AuditLogModel.timestamp < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()

        # CursorResult has rowcount but Result[Any] doesn't
        return getattr(result, "rowcount", 0) or 0


class InMemoryAuditLogRepository(AuditLogRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        action: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Log an audit event."""
        log_entry = {
            "id": str(uuid4()),
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor_id": actor_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(UTC),
        }
        self.logs.append(log_entry)
        return log_entry

    async def query(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query audit logs with filtering."""
        filtered = self.logs.copy()

        if resource_type:
            filtered = [log for log in filtered if log["resource_type"] == resource_type]
        if resource_id:
            filtered = [log for log in filtered if log["resource_id"] == resource_id]
        if actor_id:
            filtered = [log for log in filtered if log["actor_id"] == actor_id]
        if event_type:
            filtered = [log for log in filtered if log["event_type"] == event_type]
        if start_time:
            filtered = [log for log in filtered if log["timestamp"] >= start_time]
        if end_time:
            filtered = [log for log in filtered if log["timestamp"] <= end_time]

        # Sort by timestamp descending
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)

        total = len(filtered)
        filtered = filtered[offset : offset + limit]

        return filtered, total

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get audit logs for a specific resource."""
        filtered = [log for log in self.logs if log["resource_type"] == resource_type and log["resource_id"] == resource_id]
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        return filtered[:limit]

    async def delete_older_than(self, days: int) -> int:
        """Delete logs older than specified days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        original_count = len(self.logs)
        self.logs = [log for log in self.logs if log["timestamp"] >= cutoff]
        return original_count - len(self.logs)
