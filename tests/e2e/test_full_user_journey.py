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

from typing import Any, Dict

import pytest
import pytest_asyncio

# These tests require the full test infrastructure
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.slow,
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
    """Test user credentials for E2E tests"""
    return {
        "username": "e2e_test_user",
        "password": "test_password_123",
        "email": "e2e@example.com",
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

    async def test_01_login(self, test_user_credentials):
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

    @pytest.mark.xfail(strict=True, reason="Implement when MCP server test fixture is ready")
    async def test_04_agent_chat_create_conversation(self, authenticated_session):
        """Step 4: Chat with agent and create new conversation"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call agent_chat tool with message and new thread_id
        # Receive AI response
        # Verify response format (concise vs detailed)
        # Verify conversation is persisted
        # Verify OpenFGA tuples are seeded (owner, editor, viewer)
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when MCP server test fixture is ready")
    async def test_05_agent_chat_continue_conversation(self, authenticated_session):
        """Step 5: Continue existing conversation"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call agent_chat with same thread_id
        # Verify context continuity (agent remembers previous messages)
        # Verify authorization check for existing conversation
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when MCP server test fixture is ready")
    async def test_06_search_conversations(self, authenticated_session):
        """Step 6: Search user's conversations"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call conversation_search with query
        # Receive matching conversations
        # Verify results are authorized (user can only see their own)
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when MCP server test fixture is ready")
    async def test_07_get_conversation(self, authenticated_session):
        """Step 7: Retrieve specific conversation by ID"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # Call conversation_get with thread_id
        # Receive full conversation history
        # Verify all messages are present
        # Verify viewer authorization
        pytest.fail("Test not yet implemented")

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
class TestGDPRComplianceJourney:
    """
    Test GDPR compliance operations:
    1. Right to Access (Article 15)
    2. Right to Data Portability (Article 20)
    3. Right to Rectification (Article 16)
    4. Right to Erasure (Article 17)
    5. Consent Management (Article 21)
    """

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_01_access_user_data(self, authenticated_session):
        """Article 15: Right to Access"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # GET /api/v1/users/me/data
        # Receive all user data in structured format
        # Verify data includes: profile, conversations, api_keys, service_principals
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when GDPR endpoints are integrated")
    async def test_02_export_user_data(self, authenticated_session):
        """Article 20: Right to Data Portability"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # GET /api/v1/users/me/export
        # Receive data in machine-readable format (JSON)
        # Verify export includes all personal data
        # Verify export can be imported elsewhere
        pytest.fail("Test not yet implemented")

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

    @pytest.mark.xfail(strict=True, reason="Implement when SP API is integrated")
    async def test_01_create_service_principal(self, authenticated_session):
        """Step 1: Create service principal"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /api/v1/service-principals/ with name, description, mode
        # Receive service_id and client_secret
        # Store client_secret for authentication
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when SP API is integrated")
    async def test_02_list_service_principals(self, authenticated_session):
        """Step 2: List user's service principals"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # GET /api/v1/service-principals/
        # Receive list including newly created SP
        # Verify no client_secret in response
        pytest.fail("Test not yet implemented")

    @pytest.mark.xfail(strict=True, reason="Implement when SP authentication is integrated")
    async def test_03_authenticate_with_client_credentials(self):
        """Step 3: Authenticate SP using OAuth2 client credentials flow"""
        pytest.fail("Test not yet implemented")
        # Expected flow:
        # POST /auth/token with client_id, client_secret, grant_type=client_credentials
        # Receive access_token for service principal
        # Verify token has correct claims (sub=service_id)
        pytest.fail("Test not yet implemented")

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
class TestAPIKeyJourney:
    """
    Test API key lifecycle:
    1. Create API key
    2. Use API key to authenticate (Kong plugin validates)
    3. Invoke tools using API key
    4. Rotate API key
    5. Revoke API key
    """

    @pytest.mark.xfail(strict=True, reason="Implement when API key endpoints are integrated")
    async def test_01_create_api_key(self, authenticated_session):
        """Step 1: Create API key"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # POST /api/v1/api-keys/ with name, expires_days
        # Receive key_id and api_key
        # Store api_key for later use

    @pytest.mark.xfail(strict=True, reason="Implement when API key endpoints are integrated")
    async def test_02_list_api_keys(self, authenticated_session):
        """Step 2: List user's API keys"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # GET /api/v1/api-keys/
        # Receive list including newly created key
        # Verify no api_key value in response (only metadata)

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

    @pytest.mark.xfail(strict=True, reason="Implement when API key revocation is integrated")
    async def test_06_revoke_api_key(self, authenticated_session):
        """Step 6: Revoke API key"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # DELETE /api/v1/api-keys/{key_id}
        # Receive 204 No Content
        # Verify key is deleted from Keycloak
        # Verify key no longer validates


# ==============================================================================
# Journey 5: Error Recovery and Edge Cases
# ==============================================================================


@pytest.mark.asyncio
class TestErrorRecoveryJourney:
    """
    Test error handling and recovery:
    1. Expired token handling
    2. Invalid credentials
    3. Authorization failures
    4. Network errors / retries
    5. Rate limiting
    """

    @pytest.mark.xfail(strict=True, reason="Implement when token expiration handling is ready")
    async def test_01_expired_token_refresh(self):
        """Test automatic token refresh on expiration"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Wait for token to expire (or mock expiration)
        # Make API call with expired token
        # Verify 401 Unauthorized
        # Refresh token
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
class TestMultiUserCollaboration:
    """
    Test multi-user scenarios:
    1. Share conversation with another user
    2. Collaborative editing
    3. Permission inheritance
    4. Conversation transfer
    """

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
class TestPerformanceE2E:
    """
    Test system performance under realistic load:
    1. Concurrent user sessions
    2. Large conversation history
    3. Bulk operations
    """

    @pytest.mark.xfail(strict=True, reason="Implement when performance testing is prioritized")
    async def test_01_concurrent_users(self):
        """Test system with multiple concurrent users"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Spawn 10 concurrent user sessions
        # Each user performs standard flow
        # Verify all succeed
        # Measure response times

    @pytest.mark.xfail(strict=True, reason="Implement when performance testing is prioritized")
    async def test_02_large_conversation(self, authenticated_session):
        """Test performance with large conversation history"""
        pytest.fail("Test not yet implemented")

        # Expected flow:
        # Create conversation with 1000+ messages
        # Retrieve conversation
        # Verify response time < 2 seconds
        # Verify memory usage is reasonable

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


async def create_test_user(username: str, password: str, email: str) -> Dict[str, Any]:
    """Create test user in Keycloak"""
    # TODO: Implement Keycloak user creation via admin API


async def login_user(username: str, password: str) -> Dict[str, Any]:
    """Login and get JWT token"""
    # TODO: Implement POST /auth/login


async def invoke_mcp_tool(tool_name: str, arguments: Dict[str, Any], token: str) -> Any:
    """Invoke MCP tool and get response"""
    # TODO: Implement MCP protocol communication


async def cleanup_test_data(user_id: str):
    """Clean up test data after tests"""
    # TODO: Delete test user, conversations, API keys, service principals
