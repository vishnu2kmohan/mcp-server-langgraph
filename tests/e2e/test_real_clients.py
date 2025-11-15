"""
Unit tests for real E2E client implementations.

These tests validate the RealKeycloakAuth and RealMCPClient classes
work correctly with mock HTTP responses (not actual infrastructure).
Integration tests in test_full_user_journey.py use actual test infrastructure.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.e2e.real_clients import RealKeycloakAuth, RealMCPClient, real_keycloak_auth, real_mcp_client

# Mark as unit test to ensure it runs in CI (uses mocks)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="e2e_real_clients_tests")
class TestRealKeycloakAuth:
    """
    Unit tests for RealKeycloakAuth client.

    GIVEN: RealKeycloakAuth class for Keycloak authentication
    WHEN: Testing login, refresh, logout, introspect operations
    THEN: Should correctly format requests and handle responses
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_login_success(self):
        """
        GIVEN: RealKeycloakAuth client
        WHEN: Calling login with valid credentials
        THEN: Should make POST request to token endpoint and return tokens
        """
        with patch("tests.e2e.real_clients.httpx.AsyncClient") as mock_client_class:
            # Arrange
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "expires_in": 300,
                "token_type": "Bearer",
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_instance

            auth = RealKeycloakAuth(base_url="http://localhost:9082")

            # Act
            tokens = await auth.login("alice", "password123")

            # Assert
            assert tokens["access_token"] == "fake-access-token"
            assert tokens["refresh_token"] == "fake-refresh-token"
            assert tokens["expires_in"] == 300

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "/realms/master/protocol/openid-connect/token" in call_args[0][0]
            assert call_args[1]["data"]["grant_type"] == "password"
            assert call_args[1]["data"]["username"] == "alice"
            assert call_args[1]["data"]["password"] == "password123"

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """
        GIVEN: real_keycloak_auth context manager
        WHEN: Using async with statement
        THEN: Should properly close HTTP client on exit
        """
        with patch("tests.e2e.real_clients.httpx.AsyncClient") as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            async with real_keycloak_auth() as auth:
                assert isinstance(auth, RealKeycloakAuth)

            # Verify close was called
            mock_instance.aclose.assert_called_once()


@pytest.mark.xdist_group(name="e2e_real_clients_tests")
class TestRealMCPClient:
    """
    Unit tests for RealMCPClient.

    GIVEN: RealMCPClient class for MCP protocol communication
    WHEN: Testing initialize, list_tools, call_tool operations
    THEN: Should correctly format MCP requests and handle responses
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_session(self):
        """
        GIVEN: RealMCPClient
        WHEN: Calling initialize to start MCP session
        THEN: Should POST to /mcp/initialize with protocol version
        """
        with patch("tests.e2e.real_clients.httpx.AsyncClient") as mock_client_class:
            # Arrange
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "protocol_version": "2024-11-05",
                "server_info": {"name": "mcp-server-langgraph", "version": "0.1.0"},
                "capabilities": {"tools": True, "resources": True},
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_instance

            client = RealMCPClient(base_url="http://localhost:8000")

            # Act
            result = await client.initialize()

            # Assert
            assert result["protocol_version"] == "2024-11-05"
            assert result["capabilities"]["tools"] is True

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "/mcp/initialize"
            assert call_args[1]["json"]["protocol_version"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """
        GIVEN: RealMCPClient with initialized session
        WHEN: Calling list_tools
        THEN: Should GET /mcp/tools/list and return tools array
        """
        with patch("tests.e2e.real_clients.httpx.AsyncClient") as mock_client_class:
            # Arrange
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "tools": [
                    {"name": "search", "description": "Search documents"},
                    {"name": "analyze", "description": "Analyze data"},
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_instance

            client = RealMCPClient()

            # Act
            result = await client.list_tools()

            # Assert
            assert len(result["tools"]) == 2
            assert result["tools"][0]["name"] == "search"

            mock_instance.get.assert_called_once_with("/mcp/tools/list")

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """
        GIVEN: real_mcp_client context manager
        WHEN: Using async with statement
        THEN: Should properly close HTTP client on exit
        """
        with patch("tests.e2e.real_clients.httpx.AsyncClient") as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            async with real_mcp_client(access_token="token") as client:
                assert isinstance(client, RealMCPClient)

            # Verify close was called
            mock_instance.aclose.assert_called_once()


@pytest.mark.xdist_group(name="e2e_real_clients_tests")
class TestBackwardsCompatibility:
    """
    Test backwards compatibility aliases.

    GIVEN: Backwards compatibility aliases for gradual migration
    WHEN: Using mock_* names
    THEN: Should map to real_* implementations
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_class_aliases_exist(self):
        """
        GIVEN: real_clients module
        WHEN: Checking for backwards compatibility aliases
        THEN: MockKeycloakAuth and MockMCPClient should exist
        """
        from tests.e2e.real_clients import MockKeycloakAuth, MockMCPClient

        assert MockKeycloakAuth is RealKeycloakAuth
        assert MockMCPClient is RealMCPClient

    def test_function_aliases_exist(self):
        """
        GIVEN: real_clients module
        WHEN: Checking for backwards compatibility function aliases
        THEN: mock_keycloak_auth and mock_mcp_client should exist
        """
        from tests.e2e.real_clients import mock_keycloak_auth, mock_mcp_client

        assert mock_keycloak_auth is real_keycloak_auth
        assert mock_mcp_client is real_mcp_client
