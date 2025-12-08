"""
Real Client Implementations for E2E Tests

This module provides real HTTP client implementations that connect to
the actual test infrastructure (docker-compose.test.yml services).

Migration from Mocks:
- Replaces MockKeycloakAuth with RealKeycloakAuth
- Replaces MockMCPClient with RealMCPClient
- Uses actual HTTP calls to test services on offset ports (9000+)

Usage:
    from tests.e2e.real_clients import real_keycloak_auth, real_mcp_client

    async with real_keycloak_auth() as auth:
        token = await auth.login("alice", "password")
        # Real JWT token from Keycloak on port 9082
"""

import os
import httpx
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

# Import helper for worker-safe IDs
from tests.conftest import get_user_id


class RealKeycloakAuth:
    """Real Keycloak authentication client for E2E tests

    Connects to Keycloak test instance on port 9082.
    Uses password grant flow for user authentication.

    IMPORTANT: Keycloak is configured with KC_HTTP_RELATIVE_PATH=/authn
    All endpoints must be prefixed with /authn (e.g., /authn/realms/master/...)
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Keycloak auth client.

        Args:
            base_url: Keycloak base URL (default: http://localhost:9082/authn)
                      Note: Must include /authn path due to KC_HTTP_RELATIVE_PATH config
        """
        # Default includes /authn path per KC_HTTP_RELATIVE_PATH in docker-compose.test.yml
        self.base_url = base_url or os.getenv("KEYCLOAK_URL", "http://localhost:9082/authn")
        self.realm = os.getenv("KEYCLOAK_REALM", "master")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-server")
        # CODEX FINDING FIX (2025-11-20): Add client_secret for token introspection
        # Keycloak requires client authentication for introspection endpoint
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "test-client-secret-for-e2e-tests")
        # S501: verify=False is intentional for e2e tests against local dev servers
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)  # noqa: S501 # nosec B501

    async def login(self, username: str, password: str) -> dict[str, str]:
        """
        Login user and get real JWT tokens from Keycloak.

        Args:
            username: User username
            password: User password

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.

        Raises:
            RuntimeError: If authentication fails (with specific error context)
        """
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": username,
            "password": password,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            response = await self.client.post(
                token_url,
                data=data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"Keycloak auth timeout after 30s at {self.base_url} - "
                f"service may be down or overloaded. "
                f"Check docker-compose services are running."
            ) from e
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to Keycloak at {self.base_url} - "
                f"service is not reachable. "
                f"Ensure docker-compose.test.yml is running: docker compose -f docker-compose.test.yml up -d"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Keycloak auth failed: {e.response.status_code} - {e.response.text[:200]} (URL: {token_url})"
            ) from e

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token, refresh_token, expires_in, etc.
        """
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = await self.client.post(
            token_url,
            data=data,
        )
        response.raise_for_status()

        return response.json()

    async def logout(self, refresh_token: str) -> None:
        """
        Logout user session.

        Args:
            refresh_token: Valid refresh token
        """
        logout_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/logout"

        await self.client.post(
            logout_url,
            data={
                "client_id": self.client_id,
                "refresh_token": refresh_token,
            },
        )

    async def introspect(self, token: str) -> dict[str, Any]:
        """
        Introspect token to get metadata.

        CODEX FINDING FIX (2025-11-20): Added client_secret for proper Keycloak authentication.
        Previous issue: Missing client_secret caused 403 Forbidden errors.

        Args:
            token: Access token to introspect

        Returns:
            Dict with token metadata (active, sub, username, etc.)

        Raises:
            httpx.HTTPStatusError: If introspection fails (e.g., 403 without client_secret)
        """
        introspect_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token/introspect"

        # Keycloak requires client authentication for introspection
        # Use client_secret if available, otherwise try public client introspection
        data = {
            "client_id": self.client_id,
            "token": token,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = await self.client.post(introspect_url, data=data)
        response.raise_for_status()

        return response.json()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class RealMCPClient:
    """Real MCP (Model Context Protocol) client for E2E tests

    Connects to MCP server test instance.
    Uses real HTTP/SSE transport for MCP protocol.
    """

    def __init__(self, base_url: str = None, access_token: str = None):
        """
        Initialize MCP client.

        Args:
            base_url: MCP server base URL (default: http://localhost:8000)
            access_token: Optional access token for authentication
        """
        self.base_url = base_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.access_token = access_token

        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # S501: verify=False is intentional for e2e tests against local dev servers
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0, verify=False)  # noqa: S501 # nosec B501

    async def initialize(self) -> dict[str, Any]:
        """
        Initialize MCP session.

        Returns:
            Dict with protocol_version, server_info, capabilities
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {},
            },
        }
        try:
            response = await self.client.post("/message", json=payload)
            response.raise_for_status()
            return response.json().get("result", {})

        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"MCP initialize timeout after 30s at {self.base_url} - server may be down or overloaded."
            ) from e
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to MCP server at {self.base_url} - service is not reachable. Check server is running."
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"MCP initialize failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def list_tools(self) -> dict[str, Any]:
        """
        List available tools.

        Returns:
            Dict with tools array
        """
        payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
        try:
            response = await self.client.post("/message", json=payload)
            response.raise_for_status()
            return response.json().get("result", {})

        except httpx.TimeoutException as e:
            raise RuntimeError(f"MCP list_tools timeout after 30s at {self.base_url}") from e
        except httpx.ConnectError as e:
            raise RuntimeError(f"Cannot connect to MCP server at {self.base_url} for list_tools") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"MCP list_tools failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call a tool.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Dict with tool result
        """
        # Ensure token is in arguments if available
        if self.access_token and "token" not in arguments:
            arguments["token"] = self.access_token

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        response = await self.client.post("/message", json=payload)
        response.raise_for_status()

        result = response.json().get("result", {})
        error = response.json().get("error")
        if error:
            raise RuntimeError(f"MCP call_tool failed: {error}")

        # MCP returns {content: [...]}
        return result

    async def create_conversation(self, user_id: str = "test-user") -> str:
        """
        Create a new conversation (Generate ID, actual creation is implicit).

        Args:
            user_id: User ID for conversation

        Returns:
            Conversation ID
        """
        import uuid

        return f"conv_{uuid.uuid4().hex[:8]}"

    async def send_message(self, conversation_id: str, content: str) -> dict[str, Any]:
        """
        Send message to conversation using agent_chat tool.

        Args:
            conversation_id: Conversation ID
            content: Message content

        Returns:
            Dict with message response
        """
        arguments = {
            "message": content,
            "thread_id": conversation_id,
            "user_id": get_user_id(),
        }
        if self.access_token:
            arguments["token"] = self.access_token

        result = await self.call_tool("agent_chat", arguments)
        return result

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """
        Get conversation details using conversation_get tool.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with conversation data
        """
        arguments = {"thread_id": conversation_id, "user_id": get_user_id("test")}
        if self.access_token:
            arguments["token"] = self.access_token

        result = await self.call_tool("conversation_get", arguments)
        return result

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


@asynccontextmanager
async def real_keycloak_auth(base_url: str = None) -> AsyncGenerator[RealKeycloakAuth, None]:
    """
    Context manager for RealKeycloakAuth.

    Usage:
        async with real_keycloak_auth() as auth:
            token = await auth.login("alice", "password")

    Args:
        base_url: Optional Keycloak base URL

    Yields:
        RealKeycloakAuth instance
    """
    auth = RealKeycloakAuth(base_url=base_url)
    try:
        yield auth
    finally:
        await auth.close()


@asynccontextmanager
async def real_mcp_client(base_url: str = None, access_token: str = None) -> AsyncGenerator[RealMCPClient, None]:
    """
    Context manager for RealMCPClient.

    Usage:
        async with real_mcp_client(access_token=token) as client:
            tools = await client.list_tools()

    Args:
        base_url: Optional MCP server base URL
        access_token: Optional access token for authentication

    Yields:
        RealMCPClient instance
    """
    client = RealMCPClient(base_url=base_url, access_token=access_token)
    try:
        yield client
    finally:
        await client.close()


# Backwards compatibility aliases
# These allow gradual migration from mock_ to real_ prefixes
MockKeycloakAuth = RealKeycloakAuth
MockMCPClient = RealMCPClient
mock_keycloak_auth = real_keycloak_auth
mock_mcp_client = real_mcp_client
