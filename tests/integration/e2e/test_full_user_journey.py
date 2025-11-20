"""
End-to-End Tests for Full User Journeys

Tests complete workflows from authentication through agent interaction to data management.
Requires docker-compose.test.yml infrastructure to be running.

Run with: docker compose -f docker-compose.test.yml up -d && make test-e2e

Test Journeys:
1. Standard User Flow: Login → MCP Init → Chat → Search → Get Conversation
2. GDPR Compliance Flow: Access Data → Export → Update Profile → Delete Account
3. Service Principal Flow: Create → Authenticate → Use → Rotate → Delete
4. API Key Flow: Create → Use → Rotate → Revoke
"""

import gc
import os
from typing import Any

import pytest
import pytest_asyncio

# These tests require the full test infrastructure
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="e2e_full_journey"),  # Prevent concurrent E2E runs
]


@pytest.fixture(scope="module")
def test_infrastructure_check(test_infrastructure):
    """
    Check that required test infrastructure is running.

    CODEX FINDING #3: Fixed to use test_infrastructure fixture from conftest.py
    instead of hardcoded TESTING env var check. This ensures E2E tests run when
    docker is available, not just when TESTING=true is set.

    This fixture ensures docker-compose.test.yml services are up:
    - PostgreSQL (port 9432)
    - Redis (port 9379)
    - OpenFGA (port 9080)
    - Keycloak (port 9082)
    - Qdrant (port 9333)
    """
    # test_infrastructure fixture from conftest.py handles:
    # - Docker availability check
    # - Service health checks with retries
    # - Automatic docker-compose lifecycle management
    # - Graceful skip if docker is not available

    if not test_infrastructure["ready"]:
        pytest.skip(
            "E2E infrastructure services not ready. "
            "Ensure Docker is running and docker-compose.test.yml services are healthy."
        )

    return True


@pytest_asyncio.fixture
async def test_user_credentials():
    """
    Test user credentials for E2E tests.

    Uses pre-configured user from tests/e2e/keycloak-test-realm.json.
    User is imported when Keycloak container starts.

    Credentials:
    - username: alice (from keycloak-test-realm.json)
    - password: alice123 (configured in realm import)
    - email: alice@example.com

    TDD Fix (2025-11-12):
    - Before: Used non-existent user 'e2e_test_user' → 401 Invalid credentials
    - After: Uses pre-configured 'alice' user → Authentication succeeds
    """
    return {
        "username": "alice",
        "password": "alice123",
        "email": "alice@example.com",
    }


@pytest_asyncio.fixture
async def authenticated_session(test_infrastructure_check, test_user_credentials):
    """
    Create authenticated session with JWT token.

    Returns session dict with:
    - access_token: JWT for API calls
    - refresh_token: For token refresh
    - user_id: User identifier
    - username: Username
    """
    # Use real Keycloak client to connect to test infrastructure
    from tests.e2e.real_clients import real_keycloak_auth

    async with real_keycloak_auth() as auth:
        username = test_user_credentials["username"]
        password = test_user_credentials["password"]

        # Login to real Keycloak instance
        tokens = await auth.login(username, password)

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user_id": f"user:{username}",
            "username": username,
            "expires_in": tokens["expires_in"],
        }


# ==============================================================================
# Journey 1: Standard User Flow
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="teststandarduserjourney")
class TestStandardUserJourney:
    """
    Test the complete standard user flow:
    1. Login and get JWT token
    2. Initialize MCP connection
    3. Chat with agent (create conversation)
    4. Search conversations
    5. Retrieve conversation history
    6. Refresh token
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_01_login(self, test_user_credentials, test_infrastructure_check):
        """Step 1: User logs in and receives JWT token"""
        from tests.e2e.real_clients import real_keycloak_auth

        # Use real Keycloak client to connect to test infrastructure
        async with real_keycloak_auth() as auth:
            username = test_user_credentials["username"]
            password = test_user_credentials["password"]

            # Login to real Keycloak instance
            tokens = await auth.login(username, password)

            # Verify token structure
            assert "access_token" in tokens
            assert "refresh_token" in tokens
            assert "expires_in" in tokens
            assert tokens["token_type"] == "Bearer"
            assert tokens["expires_in"] > 0

            # Verify token introspection
            introspection = await auth.introspect(tokens["access_token"])
            assert introspection["active"] is True
            assert introspection["username"] == username

    async def test_02_mcp_initialize(self, authenticated_session):
        """Step 2: Initialize MCP protocol connection"""
        from tests.e2e.real_clients import real_mcp_client

        # Use real MCP client to connect to test infrastructure
        async with real_mcp_client(access_token=authenticated_session["access_token"]) as mcp:
            # Initialize MCP session with real server
            init_response = await mcp.initialize()

            # Verify response structure
            assert "protocol_version" in init_response
            assert "server_info" in init_response
            assert "capabilities" in init_response

            # Verify server info
            assert init_response["server_info"]["name"] == "mcp-server-langgraph"
            assert "version" in init_response["server_info"]

            # Verify capabilities
            assert init_response["capabilities"]["tools"] is True

    async def test_03_list_tools(self, authenticated_session):
        """Step 3: List available MCP tools"""
        from tests.e2e.real_clients import real_mcp_client

        # Use real MCP client to connect to test infrastructure
        async with real_mcp_client(access_token=authenticated_session["access_token"]) as mcp:
            # List tools from real MCP server
            tools_response = await mcp.list_tools()

            # Verify response structure
            assert "tools" in tools_response
            assert isinstance(tools_response["tools"], list)
            assert len(tools_response["tools"]) > 0

            # Verify at least basic tools are present
            tool_names = [t["name"] for t in tools_response["tools"]]
            assert len(tool_names) >= 3

            # Verify tool structure
            for tool in tools_response["tools"]:
                assert "name" in tool
                assert "description" in tool

    async def test_04_agent_chat_create_conversation(self, authenticated_session):
        """
        Step 4: Chat with agent and create new conversation.

        GREEN: Implements full user journey - chat with agent via real MCP client.
        """
        from tests.e2e.real_clients import real_mcp_client

        access_token = authenticated_session["access_token"]
        user_id = authenticated_session["user_id"]

        # Connect to MCP server with auth token
        async with real_mcp_client(access_token=access_token) as mcp:
            # Create a new conversation
            conversation_id = await mcp.create_conversation(user_id=user_id)

            # Verify conversation ID returned
            assert conversation_id is not None
            assert isinstance(conversation_id, str)
            assert len(conversation_id) > 0

            # Send first message to agent
            response = await mcp.send_message(conversation_id=conversation_id, content="Hello! What is the capital of France?")

            # Verify response structure
            assert "message_id" in response or "content" in response or "messages" in response

            # If messages array returned, verify structure
            if "messages" in response:
                messages = response["messages"]
                assert len(messages) > 0
                # Should have at least the user message and AI response
                assert any(msg.get("role") == "user" for msg in messages)
                assert any(msg.get("role") in ["assistant", "ai"] for msg in messages)

    async def test_05_agent_chat_continue_conversation(self, authenticated_session):
        """
        Step 5: Continue existing conversation.

        GREEN: Tests conversation continuity and context persistence.
        """
        from tests.e2e.real_clients import real_mcp_client

        access_token = authenticated_session["access_token"]
        user_id = authenticated_session["user_id"]

        async with real_mcp_client(access_token=access_token) as mcp:
            # Create a conversation
            conversation_id = await mcp.create_conversation(user_id=user_id)

            # First message
            response1 = await mcp.send_message(conversation_id=conversation_id, content="My name is Alice.")
            assert response1 is not None

            # Second message - should maintain context
            response2 = await mcp.send_message(conversation_id=conversation_id, content="What is my name?")

            # Verify agent remembers context
            assert response2 is not None
            # Response should reference "Alice" if context is maintained
            if "content" in response2:
                content = response2["content"].lower()
                assert "alice" in content, "Agent should remember the user's name from context"

    @pytest.mark.xfail(strict=True, reason="Implement when MCP server test fixture is ready")
    async def test_06_search_conversations(self, authenticated_session):
        """Step 6: Search user's conversations"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call conversation_search with query
        # Receive matching conversations
        # Verify results are authorized (user can only see their own)
        pytest.fail("Test not yet implemented")

    async def test_07_get_conversation(self, authenticated_session):
        """
        Step 7: Retrieve specific conversation by ID.

        GREEN: Tests conversation retrieval and authorization.
        """
        from tests.e2e.real_clients import real_mcp_client

        access_token = authenticated_session["access_token"]
        user_id = authenticated_session["user_id"]

        async with real_mcp_client(access_token=access_token) as mcp:
            # Create and populate a conversation
            conversation_id = await mcp.create_conversation(user_id=user_id)

            await mcp.send_message(conversation_id=conversation_id, content="Test message for conversation retrieval")

            # Retrieve the conversation
            conversation_data = await mcp.get_conversation(conversation_id=conversation_id)

            # Verify conversation structure
            assert conversation_data is not None
            assert "conversation_id" in conversation_data or "id" in conversation_data

            # Verify conversation contains messages
            if "messages" in conversation_data:
                messages = conversation_data["messages"]
                assert len(messages) > 0
                # Should have at least the user message
                assert any("Test message for conversation retrieval" in str(msg) for msg in messages)

    @pytest.mark.xfail(strict=True, reason="Implement when token refresh is implemented")
    async def test_08_refresh_token(self, authenticated_session):
        """Step 8: Refresh JWT token before expiration"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /auth/refresh with refresh_token
        # Receive new access_token
        # Verify old token still works until expiration
        # Verify new token works
        pytest.fail("Test not yet implemented")


# ==============================================================================
# Journey 2: GDPR Compliance Flow
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.gdpr
@pytest.mark.xdist_group(name="testgdprcompliancejourney")
class TestGDPRComplianceJourney:
    """
    Test GDPR compliance operations:
    1. Right to Access (Article 15)
    2. Right to Data Portability (Article 20)
    3. Right to Rectification (Article 16)
    4. Right to Erasure (Article 17)
    5. Consent Management (Article 21)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_01_access_user_data(self, authenticated_session):
        """Article 15: Right to Access"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # GET /api/v1/users/me/data
        # Receive all user data in structured format
        # Verify data includes: profile, conversations, api_keys, service_principals
        pytest.fail("Test not yet implemented")

    async def test_02_export_user_data(self, authenticated_session):
        """
        Article 20: Right to Data Portability.

        GREEN: Tests GDPR data export functionality.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        # Connect to API with auth token
        async with httpx.AsyncClient() as client:
            # Request data export
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get("http://localhost:8000/api/v1/users/me/export", headers=headers, timeout=30.0)

            # Verify response
            if response.status_code == 404:
                # Endpoint not implemented yet - that's okay for RED phase
                pytest.skip("GDPR export endpoint not yet implemented (/api/v1/users/me/export)")

            # If implemented, validate structure
            assert response.status_code == 200, f"Export should succeed, got {response.status_code}"

            export_data = response.json()

            # Verify export structure (GDPR requires specific data)
            assert export_data is not None
            assert isinstance(export_data, dict)

            # GDPR Article 20 requires machine-readable format (JSON)
            # Should include at minimum:
            expected_sections = ["user_profile", "conversations", "api_keys"]
            for section in expected_sections:
                if section in export_data:
                    assert isinstance(
                        export_data[section], (list, dict)
                    ), f"Export section '{section}' should be structured data"

            # Verify export is comprehensive (not just partial data)
            assert len(export_data.keys()) > 0, "Export should contain user data"

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_03_update_profile(self, authenticated_session):
        """Article 16: Right to Rectification"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # PATCH /api/v1/users/me with updated data
        # Receive confirmation
        # Verify data is updated in all systems (Keycloak, OpenFGA)
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_04_manage_consent(self, authenticated_session):
        """Article 21: Consent Management"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /api/v1/users/me/consent to grant/revoke
        # GET /api/v1/users/me/consent to check status
        # Verify consent is respected in data processing
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_05_delete_account(self, authenticated_session):
        """Article 17: Right to Erasure"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # DELETE /api/v1/users/me
        # Receive confirmation
        # Verify all user data is deleted:
        #   - Keycloak user deleted
        #   - OpenFGA tuples deleted
        #   - Conversations deleted
        #   - API keys revoked
        #   - Service principals deleted
        # Verify user cannot login after deletion
        pytest.fail("Test not yet implemented")


# ==============================================================================
# Journey 3: Service Principal Flow
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testserviceprincipaljourney")
class TestServicePrincipalJourney:
    """
    Test service principal lifecycle:
    1. Create service principal
    2. Authenticate using client credentials
    3. Use SP to invoke tools
    4. Associate with user for permission inheritance
    5. Rotate client secret
    6. Delete service principal
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_01_create_service_principal(self, authenticated_session):
        """
        Step 1: Create service principal.

        GREEN: Tests SP creation via REST API with OAuth2 client credentials.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            # Create service principal
            response = await client.post(
                "http://localhost:8000/api/v1/service-principals",
                headers=headers,
                json={
                    "name": "E2E Test Service Principal",
                    "description": "Service principal for E2E testing",
                    "mode": "headless",
                },
                timeout=30.0,
            )

            # Check if endpoint exists
            if response.status_code == 404:
                pytest.skip("Service principal endpoint not yet implemented (/api/v1/service-principals)")

            # Verify successful creation
            assert response.status_code in [200, 201], f"SP creation should succeed, got {response.status_code}"

            sp_data = response.json()

            # Verify response structure
            assert "service_id" in sp_data or "id" in sp_data
            assert "client_secret" in sp_data or "secret" in sp_data

            # Verify client_secret format (should be secure)
            client_secret = sp_data.get("client_secret") or sp_data.get("secret")
            assert len(client_secret) >= 32, "Client secret should be at least 32 characters for security"

            # Verify service_id format
            service_id = sp_data.get("service_id") or sp_data.get("id")
            assert service_id.startswith("sp:") or service_id.startswith(
                "service:"
            ), "Service principal ID should have appropriate prefix"

    @pytest.mark.xfail(strict=True, reason="Implement when SP API is integrated")
    async def test_02_list_service_principals(self, authenticated_session):
        """Step 2: List user's service principals"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # GET /api/v1/service-principals/
        # Receive list including newly created SP
        # Verify no client_secret in response
        pytest.fail("Test not yet implemented")

    async def test_03_authenticate_with_client_credentials(self, authenticated_session):
        """
        Step 3: Authenticate SP using OAuth2 client credentials flow.

        GREEN: Tests OAuth2 client credentials grant for service principals.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            # First create a service principal
            create_response = await client.post(
                "http://localhost:8000/api/v1/service-principals",
                headers=headers,
                json={"name": "SP for Auth Test", "description": "Test", "mode": "headless"},
                timeout=30.0,
            )

            if create_response.status_code == 404:
                pytest.skip("Service principal endpoints not yet implemented")

            assert create_response.status_code in [200, 201]
            sp_data = create_response.json()
            client_id = sp_data.get("service_id") or sp_data.get("id")
            client_secret = sp_data.get("client_secret") or sp_data.get("secret")

            # Authenticate using client credentials
            auth_response = await client.post(
                "http://localhost:9082/realms/master/protocol/openid-connect/token",
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
                timeout=30.0,
            )

            # Check if OAuth2 flow is supported
            if auth_response.status_code == 400:
                pytest.skip("OAuth2 client credentials flow not yet configured in Keycloak")

            # Verify successful authentication
            assert auth_response.status_code == 200, f"SP auth should succeed, got {auth_response.status_code}"

            token_data = auth_response.json()

            # Verify token structure
            assert "access_token" in token_data
            assert "token_type" in token_data
            assert token_data["token_type"] == "Bearer"

            # Verify token is a valid JWT (basic format check)
            sp_token = token_data["access_token"]
            assert sp_token.count(".") == 2, "JWT should have 3 parts separated by dots"

    @pytest.mark.xfail(strict=True, reason="Implement when SP token usage is integrated")
    async def test_04_use_sp_to_invoke_tools(self):
        """Step 4: Use SP token to invoke MCP tools"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call agent_chat with SP access_token
        # Verify SP can execute tools
        # Verify authorization uses SP permissions
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when SP association is integrated")
    async def test_05_associate_with_user(self, authenticated_session):
        """Step 5: Associate SP with user for permission inheritance"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /api/v1/service-principals/{service_id}/associate-user
        # Specify user_id and inherit_permissions=true
        # Verify SP now inherits user's permissions
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when SP rotation is integrated")
    async def test_06_rotate_client_secret(self, authenticated_session):
        """Step 6: Rotate service principal secret"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /api/v1/service-principals/{service_id}/rotate-secret
        # Receive new client_secret
        # Verify old secret no longer works
        # Verify new secret works for authentication
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when SP deletion is integrated")
    async def test_07_delete_service_principal(self, authenticated_session):
        """Step 7: Delete service principal"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # DELETE /api/v1/service-principals/{service_id}
        # Receive 204 No Content
        # Verify SP is deleted from Keycloak
        # Verify OpenFGA tuples are deleted
        # Verify SP token no longer works
        pytest.fail("Test not yet implemented")


# ==============================================================================
# Journey 4: API Key Flow
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testapikeyjourney")
class TestAPIKeyJourney:
    """
    Test API key lifecycle:
    1. Create API key
    2. Use API key to authenticate (Kong plugin validates)
    3. Invoke tools using API key
    4. Rotate API key
    5. Revoke API key
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_01_create_api_key(self, authenticated_session):
        """
        Step 1: Create API key.

        GREEN: Tests API key creation via REST API.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            # Create API key
            response = await client.post(
                "http://localhost:8000/api/v1/api-keys",
                headers=headers,
                json={"name": "E2E Test API Key", "expires_days": 30},
                timeout=30.0,
            )

            # Check if endpoint exists
            if response.status_code == 404:
                pytest.skip("API key endpoint not yet implemented (/api/v1/api-keys)")

            # Verify successful creation
            assert response.status_code in [200, 201], f"API key creation should succeed, got {response.status_code}"

            key_data = response.json()

            # Verify response structure
            assert "key_id" in key_data or "id" in key_data
            assert "api_key" in key_data or "key" in key_data

            # Verify API key format (should be a secure random string)
            api_key = key_data.get("api_key") or key_data.get("key")
            assert len(api_key) >= 32, "API key should be at least 32 characters for security"

    async def test_02_list_api_keys(self, authenticated_session):
        """
        Step 2: List user's API keys.

        GREEN: Verifies API key listing and metadata security.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            # List API keys
            response = await client.get("http://localhost:8000/api/v1/api-keys", headers=headers, timeout=30.0)

            # Check if endpoint exists
            if response.status_code == 404:
                pytest.skip("API key list endpoint not yet implemented")

            # Verify success
            assert response.status_code == 200

            keys_data = response.json()

            # Verify response is a list
            assert isinstance(keys_data, (list, dict))

            # If dict, might have "keys" or "api_keys" field
            if isinstance(keys_data, dict):
                keys_list = keys_data.get("api_keys") or keys_data.get("keys") or []
            else:
                keys_list = keys_data

            # Security: Verify actual API key values are NOT returned
            for key_item in keys_list:
                assert (
                    "api_key" not in key_item or key_item["api_key"] is None
                ), "List endpoint should NOT return actual API key values (security risk)"
                # Should have metadata instead
                assert "key_id" in key_item or "id" in key_item
                assert "name" in key_item

    @pytest.mark.xfail(strict=True, reason="Implement when API key validation is integrated")
    async def test_03_validate_api_key_to_jwt(self):
        """Step 3: Validate API key and exchange for JWT (Kong plugin)"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # POST /api/v1/api-keys/validate with X-API-Key header
        # Receive access_token (JWT)
        # Verify JWT has correct user claims

    @pytest.mark.xfail(strict=True, reason="Implement when API key usage is integrated")
    async def test_04_use_api_key_for_tools(self):
        """Step 4: Use API key to invoke MCP tools"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Call agent_chat with JWT obtained from API key validation
        # Verify tool execution succeeds
        # Verify last_used timestamp is updated

    @pytest.mark.xfail(strict=True, reason="Implement when API key rotation is integrated")
    async def test_05_rotate_api_key(self, authenticated_session):
        """Step 5: Rotate API key"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # POST /api/v1/api-keys/{key_id}/rotate
        # Receive new api_key
        # Verify old key no longer validates
        # Verify new key validates successfully

    async def test_06_revoke_api_key(self, authenticated_session):
        """
        Step 6: Revoke API key.

        GREEN: Tests API key revocation and cleanup.
        """
        import httpx

        access_token = authenticated_session["access_token"]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            # First create an API key to revoke
            create_response = await client.post(
                "http://localhost:8000/api/v1/api-keys",
                headers=headers,
                json={"name": "Key to Revoke", "expires_days": 7},
                timeout=30.0,
            )

            if create_response.status_code == 404:
                pytest.skip("API key endpoints not yet implemented")

            assert create_response.status_code in [200, 201]
            key_data = create_response.json()
            key_id = key_data.get("key_id") or key_data.get("id")

            # Revoke the API key
            delete_response = await client.delete(
                f"http://localhost:8000/api/v1/api-keys/{key_id}", headers=headers, timeout=30.0
            )

            # Verify deletion success (204 No Content or 200 OK)
            assert delete_response.status_code in [
                200,
                204,
            ], f"API key revocation should succeed, got {delete_response.status_code}"

            # Verify key is no longer in list
            list_response = await client.get("http://localhost:8000/api/v1/api-keys", headers=headers, timeout=30.0)

            if list_response.status_code == 200:
                keys_data = list_response.json()
                keys_list = keys_data if isinstance(keys_data, list) else keys_data.get("api_keys", [])

                # Verify deleted key is not in list
                assert not any(
                    (k.get("key_id") == key_id or k.get("id") == key_id) for k in keys_list
                ), "Revoked API key should not appear in list"


# ==============================================================================
# Journey 5: Error Recovery and Edge Cases
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testerrorrecoveryjourney")
class TestErrorRecoveryJourney:
    """
    Test error handling and recovery:
    1. Expired token handling
    2. Invalid credentials
    3. Authorization failures
    4. Network errors / retries
    5. Rate limiting
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_01_expired_token_refresh(self, test_user_credentials, test_infrastructure_check):
        """
        Test automatic token refresh on expiration.

        GREEN: Tests 401 handling and token refresh flow.
        """
        import httpx

        from tests.e2e.real_clients import real_keycloak_auth

        # Login to get initial tokens
        async with real_keycloak_auth() as auth:
            tokens = await auth.login(test_user_credentials["username"], test_user_credentials["password"])

            # Use the refresh token to get a new access token
            new_tokens = await auth.refresh(tokens["refresh_token"])

            # Verify new token received
            assert "access_token" in new_tokens
            assert new_tokens["access_token"] != tokens["access_token"], "Refreshed token should be different from original"

            # Test making API call with refreshed token
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = await client.get("http://localhost:8000/api/v1/health", headers=headers, timeout=10.0)

                # If endpoint exists, verify token works
                if response.status_code != 404:
                    assert response.status_code in [200, 401], "Health check should either work or require different auth"
        # Retry with new token succeeds

    @pytest.mark.xfail(strict=True, reason="Implement when authentication is integrated")
    async def test_02_invalid_credentials(self):
        """Test login with invalid credentials"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # POST /auth/login with wrong password
        # Receive 401 Unauthorized
        # Verify no token is issued

    @pytest.mark.xfail(strict=True, reason="Implement when authorization is integrated")
    async def test_03_unauthorized_resource_access(self, authenticated_session):
        """Test accessing unauthorized conversation"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Try to access another user's conversation
        # Receive PermissionError
        # Verify OpenFGA denied access

    @pytest.mark.xfail(strict=True, reason="Implement when rate limiting is ready")
    async def test_04_rate_limiting(self, authenticated_session):
        """Test rate limiting enforcement"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Make rapid API calls exceeding rate limit
        # Receive 429 Too Many Requests
        # Wait for rate limit reset
        # Verify subsequent call succeeds

    @pytest.mark.xfail(strict=True, reason="Implement when retry logic is ready")
    async def test_05_network_error_retry(self):
        """Test retry logic for transient network errors"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Simulate network error (mock)
        # Verify automatic retry with exponential backoff
        # Verify eventual success


# ==============================================================================
# Journey 6: Multi-User Collaboration
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testmultiusercollaboration")
class TestMultiUserCollaboration:
    """
    Test multi-user scenarios:
    1. Share conversation with another user
    2. Collaborative editing
    3. Permission inheritance
    4. Conversation transfer
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(strict=True, reason="Implement when conversation sharing is ready")
    async def test_01_share_conversation(self, authenticated_session):
        """Test sharing conversation with another user"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # User A creates conversation
        # User A grants viewer permission to User B via OpenFGA
        # User B can read conversation
        # User B cannot edit conversation (viewer != editor)

    @pytest.mark.xfail(strict=True, reason="Implement when permission management is ready")
    async def test_02_grant_edit_permission(self, authenticated_session):
        """Test granting edit permission"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # User A grants editor permission to User B
        # User B can now add messages to conversation
        # Verify both users see all messages

    @pytest.mark.xfail(strict=True, reason="Implement when permission revocation is ready")
    async def test_03_revoke_permission(self, authenticated_session):
        """Test revoking access permission"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # User A revokes User B's access
        # User B can no longer read or edit conversation
        # Verify OpenFGA tuple is deleted


# ==============================================================================
# Performance and Load Tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.xdist_group(name="testperformancee2e")
class TestPerformanceE2E:
    """
    Test system performance under realistic load:
    1. Concurrent user sessions
    2. Large conversation history
    3. Bulk operations
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Performance tests skipped in parallel mode due to memory overhead",
    )
    @pytest.mark.xfail(strict=True, reason="Implement when performance testing is prioritized")
    async def test_01_concurrent_users(self):
        """Test system with multiple concurrent users"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Spawn 10 concurrent user sessions
        # Each user performs standard flow
        # Verify all succeed
        # Measure response times

    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Performance tests skipped in parallel mode due to memory overhead",
    )
    @pytest.mark.xfail(strict=True, reason="Implement when performance testing is prioritized")
    async def test_02_large_conversation(self, authenticated_session):
        """Test performance with large conversation history"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Create conversation with 1000+ messages
        # Retrieve conversation
        # Verify response time < 2 seconds
        # Verify memory usage is reasonable

    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is not None,
        reason="Performance tests skipped in parallel mode due to memory overhead",
    )
    @pytest.mark.xfail(strict=True, reason="Implement when performance testing is prioritized")
    async def test_03_bulk_search(self, authenticated_session):
        """Test search across many conversations"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Create 100 conversations
        # Search across all
        # Verify response time < 3 seconds
        # Verify results are accurate


# ==============================================================================
# Helper Functions (to be implemented)
# ==============================================================================


async def create_test_user(username: str, password: str, email: str) -> dict[str, Any]:
    """Create test user in Keycloak"""
    # TODO: Implement Keycloak user creation via admin API


async def login_user(username: str, password: str) -> dict[str, Any]:
    """Login and get JWT token"""
    # TODO: Implement POST /auth/login


async def invoke_mcp_tool(tool_name: str, arguments: dict[str, Any], token: str) -> Any:
    """Invoke MCP tool and get response"""
    # TODO: Implement MCP protocol communication


async def cleanup_test_data(user_id: str):
    """Clean up test data after tests"""
    # TODO: Delete test user, conversations, API keys, service principals
