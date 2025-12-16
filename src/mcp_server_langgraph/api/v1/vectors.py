"""
Protected Qdrant Vector Database Proxy

All Qdrant operations go through this proxy with:
- Keycloak JWT authentication via get_current_user dependency
- OpenFGA authorization checks for fine-grained permissions

Permission Model (vector_store type):
- viewer: Can list collections and search vectors
- editor: Can create collections and upsert points (includes viewer)
- owner: Can delete collections (includes editor)

Routes:
- GET  /collections           - List collections (viewer)
- POST /collections           - Create collection (editor)
- DELETE /collections/{name}  - Delete collection (owner)
- POST /search                - Search vectors (viewer)
- POST /points                - Upsert points (editor)

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.dependencies import get_openfga_client
from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(prefix="", tags=["vectors"])

# Default vector store object for authorization
DEFAULT_VECTOR_STORE = "vector_store:default"


# Request/Response models
class VectorConfig(BaseModel):
    """Vector configuration for collection creation."""

    size: int = Field(..., description="Vector dimension size", ge=1)
    distance: str = Field(default="Cosine", description="Distance metric: Cosine, Euclidean, Dot")


class CreateCollectionRequest(BaseModel):
    """Request to create a new collection."""

    name: str = Field(..., description="Collection name", min_length=1, max_length=255)
    vectors: VectorConfig = Field(..., description="Vector configuration")


class SearchRequest(BaseModel):
    """Request to search vectors."""

    collection_name: str = Field(..., description="Collection to search in")
    query_vector: list[float] = Field(..., description="Query vector")
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)


class TextSearchRequest(BaseModel):
    """Request to search vectors using text (will be embedded)."""

    collection_name: str = Field(..., description="Collection to search in")
    query_text: str = Field(..., description="Query text to embed and search", min_length=1)
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)


class TextUpsertRequest(BaseModel):
    """Request to upsert a text document (will be embedded)."""

    collection_name: str = Field(..., description="Target collection")
    text: str = Field(..., description="Text content to embed and store", min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata to store with the point")


class UpsertPointsRequest(BaseModel):
    """Request to upsert points into a collection."""

    collection_name: str = Field(..., description="Target collection")
    points: list[dict[str, Any]] = Field(..., description="Points to upsert")


# Dependency providers
# NOTE: get_openfga_client is imported from core.dependencies (centralized singleton)


def get_qdrant_client() -> Any:
    """Get Qdrant client instance."""
    # Lazy import to avoid import errors if qdrant-client not installed
    from qdrant_client import QdrantClient

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=qdrant_url)


def get_embedding_model() -> Any:
    """
    Get embedding model for text-to-vector conversion.

    Uses LangChain embeddings based on configured provider.

    Returns:
        Embeddings model instance with embed_query method.
    """
    from mcp_server_langgraph.core.config import settings

    provider = settings.embedding_provider
    model_name = settings.embedding_model_name

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model_name)
    elif provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=model_name)
    elif provider in ("huggingface", "local"):
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name)
    else:
        # Default to OpenAI (already imported with type: ignore above)
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model_name or "text-embedding-3-small")


async def require_viewer_permission(
    current_user: dict[str, Any] = Depends(get_current_user),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> dict[str, Any]:
    """Require viewer permission on vector_store:default."""
    # get_current_user returns dict with 'user_id' already in "user:username" format
    user_id = current_user.get("user_id") or f"user:{current_user.get('username', 'unknown')}"

    try:
        allowed = await openfga.check_permission(
            user=user_id,
            relation="viewer",
            object=DEFAULT_VECTOR_STORE,
        )
    finally:
        await openfga.close()

    if not allowed:
        logger.warning(
            "Vector store access denied",
            extra={"user": user_id, "permission": "viewer", "object": DEFAULT_VECTOR_STORE},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access vector store",
        )

    return current_user


async def require_editor_permission(
    current_user: dict[str, Any] = Depends(get_current_user),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> dict[str, Any]:
    """Require editor permission on vector_store:default."""
    # get_current_user returns dict with 'user_id' already in "user:username" format
    user_id = current_user.get("user_id") or f"user:{current_user.get('username', 'unknown')}"

    try:
        allowed = await openfga.check_permission(
            user=user_id,
            relation="editor",
            object=DEFAULT_VECTOR_STORE,
        )
    finally:
        await openfga.close()

    if not allowed:
        logger.warning(
            "Vector store write denied",
            extra={"user": user_id, "permission": "editor", "object": DEFAULT_VECTOR_STORE},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify vector store",
        )

    return current_user


async def require_owner_permission(
    current_user: dict[str, Any] = Depends(get_current_user),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> dict[str, Any]:
    """Require owner permission on vector_store:default."""
    # get_current_user returns dict with 'user_id' already in "user:username" format
    user_id = current_user.get("user_id") or f"user:{current_user.get('username', 'unknown')}"

    try:
        allowed = await openfga.check_permission(
            user=user_id,
            relation="owner",
            object=DEFAULT_VECTOR_STORE,
        )
    finally:
        await openfga.close()

    if not allowed:
        logger.warning(
            "Vector store delete denied",
            extra={"user": user_id, "permission": "owner", "object": DEFAULT_VECTOR_STORE},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete from vector store",
        )

    return current_user


@router.get("/collections")
async def list_collections(
    current_user: dict[str, Any] = Depends(require_viewer_permission),
    qdrant: Any = Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    List all vector collections.

    Requires: viewer permission on vector_store:default
    """
    try:
        collections = qdrant.get_collections()
        return {
            "collections": [
                {"name": c.name, "vectors_count": getattr(c, "vectors_count", None)} for c in collections.collections
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list collections",
        )


@router.post("/collections", status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CreateCollectionRequest,
    current_user: dict[str, Any] = Depends(require_editor_permission),
    qdrant: Any = Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    Create a new vector collection.

    Requires: editor permission on vector_store:default
    """
    from qdrant_client.models import Distance, VectorParams

    distance_map = {
        "Cosine": Distance.COSINE,
        "Euclidean": Distance.EUCLID,
        "Dot": Distance.DOT,
    }

    try:
        qdrant.create_collection(
            collection_name=request.name,
            vectors_config=VectorParams(
                size=request.vectors.size,
                distance=distance_map.get(request.vectors.distance, Distance.COSINE),
            ),
        )

        logger.info(
            "Collection created",
            extra={
                "collection": request.name,
                "user": current_user.get("username"),
            },
        )

        return {"name": request.name, "status": "created"}
    except Exception as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {e}",
        )


@router.delete("/collections/{collection_name}")
async def delete_collection(
    collection_name: str,
    current_user: dict[str, Any] = Depends(require_owner_permission),
    qdrant: Any = Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    Delete a vector collection.

    Requires: owner permission on vector_store:default
    """
    try:
        qdrant.delete_collection(collection_name=collection_name)

        logger.info(
            "Collection deleted",
            extra={
                "collection": collection_name,
                "user": current_user.get("username"),
            },
        )

        return {"name": collection_name, "status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {e}",
        )


@router.post("/search")
async def search_vectors(
    request: SearchRequest,
    current_user: dict[str, Any] = Depends(require_viewer_permission),
    qdrant: Any = Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    Search for similar vectors in a collection.

    Requires: viewer permission on vector_store:default
    """
    try:
        results = qdrant.search(
            collection_name=request.collection_name,
            query_vector=request.query_vector,
            limit=request.limit,
        )

        return {
            "results": [
                {
                    "id": str(r.id),
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Failed to search vectors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search vectors: {e}",
        )


@router.post("/points")
async def upsert_points(
    request: UpsertPointsRequest,
    current_user: dict[str, Any] = Depends(require_editor_permission),
    qdrant: Any = Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    Upsert points into a collection.

    Requires: editor permission on vector_store:default
    """
    from qdrant_client.models import PointStruct

    try:
        points = []
        for p in request.points:
            point_id = p.get("id")
            point_vector = p.get("vector")
            if point_id is None or point_vector is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each point must have 'id' and 'vector' fields",
                )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=point_vector,
                    payload=p.get("payload", {}),
                )
            )

        qdrant.upsert(
            collection_name=request.collection_name,
            points=points,
        )

        logger.info(
            "Points upserted",
            extra={
                "collection": request.collection_name,
                "count": len(points),
                "user": current_user.get("username"),
            },
        )

        return {"collection": request.collection_name, "upserted_count": len(points)}
    except Exception as e:
        logger.error(f"Failed to upsert points: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert points: {e}",
        )


@router.post("/search-text")
async def search_vectors_by_text(
    request: TextSearchRequest,
    current_user: dict[str, Any] = Depends(require_viewer_permission),
    qdrant: Any = Depends(get_qdrant_client),
    embeddings: Any = Depends(get_embedding_model),
) -> dict[str, Any]:
    """
    Search for similar vectors using text query.

    The text query is converted to a vector using the configured embedding model,
    then used to search for similar vectors in the collection.

    Requires: viewer permission on vector_store:default
    """
    try:
        # Convert text to embedding vector
        query_vector = embeddings.embed_query(request.query_text)

        # Search Qdrant with the embedding
        results = qdrant.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            limit=request.limit,
        )

        return {
            "results": [
                {
                    "id": str(r.id),
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Failed to search vectors by text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search vectors: {e}",
        )


@router.post("/upsert-text")
async def upsert_vector_by_text(
    request: TextUpsertRequest,
    current_user: dict[str, Any] = Depends(require_editor_permission),
    qdrant: Any = Depends(get_qdrant_client),
    embeddings: Any = Depends(get_embedding_model),
) -> dict[str, Any]:
    """
    Upsert a text document as a vector.

    The text is converted to a vector using the configured embedding model,
    then stored in the collection with the text and metadata as payload.

    Requires: editor permission on vector_store:default
    """
    import uuid

    from qdrant_client.models import PointStruct

    try:
        # Generate a UUID for the point
        point_id = str(uuid.uuid4())

        # Convert text to embedding vector
        vector = embeddings.embed_query(request.text)

        # Build payload with text and metadata
        payload = {"text": request.text, **request.metadata}

        # Create the point
        point = PointStruct(
            id=point_id,
            vector=vector,
            payload=payload,
        )

        # Upsert to Qdrant
        qdrant.upsert(
            collection_name=request.collection_name,
            points=[point],
        )

        logger.info(
            "Text vector upserted",
            extra={
                "collection": request.collection_name,
                "point_id": point_id,
                "user": current_user.get("username"),
            },
        )

        return {
            "collection": request.collection_name,
            "point_id": point_id,
            "status": "created",
        }
    except Exception as e:
        logger.error(f"Failed to upsert text vector: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert text: {e}",
        )
