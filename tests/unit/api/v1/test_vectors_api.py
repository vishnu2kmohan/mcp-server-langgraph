"""
Unit tests for Qdrant Vectors Proxy API.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Unauthenticated requests are rejected
2. Authenticated requests with viewer permission can list/search collections
3. Authenticated requests with editor permission can create/upsert
4. Authenticated requests with owner permission can delete
5. Requests without required permissions are denied

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.qdrant,
]


@pytest.fixture
def mock_openfga_client():
    """Create a mock OpenFGA client for testing."""
    client = AsyncMock(return_value=None)
    client.check_permission = AsyncMock(return_value=True)
    client.close = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client for testing."""
    client = MagicMock()
    client.get_collections = MagicMock(return_value=MagicMock(collections=[]))
    client.create_collection = MagicMock()
    client.delete_collection = MagicMock()
    client.search = MagicMock(return_value=[])
    return client


@pytest.fixture
def mock_current_user():
    """Create a mock authenticated user."""
    return {
        "sub": "user:alice",
        "preferred_username": "alice",
        "email": "alice@example.com",
        "realm_access": {"roles": ["user"]},
    }


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return {
        "sub": "user:admin",
        "preferred_username": "admin",
        "email": "admin@example.com",
        "realm_access": {"roles": ["user", "admin"]},
    }


def create_test_app_with_mocks(
    mock_user: dict[str, Any] | None,
    mock_openfga: AsyncMock | None,
    mock_qdrant: MagicMock | None,
) -> FastAPI:
    """Create a test FastAPI app with dependency overrides."""
    from mcp_server_langgraph.api.v1.vectors import (
        get_openfga_client,
        get_qdrant_client,
        router,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router)

    if mock_user is not None:
        # Use async function instead of sync lambda per xdist safety pattern
        async def get_mock_user() -> dict[str, Any]:
            return mock_user  # type: ignore[return-value]

        app.dependency_overrides[get_current_user] = get_mock_user

    if mock_openfga is not None:
        app.dependency_overrides[get_openfga_client] = lambda: mock_openfga

    if mock_qdrant is not None:
        app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

    return app


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPIListCollections:
    """Test listing collections requires viewer permission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_collections_requires_authentication(self):
        """
        GIVEN: No authentication
        WHEN: Listing collections
        THEN: Should return 401 Unauthorized
        """
        # Create app without authentication mock
        app = create_test_app_with_mocks(mock_user=None, mock_openfga=None, mock_qdrant=None)
        client = TestClient(app)

        response = client.get("/collections")

        assert response.status_code == 401

    def test_list_collections_with_viewer_permission(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user with viewer permission
        WHEN: Listing collections
        THEN: Should return 200 with collections list
        """
        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.get("/collections")

        assert response.status_code == 200
        mock_openfga_client.check_permission.assert_called_once()

    def test_list_collections_without_viewer_permission(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user without viewer permission
        WHEN: Listing collections
        THEN: Should return 403 Forbidden
        """
        # Mock permission check to return False
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.get("/collections")

        assert response.status_code == 403


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPICreateCollection:
    """Test creating collections requires editor permission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_collection_requires_editor_permission(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user with editor permission
        WHEN: Creating a collection
        THEN: Should return 201 Created
        """
        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.post(
            "/collections",
            json={"name": "test-collection", "vectors": {"size": 768, "distance": "Cosine"}},
        )

        assert response.status_code == 201

    def test_create_collection_denied_for_viewer(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user with only viewer permission
        WHEN: Creating a collection
        THEN: Should return 403 Forbidden
        """
        # Mock: editor=False (deny editor permission)
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.post(
            "/collections",
            json={"name": "test-collection", "vectors": {"size": 768, "distance": "Cosine"}},
        )

        assert response.status_code == 403


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPIDeleteCollection:
    """Test deleting collections requires owner permission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_collection_requires_owner_permission(self, mock_admin_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated admin with owner permission
        WHEN: Deleting a collection
        THEN: Should return 200 OK
        """
        app = create_test_app_with_mocks(
            mock_user=mock_admin_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.delete("/collections/test-collection")

        assert response.status_code == 200

    def test_delete_collection_denied_for_editor(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user with only editor permission
        WHEN: Deleting a collection
        THEN: Should return 403 Forbidden
        """
        # Mock: owner=False (deny owner permission)
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.delete("/collections/test-collection")

        assert response.status_code == 403


@pytest.mark.xdist_group(name="test_vectors_api")
class TestVectorsAPISearch:
    """Test searching vectors requires viewer permission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_vectors_with_viewer_permission(self, mock_current_user, mock_openfga_client, mock_qdrant_client):
        """
        GIVEN: Authenticated user with viewer permission
        WHEN: Searching vectors
        THEN: Should return 200 with search results
        """
        app = create_test_app_with_mocks(
            mock_user=mock_current_user,
            mock_openfga=mock_openfga_client,
            mock_qdrant=mock_qdrant_client,
        )
        client = TestClient(app)

        response = client.post(
            "/search",
            json={"collection_name": "test-collection", "query_vector": [0.1] * 768, "limit": 10},
        )

        assert response.status_code == 200
