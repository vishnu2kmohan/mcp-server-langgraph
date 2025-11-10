"""
Integration tests for Keycloak Admin API with real Keycloak instance.

These tests require a running Keycloak instance (via docker-compose).
Run: docker-compose -f docker-compose.keycloak-test.yml up -d

TDD RED phase: Tests written FIRST, will fail until Admin API methods are implemented.
"""

import gc
import os
from typing import AsyncGenerator
from uuid import uuid4

import httpx
import pytest
from pytest import FixtureRequest

from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig

# Test configuration - can be overridden via environment variables
KEYCLOAK_TEST_URL = os.getenv("KEYCLOAK_TEST_URL", "http://localhost:8180")
KEYCLOAK_TEST_REALM = os.getenv("KEYCLOAK_TEST_REALM", "test-realm")
KEYCLOAK_TEST_CLIENT_ID = os.getenv("KEYCLOAK_TEST_CLIENT_ID", "test-client")
KEYCLOAK_TEST_CLIENT_SECRET = os.getenv("KEYCLOAK_TEST_CLIENT_SECRET", "test-secret")  # gitleaks:allow
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Skip integration tests if Keycloak is not available
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def keycloak_available() -> bool:
    """Check if Keycloak test instance is available"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{KEYCLOAK_TEST_URL}/health/ready", timeout=5.0)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="module")
def skip_if_no_keycloak(keycloak_available: bool, request: FixtureRequest) -> None:
    """Skip tests if Keycloak is not available"""
    if not keycloak_available:
        pytest.skip(
            "Keycloak test instance not available. " "Start with: docker-compose -f docker-compose.keycloak-test.yml up -d"
        )


@pytest.fixture(scope="module")
def keycloak_config() -> KeycloakConfig:
    """Real Keycloak configuration for integration tests"""
    return KeycloakConfig(
        server_url=KEYCLOAK_TEST_URL,
        realm=KEYCLOAK_TEST_REALM,
        client_id=KEYCLOAK_TEST_CLIENT_ID,
        client_secret=KEYCLOAK_TEST_CLIENT_SECRET,
        admin_username=KEYCLOAK_ADMIN_USER,
        admin_password=KEYCLOAK_ADMIN_PASSWORD,
        verify_ssl=False,
        timeout=10,
    )


@pytest.fixture(scope="function")
async def keycloak_client(keycloak_config: KeycloakConfig) -> AsyncGenerator[KeycloakClient, None]:
    """Create Keycloak client for each test"""
    client = KeycloakClient(keycloak_config)
    yield client


@pytest.fixture
def unique_username() -> str:
    """Generate unique username for test isolation"""
    return f"test_user_{uuid4().hex[:8]}"


@pytest.fixture
def unique_group_name() -> str:
    """Generate unique group name for test isolation"""
    return f"test_group_{uuid4().hex[:8]}"


@pytest.fixture
def unique_client_id() -> str:
    """Generate unique client ID for test isolation"""
    return f"test_client_{uuid4().hex[:8]}"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_integration")
class TestKeycloakUserAdminAPIs:
    """Integration tests for Keycloak User Admin APIs (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_update_user_integration(
        self, keycloak_client: KeycloakClient, unique_username: str, skip_if_no_keycloak: None
    ):
        """Test updating user with real Keycloak instance"""
        # Create user first
        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
            "firstName": "Test",
            "lastName": "User",
        }

        user_id = await keycloak_client.create_user(user_config)
        assert user_id is not None

        try:
            # Update user (RED phase - will fail until implemented)
            updated_config = {
                "firstName": "Updated",
                "lastName": "TestUser",
                "email": f"{unique_username}_updated@example.com",
                "attributes": {
                    "department": ["engineering"],
                },
            }

            await keycloak_client.update_user(user_id, updated_config)

            # Verify update
            user = await keycloak_client.get_user(user_id)
            assert user is not None
            assert user["firstName"] == "Updated"
            assert user["lastName"] == "TestUser"
            assert user["email"] == f"{unique_username}_updated@example.com"

        finally:
            # Cleanup
            await keycloak_client.delete_user(user_id)

    async def test_set_user_password_integration(
        self, keycloak_client: KeycloakClient, unique_username: str, skip_if_no_keycloak: None
    ):
        """Test setting user password with real Keycloak"""
        # Create user
        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
        }

        user_id = await keycloak_client.create_user(user_config)

        try:
            # Set password (RED phase - will fail until implemented)
            await keycloak_client.set_user_password(user_id, "TestPassword123!", temporary=False)

            # Verify password works by authenticating
            tokens = await keycloak_client.authenticate_user(unique_username, "TestPassword123!")
            assert tokens["access_token"] is not None

        finally:
            await keycloak_client.delete_user(user_id)

    async def test_get_user_integration(
        self, keycloak_client: KeycloakClient, unique_username: str, skip_if_no_keycloak: None
    ):
        """Test getting user by ID with real Keycloak"""
        # Create user
        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
            "firstName": "John",
            "lastName": "Doe",
        }

        user_id = await keycloak_client.create_user(user_config)

        try:
            # Get user (RED phase - will fail until implemented)
            user = await keycloak_client.get_user(user_id)

            assert user is not None
            assert user["id"] == user_id
            assert user["username"] == unique_username
            assert user["email"] == f"{unique_username}@example.com"
            assert user["firstName"] == "John"
            assert user["lastName"] == "Doe"

        finally:
            await keycloak_client.delete_user(user_id)

    async def test_get_user_not_found_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test get_user returns None for non-existent user"""
        # RED phase - will fail until implemented
        user = await keycloak_client.get_user("non-existent-user-uuid")
        assert user is None

    async def test_search_users_integration(
        self, keycloak_client: KeycloakClient, unique_username: str, skip_if_no_keycloak: None
    ):
        """Test searching users with real Keycloak"""
        # Create multiple users for search
        user_ids = []
        for i in range(3):
            user_config = {
                "username": f"{unique_username}_{i}",
                "email": f"{unique_username}_{i}@example.com",
                "enabled": True,
            }
            user_id = await keycloak_client.create_user(user_config)
            user_ids.append(user_id)

        try:
            # Search users (RED phase - will fail until implemented)
            users = await keycloak_client.search_users(query={"username": unique_username}, first=0, max=10)

            assert len(users) >= 3
            usernames = [u["username"] for u in users]
            for i in range(3):
                assert f"{unique_username}_{i}" in usernames

        finally:
            # Cleanup
            for user_id in user_ids:
                await keycloak_client.delete_user(user_id)

    async def test_get_users_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test getting all users with real Keycloak"""
        # RED phase - will fail until implemented
        users = await keycloak_client.get_users()

        assert isinstance(users, list)
        assert len(users) > 0  # At least admin user should exist


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_integration")
class TestKeycloakGroupAdminAPIs:
    """Integration tests for Keycloak Group Admin APIs (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_create_group_integration(
        self, keycloak_client: KeycloakClient, unique_group_name: str, skip_if_no_keycloak: None
    ):
        """Test creating group with real Keycloak"""
        group_config = {
            "name": unique_group_name,
            "attributes": {
                "description": ["Test group for integration testing"],
            },
        }

        # RED phase - will fail until implemented
        group_id = await keycloak_client.create_group(group_config)

        assert group_id is not None
        assert len(group_id) > 0

        # Verify group was created
        group = await keycloak_client.get_group(group_id)
        assert group is not None
        assert group["name"] == unique_group_name

    async def test_get_group_integration(
        self, keycloak_client: KeycloakClient, unique_group_name: str, skip_if_no_keycloak: None
    ):
        """Test getting group by ID with real Keycloak"""
        # Create group first
        group_config = {"name": unique_group_name}
        group_id = await keycloak_client.create_group(group_config)

        # Get group (RED phase - will fail until implemented)
        group = await keycloak_client.get_group(group_id)

        assert group is not None
        assert group["id"] == group_id
        assert group["name"] == unique_group_name

    async def test_get_group_not_found_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test get_group returns None for non-existent group"""
        # RED phase - will fail until implemented
        group = await keycloak_client.get_group("non-existent-group-uuid")
        assert group is None

    async def test_get_group_members_integration(
        self,
        keycloak_client: KeycloakClient,
        unique_username: str,
        unique_group_name: str,
        skip_if_no_keycloak: None,
    ):
        """Test getting group members with real Keycloak"""
        # Create group and user
        group_config = {"name": unique_group_name}
        group_id = await keycloak_client.create_group(group_config)

        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
        }
        user_id = await keycloak_client.create_user(user_config)

        try:
            # Add user to group
            await keycloak_client.add_user_to_group(user_id, group_id)

            # Get group members (RED phase - will fail until implemented)
            members = await keycloak_client.get_group_members(group_id)

            assert len(members) >= 1
            member_ids = [m["id"] for m in members]
            assert user_id in member_ids

        finally:
            # Cleanup
            await keycloak_client.delete_user(user_id)

    async def test_add_user_to_group_integration(
        self,
        keycloak_client: KeycloakClient,
        unique_username: str,
        unique_group_name: str,
        skip_if_no_keycloak: None,
    ):
        """Test adding user to group with real Keycloak"""
        # Create group and user
        group_config = {"name": unique_group_name}
        group_id = await keycloak_client.create_group(group_config)

        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
        }
        user_id = await keycloak_client.create_user(user_config)

        try:
            # Add user to group (RED phase - will fail until implemented)
            await keycloak_client.add_user_to_group(user_id, group_id)

            # Verify membership
            members = await keycloak_client.get_group_members(group_id)
            member_ids = [m["id"] for m in members]
            assert user_id in member_ids

        finally:
            # Cleanup
            await keycloak_client.delete_user(user_id)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_integration")
class TestKeycloakClientAdminAPIs:
    """Integration tests for Keycloak Client Admin APIs (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_get_clients_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test getting all clients with real Keycloak"""
        # RED phase - will fail until implemented
        clients = await keycloak_client.get_clients()

        assert isinstance(clients, list)
        assert len(clients) > 0  # At least test-client should exist

    async def test_get_clients_with_query_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test getting clients with query filter"""
        # RED phase - will fail until implemented
        clients = await keycloak_client.get_clients(query={"clientId": KEYCLOAK_TEST_CLIENT_ID})

        assert isinstance(clients, list)
        # Should find at least the test client
        client_ids = [c.get("clientId") for c in clients]
        assert KEYCLOAK_TEST_CLIENT_ID in client_ids

    async def test_get_client_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test getting client by ID with real Keycloak"""
        # First get all clients to find test client UUID
        clients = await keycloak_client.get_clients(query={"clientId": KEYCLOAK_TEST_CLIENT_ID})
        assert len(clients) > 0
        test_client_uuid = clients[0]["id"]

        # Get specific client (RED phase - will fail until implemented)
        client = await keycloak_client.get_client(test_client_uuid)

        assert client is not None
        assert client["id"] == test_client_uuid
        assert client["clientId"] == KEYCLOAK_TEST_CLIENT_ID

    async def test_get_client_not_found_integration(self, keycloak_client: KeycloakClient, skip_if_no_keycloak: None):
        """Test get_client returns None for non-existent client"""
        # RED phase - will fail until implemented
        client = await keycloak_client.get_client("non-existent-client-uuid")
        assert client is None

    async def test_update_client_attributes_integration(
        self, keycloak_client: KeycloakClient, unique_client_id: str, skip_if_no_keycloak: None
    ):
        """Test updating client attributes with real Keycloak"""
        # Create client first
        client_config = {
            "clientId": unique_client_id,
            "enabled": True,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "publicClient": False,
        }

        client_uuid = await keycloak_client.create_client(client_config)

        try:
            # Update attributes (RED phase - will fail until implemented)
            new_attributes = {
                "owner": "user:alice",
                "environment": "test",
                "purpose": "integration-testing",
            }

            await keycloak_client.update_client_attributes(client_uuid, new_attributes)

            # Verify attributes updated
            client = await keycloak_client.get_client(client_uuid)
            assert client["attributes"] == new_attributes

        finally:
            # Cleanup
            await keycloak_client.delete_client(client_uuid)

    async def test_update_client_secret_integration(
        self, keycloak_client: KeycloakClient, unique_client_id: str, skip_if_no_keycloak: None
    ):
        """Test updating client secret with real Keycloak"""
        # Create client
        client_config = {
            "clientId": unique_client_id,
            "enabled": True,
            "serviceAccountsEnabled": True,
            "publicClient": False,
            "secret": "initial-secret-123",  # gitleaks:allow
        }

        client_uuid = await keycloak_client.create_client(client_config)

        try:
            # Update secret (RED phase - will fail until implemented)
            new_secret = "new-secret-456"
            await keycloak_client.update_client_secret(client_uuid, new_secret)

            # Note: Keycloak doesn't expose secrets via GET, so we can't verify directly
            # But if the call doesn't raise an exception, it succeeded

        finally:
            # Cleanup
            await keycloak_client.delete_client(client_uuid)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_integration")
class TestKeycloakEndToEndWorkflows:
    """End-to-end integration tests for complete SCIM workflows"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_user_lifecycle_workflow(
        self, keycloak_client: KeycloakClient, unique_username: str, skip_if_no_keycloak: None
    ):
        """Test complete user lifecycle: create → update → password → delete"""
        # Create
        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
            "firstName": "Test",
            "lastName": "User",
        }
        user_id = await keycloak_client.create_user(user_config)
        assert user_id is not None

        try:
            # Get
            user = await keycloak_client.get_user(user_id)
            assert user["username"] == unique_username

            # Update
            await keycloak_client.update_user(user_id, {"firstName": "Updated", "lastName": "Name"})

            user = await keycloak_client.get_user(user_id)
            assert user["firstName"] == "Updated"

            # Set password
            await keycloak_client.set_user_password(user_id, "SecurePass123!", temporary=False)

            # Verify authentication
            tokens = await keycloak_client.authenticate_user(unique_username, "SecurePass123!")
            assert tokens["access_token"] is not None

        finally:
            # Delete
            await keycloak_client.delete_user(user_id)

            # Verify deleted
            deleted_user = await keycloak_client.get_user(user_id)
            assert deleted_user is None

    async def test_group_membership_workflow(
        self,
        keycloak_client: KeycloakClient,
        unique_username: str,
        unique_group_name: str,
        skip_if_no_keycloak: None,
    ):
        """Test complete group workflow: create group → create user → add to group → verify"""
        # Create group
        group_config = {"name": unique_group_name}
        group_id = await keycloak_client.create_group(group_config)

        # Create user
        user_config = {
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "enabled": True,
        }
        user_id = await keycloak_client.create_user(user_config)

        try:
            # Add user to group
            await keycloak_client.add_user_to_group(user_id, group_id)

            # Verify membership
            members = await keycloak_client.get_group_members(group_id)
            member_usernames = [m["username"] for m in members]
            assert unique_username in member_usernames

        finally:
            # Cleanup
            await keycloak_client.delete_user(user_id)
