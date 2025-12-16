#!/usr/bin/env python3
"""
OpenFGA Seeding Script for Test Infrastructure

This script runs as a Docker init container to automatically seed OpenFGA with:
1. Authorization store (creates if not exists)
2. Authorization model from config/openfga/model.json
3. Relationship tuples for test users (admin, alice, bob)

Usage:
    python scripts/docker/seed_openfga.py

Environment Variables:
    OPENFGA_API_URL: OpenFGA HTTP API URL (default: http://openfga:8080)
    OPENFGA_PRESHARED_KEY: Preshared key for authentication (deprecated, use OIDC)
    OPENFGA_OIDC_CLIENT_ID: OIDC client ID for authentication
    OPENFGA_OIDC_CLIENT_SECRET: OIDC client secret for authentication
    KEYCLOAK_SERVER_URL: Keycloak server URL (required for OIDC)
    KEYCLOAK_REALM: Keycloak realm (default: default)

Reference: ADR-0068 - Gateway-Level Authentication
Reference: ADR-0070 - OpenFGA OIDC Authentication Migration
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx

# Configuration
OPENFGA_API_URL = os.getenv("OPENFGA_API_URL", "http://openfga:8080")
OPENFGA_PRESHARED_KEY = os.getenv("OPENFGA_PRESHARED_KEY")

# OIDC Configuration (ADR-0070)
OPENFGA_OIDC_CLIENT_ID = os.getenv("OPENFGA_OIDC_CLIENT_ID")
OPENFGA_OIDC_CLIENT_SECRET = os.getenv("OPENFGA_OIDC_CLIENT_SECRET")
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "default")

STORE_NAME = "mcp-server-langgraph-test"
MODEL_PATH = Path("/app/config/openfga/model.json")
TUPLES_PATH = Path("/app/config/openfga/sample-tuples.json")
MAX_RETRIES = 30
RETRY_DELAY = 2

# Token cache (simple in-memory cache for script lifetime)
_oidc_token_cache: dict[str, str | int] = {}


def get_oidc_access_token() -> str | None:
    """
    Obtain OIDC access token from Keycloak using client credentials grant.

    Implements OAuth 2.0 client credentials grant (RFC 6749 Section 4.4)
    for service-to-service authentication.

    Returns:
        Access token string, or None if token acquisition fails
    """
    # Check cache first (with 60s buffer before expiration)
    if _oidc_token_cache.get("access_token") and _oidc_token_cache.get("expires_at"):
        if time.time() < (_oidc_token_cache["expires_at"] - 60):  # type: ignore
            return str(_oidc_token_cache["access_token"])

    # Validate required configuration
    if not all([KEYCLOAK_SERVER_URL, OPENFGA_OIDC_CLIENT_ID, OPENFGA_OIDC_CLIENT_SECRET]):
        print("✗ OIDC configuration incomplete (missing KEYCLOAK_SERVER_URL, CLIENT_ID, or CLIENT_SECRET)")
        return None

    # Construct token endpoint
    token_endpoint = f"{KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    try:
        # Request token via client credentials grant
        response = httpx.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": OPENFGA_OIDC_CLIENT_ID,
                "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )

        if response.status_code != 200:
            print(f"✗ Failed to obtain OIDC token: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            return None

        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            print("✗ No access_token in Keycloak token response")
            return None

        # Cache token with expiration time
        _oidc_token_cache["access_token"] = access_token
        _oidc_token_cache["expires_at"] = time.time() + expires_in

        print("✓ OIDC access token obtained")
        return access_token

    except Exception as e:
        print(f"✗ Error obtaining OIDC token: {e}")
        return None


def get_headers() -> dict[str, str]:
    """Get HTTP headers including auth if configured."""
    headers = {"Content-Type": "application/json"}

    # Prefer OIDC authentication (ADR-0070)
    if OPENFGA_OIDC_CLIENT_ID and OPENFGA_OIDC_CLIENT_SECRET:
        token = get_oidc_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            print("⚠ Failed to obtain OIDC token, requests may be rejected")
    # Fallback to preshared key (deprecated)
    elif OPENFGA_PRESHARED_KEY:
        headers["Authorization"] = f"Bearer {OPENFGA_PRESHARED_KEY}"

    return headers


def wait_for_openfga() -> bool:
    """Wait for OpenFGA to be ready."""
    print(f"Waiting for OpenFGA at {OPENFGA_API_URL}...")

    for attempt in range(MAX_RETRIES):
        try:
            # Health endpoint doesn't require auth
            response = httpx.get(f"{OPENFGA_API_URL}/healthz", timeout=5)
            if response.status_code == 200:
                print("✓ OpenFGA is ready")
                return True
        except Exception:
            pass

        print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: Waiting...")
        time.sleep(RETRY_DELAY)

    print("✗ OpenFGA did not become ready in time")
    return False


def get_or_create_store() -> str | None:
    """Get existing store or create a new one."""
    print(f"\nChecking for existing store '{STORE_NAME}'...")

    try:
        # List existing stores
        response = httpx.get(
            f"{OPENFGA_API_URL}/stores",
            headers=get_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            stores = response.json().get("stores", [])
            for store in stores:
                if store.get("name") == STORE_NAME:
                    store_id = store["id"]
                    print(f"✓ Found existing store: {store_id}")
                    return store_id

        # Create new store
        print(f"Creating new store '{STORE_NAME}'...")
        response = httpx.post(
            f"{OPENFGA_API_URL}/stores",
            headers=get_headers(),
            json={"name": STORE_NAME},
            timeout=10,
        )

        if response.status_code in [200, 201]:
            store_id = response.json()["id"]
            print(f"✓ Created store: {store_id}")
            return store_id
        else:
            print(f"✗ Failed to create store: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"✗ Error managing store: {e}")
        return None


def upload_authorization_model(store_id: str) -> str | None:
    """Upload authorization model from config file."""
    print(f"\nUploading authorization model from {MODEL_PATH}...")

    if not MODEL_PATH.exists():
        # Try alternative paths
        alt_paths = [
            Path("config/openfga/model.json"),
            Path("/config/openfga/model.json"),
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                model_path = alt_path
                break
        else:
            print(f"✗ Authorization model not found at {MODEL_PATH} or alternatives")
            return None
    else:
        model_path = MODEL_PATH

    try:
        with open(model_path) as f:
            model = json.load(f)

        response = httpx.post(
            f"{OPENFGA_API_URL}/stores/{store_id}/authorization-models",
            headers=get_headers(),
            json=model,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            model_id = response.json()["authorization_model_id"]
            print(f"✓ Uploaded authorization model: {model_id}")
            return model_id
        else:
            print(f"✗ Failed to upload model: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"✗ Error uploading model: {e}")
        return None


def load_tuples_from_config() -> list[dict[str, str]]:
    """Load relationship tuples from config file (single source of truth)."""
    tuples_path = TUPLES_PATH

    # Try alternative paths
    if not tuples_path.exists():
        alt_paths = [
            Path("config/openfga/sample-tuples.json"),
            Path("/config/openfga/sample-tuples.json"),
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                tuples_path = alt_path
                break
        else:
            print(f"✗ Tuples config not found at {TUPLES_PATH} or alternatives")
            return []

    try:
        with open(tuples_path) as f:
            config = json.load(f)

        raw_tuples = config.get("tuples", [])

        # Filter out _comment keys and keep only user/relation/object
        tuples = []
        for t in raw_tuples:
            tuples.append(
                {
                    "user": t["user"],
                    "relation": t["relation"],
                    "object": t["object"],
                }
            )

        print(f"✓ Loaded {len(tuples)} tuples from {tuples_path}")
        return tuples

    except Exception as e:
        print(f"✗ Error loading tuples config: {e}")
        return []


def seed_relationship_tuples(store_id: str, model_id: str) -> bool:
    """Seed relationship tuples for test users from config file."""
    print("\nSeeding relationship tuples...")

    # Load tuples from config file (single source of truth)
    tuples = load_tuples_from_config()
    if not tuples:
        print("✗ No tuples to seed")
        return False

    # Write tuples in batches (OpenFGA has a limit per request)
    batch_size = 20
    success_count = 0
    error_count = 0

    for i in range(0, len(tuples), batch_size):
        batch = tuples[i : i + batch_size]

        try:
            response = httpx.post(
                f"{OPENFGA_API_URL}/stores/{store_id}/write",
                headers=get_headers(),
                json={
                    "authorization_model_id": model_id,
                    "writes": {"tuple_keys": batch},
                },
                timeout=10,
            )

            if response.status_code == 200:
                success_count += len(batch)
                print(f"  ✓ Wrote batch {i // batch_size + 1}: {len(batch)} tuples")
            elif response.status_code == 400 and "already exists" in response.text.lower():
                # Tuples already exist - this is fine for idempotency
                success_count += len(batch)
                print(f"  ✓ Batch {i // batch_size + 1}: {len(batch)} tuples (already exist)")
            else:
                error_count += len(batch)
                print(f"  ✗ Failed batch {i // batch_size + 1}: {response.status_code} - {response.text}")

        except Exception as e:
            error_count += len(batch)
            print(f"  ✗ Error writing batch {i // batch_size + 1}: {e}")

    print(f"\n✓ Seeded {success_count} tuples ({error_count} errors)")
    return error_count == 0


def verify_permissions(store_id: str, model_id: str) -> bool:
    """Verify key permissions work correctly."""
    print("\nVerifying permissions...")

    test_cases = [
        # User | Relation | Object | Expected
        ("user:admin", "owner", "vector_store:default", True),
        ("user:alice", "editor", "vector_store:default", True),  # alice has CRUD
        ("user:alice", "viewer", "vector_store:default", True),  # editor implies viewer
        ("user:bob", "viewer", "vector_store:default", True),  # bob is read-only
        ("user:bob", "editor", "vector_store:default", False),  # bob cannot edit
        ("user:admin", "admin", "authz:playground", True),
        ("user:alice", "admin", "authz:playground", False),  # alice is only viewer
        ("user:bob", "viewer", "authz:playground", False),  # bob has no access
    ]

    all_passed = True

    for user, relation, obj, expected in test_cases:
        try:
            response = httpx.post(
                f"{OPENFGA_API_URL}/stores/{store_id}/check",
                headers=get_headers(),
                json={
                    "authorization_model_id": model_id,
                    "tuple_key": {
                        "user": user,
                        "relation": relation,
                        "object": obj,
                    },
                },
                timeout=10,
            )

            if response.status_code == 200:
                allowed = response.json().get("allowed", False)
                status = "✓" if allowed == expected else "✗"
                if allowed != expected:
                    all_passed = False
                print(f"  {status} {user} {relation} {obj}: {allowed} (expected: {expected})")
            else:
                print(f"  ✗ Check failed: {response.status_code} - {response.text}")
                all_passed = False

        except Exception as e:
            print(f"  ✗ Error checking {user} {relation} {obj}: {e}")
            all_passed = False

    return all_passed


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("OpenFGA Seeding Script")
    print("=" * 60)
    print(f"API URL: {OPENFGA_API_URL}")

    # Show authentication method
    if OPENFGA_OIDC_CLIENT_ID and OPENFGA_OIDC_CLIENT_SECRET:
        print(f"Auth: OIDC (client: {OPENFGA_OIDC_CLIENT_ID})")
    elif OPENFGA_PRESHARED_KEY:
        print("Auth: Preshared Key (deprecated)")
    else:
        print("Auth: Disabled")

    # Step 1: Wait for OpenFGA
    if not wait_for_openfga():
        return 1

    # Step 2: Get or create store
    store_id = get_or_create_store()
    if not store_id:
        return 1

    # Step 3: Upload authorization model
    model_id = upload_authorization_model(store_id)
    if not model_id:
        return 1

    # Step 4: Seed relationship tuples
    if not seed_relationship_tuples(store_id, model_id):
        print("\n⚠ Some tuples failed to seed, but continuing...")

    # Step 5: Verify permissions
    if not verify_permissions(store_id, model_id):
        print("\n⚠ Some permission checks failed")

    # Summary
    print("\n" + "=" * 60)
    print("✓ OpenFGA seeding complete!")
    print("=" * 60)
    print(f"\nStore ID: {store_id}")
    print(f"Model ID: {model_id}")
    print("\nSeeded permissions:")
    print("  - admin: owner on vector_store:default, admin on authz:playground (OpenFGA UI)")
    print("  - alice: editor on vector_store:default (CRUD), viewer on authz:playground")
    print("  - bob:   viewer on vector_store:default (read-only, no authz UI access)")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
