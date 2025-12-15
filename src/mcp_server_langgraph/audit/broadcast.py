"""
Audit Event Broadcasting for Real-Time Monitoring.

Provides real-time streaming of audit events to connected WebSocket clients.

Features:
- Subscribe/unsubscribe pattern for WebSocket connections
- Event filtering by category, regulation, actor
- Graceful handling of disconnected clients
- Thread-safe subscriber management

Use Cases:
- Real-time compliance monitoring dashboards
- Security operations center (SOC) integration
- Audit event alerting
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class WebSocketConnection(Protocol):
    """Protocol for WebSocket connections."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket."""
        ...


@dataclass
class AuditEventFilter:
    """
    Filter for audit events.

    Events must match ALL specified criteria (AND logic).
    Empty criteria match all events.
    """

    categories: list[str] | None = None
    regulations: list[str] | None = None
    actors: list[str] | None = None
    event_types: list[str] | None = None

    def matches(self, event: dict[str, Any]) -> bool:
        """
        Check if an event matches this filter.

        Args:
            event: The audit event to check.

        Returns:
            True if the event matches all filter criteria.
        """
        # Check category
        if self.categories:
            event_category = event.get("category")
            if event_category not in self.categories:
                return False

        # Check regulations
        if self.regulations:
            event_regulations = event.get("regulation_tags", [])
            if not event_regulations:
                return False
            if not any(reg in event_regulations for reg in self.regulations):
                return False

        # Check actors
        if self.actors:
            event_actor = event.get("actor_id") or event.get("actor", {}).get("actor_id")
            if event_actor not in self.actors:
                return False

        # Check event types
        if self.event_types:
            event_type = event.get("event_type")
            if event_type not in self.event_types:
                return False

        return True


@dataclass
class Subscriber:
    """A WebSocket subscriber with optional filter."""

    connection: WebSocketConnection
    filter: AuditEventFilter = field(default_factory=AuditEventFilter)


class AuditEventBroadcaster:
    """
    Broadcasts audit events to subscribed WebSocket connections.

    Provides real-time streaming of audit events for compliance monitoring,
    security dashboards, and alerting integrations.
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        self._subscribers: list[Subscriber] = []
        self._lock = asyncio.Lock()

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    async def subscribe(
        self,
        connection: WebSocketConnection,
        filter_: AuditEventFilter | None = None,
    ) -> None:
        """
        Subscribe a WebSocket connection to audit events.

        Args:
            connection: The WebSocket connection to subscribe.
            filter_: Optional filter for events. If None, receives all events.
        """
        async with self._lock:
            subscriber = Subscriber(
                connection=connection,
                filter=filter_ or AuditEventFilter(),
            )
            self._subscribers.append(subscriber)
            logger.info(f"Subscriber added. Total: {self.subscriber_count}")

    async def unsubscribe(self, connection: WebSocketConnection) -> None:
        """
        Unsubscribe a WebSocket connection.

        Args:
            connection: The WebSocket connection to unsubscribe.
        """
        async with self._lock:
            self._subscribers = [s for s in self._subscribers if s.connection != connection]
            logger.info(f"Subscriber removed. Total: {self.subscriber_count}")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """
        Broadcast an audit event to all matching subscribers.

        Args:
            event: The audit event to broadcast.
        """
        if not self._subscribers:
            return

        failed_connections: list[WebSocketConnection] = []

        async with self._lock:
            for subscriber in self._subscribers:
                # Check if event matches subscriber's filter
                if not subscriber.filter.matches(event):
                    continue

                try:
                    await subscriber.connection.send_json(event)
                except Exception as e:
                    logger.warning(f"Failed to send to subscriber: {e}")
                    failed_connections.append(subscriber.connection)

            # Remove failed connections
            if failed_connections:
                self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")

    async def broadcast_batch(self, events: list[dict[str, Any]]) -> None:
        """
        Broadcast multiple audit events.

        Args:
            events: List of audit events to broadcast.
        """
        for event in events:
            await self.broadcast(event)
