"""
End-to-End tests for SCIM 2.0 User/Group Provisioning.

Tests the complete SCIM workflow from API request → Keycloak → OpenFGA.
Requires:
- Running Keycloak instance (docker-compose.keycloak-test.yml)
- Running application server

TDD RED phase: These tests will FAIL until Keycloak Admin API methods are implemented.

Run with:
    docker-compose -f docker-compose.keycloak-test.yml up -d
    pytest tests/e2e/test_scim_provisioning.py -v
"""

import os
from typing import AsyncGenerator, Dict
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
KEYCLOAK_TEST_URL = os.getenv("KEYCLOAK_TEST_URL", "http://localhost:8180")
SCIM_BASE_URL = f"{API_BASE_URL}/scim/v2"

pytestmark = [pytest.mark.e2e, pytest.mark.scim]


@pytest.fixture(scope="module")
async def keycloak_available() -> bool:
    """Check if Keycloak is available for E2E tests"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{KEYCLOAK_TEST_URL}/health/ready", timeout=5.0)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="module")
def skip_if_no_services(keycloak_available: bool) -> None:
    """Skip E2E tests if required services aren't running"""
    if not keycloak_available:
        pytest.skip(
            "E2E tests require running services. " "Start with: docker-compose -f docker-compose.keycloak-test.yml up -d"
        )


@pytest.fixture
async def authenticated_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client with authentication token"""
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        # Authenticate with test credentials
        # (Assumes inmemory auth provider with alice:alice123 for E2E tests)
        login_response = await client.post(
            "/auth/login",
            json={"username": "alice", "password": "alice123"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # Add auth header
        client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield client


@pytest.fixture
def unique_scim_user() -> Dict[str, any]:
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
def unique_scim_group() -> Dict[str, any]:
    """Generate unique SCIM group payload for test isolation"""
    unique_id = uuid4().hex[:8]
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": f"test_group_{unique_id}",
        "members": [],
    }


@pytest.mark.asyncio
@pytest.mark.e2e
class TestSCIMUserProvisioning:
    """E2E tests for SCIM 2.0 User endpoints (TDD RED phase)"""

    async def test_create_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: Dict,
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
        unique_scim_user: Dict,
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
        unique_scim_user: Dict,
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

    async def test_patch_update_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: Dict,
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

    async def test_delete_user_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: Dict,
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
class TestSCIMGroupProvisioning:
    """E2E tests for SCIM 2.0 Group endpoints (TDD RED phase)"""

    async def test_create_group_scim_endpoint(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_group: Dict,
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
        unique_scim_group: Dict,
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

    async def test_create_group_with_members(
        self,
        authenticated_client: httpx.AsyncClient,
        unique_scim_user: Dict,
        unique_scim_group: Dict,
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
class TestSCIMCompleteWorkflows:
    """E2E tests for complete SCIM provisioning workflows"""

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
class TestSCIMErrorHandling:
    """E2E tests for SCIM error handling and edge cases"""

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
        unique_scim_user: Dict,
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
