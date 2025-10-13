#!/usr/bin/env python3
"""
Example usage of Keycloak authentication

Demonstrates:
- User authentication with Keycloak
- Token verification
- Token refresh
- Role synchronization to OpenFGA
- User provider pattern
"""

import asyncio

from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig, sync_user_to_openfga
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.user_provider import KeycloakUserProvider, create_user_provider
from mcp_server_langgraph.core.config import settings


async def demo_keycloak_authentication():
    """
    Demonstrate Keycloak authentication flows
    """
    print("\n" + "=" * 70)
    print("Keycloak Authentication Demo")
    print("=" * 70)

    # Check if Keycloak is configured
    if not settings.keycloak_client_secret:
        print("\n⚠️  Keycloak not fully configured!")
        print("Run: make setup-keycloak")
        print("Then update your .env file with KEYCLOAK_CLIENT_SECRET")
        return

    # Create Keycloak configuration
    keycloak_config = KeycloakConfig(
        server_url=settings.keycloak_server_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
        admin_username=settings.keycloak_admin_username,
        admin_password=settings.keycloak_admin_password,
        verify_ssl=settings.keycloak_verify_ssl,
        timeout=settings.keycloak_timeout,
    )

    print("\n1. Testing Direct Keycloak Client")
    print("-" * 70)

    keycloak_client = KeycloakClient(keycloak_config)

    # Authenticate user
    print("Authenticating user 'alice'...")
    try:
        tokens = await keycloak_client.authenticate_user("alice", "alice123")
        print(f"✓ Authentication successful!")
        print(f"  Access token (first 50 chars): {tokens['access_token'][:50]}...")
        print(f"  Token expires in: {tokens.get('expires_in')} seconds")

        # Verify token
        print("\nVerifying access token...")
        payload = await keycloak_client.verify_token(tokens["access_token"])
        print(f"✓ Token verified!")
        print(f"  Subject: {payload.get('sub')}")
        print(f"  Username: {payload.get('preferred_username')}")
        print(f"  Email: {payload.get('email')}")

        # Get user info
        print("\nGetting user info...")
        userinfo = await keycloak_client.get_userinfo(tokens["access_token"])
        print(f"✓ User info retrieved!")
        print(f"  Email verified: {userinfo.get('email_verified')}")

        # Refresh token
        if "refresh_token" in tokens:
            print("\nRefreshing access token...")
            new_tokens = await keycloak_client.refresh_token(tokens["refresh_token"])
            print(f"✓ Token refreshed!")
            print(f"  New access token (first 50 chars): {new_tokens['access_token'][:50]}...")

    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("\nMake sure:")
        print("  1. Keycloak is running (make setup-infra)")
        print("  2. Keycloak is initialized (make setup-keycloak)")
        print("  3. .env has KEYCLOAK_CLIENT_SECRET set")
        return

    print("\n2. Testing User Provider Pattern")
    print("-" * 70)

    # Create user provider
    user_provider = create_user_provider(
        provider_type="keycloak",
        keycloak_config=keycloak_config,
        openfga_client=None,  # Will add later
    )

    print("Authenticating via KeycloakUserProvider...")
    auth_result = await user_provider.authenticate("alice", "alice123")

    if auth_result.get("authorized"):
        print(f"✓ User authenticated!")
        print(f"  Username: {auth_result['username']}")
        print(f"  User ID: {auth_result['user_id']}")
        print(f"  Email: {auth_result['email']}")
        print(f"  Roles: {auth_result['roles']}")
    else:
        print(f"✗ Authentication failed: {auth_result.get('reason')}")

    # Get user by username
    print("\nGetting user details...")
    user_details = await user_provider.get_user_by_username("alice")
    if user_details:
        print(f"✓ User found!")
        print(f"  First name: {user_details.get('first_name')}")
        print(f"  Last name: {user_details.get('last_name')}")
        print(f"  Groups: {user_details.get('groups')}")

    print("\n3. Testing OpenFGA Integration")
    print("-" * 70)

    # Check if OpenFGA is configured
    if not settings.openfga_store_id or not settings.openfga_model_id:
        print("\n⚠️  OpenFGA not configured - skipping integration demo")
        print("Run: make setup-openfga")
    else:
        # Create OpenFGA client
        openfga_client = OpenFGAClient(
            api_url=settings.openfga_api_url, store_id=settings.openfga_store_id, model_id=settings.openfga_model_id
        )

        # Get full user details
        print("Fetching user details from Keycloak...")
        keycloak_user = await keycloak_client.get_user_by_username("alice")

        if keycloak_user:
            print(f"✓ User retrieved!")
            print(f"  User ID: {keycloak_user.user_id}")
            print(f"  Realm roles: {keycloak_user.realm_roles}")
            print(f"  Client roles: {keycloak_user.client_roles}")
            print(f"  Groups: {keycloak_user.groups}")

            # Sync to OpenFGA
            print("\nSyncing roles to OpenFGA...")
            await sync_user_to_openfga(keycloak_user, openfga_client)
            print(f"✓ Roles synchronized to OpenFGA!")

            # Verify permissions
            print("\nVerifying permissions via OpenFGA...")

            # Check if user can execute tools
            can_execute = await openfga_client.check_permission(
                user=keycloak_user.user_id, relation="executor", object="tool:chat"
            )
            print(f"  Can execute tool:chat: {can_execute}")

            # List accessible tools
            accessible_tools = await openfga_client.list_objects(
                user=keycloak_user.user_id, relation="executor", object_type="tool"
            )
            print(f"  Accessible tools: {accessible_tools}")

    print("\n4. Testing AuthMiddleware with Keycloak")
    print("-" * 70)

    # Create AuthMiddleware with Keycloak provider
    openfga_client = None
    if settings.openfga_store_id and settings.openfga_model_id:
        openfga_client = OpenFGAClient(
            api_url=settings.openfga_api_url, store_id=settings.openfga_store_id, model_id=settings.openfga_model_id
        )

    keycloak_provider = KeycloakUserProvider(config=keycloak_config, openfga_client=openfga_client, sync_on_login=True)

    auth = AuthMiddleware(secret_key=settings.jwt_secret_key, openfga_client=openfga_client, user_provider=keycloak_provider)

    # Authenticate
    print("Authenticating 'bob' via AuthMiddleware...")
    result = await auth.authenticate("bob", "bob123")

    if result.get("authorized"):
        print(f"✓ Authentication successful!")
        print(f"  User ID: {result['user_id']}")

        # Authorize (if OpenFGA available)
        if openfga_client:
            authorized = await auth.authorize(user_id=result["user_id"], relation="executor", resource="tool:chat")
            print(f"  Authorized to execute tool:chat: {authorized}")
    else:
        print(f"✗ Authentication failed: {result.get('reason')}")

    print("\n5. Comparing Providers")
    print("-" * 70)

    # InMemory provider
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    inmemory_provider = InMemoryUserProvider(secret_key=settings.jwt_secret_key)

    print("InMemory provider (development):")
    inmemory_result = await inmemory_provider.authenticate("alice")
    print(f"  Alice in InMemory: {inmemory_result.get('authorized')}")

    print("\nKeycloak provider (production):")
    keycloak_result = await keycloak_provider.authenticate("alice", "alice123")
    print(f"  Alice in Keycloak: {keycloak_result.get('authorized')}")

    print("\n" + "=" * 70)
    print("✓ Demo completed!")
    print("=" * 70)

    print("\n📊 Key Takeaways:")
    print(
        """
    1. Keycloak provides production-ready user management
    2. User provider pattern allows switching between backends
    3. Keycloak tokens are verified using JWKS (no shared secret)
    4. Roles automatically sync to OpenFGA for authorization
    5. Token refresh extends session without re-authentication
    6. Development uses InMemory, production uses Keycloak

    Switching providers in .env:
    - Development: AUTH_PROVIDER=inmemory
    - Production:  AUTH_PROVIDER=keycloak
    """
    )


if __name__ == "__main__":
    asyncio.run(demo_keycloak_authentication())
