#!/usr/bin/env python3
"""
SAML Identity Provider Setup

Configures Keycloak to federate users from SAML identity providers (ADFS, Azure AD, etc.).
Users authenticate via SAML SSO, and Keycloak issues JWTs.

See ADR-0037 for identity federation architecture.

Usage:
    python setup_saml_idp.py

Environment Variables:
    KEYCLOAK_SERVER_URL: Keycloak server URL (default: http://localhost:8080)
    KEYCLOAK_ADMIN_USERNAME: Admin username (default: admin)
    KEYCLOAK_ADMIN_PASSWORD: Admin password (default: admin)
    KEYCLOAK_REALM: Realm name (default: langgraph-agent)

    SAML_ALIAS: Identity provider alias (required, e.g., 'adfs', 'azure-ad')
    SAML_DISPLAY_NAME: Display name (default: same as alias)
    SAML_SSO_URL: Single Sign-On Service URL (required)
    SAML_LOGOUT_URL: Single Logout Service URL (optional)
    SAML_ENTITY_ID: Entity ID (optional, defaults to SSO URL)
    SAML_NAME_ID_FORMAT: Name ID format (default: emailAddress)
"""

import asyncio
import os
import sys
from typing import Any

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

    async def create_identity_provider(self, realm: str, idp_config: dict[str, Any]):
        """Create identity provider"""
        if not self.access_token:
            await self.get_admin_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/admin/realms/{realm}/identity-provider/instances",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=idp_config,
            )

            if response.status_code == 409:
                print(f"Identity provider already exists: {idp_config['alias']}")
                return None

            response.raise_for_status()
            return response.json()

    async def create_identity_provider_mapper(self, realm: str, idp_alias: str, mapper_config: dict[str, Any]):
        """Create identity provider mapper"""
        if not self.access_token:
            await self.get_admin_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/admin/realms/{realm}/identity-provider/instances/{idp_alias}/mappers",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=mapper_config,
            )

            if response.status_code == 409:
                print(f"  Mapper already exists: {mapper_config['name']}")
                return None

            response.raise_for_status()
            return response.json()


async def configure_saml_identity_provider(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    saml_config: dict[str, str],
) -> str:
    """
    Configure SAML 2.0 identity provider

    Args:
        keycloak_admin: Keycloak admin client
        realm_name: Realm to configure
        saml_config: SAML configuration parameters

    Returns:
        Identity provider alias
    """
    alias = saml_config["alias"]
    display_name = saml_config.get("displayName", alias.upper())

    print(f"\nConfiguring SAML Identity Provider: {display_name}")
    print(f"Alias: {alias}")
    print(f"SSO URL: {saml_config['ssoUrl']}")

    idp_config = {
        "alias": alias,
        "displayName": display_name,
        "providerId": "saml",
        "enabled": True,
        "trustEmail": True,
        "storeToken": False,
        "addReadTokenRoleOnCreate": False,
        "firstBrokerLoginFlowAlias": "first broker login",
        "config": {
            # SAML endpoints
            "singleSignOnServiceUrl": saml_config["ssoUrl"],
            "singleLogoutServiceUrl": saml_config.get("logoutUrl", saml_config["ssoUrl"]),
            # Name ID
            "nameIDPolicyFormat": saml_config.get("nameIdFormat", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"),
            # Signature/encryption
            "signatureAlgorithm": "RSA_SHA256",
            "xmlSigKeyInfoKeyNameTransformer": "KEY_ID",
            "validateSignature": "true",
            "wantAuthnRequestsSigned": saml_config.get("signRequests", "false"),
            # Binding
            "postBindingResponse": "true",
            "postBindingAuthnRequest": "true",
            "postBindingLogout": "true",
            # Principal type
            "principalType": "SUBJECT",
            # Entity ID
            "entityId": saml_config.get("entityId", saml_config["ssoUrl"]),
            # Backchannel logout
            "backchannelSupported": "false",
        },
    }

    await keycloak_admin.create_identity_provider(realm_name, idp_config)
    print(f"✓ SAML identity provider '{alias}' configured")

    return alias


async def configure_saml_attribute_mappers(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    idp_alias: str,
):
    """
    Configure SAML attribute mappers

    Maps SAML assertion attributes to Keycloak user attributes.
    """
    print(f"\nConfiguring SAML attribute mappers for '{idp_alias}'...")

    mappers = [
        {
            "name": "email",
            "mapperType": "saml-user-attribute-idp-mapper",
            "samlAttribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "userAttribute": "email",
        },
        {
            "name": "firstName",
            "mapperType": "saml-user-attribute-idp-mapper",
            "samlAttribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
            "userAttribute": "firstName",
        },
        {
            "name": "lastName",
            "mapperType": "saml-user-attribute-idp-mapper",
            "samlAttribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
            "userAttribute": "lastName",
        },
        {
            "name": "groups",
            "mapperType": "saml-role-idp-mapper",
            "samlAttribute": "http://schemas.xmlsoap.org/claims/Group",
            "role": "",  # Maps to Keycloak roles
        },
    ]

    for mapper_def in mappers:
        mapper_config = {
            "name": mapper_def["name"],
            "identityProviderAlias": idp_alias,
            "identityProviderMapper": mapper_def["mapperType"],
            "config": {
                "attribute.name": mapper_def["samlAttribute"],
                "user.attribute": mapper_def.get("userAttribute", ""),
                "role": mapper_def.get("role", ""),
                "syncMode": "INHERIT",
            },
        }

        await keycloak_admin.create_identity_provider_mapper(realm_name, idp_alias, mapper_config)
        print(f"  ✓ Mapper configured: {mapper_def['name']}")


async def main():
    """Main function"""
    print("=" * 70)
    print(" " * 15 + "SAML Identity Provider Setup")
    print("=" * 70)

    # Get configuration from environment
    keycloak_url = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
    admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    realm_name = os.getenv("KEYCLOAK_REALM", "langgraph-agent")

    # SAML configuration (required)
    saml_alias = os.getenv("SAML_ALIAS")
    saml_sso_url = os.getenv("SAML_SSO_URL")

    if not all([saml_alias, saml_sso_url]):
        print("\nERROR: Missing required SAML configuration")
        print("Required environment variables:")
        print("  - SAML_ALIAS (e.g., 'adfs', 'azure-ad')")
        print("  - SAML_SSO_URL (e.g., 'https://adfs.example.com/adfs/ls/')")
        print("\nOptional:")
        print("  - SAML_DISPLAY_NAME")
        print("  - SAML_LOGOUT_URL")
        print("  - SAML_ENTITY_ID")
        print("  - SAML_NAME_ID_FORMAT")
        sys.exit(1)

    saml_config = {
        "alias": saml_alias,
        "displayName": os.getenv("SAML_DISPLAY_NAME", saml_alias.upper()),
        "ssoUrl": saml_sso_url,
        "logoutUrl": os.getenv("SAML_LOGOUT_URL"),
        "entityId": os.getenv("SAML_ENTITY_ID"),
        "nameIdFormat": os.getenv("SAML_NAME_ID_FORMAT"),
        "signRequests": os.getenv("SAML_SIGN_REQUESTS", "false"),
    }

    try:
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient(
            server_url=keycloak_url,
            admin_username=admin_username,
            admin_password=admin_password,
        )

        # Configure SAML identity provider
        await configure_saml_identity_provider(keycloak_admin, realm_name, saml_config)

        # Configure attribute mappers
        await configure_saml_attribute_mappers(keycloak_admin, realm_name, saml_alias)

        print("\n" + "=" * 70)
        print("✓ SAML identity provider setup completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Import SAML metadata in Keycloak Admin Console")
        print(f"   - Identity Providers → {saml_alias} → Import from URL/file")
        print("2. Test SAML SSO flow")
        print("3. Verify attribute mapping")
        print("4. Configure account linking if needed")
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
