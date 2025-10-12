#!/usr/bin/env python3
"""
Setup script for OpenFGA authorization model and sample data
"""
import asyncio

from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store, seed_sample_data
from mcp_server_langgraph.core.config import settings


async def setup_openfga():
    """Initialize OpenFGA with authorization model and sample data"""
    print("\n" + "=" * 60)
    print("OpenFGA Setup")
    print("=" * 60)

    # Create client
    print(f"\n1. Connecting to OpenFGA at {settings.openfga_api_url}...")
    client = OpenFGAClient(api_url=settings.openfga_api_url)

    # Initialize store and model
    print("\n2. Creating authorization store and model...")
    try:
        store_id = await initialize_openfga_store(client)
        print(f"   ✓ Store created: {store_id}")
        print(f"   ✓ Model created: {client.model_id}")

        # Save to environment
        print("\n3. Update your .env file with:")
        print(f"   OPENFGA_STORE_ID={store_id}")
        print(f"   OPENFGA_MODEL_ID={client.model_id}")

    except Exception as e:
        print(f"   ✗ Failed to initialize store: {e}")
        return

    # Seed sample data
    print("\n4. Seeding sample relationship data...")
    try:
        await seed_sample_data(client)
        print("   ✓ Sample data seeded")
    except Exception as e:
        print(f"   ✗ Failed to seed data: {e}")
        return

    # Verify with some checks
    print("\n5. Verifying authorization checks...")
    test_cases = [
        {"user": "user:alice", "relation": "executor", "object": "tool:chat", "expected": True},
        {"user": "user:bob", "relation": "executor", "object": "tool:chat", "expected": True},
        {"user": "user:alice", "relation": "owner", "object": "conversation:thread_1", "expected": True},
        {"user": "user:bob", "relation": "owner", "object": "conversation:thread_1", "expected": False},
        {"user": "user:bob", "relation": "viewer", "object": "conversation:thread_1", "expected": True},
    ]

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        try:
            result = await client.check_permission(user=test["user"], relation=test["relation"], object=test["object"])

            status = "✓" if result == test["expected"] else "✗"
            if result != test["expected"]:
                all_passed = False

            print(f"   {status} Test {i}: {test['user']} can {test['relation']} {test['object']}: {result}")

        except Exception as e:
            print(f"   ✗ Test {i} failed: {e}")
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ OpenFGA setup completed successfully!")
    else:
        print("✗ Some tests failed. Please review the output above.")
    print("=" * 60)

    # Show relationship examples
    print("\n📋 Sample Relationships Created:")
    print(
        """
    Organizations:
      - user:alice is member of organization:acme
      - user:alice is admin of organization:acme
      - user:bob is member of organization:acme

    Tools:
      - user:alice can execute tool:chat
      - user:bob can execute tool:chat
      - organization:acme has access to tool:chat

    Conversations:
      - user:alice owns conversation:thread_1
      - user:bob can view conversation:thread_1

    Roles:
      - user:alice has role:premium
      - user:bob has role:standard
    """
    )

    print("\n🔧 Next Steps:")
    print("1. Update .env with the store_id and model_id shown above")
    print("2. Run: python example_client.py")
    print("3. Check authorization in action!")
    print()


if __name__ == "__main__":
    asyncio.run(setup_openfga())
