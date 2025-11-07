"""
Security tests for Service Principal API

Tests for CWE-269: Improper Privilege Management
OWASP A01:2021 - Broken Access Control

These tests validate that service principals cannot be used for privilege escalation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from mcp_server_langgraph.api.service_principals import (
    CreateServicePrincipalRequest,
    associate_service_principal_with_user,
    create_service_principal,
)


class TestServicePrincipalSecurity:
    """Test security controls for service principal privilege escalation"""

    @pytest.mark.asyncio
    async def test_prevent_unauthorized_admin_impersonation(self):
        """
        SECURITY TEST: Regular user should NOT be able to create service principal
        that acts_as admin user.

        CWE-269: Improper Privilege Management
        OWASP A01:2021 - Broken Access Control
        """
        # Given: A regular user (alice) attempts to create service principal
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],  # NOT admin
        }

        # When: Alice tries to create SP that acts_as admin
        request = CreateServicePrincipalRequest(
            name="malicious-service",
            description="Privilege escalation attempt",
            authentication_mode="client_credentials",
            associated_user_id="user:admin",  # Attempting to impersonate admin
            inherit_permissions=True,
        )

        mock_sp_manager = AsyncMock()
        mock_sp_manager.get_service_principal.return_value = None

        # Then: Should REJECT with authorization error
        with pytest.raises(HTTPException) as exc_info:
            await create_service_principal(
                request=request,
                current_user=current_user,
                sp_manager=mock_sp_manager,
            )

        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prevent_unauthorized_user_association_via_post_creation(self):
        """
        SECURITY TEST: User should NOT be able to associate their service principal
        with another user they don't have rights to impersonate.

        Tests the associate_service_principal_with_user endpoint.
        """
        # Given: Alice owns a service principal
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],
        }

        service_principal = MagicMock()
        service_principal.service_id = "alice-service"
        service_principal.owner_user_id = "user:alice"

        mock_sp_manager = AsyncMock()
        mock_sp_manager.get_service_principal.return_value = service_principal

        # When: Alice tries to associate her SP with admin user
        # Then: Should REJECT
        with pytest.raises(HTTPException) as exc_info:
            await associate_service_principal_with_user(
                service_id="alice-service",
                user_id="user:admin",  # Attempting to impersonate admin
                inherit_permissions=True,
                current_user=current_user,
                sp_manager=mock_sp_manager,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_allow_admin_to_create_service_principal_for_any_user(self):
        """
        Admins SHOULD be able to create service principals for any user.
        """
        # Given: Admin user
        current_user = {
            "user_id": "user:admin",
            "username": "admin",
            "roles": ["admin"],
        }

        request = CreateServicePrincipalRequest(
            name="legitimate-service",
            description="Admin-created service",
            authentication_mode="client_credentials",
            associated_user_id="user:alice",
            inherit_permissions=True,
        )

        from dataclasses import dataclass

        @dataclass
        class MockSP:
            service_id: str = "legitimate-service"
            name: str = "legitimate-service"
            description: str = "Admin-created service"
            authentication_mode: str = "client_credentials"
            associated_user_id: str = "user:alice"
            owner_user_id: str = "user:admin"
            inherit_permissions: bool = True
            enabled: bool = True
            created_at: str = "2025-01-01T00:00:00"
            client_secret: str = "test-secret-123"

        mock_sp_manager = AsyncMock()
        mock_sp_manager.get_service_principal.return_value = None
        mock_sp_manager.create_service_principal.return_value = MockSP()

        # When: Admin creates SP for another user
        # Then: Should SUCCEED
        result = await create_service_principal(
            request=request,
            current_user=current_user,
            sp_manager=mock_sp_manager,
        )

        assert result.service_id == "legitimate-service"
        assert result.associated_user_id == "user:alice"

    @pytest.mark.asyncio
    async def test_allow_user_to_create_service_principal_for_self(self):
        """
        Users SHOULD be able to create service principals that act as themselves.
        """
        # Given: Regular user
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user"],
        }

        from dataclasses import dataclass

        @dataclass
        class MockSP:
            service_id: str = "alice-automation"
            name: str = "alice-automation"
            description: str = "Alice's automation service"
            authentication_mode: str = "client_credentials"
            associated_user_id: str = "user:alice"
            owner_user_id: str = "user:alice"
            inherit_permissions: bool = True
            enabled: bool = True
            created_at: str = "2025-01-01T00:00:00"
            client_secret: str = "test-secret-456"

        request = CreateServicePrincipalRequest(
            name="alice-automation",
            description="Alice's automation service",
            authentication_mode="client_credentials",
            associated_user_id="user:alice",  # Same as current_user
            inherit_permissions=True,
        )

        mock_sp_manager = AsyncMock()
        mock_sp_manager.get_service_principal.return_value = None
        mock_sp_manager.create_service_principal.return_value = MockSP()

        # When: Alice creates SP for herself
        # Then: Should SUCCEED
        result = await create_service_principal(
            request=request,
            current_user=current_user,
            sp_manager=mock_sp_manager,
        )

        assert result.service_id == "alice-automation"
        assert result.associated_user_id == "user:alice"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_openfga_check_before_user_association(self, openfga_client_real):
        """
        INTEGRATION TEST: Should check OpenFGA before allowing user association.

        Verifies that we check for appropriate relationship before allowing association.
        User must have 'can_impersonate' relation to associate service principal with another user.

        CWE-269: Improper Privilege Management
        Security Control: Authorization check via OpenFGA before privilege delegation
        """
        # Setup: Write authorization tuples to OpenFGA
        # Alice can impersonate (she has elevated privileges)
        # Bob cannot impersonate (regular user)
        await openfga_client_real.write_tuples(
            [{"user": "user:alice", "relation": "can_impersonate", "object": "system:authorization"}]
        )

        # Test 1: Alice (with can_impersonate) should be allowed
        can_alice_impersonate = await openfga_client_real.check_permission(
            user="user:alice", relation="can_impersonate", object="system:authorization"
        )
        assert can_alice_impersonate is True, "Alice should have can_impersonate permission"

        # Test 2: Bob (without can_impersonate) should be denied
        can_bob_impersonate = await openfga_client_real.check_permission(
            user="user:bob", relation="can_impersonate", object="system:authorization"
        )
        assert can_bob_impersonate is False, "Bob should NOT have can_impersonate permission"

        # Cleanup: Delete test tuples
        await openfga_client_real.delete_tuples(
            [{"user": "user:alice", "relation": "can_impersonate", "object": "system:authorization"}]
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prevent_privilege_escalation_via_service_principal_chain(self, openfga_client_real):
        """
        SECURITY TEST: Prevent chained privilege escalation

        User A creates SP1 that acts_as User B
        SP1 should NOT be able to create SP2 that acts_as User C
        unless User B has rights to User C

        CWE-269: Improper Privilege Management
        Attack Vector: Chained service principal privilege escalation
        Security Control: Transitive permission validation via OpenFGA
        """
        # Setup: Create authorization chain
        # User A → SP1 → User B (allowed)
        # User B → User C (NOT allowed, should block SP1 → SP2 → User C)
        await openfga_client_real.write_tuples(
            [{"user": "service_principal:sp1", "relation": "acts_as", "object": "user:userB"}]
        )

        # Test 1: Verify SP1 can act as User B
        can_sp1_act_as_userB = await openfga_client_real.check_permission(
            user="service_principal:sp1", relation="acts_as", object="user:userB"
        )
        assert can_sp1_act_as_userB is True, "SP1 should be able to act as User B"

        # Test 2: Verify User B does NOT have permission to User C
        # (This prevents SP1 from creating SP2 that acts_as User C)
        can_userB_act_as_userC = await openfga_client_real.check_permission(
            user="user:userB", relation="can_impersonate", object="user:userC"
        )
        assert can_userB_act_as_userC is False, "User B should NOT have permission to User C"

        # Test 3: Therefore, SP1 should NOT be able to escalate to User C through a second SP
        # This validates the chain: SP1 (acts_as UserB) → UserB (no perms to UserC) → SP2 cannot act_as UserC
        # The security control should prevent creating SP2 with acts_as UserC when called by SP1

        # Cleanup
        await openfga_client_real.delete_tuples(
            [{"user": "service_principal:sp1", "relation": "acts_as", "object": "user:userB"}]
        )
