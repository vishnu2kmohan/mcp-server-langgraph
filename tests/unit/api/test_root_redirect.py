"""
Tests for root endpoint redirect to studio

TDD: Tests written FIRST to define expected behavior.

Follows memory safety patterns for pytest-xdist.
"""

import gc

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import create_app

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def client():
    """Create a test client with skip_startup_validation to avoid DB dependency."""
    app = create_app(skip_startup_validation=True)
    return TestClient(app)


class TestRootRedirect:
    """Tests for GET / endpoint"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_root_redirects_to_studio(self, client):
        """Root path should redirect to /studio with 307 status."""
        response = client.get("/", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "/studio"

    def test_root_redirect_is_temporary(self, client):
        """Root redirect should use 307 (temporary redirect)."""
        response = client.get("/", follow_redirects=False)

        # 307 preserves HTTP method (important for REST semantics)
        assert response.status_code == 307

    def test_root_redirect_follows_correctly(self, client):
        """Following the redirect should reach /studio."""
        response = client.get("/", follow_redirects=True)

        # Should eventually reach /studio endpoint
        # Note: /studio might not exist yet, but redirect should work
        assert response.history[0].status_code == 307
        assert response.history[0].headers["location"] == "/studio"
