"""
Tests for Marketplace Admin API endpoints.

These endpoints allow admin users to manage skill marketplaces,
including registering new marketplaces, syncing skills, and
listing available skills from each marketplace.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.skills]


@pytest.fixture
def mock_marketplace_registry():
    """Create a mock marketplace registry."""
    registry = MagicMock()
    registry.list_marketplaces.return_value = [
        {
            "name": "anthropic",
            "uri": "https://github.com/anthropics/skills",
            "type": "github",
            "trusted": True,
            "auto_sync": True,
            "skill_count": 16,
        },
        {
            "name": "enterprise",
            "uri": "https://github.com/myorg/skills",
            "type": "github",
            "trusted": True,
            "auto_sync": False,
            "skill_count": 5,
        },
    ]
    registry.get_marketplace.return_value = {
        "name": "anthropic",
        "uri": "https://github.com/anthropics/skills",
        "type": "github",
        "trusted": True,
        "auto_sync": True,
        "skill_count": 16,
        "last_sync": "2025-12-20T10:00:00Z",
    }
    registry.register_marketplace = AsyncMock(return_value=True)
    registry.remove_marketplace = AsyncMock(return_value=True)
    registry.sync_marketplace = AsyncMock(return_value={"synced": 16, "new": 2, "updated": 1})
    registry.list_skills.return_value = [
        {"name": "pdf", "description": "PDF document handling"},
        {"name": "docx", "description": "Word document handling"},
    ]
    return registry


@pytest.fixture
def app_with_marketplace(mock_marketplace_registry):
    """Create a test app with marketplace routes."""
    from mcp_server_langgraph.api.v1.marketplace_admin import (
        create_marketplace_router,
    )
    from mcp_server_langgraph.auth.dependencies import get_current_user, require_admin

    app = FastAPI()
    router = create_marketplace_router(mock_marketplace_registry)
    app.include_router(router, prefix="/api/v1/admin")

    # Mock authentication - return an admin user
    mock_user = {
        "sub": "admin-user-id",
        "user_id": "admin-user-id",
        "username": "admin",
        "roles": ["admin"],
        "realm_access": {"roles": ["admin"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: mock_user

    return app


@pytest.mark.xdist_group(name="test_marketplace_admin_list")
class TestMarketplaceAdminList:
    """Tests for listing marketplaces."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_marketplaces_returns_all(self, app_with_marketplace, mock_marketplace_registry):
        """Test listing all registered marketplaces."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces")

        assert response.status_code == 200
        data = response.json()
        assert "marketplaces" in data
        assert len(data["marketplaces"]) == 2
        assert data["marketplaces"][0]["name"] == "anthropic"

    @pytest.mark.asyncio
    async def test_list_marketplaces_includes_skill_count(self, app_with_marketplace, mock_marketplace_registry):
        """Test that marketplace listing includes skill counts."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces")

        data = response.json()
        assert data["marketplaces"][0]["skill_count"] == 16


@pytest.mark.xdist_group(name="test_marketplace_admin_register")
class TestMarketplaceAdminRegister:
    """Tests for registering new marketplaces."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_register_marketplace_success(self, app_with_marketplace, mock_marketplace_registry):
        """Test registering a new marketplace."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/admin/marketplaces",
                json={
                    "name": "custom",
                    "uri": "https://github.com/custom/skills",
                    "type": "github",
                    "trusted": False,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        mock_marketplace_registry.register_marketplace.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_marketplace_validates_uri(self, app_with_marketplace, mock_marketplace_registry):
        """Test that marketplace registration validates URI format."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/admin/marketplaces",
                json={
                    "name": "invalid",
                    "uri": "not-a-valid-uri",
                    "type": "github",
                },
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_marketplace_requires_name(self, app_with_marketplace, mock_marketplace_registry):
        """Test that marketplace name is required."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/admin/marketplaces",
                json={
                    "uri": "https://github.com/org/skills",
                    "type": "github",
                },
            )

        assert response.status_code == 422


@pytest.mark.xdist_group(name="test_marketplace_admin_remove")
class TestMarketplaceAdminRemove:
    """Tests for removing marketplaces."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_remove_marketplace_success(self, app_with_marketplace, mock_marketplace_registry):
        """Test removing a marketplace."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/admin/marketplaces/enterprise")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_marketplace_registry.remove_marketplace.assert_called_once_with("enterprise")

    @pytest.mark.asyncio
    async def test_remove_anthropic_marketplace_forbidden(self, app_with_marketplace, mock_marketplace_registry):
        """Test that the default Anthropic marketplace cannot be removed."""
        mock_marketplace_registry.remove_marketplace = AsyncMock(
            side_effect=ValueError("Cannot remove default Anthropic marketplace")
        )

        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/admin/marketplaces/anthropic")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remove_nonexistent_marketplace(self, app_with_marketplace, mock_marketplace_registry):
        """Test removing a marketplace that doesn't exist."""
        mock_marketplace_registry.remove_marketplace = AsyncMock(side_effect=KeyError("Marketplace not found"))

        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/admin/marketplaces/nonexistent")

        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_marketplace_admin_sync")
class TestMarketplaceAdminSync:
    """Tests for syncing marketplaces."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sync_marketplace_success(self, app_with_marketplace, mock_marketplace_registry):
        """Test syncing a marketplace."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/admin/marketplaces/anthropic/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced"] == 16
        assert data["new"] == 2

    @pytest.mark.asyncio
    async def test_sync_nonexistent_marketplace(self, app_with_marketplace, mock_marketplace_registry):
        """Test syncing a marketplace that doesn't exist."""
        mock_marketplace_registry.sync_marketplace = AsyncMock(side_effect=KeyError("Marketplace not found"))

        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/admin/marketplaces/unknown/sync")

        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_marketplace_admin_skills")
class TestMarketplaceAdminSkills:
    """Tests for listing skills from a marketplace."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_skills_from_marketplace(self, app_with_marketplace, mock_marketplace_registry):
        """Test listing skills from a specific marketplace."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces/anthropic/skills")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert len(data["skills"]) == 2
        assert data["skills"][0]["name"] == "pdf"

    @pytest.mark.asyncio
    async def test_list_skills_from_nonexistent_marketplace(self, app_with_marketplace, mock_marketplace_registry):
        """Test listing skills from a marketplace that doesn't exist."""
        mock_marketplace_registry.list_skills = MagicMock(side_effect=KeyError("Marketplace not found"))

        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces/unknown/skills")

        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_marketplace_admin_get_single")
class TestMarketplaceAdminGetSingle:
    """Tests for getting a single marketplace."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_marketplace_details(self, app_with_marketplace, mock_marketplace_registry):
        """Test getting details for a specific marketplace."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces/anthropic")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "anthropic"
        assert data["skill_count"] == 16
        assert "last_sync" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_marketplace(self, app_with_marketplace, mock_marketplace_registry):
        """Test getting a marketplace that doesn't exist."""
        mock_marketplace_registry.get_marketplace = MagicMock(side_effect=KeyError("Marketplace not found"))

        async with AsyncClient(
            transport=ASGITransport(app=app_with_marketplace),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/admin/marketplaces/unknown")

        assert response.status_code == 404
