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
from tests.conftest import get_user_id
from tests.helpers.async_mock_helpers import configured_async_mock


@pytest.mark.xdist_group(name="scim_security_tests")
class TestSCIMSecurityControls:
    """Test that SCIM endpoints require admin authorization"""

    def setup_method(self):
        """Reset state BEFORE test to prevent cross-test pollution"""
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None

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
        current_user = {"user_id": get_user_id("alice"), "username": "alice", "roles": ["user"]}
        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "name": {"givenName": "New", "familyName": "User"},
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True,
        }
        mock_keycloak = configured_async_mock(return_value=None)
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        mock_openfga.check_permission.return_value = False
        with pytest.raises(HTTPException) as exc_info:
            await create_user(user_data=user_data, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga)
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_user_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to delete users via SCIM.
        """
        current_user = {"user_id": get_user_id("alice"), "username": "alice", "roles": ["user"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        mock_openfga.check_permission.return_value = False
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(
                user_id="user-to-delete-123", current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_group_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to create groups via SCIM.
        """
        current_user = {"user_id": get_user_id("alice"), "username": "alice", "roles": ["user"]}
        group_data = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"], "displayName": "Engineering", "members": []}
        mock_keycloak = configured_async_mock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await create_group(group_data=group_data, current_user=current_user, keycloak=mock_keycloak)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_user_requires_admin_role(self):
        """
        SECURITY TEST: Regular user should NOT be able to update users via SCIM PATCH.
        """
        current_user = {"user_id": get_user_id("alice"), "username": "alice", "roles": ["user"]}
        from mcp_server_langgraph.scim.schema import SCIMPatchOperation, SCIMPatchRequest

        patch_request = SCIMPatchRequest(Operations=[SCIMPatchOperation(op="replace", path="active", value=False)])
        mock_keycloak = configured_async_mock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="user-to-update-123", patch_request=patch_request, current_user=current_user, keycloak=mock_keycloak
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_create_user(self):
        """
        Admin users SHOULD be able to create users via SCIM.
        """
        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "name": {"givenName": "New", "familyName": "User"},
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True,
        }
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_user.return_value = "new-user-id-123"
        mock_keycloak.get_user.return_value = {
            "id": "new-user-id-123",
            "username": "newuser@example.com",
            "email": "newuser@example.com",
            "firstName": "New",
            "lastName": "User",
            "enabled": True,
        }
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        result = await create_user(
            user_data=user_data, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga
        )
        assert result.userName == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_scim_client_credentials_allowed(self):
        """
        ALTERNATIVE: SCIM operations should be allowed with dedicated SCIM client credentials.

        This is for SSO/IdP provisioning scenarios (Okta, Azure AD, etc.)
        """
        current_user = {"user_id": "service:scim-client", "username": "scim-client", "roles": ["scim-provisioner"]}
        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "provisioned@example.com",
            "name": {"givenName": "Provisioned", "familyName": "User"},
            "emails": [{"value": "provisioned@example.com", "primary": True}],
            "active": True,
        }
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_user.return_value = "provisioned-user-id"
        mock_keycloak.get_user.return_value = {
            "id": "provisioned-user-id",
            "username": "provisioned@example.com",
            "email": "provisioned@example.com",
            "firstName": "Provisioned",
            "lastName": "User",
            "enabled": True,
        }
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        result = await create_user(
            user_data=user_data, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga
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
        await openfga_client_real.write_tuples(
            [{"user": get_user_id("alice"), "relation": "admin", "object": "organization:acme"}]
        )
        is_alice_admin = await openfga_client_real.check_permission(
            user=get_user_id("alice"), relation="admin", object="organization:acme"
        )
        assert is_alice_admin is True, "Alice should have admin relation to organization"
        is_bob_admin = await openfga_client_real.check_permission(
            user=get_user_id("bob"), relation="admin", object="organization:acme"
        )
        assert is_bob_admin is False, "Bob should NOT have admin relation to organization"
        is_unknown_admin = await openfga_client_real.check_permission(
            user=get_user_id("unknown"), relation="admin", object="organization:acme"
        )
        assert is_unknown_admin is False, "Unknown user should NOT have admin privileges"
        await openfga_client_real.delete_tuples(
            [{"user": get_user_id("alice"), "relation": "admin", "object": "organization:acme"}]
        )


@pytest.mark.xdist_group(name="scim_filter_injection_tests")
class TestSCIMFilterInjection:
    """
    SECURITY TEST: SCIM filter injection protection

    CWE-20: Improper Input Validation
    OWASP A03:2021 - Injection

    Tests that SCIM filter parsing safely handles malicious input and prevents injection attacks.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scim_filter_username_eq_safe_parsing(self):
        """
        SECURITY TEST: userName eq filter should safely parse without injection

        CWE-20: Improper Input Validation
        """
        from mcp_server_langgraph.api.scim import list_users

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        filter_expr = 'userName eq "alice@example.com"'
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users.return_value = [
            {
                "id": "user-123",
                "username": "alice@example.com",
                "email": "alice@example.com",
                "firstName": "Alice",
                "lastName": "Smith",
                "enabled": True,
            }
        ]
        result = await list_users(
            filter=filter_expr, startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        assert result.totalResults == 1
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        assert call_args[1]["query"]["username"] == "alice@example.com"
        assert call_args[1]["query"]["exact"] == "true"

    @pytest.mark.asyncio
    async def test_scim_filter_malformed_no_quotes_fail_safe(self):
        """
        SECURITY TEST: Malformed filter without quotes should fail safely (not crash)

        CWE-20: Improper Input Validation
        OWASP A03:2021 - Injection
        """
        from mcp_server_langgraph.api.scim import list_users

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        filter_expr = "userName eq alice"
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users.return_value = []
        await list_users(filter=filter_expr, startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak)
        call_args = mock_keycloak.search_users.call_args
        assert call_args[1]["query"] == {}


@pytest.mark.xdist_group(name="scim_error_handling_tests")
class TestSCIMErrorHandling:
    """
    Tests for SCIM error handling functions and CRUD operation error paths
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scim_error_with_scim_type(self):
        """Test scim_error() helper with scimType parameter"""
        from mcp_server_langgraph.api.scim import scim_error

        response = scim_error(404, "Resource not found", scim_type="notFound")
        assert response.status_code == 404
        import json

        body = json.loads(response.body)
        assert body["status"] == 404
        assert body["detail"] == "Resource not found"
        assert body["scimType"] == "notFound"

    @pytest.mark.asyncio
    async def test_delete_user_openfga_cleanup(self):
        """
        Test that delete_user calls OpenFGA delete_tuples_for_object

        GDPR/Data Protection: User deletion must clean up all authorization tuples
        """
        from mcp_server_langgraph.api.scim import delete_user

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        user_id_to_delete = "user-to-delete-123"
        await delete_user(user_id=user_id_to_delete, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga)
        mock_keycloak.update_user.assert_called_once_with(user_id_to_delete, {"enabled": False})
        mock_openfga.delete_tuples_for_object.assert_called_once_with(get_user_id("user-to-delete-123"))

    @pytest.mark.asyncio
    async def test_get_user_not_found_returns_404(self):
        """
        Test that get_user returns 404 when user not found
        """
        from mcp_server_langgraph.api.scim import get_user

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.get_user.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id="non-existent-user-id", current_user=current_user, keycloak=mock_keycloak)
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_user_generic_exception_returns_500(self):
        """
        Test that generic exceptions during user creation return 500
        """
        from mcp_server_langgraph.api.scim import create_user

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "newuser@example.com",
            "name": {"givenName": "New", "familyName": "User"},
            "emails": [{"value": "newuser@example.com", "primary": True}],
            "active": True,
        }
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_user.side_effect = Exception("Keycloak connection error")
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        with pytest.raises(HTTPException) as exc_info:
            await create_user(user_data=user_data, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga)
        assert exc_info.value.status_code == 500
        assert "Failed to create user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_user_patch_active_field(self):
        """
        Test that update_user (PATCH) correctly updates active field
        """
        from mcp_server_langgraph.api.scim import update_user
        from mcp_server_langgraph.scim.schema import SCIMPatchOperation, SCIMPatchRequest

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        patch_request = SCIMPatchRequest(Operations=[SCIMPatchOperation(op="replace", path="active", value=False)])
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.get_user.return_value = {
            "id": "user-123",
            "username": "alice@example.com",
            "email": "alice@example.com",
            "enabled": True,
        }
        mock_keycloak.update_user.return_value = None
        mock_keycloak.get_user.side_effect = [
            {"id": "user-123", "username": "alice@example.com", "email": "alice@example.com", "enabled": True},
            {"id": "user-123", "username": "alice@example.com", "email": "alice@example.com", "enabled": False},
        ]
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        result = await update_user(
            user_id="user-123",
            patch_request=patch_request,
            current_user=current_user,
            keycloak=mock_keycloak,
            openfga=mock_openfga,
        )
        assert result.active is False
        mock_keycloak.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_group_with_members(self):
        """
        Test that create_group adds all members to the group
        """
        from mcp_server_langgraph.api.scim import create_group

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        group_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "Engineering",
            "members": [{"value": "user-1", "display": "Alice"}, {"value": "user-2", "display": "Bob"}],
        }
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_group.return_value = "group-123"
        mock_keycloak.get_group.return_value = {"id": "group-123", "name": "Engineering"}
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        result = await create_group(
            group_data=group_data, current_user=current_user, keycloak=mock_keycloak, openfga=mock_openfga
        )
        assert mock_keycloak.add_user_to_group.call_count == 2
        mock_keycloak.add_user_to_group.assert_any_call("user-1", "group-123")
        mock_keycloak.add_user_to_group.assert_any_call("user-2", "group-123")
        assert result.displayName == "Engineering"

    @pytest.mark.asyncio
    async def test_get_group_not_found_returns_scim_error(self):
        """
        Test that get_group returns SCIM error when group not found
        """
        from mcp_server_langgraph.api.scim import get_group

        current_user = {"user_id": get_user_id("admin"), "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.get_group.return_value = None
        result = await get_group(group_id="non-existent-group", current_user=current_user, keycloak=mock_keycloak)
        import json

        assert result.status_code == 404
        body = json.loads(result.body)
        assert body["scimType"] == "notFound"
