#!/usr/bin/env python3
"""
Keycloak setup script

Initializes Keycloak with:
- Realm creation
- Client configuration
- Default users (alice, bob, admin)
- Role mappings
- OpenFGA tuple synchronization (optional)
"""

import asyncio
import sys
from typing import Optional

import httpx

from mcp_server_langgraph.core.config import settings


async def wait_for_keycloak(server_url: str, max_retries: int = 30, delay: int = 2) -> bool:
    """
    Wait for Keycloak to be ready

    Args:
        server_url: Keycloak server URL
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds

    Returns:
        True if Keycloak is ready, False otherwise
    """
    print(f"Waiting for Keycloak at {server_url}...")

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(verify=False, timeout=5) as client:
                response = await client.get(f"{server_url}/health/ready")
                if response.status_code == 200:
                    print("✓ Keycloak is ready!")
                    return True
        except Exception:
            pass

        print(f"  Attempt {attempt + 1}/{max_retries}... (waiting {delay}s)")
        await asyncio.sleep(delay)

    print("✗ Keycloak not ready after maximum retries")
    return False


async def setup_realm(server_url: str, admin_username: str, admin_password: str, realm_name: str) -> bool:
    """
    Create Keycloak realm

    Args:
        server_url: Keycloak server URL
        admin_username: Admin username
        admin_password: Admin password
        realm_name: Realm name to create

    Returns:
        True if successful
    """
    print(f"\nCreating realm: {realm_name}")

    try:
        # Get admin token
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Get admin token
            token_url = f"{server_url}/realms/master/protocol/openid-connect/token"
            token_data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": admin_username,
                "password": admin_password,
            }

            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            admin_token = token_response.json()["access_token"]

            headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

            # Check if realm exists
            realms_url = f"{server_url}/admin/realms"
            realms_response = await client.get(realms_url, headers=headers)
            existing_realms = [r["realm"] for r in realms_response.json()]

            if realm_name in existing_realms:
                print(f"  Realm '{realm_name}' already exists")
                return True

            # Create realm
            realm_config = {
                "realm": realm_name,
                "enabled": True,
                "displayName": "LangGraph Agent",
                "registrationAllowed": False,
                "resetPasswordAllowed": True,
                "rememberMe": True,
                "verifyEmail": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "sslRequired": "external",
                "accessTokenLifespan": 900,  # 15 minutes
                "refreshTokenMaxReuse": 0,
                "ssoSessionIdleTimeout": 1800,  # 30 minutes
                "ssoSessionMaxLifespan": 36000,  # 10 hours
            }

            create_response = await client.post(realms_url, headers=headers, json=realm_config)
            create_response.raise_for_status()

            print(f"✓ Realm '{realm_name}' created successfully")
            return True

    except Exception as e:
        print(f"✗ Failed to create realm: {e}")
        return False


async def setup_client(
    server_url: str, admin_username: str, admin_password: str, realm_name: str, client_id: str
) -> Optional[str]:
    """
    Create Keycloak client

    Args:
        server_url: Keycloak server URL
        admin_username: Admin username
        admin_password: Admin password
        realm_name: Realm name
        client_id: Client ID to create

    Returns:
        Client secret if successful, None otherwise
    """
    print(f"\nCreating client: {client_id}")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Get admin token
            token_url = f"{server_url}/realms/master/protocol/openid-connect/token"
            token_data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": admin_username,
                "password": admin_password,
            }

            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            admin_token = token_response.json()["access_token"]

            headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

            # Check if client exists
            clients_url = f"{server_url}/admin/realms/{realm_name}/clients"
            clients_response = await client.get(clients_url, headers=headers)
            existing_clients = {c["clientId"]: c["id"] for c in clients_response.json()}

            if client_id in existing_clients:
                print(f"  Client '{client_id}' already exists")
                # Get client secret
                client_uuid = existing_clients[client_id]
                secret_url = f"{clients_url}/{client_uuid}/client-secret"
                secret_response = await client.get(secret_url, headers=headers)
                client_secret = secret_response.json().get("value")
                return client_secret

            # Create client
            client_config = {
                "clientId": client_id,
                "name": "LangGraph Agent Client",
                "description": "OAuth2/OIDC client for LangGraph MCP Agent",
                "enabled": True,
                "publicClient": False,
                "protocol": "openid-connect",
                "directAccessGrantsEnabled": True,  # Enable ROPC flow
                "serviceAccountsEnabled": False,
                "standardFlowEnabled": True,  # Enable authorization code flow
                "implicitFlowEnabled": False,
                "redirectUris": ["http://localhost:8000/*", "http://localhost:3000/*"],
                "webOrigins": ["http://localhost:8000", "http://localhost:3000"],
                "attributes": {"access.token.lifespan": "900"},
            }

            create_response = await client.post(clients_url, headers=headers, json=client_config)
            create_response.raise_for_status()

            # Get the created client ID
            clients_response = await client.get(clients_url, headers=headers)
            client_uuid = None
            for c in clients_response.json():
                if c["clientId"] == client_id:
                    client_uuid = c["id"]
                    break

            if not client_uuid:
                print("✗ Failed to get client UUID")
                return None

            # Get client secret
            secret_url = f"{clients_url}/{client_uuid}/client-secret"
            secret_response = await client.get(secret_url, headers=headers)
            client_secret = secret_response.json().get("value")

            print(f"✓ Client '{client_id}' created successfully")
            print(f"  Client Secret: {client_secret}")

            return client_secret

    except Exception as e:
        print(f"✗ Failed to create client: {e}")
        return None


async def create_user(
    server_url: str,
    admin_username: str,
    admin_password: str,
    realm_name: str,
    username: str,
    email: str,
    password: str,
    roles: list,
):
    """Create a user in Keycloak"""
    print(f"\nCreating user: {username}")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Get admin token
            token_url = f"{server_url}/realms/master/protocol/openid-connect/token"
            token_data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": admin_username,
                "password": admin_password,
            }

            token_response = await client.post(token_url, data=token_data)
            admin_token = token_response.json()["access_token"]

            headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

            # Check if user exists
            users_url = f"{server_url}/admin/realms/{realm_name}/users"
            search_response = await client.get(users_url, headers=headers, params={"username": username, "exact": "true"})

            if search_response.json():
                print(f"  User '{username}' already exists")
                return True

            # Create user
            user_config = {
                "username": username,
                "email": email,
                "enabled": True,
                "emailVerified": True,
                "firstName": username.capitalize(),
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            }

            create_response = await client.post(users_url, headers=headers, json=user_config)
            create_response.raise_for_status()

            # Get user ID
            search_response = await client.get(users_url, headers=headers, params={"username": username, "exact": "true"})
            user_id = search_response.json()[0]["id"]

            # Assign roles
            for role in roles:
                await assign_realm_role(client, headers, server_url, realm_name, user_id, role)

            print(f"✓ User '{username}' created successfully")
            return True

    except Exception as e:
        print(f"✗ Failed to create user {username}: {e}")
        return False


async def create_realm_role(
    http_client: httpx.AsyncClient, headers: dict, server_url: str, realm_name: str, role_name: str
) -> bool:
    """Create a realm role"""
    try:
        roles_url = f"{server_url}/admin/realms/{realm_name}/roles"

        # Check if role exists
        search_response = await http_client.get(f"{roles_url}/{role_name}", headers=headers)
        if search_response.status_code == 200:
            return True

        # Create role
        role_config = {"name": role_name, "description": f"Role: {role_name}"}
        create_response = await http_client.post(roles_url, headers=headers, json=role_config)
        create_response.raise_for_status()
        return True

    except Exception:
        return False


async def assign_realm_role(
    http_client: httpx.AsyncClient, headers: dict, server_url: str, realm_name: str, user_id: str, role_name: str
):
    """Assign realm role to user"""
    try:
        # Ensure role exists
        await create_realm_role(http_client, headers, server_url, realm_name, role_name)

        # Get role details
        roles_url = f"{server_url}/admin/realms/{realm_name}/roles/{role_name}"
        role_response = await http_client.get(roles_url, headers=headers)
        role_data = role_response.json()

        # Assign role to user
        assign_url = f"{server_url}/admin/realms/{realm_name}/users/{user_id}/role-mappings/realm"
        await http_client.post(assign_url, headers=headers, json=[role_data])

        print(f"  Assigned role: {role_name}")

    except Exception as e:
        print(f"  Failed to assign role {role_name}: {e}")


async def create_group(
    server_url: str, admin_username: str, admin_password: str, realm_name: str, group_name: str, members: list
):
    """Create a group in Keycloak"""
    print(f"\nCreating group: {group_name}")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Get admin token
            token_url = f"{server_url}/realms/master/protocol/openid-connect/token"
            token_data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": admin_username,
                "password": admin_password,
            }

            token_response = await client.post(token_url, data=token_data)
            admin_token = token_response.json()["access_token"]

            headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

            # Create group
            groups_url = f"{server_url}/admin/realms/{realm_name}/groups"
            group_config = {"name": group_name}

            create_response = await client.post(groups_url, headers=headers, json=group_config)

            if create_response.status_code not in [201, 409]:
                create_response.raise_for_status()

            # Get group ID
            groups_response = await client.get(groups_url, headers=headers)
            group_id = None
            for g in groups_response.json():
                if g["name"] == group_name:
                    group_id = g["id"]
                    break

            if not group_id:
                print(f"✗ Failed to get group ID for {group_name}")
                return False

            # Add members
            users_url = f"{server_url}/admin/realms/{realm_name}/users"
            for member_username in members:
                search_response = await client.get(
                    users_url, headers=headers, params={"username": member_username, "exact": "true"}
                )
                if search_response.json():
                    user_id = search_response.json()[0]["id"]
                    member_url = f"{users_url}/{user_id}/groups/{group_id}"
                    await client.put(member_url, headers=headers)
                    print(f"  Added member: {member_username}")

            print(f"✓ Group '{group_name}' created successfully")
            return True

    except Exception as e:
        print(f"✗ Failed to create group {group_name}: {e}")
        return False


async def main():
    """Main setup function"""
    print("=" * 70)
    print("Keycloak Setup Script")
    print("=" * 70)

    # Configuration
    server_url = settings.keycloak_server_url
    realm_name = settings.keycloak_realm
    client_id = settings.keycloak_client_id
    admin_username = settings.keycloak_admin_username
    admin_password = settings.keycloak_admin_password

    if not admin_password:
        print("✗ KEYCLOAK_ADMIN_PASSWORD not set")
        print("  Set it in .env or environment variables")
        return 1

    # Wait for Keycloak
    if not await wait_for_keycloak(server_url):
        return 1

    # Setup realm
    if not await setup_realm(server_url, admin_username, admin_password, realm_name):
        return 1

    # Setup client
    client_secret = await setup_client(server_url, admin_username, admin_password, realm_name, client_id)
    if not client_secret:
        return 1

    # Create users
    users = [
        {"username": "alice", "email": "alice@acme.com", "password": "alice123", "roles": ["user", "premium"]},
        {"username": "bob", "email": "bob@acme.com", "password": "bob123", "roles": ["user"]},
        {"username": "admin", "email": "admin@acme.com", "password": "admin123", "roles": ["admin"]},
    ]

    for user in users:
        await create_user(
            server_url,
            admin_username,
            admin_password,
            realm_name,
            user["username"],
            user["email"],
            user["password"],
            user["roles"],
        )

    # Create groups
    await create_group(server_url, admin_username, admin_password, realm_name, "acme", ["alice", "bob"])

    # Print summary
    print("\n" + "=" * 70)
    print("✓ Keycloak setup completed successfully!")
    print("=" * 70)
    print("\nConfiguration for .env file:")
    print("-" * 70)
    print(f"KEYCLOAK_SERVER_URL={server_url}")
    print(f"KEYCLOAK_REALM={realm_name}")
    print(f"KEYCLOAK_CLIENT_ID={client_id}")
    print(f"KEYCLOAK_CLIENT_SECRET={client_secret}")
    print()
    print("Add these to your .env file, then restart the agent.")
    print("\nTest users (password same as username + '123'):")
    print("- alice (premium user, member of acme)")
    print("- bob (standard user, member of acme)")
    print("- admin (admin user)")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
