"""
E2E Test Configuration and Fixtures

Provides fixtures for end-to-end tests including:
- OpenFGA tuple verification for authorization testing
- Real infrastructure client connections
- User journey helper fixtures
- Infrastructure availability skip fixture (autouse)

These fixtures work with docker-compose.test.yml infrastructure.

IMPORTANT: OpenFGA Tuple Management
-----------------------------------
The single source of truth for base user permissions (alice, bob, admin)
is config/openfga/sample-tuples.json. This file is seeded into OpenFGA
by docker-compose.test.yml via the openfga-seed-test container.

E2E fixtures should VERIFY pre-seeded tuples exist, NOT create them.
This ensures:
1. Consistent permissions across all tests using make test-infra-up-build
2. No "tuple already exists" errors from duplicate creation attempts
3. Alignment with ADR-0068 for gateway-level authentication

For test-specific tuples not covered by sample-tuples.json, individual
tests may create and clean up their own tuples as needed.
"""

import os

import pytest
import pytest_asyncio
import requests


def _e2e_infrastructure_available() -> bool:
    """Check if E2E infrastructure is available (Keycloak via gateway)."""
    try:
        # Check Keycloak via gateway
        keycloak_response = requests.get(
            "http://localhost/authn/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return keycloak_response.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_e2e_infrastructure_unavailable():
    """Skip E2E tests if infrastructure is not available.

    This autouse fixture runs before each E2E test and properly skips when
    Keycloak/OpenFGA infrastructure is not reachable. Centralized in conftest.py
    to avoid duplicate autouse fixtures across test files (best practice).
    """
    if not _e2e_infrastructure_available():
        pytest.skip("E2E infrastructure not available")


# OpenFGA configuration constants
OPENFGA_URL = os.getenv("OPENFGA_API_URL", "http://localhost:9080")
OPENFGA_TEST_STORE_NAME = "agent-studio-openfga-store-test"

# OIDC credentials for OpenFGA API access (ADR-0070: OIDC replaces preshared key)
OPENFGA_OIDC_CLIENT_ID = os.getenv("OPENFGA_OIDC_CLIENT_ID", "agent-studio-openfga-oidc-cient-id-for-e2e-tests")
OPENFGA_OIDC_CLIENT_SECRET = os.getenv("OPENFGA_OIDC_CLIENT_SECRET", "agent-studio-openfga-oidc-client-secret-for-e2e-tests")
KEYCLOAK_TOKEN_URL = os.getenv(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost/authn/realms/default/protocol/openid-connect/token",
)

# Cache OIDC token at module level to avoid repeated Keycloak calls
_cached_openfga_oidc_token: str | None = None


def _get_openfga_oidc_token() -> str | None:
    """Obtain OIDC token from Keycloak for OpenFGA API access."""
    global _cached_openfga_oidc_token
    if _cached_openfga_oidc_token:
        return _cached_openfga_oidc_token
    try:
        response = requests.post(
            KEYCLOAK_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OPENFGA_OIDC_CLIENT_ID,
                "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
            },
            timeout=10,
        )
        if response.status_code == 200:
            _cached_openfga_oidc_token = response.json().get("access_token")
            return _cached_openfga_oidc_token
    except Exception:
        pass
    return None


def _get_openfga_auth_headers() -> dict[str, str]:
    """Get OIDC authentication headers for OpenFGA API requests."""
    token = _get_openfga_oidc_token()
    if not token:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_openfga_store_and_model() -> tuple[str | None, str | None]:
    """
    Dynamically discover OpenFGA store and model IDs.

    Queries the OpenFGA API to find the test store and its latest authorization model.
    This avoids the need for environment variables that are only available inside Docker.

    Returns:
        Tuple of (store_id, model_id) or (None, None) if not found
    """
    import requests

    headers = _get_openfga_auth_headers()

    # Find the test store
    try:
        stores_resp = requests.get(f"{OPENFGA_URL}/stores", headers=headers, timeout=10)
        if stores_resp.status_code != 200:
            return None, None

        stores = stores_resp.json().get("stores", [])
        store_id = None
        for store in stores:
            if store.get("name") == OPENFGA_TEST_STORE_NAME:
                store_id = store.get("id")
                break

        if not store_id:
            return None, None

        # Get the latest authorization model
        models_resp = requests.get(
            f"{OPENFGA_URL}/stores/{store_id}/authorization-models",
            headers=headers,
            timeout=10,
        )
        if models_resp.status_code != 200:
            return store_id, None

        models = models_resp.json().get("authorization_models", [])
        if not models:
            return store_id, None

        model_id = models[0].get("id")
        return store_id, model_id

    except Exception:
        return None, None


@pytest_asyncio.fixture
async def openfga_seeded_tuples(test_infrastructure):
    """
    Provide access to pre-seeded OpenFGA tuples for E2E tests.

    This fixture verifies that the pre-seeded tuples from docker-compose
    (config/openfga/sample-tuples.json) exist for alice.

    Pre-seeded tuples (from sample-tuples.json):
    - user:alice executor tool:chat
    - user:alice member organization:acme
    - user:alice admin organization:acme
    - user:alice owner conversation:thread_1
    - user:alice editor vector_store:default

    Yields:
        dict: Mapping of pre-seeded tuples for test assertions
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Dynamically discover OpenFGA store and model IDs
    store_id, model_id = _get_openfga_store_and_model()

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (store not found)")

    config = OpenFGAConfig(
        api_url=OPENFGA_URL,
        store_id=store_id,
        model_id=model_id,
        oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
        oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
        oidc_issuer=os.getenv("OPENFGA_OIDC_ISSUER", "http://localhost/authn/realms/default"),
    )
    client = OpenFGAClient(config=config)

    # Verify pre-seeded tuple exists (alice can execute tool:chat)
    try:
        can_execute = await client.check_permission(
            user="user:alice",
            relation="executor",
            object="tool:chat",
        )
        if not can_execute:
            pytest.skip("Pre-seeded OpenFGA tuples not found (alice cannot execute tool:chat)")
    except Exception as e:
        await client.close()
        pytest.skip(f"Failed to verify OpenFGA tuples: {e}")

    yield {
        "tuples": [
            {"user": "user:alice", "relation": "executor", "object": "tool:chat"},
            {"user": "user:alice", "relation": "member", "object": "organization:acme"},
            {"user": "user:alice", "relation": "admin", "object": "organization:acme"},
        ],
        "user": "user:alice",
        "tools": ["chat"],  # Pre-seeded tool
    }

    # No cleanup needed - we didn't create any tuples
    await client.close()


@pytest_asyncio.fixture
async def openfga_admin_tuples(test_infrastructure):
    """
    Provide access to pre-seeded admin-level OpenFGA tuples for E2E tests.

    This fixture verifies that the pre-seeded tuples from docker-compose
    exist for alice as admin on organization:acme.

    Pre-seeded tuples (from sample-tuples.json):
    - user:alice admin organization:acme

    Yields:
        dict: Mapping of pre-seeded admin tuples
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Dynamically discover OpenFGA store and model IDs
    store_id, model_id = _get_openfga_store_and_model()

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (store not found)")

    config = OpenFGAConfig(
        api_url=OPENFGA_URL,
        store_id=store_id,
        model_id=model_id,
        oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
        oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
        oidc_issuer=os.getenv("OPENFGA_OIDC_ISSUER", "http://localhost/authn/realms/default"),
    )
    client = OpenFGAClient(config=config)

    # Verify pre-seeded tuple exists (alice is admin on organization:acme)
    try:
        is_admin = await client.check_permission(
            user="user:alice",
            relation="admin",
            object="organization:acme",
        )
        if not is_admin:
            pytest.skip("Pre-seeded OpenFGA tuples not found (alice is not admin)")
    except Exception as e:
        await client.close()
        pytest.skip(f"Failed to verify admin OpenFGA tuples: {e}")

    yield {
        "tuples": [
            {"user": "user:alice", "relation": "admin", "object": "organization:acme"},
        ],
        "user": "user:alice",
        "is_admin": True,
    }

    # No cleanup needed - we didn't create any tuples
    await client.close()


@pytest_asyncio.fixture
async def openfga_bob_tuples(test_infrastructure):
    """
    Provide access to pre-seeded OpenFGA tuples for bob user (standard tier).

    This fixture verifies that the pre-seeded tuples from docker-compose
    exist for bob with limited permissions compared to alice.

    Pre-seeded tuples (from sample-tuples.json):
    - user:bob executor tool:chat
    - user:bob member organization:acme
    - user:bob viewer conversation:thread_1
    - user:bob assignee role:standard
    - user:bob viewer vector_store:default

    Yields:
        dict: Mapping of pre-seeded tuples for test assertions
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Dynamically discover OpenFGA store and model IDs
    store_id, model_id = _get_openfga_store_and_model()

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (store not found)")

    config = OpenFGAConfig(
        api_url=OPENFGA_URL,
        store_id=store_id,
        model_id=model_id,
        oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
        oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
        oidc_issuer=os.getenv("OPENFGA_OIDC_ISSUER", "http://localhost/authn/realms/default"),
    )
    client = OpenFGAClient(config=config)

    # Verify pre-seeded tuple exists (bob is member of organization:acme)
    try:
        is_member = await client.check_permission(
            user="user:bob",
            relation="member",
            object="organization:acme",
        )
        if not is_member:
            pytest.skip("Pre-seeded OpenFGA tuples not found (bob is not member)")
    except Exception as e:
        await client.close()
        pytest.skip(f"Failed to verify bob OpenFGA tuples: {e}")

    yield {
        "tuples": [
            {"user": "user:bob", "relation": "executor", "object": "tool:chat"},
            {"user": "user:bob", "relation": "member", "object": "organization:acme"},
        ],
        "user": "user:bob",
        "tier": "standard",
        "tools": ["chat"],  # Pre-seeded tool
    }

    # No cleanup needed - we didn't create any tuples
    await client.close()


@pytest_asyncio.fixture
async def openfga_cross_user_tuples(test_infrastructure):
    """
    Provide access to pre-seeded tuples for testing cross-user access scenarios.

    This fixture verifies that the pre-seeded tuples from docker-compose
    exist for cross-user access testing.

    Pre-seeded tuples (from sample-tuples.json):
    - user:alice owner workflow:alice_workflow
    - user:bob viewer workflow:alice_workflow
    - user:admin owner workflow:default
    - user:admin admin organization:acme

    Yields:
        dict: Mapping of pre-seeded tuples for test assertions
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Dynamically discover OpenFGA store and model IDs
    store_id, model_id = _get_openfga_store_and_model()

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (store not found)")

    config = OpenFGAConfig(
        api_url=OPENFGA_URL,
        store_id=store_id,
        model_id=model_id,
        oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
        oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
        oidc_issuer=os.getenv("OPENFGA_OIDC_ISSUER", "http://localhost/authn/realms/default"),
    )
    client = OpenFGAClient(config=config)

    # Verify pre-seeded tuples exist (alice owns workflow, bob can view)
    try:
        alice_owns = await client.check_permission(
            user="user:alice",
            relation="owner",
            object="workflow:alice_workflow",
        )
        bob_can_view = await client.check_permission(
            user="user:bob",
            relation="viewer",
            object="workflow:alice_workflow",
        )
        if not alice_owns or not bob_can_view:
            pytest.skip("Pre-seeded cross-user tuples not found")
    except Exception as e:
        await client.close()
        pytest.skip(f"Failed to verify cross-user OpenFGA tuples: {e}")

    yield {
        "tuples": [
            {"user": "user:alice", "relation": "owner", "object": "workflow:alice_workflow"},
            {"user": "user:bob", "relation": "viewer", "object": "workflow:alice_workflow"},
            {"user": "user:admin", "relation": "admin", "object": "organization:acme"},
        ],
        "shared_workflow_id": "alice_workflow",
        "shared_conversation_id": "thread_1",  # Kept for backward compatibility
        "owner": "user:alice",
        "viewer": "user:bob",
        "admin": "user:admin",
    }

    # No cleanup needed - we didn't create any tuples
    await client.close()


@pytest_asyncio.fixture
async def openfga_workflow_tuples(test_infrastructure):
    """
    Provide access to pre-seeded workflow tuples for E2E tests.

    This fixture verifies that the pre-seeded workflow tuples from docker-compose
    exist for workflow authorization testing.

    Pre-seeded tuples (from sample-tuples.json):
    - user:admin owner workflow:default
    - user:alice owner workflow:alice_workflow
    - user:bob viewer workflow:alice_workflow

    Yields:
        dict: Mapping of pre-seeded workflow tuples for test assertions
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Dynamically discover OpenFGA store and model IDs
    store_id, model_id = _get_openfga_store_and_model()

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (store not found)")

    config = OpenFGAConfig(
        api_url=OPENFGA_URL,
        store_id=store_id,
        model_id=model_id,
        oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
        oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
        oidc_issuer=os.getenv("OPENFGA_OIDC_ISSUER", "http://localhost/authn/realms/default"),
    )
    client = OpenFGAClient(config=config)

    # Verify pre-seeded tuple exists (alice owns workflow:alice_workflow)
    try:
        alice_owns = await client.check_permission(
            user="user:alice",
            relation="owner",
            object="workflow:alice_workflow",
        )
        if not alice_owns:
            pytest.skip("Pre-seeded workflow tuples not found")
    except Exception as e:
        await client.close()
        pytest.skip(f"Failed to verify workflow OpenFGA tuples: {e}")

    yield {
        "tuples": [
            {"user": "user:admin", "relation": "owner", "object": "workflow:default"},
            {"user": "user:alice", "relation": "owner", "object": "workflow:alice_workflow"},
            {"user": "user:bob", "relation": "viewer", "object": "workflow:alice_workflow"},
        ],
        "admin_workflow": "default",
        "alice_workflow": "alice_workflow",
    }

    # No cleanup needed - we didn't create any tuples
    await client.close()


@pytest.fixture
def e2e_api_base_url():
    """
    Get the base URL for E2E API calls.

    Returns the MCP server URL for E2E tests.
    Default: http://localhost:8000
    """
    return os.getenv("MCP_SERVER_URL", "http://localhost:8000")


@pytest.fixture
def e2e_keycloak_base_url():
    """
    Get the Keycloak base URL for E2E tests.

    Uses gateway URL (port 80) with /authn prefix for consistency with
    integration tests and production configuration.

    Default: http://localhost/authn
    """
    return os.getenv("KEYCLOAK_URL", "http://localhost/authn")


# OAuth2 client configuration for E2E tests
E2E_CLIENT_ID = "agent-studio-keycloak-client-id-for-e2e-tests"
E2E_CLIENT_SECRET = "test-client-secret-for-e2e-tests"


@pytest.fixture
def alice_credentials():
    """
    Get alice's test credentials for E2E tests.

    Returns:
        dict: Username, password, and OAuth2 client credentials for alice
    """
    return {
        "username": "alice",
        "password": "alice123",
        "email": "alice@example.com",
        "tier": "premium",
        "client_id": E2E_CLIENT_ID,
        "client_secret": E2E_CLIENT_SECRET,
    }


@pytest.fixture
def bob_credentials():
    """
    Get bob's test credentials for E2E tests.

    Returns:
        dict: Username, password, and OAuth2 client credentials for bob
    """
    return {
        "username": "bob",
        "password": "bob123",
        "email": "bob@example.com",
        "tier": "standard",
        "client_id": E2E_CLIENT_ID,
        "client_secret": E2E_CLIENT_SECRET,
    }


@pytest.fixture
def admin_credentials():
    """
    Get admin's test credentials for E2E tests.

    Returns:
        dict: Username, password, and OAuth2 client credentials for admin
    """
    return {
        "username": "admin",
        "password": "admin123",
        "email": "admin@example.com",
        "roles": ["admin"],
        "client_id": E2E_CLIENT_ID,
        "client_secret": E2E_CLIENT_SECRET,
    }


def get_keycloak_token_for_tests(
    keycloak_base_url: str = "http://localhost/authn",
    client_id: str = E2E_CLIENT_ID,
    client_secret: str = E2E_CLIENT_SECRET,
) -> str | None:
    """
    Get Keycloak access token for E2E tests using client_credentials grant.

    Uses client_credentials grant per ADR-0086 (ROPC is disabled).

    Args:
        keycloak_base_url: Keycloak base URL (default: http://localhost/authn)
        client_id: OAuth2 client ID (default: agent-studio-keycloak-client-id-for-e2e-tests)
        client_secret: OAuth2 client secret (default: test-client-secret-for-e2e-tests)

    Returns:
        Access token or None if authentication fails
    """
    token_url = f"{keycloak_base_url}/realms/default/protocol/openid-connect/token"

    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid profile email offline_access",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


@pytest.fixture
def e2e_auth_token(e2e_keycloak_base_url):
    """
    Get a valid Keycloak access token for E2E API tests.

    Returns:
        str | None: Access token or None if authentication fails
    """
    return get_keycloak_token_for_tests(keycloak_base_url=e2e_keycloak_base_url)
