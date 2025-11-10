"""
Tests for Service Principal Manager

Following TDD principles - these tests are written BEFORE implementation.
Tests cover:
- Service principal creation (both authentication modes)
- User association and permission inheritance
- Secret rotation
- Listing and deletion
- OpenFGA tuple synchronization
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.auth.service_principal import ServicePrincipal, ServicePrincipalManager


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client for testing"""
    client = AsyncMock()
    client.create_client = AsyncMock(return_value={"id": "client-uuid-123"})
    client.create_user = AsyncMock(return_value="user-uuid-456")
    client.update_client_attributes = AsyncMock()
    client.update_client_secret = AsyncMock()
    client.get_clients = AsyncMock(return_value=[])
    client.get_users = AsyncMock(return_value=[])
    client.delete_client = AsyncMock()
    return client


@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for testing"""
    client = AsyncMock()
    client.write_tuples = AsyncMock()
    client.delete_tuples_for_object = AsyncMock()
    return client


@pytest.fixture
def service_principal_manager(mock_keycloak_client, mock_openfga_client):
    """Service Principal Manager instance for testing"""
    return ServicePrincipalManager(
        keycloak_client=mock_keycloak_client,
        openfga_client=mock_openfga_client,
    )


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalCreation:
    """Test service principal creation with different authentication modes"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_service_principal_client_credentials_mode(
        self, service_principal_manager, mock_keycloak_client, mock_openfga_client
    ):
        """Test creating service principal using client credentials flow"""
        # Arrange
        service_id = "batch-etl-job"
        name = "Batch ETL Job"
        description = "Nightly data processing"
        owner_user_id = "user:bob"

        # Act
        sp = await service_principal_manager.create_service_principal(
            service_id=service_id,
            name=name,
            description=description,
            authentication_mode="client_credentials",
            owner_user_id=owner_user_id,
        )

        # Assert
        assert sp.service_id == service_id
        assert sp.name == name
        assert sp.authentication_mode == "client_credentials"
        assert sp.client_secret is not None
        assert len(sp.client_secret) >= 32  # Secure secret length

        # Verify Keycloak client was created
        mock_keycloak_client.create_client.assert_called_once()
        call_args = mock_keycloak_client.create_client.call_args[0][0]
        assert call_args["clientId"] == service_id
        assert call_args["serviceAccountsEnabled"] is True
        assert call_args["standardFlowEnabled"] is False
        assert call_args["attributes"]["owner"] == owner_user_id

        # Verify OpenFGA tuple for ownership
        mock_openfga_client.write_tuples.assert_called_once()
        tuples = mock_openfga_client.write_tuples.call_args[0][0]
        assert any(
            t["user"] == owner_user_id and t["relation"] == "owner" and t["object"] == f"service_principal:{service_id}"
            for t in tuples
        )

    @pytest.mark.asyncio
    async def test_create_service_principal_service_account_user_mode(self, service_principal_manager, mock_keycloak_client):
        """Test creating service principal using service account user mode"""
        # Arrange
        service_id = "legacy-integration"
        name = "Legacy Integration"

        # Act
        sp = await service_principal_manager.create_service_principal(
            service_id=service_id,
            name=name,
            description="Legacy system integration",
            authentication_mode="service_account_user",
        )

        # Assert
        assert sp.authentication_mode == "service_account_user"
        assert sp.client_secret is not None

        # Verify Keycloak user was created
        mock_keycloak_client.create_user.assert_called_once()
        call_args = mock_keycloak_client.create_user.call_args[0][0]
        assert call_args["username"] == f"svc_{service_id}"
        assert call_args["attributes"]["serviceAccount"] == "true"
        assert len(call_args["credentials"]) == 1
        assert call_args["realmRoles"] == ["service-principal"]

    @pytest.mark.asyncio
    async def test_create_service_principal_with_user_association(self, service_principal_manager, mock_openfga_client):
        """Test creating service principal associated with user for permission inheritance"""
        # Arrange
        service_id = "scheduled-reports"
        associated_user_id = "user:alice"

        # Act
        sp = await service_principal_manager.create_service_principal(
            service_id=service_id,
            name="Scheduled Reports",
            description="Generate reports for Alice",
            authentication_mode="client_credentials",
            associated_user_id=associated_user_id,
            inherit_permissions=True,
        )

        # Assert
        assert sp.associated_user_id == associated_user_id
        assert sp.inherit_permissions is True

        # Verify OpenFGA acts_as tuple was created
        tuples = mock_openfga_client.write_tuples.call_args[0][0]
        assert any(
            t["user"] == f"service:{service_id}" and t["relation"] == "acts_as" and t["object"] == associated_user_id
            for t in tuples
        )

    @pytest.mark.asyncio
    async def test_create_service_principal_invalid_mode_raises_error(self, service_principal_manager):
        """Test that invalid authentication mode raises ValueError"""
        with pytest.raises(ValueError, match="Invalid authentication mode"):
            await service_principal_manager.create_service_principal(
                service_id="test",
                name="Test",
                description="Test",
                authentication_mode="invalid_mode",
            )


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalUserAssociation:
    """Test associating service principals with users"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_associate_with_user(self, service_principal_manager, mock_keycloak_client, mock_openfga_client):
        """Test associating existing service principal with user"""
        # Arrange
        service_id = "batch-job"
        user_id = "user:charlie"

        # Act
        await service_principal_manager.associate_with_user(
            service_id=service_id,
            user_id=user_id,
            inherit_permissions=True,
        )

        # Assert
        # Verify Keycloak attributes updated
        mock_keycloak_client.update_client_attributes.assert_called_once_with(
            service_id,
            {
                "associatedUserId": user_id,
                "inheritPermissions": "true",
            },
        )

        # Verify OpenFGA tuple created
        mock_openfga_client.write_tuples.assert_called_once()
        tuples = mock_openfga_client.write_tuples.call_args[0][0]
        assert tuples[0]["user"] == f"service:{service_id}"
        assert tuples[0]["relation"] == "acts_as"
        assert tuples[0]["object"] == user_id

    @pytest.mark.asyncio
    async def test_associate_without_permission_inheritance(
        self, service_principal_manager, mock_keycloak_client, mock_openfga_client
    ):
        """Test associating user without permission inheritance"""
        # Act
        await service_principal_manager.associate_with_user(
            service_id="batch-job",
            user_id="user:dave",
            inherit_permissions=False,
        )

        # Assert
        # Attributes updated but no OpenFGA tuple
        mock_keycloak_client.update_client_attributes.assert_called_once()
        mock_openfga_client.write_tuples.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalSecretRotation:
    """Test secret rotation for service principals"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rotate_secret(self, service_principal_manager, mock_keycloak_client):
        """Test rotating service principal secret"""
        # Arrange
        service_id = "api-integration"

        # Act
        new_secret = await service_principal_manager.rotate_secret(service_id)

        # Assert
        assert new_secret is not None
        assert len(new_secret) >= 32

        # Verify Keycloak secret was updated
        mock_keycloak_client.update_client_secret.assert_called_once_with(service_id, new_secret)

    @pytest.mark.asyncio
    async def test_rotate_secret_generates_different_secret(self, service_principal_manager):
        """Test that rotation generates cryptographically unique secrets"""
        # Act
        secret1 = await service_principal_manager.rotate_secret("service1")
        secret2 = await service_principal_manager.rotate_secret("service2")

        # Assert
        assert secret1 != secret2


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalListing:
    """Test listing service principals"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_all_service_principals(self, service_principal_manager, mock_keycloak_client):
        """Test listing all service principals"""
        # Arrange
        mock_keycloak_client.get_clients.return_value = [
            {
                "clientId": "service1",
                "name": "Service 1",
                "description": "Test service",
                "serviceAccountsEnabled": True,
                "enabled": True,
                "attributes": {
                    "owner": "user:alice",
                    "associatedUserId": "user:bob",
                    "inheritPermissions": "true",
                },
            }
        ]
        mock_keycloak_client.get_users.return_value = []

        # Act
        service_principals = await service_principal_manager.list_service_principals()

        # Assert
        assert len(service_principals) == 1
        sp = service_principals[0]
        assert sp.service_id == "service1"
        assert sp.name == "Service 1"
        assert sp.authentication_mode == "client_credentials"
        assert sp.owner_user_id == "user:alice"
        assert sp.associated_user_id == "user:bob"
        assert sp.inherit_permissions is True

    @pytest.mark.asyncio
    async def test_list_service_principals_filtered_by_owner(self, service_principal_manager, mock_keycloak_client):
        """Test listing service principals filtered by owner"""
        # Arrange
        owner = "user:alice"
        mock_keycloak_client.get_clients.return_value = [
            {
                "clientId": "service1",
                "serviceAccountsEnabled": True,
                "enabled": True,
                "attributes": {"owner": owner},
            },
            {
                "clientId": "service2",
                "serviceAccountsEnabled": True,
                "enabled": True,
                "attributes": {"owner": "user:bob"},
            },
        ]

        # Act
        service_principals = await service_principal_manager.list_service_principals(owner_user_id=owner)

        # Assert
        assert len(service_principals) == 1
        assert service_principals[0].service_id == "service1"


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalRetrieval:
    """Test retrieving service principals (regression test for Codex finding)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_service_principal_service_account_user_uses_correct_method(
        self, service_principal_manager, mock_keycloak_client
    ):
        """
        Test that get_service_principal uses get_user_by_username for service account users.

        REGRESSION TEST for Codex finding: get_user() expects UUID, not username.
        Service account usernames like 'svc_my-service' are NOT UUIDs, so we must
        use get_user_by_username() instead of get_user().
        """
        # Arrange
        service_id = "test-service"
        expected_username = f"svc_{service_id}"

        # Mock get_client to fail (not a client credentials service principal)
        mock_keycloak_client.get_client = AsyncMock(return_value=None)

        # Mock get_user_by_username to return a service account user
        mock_keycloak_client.get_user_by_username = AsyncMock(
            return_value={
                "id": "user-uuid-123",
                "username": expected_username,
                "firstName": "Test Service",
                "enabled": True,
                "attributes": {
                    "serviceAccount": "true",
                    "purpose": "Testing service account retrieval",
                    "owner": "user:alice",
                },
            }
        )

        # Mock get_user to raise an error if called (should NOT be called)
        mock_keycloak_client.get_user = AsyncMock(
            side_effect=Exception("get_user should not be called with username - requires UUID")
        )

        # Act
        sp = await service_principal_manager.get_service_principal(service_id)

        # Assert
        assert sp is not None, "Should retrieve service principal"
        assert sp.service_id == service_id
        assert sp.name == "Test Service"
        assert sp.authentication_mode == "service_account_user"

        # CRITICAL: Verify get_user_by_username was called with username, not get_user
        mock_keycloak_client.get_user_by_username.assert_called_once_with(expected_username)
        # Verify get_user was NOT called (if it was, the exception would have been raised)


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalDeletion:
    """Test deleting service principals"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_service_principal(self, service_principal_manager, mock_keycloak_client, mock_openfga_client):
        """Test deleting service principal removes from Keycloak and OpenFGA"""
        # Arrange
        service_id = "deprecated-service"

        # Act
        await service_principal_manager.delete_service_principal(service_id)

        # Assert
        # Verify removed from Keycloak
        mock_keycloak_client.delete_client.assert_called_once_with(service_id)

        # Verify OpenFGA tuples deleted
        mock_openfga_client.delete_tuples_for_object.assert_called_once_with(f"service_principal:{service_id}")


@pytest.mark.unit
@pytest.mark.xdist_group(name="service_principal_tests")
class TestServicePrincipalDataModel:
    """Test ServicePrincipal data model"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_service_principal_dataclass(self):
        """Test ServicePrincipal dataclass structure"""
        sp = ServicePrincipal(
            service_id="test-service",
            name="Test Service",
            description="Test description",
            authentication_mode="client_credentials",
            associated_user_id="user:test",
            owner_user_id="user:owner",
            inherit_permissions=True,
            enabled=True,
            created_at="2025-01-28T00:00:00Z",
            client_secret="secret123",
        )

        assert sp.service_id == "test-service"
        assert sp.authentication_mode == "client_credentials"
        assert sp.inherit_permissions is True

    def test_service_principal_optional_fields(self):
        """Test ServicePrincipal with optional fields omitted"""
        sp = ServicePrincipal(
            service_id="test",
            name="Test",
            description="Test",
            authentication_mode="client_credentials",
        )

        assert sp.associated_user_id is None
        assert sp.owner_user_id is None
        assert sp.inherit_permissions is False
        assert sp.enabled is True
