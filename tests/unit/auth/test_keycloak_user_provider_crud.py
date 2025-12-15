"""
Unit tests for KeycloakUserProvider CRUD methods

TDD tests for list_users, create_user, update_user, delete_user operations
that integrate with Keycloak Admin API.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.auth.keycloak import KeycloakConfig, KeycloakUser
from mcp_server_langgraph.auth.user_provider import KeycloakUserProvider, UserData

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.fixture
def keycloak_config() -> KeycloakConfig:
    """Create test Keycloak configuration."""
    return KeycloakConfig(
        server_url="http://localhost:8180",
        realm="test-realm",
        client_id="test-client",
        client_secret="test-secret",
        admin_username="admin",
        admin_password="admin-password",
    )


@pytest.fixture
def mock_keycloak_client():
    """Create mock KeycloakClient with async methods.

    These mocks are intentionally unconfigured here as individual tests
    configure the return_value or side_effect as needed.
    """
    mock_client = MagicMock()
    # Mocks configured per-test with return_value or side_effect
    mock_client.get_users = AsyncMock()  # noqa: async-mock-config
    mock_client.create_user = AsyncMock()  # noqa: async-mock-config
    mock_client.update_user = AsyncMock()  # noqa: async-mock-config
    mock_client.delete_user = AsyncMock()  # noqa: async-mock-config
    mock_client.get_user_by_username = AsyncMock()  # noqa: async-mock-config
    mock_client.get_user = AsyncMock()  # noqa: async-mock-config
    mock_client.set_user_password = AsyncMock()  # noqa: async-mock-config
    mock_client._get_user_realm_roles = AsyncMock(return_value=[])
    mock_client._get_user_client_roles = AsyncMock(return_value={})
    mock_client._get_user_groups = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def keycloak_provider(keycloak_config, mock_keycloak_client):
    """Create KeycloakUserProvider with mocked client."""
    provider = KeycloakUserProvider(config=keycloak_config)
    provider.client = mock_keycloak_client
    return provider


@pytest.mark.xdist_group(name="keycloak_provider_crud")
class TestKeycloakUserProviderListUsers:
    """Tests for list_users operation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_users_returns_empty_list_when_no_users(self, keycloak_provider, mock_keycloak_client):
        """Test list_users returns empty list when no users exist."""
        mock_keycloak_client.get_users.return_value = []

        result = await keycloak_provider.list_users()

        assert result == []
        mock_keycloak_client.get_users.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_users_returns_user_data_objects(self, keycloak_provider, mock_keycloak_client):
        """Test list_users converts Keycloak users to UserData objects."""
        mock_keycloak_client.get_users.return_value = [
            {
                "id": "user-uuid-1",
                "username": "alice",
                "email": "alice@example.com",
                "enabled": True,
            },
            {
                "id": "user-uuid-2",
                "username": "bob",
                "email": "bob@example.com",
                "enabled": False,
            },
        ]

        result = await keycloak_provider.list_users()

        assert len(result) == 2
        assert all(isinstance(u, UserData) for u in result)
        assert result[0].username == "alice"
        assert result[0].email == "alice@example.com"
        assert result[0].active is True
        assert result[1].username == "bob"
        assert result[1].active is False

    @pytest.mark.asyncio
    async def test_list_users_handles_keycloak_error_gracefully(self, keycloak_provider, mock_keycloak_client):
        """Test list_users handles Keycloak API errors gracefully."""
        import httpx

        mock_keycloak_client.get_users.side_effect = httpx.HTTPError("Connection failed")

        # Should return empty list on error, not raise
        result = await keycloak_provider.list_users()
        assert result == []


@pytest.mark.xdist_group(name="keycloak_provider_crud")
class TestKeycloakUserProviderCreateUser:
    """Tests for create_user operation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_user_calls_keycloak_admin_api(self, keycloak_provider, mock_keycloak_client):
        """Test create_user calls Keycloak Admin API with correct parameters."""
        mock_keycloak_client.create_user.return_value = "new-user-uuid"
        mock_keycloak_client.get_user.return_value = {
            "id": "new-user-uuid",
            "username": "newuser",
            "email": "newuser@example.com",
            "enabled": True,
        }

        result = await keycloak_provider.create_user(
            username="newuser",
            email="newuser@example.com",
            password="securepass123",
            roles=["user"],
        )

        assert isinstance(result, UserData)
        assert result.username == "newuser"
        assert result.email == "newuser@example.com"
        mock_keycloak_client.create_user.assert_called_once()
        mock_keycloak_client.set_user_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_sets_password_after_creation(self, keycloak_provider, mock_keycloak_client):
        """Test create_user sets password after creating user."""
        mock_keycloak_client.create_user.return_value = "user-uuid"
        mock_keycloak_client.get_user.return_value = {
            "id": "user-uuid",
            "username": "testuser",
            "email": "test@example.com",
            "enabled": True,
        }

        await keycloak_provider.create_user(
            username="testuser",
            email="test@example.com",
            password="mypassword",
        )

        mock_keycloak_client.set_user_password.assert_called_once_with("user-uuid", "mypassword", temporary=False)

    @pytest.mark.asyncio
    async def test_create_user_with_default_roles(self, keycloak_provider, mock_keycloak_client):
        """Test create_user uses default 'user' role when none specified."""
        mock_keycloak_client.create_user.return_value = "user-uuid"
        mock_keycloak_client.get_user.return_value = {
            "id": "user-uuid",
            "username": "testuser",
            "email": "test@example.com",
            "enabled": True,
        }

        result = await keycloak_provider.create_user(
            username="testuser",
            email="test@example.com",
            password="password",
        )

        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_create_user_raises_on_duplicate(self, keycloak_provider, mock_keycloak_client):
        """Test create_user raises ValueError if user already exists."""
        import httpx

        # Keycloak returns 409 Conflict for duplicate users
        response = MagicMock()
        response.status_code = 409
        response.text = "User exists"
        mock_keycloak_client.create_user.side_effect = httpx.HTTPStatusError(
            "Conflict", request=MagicMock(), response=response
        )

        with pytest.raises(ValueError, match="already exists"):
            await keycloak_provider.create_user(
                username="existing",
                email="existing@example.com",
                password="password",
            )


@pytest.mark.xdist_group(name="keycloak_provider_crud")
class TestKeycloakUserProviderUpdateUser:
    """Tests for update_user operation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_user_updates_email(self, keycloak_provider, mock_keycloak_client):
        """Test update_user updates user email."""
        mock_keycloak_client.get_user_by_username.return_value = KeycloakUser(
            id="user-uuid",
            username="testuser",
            email="old@example.com",
            enabled=True,
            realm_roles=["user"],
        )
        mock_keycloak_client.get_user.return_value = {
            "id": "user-uuid",
            "username": "testuser",
            "email": "new@example.com",
            "enabled": True,
        }

        result = await keycloak_provider.update_user(
            username="testuser",
            email="new@example.com",
        )

        assert result.email == "new@example.com"
        mock_keycloak_client.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_updates_active_status(self, keycloak_provider, mock_keycloak_client):
        """Test update_user updates active/enabled status."""
        mock_keycloak_client.get_user_by_username.return_value = KeycloakUser(
            id="user-uuid",
            username="testuser",
            email="test@example.com",
            enabled=True,
            realm_roles=["user"],
        )
        mock_keycloak_client.get_user.return_value = {
            "id": "user-uuid",
            "username": "testuser",
            "email": "test@example.com",
            "enabled": False,
        }

        result = await keycloak_provider.update_user(
            username="testuser",
            active=False,
        )

        assert result.active is False
        # Verify update_user was called with enabled=False
        call_args = mock_keycloak_client.update_user.call_args
        assert call_args[1].get("enabled") is False or call_args[0][1].get("enabled") is False

    @pytest.mark.asyncio
    async def test_update_user_raises_on_not_found(self, keycloak_provider, mock_keycloak_client):
        """Test update_user raises ValueError if user not found."""
        mock_keycloak_client.get_user_by_username.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await keycloak_provider.update_user(
                username="nonexistent",
                email="new@example.com",
            )


@pytest.mark.xdist_group(name="keycloak_provider_crud")
class TestKeycloakUserProviderDeleteUser:
    """Tests for delete_user operation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_user_returns_true_on_success(self, keycloak_provider, mock_keycloak_client):
        """Test delete_user returns True when user is deleted."""
        mock_keycloak_client.get_user_by_username.return_value = KeycloakUser(
            id="user-uuid",
            username="testuser",
            email="test@example.com",
            enabled=True,
            realm_roles=["user"],
        )
        mock_keycloak_client.delete_user.return_value = None

        result = await keycloak_provider.delete_user("testuser")

        assert result is True
        mock_keycloak_client.delete_user.assert_called_once_with("user-uuid")

    @pytest.mark.asyncio
    async def test_delete_user_returns_false_on_not_found(self, keycloak_provider, mock_keycloak_client):
        """Test delete_user returns False when user not found."""
        mock_keycloak_client.get_user_by_username.return_value = None

        result = await keycloak_provider.delete_user("nonexistent")

        assert result is False
        mock_keycloak_client.delete_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_handles_keycloak_error(self, keycloak_provider, mock_keycloak_client):
        """Test delete_user handles Keycloak API errors."""
        import httpx

        mock_keycloak_client.get_user_by_username.return_value = KeycloakUser(
            id="user-uuid",
            username="testuser",
            email="test@example.com",
            enabled=True,
            realm_roles=["user"],
        )
        mock_keycloak_client.delete_user.side_effect = httpx.HTTPError("Delete failed")

        # Should return False on error
        result = await keycloak_provider.delete_user("testuser")
        assert result is False
