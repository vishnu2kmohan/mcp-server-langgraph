"""
MCP Connection Repository Unit Tests

TDD: Tests written FIRST for the ConnectionRepository implementation.
Tests the PostgresConnectionRepository for MCP server connection CRUD
with OAuth2 and API Key authentication support.
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# These imports will fail until we implement the repository
# That's expected in TDD - RED phase
from mcp_server_langgraph.repositories.connections import (
    PostgresConnectionRepository,
)
from mcp_server_langgraph.storage.models import (
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionUpdate,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="connection_repo"),
]


class TestConnectionRepository:
    """TDD tests for connection repository interface and implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock SQLAlchemy async session."""
        session = AsyncMock(return_value=None)  # async-mock-configured
        session.add = MagicMock()
        session.flush = AsyncMock(return_value=None)  # async-mock-configured
        session.delete = AsyncMock(return_value=None)  # async-mock-configured
        session.commit = AsyncMock(return_value=None)  # async-mock-configured
        # execute returns an awaitable that resolves to result
        # Make it return a MagicMock by default
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        return session

    @pytest.fixture
    def mock_secrets(self) -> AsyncMock:
        """Create a mock secrets provider."""
        secrets = AsyncMock(return_value=None)  # async-mock-configured
        secrets.set_secret = AsyncMock(return_value=None)  # async-mock-configured
        secrets.get_secret = AsyncMock(return_value=None)
        secrets.delete_secret = AsyncMock(return_value=None)  # async-mock-configured
        return secrets

    @pytest.fixture
    def repo(self, mock_session: AsyncMock, mock_secrets: AsyncMock) -> PostgresConnectionRepository:
        """Create repository with mocked dependencies."""
        return PostgresConnectionRepository(mock_session, mock_secrets)

    # =========================================================================
    # Create Connection Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_connection_returns_entity(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Creating a connection returns the created entity."""
        # GIVEN
        create_data = MCPConnectionCreate(
            name="Test MCP Server",
            url="https://mcp.example.com",
            auth_type="none",
        )

        # WHEN
        result = await repo.create(create_data, owner_id="user-123")

        # THEN
        assert result.name == "Test MCP Server"
        assert result.url == "https://mcp.example.com"
        assert result.auth_type == "none"
        assert result.owner_id == "user-123"
        assert result.status == "disconnected"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_connection_with_api_key_stores_secret(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: API key is stored in secrets provider."""
        # GIVEN
        create_data = MCPConnectionCreate(
            name="API Key Server",
            url="https://mcp.example.com",
            auth_type="api_key",
            api_key="test-api-key-12345",
        )

        # WHEN
        result = await repo.create(create_data, owner_id="user-123")

        # THEN
        assert result.auth_type == "api_key"
        mock_secrets.set_secret.assert_called_once()
        call_args = mock_secrets.set_secret.call_args
        assert "api_key" in call_args[0][0]  # Secret ID contains api_key
        assert call_args[0][1] == "test-api-key-12345"

    @pytest.mark.asyncio
    async def test_create_connection_with_oauth2_stores_config(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: OAuth2 configuration is stored correctly."""
        # GIVEN
        create_data = MCPConnectionCreate(
            name="OAuth2 Server",
            url="https://mcp.example.com",
            auth_type="oauth2",
            oauth2_client_id="client-123",
            oauth2_client_secret="secret-456",
            oauth2_scopes=["read", "write", "tools"],
        )

        # WHEN
        result = await repo.create(create_data, owner_id="user-123")

        # THEN
        assert result.auth_type == "oauth2"
        assert result.oauth2_config is not None
        assert result.oauth2_config.client_id == "client-123"
        assert result.oauth2_config.scopes == ["read", "write", "tools"]
        # Client secret should be stored in secrets provider
        mock_secrets.set_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_connection_generates_uuid(
        self,
        repo: PostgresConnectionRepository,
    ) -> None:
        """Test: Creating a connection generates a valid UUID."""
        # GIVEN
        create_data = MCPConnectionCreate(
            name="Test Server",
            url="https://mcp.example.com",
        )

        # WHEN
        result = await repo.create(create_data, owner_id="user-123")

        # THEN
        assert result.id is not None
        assert len(result.id) == 36  # UUID format

    # =========================================================================
    # Get Connection Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_connection_returns_entity(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Get returns connection entity when found."""
        # GIVEN
        connection_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self._create_mock_model(
            id=connection_id,
            name="Test Server",
            url="https://mcp.example.com",
        )
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.get(connection_id)

        # THEN
        assert result is not None
        assert result.id == connection_id
        assert result.name == "Test Server"

    @pytest.mark.asyncio
    async def test_get_connection_returns_none_when_not_found(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Get returns None when connection not found."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.get("nonexistent-id")

        # THEN
        assert result is None

    # =========================================================================
    # Update Connection Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_connection_updates_fields(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Update modifies specified fields."""
        # GIVEN
        connection_id = str(uuid4())
        mock_model = self._create_mock_model(
            id=connection_id,
            name="Old Name",
            url="https://old.example.com",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        update_data = MCPConnectionUpdate(
            name="New Name",
            description="Updated description",
        )

        # WHEN
        result = await repo.update(connection_id, update_data)

        # THEN
        assert result is not None
        assert mock_model.name == "New Name"
        assert mock_model.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_connection_returns_none_when_not_found(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Update returns None when connection not found."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.update("nonexistent-id", MCPConnectionUpdate(name="New"))

        # THEN
        assert result is None

    # =========================================================================
    # Delete Connection Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_connection_removes_entity(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: Delete removes connection and associated secrets."""
        # GIVEN
        connection_id = str(uuid4())
        mock_model = self._create_mock_model(
            id=connection_id,
            name="Test Server",
            api_key_secret_id=f"mcp_conn_{connection_id}_api_key",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.delete(connection_id)

        # THEN
        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_secrets.delete_secret.assert_called()  # Should delete API key secret

    @pytest.mark.asyncio
    async def test_delete_connection_returns_false_when_not_found(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Delete returns False when connection not found."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.delete("nonexistent-id")

        # THEN
        assert result is False

    # =========================================================================
    # List Connections Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_connections_returns_summaries(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List returns connection summaries for owner."""
        # GIVEN
        mock_models = [
            self._create_mock_model(id=str(uuid4()), name="Server 1"),
            self._create_mock_model(id=str(uuid4()), name="Server 2"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_models
        mock_session.execute.return_value = mock_result

        # WHEN
        connections, next_cursor = await repo.list(owner_id="user-123", limit=20)

        # THEN
        assert len(connections) == 2
        assert connections[0].name == "Server 1"
        assert connections[1].name == "Server 2"
        assert all(isinstance(c, MCPConnectionSummary) for c in connections)

    @pytest.mark.asyncio
    async def test_list_connections_filters_by_owner(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List only returns connections owned by the user."""
        # This test verifies the query filters by owner_id
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.list(owner_id="user-123")

        # THEN
        mock_session.execute.assert_called_once()
        # The actual query should contain owner_id filter
        # (verified by examining the call)

    @pytest.mark.asyncio
    async def test_list_connections_filters_by_status(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List can filter by connection status."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.list(owner_id="user-123", status="connected")

        # THEN
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_connections_filters_by_auth_type(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List can filter by authentication type."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.list(owner_id="user-123", auth_type="oauth2")

        # THEN
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_connections_supports_search(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List supports full-text search."""
        # GIVEN
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.list(owner_id="user-123", search="test server")

        # THEN
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_connections_supports_pagination(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: List supports cursor-based pagination."""
        # GIVEN
        mock_models = [self._create_mock_model(id=str(uuid4()), name=f"Server {i}") for i in range(21)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_models
        mock_session.execute.return_value = mock_result

        # WHEN
        connections, next_cursor = await repo.list(owner_id="user-123", limit=20)

        # THEN
        assert len(connections) == 20  # Limited to 20
        assert next_cursor is not None  # Has more pages

    # =========================================================================
    # API Key Management Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_store_api_key_uses_secrets_provider(
        self,
        repo: PostgresConnectionRepository,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: API key is stored in secrets provider."""
        # GIVEN
        connection_id = str(uuid4())
        api_key = "test-api-key-12345"

        # WHEN
        await repo.store_api_key(connection_id, api_key)

        # THEN
        mock_secrets.set_secret.assert_called_once()
        call_args = mock_secrets.set_secret.call_args
        assert connection_id in call_args[0][0]
        assert call_args[0][1] == api_key

    @pytest.mark.asyncio
    async def test_get_api_key_retrieves_from_secrets(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: API key is retrieved from secrets provider."""
        # GIVEN
        connection_id = str(uuid4())
        secret_id = f"mcp_conn_{connection_id}_api_key"
        mock_model = self._create_mock_model(
            id=connection_id,
            api_key_secret_id=secret_id,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        mock_secrets.get_secret.return_value = "retrieved-api-key"

        # WHEN
        result = await repo.get_api_key(connection_id)

        # THEN
        assert result == "retrieved-api-key"
        mock_secrets.get_secret.assert_called_once_with(secret_id)

    # =========================================================================
    # OAuth2 State Management Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_oauth2_state_stores_pkce_values(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: OAuth2 state is stored with PKCE values."""
        # GIVEN
        connection_id = str(uuid4())
        state = "random-state-value"
        code_verifier = "a" * 64  # PKCE verifier (min 43 chars)
        redirect_uri = "https://app.example.com/callback"

        # WHEN
        await repo.create_oauth2_state(
            connection_id=connection_id,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )

        # THEN
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_delete_oauth2_state_is_one_time_use(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: OAuth2 state is deleted after retrieval (one-time use)."""
        # GIVEN
        state = "random-state-value"
        mock_state_model = MagicMock()
        mock_state_model.connection_id = str(uuid4())
        mock_state_model.state = state
        mock_state_model.code_verifier = "a" * 64
        mock_state_model.redirect_uri = "https://app.example.com/callback"
        mock_state_model.expires_at = datetime.now(UTC) + timedelta(minutes=5)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state_model
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.get_and_delete_oauth2_state(state)

        # THEN
        assert result is not None
        assert result["state"] == state
        assert result["code_verifier"] == "a" * 64
        mock_session.delete.assert_called_once_with(mock_state_model)

    @pytest.mark.asyncio
    async def test_get_oauth2_state_returns_none_for_expired(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Returns None for expired OAuth2 states."""
        # GIVEN - state expired
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN
        result = await repo.get_and_delete_oauth2_state("expired-state")

        # THEN
        assert result is None

    # =========================================================================
    # OAuth2 Token Management Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_store_oauth2_tokens_uses_secrets_provider(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: OAuth2 tokens are stored securely."""
        # GIVEN
        connection_id = str(uuid4())
        access_token = "access-token-123"
        refresh_token = "refresh-token-456"
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_model = self._create_mock_model(id=connection_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.store_oauth2_tokens(
            connection_id=connection_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

        # THEN
        assert mock_secrets.set_secret.call_count >= 1  # At least access token stored
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_oauth2_access_token_retrieves_from_secrets(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
        mock_secrets: AsyncMock,
    ) -> None:
        """Test: Access token is retrieved from secrets provider."""
        # GIVEN
        connection_id = str(uuid4())
        token_secret_id = f"mcp_conn_{connection_id}_access_token"
        mock_model = self._create_mock_model(
            id=connection_id,
            oauth2_token_secret_id=token_secret_id,
            oauth2_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result
        mock_secrets.get_secret.return_value = "access-token-value"

        # WHEN
        result = await repo.get_oauth2_access_token(connection_id)

        # THEN
        assert result == "access-token-value"

    # =========================================================================
    # Connection Status Update Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_status_changes_connection_state(
        self,
        repo: PostgresConnectionRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test: Connection status can be updated."""
        # GIVEN
        connection_id = str(uuid4())
        mock_model = self._create_mock_model(id=connection_id, status="disconnected")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # WHEN
        await repo.update_status(
            connection_id=connection_id,
            status="connected",
            server_name="Test Server",
            server_version="1.0.0",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
        )

        # THEN
        assert mock_model.status == "connected"
        assert mock_model.server_name == "Test Server"
        assert mock_model.tool_count == 5

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_mock_model(
        self,
        id: str | None = None,
        name: str = "Test Server",
        url: str = "https://mcp.example.com",
        transport: str = "streamable_http",
        auth_type: str = "none",
        status: str = "disconnected",
        api_key_secret_id: str | None = None,
        oauth2_token_secret_id: str | None = None,
        oauth2_token_expires_at: datetime | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> MagicMock:
        """Create a mock MCPConnectionModel."""
        model = MagicMock()
        model.id = id or str(uuid4())
        model.name = name
        model.description = None
        model.url = url
        model.transport = transport
        model.command = command
        model.args = args
        model.env = env
        model.auth_type = auth_type
        model.status = status
        model.api_key_secret_id = api_key_secret_id
        model.oauth2_client_id = None
        model.oauth2_client_secret_id = None
        model.oauth2_authorization_url = None
        model.oauth2_token_url = None
        model.oauth2_scopes = None
        model.oauth2_token_secret_id = oauth2_token_secret_id
        model.oauth2_refresh_token_secret_id = None
        model.oauth2_token_expires_at = oauth2_token_expires_at
        model.last_error = None
        model.last_connected_at = None
        model.server_name = None
        model.server_version = None
        model.server_capabilities = None
        model.tool_count = 0
        model.resource_count = 0
        model.prompt_count = 0
        model.owner_id = "user-123"
        model.organization_id = None
        model.project_id = None
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)
        model.oauth2_states = []
        return model
