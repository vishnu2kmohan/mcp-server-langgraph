"""
End-to-End tests for SCIM 2.0 User/Group Provisioning.

Tests the complete SCIM workflow from API request → Keycloak → OpenFGA.
Requires:
- Running Keycloak instance (docker-compose.keycloak-test.yml)
- Running application server

Partial TDD RED phase: Some SCIM endpoints are implemented and passing.
Tests still in RED phase have individual xfail markers.

Run with:
    docker-compose -f docker-compose.keycloak-test.yml up -d
    pytest tests/e2e/test_scim_provisioning.py -v
"""

import gc
import os
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest

httpx = pytest.importorskip("httpx", reason="httpx required for SCIM E2E tests")


# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# CRITICAL: Include /authn prefix because Keycloak is configured with KC_HTTP_RELATIVE_PATH=/authn
KEYCLOAK_TEST_URL = os.getenv("KEYCLOAK_TEST_URL", "http://localhost/authn")
SCIM_BASE_URL = f"{API_BASE_URL}/scim/v2"
E2E_CLIENT_ID = "agent-studio-keycloak-client-id-for-e2e-tests"
E2E_CLIENT_SECRET = "test-client-secret-for-e2e-tests"

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def api_server_available() -> bool:
    """Check if API server is available for E2E tests"""
    import asyncio

    async def _check():
        try:
            # nosec B501: verify=False is intentional for E2E tests against local dev servers
            async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:  # nosec B501
                response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    return asyncio.run(_check())


@pytest.fixture(scope="module")
def keycloak_available() -> bool:
    """Check if Keycloak is available for E2E tests"""
    import asyncio

    async def _check():
        try:
            # nosec B501: verify=False is intentional for E2E tests against local dev servers
            async with httpx.AsyncClient(verify=False) as client:  # nosec B501
                # Use OIDC discovery endpoint — /health/ready isn't proxied via gateway
                response = await client.get(
                    f"{KEYCLOAK_TEST_URL}/realms/default/.well-known/openid-configuration",
                    timeout=5.0,
                )
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    return asyncio.run(_check())


@pytest.fixture(scope="module")
def skip_if_no_services(api_server_available: bool, keycloak_available: bool) -> None:
    """Skip E2E tests if required services aren't running"""
    missing_services = []
    if not api_server_available:
        missing_services.append(f"API server ({API_BASE_URL})")
    if not keycloak_available:
        missing_services.append(f"Keycloak ({KEYCLOAK_TEST_URL})")

    if missing_services:
        pytest.skip(
            f"E2E tests require running services. Missing: {', '.join(missing_services)}. "
            "Start with: docker-compose -f docker-compose.keycloak-test.yml up -d"
        )


async def _get_keycloak_token(username: str = "alice") -> str | None:
    """Get Keycloak access token via Token Exchange (RFC 8693).

    Two-step flow: client_credentials → token-exchange for user-specific token.
    ROPC (password grant) is disabled per ADR-0086.
    """
    token_url = f"{KEYCLOAK_TEST_URL}/realms/default/protocol/openid-connect/token"

    # nosec B501: verify=False for local test infrastructure
    async with httpx.AsyncClient(verify=False) as client:  # nosec B501
        # Step 1: Service account token via client_credentials
        sa_response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": E2E_CLIENT_ID,
                "client_secret": E2E_CLIENT_SECRET,
                "scope": "openid profile email offline_access",
            },
            timeout=10.0,
        )
        if sa_response.status_code != 200:
            return None
        sa_token = sa_response.json().get("access_token")
        if not sa_token:
            return None

        # Step 2: Exchange for user-specific token
        exchange_response = await client.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": E2E_CLIENT_ID,
                "client_secret": E2E_CLIENT_SECRET,
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": username,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email offline_access",
            },
            timeout=10.0,
        )
        if exchange_response.status_code == 200:
            return exchange_response.json().get("access_token")

        # Fallback to service account token if exchange not configured
        return sa_token


@pytest.fixture
async def authenticated_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client with authentication token via Keycloak Token Exchange."""
    token = await _get_keycloak_token("alice")
    if not token:
        pytest.skip("Could not obtain Keycloak token for SCIM tests")

    # nosec B501: verify=False for local test infrastructure
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:  # nosec B501
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture
def unique_scim_user() -> dict[str, Any]:
    """Generate unique SCIM user payload for test isolation"""
    unique_id = uuid4().hex[:8]
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": f"test_user_{unique_id}@example.com",
        "name": {
            "givenName": "Test",
            "familyName": f"User{unique_id}",
        },
        "emails": [
            {
                "value": f"test_user_{unique_id}@example.com",
                "primary": True,
            }
        ],
        "active": True,
    }


@pytest.fixture
def unique_scim_group() -> dict[str, Any]:
    """Generate unique SCIM group payload for test isolation"""
    unique_id = uuid4().hex[:8]
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": f"test_group_{unique_id}",
        "members": [],
    }


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.xdist_group(name="testscimuserprovisioning")
class TestSCIMUserProvisioning:
    """E2E tests for SCIM 2.0 User endpoints (partial TDD RED phase)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(reason="SCIM create_user: set_user_password not fully implemented", strict=False)
    async def test_create_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: POST /scim/v2/Users

        RED phase: Will fail until set_user_password() and get_user() are implemented.
        """
        response = await authenticated_client.post(
            "/scim/v2/Users",
            json=unique_scim_user,
        )

        # Expect 201 Created
        assert response.status_code == 201
        user = response.json()

        # Verify SCIM response structure
        assert "id" in user
        assert user["userName"] == unique_scim_user["userName"]
        assert user["name"]["givenName"] == "Test"
        assert user["active"] is True

        # Cleanup
        user_id = user["id"]
        delete_response = await authenticated_client.delete(f"/scim/v2/Users/{user_id}")
        assert delete_response.status_code == 204

    async def test_get_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: GET /scim/v2/Users/{id}

        RED phase: Will fail until get_user() is implemented.
        """
        # Create user first
        create_response = await authenticated_client.post("/scim/v2/Users", json=unique_scim_user)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        try:
            # Get user
            response = await authenticated_client.get(f"/scim/v2/Users/{user_id}")

            # Expect 200 OK
            assert response.status_code == 200
            user = response.json()

            assert user["id"] == user_id
            assert user["userName"] == unique_scim_user["userName"]
            assert user["name"]["givenName"] == "Test"

        finally:
            # Cleanup
            await authenticated_client.delete(f"/scim/v2/Users/{user_id}")

    async def test_put_replace_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: PUT /scim/v2/Users/{id} (Replace)

        RED phase: Will fail until update_user() is implemented.
        """
        # Create user
        create_response = await authenticated_client.post("/scim/v2/Users", json=unique_scim_user)
        user_id = create_response.json()["id"]

        try:
            # Replace user (PUT)
            updated_user = {
                **unique_scim_user,
                "name": {
                    "givenName": "Updated",
                    "familyName": "Name",
                },
                "active": True,
            }

            response = await authenticated_client.put(
                f"/scim/v2/Users/{user_id}",
                json=updated_user,
            )

            # Expect 200 OK
            assert response.status_code == 200
            user = response.json()

            assert user["name"]["givenName"] == "Updated"
            assert user["name"]["familyName"] == "Name"

        finally:
            await authenticated_client.delete(f"/scim/v2/Users/{user_id}")

    @pytest.mark.xfail(reason="SCIM patch_update_user: update_user not fully implemented", strict=False)
    async def test_patch_update_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: PATCH /scim/v2/Users/{id} (Partial update)

        RED phase: Will fail until update_user() is implemented.
        """
        # Create user
        create_response = await authenticated_client.post("/scim/v2/Users", json=unique_scim_user)
        user_id = create_response.json()["id"]

        try:
            # Patch user (PATCH)
            patch_operations = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {
                        "op": "replace",
                        "path": "name.givenName",
                        "value": "Patched",
                    },
                    {
                        "op": "add",
                        "path": "emails",
                        "value": [
                            {
                                "value": "patched@example.com",
                                "primary": False,
                            }
                        ],
                    },
                ],
            }

            response = await authenticated_client.patch(
                f"/scim/v2/Users/{user_id}",
                json=patch_operations,
            )

            # Expect 200 OK
            assert response.status_code == 200
            user = response.json()

            assert user["name"]["givenName"] == "Patched"
            # Verify emails include both original and new
            email_values = [e["value"] for e in user["emails"]]
            assert "patched@example.com" in email_values

        finally:
            await authenticated_client.delete(f"/scim/v2/Users/{user_id}")

    @pytest.mark.xfail(reason="SCIM delete_user: deactivation via update_user not fully implemented", strict=False)
    async def test_delete_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: DELETE /scim/v2/Users/{id} (Deactivate)

        RED phase: Will fail until update_user() is implemented (SCIM delete = deactivate).
        """
        # Create user
        create_response = await authenticated_client.post("/scim/v2/Users", json=unique_scim_user)
        user_id = create_response.json()["id"]

        # Delete user
        response = await authenticated_client.delete(f"/scim/v2/Users/{user_id}")

        # Expect 204 No Content
        assert response.status_code == 204

        # Verify user is deactivated (active=false)
        get_response = await authenticated_client.get(f"/scim/v2/Users/{user_id}")
        if get_response.status_code == 200:
            user = get_response.json()
            assert user["active"] is False

    async def test_search_users_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        skip_if_no_services: None,
    ):
        """
        E2E test: GET /scim/v2/Users?filter=...

        RED phase: Will fail until search_users() is implemented.
        """
        # Create multiple test users
        unique_prefix = f"search_test_{uuid4().hex[:8]}"
        user_ids = []

        for i in range(3):
            user_payload = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": f"{unique_prefix}_{i}@example.com",
                "name": {"givenName": f"Search{i}", "familyName": "Test"},
                "emails": [{"value": f"{unique_prefix}_{i}@example.com", "primary": True}],
                "active": True,
            }
            create_response = await authenticated_client.post("/scim/v2/Users", json=user_payload)
            user_ids.append(create_response.json()["id"])

        try:
            # Search users by filter
            response = await authenticated_client.get(
                "/scim/v2/Users",
                params={"filter": f'userName sw "{unique_prefix}"'},
            )

            # Expect 200 OK with list response
            assert response.status_code == 200
            result = response.json()

            assert "Resources" in result
            assert result["totalResults"] >= 3
            assert "itemsPerPage" in result
            assert "startIndex" in result

            # Verify our users are in results
            usernames = [u["userName"] for u in result["Resources"]]
            for i in range(3):
                assert f"{unique_prefix}_{i}@example.com" in usernames

        finally:
            # Cleanup
            for user_id in user_ids:
                await authenticated_client.delete(f"/scim/v2/Users/{user_id}")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.xdist_group(name="testscimgroupprovisioning")
class TestSCIMGroupProvisioning:
    """E2E tests for SCIM 2.0 Group endpoints (partial TDD RED phase)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_create_group_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_group: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: POST /scim/v2/Groups

        RED phase: Will fail until create_group(), add_user_to_group(), get_group() are implemented.
        """
        response = await authenticated_client.post(
            "/scim/v2/Groups",
            json=unique_scim_group,
        )

        # Expect 201 Created
        assert response.status_code == 201
        group = response.json()

        # Verify SCIM response structure
        assert "id" in group
        assert group["displayName"] == unique_scim_group["displayName"]
        assert "members" in group

    async def test_get_group_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_group: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: GET /scim/v2/Groups/{id}

        RED phase: Will fail until get_group() and get_group_members() are implemented.
        """
        # Create group first
        create_response = await authenticated_client.post("/scim/v2/Groups", json=unique_scim_group)
        assert create_response.status_code == 201
        group_id = create_response.json()["id"]

        # Get group
        response = await authenticated_client.get(f"/scim/v2/Groups/{group_id}")

        # Expect 200 OK
        assert response.status_code == 200
        group = response.json()

        assert group["id"] == group_id
        assert group["displayName"] == unique_scim_group["displayName"]
        assert "members" in group

    @pytest.mark.xfail(reason="SCIM create_group_with_members: member assignment not fully implemented", strict=False)
    async def test_create_group_with_members(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        unique_scim_group: dict,
        skip_if_no_services: None,
    ):
        """
        E2E test: Create group with members

        Tests complete workflow: create users → create group with members → verify.
        RED phase: Will fail until all group/user methods are implemented.
        """
        # Create users first
        user_ids = []
        for i in range(2):
            user_payload = {
                **unique_scim_user,
                "userName": f"member_{i}_{uuid4().hex[:8]}@example.com",
            }
            create_response = await authenticated_client.post("/scim/v2/Users", json=user_payload)
            user_ids.append(create_response.json()["id"])

        try:
            # Create group with members
            group_with_members = {
                **unique_scim_group,
                "members": [{"value": user_id} for user_id in user_ids],
            }

            response = await authenticated_client.post("/scim/v2/Groups", json=group_with_members)

            assert response.status_code == 201
            group = response.json()

            # Verify members
            assert len(group["members"]) == 2
            member_ids = [m["value"] for m in group["members"]]
            for user_id in user_ids:
                assert user_id in member_ids

        finally:
            # Cleanup
            for user_id in user_ids:
                await authenticated_client.delete(f"/scim/v2/Users/{user_id}")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.xdist_group(name="testscimcompleteworkflows")
class TestSCIMCompleteWorkflows:
    """E2E tests for complete SCIM provisioning workflows (partial TDD RED phase)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(
        reason="SCIM Okta-style workflow: user activation/deactivation via PATCH not fully implemented", strict=False
    )
    async def test_okta_style_user_provisioning_workflow(
        self,
        authenticated_client: httpx.AsyncClient,
        skip_if_no_services: None,
    ):
        """
        E2E test: Simulate Okta-style user provisioning workflow

        Workflow:
        1. Okta creates user (POST /Users)
        2. Okta sets password (PATCH /Users/{id})
        3. Okta activates user (PATCH /Users/{id})
        4. User authenticates
        5. Okta deactivates user on offboarding (DELETE /Users/{id})
        """
        unique_id = uuid4().hex[:8]

        # Step 1: Create user
        user_payload = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": f"okta_user_{unique_id}@example.com",
            "name": {"givenName": "Okta", "familyName": "Test"},
            "emails": [{"value": f"okta_user_{unique_id}@example.com", "primary": True}],
            "active": False,  # Start inactive
        }

        create_response = await authenticated_client.post("/scim/v2/Users", json=user_payload)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        try:
            # Step 2: Activate user
            activate_patch = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{"op": "replace", "path": "active", "value": True}],
            }

            patch_response = await authenticated_client.patch(
                f"/scim/v2/Users/{user_id}",
                json=activate_patch,
            )
            assert patch_response.status_code == 200
            assert patch_response.json()["active"] is True

            # Step 3: Deactivate user (DELETE in SCIM = deactivate)
            delete_response = await authenticated_client.delete(f"/scim/v2/Users/{user_id}")
            assert delete_response.status_code == 204

            # Verify deactivated
            get_response = await authenticated_client.get(f"/scim/v2/Users/{user_id}")
            if get_response.status_code == 200:
                assert get_response.json()["active"] is False

        finally:
            # Cleanup
            pass  # Already deleted

    async def test_azure_ad_style_group_sync_workflow(
        self,
        authenticated_client: httpx.AsyncClient,
        skip_if_no_services: None,
    ):
        """
        E2E test: Simulate Azure AD group sync workflow

        Workflow:
        1. Azure AD creates groups
        2. Azure AD creates users
        3. Azure AD adds users to groups
        4. Verify group memberships
        """
        unique_prefix = f"azure_{uuid4().hex[:8]}"

        # Create users
        user_ids = []
        for i in range(2):
            user_payload = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": f"{unique_prefix}_user{i}@example.com",
                "name": {"givenName": f"Azure{i}", "familyName": "User"},
                "emails": [{"value": f"{unique_prefix}_user{i}@example.com"}],
                "active": True,
            }
            create_response = await authenticated_client.post("/scim/v2/Users", json=user_payload)
            user_ids.append(create_response.json()["id"])

        try:
            # Create group with members
            group_payload = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                "displayName": f"{unique_prefix}_engineering",
                "members": [{"value": uid} for uid in user_ids],
            }

            group_response = await authenticated_client.post("/scim/v2/Groups", json=group_payload)
            assert group_response.status_code == 201

            group_id = group_response.json()["id"]

            # Verify group has members
            get_response = await authenticated_client.get(f"/scim/v2/Groups/{group_id}")
            assert get_response.status_code == 200

            group = get_response.json()
            assert len(group["members"]) == 2

        finally:
            # Cleanup
            for user_id in user_ids:
                await authenticated_client.delete(f"/scim/v2/Users/{user_id}")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.xdist_group(name="testscimerrorhandling")
@pytest.mark.xfail(
    reason="SCIM error handling not fully RFC 7644 compliant (missing status field, 500 instead of 409 for duplicates)",
    strict=False,
)
class TestSCIMErrorHandling:
    """E2E tests for SCIM error handling and edge cases"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_scim_error_format(
        self,
        authenticated_client: httpx.AsyncClient,
        skip_if_no_services: None,
    ):
        """Verify SCIM error responses follow RFC 7644 format"""
        # Try to get non-existent user
        response = await authenticated_client.get("/scim/v2/Users/nonexistent-uuid")

        assert response.status_code == 404
        error = response.json()

        # SCIM error format
        assert "status" in error
        assert error["status"] == 404
        assert "detail" in error

    async def test_duplicate_user_creation(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: dict,
        skip_if_no_services: None,
    ):
        """Test creating duplicate user returns proper error"""
        # Create user
        create_response = await authenticated_client.post("/scim/v2/Users", json=unique_scim_user)
        user_id = create_response.json()["id"]

        try:
            # Try to create duplicate
            duplicate_response = await authenticated_client.post(
                "/scim/v2/Users",
                json=unique_scim_user,
            )

            # Expect conflict error
            assert duplicate_response.status_code == 409
            error = duplicate_response.json()
            assert error["scimType"] == "uniqueness"

        finally:
            await authenticated_client.delete(f"/scim/v2/Users/{user_id}")
