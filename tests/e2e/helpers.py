"""
E2E Test Helpers and HTTP Mocks

Provides lightweight HTTP mocks for E2E tests until full infrastructure is implemented.
This follows the recommendation to "swap to HTTP mocks" for rapid E2E test activation.

Usage:
    from tests.e2e.helpers import mock_keycloak_auth, mock_mcp_client

    async with mock_keycloak_auth() as auth:
        token = await auth.login("user", "password")
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import httpx


class MockKeycloakAuth:
    """Mock Keycloak authentication for E2E tests"""

    def __init__(self):
        self.users = {}
        self.tokens = {}

    async def login(self, username: str, password: str) -> Dict[str, str]:
        """Mock login that returns JWT tokens"""
        # Simulate successful login
        access_token = f"mock_access_token_{username}"
        refresh_token = f"mock_refresh_token_{username}"

        self.tokens[username] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 900,
            "refresh_expires_in": 1800,
            "token_type": "Bearer"
        }

        return self.tokens[username]

    async def refresh(self, refresh_token: str) -> Dict[str, str]:
        """Mock token refresh"""
        # Extract username from mock token
        username = refresh_token.replace("mock_refresh_token_", "")

        if username in self.tokens:
            # Generate new tokens
            new_access = f"mock_access_token_{username}_refreshed"
            new_refresh = f"mock_refresh_token_{username}_refreshed"

            self.tokens[username] = {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "expires_in": 900,
                "refresh_expires_in": 1800,
                "token_type": "Bearer"
            }

            return self.tokens[username]

        raise ValueError("Invalid refresh token")

    async def logout(self, refresh_token: str) -> None:
        """Mock logout"""
        username = refresh_token.replace("mock_refresh_token_", "")
        if username in self.tokens:
            del self.tokens[username]

    async def introspect(self, token: str) -> Dict[str, Any]:
        """Mock token introspection"""
        # Check if token exists
        for username, token_data in self.tokens.items():
            if token == token_data["access_token"]:
                return {
                    "active": True,
                    "sub": username,
                    "username": username,
                    "email": f"{username}@test.com",
                    "exp": 9999999999,
                    "iat": 1000000000
                }

        return {"active": False}


class MockMCPClient:
    """Mock MCP (Model Context Protocol) client for E2E tests"""

    def __init__(self):
        self.tools = [
            {"name": "get_weather", "description": "Get weather for a location"},
            {"name": "search_web", "description": "Search the web"},
            {"name": "calculate", "description": "Perform calculations"}
        ]
        self.conversations = {}

    async def initialize(self) -> Dict[str, Any]:
        """Mock MCP initialization"""
        return {
            "protocol_version": "2024-11-05",
            "server_info": {
                "name": "mcp-server-langgraph",
                "version": "2.8.0"
            },
            "capabilities": {
                "tools": True,
                "prompts": True,
                "resources": False
            }
        }

    async def list_tools(self) -> Dict[str, Any]:
        """Mock tool listing"""
        return {"tools": self.tools}

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool invocation"""
        if name not in [t["name"] for t in self.tools]:
            raise ValueError(f"Tool {name} not found")

        # Simulate tool execution
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Mock result for {name} with args {arguments}"
                }
            ]
        }

    async def create_conversation(self, user_id: str) -> str:
        """Mock conversation creation"""
        conv_id = f"conv_{len(self.conversations) + 1}"
        self.conversations[conv_id] = {
            "id": conv_id,
            "user_id": user_id,
            "messages": []
        }
        return conv_id

    async def send_message(self, conv_id: str, message: str) -> Dict[str, Any]:
        """Mock message sending"""
        if conv_id not in self.conversations:
            raise ValueError(f"Conversation {conv_id} not found")

        self.conversations[conv_id]["messages"].append({
            "role": "user",
            "content": message
        })

        # Mock AI response
        response = f"Mock AI response to: {message}"
        self.conversations[conv_id]["messages"].append({
            "role": "assistant",
            "content": response
        })

        return {
            "role": "assistant",
            "content": response
        }

    async def get_conversation(self, conv_id: str) -> Dict[str, Any]:
        """Mock conversation retrieval"""
        if conv_id not in self.conversations:
            raise ValueError(f"Conversation {conv_id} not found")

        return self.conversations[conv_id]

    async def search_conversations(self, user_id: str, query: str = None) -> list:
        """Mock conversation search"""
        results = []
        for conv_id, conv in self.conversations.items():
            if conv["user_id"] == user_id:
                if query is None or query.lower() in str(conv).lower():
                    results.append({
                        "id": conv_id,
                        "user_id": user_id,
                        "message_count": len(conv["messages"])
                    })
        return results


@asynccontextmanager
async def mock_keycloak_auth() -> AsyncGenerator[MockKeycloakAuth, None]:
    """Context manager for mock Keycloak authentication"""
    auth = MockKeycloakAuth()
    try:
        yield auth
    finally:
        # Cleanup
        auth.users.clear()
        auth.tokens.clear()


@asynccontextmanager
async def mock_mcp_client() -> AsyncGenerator[MockMCPClient, None]:
    """Context manager for mock MCP client"""
    client = MockMCPClient()
    try:
        yield client
    finally:
        # Cleanup
        client.conversations.clear()


async def mock_api_request(
    method: str,
    url: str,
    headers: Dict[str, str] = None,
    json: Dict[str, Any] = None
) -> httpx.Response:
    """
    Mock API request for testing without actual HTTP calls.

    This allows E2E tests to validate logic without running infrastructure.
    """
    # Mock common endpoints
    if "/api/v1/api-keys" in url:
        if method == "POST":
            return httpx.Response(
                status_code=201,
                json={
                    "key_id": "mock_key_123",
                    "api_key": "mcp_mock_key_xyz",
                    "name": json.get("name", "Test Key"),
                    "created": "2024-01-01T00:00:00Z",
                    "expires_at": "2025-01-01T00:00:00Z"
                }
            )
        elif method == "GET":
            return httpx.Response(
                status_code=200,
                json=[
                    {
                        "key_id": "mock_key_123",
                        "name": "Test Key",
                        "created": "2024-01-01T00:00:00Z",
                        "expires_at": "2025-01-01T00:00:00Z"
                    }
                ]
            )

    elif "/api/v1/service-principals" in url:
        if method == "POST":
            return httpx.Response(
                status_code=201,
                json={
                    "service_id": "mock_sp_123",
                    "name": json.get("name", "Test SP"),
                    "client_secret": "mock_secret_xyz",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            )
        elif method == "GET":
            return httpx.Response(
                status_code=200,
                json=[
                    {
                        "service_id": "mock_sp_123",
                        "name": "Test SP",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ]
            )

    elif "/api/v1/users" in url and "/export" in url:
        # GDPR export endpoint
        return httpx.Response(
            status_code=200,
            json={
                "user_id": "test_user",
                "personal_data": {"name": "Test User", "email": "test@example.com"},
                "conversations": [],
                "api_keys": []
            }
        )

    # Default mock response
    return httpx.Response(status_code=404, json={"error": "Not found"})
