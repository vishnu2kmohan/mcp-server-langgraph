"""
Integration tests for Postgres-backed session management.

Tests the session manager against real PostgreSQL infrastructure:
- Session CRUD operations with real Postgres
- Message history persistence
- Multi-user session isolation
- Complex query support (search, pagination)

Requires: PostgreSQL running at TEST_POSTGRES_URL or docker-compose.test.yml

Run with:
    make test-infra-up
    pytest tests/integration/playground/test_playground_postgres_session.py -v
"""

import asyncio
import gc
import uuid

import pytest

from tests.constants import (
    TEST_POSTGRES_DB,
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.playground,
    pytest.mark.postgres,
    pytest.mark.xdist_group(name="playground_postgres_integration_tests"),
]


@pytest.fixture
def postgres_url() -> str:
    """Get PostgreSQL URL for playground sessions."""
    return f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{TEST_POSTGRES_DB}"


@pytest.fixture
async def postgres_engine(postgres_url: str):
    """Create async SQLAlchemy engine for testing."""
    from mcp_server_langgraph.playground.session.postgres_manager import (
        create_postgres_engine,
        init_playground_database,
    )

    try:
        engine = await create_postgres_engine(postgres_url, echo=False)
        await init_playground_database(engine)
    except OSError as e:
        pytest.skip(f"PostgreSQL infrastructure not available: {e}")
    except Exception as e:
        # Catch other connection-related errors
        error_msg = str(e)
        if any(pattern in error_msg for pattern in ["Connect call failed", "Connection refused", "Network is unreachable"]):
            pytest.skip(f"PostgreSQL infrastructure not available: {e}")
        raise
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_manager(postgres_engine):
    """Create session manager with real Postgres."""
    from mcp_server_langgraph.playground.session.postgres_manager import PostgresSessionManager

    manager = PostgresSessionManager(engine=postgres_engine)
    yield manager
    await manager.close()


@pytest.mark.xdist_group(name="playground_postgres_integration_tests")
class TestPostgresSessionIntegration:
    """Integration tests for Postgres session storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_session_persists_to_postgres(self, session_manager) -> None:
        """Test that created sessions are actually stored in Postgres."""
        session = await session_manager.create_session(
            name="Integration Test Session",
            user_id="alice",
        )

        assert session is not None
        assert session.session_id is not None
        assert session.name == "Integration Test Session"
        assert session.user_id == "alice"

        # Verify session can be retrieved
        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_session_retrieves_from_postgres(self, session_manager) -> None:
        """Test retrieving a session from Postgres."""
        created = await session_manager.create_session(
            name="Retrieve Test",
            user_id="bob",
        )

        retrieved = await session_manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.name == "Retrieve Test"
        assert retrieved.user_id == "bob"

    @pytest.mark.asyncio
    async def test_update_session_persists_changes(self, session_manager) -> None:
        """Test updating a session updates the database."""
        session = await session_manager.create_session(
            name="Update Test",
            user_id="charlie",
        )

        updated = await session_manager.update_session(
            session_id=session.session_id,
            name="Updated Name",
        )

        assert updated is not None
        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_add_message_updates_session(self, session_manager) -> None:
        """Test adding messages to session history."""
        session = await session_manager.create_session(
            name="Message Test",
            user_id="dave",
        )

        # Add a message
        message = await session_manager.add_message(
            session_id=session.session_id,
            role="user",
            content="Hello, world!",
            metadata={"source": "integration_test"},
        )

        assert message is not None
        assert message.role == "user"
        assert message.content == "Hello, world!"

        # Verify message persisted
        retrieved = await session_manager.get_session(session.session_id)
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_postgres(self, session_manager) -> None:
        """Test that deleted sessions are removed from Postgres."""
        session = await session_manager.create_session(
            name="Delete Test",
            user_id="eve",
        )

        result = await session_manager.delete_session(session.session_id)

        assert result is True

        # Verify session is gone
        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_sessions_for_user(self, session_manager) -> None:
        """Test listing sessions scoped to a user."""
        user_id = f"user-{uuid.uuid4()}"

        # Create multiple sessions for the user
        session1 = await session_manager.create_session(name="Session 1", user_id=user_id)
        session2 = await session_manager.create_session(name="Session 2", user_id=user_id)
        session3 = await session_manager.create_session(name="Session 3", user_id=user_id)

        # Create session for different user
        await session_manager.create_session(name="Other User", user_id="other")

        sessions = await session_manager.list_sessions(user_id=user_id)

        assert len(sessions) >= 3
        session_ids = {s.session_id for s in sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_manager) -> None:
        """Test concurrent session operations don't interfere."""
        user_id = f"concurrent-{uuid.uuid4()}"

        # Create sessions concurrently
        tasks = [session_manager.create_session(name=f"Concurrent {i}", user_id=user_id) for i in range(5)]
        sessions = await asyncio.gather(*tasks)

        assert len(sessions) == 5
        assert len({s.session_id for s in sessions}) == 5  # All unique IDs

    @pytest.mark.asyncio
    async def test_message_order_preserved(self, session_manager) -> None:
        """Test that message order is preserved in session history."""
        session = await session_manager.create_session(
            name="Order Test",
            user_id="grace",
        )

        # Add messages in order
        for i in range(5):
            await session_manager.add_message(
                session_id=session.session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        retrieved = await session_manager.get_session(session.session_id)

        assert len(retrieved.messages) == 5
        for i, msg in enumerate(retrieved.messages):
            assert msg.content == f"Message {i}"

    @pytest.mark.asyncio
    async def test_search_sessions_by_name(self, session_manager) -> None:
        """Test searching sessions by name (Postgres-specific feature)."""
        user_id = f"search-{uuid.uuid4()}"

        await session_manager.create_session(name="Alpha Project", user_id=user_id)
        await session_manager.create_session(name="Beta Project", user_id=user_id)
        await session_manager.create_session(name="Gamma Test", user_id=user_id)

        # Search for sessions containing "Project"
        sessions = await session_manager.list_sessions(user_id=user_id, search="Project")

        assert len(sessions) >= 2
        names = {s.name for s in sessions}
        assert "Alpha Project" in names
        assert "Beta Project" in names

    @pytest.mark.asyncio
    async def test_pagination_support(self, session_manager) -> None:
        """Test pagination of session listing (Postgres-specific feature)."""
        user_id = f"pagination-{uuid.uuid4()}"

        # Create 10 sessions
        for i in range(10):
            await session_manager.create_session(name=f"Page Test {i}", user_id=user_id)

        # Get first page
        page1 = await session_manager.list_sessions(user_id=user_id, limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = await session_manager.list_sessions(user_id=user_id, limit=3, offset=3)
        assert len(page2) == 3

        # Pages should have different sessions
        page1_ids = {s.session_id for s in page1}
        page2_ids = {s.session_id for s in page2}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.xdist_group(name="playground_postgres_integration_tests")
class TestPostgresConnectionResilience:
    """Test Postgres connection handling and error cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handles_nonexistent_session(self, session_manager) -> None:
        """Test graceful handling of nonexistent sessions."""
        result = await session_manager.get_session("nonexistent-session-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_false(self, session_manager) -> None:
        """Test deleting nonexistent session returns False."""
        result = await session_manager.delete_session("nonexistent-session-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_session_returns_none(self, session_manager) -> None:
        """Test adding message to nonexistent session."""
        result = await session_manager.add_message(
            session_id="nonexistent-session-id",
            role="user",
            content="Test",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_session_returns_none(self, session_manager) -> None:
        """Test updating nonexistent session returns None."""
        result = await session_manager.update_session(
            session_id="nonexistent-session-id",
            name="New Name",
        )
        assert result is None
