"""
KB (Knowledge Base) Status API

Provides status information about the Knowledge Base / DynamicContextLoader
for frontend integration.

Endpoints:
- GET /status - Get current KB status, collection info, and embedding config

Reference:
- ADR-0068 - Gateway-Level Authentication
- DynamicContextLoader - src/mcp_server_langgraph/core/dynamic_context_loader.py
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(prefix="", tags=["kb"])


# =============================================================================
# Enums and Response Models
# =============================================================================


class KBStatus(str, Enum):
    """KB status enumeration."""

    READY = "ready"
    MISCONFIGURED = "misconfigured"
    UNAVAILABLE = "unavailable"


class KBStatusResponse(BaseModel):
    """Response model for KB status endpoint."""

    status: str = Field(..., description="KB status: ready, misconfigured, or unavailable")
    qdrant_connected: bool = Field(..., description="Whether Qdrant is connected")
    collection_name: str | None = Field(None, description="Active collection name")
    vectors_count: int = Field(0, description="Number of vectors in collection")
    embedding_provider: str | None = Field(None, description="Embedding provider (google_vertex, openai, etc.)")
    embedding_model: str | None = Field(None, description="Embedding model name")
    embedding_dimensions: int | None = Field(None, description="Embedding vector dimensions")
    last_updated: str | None = Field(None, description="ISO timestamp of last update")
    context_token_budget: int | None = Field(None, description="Max tokens for context loading")
    context_top_k: int | None = Field(None, description="Number of top results for context")
    message: str | None = Field(None, description="Status message or error details")


# =============================================================================
# Helper Functions
# =============================================================================


async def get_kb_status() -> dict[str, Any]:
    """Get current KB status by checking Qdrant and embedding configuration.

    Returns:
        Dictionary with KB status information.
    """
    result: dict[str, Any] = {
        "status": KBStatus.MISCONFIGURED.value,
        "qdrant_connected": False,
        "collection_name": None,
        "vectors_count": 0,
        "embedding_provider": None,
        "embedding_model": None,
        "embedding_dimensions": None,
        "last_updated": None,
        "context_token_budget": None,
        "context_top_k": None,
        "message": None,
    }

    # Check if dynamic context loading is enabled
    if not settings.enable_dynamic_context_loading:
        result["status"] = KBStatus.MISCONFIGURED.value
        result["message"] = "Dynamic context loading is disabled. Set ENABLE_DYNAMIC_CONTEXT_LOADING=true."
        return result

    # Check Qdrant configuration
    qdrant_url = settings.qdrant_url
    if not qdrant_url:
        result["status"] = KBStatus.MISCONFIGURED.value
        result["message"] = "Qdrant URL not configured. Set QDRANT_URL environment variable."
        return result

    # Get embedding configuration
    result["embedding_provider"] = settings.embedding_provider
    result["embedding_model"] = settings.embedding_model_name
    result["embedding_dimensions"] = settings.embedding_dimensions
    result["context_token_budget"] = getattr(settings, "dynamic_context_max_tokens", 2000)
    result["context_top_k"] = getattr(settings, "dynamic_context_top_k", 5)
    result["collection_name"] = settings.qdrant_collection_name

    # Try to connect to Qdrant and get collection info
    try:
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_async_qdrant_client,
        )

        client = await get_shared_async_qdrant_client()
        # get_shared_async_qdrant_client() raises RuntimeError if unavailable
        # (never returns None), so client is always valid here

        result["qdrant_connected"] = True

        # Get collection info
        collection_name = settings.qdrant_collection_name
        if collection_name:
            try:
                collection_info = await client.get_collection(collection_name)
                result["vectors_count"] = collection_info.points_count or 0
                result["last_updated"] = datetime.utcnow().isoformat() + "Z"
                result["status"] = KBStatus.READY.value
            except Exception as e:
                # Collection might not exist yet
                logger.warning(f"Collection {collection_name} not found: {e}")
                result["status"] = KBStatus.READY.value  # Still ready, just empty
                result["vectors_count"] = 0
                result["message"] = f"Collection '{collection_name}' is empty or not yet created."
        else:
            result["status"] = KBStatus.MISCONFIGURED.value
            result["message"] = "Collection name not configured. Set QDRANT_COLLECTION_NAME."

    except Exception as e:
        logger.error(f"Error checking KB status: {e}")
        result["status"] = KBStatus.UNAVAILABLE.value
        result["qdrant_connected"] = False
        result["message"] = f"Unable to connect to Qdrant at {qdrant_url}"

    return result


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=KBStatusResponse,
    summary="Get KB Status",
    description="Get current Knowledge Base status including Qdrant connection and embedding configuration.",
)
async def get_status(
    _current_user: Any = Depends(get_current_user),
) -> KBStatusResponse:
    """Get current KB status.

    Returns:
        KBStatusResponse with current KB configuration and connection status.

    Raises:
        HTTPException: 500 if an unexpected error occurs.
    """
    try:
        status_data = await get_kb_status()
        return KBStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Error getting KB status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting KB status: {str(e)}",
        ) from e
