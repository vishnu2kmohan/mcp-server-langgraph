#!/usr/bin/env python3
"""
OIDC Identity Provider Setup

Configures Keycloak to federate users from OIDC providers
(Google, Microsoft, GitHub, Okta, OneLogin, etc.).

See ADR-0037 for identity federation architecture.

Usage:
    python setup_oidc_idp.py --provider google
    python setup_oidc_idp.py --provider microsoft
    python setup_oidc_idp.py --provider github
    python setup_oidc_idp.py --provider okta
    python setup_oidc_idp.py --provider custom

Environment Variables:
    KEYCLOAK_SERVER_URL: Keycloak server URL (default: http://localhost:8080)
    KEYCLOAK_ADMIN_USERNAME: Admin username (default: admin)
    KEYCLOAK_ADMIN_PASSWORD: Admin password (default: admin)
    KEYCLOAK_REALM: Realm name (default: langgraph-agent)

Provider-specific (replace PROVIDER with google, microsoft, github, okta):
    {PROVIDER}_CLIENT_ID: OAuth2 client ID (required)
    {PROVIDER}_CLIENT_SECRET: OAuth2 client secret (required)
    {PROVIDER}_HOSTED_DOMAIN: Restrict to specific domain (optional, for Google)
    {PROVIDER}_TENANT_ID: Tenant ID (optional, for Microsoft)
"""

import asyncio
import os
import sys
import argparse
from typing import Dict, Any

import httpx


PROVIDER_CONFIGS = {
    "google": {
        "providerId": "google",
        "displayName": "Google",
        "defaultScope": "openid profile email",
    },
    "microsoft": {
        "providerId": "microsoft",
        "displayName": "Microsoft",
        "defaultScope": "openid profile email",
    },
    "github": {
        "providerId": "github",
        "displayName": "GitHub",
        "defaultScope": "user:email",
    },
    "okta": {
        "providerId": "oidc",
        "displayName": "Okta",
        "defaultScope": "openid profile email",
    },
    "onelogin": {
        "providerId": "oidc",
        "displayName": "OneLogin",
        "defaultScope": "openid profile email",
    },
}


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

    async def create_identity_provider(
        self, realm: str, idp_config: Dict[str, Any]
    ):
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

    async def create_identity_provider_mapper(
        self, realm: str, idp_alias: str, mapper_config: Dict[str, Any]
    ):
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


async def configure_google_identity_provider(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    client_id: str,
    client_secret: str,
    hosted_domain: str = None,
) -> str:
    """Configure Google Workspace / Gmail identity provider"""
    print(f"\nConfiguring Google Identity Provider")

    idp_config = {
        "alias": "google",
        "displayName": "Google",
        "providerId": "google",
        "enabled": True,
        "trustEmail": True,
        "config": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "defaultScope": "openid profile email",
            "hostedDomain": hosted_domain or "",  # Restrict to specific Google Workspace domain
        },
    }

    await keycloak_admin.create_identity_provider(realm_name, idp_config)
    print(f"✓ Google identity provider configured")

    return "google"


async def configure_microsoft_identity_provider(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    client_id: str,
    client_secret: str,
    tenant_id: str = "common",
) -> str:
    """Configure Microsoft 365 / Azure AD identity provider"""
    print(f"\nConfiguring Microsoft Identity Provider")
    print(f"Tenant ID: {tenant_id}")

    idp_config = {
        "alias": "microsoft",
        "displayName": "Microsoft",
        "providerId": "microsoft",
        "enabled": True,
        "trustEmail": True,
        "config": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "defaultScope": "openid profile email",
        },
    }

    await keycloak_admin.create_identity_provider(realm_name, idp_config)
    print(f"✓ Microsoft identity provider configured")

    return "microsoft"


async def configure_github_identity_provider(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Configure GitHub identity provider"""
    print(f"\nConfiguring GitHub Identity Provider")

    idp_config = {
        "alias": "github",
        "displayName": "GitHub",
        "providerId": "github",
        "enabled": True,
        "trustEmail": False,  # GitHub emails may not be verified
        "config": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "defaultScope": "user:email",
        },
    }

    await keycloak_admin.create_identity_provider(realm_name, idp_config)
    print(f"✓ GitHub identity provider configured")

    return "github"


async def configure_okta_identity_provider(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    client_id: str,
    client_secret: str,
    okta_domain: str,
) -> str:
    """Configure Okta identity provider"""
    print(f"\nConfiguring Okta Identity Provider")
    print(f"Okta Domain: {okta_domain}")

    idp_config = {
        "alias": "okta",
        "displayName": "Okta",
        "providerId": "oidc",
        "enabled": True,
        "trustEmail": True,
        "config": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "defaultScope": "openid profile email",
            "authorizationUrl": f"https://{okta_domain}/oauth2/v1/authorize",
            "tokenUrl": f"https://{okta_domain}/oauth2/v1/token",
            "userInfoUrl": f"https://{okta_domain}/oauth2/v1/userinfo",
            "jwksUrl": f"https://{okta_domain}/oauth2/v1/keys",
            "issuer": f"https://{okta_domain}",
            "validateSignature": "true",
            "useJwksUrl": "true",
        },
    }

    await keycloak_admin.create_identity_provider(realm_name, idp_config)
    print(f"✓ Okta identity provider configured")

    return "okta"


async def configure_oidc_attribute_mappers(
    keycloak_admin: KeycloakAdminClient,
    realm_name: str,
    idp_alias: str,
):
    """Configure OIDC attribute mappers"""
    print(f"\nConfiguring OIDC attribute mappers for '{idp_alias}'...")

    mappers = [
        {
            "name": "email",
            "claim": "email",
            "userAttribute": "email",
        },
        {
            "name": "firstName",
            "claim": "given_name",
            "userAttribute": "firstName",
        },
        {
            "name": "lastName",
            "claim": "family_name",
            "userAttribute": "lastName",
        },
        {
            "name": "username",
            "claim": "preferred_username",
            "userAttribute": "username",
        },
    ]

    for mapper_def in mappers:
        mapper_config = {
            "name": mapper_def["name"],
            "identityProviderAlias": idp_alias,
            "identityProviderMapper": "oidc-user-attribute-idp-mapper",
            "config": {
                "claim": mapper_def["claim"],
                "user.attribute": mapper_def["userAttribute"],
                "syncMode": "INHERIT",
            },
        }

        await keycloak_admin.create_identity_provider_mapper(
            realm_name, idp_alias, mapper_config
        )
        print(f"  ✓ Mapper configured: {mapper_def['name']}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Setup OIDC identity provider in Keycloak")
    parser.add_argument(
        "--provider",
        choices=["google", "microsoft", "github", "okta", "onelogin"],
        required=True,
        help="Identity provider to configure",
    )
    args = parser.parse_args()

    provider = args.provider

    print("=" * 70)
    print(f" " * 15 + f"{provider.upper()} Identity Provider Setup")
    print("=" * 70)

    # Get configuration from environment
    keycloak_url = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
    admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    realm_name = os.getenv("KEYCLOAK_REALM", "langgraph-agent")

    # Provider-specific configuration
    client_id = os.getenv(f"{provider.upper()}_CLIENT_ID")
    client_secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        print(f"\nERROR: Missing required {provider.upper()} configuration")
        print("Required environment variables:")
        print(f"  - {provider.upper()}_CLIENT_ID")
        print(f"  - {provider.upper()}_CLIENT_SECRET")

        if provider == "google":
            print("\nOptional:")
            print("  - GOOGLE_HOSTED_DOMAIN (restrict to specific domain)")
        elif provider == "microsoft":
            print("\nOptional:")
            print("  - MICROSOFT_TENANT_ID (default: common)")
        elif provider == "okta":
            print("\nRequired:")
            print("  - OKTA_DOMAIN (e.g., 'example.okta.com')")

        sys.exit(1)

    try:
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient(
            server_url=keycloak_url,
            admin_username=admin_username,
            admin_password=admin_password,
        )

        # Configure identity provider based on type
        if provider == "google":
            hosted_domain = os.getenv("GOOGLE_HOSTED_DOMAIN")
            idp_alias = await configure_google_identity_provider(
                keycloak_admin, realm_name, client_id, client_secret, hosted_domain
            )

        elif provider == "microsoft":
            tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
            idp_alias = await configure_microsoft_identity_provider(
                keycloak_admin, realm_name, client_id, client_secret, tenant_id
            )

        elif provider == "github":
            idp_alias = await configure_github_identity_provider(
                keycloak_admin, realm_name, client_id, client_secret
            )

        elif provider == "okta":
            okta_domain = os.getenv("OKTA_DOMAIN")
            if not okta_domain:
                print("ERROR: OKTA_DOMAIN environment variable required")
                sys.exit(1)
            idp_alias = await configure_okta_identity_provider(
                keycloak_admin, realm_name, client_id, client_secret, okta_domain
            )

        # Configure attribute mappers
        await configure_oidc_attribute_mappers(
            keycloak_admin, realm_name, idp_alias
        )

        print("\n" + "=" * 70)
        print(f"✓ {provider.upper()} identity provider setup completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print(f"1. Test {provider} SSO flow")
        print(f"2. Verify attribute mapping")
        print(f"3. Configure account linking if needed")
        print(f"4. Test JWT issuance after {provider} login")
        print("=" * 70)

        return 0

    except httpx.HTTPError as e:
        print(f"\nHTTP ERROR: {e}")
        if hasattr(e, 'response'):
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
