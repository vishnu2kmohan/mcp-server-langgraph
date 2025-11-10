"""
Security tests for SCIM 2.0 API Endpoints

Tests for CWE-862: Missing Authorization
OWASP A01:2021 - Broken Access Control

These tests validate that SCIM identity management endpoints require admin authorization.
"""

import gc
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from mcp_server_langgraph.api.scim import create_group, create_user, delete_user, update_user


@pytest.mark.xdist_group(name="scim_security_tests")
class TestSCIMSecurityControls:
    """Test that SCIM endpoints require admin authorization"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_user_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to create users via SCIM.

        CWE-862: Missing Authorization
        OWASP A01:2021 - Broken Access Control
        """
        # Given: A regular user without admin privileges
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],  # NOT admin
        }

        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "name": {"givenName": "New", "familyName": "User"},
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True,
        }

        mock_keycloak = AsyncMock()
        mock_openfga = AsyncMock()

        # When: Regular user attempts to create a user
        # Then: Should be REJECTED with 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await create_user(
                user_data=user_data,
                current_user=current_user,
                keycloak=mock_keycloak,
                openfga=mock_openfga,
            )

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_user_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to delete users via SCIM.
        """
        # Given: Regular user
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],
        }

        mock_keycloak = AsyncMock()
        mock_openfga = AsyncMock()

        # When: Regular user tries to delete a user
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(
                user_id="user-to-delete-123",
                current_user=current_user,
                keycloak=mock_keycloak,
                openfga=mock_openfga,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_group_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to create groups via SCIM.
        """
        # Given: Regular user
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],
        }

        group_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "Engineering",
            "members": [],
        }

        mock_keycloak = AsyncMock()

        # When: Regular user tries to create a group
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await create_group(
                group_data=group_data,
                current_user=current_user,
                keycloak=mock_keycloak,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_user_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to update users via SCIM PATCH.
        """
        # Given: Regular user
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],
        }

        # Mock SCIM PATCH request
        from mcp_server_langgraph.scim.schema import SCIMPatchOperation, SCIMPatchRequest

        patch_request = SCIMPatchRequest(Operations=[SCIMPatchOperation(op="replace", path="active", value=False)])

        mock_keycloak = AsyncMock()

        # When: Regular user tries to update another user
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="user-to-update-123",
                patch_request=patch_request,
                current_user=current_user,
                keycloak=mock_keycloak,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_create_user(self):
        """
        Admin users SHOULD be able to create users via SCIM.
        """
        # Given: Admin user
        current_user = {
            "user_id": "user:admin",
            "username": "admin",
            "roles": ["admin"],
        }

        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "name": {"givenName": "New", "familyName": "User"},
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True,
        }

        mock_keycloak = AsyncMock()
        mock_keycloak.create_user.return_value = "new-user-id-123"
        mock_keycloak.get_user.return_value = {
            "id": "new-user-id-123",
            "username": "newuser@example.com",
            "email": "newuser@example.com",
            "firstName": "New",
            "lastName": "User",
            "enabled": True,
        }

        mock_openfga = AsyncMock()

        # When: Admin creates a user
        # Then: Should SUCCEED
        result = await create_user(
            user_data=user_data,
            current_user=current_user,
            keycloak=mock_keycloak,
            openfga=mock_openfga,
        )

        assert result.userName == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_scim_client_credentials_allowed(self):
        """
        ALTERNATIVE: SCIM operations should be allowed with dedicated SCIM client credentials.

        This is for SSO/IdP provisioning scenarios (Okta, Azure AD, etc.)
        """
        # Given: SCIM client authentication (service account)
        current_user = {
            "user_id": "service:scim-client",
            "username": "scim-client",
            "roles": ["scim-provisioner"],  # Special SCIM role
        }

        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "provisioned@example.com",
            "name": {"givenName": "Provisioned", "familyName": "User"},
            "emails": [{"value": "provisioned@example.com", "primary": True}],
            "active": True,
        }

        mock_keycloak = AsyncMock()
        mock_keycloak.create_user.return_value = "provisioned-user-id"
        mock_keycloak.get_user.return_value = {
            "id": "provisioned-user-id",
            "username": "provisioned@example.com",
            "email": "provisioned@example.com",
            "firstName": "Provisioned",
            "lastName": "User",
            "enabled": True,
        }

        mock_openfga = AsyncMock()

        # When: SCIM client creates a user
        # Then: Should SUCCEED
        result = await create_user(
            user_data=user_data,
            current_user=current_user,
            keycloak=mock_keycloak,
            openfga=mock_openfga,
        )

        assert result.userName == "provisioned@example.com"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_openfga_admin_relation_check(self, openfga_client_real):
        """
        INTEGRATION TEST: Should check OpenFGA for admin relation before allowing SCIM operations.

        SCIM provisioning is a privileged operation that should only be allowed for users
        with admin relation to the organization or system.

        Security Control: Admin authorization check via OpenFGA before SCIM user provisioning
        """
        # Setup: Grant alice admin relation, bob is regular user
        await openfga_client_real.write_tuples([{"user": "user:alice", "relation": "admin", "object": "organization:acme"}])

        # Test 1: Alice (with admin relation) should be allowed SCIM operations
        is_alice_admin = await openfga_client_real.check_permission(
            user="user:alice", relation="admin", object="organization:acme"
        )
        assert is_alice_admin is True, "Alice should have admin relation to organization"

        # Test 2: Bob (without admin relation) should be denied SCIM operations
        is_bob_admin = await openfga_client_real.check_permission(
            user="user:bob", relation="admin", object="organization:acme"
        )
        assert is_bob_admin is False, "Bob should NOT have admin relation to organization"

        # Test 3: Verify non-existent user has no admin rights
        is_unknown_admin = await openfga_client_real.check_permission(
            user="user:unknown", relation="admin", object="organization:acme"
        )
        assert is_unknown_admin is False, "Unknown user should NOT have admin privileges"

        # Cleanup
        await openfga_client_real.delete_tuples([{"user": "user:alice", "relation": "admin", "object": "organization:acme"}])
