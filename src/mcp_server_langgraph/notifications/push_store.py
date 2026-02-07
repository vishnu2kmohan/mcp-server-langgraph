"""
Push Subscription Store Module.

Models and storage for Web Push API subscriptions.
Enables browser push notifications for critical alerts.

Features:
- PushSubscription dataclass for subscription data
- PushSubscriptionStore protocol for persistence abstraction
- InMemoryPushSubscriptionStore for testing
- Subscription expiry handling

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sqlalchemy import DateTime, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PushSubscription:
    """
    Web Push API subscription data.

    Stores the information needed to send push notifications to a browser.
    Based on the PushSubscription interface from the Web Push API.

    Attributes:
        id: Unique subscription ID.
        user_id: The user who created this subscription.
        endpoint: Push service endpoint URL from PushSubscription.endpoint.
        p256dh_key: User's public key from PushSubscription.getKey('p256dh'), base64.
        auth_key: Auth secret from PushSubscription.getKey('auth'), base64.
        user_agent: Browser/device user agent string.
        device_name: User-provided device name for management UI.
        created_at: When the subscription was created.
        updated_at: When the subscription was last updated.
        expires_at: Optional expiration time from PushSubscription.expirationTime.
        last_used_at: When the last notification was sent to this subscription.
    """

    id: str
    user_id: str
    endpoint: str
    p256dh_key: str
    auth_key: str
    created_at: datetime
    updated_at: datetime
    user_agent: str | None = None
    device_name: str | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None

    def is_expired(self) -> bool:
        """
        Check if this subscription has expired.

        Returns:
            True if the subscription has a past expiration time.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


# =============================================================================
# Storage Protocol
# =============================================================================


@runtime_checkable
class PushSubscriptionStore(Protocol):
    """
    Protocol for push subscription persistence.

    Implementations can use PostgreSQL, Redis, or any other storage backend.
    """

    @abstractmethod
    async def save_subscription(self, subscription: PushSubscription) -> None:
        """
        Save a push subscription.

        If a subscription with the same endpoint already exists, it should be updated.

        Args:
            subscription: The subscription to save.
        """
        ...

    @abstractmethod
    async def get_subscriptions_for_user(self, user_id: str) -> list[PushSubscription]:
        """
        Get all subscriptions for a user.

        Args:
            user_id: The user ID to look up.

        Returns:
            List of subscriptions for the user.
        """
        ...

    @abstractmethod
    async def get_all_subscriptions(self) -> list[PushSubscription]:
        """
        Get all subscriptions.

        Returns:
            List of all subscriptions.
        """
        ...

    @abstractmethod
    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """
        Get a subscription by endpoint.

        Args:
            endpoint: The push service endpoint URL.

        Returns:
            The subscription if found, None otherwise.
        """
        ...

    @abstractmethod
    async def delete_subscription(self, endpoint: str) -> None:
        """
        Delete a subscription by endpoint.

        Args:
            endpoint: The push service endpoint URL.
        """
        ...

    @abstractmethod
    async def delete_expired_subscriptions(self) -> int:
        """
        Delete all expired subscriptions.

        Returns:
            Number of subscriptions deleted.
        """
        ...

    @abstractmethod
    async def update_last_used(self, endpoint: str, timestamp: datetime) -> None:
        """
        Update the last_used_at timestamp for a subscription.

        Args:
            endpoint: The push service endpoint URL.
            timestamp: The new timestamp.
        """
        ...


# =============================================================================
# In-Memory Implementation (for testing)
# =============================================================================


class InMemoryPushSubscriptionStore(PushSubscriptionStore):
    """
    In-memory push subscription store for testing.

    Not suitable for production as data is not persisted.
    """

    def __init__(self) -> None:
        """Initialize empty subscription store."""
        self._subscriptions: dict[str, PushSubscription] = {}  # endpoint -> subscription

    async def save_subscription(self, subscription: PushSubscription) -> None:
        """
        Save a subscription to memory.

        Uses endpoint as the unique key, so saving with the same endpoint updates.
        """
        self._subscriptions[subscription.endpoint] = subscription
        logger.debug(f"Saved push subscription for user {subscription.user_id} to endpoint {subscription.endpoint[:50]}...")

    async def get_subscriptions_for_user(self, user_id: str) -> list[PushSubscription]:
        """Get all subscriptions for a user."""
        return [sub for sub in self._subscriptions.values() if sub.user_id == user_id]

    async def get_all_subscriptions(self) -> list[PushSubscription]:
        """Get all subscriptions."""
        return list(self._subscriptions.values())

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """Get a subscription by endpoint."""
        return self._subscriptions.get(endpoint)

    async def delete_subscription(self, endpoint: str) -> None:
        """Delete a subscription by endpoint."""
        if endpoint in self._subscriptions:
            del self._subscriptions[endpoint]
            logger.debug(f"Deleted push subscription for endpoint {endpoint[:50]}...")

    async def delete_expired_subscriptions(self) -> int:
        """
        Delete all expired subscriptions.

        Returns:
            Number of subscriptions deleted.
        """
        expired_endpoints = [endpoint for endpoint, sub in self._subscriptions.items() if sub.is_expired()]

        for endpoint in expired_endpoints:
            del self._subscriptions[endpoint]

        if expired_endpoints:
            logger.debug(f"Deleted {len(expired_endpoints)} expired push subscriptions")

        return len(expired_endpoints)

    async def update_last_used(self, endpoint: str, timestamp: datetime) -> None:
        """Update the last_used_at timestamp for a subscription."""
        if endpoint in self._subscriptions:
            sub = self._subscriptions[endpoint]
            # Create a new dataclass instance with updated field
            self._subscriptions[endpoint] = PushSubscription(
                id=sub.id,
                user_id=sub.user_id,
                endpoint=sub.endpoint,
                p256dh_key=sub.p256dh_key,
                auth_key=sub.auth_key,
                user_agent=sub.user_agent,
                device_name=sub.device_name,
                created_at=sub.created_at,
                updated_at=datetime.now(UTC),
                expires_at=sub.expires_at,
                last_used_at=timestamp,
            )
            logger.debug(f"Updated last_used_at for endpoint {endpoint[:50]}...")


# =============================================================================
# SQLAlchemy Model
# =============================================================================


class PushSubscriptionRecord(Base):
    """
    SQLAlchemy model for push subscription records.

    Corresponds to the push_subscriptions table in PostgreSQL.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =============================================================================
# PostgreSQL Implementation
# =============================================================================


class PostgresPushSubscriptionStore(PushSubscriptionStore):
    """
    PostgreSQL-backed push subscription store.

    Production-ready implementation using SQLAlchemy async sessions.
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize the PostgreSQL push subscription store.

        Args:
            session_maker: SQLAlchemy async session factory.
        """
        self._session_maker = session_maker

    def _record_to_subscription(self, record: PushSubscriptionRecord) -> PushSubscription:
        """
        Convert a database record to a PushSubscription dataclass.

        Args:
            record: The database record.

        Returns:
            A PushSubscription instance.
        """
        return PushSubscription(
            id=record.id,
            user_id=record.user_id,
            endpoint=record.endpoint,
            p256dh_key=record.p256dh_key,
            auth_key=record.auth_key,
            user_agent=record.user_agent,
            device_name=record.device_name,
            created_at=record.created_at,
            updated_at=record.updated_at,
            expires_at=record.expires_at,
            last_used_at=record.last_used_at,
        )

    async def save_subscription(self, subscription: PushSubscription) -> None:
        """
        Save or update a push subscription.

        If a subscription with the same endpoint exists, it will be updated.
        """
        async with self._session_maker() as session:
            # Check if subscription exists
            stmt = select(PushSubscriptionRecord).where(PushSubscriptionRecord.endpoint == subscription.endpoint)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.user_id = subscription.user_id
                existing.p256dh_key = subscription.p256dh_key
                existing.auth_key = subscription.auth_key
                existing.user_agent = subscription.user_agent
                existing.device_name = subscription.device_name
                existing.updated_at = datetime.now(UTC)
                existing.expires_at = subscription.expires_at
            else:
                # Create new record
                record = PushSubscriptionRecord(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    endpoint=subscription.endpoint,
                    p256dh_key=subscription.p256dh_key,
                    auth_key=subscription.auth_key,
                    user_agent=subscription.user_agent,
                    device_name=subscription.device_name,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at,
                    expires_at=subscription.expires_at,
                    last_used_at=subscription.last_used_at,
                )
                session.add(record)

            await session.commit()
            logger.debug(
                f"Saved push subscription for user {subscription.user_id} to endpoint {subscription.endpoint[:50]}..."
            )

    async def get_subscriptions_for_user(self, user_id: str) -> list[PushSubscription]:
        """Get all subscriptions for a user."""
        async with self._session_maker() as session:
            stmt = select(PushSubscriptionRecord).where(PushSubscriptionRecord.user_id == user_id)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [self._record_to_subscription(r) for r in records]

    async def get_all_subscriptions(self) -> list[PushSubscription]:
        """Get all subscriptions."""
        async with self._session_maker() as session:
            stmt = select(PushSubscriptionRecord)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [self._record_to_subscription(r) for r in records]

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """Get a subscription by endpoint."""
        async with self._session_maker() as session:
            stmt = select(PushSubscriptionRecord).where(PushSubscriptionRecord.endpoint == endpoint)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                return self._record_to_subscription(record)
            return None

    async def delete_subscription(self, endpoint: str) -> None:
        """Delete a subscription by endpoint."""
        async with self._session_maker() as session:
            stmt = delete(PushSubscriptionRecord).where(PushSubscriptionRecord.endpoint == endpoint)
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"Deleted push subscription for endpoint {endpoint[:50]}...")

    async def delete_expired_subscriptions(self) -> int:
        """
        Delete all expired subscriptions.

        Returns:
            Number of subscriptions deleted.
        """
        async with self._session_maker() as session:
            now = datetime.now(UTC)
            stmt = delete(PushSubscriptionRecord).where(PushSubscriptionRecord.expires_at < now)
            result = await session.execute(stmt)
            await session.commit()

            deleted_count: int = getattr(result, "rowcount", 0) or 0
            if deleted_count > 0:
                logger.debug(f"Deleted {deleted_count} expired push subscriptions")
            return deleted_count

    async def update_last_used(self, endpoint: str, timestamp: datetime) -> None:
        """Update the last_used_at timestamp for a subscription."""
        async with self._session_maker() as session:
            stmt = select(PushSubscriptionRecord).where(PushSubscriptionRecord.endpoint == endpoint)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                record.last_used_at = timestamp
                record.updated_at = datetime.now(UTC)
                await session.commit()
                logger.debug(f"Updated last_used_at for endpoint {endpoint[:50]}...")
