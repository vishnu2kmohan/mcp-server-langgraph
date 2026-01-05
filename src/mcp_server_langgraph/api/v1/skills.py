"""
Skills API Endpoints.

Provides REST API for skill management and auto-update operations.

Endpoints:
- GET /admin/skills/list - List skills from a marketplace
- POST /admin/skills/install - Install a skill
- GET /admin/skills/installed - List installed skills
- DELETE /admin/skills/{skill_name} - Uninstall a skill
- GET /admin/skills/updates - Check for skill updates
- POST /admin/skills/updates/apply - Apply all available updates
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import require_admin
from mcp_server_langgraph.skills.auto_update import get_auto_update_scheduler
from mcp_server_langgraph.skills.installer import SkillInstaller
from mcp_server_langgraph.skills.marketplace import MarketplaceClient, MarketplaceRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/skills", tags=["skills"])

# Type alias for admin user dependency
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]


# =============================================================================
# Request/Response Models
# =============================================================================


class SkillMetadata(BaseModel):
    """Skill metadata returned from marketplace listings."""

    name: str = Field(description="Skill name (unique identifier)")
    description: str = Field(default="", description="Skill description")
    version: str = Field(default="latest", description="Skill version")
    author: str = Field(default="", description="Skill author")
    tags: list[str] = Field(default_factory=list, description="Skill tags")
    source: str | None = Field(default=None, description="Source marketplace")


class SkillListResponse(BaseModel):
    """Response for listing marketplace skills."""

    skills: list[SkillMetadata]
    total: int
    marketplace: str
    cached: bool = False


class SkillInstallRequest(BaseModel):
    """Request body for skill installation."""

    skill_name: str = Field(description="Name of skill to install")
    marketplace: str = Field(default="anthropic", description="Source marketplace")
    version: str | None = Field(default=None, description="Specific version (latest if not specified)")


class InstalledSkillsResponse(BaseModel):
    """Response for listing installed skills."""

    skills: list[str]
    count: int


class UninstallResponse(BaseModel):
    """Response for skill uninstallation."""

    success: bool
    skill_name: str
    message: str = ""


# =============================================================================
# Helper Functions
# =============================================================================


async def list_skills_from_marketplace(
    marketplace_name: str,
    search: str | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List skills from a marketplace with optional filtering.

    Args:
        marketplace_name: Name of the marketplace
        search: Optional search query
        tags: Optional list of tags to filter by

    Returns:
        List of skill metadata dictionaries
    """
    registry = MarketplaceRegistry()
    client = MarketplaceClient()

    marketplace = registry.get(marketplace_name)
    if marketplace is None:
        raise ValueError(f"Unknown marketplace: {marketplace_name}")

    skills = await client.list_skills(marketplace)

    # Apply search filter
    if search:
        search_lower = search.lower()
        skills = [
            s for s in skills if search_lower in s.get("name", "").lower() or search_lower in s.get("description", "").lower()
        ]

    # Apply tags filter
    if tags:
        skills = [s for s in skills if any(t in s.get("tags", []) for t in tags)]

    return skills


async def install_skill(
    skill_name: str,
    marketplace: str = "anthropic",
    version: str | None = None,
) -> dict[str, Any]:
    """Install a skill from a marketplace.

    Args:
        skill_name: Name of skill to install
        marketplace: Source marketplace name
        version: Optional specific version

    Returns:
        Installation result dictionary
    """
    installer = SkillInstaller()
    result = await installer.install(skill_name, source=marketplace, version=version)
    return result.model_dump()


async def list_installed_skills() -> list[str]:
    """List all installed skills.

    Returns:
        List of installed skill names
    """
    installer = SkillInstaller()
    return installer.list_installed()


async def uninstall_skill(skill_name: str) -> bool:
    """Uninstall a skill.

    Args:
        skill_name: Name of skill to uninstall

    Returns:
        True if skill was uninstalled
    """
    installer = SkillInstaller()
    return await installer.uninstall(skill_name)


# =============================================================================
# API Endpoints - Marketplace Operations
# =============================================================================


@router.get("/list")
async def list_marketplace_skills_endpoint(
    admin_user: AdminUser,
    marketplace: str = Query(default="anthropic", description="Marketplace name"),
    search: str | None = Query(default=None, description="Search query"),
    tags: str | None = Query(default=None, description="Comma-separated tags"),
) -> dict[str, Any]:
    """List skills from a marketplace.

    Query Parameters:
        marketplace: Marketplace name (default: anthropic)
        search: Optional search query to filter skills
        tags: Optional comma-separated tags to filter by

    Returns:
        List of skills with metadata
    """
    try:
        tags_list = tags.split(",") if tags else None
        skills = await list_skills_from_marketplace(marketplace, search=search, tags=tags_list)

        return {
            "skills": skills,
            "total": len(skills),
            "marketplace": marketplace,
            "cached": False,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to list marketplace skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skills: {e}",
        )


@router.post("/install")
async def install_skill_endpoint(
    admin_user: AdminUser,
    request: SkillInstallRequest,
) -> dict[str, Any]:
    """Install a skill from a marketplace.

    Request Body:
        skill_name: Name of the skill to install
        marketplace: Source marketplace (default: anthropic)
        version: Optional specific version

    Returns:
        Installation result with success/failure details
    """
    try:
        result = await install_skill(
            skill_name=request.skill_name,
            marketplace=request.marketplace,
            version=request.version,
        )
        return result
    except Exception as e:
        logger.exception(f"Failed to install skill {request.skill_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install skill: {e}",
        )


@router.get("/installed")
async def list_installed_skills_endpoint(
    admin_user: AdminUser,
) -> dict[str, Any]:
    """List all installed skills.

    Returns:
        List of installed skill names
    """
    try:
        skills = await list_installed_skills()
        return {
            "skills": skills,
            "count": len(skills),
        }
    except Exception as e:
        logger.exception(f"Failed to list installed skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list installed skills: {e}",
        )


@router.delete("/{skill_name}")
async def uninstall_skill_endpoint(
    admin_user: AdminUser,
    skill_name: str,
) -> dict[str, Any]:
    """Uninstall a skill.

    Path Parameters:
        skill_name: Name of the skill to uninstall

    Returns:
        Uninstall result
    """
    try:
        success = await uninstall_skill(skill_name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill not found: {skill_name}",
            )
        return {
            "success": True,
            "skill_name": skill_name,
            "message": f"Skill {skill_name} uninstalled successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to uninstall skill {skill_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to uninstall skill: {e}",
        )


# =============================================================================
# API Endpoints - Auto-Update Operations
# =============================================================================


@router.get("/updates")
async def check_skill_updates(admin_user: AdminUser) -> dict[str, Any]:
    """Check for available skill updates.

    Requires admin authorization.

    Returns:
        Dict with list of available updates
    """
    try:
        scheduler = get_auto_update_scheduler()
        updates = await scheduler.check_updates_available()

        return {
            "updates": [
                {
                    "skill_name": u.skill_name,
                    "current_version": u.current_version,
                    "new_version": u.new_version,
                    "marketplace": u.marketplace,
                    "changelog": u.changelog,
                }
                for u in updates
            ],
            "count": len(updates),
        }
    except Exception as e:
        logger.exception(f"Failed to check skill updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check updates: {e}",
        )


@router.post("/updates/apply")
async def apply_skill_updates(admin_user: AdminUser) -> dict[str, Any]:
    """Apply all available skill updates.

    Requires admin authorization.

    Returns:
        Dict with list of applied updates
    """
    try:
        scheduler = get_auto_update_scheduler()
        results = await scheduler.apply_updates()

        return {
            "applied": results,
            "count": len(results),
            "success_count": sum(1 for r in results if r.get("success", False)),
        }
    except Exception as e:
        logger.exception(f"Failed to apply skill updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply updates: {e}",
        )
