"""
Integration tests for audit repository.

TDD RED phase: These tests verify PostgreSQL persistence.

The repository should:
- Persist events to PostgreSQL
- Support querying by regulation, category, time range
- Support pagination and filtering
- Handle concurrent writes correctly
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_repository")
class TestAuditRepositoryPersistence:
    """Tests for event persistence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_log_event_persists_to_repository(self) -> None:
        """GIVEN audit event WHEN logged THEN persisted to repository."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.create = AsyncMock(return_value=None)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id="req-001"),
        )

        await service.log_event(event)

        mock_repo.create.assert_called_once()
        logged_event = mock_repo.create.call_args.args[0]
        assert logged_event.actor.actor_id == "user:alice"
        assert logged_event.event_hash is not None

    @pytest.mark.asyncio
    async def test_batch_log_persists_all_events(self) -> None:
        """GIVEN batch of events WHEN logged THEN all persisted."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.bulk_create = AsyncMock(return_value=None)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events = [
            UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:bob", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            for i in range(10)
        ]

        await service.batch_log_events(events)

        mock_repo.bulk_create.assert_called_once()
        logged_events = mock_repo.bulk_create.call_args.args[0]
        assert len(logged_events) == 10


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_repository")
class TestAuditRepositoryQuerying:
    """Tests for event querying."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_category(self) -> None:
        """GIVEN events WHEN queried by category THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured

        # Mock repository to return filtered events
        mock_events = [
            {
                "event_id": "evt-001",
                "category": "authentication",
                "event_type": "login.success",
            },
            {
                "event_id": "evt-002",
                "category": "authentication",
                "event_type": "login.failed",
            },
        ]
        mock_repo.query_events = AsyncMock(return_value=(mock_events, 2))

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events, count = await service.query_events(category="authentication")

        assert count == 2
        mock_repo.query_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_by_regulation(self) -> None:
        """GIVEN events WHEN queried by regulation THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured

        mock_events = [
            {
                "event_id": "evt-001",
                "regulation_tags": ["hipaa", "fedramp"],
            },
        ]
        mock_repo.query_events = AsyncMock(return_value=(mock_events, 1))

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events, count = await service.query_events(regulation="hipaa")

        assert count == 1
        mock_repo.query_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_by_time_range(self) -> None:
        """GIVEN events WHEN queried by time range THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_events = AsyncMock(return_value=([], 0))

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)

        events, count = await service.query_events(
            start_time=start,
            end_time=end,
        )

        mock_repo.query_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_pagination(self) -> None:
        """GIVEN many events WHEN paginated THEN correct page returned."""
        mock_repo = AsyncMock()  # async-mock-configured

        # Page 2 of results
        mock_events = [{"event_id": f"evt-{i}"} for i in range(10, 20)]
        mock_repo.query_events = AsyncMock(return_value=(mock_events, 100))

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        events, count = await service.query_events(page=2, page_size=10)

        assert count == 100
        assert len(events) == 10


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_repository")
class TestAuditRepositoryRetention:
    """Tests for retention policy enforcement."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_apply_retention_deletes_old_events(self) -> None:
        """GIVEN old events WHEN retention applied THEN deleted."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.delete_expired_by_regulation = AsyncMock(return_value=100)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        deleted = await service.apply_retention_policy(Regulation.GDPR)

        assert deleted == 100
        mock_repo.delete_expired_by_regulation.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_retention_status(self) -> None:
        """GIVEN events WHEN checking status THEN returns statistics."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.get_retention_status = AsyncMock(
            return_value={
                "gdpr": {"total": 1000, "expiring_soon": 50},
                "hipaa": {"total": 500, "expiring_soon": 10},
            }
        )

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        status = await service.get_retention_status()

        assert "gdpr" in status
        assert status["gdpr"]["total"] == 1000


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_repository")
class TestAuditRepositoryExport:
    """Tests for event export functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_export_to_json(self) -> None:
        """GIVEN events WHEN exported to JSON THEN valid JSON returned."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_events = [
            {
                "event_id": "evt-001",
                "category": "authentication",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]
        mock_repo.export_events = AsyncMock(return_value=mock_events)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC)

        json_output = await service.export_events(
            start_time=start,
            end_time=end,
        )

        assert len(json_output) == 1
        assert json_output[0]["event_id"] == "evt-001"

    @pytest.mark.asyncio
    async def test_export_to_csv(self) -> None:
        """GIVEN events WHEN exported to CSV THEN valid CSV returned."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_events = [
            {
                "event_id": "evt-001",
                "category": "authentication",
                "event_type": "login.success",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]
        mock_repo.export_events = AsyncMock(return_value=mock_events)

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC)

        csv_output = await service.export_events_csv(
            start_time=start,
            end_time=end,
        )

        assert "event_id" in csv_output
        assert "evt-001" in csv_output
