"""
Tests for SessionManagedAuditRepository.

TDD RED phase: These tests define expected behavior for the session-managed
wrapper that allows PostgresUnifiedAuditRepository to be used without
external session management.

The wrapper should:
- Create a new session for each operation
- Automatically commit/rollback on success/failure
- Close sessions after each operation
- Delegate all operations to the underlying PostgresUnifiedAuditRepository
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

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


def _create_test_event() -> UnifiedAuditEvent:
    """Create a test audit event."""
    return UnifiedAuditEvent(
        category=AuditEventCategory.AUTHENTICATION,
        event_type=AuditEventType.LOGIN_SUCCESS,
        actor=AuditActor(actor_id="user:alice", actor_type="user"),
        context=AuditContext(request_id="req-001"),
        resource_type="session",
        resource_id="sess-001",
        action="Login",
        outcome="success",
        regulation_tags=["gdpr", "soc2"],
    )


@pytest.mark.unit
@pytest.mark.xdist_group(name="session_managed_repo")
class TestSessionManagedAuditRepositoryCreate:
    """Tests for create operations with session management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_uses_session_context_manager(self) -> None:
        """
        GIVEN a SessionManagedAuditRepository
        WHEN create is called
        THEN it creates a new session and commits on success.
        """
        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        mock_session = AsyncMock()  # async-mock-configured
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        repo = SessionManagedAuditRepository(database_url="postgresql+asyncpg://test:test@localhost/test")

        event = _create_test_event()

        with patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            return_value=mock_session_maker,
        ):
            await repo.create(event)

        # Verify session was used
        mock_session_maker.return_value.__aenter__.assert_awaited()

    @pytest.mark.asyncio
    async def test_create_stores_event_in_database(self) -> None:
        """
        GIVEN a SessionManagedAuditRepository
        WHEN create is called
        THEN event is persisted via the session.
        """
        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        mock_session = AsyncMock()  # async-mock-configured
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        repo = SessionManagedAuditRepository(database_url="postgresql+asyncpg://test:test@localhost/test")

        event = _create_test_event()

        with patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            return_value=mock_session_maker,
        ):
            await repo.create(event)

        # Verify session.add was called
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_stores_all_events(self) -> None:
        """
        GIVEN a SessionManagedAuditRepository
        WHEN bulk_create is called with multiple events
        THEN all events are persisted.
        """
        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        mock_session = AsyncMock()  # async-mock-configured
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        repo = SessionManagedAuditRepository(database_url="postgresql+asyncpg://test:test@localhost/test")

        events = [_create_test_event() for _ in range(3)]

        with patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            return_value=mock_session_maker,
        ):
            await repo.bulk_create(events)

        # Verify session.add_all was called (bulk insert uses add_all)
        mock_session.add_all.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="session_managed_repo")
class TestSessionManagedAuditRepositoryQuery:
    """Tests for query operations with session management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_regulation_returns_events(self) -> None:
        """
        GIVEN events with regulation tags stored
        WHEN query_by_regulation is called
        THEN matching events are returned.
        """
        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()  # async-mock-configured
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        repo = SessionManagedAuditRepository(database_url="postgresql+asyncpg://test:test@localhost/test")

        with patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            return_value=mock_session_maker,
        ):
            result = await repo.query_by_regulation(Regulation.GDPR)

        assert isinstance(result, list)
        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_query_by_category_returns_events(self) -> None:
        """
        GIVEN events with categories stored
        WHEN query_by_category is called
        THEN matching events are returned.
        """
        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()  # async-mock-configured
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        repo = SessionManagedAuditRepository(database_url="postgresql+asyncpg://test:test@localhost/test")

        with patch(
            "mcp_server_langgraph.database.session.get_session_maker",
            return_value=mock_session_maker,
        ):
            result = await repo.query_by_category(AuditEventCategory.AUTHENTICATION)

        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.xdist_group(name="session_managed_repo")
class TestSessionManagedAuditRepositoryFactory:
    """Tests for factory function that creates the appropriate repository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_audit_repository_returns_session_managed_for_production(
        self,
    ) -> None:
        """
        GIVEN a database URL is configured
        WHEN create_audit_repository is called
        THEN SessionManagedAuditRepository is returned.
        """
        from mcp_server_langgraph.audit.repository import create_audit_repository

        repo = create_audit_repository(database_url="postgresql+asyncpg://test:test@localhost/test")

        from mcp_server_langgraph.audit.repository import (
            SessionManagedAuditRepository,
        )

        assert isinstance(repo, SessionManagedAuditRepository)

    def test_create_audit_repository_returns_inmemory_without_database(self) -> None:
        """
        GIVEN no database URL is configured
        WHEN create_audit_repository is called
        THEN InMemoryUnifiedAuditRepository is returned.
        """
        from mcp_server_langgraph.audit.repository import create_audit_repository

        repo = create_audit_repository(database_url=None)

        from mcp_server_langgraph.audit.repository import (
            InMemoryUnifiedAuditRepository,
        )

        assert isinstance(repo, InMemoryUnifiedAuditRepository)
