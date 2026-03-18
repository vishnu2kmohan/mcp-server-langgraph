"""
Integration tests for Vectors API (/api/v1/vectors).

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify the full stack that VectorsPage uses:
1. Keycloak JWT authentication
2. OpenFGA authorization (vector_store permissions)
3. Qdrant client connectivity

This test was created to diagnose VectorsPage E2E test failures showing
"Failed to load collections" error. The E2E tests couldn't determine if
the failure was:
- 403 Forbidden (OpenFGA authorization issue)
- 500 Internal Server Error (Qdrant connectivity issue)
- Network error (mcp-server-test not reachable)

Reference:
- ADR-0068 - Gateway-Level Authentication (OAuth2/JWT)
- config/openfga/sample-tuples.json - Pre-seeded permissions
- src/mcp_server_langgraph/api/v1/vectors.py - Vectors API implementation
"""

import gc
import os

import pytest

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.qdrant,
    pytest.mark.vectors,
]

# API configuration - use mcp-server-test container port
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:9082/authn")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:9333")

# Test credentials from tests/e2e/default-realm.json
TEST_USERS = {
    "admin": {"username": "admin", "password": "admin123"},
    "alice": {"username": "alice", "password": "alice123"},
    "bob": {"username": "bob", "password": "bob123"},
}

# Keycloak client credentials from config
KEYCLOAK_CLIENT_ID = "agent-studio-keycloak-client-id-for-e2e-tests"
KEYCLOAK_CLIENT_SECRET = "test-client-secret-for-e2e-tests"


def _api_available() -> bool:
    """Check if the API server is available."""
    try:
        import requests

        response = requests.get(f"{API_BASE_URL}/health/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def _keycloak_available() -> bool:
    """Check if Keycloak is available."""
    try:
        import requests

        response = requests.get(
            f"{KEYCLOAK_URL}/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _qdrant_available() -> bool:
    """Check if Qdrant is available."""
    try:
        import requests

        # Qdrant root endpoint returns version info when healthy
        response = requests.get(f"{QDRANT_URL}/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def _token_issuer_valid() -> bool:
    """Check if token issuer matches what API server expects.

    Gets a test token and makes a request to verify the issuer is valid.
    This catches environment mismatches where Keycloak is reachable but
    the token issuer URL doesn't match the API server's expected issuer.
    """
    try:
        import requests

        # Get a test token
        token = _get_token(TEST_USERS["admin"]["username"], TEST_USERS["admin"]["password"])
        if not token:
            return False

        # Try to use the token - if issuer doesn't match, we'll get 401
        response = requests.get(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        # 200 = token valid, 403 = token valid but no permission (still valid issuer)
        # 401 with "Invalid issuer" = environment mismatch
        if response.status_code == 401:
            try:
                error_detail = response.json().get("detail", "")
                if "Invalid issuer" in error_detail:
                    return False
            except Exception:
                pass

        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def skip_if_infra_unavailable():
    """Skip tests if required infrastructure is not available."""
    if not _api_available():
        pytest.skip("API server not available at " + API_BASE_URL)
    if not _keycloak_available():
        pytest.skip("Keycloak not available at " + KEYCLOAK_URL)
    if not _qdrant_available():
        pytest.skip("Qdrant not available at " + QDRANT_URL)
    if not _token_issuer_valid():
        pytest.skip(
            "Token issuer mismatch - Keycloak and API server not properly configured. "
            "Run `docker-compose -f docker-compose.test.yml up` to start test environment."
        )


def _get_token(username: str, password: str = "") -> str | None:
    """Get access token from Keycloak using modern OAuth2 flows.

    Two-step Token Exchange (RFC 8693):
    1. Get service account token via client_credentials
    2. Exchange it for a user-specific token with subject_token

    ROPC (password grant) is disabled per security audit (ADR-0086).
    """
    import requests

    token_url = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

    # Step 1: Get service account token via client_credentials
    try:
        sa_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": KEYCLOAK_CLIENT_ID,
                "client_secret": KEYCLOAK_CLIENT_SECRET,
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if sa_response.status_code != 200:
            return None
        sa_token = sa_response.json().get("access_token")
        if not sa_token:
            return None
    except Exception:
        return None

    # Step 2: Exchange for user-specific token (RFC 8693)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": KEYCLOAK_CLIENT_ID,
                "client_secret": KEYCLOAK_CLIENT_SECRET,
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": username,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass

    # Fallback to service account token if exchange not configured
    return sa_token


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPIAuthentication:
    """Test Vectors API authentication requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_vectors_collections_requires_auth(self, skip_if_infra_unavailable):
        """
        GIVEN: Vectors API endpoint
        WHEN: Accessing without authentication
        THEN: Should return 401 Unauthorized
        """
        import requests

        response = requests.get(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            timeout=10,
        )

        assert response.status_code == 401, (
            f"Vectors API should require authentication, got {response.status_code}\nResponse: {response.text[:500]}"
        )


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPIAuthorization:
    """Test Vectors API authorization via OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def admin_token(self, skip_if_infra_unavailable) -> str:
        """Get admin access token."""
        token = _get_token(
            TEST_USERS["admin"]["username"],
            TEST_USERS["admin"]["password"],
        )
        if not token:
            pytest.skip("Could not get admin token from Keycloak")
        return token

    @pytest.fixture
    def alice_token(self, skip_if_infra_unavailable) -> str:
        """Get alice access token."""
        token = _get_token(
            TEST_USERS["alice"]["username"],
            TEST_USERS["alice"]["password"],
        )
        if not token:
            pytest.skip("Could not get alice token from Keycloak")
        return token

    @pytest.fixture
    def bob_token(self, skip_if_infra_unavailable) -> str:
        """Get bob access token."""
        token = _get_token(
            TEST_USERS["bob"]["username"],
            TEST_USERS["bob"]["password"],
        )
        if not token:
            pytest.skip("Could not get bob token from Keycloak")
        return token

    def test_admin_can_list_collections(self, admin_token: str):
        """
        GIVEN: Admin user with owner permission on vector_store:default
        WHEN: Listing vector collections
        THEN: Should return 200 with collections list

        Pre-seeded tuple: user:admin owner vector_store:default
        """
        import requests

        response = requests.get(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )

        # Check status code
        assert response.status_code == 200, (
            f"Admin should be able to list collections, got {response.status_code}\n"
            f"Response: {response.text[:500]}\n\n"
            "If 403: OpenFGA tuples not seeded (check openfga-seed-test container)\n"
            "If 500: Qdrant connection failed (check qdrant-test container)"
        )

        # Verify response format
        data = response.json()
        assert "collections" in data, f"Response should have 'collections' key: {data}"
        assert isinstance(data["collections"], list), "Collections should be a list"

    def test_alice_can_list_collections_as_editor(self, alice_token: str):
        """
        GIVEN: Alice user with editor permission on vector_store:default
        WHEN: Listing vector collections
        THEN: Should return 200 with collections list

        Pre-seeded tuple: user:alice editor vector_store:default
        Editor implies viewer permission.
        """
        import requests

        response = requests.get(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {alice_token}"},
            timeout=10,
        )

        assert response.status_code == 200, (
            f"Alice (viewer) should be able to list collections, got {response.status_code}\nResponse: {response.text[:500]}"
        )

        data = response.json()
        assert "collections" in data

    def test_bob_can_list_collections_as_viewer(self, bob_token: str):
        """
        GIVEN: Bob user with viewer permission on vector_store:default
        WHEN: Listing vector collections
        THEN: Should return 200 with collections list

        Pre-seeded tuple: user:bob viewer vector_store:default
        """
        import requests

        response = requests.get(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {bob_token}"},
            timeout=10,
        )

        assert response.status_code == 200, (
            f"Bob (viewer) should be able to list collections, got {response.status_code}\nResponse: {response.text[:500]}"
        )

        data = response.json()
        assert "collections" in data


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPICRUD:
    """Test Vectors API CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def admin_token(self, skip_if_infra_unavailable) -> str:
        """Get admin access token."""
        token = _get_token(
            TEST_USERS["admin"]["username"],
            TEST_USERS["admin"]["password"],
        )
        if not token:
            pytest.skip("Could not get admin token from Keycloak")
        return token

    @pytest.fixture
    def alice_token(self, skip_if_infra_unavailable) -> str:
        """Get alice access token."""
        token = _get_token(
            TEST_USERS["alice"]["username"],
            TEST_USERS["alice"]["password"],
        )
        if not token:
            pytest.skip("Could not get alice token from Keycloak")
        return token

    @pytest.fixture
    def bob_token(self, skip_if_infra_unavailable) -> str:
        """Get bob access token."""
        token = _get_token(
            TEST_USERS["bob"]["username"],
            TEST_USERS["bob"]["password"],
        )
        if not token:
            pytest.skip("Could not get bob token from Keycloak")
        return token

    def test_admin_can_create_collection(self, admin_token: str):
        """
        GIVEN: Admin user with owner permission (includes editor)
        WHEN: Creating a new collection
        THEN: Should return 201 Created

        Admin has owner permission which implies editor (can create).
        """
        import requests
        import uuid

        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"

        response = requests.post(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": collection_name,
                "vectors": {
                    "size": 384,
                    "distance": "Cosine",
                },
            },
            timeout=10,
        )

        assert response.status_code == 201, (
            f"Admin should be able to create collection, got {response.status_code}\nResponse: {response.text[:500]}"
        )

        # Cleanup: delete the collection
        requests.delete(
            f"{API_BASE_URL}/api/v1/vectors/collections/{collection_name}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )

    def test_alice_can_create_collection_as_editor(self, alice_token: str):
        """
        GIVEN: Alice user with editor permission
        WHEN: Creating a new collection
        THEN: Should return 201 Created

        Alice has editor permission which includes create (CRUD).
        """
        import requests
        import uuid

        collection_name = f"test_collection_alice_{uuid.uuid4().hex[:8]}"

        response = requests.post(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={
                "name": collection_name,
                "vectors": {
                    "size": 384,
                    "distance": "Cosine",
                },
            },
            timeout=10,
        )

        assert response.status_code == 201, (
            f"Alice (editor) should be able to create collection, got {response.status_code}\nResponse: {response.text[:500]}"
        )

        # Cleanup: delete the collection (Alice can delete as editor)
        requests.delete(
            f"{API_BASE_URL}/api/v1/vectors/collections/{collection_name}",
            headers={"Authorization": f"Bearer {alice_token}"},
            timeout=10,
        )

    def test_bob_cannot_create_collection_as_viewer(self, bob_token: str):
        """
        GIVEN: Bob user with only viewer permission
        WHEN: Trying to create a collection
        THEN: Should return 403 Forbidden

        Bob has viewer permission, not editor, so cannot create.
        """
        import requests
        import uuid

        collection_name = f"test_collection_bob_{uuid.uuid4().hex[:8]}"

        response = requests.post(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {bob_token}"},
            json={
                "name": collection_name,
                "vectors": {
                    "size": 384,
                    "distance": "Cosine",
                },
            },
            timeout=10,
        )

        assert response.status_code == 403, (
            f"Bob (viewer only) should not be able to create collection, got {response.status_code}\n"
            f"Response: {response.text[:500]}"
        )

    def test_admin_can_delete_collection(self, admin_token: str):
        """
        GIVEN: Admin user with owner permission
        WHEN: Deleting a collection
        THEN: Should return 200 OK

        Admin has owner permission, required for delete.
        """
        import requests
        import uuid

        collection_name = f"test_delete_{uuid.uuid4().hex[:8]}"

        # First create a collection
        create_response = requests.post(
            f"{API_BASE_URL}/api/v1/vectors/collections",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": collection_name,
                "vectors": {
                    "size": 384,
                    "distance": "Cosine",
                },
            },
            timeout=10,
        )

        if create_response.status_code != 201:
            pytest.skip(f"Could not create collection for delete test: {create_response.text}")

        # Now delete it
        delete_response = requests.delete(
            f"{API_BASE_URL}/api/v1/vectors/collections/{collection_name}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )

        assert delete_response.status_code == 200, (
            f"Admin should be able to delete collection, got {delete_response.status_code}\n"
            f"Response: {delete_response.text[:500]}"
        )


@pytest.mark.xdist_group(name="test_vectors_api")
class TestQdrantConnectivity:
    """Test direct Qdrant connectivity from API server."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_qdrant_health_check_returns_healthy(self, skip_if_infra_unavailable):
        """
        GIVEN: Qdrant container running
        WHEN: Checking Qdrant health directly
        THEN: Should be healthy

        This test checks Qdrant directly at port 9333 (host mapping).
        """
        import requests

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:9333")

        response = requests.get(
            f"{qdrant_url}/",
            timeout=10,
        )

        assert response.status_code == 200, (
            f"Qdrant should be healthy, got {response.status_code}\nResponse: {response.text[:500]}"
        )

    def test_qdrant_collections_direct(self, skip_if_infra_unavailable):
        """
        GIVEN: Qdrant container running
        WHEN: Listing collections directly (no auth)
        THEN: Should return collections list

        This bypasses the API gateway to verify Qdrant itself works.
        """
        import requests

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:9333")

        response = requests.get(
            f"{qdrant_url}/collections",
            timeout=10,
        )

        assert response.status_code == 200, (
            f"Qdrant should return collections, got {response.status_code}\nResponse: {response.text[:500]}"
        )

        data = response.json()
        assert "result" in data, f"Qdrant response should have 'result' key: {data}"
