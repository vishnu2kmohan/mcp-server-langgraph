"""
Example client for testing the MCP agent server with OpenFGA and Infisical
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.config import settings


async def test_chat():
    """Test the chat functionality with OpenFGA authorization"""

    print("\n" + "=" * 60)
    print("Testing MCP Server with OpenFGA")
    print("=" * 60)

    # Create auth tokens
    auth = AuthMiddleware(secret_key=settings.jwt_secret_key)

    alice_token = auth.create_token("alice")
    bob_token = auth.create_token("bob")

    print("\n✓ Auth tokens created:")
    print(f"   Alice: {alice_token[:30]}...")
    print(f"   Bob: {bob_token[:30]}...")

    # Server parameters
    server_params = StdioServerParameters(command="python", args=["mcp_server.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("\nAvailable tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Test 1: Chat without auth (should fail)
            print("\n--- Test 1: Chat without auth (should fail) ---")
            try:
                response = await session.call_tool("chat", arguments={"message": "What is the capital of France?"})
                print("   ✗ Unexpected success!")
            except Exception as e:
                print(f"   ✓ Expected error: {e}")

            # Test 2: Alice chats (should succeed)
            print("\n--- Test 2: Alice sends a message ---")
            try:
                response = await session.call_tool(
                    "chat",
                    arguments={
                        "message": "Explain quantum computing in simple terms",
                        "thread_id": "thread_1",
                        "username": "alice",
                    },
                )
                print(f"   ✓ Response: {response.content[0].text[:150]}...")
            except Exception as e:
                print(f"   ✗ Error: {e}")

            # Test 3: Bob chats (should succeed)
            print("\n--- Test 3: Bob sends a message ---")
            try:
                response = await session.call_tool(
                    "chat",
                    arguments={
                        "message": "What are the best practices for API design?",
                        "thread_id": "thread_2",
                        "username": "bob",
                    },
                )
                print(f"   ✓ Response: {response.content[0].text[:150]}...")
            except Exception as e:
                print(f"   ✗ Error: {e}")

            # Test 4: Alice retrieves her conversation
            print("\n--- Test 4: Alice retrieves conversation:thread_1 ---")
            try:
                response = await session.call_tool(
                    "get_conversation", arguments={"thread_id": "thread_1", "username": "alice"}
                )
                print(f"   ✓ Response: {response.content[0].text}")
            except Exception as e:
                print(f"   ✗ Error: {e}")

            # Test 5: Bob tries to access Alice's conversation (should succeed as viewer)
            print("\n--- Test 5: Bob views conversation:thread_1 (as viewer) ---")
            try:
                response = await session.call_tool("get_conversation", arguments={"thread_id": "thread_1", "username": "bob"})
                print(f"   ✓ Response: {response.content[0].text}")
            except Exception as e:
                print(f"   ✗ Error: {e}")

            # Test 6: List conversations
            print("\n--- Test 6: Alice lists her conversations ---")
            try:
                response = await session.call_tool("list_conversations", arguments={"username": "alice"})
                print(f"   ✓ Response: {response.content[0].text}")
            except Exception as e:
                print(f"   ✗ Error: {e}")

            # Test 7: Unauthorized user
            print("\n--- Test 7: Unknown user attempts access ---")
            try:
                response = await session.call_tool(
                    "chat", arguments={"message": "Hello", "thread_id": "thread_1", "username": "unknown_user"}
                )
                print("   ✗ Unexpected success!")
            except Exception as e:
                print(f"   ✓ Expected error: {e}")


async def test_auth():
    """Test authentication and authorization"""
    auth = AuthMiddleware()

    print("\n--- Authentication Tests ---")

    # Test valid user
    result = await auth.authenticate("user_123")
    print(f"Auth user_123: {result}")

    # Test invalid user
    result = await auth.authenticate("invalid_user")
    print(f"Auth invalid_user: {result}")

    # Test authorization
    print("\n--- Authorization Tests ---")

    can_chat = await auth.authorize("user_123", "tool:chat")
    print(f"user_123 can use chat: {can_chat}")

    can_admin = await auth.authorize("user_123", "admin:delete")
    print(f"user_123 can use admin:delete: {can_admin}")

    admin_can = await auth.authorize("admin_456", "admin:delete")
    print(f"admin_456 can use admin:delete: {admin_can}")

    # Test token creation and verification
    print("\n--- Token Tests ---")

    token = auth.create_token("user_123", expires_in=3600)
    print(f"Created token: {token[:30]}...")

    verify_result = auth.verify_token(token)
    print(f"Token verification: {verify_result}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP Server with LangGraph - Example Client")
    print("=" * 60)

    # Test authentication first
    await test_auth()

    # Then test the full MCP integration
    print("\n" + "=" * 60)
    print("Testing MCP Server Integration")
    print("=" * 60)
    # Uncomment to test with running server:
    # await test_chat()


if __name__ == "__main__":
    asyncio.run(main())
