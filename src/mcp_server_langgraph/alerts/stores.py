"""
Alert Store Implementations.

Provides both in-memory and PostgreSQL-backed alert stores.

Usage:
    # Development/Testing (in-memory)
    store = InMemoryAlertStore()

    # Production (PostgreSQL)
    store = PostgresAlertStore(session_maker)

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import logging
from datetime import datetime, UTC
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mcp_server_langgraph.alerts.models import AlertRecord
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class AlertStoreProtocol(Protocol):
    """Protocol for alert storage implementations."""

    async def add_alert(self, alert: Alert) -> None:
        """Add or update an alert in the store."""
        ...

    async def get_alert(self, alert_id: str) -> Alert | None:
        """Get an alert by ID."""
        ...

    async def remove_alert(self, alert_id: str) -> None:
        """Remove an alert from the store."""
        ...

    async def list_alerts(
        self,
        severity: list[AlertSeverity] | None = None,
        state: list[AlertState] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts with optional filtering."""
        ...

    async def clear(self) -> None:
        """Clear all alerts from the store."""
        ...


class InMemoryAlertStore:
    """
    In-memory alert store for development and testing.

    Not persistent - alerts are lost on restart.
    Use PostgresAlertStore for production.
    """

    def __init__(self) -> None:
        """Initialize empty alert store."""
        self._alerts: dict[str, Alert] = {}

    async def add_alert(self, alert: Alert) -> None:
        """Add or update an alert in the store."""
        self._alerts[alert.alert_id] = alert
        logger.debug(f"Added alert {alert.alert_id} to in-memory store")

    async def get_alert(self, alert_id: str) -> Alert | None:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    async def remove_alert(self, alert_id: str) -> None:
        """Remove an alert from the store."""
        self._alerts.pop(alert_id, None)
        logger.debug(f"Removed alert {alert_id} from in-memory store")

    async def list_alerts(
        self,
        severity: list[AlertSeverity] | None = None,
        state: list[AlertState] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts with optional filtering."""
        alerts = list(self._alerts.values())

        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity in severity]
        if state:
            alerts = [a for a in alerts if a.state in state]

        # Sort by started_at descending (newest first)
        alerts.sort(key=lambda a: a.started_at or datetime.min.replace(tzinfo=UTC), reverse=True)

        # Apply pagination
        return alerts[offset : offset + limit]

    async def clear(self) -> None:
        """Clear all alerts from the store."""
        self._alerts.clear()
        logger.debug("Cleared all alerts from in-memory store")

    # Sync methods for backward compatibility with existing AlertStore
    def add_alert_sync(self, alert: Alert) -> None:
        """Synchronous add for backward compatibility."""
        self._alerts[alert.alert_id] = alert

    def get_alert_sync(self, alert_id: str) -> Alert | None:
        """Synchronous get for backward compatibility."""
        return self._alerts.get(alert_id)


class PostgresAlertStore:
    """
    PostgreSQL-backed alert store for production use.

    Provides persistent storage with:
    - Automatic cleanup via retention policies
    - Efficient indexed queries
    - Transaction support
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize PostgreSQL alert store.

        Args:
            session_maker: SQLAlchemy async session maker.
        """
        self._session_maker = session_maker

    def _alert_to_record(self, alert: Alert) -> dict[str, Any]:
        """Convert Alert dataclass to record dict."""
        return {
            "alert_id": alert.alert_id,
            "name": alert.name,
            "severity": alert.severity.value,
            "state": alert.state.value,
            "message": alert.message,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "started_at": alert.started_at,
            "ended_at": alert.ended_at,
            "generator_url": alert.generator_url,
        }

    def _record_to_alert(self, record: AlertRecord) -> Alert:
        """Convert AlertRecord to Alert dataclass."""
        return Alert(
            alert_id=record.alert_id,
            name=record.name,
            severity=AlertSeverity(record.severity),
            state=AlertState(record.state),
            message=record.message,
            labels=record.labels or {},
            annotations=record.annotations or {},
            started_at=record.started_at,
            ended_at=record.ended_at,
            generator_url=record.generator_url,
        )

    async def add_alert(self, alert: Alert) -> None:
        """Add or update an alert in the store."""
        async with self._session_maker() as session:
            # Check if alert exists
            stmt = select(AlertRecord).where(AlertRecord.alert_id == alert.alert_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                for key, value in self._alert_to_record(alert).items():
                    if key != "alert_id":  # Don't update primary key
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(UTC)
            else:
                # Create new record
                record = AlertRecord(**self._alert_to_record(alert))
                session.add(record)

            await session.commit()
            logger.debug(f"Stored alert {alert.alert_id} in PostgreSQL")

    async def get_alert(self, alert_id: str) -> Alert | None:
        """Get an alert by ID."""
        async with self._session_maker() as session:
            stmt = select(AlertRecord).where(AlertRecord.alert_id == alert_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                return self._record_to_alert(record)
            return None

    async def remove_alert(self, alert_id: str) -> None:
        """Remove an alert from the store."""
        async with self._session_maker() as session:
            stmt = delete(AlertRecord).where(AlertRecord.alert_id == alert_id)
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"Removed alert {alert_id} from PostgreSQL")

    async def list_alerts(
        self,
        severity: list[AlertSeverity] | None = None,
        state: list[AlertState] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts with optional filtering."""
        async with self._session_maker() as session:
            stmt = select(AlertRecord)

            # Apply filters
            if severity:
                severity_values = [s.value for s in severity]
                stmt = stmt.where(AlertRecord.severity.in_(severity_values))
            if state:
                state_values = [s.value for s in state]
                stmt = stmt.where(AlertRecord.state.in_(state_values))

            # Order by started_at descending
            stmt = stmt.order_by(AlertRecord.started_at.desc())

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [self._record_to_alert(r) for r in records]

    async def clear(self) -> None:
        """Clear all alerts from the store."""
        async with self._session_maker() as session:
            stmt = delete(AlertRecord)
            await session.execute(stmt)
            await session.commit()
            logger.debug("Cleared all alerts from PostgreSQL")
