"""
Integration Tests for MCP Connections Repository

TDD integration tests for PostgresConnectionRepository with real PostgreSQL.
Tests CRUD operations, filtering, sorting, pagination, and OAuth2 state management.

Follows memory safety patterns for pytest-xdist.
Uses SQLAlchemy async sessions with test database.
"""

import asyncio
import gc
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mcp_server_langgraph.core.secrets import InMemorySecretsProvider
from mcp_server_langgraph.models.project import ProjectModel
from mcp_server_langgraph.repositories.connections import PostgresConnectionRepository
from mcp_server_langgraph.storage.models import (
    MCPConnectionCreate,
    MCPConnectionUpdate,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Test Fixtures
# ============================================================================


def _database_available() -> bool:
    """Check if the test database is available."""
    import socket

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "9432"))

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="module")
async def test_engine():
    """Create a test database engine."""
    if not _database_available():
        pytest.skip("PostgreSQL not available for integration tests")

    # Use test database URL from environment or default
    # Database name is agent_studio_test (managed by Alembic migrations)
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:9432/agent_studio_test",
    )

    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    yield engine

    await engine.dispose()


@pytest.fixture(scope="module")
async def setup_database(test_engine):
    """
    Verify mcp_connections table exists (Alembic-managed schema).

    Schema is created by Alembic migrations (docker-compose.test.yml alembic-migrate-test).
    This fixture validates the table exists rather than creating it, avoiding
    xdist collisions with Base.metadata.create_all().
    """
    async with test_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mcp_connections')")
        )
        if not result.scalar():
            pytest.skip("mcp_connections table not found — run Alembic migrations first")

    return


@pytest.fixture
async def session(test_engine, setup_database):
    """Create a database session for each test."""
    session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with session_maker() as session:
        yield session
        # Rollback to ensure clean state
        await session.rollback()


@pytest.fixture
def secrets_provider():
    """Create an in-memory secrets provider for testing."""
    return InMemorySecretsProvider()


@pytest.fixture
def repo(session, secrets_provider):
    """Create a repository instance for testing."""
    return PostgresConnectionRepository(session, secrets_provider)


@pytest.fixture
async def sample_connection(session, secrets_provider):
    """Create a sample connection for testing."""
    repo = PostgresConnectionRepository(session, secrets_provider)

    connection = await repo.create(
        MCPConnectionCreate(
            name="Test MCP Server",
            description="A test MCP server for integration testing",
            url="https://mcp.example.com",
            auth_type="none",
        ),
        owner_id="test-user-123",
    )

    await session.commit()
    return connection


@pytest.fixture
async def test_project(session):
    """Create a test project for FK reference testing."""
    project_id = str(uuid4())
    project = ProjectModel(
        id=project_id,
        name="Test Project",
        description="A test project for integration testing",
        owner_id="test-user-123",
        status="active",
    )
    session.add(project)
    await session.commit()
    return project


# ============================================================================
# CRUD Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionCreate:
    """Tests for creating connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_create_connection_no_auth(self, repo, session):
        """Should create a connection without authentication."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="No Auth Server",
                description="A server without authentication",
                url="https://no-auth.example.com",
                auth_type="none",
            ),
            owner_id="user-1",
        )
        await session.commit()

        assert connection.id is not None
        assert connection.name == "No Auth Server"
        assert connection.url == "https://no-auth.example.com"
        assert connection.auth_type == "none"
        assert connection.status == "disconnected"
        assert connection.owner_id == "user-1"
        assert connection.created_at is not None

    async def test_create_connection_with_api_key(self, repo, session, secrets_provider):
        """Should create a connection with API key and store secret."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="API Key Server",
                url="https://api-key.example.com",
                auth_type="api_key",
                api_key="super-secret-key-123",
            ),
            owner_id="user-2",
        )
        await session.commit()

        assert connection.auth_type == "api_key"

        # Verify API key was stored in secrets provider
        stored_key = await repo.get_api_key(connection.id)
        assert stored_key == "super-secret-key-123"

    async def test_create_connection_with_oauth2(self, repo, session):
        """Should create a connection with OAuth2 configuration."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="OAuth2 Server",
                url="https://oauth2.example.com",
                auth_type="oauth2",
                oauth2_client_id="client-abc-123",
                oauth2_scopes=["read", "write", "admin"],
            ),
            owner_id="user-3",
        )
        await session.commit()

        assert connection.auth_type == "oauth2"
        assert connection.oauth2_config is not None
        assert connection.oauth2_config.client_id == "client-abc-123"
        assert connection.oauth2_config.scopes == ["read", "write", "admin"]

    async def test_create_connection_with_project(self, repo, session, test_project):
        """Should create a connection associated with a project."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="Project Server",
                url="https://project.example.com",
                auth_type="none",
                project_id=test_project.id,
            ),
            owner_id="user-4",
        )
        await session.commit()

        assert connection.project_id == test_project.id


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionGet:
    """Tests for retrieving connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_get_existing_connection(self, repo, sample_connection, session):
        """Should retrieve an existing connection by ID."""
        connection = await repo.get(sample_connection.id)

        assert connection is not None
        assert connection.id == sample_connection.id
        assert connection.name == sample_connection.name

    async def test_get_nonexistent_connection(self, repo, session):
        """Should return None for nonexistent connection."""
        connection = await repo.get(str(uuid4()))

        assert connection is None


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionUpdate:
    """Tests for updating connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_update_connection_name(self, repo, sample_connection, session):
        """Should update connection name."""
        updated = await repo.update(
            sample_connection.id,
            MCPConnectionUpdate(name="Updated Server Name"),
        )
        await session.commit()

        assert updated is not None
        assert updated.name == "Updated Server Name"
        assert updated.updated_at > sample_connection.updated_at

    async def test_update_connection_description(self, repo, sample_connection, session):
        """Should update connection description."""
        updated = await repo.update(
            sample_connection.id,
            MCPConnectionUpdate(description="New description for the server"),
        )
        await session.commit()

        assert updated is not None
        assert updated.description == "New description for the server"

    async def test_update_connection_url(self, repo, sample_connection, session):
        """Should update connection URL."""
        updated = await repo.update(
            sample_connection.id,
            MCPConnectionUpdate(url="https://new-url.example.com"),
        )
        await session.commit()

        assert updated is not None
        assert updated.url == "https://new-url.example.com"

    async def test_update_nonexistent_connection(self, repo, session):
        """Should return None for nonexistent connection."""
        updated = await repo.update(
            str(uuid4()),
            MCPConnectionUpdate(name="Ghost Server"),
        )

        assert updated is None


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionDelete:
    """Tests for deleting connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_delete_connection(self, repo, session, secrets_provider):
        """Should delete a connection."""
        # Create a connection first
        connection = await repo.create(
            MCPConnectionCreate(
                name="To Delete",
                url="https://delete-me.example.com",
                auth_type="api_key",
                api_key="delete-this-key",
            ),
            owner_id="user-delete",
        )
        await session.commit()

        # Delete it
        deleted = await repo.delete(connection.id)
        await session.commit()

        assert deleted is True

        # Verify it's gone
        retrieved = await repo.get(connection.id)
        assert retrieved is None

        # Verify secrets are deleted
        stored_key = await secrets_provider.get_secret(f"mcp_conn_{connection.id}_api_key")
        assert stored_key is None

    async def test_delete_nonexistent_connection(self, repo, session):
        """Should return False for nonexistent connection."""
        deleted = await repo.delete(str(uuid4()))

        assert deleted is False


# ============================================================================
# List and Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionList:
    """Tests for listing connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_list_empty(self, repo, session):
        """Should return empty list when no connections exist for owner."""
        connections, cursor = await repo.list("nonexistent-owner")

        assert connections == []
        assert cursor is None

    async def test_list_owner_isolation(self, repo, session):
        """Should only return connections for the specified owner."""
        # Use unique owner_ids to avoid cross-test pollution
        owner_1 = f"owner-1-{uuid4()}"
        owner_2 = f"owner-2-{uuid4()}"
        # Create connections for different owners
        await repo.create(
            MCPConnectionCreate(name="Owner1 Server", url="https://owner1.com"),
            owner_id=owner_1,
        )
        await repo.create(
            MCPConnectionCreate(name="Owner2 Server", url="https://owner2.com"),
            owner_id=owner_2,
        )
        await session.commit()

        # List for owner-1
        connections, _ = await repo.list(owner_1)

        assert len(connections) == 1
        assert connections[0].name == "Owner1 Server"

    async def test_list_filter_by_status(self, repo, session):
        """Should filter by connection status."""
        # Use unique owner_id to avoid cross-test pollution
        filter_owner = f"filter-owner-{uuid4()}"
        # Create connections
        conn1 = await repo.create(
            MCPConnectionCreate(name="Connected Server", url="https://c1.com"),
            owner_id=filter_owner,
        )
        await repo.create(
            MCPConnectionCreate(name="Disconnected Server", url="https://c2.com"),
            owner_id=filter_owner,
        )
        await session.commit()

        # Update one to connected
        await repo.update_status(conn1.id, "connected")
        await session.commit()

        # Filter by connected
        connections, _ = await repo.list(filter_owner, status="connected")

        assert len(connections) == 1
        assert connections[0].name == "Connected Server"

    async def test_list_filter_by_auth_type(self, repo, session):
        """Should filter by authentication type."""
        # Use unique owner_id to avoid cross-test pollution
        auth_owner = f"auth-owner-{uuid4()}"
        await repo.create(
            MCPConnectionCreate(
                name="OAuth Server",
                url="https://oauth.com",
                auth_type="oauth2",
                oauth2_client_id="client-1",
            ),
            owner_id=auth_owner,
        )
        await repo.create(
            MCPConnectionCreate(
                name="API Key Server",
                url="https://api.com",
                auth_type="api_key",
                api_key="key-123",
            ),
            owner_id=auth_owner,
        )
        await session.commit()

        # Filter by oauth2
        connections, _ = await repo.list(auth_owner, auth_type="oauth2")

        assert len(connections) == 1
        assert connections[0].name == "OAuth Server"

    async def test_list_filter_by_project(self, repo, session, test_project):
        """Should filter by project ID."""
        # Use unique owner_id to avoid cross-test pollution
        project_owner = f"project-owner-{uuid4()}"
        await repo.create(
            MCPConnectionCreate(
                name="Project Server",
                url="https://project.com",
                project_id=test_project.id,
            ),
            owner_id=project_owner,
        )
        await repo.create(
            MCPConnectionCreate(name="Other Server", url="https://other.com"),
            owner_id=project_owner,
        )
        await session.commit()

        # Filter by project
        connections, _ = await repo.list(project_owner, project_id=test_project.id)

        assert len(connections) == 1
        assert connections[0].name == "Project Server"


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionSorting:
    """Tests for sorting connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_sort_by_name_asc(self, repo, session):
        """Should sort by name ascending."""
        # Use unique owner_id to avoid cross-test pollution
        sort_owner = f"sort-owner-{uuid4()}"
        await repo.create(
            MCPConnectionCreate(name="Zebra Server", url="https://z.com"),
            owner_id=sort_owner,
        )
        await repo.create(
            MCPConnectionCreate(name="Alpha Server", url="https://a.com"),
            owner_id=sort_owner,
        )
        await repo.create(
            MCPConnectionCreate(name="Beta Server", url="https://b.com"),
            owner_id=sort_owner,
        )
        await session.commit()

        connections, _ = await repo.list(sort_owner, sort_by="name", sort_order="asc")

        names = [c.name for c in connections]
        assert names == ["Alpha Server", "Beta Server", "Zebra Server"]

    async def test_sort_by_name_desc(self, repo, session):
        """Should sort by name descending."""
        # Use unique owner_id to avoid cross-test pollution
        sort_desc_owner = f"sort-desc-owner-{uuid4()}"
        await repo.create(
            MCPConnectionCreate(name="Apple Server", url="https://apple.com"),
            owner_id=sort_desc_owner,
        )
        await repo.create(
            MCPConnectionCreate(name="Zulu Server", url="https://zulu.com"),
            owner_id=sort_desc_owner,
        )
        await session.commit()

        connections, _ = await repo.list(sort_desc_owner, sort_by="name", sort_order="desc")

        names = [c.name for c in connections]
        assert names == ["Zulu Server", "Apple Server"]

    async def test_sort_by_created_at_desc(self, repo, session):
        """Should sort by created_at descending (default)."""
        await repo.create(
            MCPConnectionCreate(name="First Server", url="https://first.com"),
            owner_id="time-owner",
        )
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await repo.create(
            MCPConnectionCreate(name="Second Server", url="https://second.com"),
            owner_id="time-owner",
        )
        await session.commit()

        connections, _ = await repo.list("time-owner", sort_by="created_at", sort_order="desc")

        # Most recent first
        assert connections[0].name == "Second Server"


@pytest.mark.xdist_group(name="connections_integration")
class TestConnectionPagination:
    """Tests for pagination."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_limit_results(self, repo, session):
        """Should limit number of returned results."""
        # Use unique owner_id to avoid cross-test pollution
        limit_owner = f"limit-owner-{uuid4()}"
        # Create 10 connections
        for i in range(10):
            await repo.create(
                MCPConnectionCreate(name=f"Server {i}", url=f"https://s{i}.com"),
                owner_id=limit_owner,
            )
        await session.commit()

        # Request only 5
        connections, cursor = await repo.list(limit_owner, limit=5)

        assert len(connections) == 5
        assert cursor is not None  # More results available

    async def test_cursor_pagination(self, repo, session):
        """Should paginate using cursor."""
        # Use unique owner_id to avoid cross-test pollution
        cursor_owner = f"cursor-owner-{uuid4()}"
        # Create 5 connections
        for i in range(5):
            await repo.create(
                MCPConnectionCreate(name=f"Paginated {i}", url=f"https://p{i}.com"),
                owner_id=cursor_owner,
            )
        await session.commit()

        # Get first page
        page1, cursor1 = await repo.list(cursor_owner, limit=2)
        assert len(page1) == 2
        assert cursor1 is not None

        # Get second page
        page2, cursor2 = await repo.list(cursor_owner, limit=2, cursor=cursor1)
        assert len(page2) == 2
        assert cursor2 is not None

        # Get third page
        page3, cursor3 = await repo.list(cursor_owner, limit=2, cursor=cursor2)
        assert len(page3) == 1
        assert cursor3 is None  # No more pages

        # Verify all items are unique
        all_names = [c.name for c in page1 + page2 + page3]
        assert len(set(all_names)) == 5


# ============================================================================
# OAuth2 State Management Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_integration")
class TestOAuth2StateManagement:
    """Tests for OAuth2 PKCE state management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_create_and_retrieve_oauth2_state(self, repo, session, secrets_provider):
        """Should create and retrieve OAuth2 state."""
        # Create OAuth2 connection first
        connection = await repo.create(
            MCPConnectionCreate(
                name="OAuth State Test",
                url="https://oauth-state.example.com",
                auth_type="oauth2",
                oauth2_client_id="client-xyz",
            ),
            owner_id="oauth-state-owner",
        )
        await session.commit()

        # Create state
        state = f"state-{uuid4()}"
        code_verifier = "a" * 64
        redirect_uri = "https://app.example.com/callback"

        await repo.create_oauth2_state(
            connection.id,
            state,
            code_verifier,
            redirect_uri,
        )
        await session.commit()

        # Retrieve and delete state (one-time use)
        state_data = await repo.get_and_delete_oauth2_state(state)
        await session.commit()

        assert state_data is not None
        assert state_data["connection_id"] == connection.id
        assert state_data["code_verifier"] == code_verifier
        assert state_data["redirect_uri"] == redirect_uri

    async def test_oauth2_state_one_time_use(self, repo, session, secrets_provider):
        """Should only allow one retrieval of OAuth2 state."""
        # Use unique owner_id to avoid cross-test pollution
        unique_owner = f"once-owner-{uuid4()}"
        connection = await repo.create(
            MCPConnectionCreate(
                name="One Time State",
                url="https://one-time.example.com",
                auth_type="oauth2",
                oauth2_client_id="client-once",
            ),
            owner_id=unique_owner,
        )
        await session.commit()

        state = f"once-{uuid4()}"
        # PKCE code_verifier must be 43-128 characters (use 64 char string)
        code_verifier = "a" * 64
        await repo.create_oauth2_state(
            connection.id,
            state,
            code_verifier,
            "https://callback.com",
        )
        await session.commit()

        # First retrieval succeeds
        data1 = await repo.get_and_delete_oauth2_state(state)
        await session.commit()
        assert data1 is not None

        # Second retrieval fails (state deleted)
        data2 = await repo.get_and_delete_oauth2_state(state)
        assert data2 is None

    async def test_oauth2_state_not_found(self, repo, session):
        """Should return None for nonexistent state."""
        data = await repo.get_and_delete_oauth2_state("nonexistent-state")
        assert data is None


# ============================================================================
# Token Management Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_integration")
class TestOAuth2TokenManagement:
    """Tests for OAuth2 token storage and retrieval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_store_and_retrieve_tokens(self, repo, session, secrets_provider):
        """Should store and retrieve OAuth2 tokens."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="Token Test",
                url="https://token.example.com",
                auth_type="oauth2",
                oauth2_client_id="token-client",
            ),
            owner_id="token-owner",
        )
        await session.commit()

        # Store tokens
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        await repo.store_oauth2_tokens(
            connection.id,
            access_token="access-token-xyz",
            refresh_token="refresh-token-abc",
            expires_at=expires_at,
        )
        await session.commit()

        # Retrieve access token
        token = await repo.get_oauth2_access_token(connection.id)
        assert token == "access-token-xyz"

        # Verify connection status updated to connected
        updated_conn = await repo.get(connection.id)
        assert updated_conn is not None
        assert updated_conn.status == "connected"


# ============================================================================
# Status Update Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_integration")
class TestStatusUpdates:
    """Tests for connection status updates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_update_status_connected(self, repo, session, secrets_provider):
        """Should update status to connected with server info."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="Status Test",
                url="https://status.example.com",
            ),
            owner_id="status-owner",
        )
        await session.commit()

        await repo.update_status(
            connection.id,
            status="connected",
            server_name="MCP Test Server",
            server_version="1.2.3",
            tool_count=10,
            resource_count=5,
            prompt_count=3,
        )
        await session.commit()

        updated = await repo.get(connection.id)
        assert updated is not None
        assert updated.status == "connected"
        assert updated.server_name == "MCP Test Server"
        assert updated.server_version == "1.2.3"
        assert updated.tool_count == 10
        assert updated.resource_count == 5
        assert updated.prompt_count == 3
        assert updated.last_connected_at is not None
        assert updated.last_error is None

    async def test_update_status_error(self, repo, session, secrets_provider):
        """Should update status to error with error message."""
        connection = await repo.create(
            MCPConnectionCreate(
                name="Error Test",
                url="https://error.example.com",
            ),
            owner_id="error-owner",
        )
        await session.commit()

        await repo.update_status(
            connection.id,
            status="error",
            last_error="Connection refused",
        )
        await session.commit()

        updated = await repo.get(connection.id)
        assert updated is not None
        assert updated.status == "error"
        assert updated.last_error == "Connection refused"
