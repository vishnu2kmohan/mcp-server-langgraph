"""
E2E Tests for Agentic Memory API with Real Backends.

Tests the full API stack (HTTP -> FastAPI -> Manager -> Repository -> Postgres/Redis)
for notes, checkpoints, and agent state using the configured backends.

When NOTES_BACKEND=postgres, PHASE_CHECKPOINT_BACKEND=postgres, and
AGENT_STATE_BACKEND=redis are set (as in .env.test), these tests exercise
real database/Redis connections. Otherwise they fall back to in-memory backends.

Requires: docker-compose.test.yml infrastructure (make test-infra-up)

Uses httpx.AsyncClient with ASGITransport to keep all async operations
(SQLAlchemy, asyncpg, Redis) in the same event loop. This avoids the classic
"Future attached to a different loop" error that occurs with sync TestClient.

Test journeys:
1. Notes CRUD: Create -> List -> Get -> Search -> Delete
2. Checkpoints lifecycle: Create -> List -> Get latest -> Summarize
3. Cross-user isolation: Alice cannot see Bob's notes/checkpoints
4. Agent state with Redis: Save -> Get -> Checkpoint -> List sessions -> Delete
"""

from __future__ import annotations

import gc
import os
import socket
import time
import uuid
import warnings
from typing import Any, AsyncGenerator
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from tests.constants import (
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
    TEST_REDIS_PORT,
)

pytestmark = [pytest.mark.e2e, pytest.mark.memory]


# =============================================================================
# Infrastructure Checks
# =============================================================================


def _postgres_available() -> bool:
    """Check if test Postgres is reachable."""
    try:
        with socket.create_connection((TEST_POSTGRES_HOST, TEST_POSTGRES_PORT), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def _redis_available() -> bool:
    """Check if test Redis is reachable."""
    try:
        with socket.create_connection(("localhost", TEST_REDIS_PORT), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


@pytest.fixture(autouse=True)
def skip_if_e2e_infrastructure_unavailable():
    """Override conftest autouse: these tests only need Postgres/Redis, not Keycloak."""
    # Auth is mocked via dependency_overrides — no Keycloak needed


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags with agentic memory enabled."""
    mock_flags = MagicMock()
    mock_flags.enable_agentic_memory = True
    mock_flags.require_feature = MagicMock(return_value=None)
    return mock_flags


def _make_user(user_id: str, username: str) -> dict[str, Any]:
    """Create a mock user dict for auth override."""
    return {
        "sub": user_id,
        "user_id": user_id,
        "username": username,
        "roles": ["user"],
    }


@pytest.fixture
async def e2e_app(mock_feature_flags: MagicMock) -> AsyncGenerator[FastAPI, None]:
    """Create FastAPI app wired to real (or in-memory) backends.

    Uses the same backend selection as production: reads NOTES_BACKEND,
    PHASE_CHECKPOINT_BACKEND from settings to determine repository type.

    This fixture is async so that SQLAlchemy engine creation happens inside
    the same event loop used by httpx.AsyncClient (avoids loop mismatch).
    """
    from mcp_server_langgraph.api.v1 import memory as memory_module
    from mcp_server_langgraph.api.v1.memory import (
        memory_router,
        set_checkpoint_manager,
        set_notes_manager,
    )
    from mcp_server_langgraph.auth.dependencies import get_current_user
    from mcp_server_langgraph.memory.checkpoints import CheckpointManager
    from mcp_server_langgraph.memory.notes import NotesManager
    from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository
    from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1/memory")

    # Default user (alice) — tests can override per-request via app state
    alice = _make_user("user:alice-e2e", "alice")

    async def _override_current_user():
        return app.state.current_user if hasattr(app.state, "current_user") else alice

    app.dependency_overrides[get_current_user] = _override_current_user

    # Use Postgres repositories only when explicitly configured via env var
    # AND infrastructure is available (matches 12-factor: config from environment)
    notes_repo = None
    checkpoint_repo = None
    engine = None

    use_postgres = (
        os.environ.get("NOTES_BACKEND") == "postgres"
        and os.environ.get("PHASE_CHECKPOINT_BACKEND") == "postgres"
        and _postgres_available()
    )

    if use_postgres:
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

            import mcp_server_langgraph.repositories.postgres_models.agentic  # noqa: F401
            from mcp_server_langgraph.repositories.postgres_checkpoint import PostgresCheckpointRepository
            from mcp_server_langgraph.repositories.postgres_notes import PostgresNotesRepository

            database_url = (
                f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
                f"@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/compliance_test"
            )
            engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            notes_repo = PostgresNotesRepository(session_factory)
            checkpoint_repo = PostgresCheckpointRepository(session_factory)
        except ImportError:
            raise
        except Exception as exc:
            warnings.warn(
                f"Postgres backend setup failed, falling back to in-memory: {exc}",
                stacklevel=1,
            )

    if notes_repo is None:
        notes_repo = InMemoryNotesRepository()
    if checkpoint_repo is None:
        checkpoint_repo = InMemoryCheckpointRepository()

    with (
        patch("mcp_server_langgraph.core.feature_flags.feature_flags", mock_feature_flags),
        patch.object(memory_module, "feature_flags", mock_feature_flags),
    ):
        set_notes_manager(NotesManager(repository=notes_repo))
        set_checkpoint_manager(CheckpointManager(repository=checkpoint_repo))

        # Set default user
        app.state.current_user = alice

        yield app

        # Cleanup
        set_notes_manager(None)
        set_checkpoint_manager(None)
        if engine is not None:
            await engine.dispose()


@pytest.fixture
async def alice_client(e2e_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client authenticated as alice."""
    e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def bob_client(e2e_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client authenticated as bob."""
    e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Notes CRUD Journey
# =============================================================================


@pytest.mark.e2e
@pytest.mark.xdist_group(name="agentic_memory_e2e")
@pytest.mark.skip_isolation_check
class TestNotesE2EJourney:
    """E2E: Full notes lifecycle through the API."""

    def teardown_method(self) -> None:
        gc.collect()

    async def test_create_note_returns_201_with_user_ownership(self, alice_client: httpx.AsyncClient) -> None:
        """POST /notes creates a note owned by the authenticated user."""
        response = await alice_client.post(
            "/api/v1/memory/notes",
            json={
                "content": f"E2E test note {uuid.uuid4().hex[:8]}",
                "category": "research",
                "tags": ["e2e", "test"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"].startswith("E2E test note")
        assert data["category"] == "research"
        assert "id" in data

    async def test_notes_crud_lifecycle(self, alice_client: httpx.AsyncClient) -> None:
        """Full CRUD: create -> list -> get -> delete -> verify gone."""
        # Create
        create_resp = await alice_client.post(
            "/api/v1/memory/notes",
            json={
                "content": f"Lifecycle note {uuid.uuid4().hex[:8]}",
                "category": "analysis",
                "tags": ["lifecycle"],
            },
        )
        assert create_resp.status_code == 201
        note_id = create_resp.json()["id"]

        # List (should include our note)
        list_resp = await alice_client.get("/api/v1/memory/notes")
        assert list_resp.status_code == 200
        notes = list_resp.json()["notes"]
        assert any(n["id"] == note_id for n in notes)

        # Get by ID
        get_resp = await alice_client.get(f"/api/v1/memory/notes/{note_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == note_id

        # Delete
        del_resp = await alice_client.delete(f"/api/v1/memory/notes/{note_id}")
        assert del_resp.status_code == 204

        # Verify gone
        get_resp2 = await alice_client.get(f"/api/v1/memory/notes/{note_id}")
        assert get_resp2.status_code == 404

    async def test_list_notes_filters_by_category(self, alice_client: httpx.AsyncClient) -> None:
        """GET /notes?category=X returns only matching notes."""
        suffix = uuid.uuid4().hex[:8]

        await alice_client.post(
            "/api/v1/memory/notes",
            json={"content": f"Research {suffix}", "category": "research"},
        )
        await alice_client.post(
            "/api/v1/memory/notes",
            json={"content": f"Analysis {suffix}", "category": "analysis"},
        )

        resp = await alice_client.get("/api/v1/memory/notes", params={"category": "research"})
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert all(n["category"] == "research" for n in notes)

    async def test_search_notes_returns_matching_content(self, alice_client: httpx.AsyncClient) -> None:
        """GET /notes?query=X returns notes matching the search term."""
        unique = uuid.uuid4().hex[:8]
        await alice_client.post(
            "/api/v1/memory/notes",
            json={"content": f"quantum entanglement {unique}", "category": "research"},
        )

        resp = await alice_client.get("/api/v1/memory/notes", params={"query": unique})
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert len(notes) >= 1
        assert any(unique in n["content"] for n in notes)


# =============================================================================
# Checkpoints Lifecycle Journey
# =============================================================================


@pytest.mark.e2e
@pytest.mark.xdist_group(name="agentic_memory_e2e")
@pytest.mark.skip_isolation_check
class TestCheckpointsE2EJourney:
    """E2E: Full checkpoints lifecycle through the API."""

    def teardown_method(self) -> None:
        gc.collect()

    async def test_create_checkpoint_returns_201(self, alice_client: httpx.AsyncClient) -> None:
        """POST /checkpoint creates a checkpoint for the authenticated user."""
        response = await alice_client.post(
            "/api/v1/memory/checkpoint",
            json={
                "phase": "research",
                "summary": f"E2E checkpoint {uuid.uuid4().hex[:8]}",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phase"] == "research"
        assert "id" in data

    async def test_checkpoint_create_list_latest_summarize_lifecycle(self, alice_client: httpx.AsyncClient) -> None:
        """Create multiple checkpoints -> list -> get latest -> summarize."""
        # Create two checkpoints in sequence
        cp1 = await alice_client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "research", "summary": "Started research"},
        )
        assert cp1.status_code == 201

        time.sleep(0.05)  # Ensure ordering on loaded CI runners

        cp2 = await alice_client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "analysis", "summary": "Completed analysis"},
        )
        assert cp2.status_code == 201

        # List checkpoints
        list_resp = await alice_client.get("/api/v1/memory/checkpoint")
        assert list_resp.status_code == 200
        checkpoints = list_resp.json()["checkpoints"]
        assert len(checkpoints) >= 2

        # Get latest
        latest_resp = await alice_client.get("/api/v1/memory/checkpoint/latest")
        assert latest_resp.status_code == 200
        latest = latest_resp.json()
        assert latest["phase"] == "analysis"

        # Get summary
        summary_resp = await alice_client.get("/api/v1/memory/checkpoint/summary")
        assert summary_resp.status_code == 200
        assert "summary" in summary_resp.json()


# =============================================================================
# Cross-User Isolation
# =============================================================================


@pytest.mark.e2e
@pytest.mark.xdist_group(name="agentic_memory_e2e")
@pytest.mark.skip_isolation_check
class TestCrossUserIsolationE2E:
    """E2E: Verify users cannot access each other's notes/checkpoints."""

    def teardown_method(self) -> None:
        gc.collect()

    async def test_alice_cannot_see_bobs_notes(
        self,
        alice_client: httpx.AsyncClient,
        bob_client: httpx.AsyncClient,
        e2e_app: FastAPI,
    ) -> None:
        """Alice's note listing should not include Bob's notes."""
        suffix = uuid.uuid4().hex[:8]

        # Bob creates a note (explicitly set identity before call)
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_resp = await bob_client.post(
            "/api/v1/memory/notes",
            json={"content": f"Bob secret {suffix}", "category": "private"},
        )
        assert bob_resp.status_code == 201
        bob_note_id = bob_resp.json()["id"]

        # Alice lists her notes — Bob's note should not appear
        e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
        alice_list = await alice_client.get("/api/v1/memory/notes")
        assert alice_list.status_code == 200
        alice_note_ids = [n["id"] for n in alice_list.json()["notes"]]
        assert bob_note_id not in alice_note_ids

    async def test_alice_cannot_get_bobs_note_by_id(
        self,
        alice_client: httpx.AsyncClient,
        bob_client: httpx.AsyncClient,
        e2e_app: FastAPI,
    ) -> None:
        """Alice cannot retrieve Bob's note by ID (IDOR protection)."""
        suffix = uuid.uuid4().hex[:8]

        # Bob creates a note (explicitly set identity before call)
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_resp = await bob_client.post(
            "/api/v1/memory/notes",
            json={"content": f"Bob private {suffix}", "category": "secret"},
        )
        assert bob_resp.status_code == 201
        bob_note_id = bob_resp.json()["id"]

        # Alice tries to get Bob's note by ID
        e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
        alice_get = await alice_client.get(f"/api/v1/memory/notes/{bob_note_id}")
        assert alice_get.status_code == 404

    async def test_alice_cannot_delete_bobs_note(
        self,
        alice_client: httpx.AsyncClient,
        bob_client: httpx.AsyncClient,
        e2e_app: FastAPI,
    ) -> None:
        """Alice cannot delete Bob's note (IDOR protection)."""
        suffix = uuid.uuid4().hex[:8]

        # Bob creates a note (explicitly set identity before call)
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_resp = await bob_client.post(
            "/api/v1/memory/notes",
            json={"content": f"Bob undeletable {suffix}", "category": "secure"},
        )
        assert bob_resp.status_code == 201
        bob_note_id = bob_resp.json()["id"]

        # Alice tries to delete Bob's note
        e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
        alice_del = await alice_client.delete(f"/api/v1/memory/notes/{bob_note_id}")
        assert alice_del.status_code == 404

        # Verify Bob's note still exists
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_get = await bob_client.get(f"/api/v1/memory/notes/{bob_note_id}")
        assert bob_get.status_code == 200

    async def test_alice_cannot_see_bobs_checkpoints(
        self,
        alice_client: httpx.AsyncClient,
        bob_client: httpx.AsyncClient,
        e2e_app: FastAPI,
    ) -> None:
        """Alice's checkpoint listing should not include Bob's checkpoints."""
        # Bob creates a checkpoint (explicitly set identity before call)
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_resp = await bob_client.post(
            "/api/v1/memory/checkpoint",
            json={"phase": "bob-only", "summary": "Bob's secret checkpoint"},
        )
        assert bob_resp.status_code == 201

        # Alice lists checkpoints — Bob's should not appear
        e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
        alice_list = await alice_client.get("/api/v1/memory/checkpoint")
        assert alice_list.status_code == 200
        phases = [c["phase"] for c in alice_list.json()["checkpoints"]]
        assert "bob-only" not in phases

    async def test_alice_search_does_not_return_bobs_notes(
        self,
        alice_client: httpx.AsyncClient,
        bob_client: httpx.AsyncClient,
        e2e_app: FastAPI,
    ) -> None:
        """Alice's search should not return Bob's notes (IDOR via search)."""
        unique = uuid.uuid4().hex[:8]

        # Bob creates a note with unique content
        e2e_app.state.current_user = _make_user("user:bob-e2e", "bob")
        bob_resp = await bob_client.post(
            "/api/v1/memory/notes",
            json={"content": f"bob-secret-{unique}", "category": "private"},
        )
        assert bob_resp.status_code == 201

        # Alice searches for that unique content
        e2e_app.state.current_user = _make_user("user:alice-e2e", "alice")
        resp = await alice_client.get("/api/v1/memory/notes", params={"query": unique})
        assert resp.status_code == 200
        assert len(resp.json()["notes"]) == 0


# =============================================================================
# Agent State with Redis
# =============================================================================


@pytest.mark.e2e
@pytest.mark.xdist_group(name="agentic_memory_e2e")
@pytest.mark.skip_isolation_check
class TestAgentStateE2E:
    """E2E: Agent state persistence via AgentStateRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    async def agent_state_repo(self):
        """Get agent state repository (Redis if configured, else in-memory)."""
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository

        use_redis = os.environ.get("AGENT_STATE_BACKEND") == "redis" and _redis_available()
        repo = None
        redis_client = None

        if use_redis:
            try:
                import redis.asyncio as aioredis

                from mcp_server_langgraph.repositories.redis_agent_state import RedisAgentStateRepository

                redis_client = aioredis.Redis(host="localhost", port=TEST_REDIS_PORT, db=3)
                repo = RedisAgentStateRepository(redis_client, session_ttl_seconds=60)
            except ImportError:
                raise
            except Exception as exc:
                warnings.warn(
                    f"Redis backend setup failed, falling back to in-memory: {exc}",
                    stacklevel=1,
                )

        if repo is None:
            repo = InMemoryAgentStateRepository()

        # yield outside try/except so test AssertionErrors propagate correctly
        yield repo

        if redis_client is not None:
            await redis_client.aclose()

    async def test_agent_state_save_and_get(self, agent_state_repo) -> None:
        """Save agent state and retrieve it."""
        session_id = f"e2e-session-{uuid.uuid4().hex[:8]}"
        state = {"last_query": "test query", "response_count": 1}

        await agent_state_repo.save(session_id, state)
        retrieved = await agent_state_repo.get(session_id)

        assert retrieved is not None
        assert retrieved["last_query"] == "test query"

        # Cleanup
        await agent_state_repo.delete(session_id)

    async def test_agent_state_checkpoint_and_list(self, agent_state_repo) -> None:
        """Checkpoint a session and list active sessions."""
        session_id = f"e2e-session-{uuid.uuid4().hex[:8]}"
        await agent_state_repo.save(session_id, {"status": "active"})

        await agent_state_repo.checkpoint(session_id, "research", "Did research")

        state = await agent_state_repo.get(session_id)
        assert state is not None
        assert len(state["checkpoints"]) == 1
        assert state["checkpoints"][0]["phase"] == "research"

        sessions = await agent_state_repo.list_sessions()
        assert session_id in sessions

        # Cleanup
        await agent_state_repo.delete(session_id)

    async def test_agent_state_delete_removes_session(self, agent_state_repo) -> None:
        """Deleting a session removes it from storage and index."""
        session_id = f"e2e-session-{uuid.uuid4().hex[:8]}"
        await agent_state_repo.save(session_id, {"temp": True})

        await agent_state_repo.delete(session_id)

        assert await agent_state_repo.get(session_id) is None
        sessions = await agent_state_repo.list_sessions()
        assert session_id not in sessions
