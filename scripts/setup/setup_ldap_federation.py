#!/usr/bin/env python3
"""
LDAP/Active Directory Federation Setup

Configures Keycloak to federate users from LDAP or Active Directory.
Users authenticate against LDAP, and Keycloak issues JWTs.

See ADR-0037 for identity federation architecture.

Usage:
    python setup_ldap_federation.py

Environment Variables:
    KEYCLOAK_SERVER_URL: Keycloak server URL (default: http://localhost:8080)
    KEYCLOAK_ADMIN_USERNAME: Admin username (default: admin)
    KEYCLOAK_ADMIN_PASSWORD: Admin password (default: admin)
    KEYCLOAK_REALM: Realm name (default: langgraph-agent)

    LDAP_CONNECTION_URL: LDAP server URL (required)
    LDAP_BIND_DN: Service account DN for binding (required)
    LDAP_BIND_PASSWORD: Service account password (required)
    LDAP_USERS_DN: Base DN for user search (required)
    LDAP_USERNAME_ATTRIBUTE: Username attribute (default: sAMAccountName for AD, uid for LDAP)
    LDAP_USER_OBJECT_CLASSES: User object classes (default: person,organizationalPerson,user)
    LDAP_VENDOR: LDAP vendor (default: ad for Active Directory, other for generic LDAP)
"""

import asyncio
import os
import sys
from typing import Any, Dict, List

import httpx


class KeycloakAdminClient:
    """Simplified Keycloak Admin API client"""

    def __init__(self, server_url: str, admin_username: str, admin_password: str):
        self.server_url = server_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.access_token = None

    async def get_admin_token(self):
        """Get admin access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": self.admin_username,
                    "password": self.admin_password,
                },
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]

    async def create_component(self, realm: str, component_config: Dict[str, Any]):
        """Create a component (user federation provider)"""
        if not self.access_token:
            await self.get_admin_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/admin/realms/{realm}/components",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=component_config,
            )

            if response.status_code == 409:
                print(f"Component already exists: {component_config['name']}")
                return None

            response.raise_for_status()
            return response.json()


async def configure_ldap_user_federation(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    ldap_config: Dict[str, str],
) -> str:
    """
    Configure LDAP user federation

    Args:
        keycloak_admin: Keycloak admin client
        realm_name: Realm to configure
        ldap_config: LDAP configuration parameters

    Returns:
        Component ID
    """
    print(f"\nConfiguring LDAP User Federation for realm: {realm_name}")
    print(f"LDAP URL: {ldap_config['connectionUrl']}")

    component_config = {
        "name": ldap_config.get("name", "LDAP User Federation"),
        "providerId": "ldap",
        "providerType": "org.keycloak.storage.UserStorageProvider",
        "config": {
            # Connection settings
            "connectionUrl": [ldap_config["connectionUrl"]],
            "bindDn": [ldap_config["bindDn"]],
            "bindCredential": [ldap_config["bindPassword"]],
            # User search settings
            "usersDn": [ldap_config["usersDn"]],
            "searchScope": ["2"],  # 2 = SUBTREE
            "useTruststoreSpi": ["ldapsOnly"],
            "connectionPooling": ["true"],
            "connectionTimeout": ["10000"],  # 10 seconds
            "readTimeout": ["30000"],  # 30 seconds
            # User attributes
            "usernameLDAPAttribute": [ldap_config.get("usernameAttribute", "sAMAccountName")],
            "rdnLDAPAttribute": [ldap_config.get("rdnAttribute", "cn")],
            "uuidLDAPAttribute": [
                ldap_config.get("uuidAttribute", "objectGUID" if ldap_config.get("vendor") == "ad" else "entryUUID")
            ],
            "userObjectClasses": [ldap_config.get("userObjectClasses", "person,organizationalPerson,user")],
            # Sync settings
            "editMode": ["READ_ONLY"],  # Users managed in LDAP, not Keycloak
            "syncRegistrations": ["false"],
            "importEnabled": ["true"],
            "batchSizeForSync": ["1000"],
            "fullSyncPeriod": ["86400"],  # Daily full sync
            "changedSyncPeriod": ["3600"],  # Hourly changed sync
            "cachePolicy": ["DEFAULT"],
            # Vendor
            "vendor": [ldap_config.get("vendor", "ad")],
            # Authentication
            "authType": ["simple"],
            "validatePasswordPolicy": ["false"],
            "trustEmail": ["true"],
            # Pagination
            "pagination": ["true"],
        },
    }

    component_id = await keycloak_admin.create_component(realm_name, component_config)
    print(f"✓ LDAP user federation configured")

    return component_id


async def configure_ldap_attribute_mappers(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    parent_component_id: str,
):
    """
    Configure LDAP attribute mappers

    Maps LDAP attributes to Keycloak user attributes.
    """
    print("\nConfiguring LDAP attribute mappers...")

    mappers = [
        {
            "name": "email",
            "ldapAttribute": "mail",
            "userAttribute": "email",
            "readOnly": True,
            "alwaysReadValueFromLDAP": True,
        },
        {
            "name": "firstName",
            "ldapAttribute": "givenName",
            "userAttribute": "firstName",
            "readOnly": True,
            "alwaysReadValueFromLDAP": True,
        },
        {
            "name": "lastName",
            "ldapAttribute": "sn",
            "userAttribute": "lastName",
            "readOnly": True,
            "alwaysReadValueFromLDAP": True,
        },
        {
            "name": "department",
            "ldapAttribute": "department",
            "userAttribute": "department",
            "readOnly": True,
            "alwaysReadValueFromLDAP": False,
        },
        {
            "name": "title",
            "ldapAttribute": "title",
            "userAttribute": "title",
            "readOnly": True,
            "alwaysReadValueFromLDAP": False,
        },
    ]

    for mapper_def in mappers:
        mapper_config = {
            "name": mapper_def["name"],
            "providerId": "user-attribute-ldap-mapper",
            "providerType": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
            "parentId": parent_component_id,
            "config": {
                "ldap.attribute": [mapper_def["ldapAttribute"]],
                "user.model.attribute": [mapper_def["userAttribute"]],
                "read.only": [str(mapper_def["readOnly"]).lower()],
                "always.read.value.from.ldap": [str(mapper_def["alwaysReadValueFromLDAP"]).lower()],
                "is.mandatory.in.ldap": ["false"],
            },
        }

        await keycloak_admin.create_component(realm_name, mapper_config)
        print(f"  ✓ Mapper configured: {mapper_def['name']} ({mapper_def['ldapAttribute']} → {mapper_def['userAttribute']})")


async def configure_ldap_group_mapper(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    parent_component_id: str,
    groups_dn: str,
):
    """
    Configure LDAP group mapper

    Syncs LDAP groups to Keycloak groups.
    """
    print("\nConfiguring LDAP group mapper...")

    group_mapper_config = {
        "name": "group-mapper",
        "providerId": "group-ldap-mapper",
        "providerType": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
        "parentId": parent_component_id,
        "config": {
            "groups.dn": [groups_dn],
            "group.name.ldap.attribute": ["cn"],
            "group.object.classes": ["group"],
            "preserve.group.inheritance": ["true"],
            "membership.ldap.attribute": ["member"],
            "membership.attribute.type": ["DN"],
            "membership.user.ldap.attribute": ["distinguishedName"],
            "groups.path": ["/"],
            "mode": ["READ_ONLY"],
            "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
            "mapped.group.attributes": [""],
            "drop.non.existing.groups.during.sync": ["false"],
        },
    }

    await keycloak_admin.create_component(realm_name, group_mapper_config)
    print(f"  ✓ Group mapper configured for DN: {groups_dn}")


async def main():
    """Main function"""
    print("=" * 70)
    print(" " * 15 + "LDAP/AD Federation Setup")
    print("=" * 70)

    # Get configuration from environment
    keycloak_url = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
    admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    realm_name = os.getenv("KEYCLOAK_REALM", "langgraph-agent")

    # LDAP configuration (required)
    ldap_url = os.getenv("LDAP_CONNECTION_URL")
    ldap_bind_dn = os.getenv("LDAP_BIND_DN")
    ldap_bind_password = os.getenv("LDAP_BIND_PASSWORD")
    ldap_users_dn = os.getenv("LDAP_USERS_DN")

    if not all([ldap_url, ldap_bind_dn, ldap_bind_password, ldap_users_dn]):
        print("\nERROR: Missing required LDAP configuration")
        print("Required environment variables:")
        print("  - LDAP_CONNECTION_URL")
        print("  - LDAP_BIND_DN")
        print("  - LDAP_BIND_PASSWORD")
        print("  - LDAP_USERS_DN")
        print("\nExample:")
        print("  export LDAP_CONNECTION_URL='ldap://ad.example.com:389'")
        print("  export LDAP_BIND_DN='CN=Service Account,OU=Service Accounts,DC=example,DC=com'")
        print("  export LDAP_BIND_PASSWORD='password'")
        print("  export LDAP_USERS_DN='OU=Users,DC=example,DC=com'")
        sys.exit(1)

    ldap_config = {
        "name": os.getenv("LDAP_NAME", "Active Directory"),
        "connectionUrl": ldap_url,
        "bindDn": ldap_bind_dn,
        "bindPassword": ldap_bind_password,
        "usersDn": ldap_users_dn,
        "usernameAttribute": os.getenv("LDAP_USERNAME_ATTRIBUTE", "sAMAccountName"),
        "userObjectClasses": os.getenv("LDAP_USER_OBJECT_CLASSES", "person,organizationalPerson,user"),
        "vendor": os.getenv("LDAP_VENDOR", "ad"),
    }

    try:
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient(
            server_url=keycloak_url,
            admin_username=admin_username,
            admin_password=admin_password,
        )

        # Configure LDAP user federation
        component_id = await configure_ldap_user_federation(keycloak_admin, realm_name, ldap_config)

        if component_id:
            # Configure attribute mappers
            await configure_ldap_attribute_mappers(keycloak_admin, realm_name, component_id)

            # Configure group mapper if groups DN provided
            groups_dn = os.getenv("LDAP_GROUPS_DN")
            if groups_dn:
                await configure_ldap_group_mapper(keycloak_admin, realm_name, component_id, groups_dn)

        print("\n" + "=" * 70)
        print("✓ LDAP federation setup completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Test LDAP connection in Keycloak Admin Console")
        print("2. Run user sync: Users → Synchronize all users")
        print("3. Test login with LDAP user credentials")
        print("4. Verify JWT issuance and role mapping")
        print("=" * 70)

        return 0

    except httpx.HTTPError as e:
        print(f"\nHTTP ERROR: {e}")
        if hasattr(e, "response"):
            print(f"Status: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
