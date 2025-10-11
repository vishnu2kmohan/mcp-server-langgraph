#!/usr/bin/env python3
"""
Example client for MCP StreamableHTTP transport
"""
import asyncio
import json

import httpx


class MCPStreamableClient:
    """Simple MCP StreamableHTTP client"""

    def __init__(self, url: str, auth_token: str | None = None):
        self.url = url
        self.headers = {"Content-Type": "application/json"}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    async def send_message(self, method: str, params: dict | None = None, message_id: int = 1):
        """Send a JSON-RPC message to the MCP server"""
        message = {"jsonrpc": "2.0", "method": method, "id": message_id}
        if params:
            message["params"] = params

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, json=message, headers=self.headers, timeout=30.0)
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
        """Call a tool"""
        params = {"name": name, "arguments": arguments}

        if streaming:
            async for chunk in self.send_streaming_message("tools/call", params):
                yield chunk
        else:
            result = await self.send_message("tools/call", params)
            yield result

    async def list_resources(self):
        """List available resources"""
        return await self.send_message("resources/list")


async def main():
    """Example usage"""
    print("=" * 60)
    print("MCP StreamableHTTP Client Example")
    print("=" * 60)
    print()

    # Create client
    client = MCPStreamableClient(
        url="https://mcp.langgraph-agent.example.com/message",
        # auth_token="your-jwt-token"  # Uncomment for auth
    )

    # Initialize session
    print("1. Initializing session...")
    try:
        init_response = await client.initialize()
        print(f"   ✓ Connected to: {init_response['result']['serverInfo']['name']}")
        print(f"   Version: {init_response['result']['serverInfo']['version']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print()

    # List tools
    print("2. Listing tools...")
    try:
        tools_response = await client.list_tools()
        tools = tools_response["result"]["tools"]
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool['name']}: {tool['description'][:60]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # Call tool (non-streaming)
    print("3. Calling tool (non-streaming)...")
    try:
        async for response in client.call_tool("chat", {"message": "What is 2+2?", "username": "alice"}, streaming=False):
            content = response["result"]["content"][0]["text"]
            print(f"   ✓ Response: {content[:100]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # Call tool (streaming)
    print("4. Calling tool (streaming)...")
    try:
        async for chunk in client.call_tool(
            "chat", {"message": "Explain quantum computing", "username": "alice"}, streaming=True
        ):
            if "result" in chunk:
                content = chunk["result"]["content"][0]["text"]
                print(f"   ✓ Streaming response: {content[:100]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()

    # List resources
    print("5. Listing resources...")
    try:
        resources_response = await client.list_resources()
        resources = resources_response["result"]["resources"]
        print(f"   ✓ Found {len(resources)} resources:")
        for resource in resources:
            print(f"      - {resource['name']} ({resource['uri']})")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print()
    print("=" * 60)
    print("✓ Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
