"""
Unified Audit Service.

Core service for audit logging with:
- Automatic hash chain maintenance (FedRAMP AU-9)
- Batch logging for performance
- Regulation-based queries
- Integrity verification

This service wraps the audit repository and adds compliance features.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.integrity import (
    ChainVerificationResult,
    HashChainBuilder,
    verify_chain,
)
from mcp_server_langgraph.audit.models import (
    AuditEventCategory,
    UnifiedAuditEvent,
)

logger = logging.getLogger(__name__)


class AuditRepositoryProtocol(Protocol):
    """Protocol for audit repositories."""

    async def create(self, event: UnifiedAuditEvent) -> None:
        """Create a single audit event."""
        ...

    async def bulk_create(self, events: list[UnifiedAuditEvent]) -> None:
        """Create multiple audit events."""
        ...

    async def query_by_regulation(
        self,
        regulation: Regulation,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[UnifiedAuditEvent]:
        """Query events by regulation tag."""
        ...

    async def query_by_category(
        self,
        category: AuditEventCategory,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[UnifiedAuditEvent]:
        """Query events by category."""
        ...

    async def query_by_actor(
        self,
        actor_id: str,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[UnifiedAuditEvent]:
        """Query events by actor ID."""
        ...

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[UnifiedAuditEvent]:
        """Get all events in time range for integrity verification."""
        ...

    async def get_event_count(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Get count of events in time range."""
        ...

    async def delete_expired_by_regulation(self, regulation: Regulation) -> int:
        """Delete expired events for a regulation, returns count deleted."""
        ...

    async def get_retention_status(self) -> dict[str, dict[str, int]]:
        """Get retention status per regulation."""
        ...

    async def query_events(
        self,
        category: str | None = None,
        event_type: str | None = None,
        regulation: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query events with multiple filters and pagination."""
        ...

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get a single event by ID."""
        ...

    async def export_events(
        self,
        start_time: datetime,
        end_time: datetime,
        category: str | None = None,
        regulation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Export events for a time range."""
        ...


class UnifiedAuditService:
    """
    Unified audit service with hash chain support.

    Provides:
    - Automatic hash chain for tamper-evidence (FedRAMP AU-9)
    - Batch logging for high-throughput scenarios
    - Regulation-specific queries
    - Chain integrity verification
    - Retention policy management

    Example:
        service = UnifiedAuditService(
            repository=PostgresAuditRepository(session),
            integrity_secret="your-hmac-secret",
        )

        # Log single event
        await service.log_event(audit_event)

        # Batch log for performance
        await service.batch_log_events(events)

        # Verify integrity
        result = await service.verify_integrity(start, end)
    """

    def __init__(
        self,
        repository: AuditRepositoryProtocol,
        integrity_secret: str,
        broadcaster: Any | None = None,
        alert_detector: Any | None = None,
    ) -> None:
        """
        Initialize audit service.

        Args:
            repository: Repository for persisting audit events.
            integrity_secret: HMAC secret for hash chain computation.
            broadcaster: Optional broadcaster for real-time event streaming.
            alert_detector: Optional AuditAlertDetector for real-time alert detection.
        """
        self._repository = repository
        self._integrity_secret = integrity_secret
        self._chain_builder = HashChainBuilder(secret=integrity_secret)
        self._broadcaster = broadcaster
        self._alert_detector = alert_detector

    async def log_event(self, event: UnifiedAuditEvent) -> None:
        """
        Log a single audit event with hash chain.

        The event is added to the hash chain and persisted to the repository.
        Failures are logged but not raised (FedRAMP AU-5 graceful handling).

        Args:
            event: The audit event to log.
        """
        try:
            # Add to hash chain
            chained_event = self._chain_builder.add_to_chain(event)

            # Persist to repository
            await self._repository.create(chained_event)

            # Broadcast to real-time subscribers if broadcaster is configured
            if self._broadcaster is not None:
                try:
                    await self._broadcaster.broadcast(chained_event.model_dump())
                except Exception as broadcast_error:
                    logger.warning(
                        "Failed to broadcast audit event",
                        extra={"error": str(broadcast_error)},
                    )

            # Process event for alert detection if detector is configured
            if self._alert_detector is not None:
                try:
                    await self._alert_detector.process_event_async(chained_event)
                except Exception as alert_error:
                    logger.warning(
                        "Failed to process audit event for alerts",
                        extra={"error": str(alert_error)},
                    )

        except Exception as e:
            # FedRAMP AU-5: Handle audit failures gracefully
            logger.exception(
                "Failed to log audit event",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type": event.event_type,
                    "category": event.category,
                },
            )

    async def batch_log_events(self, events: list[UnifiedAuditEvent]) -> None:
        """
        Log multiple events in a batch with hash chain.

        Events are chained together and persisted in a single operation
        for better performance with high-volume audit scenarios.

        Args:
            events: List of audit events to log.
        """
        if not events:
            return

        try:
            # Add all events to hash chain
            chained_events = []
            for event in events:
                chained_event = self._chain_builder.add_to_chain(event)
                chained_events.append(chained_event)

            # Bulk persist
            await self._repository.bulk_create(chained_events)

        except Exception as e:
            logger.exception(
                "Failed to batch log audit events",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_count": len(events),
                },
            )

    async def query_by_regulation(
        self,
        regulation: Regulation,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query audit events by regulation tag.

        Args:
            regulation: The regulation to filter by (GDPR, HIPAA, etc.)
            start_time: Optional start of time range.
            end_time: Optional end of time range.

        Returns:
            List of matching audit events.
        """
        return await self._repository.query_by_regulation(regulation, start_time, end_time)

    async def query_by_category(
        self,
        category: AuditEventCategory,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query audit events by category.

        Args:
            category: The event category to filter by.
            start_time: Optional start of time range.
            end_time: Optional end of time range.

        Returns:
            List of matching audit events.
        """
        return await self._repository.query_by_category(category, start_time, end_time)

    async def query_by_actor(
        self,
        actor_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[UnifiedAuditEvent]:
        """
        Query audit events by actor.

        Args:
            actor_id: The actor ID to filter by.
            start_time: Optional start of time range.
            end_time: Optional end of time range.

        Returns:
            List of matching audit events.
        """
        return await self._repository.query_by_actor(actor_id, start_time, end_time)

    async def verify_integrity(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> ChainVerificationResult:
        """
        Verify hash chain integrity for a time range.

        Retrieves all events in the range and verifies:
        - Each event's hash matches recomputed hash
        - Chain linkage is correct (previous_hash references)
        - Sequence numbers are consecutive

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            ChainVerificationResult with validity and any errors.
        """
        events = await self._repository.get_events_in_range(start_time, end_time)
        return verify_chain(events, self._integrity_secret)

    async def get_integrity_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """
        Generate integrity verification report.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            Dictionary with integrity report including:
            - start_time, end_time
            - events_verified
            - chain_valid
            - errors (if any)
            - verification_time
        """
        verification_start = datetime.now(UTC)

        result = await self.verify_integrity(start_time, end_time)

        verification_end = datetime.now(UTC)
        verification_duration = (verification_end - verification_start).total_seconds()

        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "events_verified": result.events_verified,
            "chain_valid": result.valid,
            "errors": result.errors,
            "verification_time": verification_duration,
            "verified_at": verification_end.isoformat(),
        }

    async def apply_retention_policy(self, regulation: Regulation) -> int:
        """
        Apply retention policy for a specific regulation.

        Deletes events that have exceeded their retention period
        based on the regulation's requirements.

        Args:
            regulation: The regulation to apply retention for.

        Returns:
            Number of events deleted.
        """
        return await self._repository.delete_expired_by_regulation(regulation)

    async def get_retention_status(self) -> dict[str, dict[str, int]]:
        """
        Get retention status per regulation.

        Returns:
            Dictionary with per-regulation status including:
            - total: Total event count
            - expiring_soon: Events expiring within 30 days
        """
        return await self._repository.get_retention_status()

    async def query_events(
        self,
        category: str | None = None,
        event_type: str | None = None,
        regulation: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query audit events with multiple filters and pagination.

        Args:
            category: Filter by event category.
            event_type: Filter by event type.
            regulation: Filter by regulation tag.
            actor_id: Filter by actor ID.
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            start_time: Start of time range.
            end_time: End of time range.
            page: Page number (1-based).
            page_size: Number of events per page.

        Returns:
            Tuple of (events list, total count).
        """
        return await self._repository.query_events(
            category=category,
            event_type=event_type,
            regulation=regulation,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """
        Get a single audit event by ID.

        Args:
            event_id: The event ID to retrieve.

        Returns:
            Event details or None if not found.
        """
        return await self._repository.get_event(event_id)

    async def export_events(
        self,
        start_time: datetime,
        end_time: datetime,
        category: str | None = None,
        regulation: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Export audit events for a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            category: Optional category filter.
            regulation: Optional regulation filter.

        Returns:
            List of event dictionaries.
        """
        return await self._repository.export_events(
            start_time=start_time,
            end_time=end_time,
            category=category,
            regulation=regulation,
        )

    async def export_events_csv(
        self,
        start_time: datetime,
        end_time: datetime,
        category: str | None = None,
        regulation: str | None = None,
    ) -> str:
        """
        Export audit events as CSV.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            category: Optional category filter.
            regulation: Optional regulation filter.

        Returns:
            CSV string.
        """
        events = await self.export_events(
            start_time=start_time,
            end_time=end_time,
            category=category,
            regulation=regulation,
        )

        if not events:
            return "event_id,timestamp,category,event_type,actor_id,resource_type,resource_id,action,outcome\n"

        import csv
        import io

        output = io.StringIO()
        # Use keys from first event as headers
        fieldnames = list(events[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for event in events:
            writer.writerow(event)

        return output.getvalue()
