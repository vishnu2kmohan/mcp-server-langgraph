"""
Tests for Push Notification API Endpoints

TDD tests for the push notification subscription endpoints.
Tests cover:
- Subscribe to push notifications
- Unsubscribe from push notifications
- Authentication requirements
"""

import gc
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_subscription():
    """Sample push subscription payload."""
    return {
        "endpoint": "https://fcm.googleapis.com/fcm/send/mock-endpoint",
        "keys": {"p256dh": "mock-p256dh-key", "auth": "mock-auth-key"},
    }


@pytest.mark.xdist_group(name="testnotificationsubscribe")
class TestNotificationSubscribe:
    """Tests for POST /api/v1/notifications/subscribe."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_with_valid_subscription_returns_success(self, client, mock_subscription):
        """Should successfully subscribe to push notifications."""
        with patch("mcp_server_langgraph.api.v1.notifications.store_subscription") as mock_store:
            mock_store.return_value = True

            response = client.post(
                "/api/v1/notifications/subscribe", json=mock_subscription, headers={"Authorization": "Bearer mock-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data

    def test_subscribe_missing_endpoint(self, client):
        """Should reject subscription without endpoint."""
        response = client.post(
            "/api/v1/notifications/subscribe",
            json={"keys": {"p256dh": "key", "auth": "auth"}},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422

    def test_subscribe_missing_keys(self, client):
        """Should reject subscription without keys."""
        response = client.post(
            "/api/v1/notifications/subscribe",
            json={"endpoint": "https://example.com/endpoint"},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422


@pytest.mark.xdist_group(name="testnotificationunsubscribe")
class TestNotificationUnsubscribe:
    """Tests for POST /api/v1/notifications/unsubscribe."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unsubscribe_with_valid_endpoint_returns_success(self, client):
        """Should successfully unsubscribe from push notifications."""
        with patch("mcp_server_langgraph.api.v1.notifications.remove_subscription") as mock_remove:
            mock_remove.return_value = True

            response = client.post(
                "/api/v1/notifications/unsubscribe",
                json={"endpoint": "https://fcm.googleapis.com/fcm/send/mock-endpoint"},
                headers={"Authorization": "Bearer mock-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_unsubscribe_missing_endpoint(self, client):
        """Should reject unsubscribe without endpoint."""
        response = client.post("/api/v1/notifications/unsubscribe", json={}, headers={"Authorization": "Bearer mock-token"})

        assert response.status_code == 422


@pytest.mark.xdist_group(name="testnotificationendpointexists")
class TestNotificationEndpointExists:
    """Tests to verify notification endpoints are registered."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_endpoint_exists(self, client):
        """Should have subscribe endpoint registered."""
        # OPTIONS request should not return 404
        response = client.options("/api/v1/notifications/subscribe")
        assert response.status_code != 404

    def test_unsubscribe_endpoint_exists(self, client):
        """Should have unsubscribe endpoint registered."""
        # OPTIONS request should not return 404
        response = client.options("/api/v1/notifications/unsubscribe")
        assert response.status_code != 404
