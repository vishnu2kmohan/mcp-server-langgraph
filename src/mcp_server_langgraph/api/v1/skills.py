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
from typing import TYPE_CHECKING, Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import (
    require_skill_viewer_global,
    require_skill_author_global,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import (
        EmbeddingServiceProtocol,
        VectorProviderProtocol,
    )
from mcp_server_langgraph.skills.auto_update import get_auto_update_scheduler
from mcp_server_langgraph.skills.installer import SkillInstaller
from mcp_server_langgraph.skills.marketplace import (
    MarketplaceRegistry,
    create_marketplace_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/skills", tags=["skills"])

# Type aliases for OpenFGA authorization dependencies
# Viewer: Can browse/list skills (admin, alice, bob)
# Author: Can install/uninstall/update skills (admin, alice)
SkillViewer = Annotated[dict[str, Any], Depends(require_skill_viewer_global)]
SkillAuthor = Annotated[dict[str, Any], Depends(require_skill_author_global)]


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
    # AgentSkills.io compliance fields (Appendix B)
    license: str = Field(default="", description="License identifier (e.g., MIT, Apache-2.0)")
    allowed_tools: list[str] = Field(default_factory=list, description="Pre-approved tools this skill can use")
    category: str = Field(default="", description="Skill category")


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
    client = create_marketplace_client()

    marketplace = registry.get(marketplace_name)
    if marketplace is None:
        raise ValueError(f"Unknown marketplace: {marketplace_name}")

    skills = await client.list_skills_with_metadata(marketplace)

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
    user: SkillViewer,
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
    user: SkillAuthor,
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
    user: SkillViewer,
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
    user: SkillAuthor,
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
async def check_skill_updates(user: SkillViewer) -> dict[str, Any]:
    """Check for available skill updates.

    Requires skill:viewer authorization (all authenticated users with skill access).

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
async def apply_skill_updates(user: SkillAuthor) -> dict[str, Any]:
    """Apply all available skill updates.

    Requires skill:author authorization (alice and admin can apply updates).

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


# =============================================================================
# Semantic Search Models
# =============================================================================


class SemanticSkillSearchRequest(BaseModel):
    """Request body for semantic skill search."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SemanticSkillSearchResult(BaseModel):
    """A single semantic search result."""

    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    tags: list[str] = Field(default_factory=list, description="Skill tags")


class SemanticSkillSearchResponse(BaseModel):
    """Response for semantic skill search."""

    query: str = Field(..., description="Original search query")
    results: list[SemanticSkillSearchResult] = Field(..., description="Search results ordered by score")
    total_results: int = Field(..., description="Number of results returned")


# =============================================================================
# Semantic Search Provider Functions
# =============================================================================


def get_vector_provider() -> VectorProviderProtocol:
    """Get the vector provider for semantic search.

    Returns:
        Vector provider instance (Qdrant, pgvector, or in-memory)

    Raises:
        HTTPException: If vector provider is not available
    """
    try:
        from mcp_server_langgraph.storage.vectors import get_vector_provider as _get_provider

        provider = _get_provider()
        if provider is None:
            raise HTTPException(
                status_code=503,
                detail="Vector provider not available. Ensure Qdrant or pgvector is configured.",
            )
        # Cast: VectorSearchProvider implements VectorProviderProtocol semantically
        return cast("VectorProviderProtocol", provider)
    except ImportError as e:
        logger.warning(f"Vector provider import failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Vector storage not configured",
        ) from e


def get_embedding_service() -> EmbeddingServiceProtocol:
    """Get the embedding service for generating query vectors.

    Returns:
        Embedding service instance

    Raises:
        HTTPException: If embedding service is not available
    """
    try:
        from mcp_server_langgraph.llm.embeddings import get_embedding_service as _get_service

        service = _get_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="Embedding service not available. Ensure LLM provider is configured.",
            )
        return service
    except ImportError as e:
        logger.warning(f"Embedding service import failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service not configured",
        ) from e


# =============================================================================
# Semantic Search Endpoint
# =============================================================================


@router.post(
    "/semantic-search",
    summary="Semantic skill search",
    description="Find skills using natural language query via vector similarity search",
    response_model=SemanticSkillSearchResponse,
)
async def semantic_search_skills(
    request: SemanticSkillSearchRequest,
    user: SkillViewer,
) -> SemanticSkillSearchResponse:
    """Search for skills using semantic similarity.

    This endpoint uses vector embeddings to find skills that semantically
    match the user's natural language query. Requires the
    enable_semantic_skill_search feature flag to be enabled.

    Args:
        request: Search request with query and options
        user: Authenticated user with skill:viewer access

    Returns:
        Semantic search results with similarity scores

    Raises:
        HTTPException: 404 if feature not enabled, 503 if services unavailable
    """
    # Check feature flag
    if not feature_flags.enable_semantic_skill_search:
        raise HTTPException(
            status_code=404,
            detail="Semantic skill search is not enabled. Set FF_ENABLE_SEMANTIC_SKILL_SEARCH=true to activate.",
        )

    # Get services
    vector_provider = get_vector_provider()
    embedding_service = get_embedding_service()

    # Generate query embedding
    query_vector = await embedding_service.embed(request.query)

    # Search vector store
    raw_results = await vector_provider.search(
        collection="skills",
        query_vector=query_vector,
        limit=request.limit,
        min_score=request.min_score,
    )

    # Transform results to response model
    results = [
        SemanticSkillSearchResult(
            skill_id=r.get("id", ""),
            name=r.get("metadata", {}).get("name", ""),
            description=r.get("metadata", {}).get("description", ""),
            score=r.get("score", 0.0),
            tags=r.get("metadata", {}).get("tags", []),
        )
        for r in raw_results
    ]

    logger.info(
        f"Semantic skill search for '{request.query[:50]}...' returned {len(results)} results",
        extra={
            "user_id": user.get("sub", "unknown"),
            "query": request.query[:100],
            "result_count": len(results),
        },
    )

    return SemanticSkillSearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )
