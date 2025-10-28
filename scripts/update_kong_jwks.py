#!/usr/bin/env python3
"""
Kong JWKS Updater Script

Fetches JWKS from Keycloak and updates Kong JWT plugin with the current public key.
Runs as a Kubernetes CronJob every 6 hours to handle key rotation.

See ADR-0035 for Kong JWT validation strategy.

Usage:
    python update_kong_jwks.py

Environment Variables:
    KEYCLOAK_URL: Keycloak base URL (default: http://keycloak:8080)
    KEYCLOAK_REALM: Keycloak realm (default: langgraph-agent)
    KONG_ADMIN_URL: Kong Admin API URL (default: http://kong-admin:8001)
    KONG_CONSUMER: Kong consumer name (default: keycloak-users)
"""

import os
import sys
import asyncio
import base64
import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "langgraph-agent")
KONG_ADMIN_URL = os.getenv("KONG_ADMIN_URL", "http://kong-admin:8001")
KONG_CONSUMER = os.getenv("KONG_CONSUMER", "keycloak-users")


async def fetch_jwks():
    """Fetch JWKS from Keycloak"""
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

    print(f"Fetching JWKS from: {jwks_url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        return response.json()


def jwk_to_pem(jwk):
    """Convert JWK to PEM format"""
    # Decode base64url encoded components
    def b64url_decode(data):
        # Add padding if necessary
        data += "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(data)

    n = int.from_bytes(b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(b64url_decode(jwk["e"]), "big")

    # Create RSA public key
    public_numbers = rsa.RSAPublicNumbers(e, n)
    public_key = public_numbers.public_key(default_backend())

    # Export to PEM format
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return pem.decode("utf-8")


async def update_kong_jwt_credential(kid, pem, issuer):
    """Update Kong JWT credential with new public key"""
    url = f"{KONG_ADMIN_URL}/consumers/{KONG_CONSUMER}/jwt"

    print(f"Updating Kong JWT credential for consumer: {KONG_CONSUMER}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # List existing JWT credentials
        response = await client.get(url)
        response.raise_for_status()
        credentials = response.json().get("data", [])

        # Check if credential exists
        existing_cred = None
        for cred in credentials:
            if cred.get("key") == issuer:
                existing_cred = cred
                break

        # Prepare credential data
        credential_data = {
            "key": issuer,
            "algorithm": "RS256",
            "rsa_public_key": pem,
        }

        if existing_cred:
            # Update existing credential
            cred_id = existing_cred["id"]
            update_url = f"{url}/{cred_id}"
            print(f"Updating existing JWT credential: {cred_id}")
            response = await client.patch(update_url, json=credential_data)
        else:
            # Create new credential
            print("Creating new JWT credential")
            response = await client.post(url, json=credential_data)

        response.raise_for_status()
        print("✓ Kong JWT credential updated successfully")
        return response.json()


async def main():
    """Main function"""
    try:
        print("=" * 60)
        print("Kong JWKS Updater")
        print("=" * 60)

        # 1. Fetch JWKS from Keycloak
        jwks = await fetch_jwks()
        keys = jwks.get("keys", [])

        if not keys:
            print("ERROR: No keys found in JWKS")
            sys.exit(1)

        print(f"Found {len(keys)} keys in JWKS")

        # 2. Find RS256 key (first one)
        rs256_key = None
        for key in keys:
            if key.get("alg") == "RS256" and key.get("use") == "sig":
                rs256_key = key
                break

        if not rs256_key:
            print("ERROR: No RS256 signing key found in JWKS")
            sys.exit(1)

        kid = rs256_key["kid"]
        print(f"Using key ID: {kid}")

        # 3. Convert JWK to PEM
        pem = jwk_to_pem(rs256_key)
        print(f"Converted JWK to PEM format ({len(pem)} bytes)")

        # 4. Update Kong
        issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        await update_kong_jwt_credential(kid, pem, issuer)

        print("=" * 60)
        print("✓ JWKS update completed successfully")
        print("=" * 60)

        return 0

    except httpx.HTTPError as e:
        print(f"HTTP ERROR: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        return 1

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
