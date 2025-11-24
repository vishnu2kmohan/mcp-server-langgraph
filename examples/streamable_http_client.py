#!/usr/bin/env python3
"""
Example client for MCP StreamableHTTP transport with token-based authentication

This example demonstrates the secure authentication flow:
1. Login with username/password to get JWT token
2. Use token for all subsequent tool calls
"""

import asyncio
import datetime
import json

import httpx


class MCPStreamableClient:
    """
    MCP StreamableHTTP client with automatic token management

    Features:
    - Automatic login and token refresh
    - Secure token storage
    - Token expiration handling
    """

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        """
        Initialize client

        Args:
            base_url: Base URL of MCP server (e.g., http://localhost:8000)
            username: Username for authentication (optional for manual token management)
            password: Password for authentication (optional for manual token management)
        """
        self.base_url = base_url.rstrip("/")
        self.message_url = f"{self.base_url}/message"
        self.login_url = f"{self.base_url}/auth/login"

        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None

        self.headers = {"Content-Type": "application/json"}

    async def login(self, username: str | None = None, password: str | None = None):
        """
        Login and obtain JWT token

        Args:
            username: Username (uses instance default if not provided)
            password: Password (uses instance default if not provided)

        Returns:
            Login response with token and user info
        """
        username = username or self.username
        password = password or self.password

        if not username or not password:
            raise ValueError("Username and password required for login")

        async with httpx.AsyncClient() as client:
            response = await client.post(self.login_url, json={"username": username, "password": password}, timeout=10.0)
            response.raise_for_status()

            data = response.json()

            # Store token and calculate expiry
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            # Set expiry with 60s buffer
            self.token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in - 60)

            print(f"✓ Logged in as {data['username']} ({data['user_id']})")
            print(f"  Roles: {', '.join(data['roles'])}")
            print(f"  Token expires in {expires_in}s")

            return data

    async def refresh_token(self):
        """
        Refresh authentication token

        Uses /auth/refresh endpoint to get a new token without re-entering password.

        Returns:
            Refresh response with new token
        """
        if not self.token:
            raise ValueError("No current token to refresh. Call login() first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/auth/refresh", json={"current_token": self.token}, timeout=10.0)
            response.raise_for_status()

            data = response.json()

            # Store new token and calculate expiry
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            self.token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in - 60)

            print(f"⟳ Token refreshed (expires in {expires_in}s)")

            return data

    async def ensure_token(self):
        """Ensure we have a valid token (auto-refresh or auto-login if needed)"""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Refresh or login if token is missing or expired
        if not self.token or (self.token_expiry and now >= self.token_expiry):
            if self.token and self.username and self.password:
                # Try to refresh first (faster, doesn't require password)
                try:
                    await self.refresh_token()
                    return
                except Exception as refresh_error:
                    print(f"   Token refresh failed: {refresh_error}")
                    print("   Falling back to re-authentication...")

            # Fall back to login
            if not self.username or not self.password:
                raise ValueError("No valid token and no credentials for auto-login. Call login() first.")

            print("⟳ Re-authenticating...")
            await self.login()

    def set_token(self, token: str):
        """
        Manually set authentication token

        Use this if you obtained a token externally.

        Args:
            token: JWT token
        """
        self.token = token
        self.token_expiry = None  # Unknown expiry

    async def send_message(self, method: str, params: dict | None = None, message_id: int = 1, require_auth: bool = False):
        """
        Send a JSON-RPC message to the MCP server

        Args:
            method: MCP method name
            params: Method parameters
            message_id: JSON-RPC message ID
            require_auth: Whether to ensure valid token before sending

        Returns:
            JSON-RPC response
        """
        if require_auth:
            await self.ensure_token()

        message = {"jsonrpc": "2.0", "method": method, "id": message_id}
        if params:
            message["params"] = params

        async with httpx.AsyncClient() as client:
            response = await client.post(self.message_url, json=message, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def send_streaming_message(self, method: str, params: dict | None = None, message_id: int = 1):
        """Send a message and receive streaming response"""
        message = {"jsonrpc": "2.0", "method": method, "id": message_id}
        if params:
            message["params"] = params

        # Request streaming response
        headers = {**self.headers, "Accept": "application/x-ndjson"}

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self.url, json=message, headers=headers, timeout=30.0) as response:
                response.raise_for_status()

                # Read streaming response line by line
                async for line in response.aiter_lines():
                    if line.strip():
                        yield json.loads(line)

    async def initialize(self):
        """Initialize the MCP session"""
        return await self.send_message(
            "initialize", {"protocolVersion": "0.1.0", "clientInfo": {"name": "example-client", "version": "1.0.0"}}
        )

    async def list_tools(self):
        """List available tools"""
        return await self.send_message("tools/list")

    async def call_tool(self, name: str, arguments: dict, streaming: bool = False):
        """
        Call a tool with automatic token injection

        Args:
            name: Tool name
            arguments: Tool arguments (token will be added automatically)
            streaming: Whether to use streaming response

        Yields:
            Tool call response chunks
        """
        # Ensure we have a valid token
        await self.ensure_token()

        # Inject token into arguments
        arguments_with_token = {**arguments, "token": self.token}

        params = {"name": name, "arguments": arguments_with_token}

        if streaming:
            async for chunk in self.send_streaming_message("tools/call", params):
                yield chunk
        else:
            result = await self.send_message("tools/call", params)
            yield result

    async def list_resources(self):
        """List available resources"""
        return await self.send_message("resources/list")


async def main():  # noqa: C901
    """Example usage demonstrating token-based authentication"""
    print("=" * 70)
    print("MCP StreamableHTTP Client Example (v2.8.0+ with Token Auth)")
    print("=" * 70)
    print()

    # Create client with credentials for automatic token management
    print("0. Creating client...")
    client = MCPStreamableClient(
        base_url="http://localhost:8000",
        username="alice",  # Default user for development
        password="alice123",  # Default password for development
    )
    print("   ✓ Client created")
    print()

    # Login to get JWT token
    print("1. Authenticating...")
    try:
        login_data = await client.login()  # noqa: F841
        print()
    except Exception as e:
        print(f"   ✗ Login failed: {e}")
        print()
        print("   Make sure the server is running:")
        print("   python -m mcp_server_langgraph.mcp.server_streamable")
        return

    # Initialize MCP session
    print("2. Initializing MCP session...")
    try:
        init_response = await client.initialize()
        print(f"   ✓ Connected to: {init_response['result']['serverInfo']['name']}")
        print(f"   Version: {init_response['result']['serverInfo']['version']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print()

    # List tools
    print("3. Listing available tools...")
    try:
        tools_response = await client.list_tools()
        tools = tools_response["result"]["tools"]
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool['name']}")
            print(f"        {tool['description'][:65]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # Call tool (non-streaming) - token automatically included
    print("4. Calling agent_chat tool (non-streaming)...")
    try:
        async for response in client.call_tool(
            "agent_chat",
            {
                "message": "What is 2+2?",
                "user_id": "user:alice",
                "response_format": "concise",
                # Note: token is added automatically by call_tool()
            },
            streaming=False,
        ):
            content = response["result"]["content"][0]["text"]
            print(f"   ✓ Response: {content[:100]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # Call tool (streaming)
    print("5. Calling agent_chat tool (streaming)...")
    try:
        async for chunk in client.call_tool(
            "agent_chat",
            {"message": "Explain quantum computing in one sentence", "user_id": "user:alice", "response_format": "concise"},
            streaming=True,
        ):
            if "result" in chunk:
                content = chunk["result"]["content"][0]["text"]
                print(f"   ✓ Streaming chunk: {content[:100]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # Search conversations
    print("6. Searching conversations...")
    try:
        async for response in client.call_tool(
            "conversation_search", {"query": "quantum", "user_id": "user:alice", "limit": 5}, streaming=False
        ):
            content = response["result"]["content"][0]["text"]
            print(f"   ✓ Results: {content}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # List resources
    print("7. Listing resources...")
    try:
        resources_response = await client.list_resources()
        resources = resources_response["result"]["resources"]
        print(f"   ✓ Found {len(resources)} resources:")
        for resource in resources:
            print(f"      - {resource['name']} ({resource['uri']})")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()
    print("=" * 70)
    print("✓ Example complete!")
    print()
    print("Key takeaways:")
    print("  1. Login with username/password to get JWT token")
    print("  2. Token is automatically included in all tool calls")
    print("  3. Token is automatically refreshed when expired")
    print("  4. All MCP operations now require valid authentication")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
