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
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

import httpx


class RealKeycloakAuth:
    """Real Keycloak authentication client for E2E tests

    Connects to Keycloak test instance on port 9082.
    Uses password grant flow for user authentication.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Keycloak auth client.

        Args:
            base_url: Keycloak base URL (default: http://localhost:9082)
        """
        self.base_url = base_url or os.getenv("KEYCLOAK_URL", "http://localhost:9082")
        self.realm = os.getenv("KEYCLOAK_REALM", "master")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-server")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def login(self, username: str, password: str) -> Dict[str, str]:
        """
        Login user and get real JWT tokens from Keycloak.

        Args:
            username: User username
            password: User password

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.

        Raises:
            httpx.HTTPError: If authentication fails
        """
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        response = await self.client.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": self.client_id,
                "username": username,
                "password": password,
            },
        )
        response.raise_for_status()

        return response.json()

    async def refresh(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token, refresh_token, expires_in, etc.
        """
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        response = await self.client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": refresh_token,
            },
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

    async def introspect(self, token: str) -> Dict[str, Any]:
        """
        Introspect token to get metadata.

        Args:
            token: Access token to introspect

        Returns:
            Dict with token metadata (active, sub, username, etc.)
        """
        introspect_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token/introspect"

        response = await self.client.post(
            introspect_url,
            data={
                "client_id": self.client_id,
                "token": token,
            },
        )
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

        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize MCP session.

        Returns:
            Dict with protocol_version, server_info, capabilities
        """
        response = await self.client.post("/mcp/initialize", json={"protocol_version": "2024-11-05"})
        response.raise_for_status()

        return response.json()

    async def list_tools(self) -> Dict[str, Any]:
        """
        List available tools.

        Returns:
            Dict with tools array
        """
        response = await self.client.get("/mcp/tools/list")
        response.raise_for_status()

        return response.json()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Dict with tool result
        """
        response = await self.client.post(
            "/mcp/tools/call",
            json={
                "name": tool_name,
                "arguments": arguments,
            },
        )
        response.raise_for_status()

        return response.json()

    async def create_conversation(self, user_id: str = "test-user") -> str:
        """
        Create a new conversation.

        Args:
            user_id: User ID for conversation

        Returns:
            Conversation ID
        """
        response = await self.client.post(
            "/conversations",
            json={
                "user_id": user_id,
                "title": "E2E Test Conversation",
            },
        )
        response.raise_for_status()

        data = response.json()
        return data["conversation_id"]

    async def send_message(self, conversation_id: str, content: str) -> Dict[str, Any]:
        """
        Send message to conversation.

        Args:
            conversation_id: Conversation ID
            content: Message content

        Returns:
            Dict with message response
        """
        response = await self.client.post(
            f"/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": content,
            },
        )
        response.raise_for_status()

        return response.json()

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation details.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with conversation data
        """
        response = await self.client.get(f"/conversations/{conversation_id}")
        response.raise_for_status()

        return response.json()

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
