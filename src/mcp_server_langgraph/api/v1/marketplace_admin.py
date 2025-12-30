"""
Marketplace Admin API endpoints.

Provides admin-only endpoints for managing skill marketplaces:
- List registered marketplaces
- Register new marketplaces
- Remove marketplaces
- Force sync marketplaces
- List skills from a marketplace

These endpoints require admin persona permissions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from mcp_server_langgraph.auth.dependencies import require_admin

if TYPE_CHECKING:
    pass

# Type alias for admin user dependency
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]


class MarketplaceRegistry(Protocol):
    """Protocol for marketplace registry implementations."""

    def list_marketplaces(self) -> list[dict[str, Any]]:
        """List all registered marketplaces."""
        ...

    def get_marketplace(self, name: str) -> dict[str, Any]:
        """Get details for a specific marketplace."""
        ...

    async def register_marketplace(
        self,
        name: str,
        uri: str,
        marketplace_type: str,
        trusted: bool,
        auto_sync: bool,
        required_approval: bool,
    ) -> bool:
        """Register a new marketplace."""
        ...

    async def remove_marketplace(self, name: str) -> bool:
        """Remove a marketplace."""
        ...

    async def sync_marketplace(self, name: str) -> dict[str, int]:
        """Sync skills from a marketplace."""
        ...

    def list_skills(self, marketplace_name: str) -> list[dict[str, Any]]:
        """List skills from a specific marketplace."""
        ...


class MarketplaceCreateRequest(BaseModel):
    """Request body for creating a new marketplace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique name for the marketplace",
    )
    uri: str = Field(
        ...,
        description="URI for the marketplace (GitHub URL, OCI registry, etc.)",
    )
    type: str = Field(
        default="github",
        description="Marketplace type: github, registry, or oci",
    )
    trusted: bool = Field(
        default=False,
        description="Whether skills from this marketplace are trusted",
    )
    auto_sync: bool = Field(
        default=False,
        description="Whether to automatically sync skills",
    )
    required_approval: bool = Field(
        default=True,
        description="Whether skills require admin approval before use",
    )

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate that URI is a proper URL."""
        uri_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        if not uri_pattern.match(v):
            raise ValueError("Invalid URI format")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate marketplace name format."""
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError("Name must start with lowercase letter and contain only lowercase letters, numbers, and hyphens")
        return v


class MarketplaceResponse(BaseModel):
    """Response for marketplace operations."""

    success: bool
    message: str | None = None


class MarketplaceListResponse(BaseModel):
    """Response for listing marketplaces."""

    marketplaces: list[dict[str, Any]]


class MarketplaceSyncResponse(BaseModel):
    """Response for sync operations."""

    synced: int
    new: int
    updated: int


class SkillListResponse(BaseModel):
    """Response for listing skills."""

    skills: list[dict[str, Any]]


def create_marketplace_router(registry: MarketplaceRegistry) -> APIRouter:
    """Create the marketplace admin router.

    Args:
        registry: The marketplace registry to use

    Returns:
        Configured APIRouter with all marketplace endpoints
    """
    router = APIRouter(prefix="/marketplaces", tags=["marketplace-admin"])

    @router.get("", response_model=MarketplaceListResponse)
    async def list_marketplaces(admin_user: AdminUser) -> MarketplaceListResponse:
        """List all registered skill marketplaces.

        Requires admin authorization.

        Returns list of marketplaces with their configuration and skill counts.
        """
        marketplaces = registry.list_marketplaces()
        return MarketplaceListResponse(marketplaces=marketplaces)

    @router.get("/{name}")
    async def get_marketplace(name: str, admin_user: AdminUser) -> dict[str, Any]:
        """Get details for a specific marketplace.

        Requires admin authorization.

        Args:
            name: Marketplace name

        Returns:
            Marketplace details including last sync time
        """
        try:
            return registry.get_marketplace(name)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Marketplace '{name}' not found",
            )

    @router.post("", response_model=MarketplaceResponse, status_code=201)
    async def register_marketplace(
        request: MarketplaceCreateRequest,
        admin_user: AdminUser,
    ) -> MarketplaceResponse:
        """Register a new skill marketplace.

        Requires admin authorization.

        Non-Anthropic marketplaces require admin approval for skills.
        """
        try:
            await registry.register_marketplace(
                name=request.name,
                uri=request.uri,
                marketplace_type=request.type,
                trusted=request.trusted,
                auto_sync=request.auto_sync,
                required_approval=request.required_approval,
            )
            return MarketplaceResponse(
                success=True,
                message=f"Marketplace '{request.name}' registered successfully",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.delete("/{name}", response_model=MarketplaceResponse)
    async def remove_marketplace(name: str, admin_user: AdminUser) -> MarketplaceResponse:
        """Remove a marketplace.

        Requires admin authorization.

        The default Anthropic marketplace cannot be removed.
        """
        try:
            await registry.remove_marketplace(name)
            return MarketplaceResponse(
                success=True,
                message=f"Marketplace '{name}' removed successfully",
            )
        except ValueError as e:
            # Cannot remove protected marketplace
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Marketplace '{name}' not found",
            )

    @router.post("/{name}/sync", response_model=MarketplaceSyncResponse)
    async def sync_marketplace(name: str, admin_user: AdminUser) -> MarketplaceSyncResponse:
        """Force sync skills from a marketplace.

        Requires admin authorization.

        Fetches latest skills from the marketplace source.
        """
        try:
            result = await registry.sync_marketplace(name)
            return MarketplaceSyncResponse(
                synced=result.get("synced", 0),
                new=result.get("new", 0),
                updated=result.get("updated", 0),
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Marketplace '{name}' not found",
            )

    @router.get("/{name}/skills", response_model=SkillListResponse)
    async def list_marketplace_skills(name: str, admin_user: AdminUser) -> SkillListResponse:
        """List all skills from a specific marketplace.

        Requires admin authorization.

        Returns skill names and descriptions.
        """
        try:
            skills = registry.list_skills(name)
            return SkillListResponse(skills=skills)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Marketplace '{name}' not found",
            )

    return router
