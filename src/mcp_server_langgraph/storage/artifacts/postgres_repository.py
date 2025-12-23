"""
PostgreSQL Repository for Artifacts Storage.

Implements the ArtifactsServiceProtocol using PostgreSQL with SQLAlchemy async.
Follows the repository pattern established in storage/base.py.

Features:
- CRUD operations for artifacts
- Version history tracking (shadow table pattern)
- User-scoped queries (security)
- Cursor-based pagination
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import desc, select

from mcp_server_langgraph.storage.artifacts.models import (
    ArtifactModel,
    ArtifactVersionModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class PostgresArtifactsRepository:
    """
    PostgreSQL repository for canvas artifacts.

    Implements full CRUD with version history tracking.
    All operations are scoped to the user for security.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """
        Create a new artifact with initial version.

        Args:
            data: Artifact data (type, content, content_type, session_id, title, etc.)
            user_id: ID of the user creating the artifact

        Returns:
            Dict with id, version, created_at
        """
        artifact_id = f"art-{uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # Create artifact model
        artifact = ArtifactModel(
            id=artifact_id,
            session_id=data["session_id"],
            user_id=user_id,
            type=data.get("type", "code"),
            title=data.get("title", "Untitled Artifact"),
            content=data["content"],
            content_type=data.get("content_type", "code"),
            version=1,
            storage_type=data.get("storage_type", "inline"),
            storage_key=data.get("storage_key"),
            edit_metadata=data.get("edit_metadata"),
            created_at=now,
            updated_at=now,
        )

        # Create initial version entry
        version = ArtifactVersionModel(
            id=f"ver-{uuid4().hex[:12]}",
            artifact_id=artifact_id,
            version=1,
            content=data["content"],
            content_type=data.get("content_type", "code"),
            storage_type=data.get("storage_type", "inline"),
            storage_key=data.get("storage_key"),
            created_by=user_id,
            created_at=now,
            version_metadata={"edit_type": "create"},
        )

        self._session.add(artifact)
        self._session.add(version)
        await self._session.commit()

        logger.info(
            "Created artifact",
            extra={"artifact_id": artifact_id, "user_id": user_id},
        )

        return {
            "id": artifact_id,
            "version": 1,
            "created_at": now.isoformat(),
        }

    async def get(self, artifact_id: str, user_id: str) -> dict[str, Any] | None:
        """
        Get artifact by ID.

        Args:
            artifact_id: Artifact ID
            user_id: User ID (for ownership check)

        Returns:
            Artifact dict or None if not found/not owned
        """
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        artifact = result.scalar_one_or_none()

        if artifact is None:
            return None

        # Security: verify ownership
        if artifact.user_id != user_id:
            logger.warning(
                "Artifact access denied - user mismatch",
                extra={
                    "artifact_id": artifact_id,
                    "requested_by": user_id,
                    "owned_by": artifact.user_id,
                },
            )
            return None

        return artifact.to_dict()

    async def update(self, artifact_id: str, data: dict[str, Any], user_id: str) -> dict[str, Any] | None:
        """
        Update artifact and create new version.

        Args:
            artifact_id: Artifact ID
            data: Update data (content, title, edit_metadata, etc.)
            user_id: User ID (for ownership check)

        Returns:
            Dict with id, version, updated_at or None if not found/not owned
        """
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        artifact = result.scalar_one_or_none()

        if artifact is None:
            return None

        # Security: verify ownership
        if artifact.user_id != user_id:
            logger.warning(
                "Artifact update denied - user mismatch",
                extra={"artifact_id": artifact_id, "requested_by": user_id},
            )
            return None

        now = datetime.now(UTC)
        old_version = artifact.version
        new_version = old_version + 1

        # Update artifact fields
        if "content" in data:
            artifact.content = data["content"]
        if "title" in data:
            artifact.title = data["title"]
        if "edit_metadata" in data:
            artifact.edit_metadata = data["edit_metadata"]
        if "storage_type" in data:
            artifact.storage_type = data["storage_type"]
        if "storage_key" in data:
            artifact.storage_key = data["storage_key"]

        artifact.version = new_version
        artifact.updated_at = now

        # Create version entry
        version = ArtifactVersionModel(
            id=f"ver-{uuid4().hex[:12]}",
            artifact_id=artifact_id,
            version=new_version,
            parent_version=old_version,
            content=artifact.content,
            content_type=artifact.content_type,
            storage_type=artifact.storage_type,
            storage_key=artifact.storage_key,
            created_by=user_id,
            created_at=now,
            version_metadata=data.get("edit_metadata", {"edit_type": "update"}),
        )

        self._session.add(version)
        await self._session.commit()

        logger.info(
            "Updated artifact",
            extra={
                "artifact_id": artifact_id,
                "old_version": old_version,
                "new_version": new_version,
            },
        )

        return {
            "id": artifact_id,
            "version": new_version,
            "updated_at": now.isoformat(),
        }

    async def delete(self, artifact_id: str, user_id: str) -> bool:
        """
        Delete artifact and all versions.

        Args:
            artifact_id: Artifact ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted, False if not found/not owned
        """
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        artifact = result.scalar_one_or_none()

        if artifact is None:
            return False

        # Security: verify ownership
        if artifact.user_id != user_id:
            logger.warning(
                "Artifact delete denied - user mismatch",
                extra={"artifact_id": artifact_id, "requested_by": user_id},
            )
            return False

        await self._session.delete(artifact)
        await self._session.commit()

        logger.info(
            "Deleted artifact",
            extra={"artifact_id": artifact_id, "user_id": user_id},
        )

        return True

    async def list(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """
        List artifacts for user with pagination.

        Args:
            user_id: User ID
            session_id: Optional session filter
            limit: Max items to return
            cursor: Pagination cursor (offset-based for simplicity)

        Returns:
            Tuple of (items, next_cursor, has_more)
        """
        # Build base query
        stmt = select(ArtifactModel).where(ArtifactModel.user_id == user_id)

        # Filter by session if provided
        if session_id:
            stmt = stmt.where(ArtifactModel.session_id == session_id)

        # Order by updated_at descending
        stmt = stmt.order_by(desc(ArtifactModel.updated_at))

        # Apply pagination
        offset = 0
        if cursor:
            try:
                offset = int(cursor)
            except ValueError:
                offset = 0

        # Fetch limit + 1 to check if there are more
        stmt = stmt.offset(offset).limit(limit + 1)

        result = await self._session.execute(stmt)
        artifacts = result.scalars().all()

        # Check if there are more
        has_more = len(artifacts) > limit
        if has_more:
            artifacts = artifacts[:limit]

        items = [a.to_dict() for a in artifacts]
        next_cursor = str(offset + limit) if has_more else None

        return items, next_cursor, has_more

    async def get_versions(self, artifact_id: str, user_id: str) -> list[dict[str, Any]] | None:  # type: ignore[valid-type]
        """
        Get version history for artifact.

        Args:
            artifact_id: Artifact ID
            user_id: User ID (for ownership check)

        Returns:
            List of version dicts or None if artifact not found/not owned
        """
        # First verify artifact exists and is owned by user
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        artifact = result.scalar_one_or_none()

        if artifact is None:
            return None

        if artifact.user_id != user_id:
            return None

        # Fetch versions
        version_stmt = (
            select(ArtifactVersionModel)
            .where(ArtifactVersionModel.artifact_id == artifact_id)
            .order_by(ArtifactVersionModel.version)
        )
        version_result = await self._session.execute(version_stmt)
        versions = version_result.scalars().all()

        return [v.to_dict() for v in versions]

    async def fork(self, artifact_id: str, new_name: str | None, user_id: str) -> dict[str, Any] | None:
        """
        Fork an artifact (create a copy).

        Args:
            artifact_id: Source artifact ID
            new_name: Optional name for forked artifact
            user_id: User ID (owner of the fork)

        Returns:
            Dict with id, parent_id, version or None if source not found
        """
        # Get source artifact
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            return None

        # Create forked artifact
        forked_id = f"art-{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        title = new_name or f"Fork of {source.title}"

        forked = ArtifactModel(
            id=forked_id,
            session_id=source.session_id,
            user_id=user_id,
            type=source.type,
            title=title,
            content=source.content,
            content_type=source.content_type,
            version=1,
            storage_type=source.storage_type,
            storage_key=source.storage_key,
            edit_metadata=source.edit_metadata,
            created_at=now,
            updated_at=now,
        )

        # Create initial version for fork
        version = ArtifactVersionModel(
            id=f"ver-{uuid4().hex[:12]}",
            artifact_id=forked_id,
            version=1,
            content=source.content,
            content_type=source.content_type,
            storage_type=source.storage_type,
            storage_key=source.storage_key,
            created_by=user_id,
            created_at=now,
            version_metadata={
                "edit_type": "fork",
                "forked_from": artifact_id,
            },
        )

        self._session.add(forked)
        self._session.add(version)
        await self._session.commit()

        logger.info(
            "Forked artifact",
            extra={
                "source_id": artifact_id,
                "forked_id": forked_id,
                "user_id": user_id,
            },
        )

        return {
            "id": forked_id,
            "parent_id": artifact_id,
            "version": 1,
        }
