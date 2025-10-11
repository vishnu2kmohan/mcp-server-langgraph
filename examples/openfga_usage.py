#!/usr/bin/env python3
"""
Example usage of OpenFGA authorization in the agent
"""
import asyncio

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.auth.openfga import OpenFGAClient


async def demo_authorization():
    """Demonstrate OpenFGA authorization checks"""

    print("\n" + "=" * 60)
    print("OpenFGA Authorization Demo")
    print("=" * 60)

    # Create OpenFGA client
    if not settings.openfga_store_id or not settings.openfga_model_id:
        print("\n⚠️  OpenFGA not configured!")
        print("Run: python setup_openfga.py")
        print("Then update your .env file with OPENFGA_STORE_ID and OPENFGA_MODEL_ID")
        return

    client = OpenFGAClient(
        api_url=settings.openfga_api_url, store_id=settings.openfga_store_id, model_id=settings.openfga_model_id
    )

    # Create auth middleware with OpenFGA
    auth = AuthMiddleware(secret_key=settings.jwt_secret_key, openfga_client=client)

    print("\n1. Testing Tool Access")
    print("-" * 60)

    # Test alice's access to chat tool
    result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")
    print(f"   Alice can execute tool:chat: {result}")

    # Test bob's access
    result = await auth.authorize(user_id="user:bob", relation="executor", resource="tool:chat")
    print(f"   Bob can execute tool:chat: {result}")

    # Test unauthorized access
    result = await auth.authorize(user_id="user:charlie", relation="executor", resource="tool:chat")
    print(f"   Charlie can execute tool:chat: {result}")

    print("\n2. Testing Conversation Access")
    print("-" * 60)

    # Alice owns conversation:thread_1
    result = await auth.authorize(user_id="user:alice", relation="owner", resource="conversation:thread_1")
    print(f"   Alice owns conversation:thread_1: {result}")

    result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:thread_1")
    print(f"   Alice can edit conversation:thread_1: {result}")

    # Bob can view but not own
    result = await auth.authorize(user_id="user:bob", relation="viewer", resource="conversation:thread_1")
    print(f"   Bob can view conversation:thread_1: {result}")

    result = await auth.authorize(user_id="user:bob", relation="owner", resource="conversation:thread_1")
    print(f"   Bob owns conversation:thread_1: {result}")

    print("\n3. Listing Accessible Resources")
    print("-" * 60)

    # List tools Alice can execute
    tools = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")
    print(f"   Tools Alice can execute: {tools}")

    # List conversations Bob can view
    conversations = await auth.list_accessible_resources(user_id="user:bob", relation="viewer", resource_type="conversation")
    print(f"   Conversations Bob can view: {conversations}")

    print("\n4. Organization-Based Access")
    print("-" * 60)

    # Both Alice and Bob are members of organization:acme
    # The tool:chat is associated with organization:acme
    # So both should have access through organization membership

    result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")
    print(f"   Alice (via org:acme) can execute tool:chat: {result}")

    result = await auth.authorize(user_id="user:bob", relation="executor", resource="tool:chat")
    print(f"   Bob (via org:acme) can execute tool:chat: {result}")

    print("\n5. Adding New Relationships")
    print("-" * 60)

    # Grant Charlie access to a specific conversation
    new_tuples = [{"user": "user:charlie", "relation": "viewer", "object": "conversation:thread_2"}]

    await client.write_tuples(new_tuples)
    print("   ✓ Granted Charlie viewer access to conversation:thread_2")

    # Verify the access
    result = await auth.authorize(user_id="user:charlie", relation="viewer", resource="conversation:thread_2")
    print(f"   Charlie can view conversation:thread_2: {result}")

    print("\n6. Expanding Relationships")
    print("-" * 60)

    # See who has access to a resource
    expansion = await client.expand_relation(relation="executor", object="tool:chat")

    print("   Users with executor access to tool:chat:")
    print(f"   {expansion}")

    print("\n" + "=" * 60)
    print("✓ Demo completed!")
    print("=" * 60)

    print("\n📊 Key Takeaways:")
    print(
        """
    1. OpenFGA provides fine-grained, relationship-based authorization
    2. Permissions are defined through tuples (user, relation, object)
    3. Relationships can be direct or inherited (e.g., via organizations)
    4. You can list all resources a user has access to
    5. Permissions can be granted/revoked dynamically
    6. Authorization checks are fast and scalable

    This enables:
    - Multi-tenant applications
    - Complex permission hierarchies
    - Audit trails of access
    - Dynamic permission management
    """
    )


if __name__ == "__main__":
    asyncio.run(demo_authorization())
