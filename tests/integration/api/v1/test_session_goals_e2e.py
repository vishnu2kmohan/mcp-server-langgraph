"""
E2E Tests for Session Goals Flow.

Tests the complete flow: API → Repository → Database → Response.
Uses PostgreSQL test database (skips if unavailable).
"""

import os
import socket
import pytest
from typing import AsyncGenerator
from unittest.mock import MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.models.session_goal import SessionGoalBase
from mcp_server_langgraph.repositories.session_goal import PostgresSessionGoalRepository

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _database_available() -> bool:
    """Check if the test database is available."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "9432"))

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for the module."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_engine():
    """Create a test database engine."""
    if not _database_available():
        pytest.skip("PostgreSQL not available for integration tests")

    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:9432/agent_studio_test",
    )

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    try:
        # Test connection and create tables
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            # Create session_goals table if not exists
            await conn.run_sync(SessionGoalBase.metadata.create_all)
    except Exception as e:
        pytest.skip(f"Could not connect to test database: {e}")

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing."""
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        # Clear any existing test data
        await session.execute(text("DELETE FROM session_goals WHERE session_id LIKE 'session-e2e-test%'"))
        await session.commit()

        yield session

        # Cleanup after test
        await session.execute(text("DELETE FROM session_goals WHERE session_id LIKE 'session-e2e-test%'"))
        await session.commit()


@pytest.fixture
def mock_current_user() -> dict:
    """Mock authenticated user."""
    return {
        "sub": "e2e-test-user",
        "preferred_username": "e2euser",
        "email": "e2e@example.com",
    }


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Mock session service that always returns valid session."""
    from unittest.mock import AsyncMock

    service = MagicMock()
    service.get_session = AsyncMock(
        return_value={
            "id": "session-e2e-test",
            "name": "E2E Test Session",
            "user_id": "e2e-test-user",
            "messages": [],
        }
    )
    return service


@pytest.fixture
def app(
    mock_current_user: dict,
    mock_session_service: MagicMock,
    async_session: AsyncSession,
) -> FastAPI:
    """Create FastAPI app with real database session."""
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.api.v1 import sessions as sessions_module
    from mcp_server_langgraph.core.dependencies import get_session_goal_repository

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    # Use real repository with test database session
    def get_test_repository():
        return PostgresSessionGoalRepository(async_session)

    app.dependency_overrides[get_session_goal_repository] = get_test_repository

    # Set mock session service
    sessions_module.set_session_service(mock_session_service)

    yield app

    # Cleanup
    sessions_module._session_service = None


@pytest.mark.integration
class TestSessionGoalsE2EFlow:
    """E2E tests for the complete session goals flow."""

    @pytest.mark.asyncio
    async def test_create_goal_and_retrieve_history(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test creating a goal and retrieving it from history."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Create a goal
            create_response = await client.post(
                "/api/v1/sessions/session-e2e-test/goal",
                json={
                    "goal": "Complete E2E test analysis",
                    "set_at": 1705123456789,
                },
            )

            assert create_response.status_code == 201
            create_data = create_response.json()
            assert create_data["goal"] == "Complete E2E test analysis"
            assert create_data["set_at"] == 1705123456789

            # Commit to ensure data is persisted
            await async_session.commit()

            # Step 2: Retrieve goal history
            history_response = await client.get("/api/v1/sessions/session-e2e-test/goals")

            assert history_response.status_code == 200
            history_data = history_response.json()
            assert history_data["total"] == 1
            assert len(history_data["goals"]) == 1
            assert history_data["goals"][0]["goal"] == "Complete E2E test analysis"

    @pytest.mark.asyncio
    async def test_create_and_complete_goal(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test creating and completing a goal."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Create a goal
            await client.post(
                "/api/v1/sessions/session-e2e-test/goal",
                json={
                    "goal": "Implement feature X",
                    "set_at": 1705100000000,
                },
            )
            await async_session.commit()

            # Step 2: Complete the goal
            complete_response = await client.post(
                "/api/v1/sessions/session-e2e-test/goal/complete",
                json={
                    "goal": "Implement feature X",
                    "achieved": True,
                    "feedback": "Completed successfully",
                    "completed_at": 1705110000000,
                },
            )

            assert complete_response.status_code == 200
            complete_data = complete_response.json()
            assert complete_data["achieved"] is True
            assert complete_data["feedback"] == "Completed successfully"
            assert complete_data["set_at"] == 1705100000000
            assert complete_data["completed_at"] == 1705110000000

            await async_session.commit()

            # Step 3: Verify in history
            history_response = await client.get("/api/v1/sessions/session-e2e-test/goals")

            history_data = history_response.json()
            goal = history_data["goals"][0]
            assert goal["achieved"] is True
            assert goal["completed_at"] == 1705110000000

    @pytest.mark.asyncio
    async def test_partial_achievement(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test completing a goal with partial achievement."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create and complete with partial achievement
            await client.post(
                "/api/v1/sessions/session-e2e-test/goal",
                json={
                    "goal": "Complete 80% of work",
                    "set_at": 1705100000000,
                },
            )
            await async_session.commit()

            complete_response = await client.post(
                "/api/v1/sessions/session-e2e-test/goal/complete",
                json={
                    "goal": "Complete 80% of work",
                    "achieved": "partial",
                    "feedback": "Got 80% done",
                    "completed_at": 1705110000000,
                },
            )

            assert complete_response.status_code == 200
            data = complete_response.json()
            assert data["achieved"] == "partial"

    @pytest.mark.asyncio
    async def test_multiple_goals_ordering(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test that goals are ordered by set_at descending (newest first)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create multiple goals with different timestamps
            for i, ts in enumerate([1705100000000, 1705200000000, 1705150000000]):
                await client.post(
                    "/api/v1/sessions/session-e2e-test/goal",
                    json={
                        "goal": f"Goal {i}",
                        "set_at": ts,
                    },
                )

            await async_session.commit()

            # Retrieve history
            history_response = await client.get("/api/v1/sessions/session-e2e-test/goals")

            history_data = history_response.json()
            assert len(history_data["goals"]) == 3

            # Should be ordered by set_at descending
            timestamps = [g["set_at"] for g in history_data["goals"]]
            assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test pagination with limit and offset."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create 5 goals
            for i in range(5):
                await client.post(
                    "/api/v1/sessions/session-e2e-test/goal",
                    json={
                        "goal": f"Goal {i}",
                        "set_at": 1705100000000 + (i * 1000),
                    },
                )

            await async_session.commit()

            # Get first 2 goals
            response1 = await client.get("/api/v1/sessions/session-e2e-test/goals?limit=2&offset=0")
            data1 = response1.json()
            assert len(data1["goals"]) == 2

            # Get next 2 goals
            response2 = await client.get("/api/v1/sessions/session-e2e-test/goals?limit=2&offset=2")
            data2 = response2.json()
            assert len(data2["goals"]) == 2

            # Verify different goals
            ids1 = {g["id"] for g in data1["goals"]}
            ids2 = {g["id"] for g in data2["goals"]}
            assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_goal_not_achieved(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Test completing a goal with achieved=false."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/sessions/session-e2e-test/goal",
                json={
                    "goal": "Blocked task",
                    "set_at": 1705100000000,
                },
            )
            await async_session.commit()

            complete_response = await client.post(
                "/api/v1/sessions/session-e2e-test/goal/complete",
                json={
                    "goal": "Blocked task",
                    "achieved": False,
                    "feedback": "Blocked by external dependency",
                    "completed_at": 1705110000000,
                },
            )

            assert complete_response.status_code == 200
            data = complete_response.json()
            assert data["achieved"] is False
            assert data["feedback"] == "Blocked by external dependency"

    @pytest.mark.asyncio
    async def test_database_persistence(
        self,
        app: FastAPI,
        async_session: AsyncSession,
    ) -> None:
        """Verify data is actually persisted in database."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/sessions/session-e2e-test/goal",
                json={
                    "goal": "Persistence test",
                    "set_at": 1705123456789,
                },
            )
            await async_session.commit()

        # Query database directly
        result = await async_session.execute(text("SELECT * FROM session_goals WHERE goal = 'Persistence test'"))
        row = result.fetchone()

        assert row is not None
        assert row.session_id == "session-e2e-test"
        assert row.user_id == "e2e-test-user"
        assert row.goal == "Persistence test"
        assert row.set_at == 1705123456789
