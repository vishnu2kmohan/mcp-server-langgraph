"""
Tests for PostgreSQL UnifiedAuditRepository.

TDD RED phase: These tests define expected behavior for the PostgreSQL
implementation of the unified audit repository.

The repository should:
- Store UnifiedAuditEvent records with all fields
- Query events by regulation, category, and actor
- Support time range queries for integrity verification
- Handle sequence numbers for hash chain
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.audit.constants import Regulation
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="postgres_audit_repo")
class TestPostgresUnifiedAuditRepositoryCreate:
    """Tests for create operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stores_event(self) -> None:
        """
        GIVEN a valid UnifiedAuditEvent
        WHEN create is called
        THEN event is stored in database.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        # Create mock session
        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock(return_value=None)  # async-mock-configured

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(
                actor_id="user:alice",
                actor_type="user",
                username="alice",
            ),
            resource_type="session",
            resource_id="sess-12345",
            action="User logged in",
            outcome="success",
            context=AuditContext(
                request_id="req-abc123",
                ip_address="192.168.1.100",
            ),
            regulation_tags=["SOC2", "GDPR"],
        )

        await repo.create(event)

        # Verify session.add was called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_stores_multiple_events(self) -> None:
        """
        GIVEN multiple UnifiedAuditEvents
        WHEN bulk_create is called
        THEN all events are stored.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_session.add_all = MagicMock()
        mock_session.flush = AsyncMock(return_value=None)  # async-mock-configured

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        events = [
            UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:bob", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read document",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            for i in range(5)
        ]

        await repo.bulk_create(events)

        # Verify add_all was called with 5 items
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="postgres_audit_repo")
class TestPostgresUnifiedAuditRepositoryQuery:
    """Tests for query operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_regulation(self) -> None:
        """
        GIVEN events with regulation tags
        WHEN query_by_regulation is called
        THEN returns only matching events.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        results = await repo.query_by_regulation(
            regulation=Regulation.GDPR,
            start_time=datetime.now(UTC) - timedelta(days=7),
            end_time=datetime.now(UTC),
        )

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_by_category(self) -> None:
        """
        GIVEN events with different categories
        WHEN query_by_category is called
        THEN returns only matching category.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        results = await repo.query_by_category(
            category=AuditEventCategory.AI_OPERATION,
        )

        mock_session.execute.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_by_actor(self) -> None:
        """
        GIVEN events from different actors
        WHEN query_by_actor is called
        THEN returns only matching actor's events.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        results = await repo.query_by_actor(
            actor_id="user:alice",
            start_time=datetime.now(UTC) - timedelta(hours=1),
        )

        mock_session.execute.assert_called_once()
        assert isinstance(results, list)


@pytest.mark.unit
@pytest.mark.xdist_group(name="postgres_audit_repo")
class TestPostgresUnifiedAuditRepositoryIntegrity:
    """Tests for integrity verification operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_events_in_range(self) -> None:
        """
        GIVEN events in a time range
        WHEN get_events_in_range is called
        THEN returns events ordered by sequence_number.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        results = await repo.get_events_in_range(
            start_time=datetime.now(UTC) - timedelta(hours=24),
            end_time=datetime.now(UTC),
        )

        mock_session.execute.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_latest_sequence_number(self) -> None:
        """
        GIVEN events with sequence numbers
        WHEN get_latest_sequence_number is called
        THEN returns the highest sequence number.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        seq = await repo.get_latest_sequence_number()

        mock_session.execute.assert_called_once()
        assert seq == 42

    @pytest.mark.asyncio
    async def test_get_latest_sequence_number_empty_table(self) -> None:
        """
        GIVEN no events in database
        WHEN get_latest_sequence_number is called
        THEN returns 0.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        seq = await repo.get_latest_sequence_number()

        assert seq == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="postgres_audit_repo")
class TestPostgresUnifiedAuditRepositoryCount:
    """Tests for count operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_event_count(self) -> None:
        """
        GIVEN events in database
        WHEN get_event_count is called
        THEN returns correct count.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        count = await repo.get_event_count()

        mock_session.execute.assert_called_once()
        assert count == 100

    @pytest.mark.asyncio
    async def test_get_event_count_with_time_range(self) -> None:
        """
        GIVEN events in database
        WHEN get_event_count is called with time range
        THEN returns count for that range only.
        """
        from mcp_server_langgraph.audit.repository import (
            PostgresUnifiedAuditRepository,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalar.return_value = 25
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PostgresUnifiedAuditRepository(session=mock_session)

        count = await repo.get_event_count(
            start_time=datetime.now(UTC) - timedelta(hours=1),
            end_time=datetime.now(UTC),
        )

        mock_session.execute.assert_called_once()
        assert count == 25
