"""
Composite Artifacts Service Adapter.

Adapts CompositeArtifactsService to the ArtifactsServiceProtocol
expected by the API router.

Key adaptations:
- Cursor-based pagination (protocol) ↔ offset-based (composite)
- Parameter unpacking for create/update operations
- Response format standardization
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.artifacts.composite_service import (
        CompositeArtifactsService,
    )


logger = logging.getLogger(__name__)


class CompositeArtifactsServiceAdapter:
    """
    Adapter that implements ArtifactsServiceProtocol using CompositeArtifactsService.

    This adapter bridges the interface differences between:
    - ArtifactsServiceProtocol (used by API router)
    - CompositeArtifactsService (multi-layer storage implementation)

    Key differences handled:
    - Pagination: cursor (string) vs offset (int)
    - Create: data dict vs explicit parameters
    - Update: data dict vs explicit parameters
    - Fork: adds parent_id to response
    """

    def __init__(self, composite_service: CompositeArtifactsService) -> None:
        """
        Initialize adapter.

        Args:
            composite_service: The underlying composite service
        """
        self._service = composite_service

    async def list_artifacts(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """
        List artifacts with cursor-based pagination.

        Converts cursor to offset for the underlying service,
        and determines has_more by requesting one extra item.

        Args:
            user_id: User ID
            session_id: Optional session filter
            limit: Max items to return
            cursor: Pagination cursor (encoded offset)

        Returns:
            Tuple of (items, next_cursor, has_more)
        """
        # Convert cursor to offset
        offset = 0
        if cursor:
            try:
                offset = int(cursor)
            except ValueError:
                offset = 0

        # Request one extra to determine has_more
        items = await self._service.list(
            user_id=user_id,
            session_id=session_id,
            limit=limit + 1,
            offset=offset,
        )

        # Check if more items exist
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]  # Remove the extra item

        # Calculate next cursor
        next_cursor = str(offset + limit) if has_more else None

        return items, next_cursor, has_more

    async def get_artifact(
        self,
        artifact_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a specific artifact.

        Args:
            artifact_id: Artifact ID
            user_id: User ID

        Returns:
            Artifact dict or None
        """
        return await self._service.get(
            artifact_id=artifact_id,
            user_id=user_id,
        )

    async def create_artifact(
        self,
        data: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """
        Create a new artifact.

        Unpacks the data dictionary into explicit parameters
        for the composite service.

        Args:
            data: Artifact creation data
            user_id: User ID

        Returns:
            Dict with id, version, created_at
        """
        artifact = await self._service.create(
            session_id=data["session_id"],
            user_id=user_id,
            artifact_type=data.get("type", "code"),
            title=data.get("title", "Untitled Artifact"),
            content=data["content"],
            content_type=data.get("content_type", "code"),
            edit_metadata=data.get("edit_metadata"),
        )

        if artifact is None:
            raise RuntimeError("Failed to create artifact")

        # Return minimal response
        return {
            "id": artifact["id"],
            "version": artifact["version"],
            "created_at": artifact["created_at"],
        }

    async def update_artifact(
        self,
        artifact_id: str,
        data: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any] | None:
        """
        Update an artifact.

        Unpacks the data dictionary into explicit parameters.

        Args:
            artifact_id: Artifact ID
            data: Update data
            user_id: User ID

        Returns:
            Dict with id, version, updated_at or None
        """
        artifact = await self._service.update(
            artifact_id=artifact_id,
            user_id=user_id,
            content=data.get("content"),
            title=data.get("title"),
            edit_metadata=data.get("edit_metadata"),
        )

        if artifact is None:
            return None

        # Return minimal response
        return {
            "id": artifact["id"],
            "version": artifact["version"],
            "updated_at": artifact["updated_at"],
        }

    async def delete_artifact(
        self,
        artifact_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete an artifact.

        Args:
            artifact_id: Artifact ID
            user_id: User ID

        Returns:
            True if deleted, False otherwise
        """
        return await self._service.delete(
            artifact_id=artifact_id,
            user_id=user_id,
        )

    async def get_artifact_versions(
        self,
        artifact_id: str,
        user_id: str,
    ) -> list[dict[str, Any]] | None:
        """
        Get version history for an artifact.

        Args:
            artifact_id: Artifact ID
            user_id: User ID

        Returns:
            List of versions or None
        """
        return await self._service.get_versions(
            artifact_id=artifact_id,
            user_id=user_id,
        )

    async def fork_artifact(
        self,
        artifact_id: str,
        new_name: str | None,
        user_id: str,
    ) -> dict[str, Any] | None:
        """
        Fork an artifact.

        Adds parent_id to the response for the API contract.

        Args:
            artifact_id: Source artifact ID
            new_name: Optional new name
            user_id: User ID

        Returns:
            Dict with id, parent_id, version or None
        """
        forked = await self._service.fork(
            artifact_id=artifact_id,
            user_id=user_id,
            new_name=new_name,
        )

        if forked is None:
            return None

        # Add parent_id for API response
        return {
            "id": forked["id"],
            "parent_id": artifact_id,
            "version": forked.get("version", 1),
        }

    # =========================================================================
    # Additional methods exposed by adapter (not in original protocol)
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across artifacts.

        Args:
            query: Search query
            user_id: User ID
            limit: Max results

        Returns:
            List of search results with scores
        """
        return await self._service.semantic_search(
            query=query,
            user_id=user_id,
            limit=limit,
        )

    async def find_similar(
        self,
        artifact_id: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find artifacts similar to a given artifact.

        Args:
            artifact_id: Source artifact ID
            user_id: User ID
            limit: Max results

        Returns:
            List of similar artifacts
        """
        return await self._service.find_similar(
            artifact_id=artifact_id,
            user_id=user_id,
            limit=limit,
        )
