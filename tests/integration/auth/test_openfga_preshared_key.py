"""
Integration tests for OpenFGA Preshared Key Authentication.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. OpenFGA API rejects unauthenticated requests
2. OpenFGA API accepts requests with valid preshared key
3. OpenFGA API rejects requests with invalid preshared key

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import gc
import os

import pytest
import requests

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.openfga,
]


def _openfga_available() -> bool:
    """Check if OpenFGA is available."""
    try:
        # OpenFGA uses /healthz for health checks (not /health)
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Infrastructure check and autouse skip fixture are in tests/integration/auth/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)

# URLs
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")

# Test preshared key from .env.test / docker-compose.test.yml
VALID_PRESHARED_KEY = os.getenv("OPENFGA_PRESHARED_KEY", "test-openfga-preshared-key")
INVALID_PRESHARED_KEY = "invalid-key-that-should-fail"


@pytest.mark.xdist_group(name="test_openfga_preshared_key")
class TestOpenFGAPresharedKeyAuth:
    """Test that OpenFGA requires preshared key authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unauthenticated_request_is_rejected(self):
        """
        GIVEN: No authentication header
        WHEN: Accessing OpenFGA stores endpoint
        THEN: Should return 401 Unauthorized

        User Journey: Unauthenticated request is blocked
        """
        response = requests.get(
            f"{OPENFGA_URL}/stores",
            timeout=10,
        )

        # Should reject unauthenticated requests
        assert response.status_code == 401, f"Expected 401 Unauthorized without preshared key, got {response.status_code}"

    def test_invalid_preshared_key_is_rejected(self):
        """
        GIVEN: Invalid preshared key in Authorization header
        WHEN: Accessing OpenFGA stores endpoint
        THEN: Should return 401 Unauthorized

        User Journey: Request with wrong key is blocked
        """
        response = requests.get(
            f"{OPENFGA_URL}/stores",
            headers={"Authorization": f"Bearer {INVALID_PRESHARED_KEY}"},
            timeout=10,
        )

        # Should reject invalid preshared key
        assert response.status_code == 401, f"Expected 401 Unauthorized with invalid key, got {response.status_code}"

    def test_valid_preshared_key_is_accepted(self):
        """
        GIVEN: Valid preshared key in Authorization header
        WHEN: Accessing OpenFGA stores endpoint
        THEN: Should return 200 OK with stores list

        User Journey: Authenticated application can access OpenFGA API
        """
        response = requests.get(
            f"{OPENFGA_URL}/stores",
            headers={"Authorization": f"Bearer {VALID_PRESHARED_KEY}"},
            timeout=10,
        )

        # Should accept valid preshared key
        assert response.status_code == 200, (
            f"Expected 200 OK with valid preshared key, got {response.status_code}: {response.text}"
        )

        # Response should be valid JSON with stores
        data = response.json()
        assert "stores" in data, f"Expected 'stores' in response, got: {data}"


@pytest.mark.xdist_group(name="test_openfga_preshared_key")
class TestOpenFGAHealthEndpoint:
    """Test OpenFGA health endpoint accessibility."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_health_endpoint_is_accessible_without_auth(self):
        """
        GIVEN: No authentication
        WHEN: Accessing OpenFGA health endpoint
        THEN: Should return 200 OK (health endpoints should be public)

        Note: Health endpoints must be accessible for K8s probes
        Note: OpenFGA uses /healthz (not /health) for health checks
        """
        response = requests.get(
            f"{OPENFGA_URL}/healthz",
            timeout=10,
        )

        # Health endpoint should be accessible without auth
        assert response.status_code == 200, f"OpenFGA health should be public, got {response.status_code}"


@pytest.mark.xdist_group(name="test_openfga_preshared_key")
class TestOpenFGAWriteOperations:
    """Test OpenFGA write operations with preshared key."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_store_with_preshared_key(self):
        """
        GIVEN: Valid preshared key
        WHEN: Creating a new store via POST
        THEN: Should successfully create the store

        User Journey: Application creates authorization store
        """
        response = requests.post(
            f"{OPENFGA_URL}/stores",
            headers={
                "Authorization": f"Bearer {VALID_PRESHARED_KEY}",
                "Content-Type": "application/json",
            },
            json={"name": "test-preshared-key-store"},
            timeout=10,
        )

        # Should successfully create store
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"

        data = response.json()
        assert "id" in data, f"Expected 'id' in response, got: {data}"
        assert data.get("name") == "test-preshared-key-store"

        # Cleanup: Delete the test store
        store_id = data["id"]
        cleanup_response = requests.delete(
            f"{OPENFGA_URL}/stores/{store_id}",
            headers={"Authorization": f"Bearer {VALID_PRESHARED_KEY}"},
            timeout=10,
        )
        assert cleanup_response.status_code in [200, 204], f"Cleanup failed: {cleanup_response.status_code}"

    def test_create_store_without_auth_is_rejected(self):
        """
        GIVEN: No authentication
        WHEN: Attempting to create a store
        THEN: Should return 401 Unauthorized

        User Journey: Unauthenticated write is blocked
        """
        response = requests.post(
            f"{OPENFGA_URL}/stores",
            headers={"Content-Type": "application/json"},
            json={"name": "should-not-be-created"},
            timeout=10,
        )

        # Should reject unauthenticated write
        assert response.status_code == 401, f"Expected 401 Unauthorized for unauthenticated write, got {response.status_code}"
