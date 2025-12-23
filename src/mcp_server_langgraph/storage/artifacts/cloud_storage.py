"""
Hybrid Cloud Storage Service for Artifacts.

Provides size-based routing for artifact content:
- Small content: Stored inline in PostgreSQL
- Large content: Uploaded to cloud storage (S3, GCS, Azure)

Features:
- Multi-provider support (S3, GCS, Azure Blob)
- Content hashing for integrity
- Transparent content retrieval
- Graceful degradation
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

# Default size threshold: 100KB
DEFAULT_SIZE_THRESHOLD = 100 * 1024

# Supported cloud providers
CloudProvider = Literal["s3", "gcs", "azure"]


class CloudStorageClient(Protocol):
    """Protocol for cloud storage clients."""

    async def put_object(self, bucket: str, key: str, body: bytes, content_type: str | None = None) -> dict[str, Any]:
        """Upload object to cloud storage."""
        ...

    async def get_object(self, bucket: str, key: str) -> bytes:
        """Download object from cloud storage."""
        ...

    async def delete_object(self, bucket: str, key: str) -> bool:
        """Delete object from cloud storage."""
        ...


def _compute_content_hash(content: str | bytes) -> str:
    """
    Compute SHA-256 hash of content.

    Args:
        content: Content to hash (string or bytes)

    Returns:
        Hex-encoded SHA-256 hash (first 16 chars for brevity)
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


def _generate_storage_key(
    artifact_id: str,
    content_hash: str,
    prefix: str = "",
) -> str:
    """
    Generate storage key for cloud object.

    Format: {prefix}{artifact_id}/{content_hash}

    Args:
        artifact_id: Artifact ID
        content_hash: Content hash for integrity
        prefix: Bucket prefix

    Returns:
        Storage key string
    """
    return f"{prefix}{artifact_id}/{content_hash}"


class HybridCloudStorageService:
    """
    Hybrid storage service for artifact content.

    Routes content based on size:
    - Small content (< threshold): Returned for inline storage
    - Large content (>= threshold): Uploaded to cloud storage
    """

    def __init__(
        self,
        client: CloudStorageClient,
        bucket: str,
        prefix: str = "",
        size_threshold: int = DEFAULT_SIZE_THRESHOLD,
        provider: CloudProvider = "s3",
    ) -> None:
        """
        Initialize hybrid storage service.

        Args:
            client: Cloud storage client
            bucket: Bucket/container name
            prefix: Key prefix for organization
            size_threshold: Size threshold in bytes for cloud storage
            provider: Cloud provider (s3, gcs, azure)
        """
        self._client = client
        self._bucket = bucket
        self._prefix = prefix
        self._size_threshold = size_threshold
        self._provider = provider

    async def upload(
        self,
        content: str,
        artifact_id: str,
        user_id: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload content with size-based routing.

        Args:
            content: Content to upload
            artifact_id: Artifact ID
            user_id: User ID (for logging/auditing)
            content_type: MIME type of content

        Returns:
            Dict with storage_type and storage_key
        """
        content_bytes = content.encode("utf-8") if isinstance(content, str) else content
        content_size = len(content_bytes)

        # Small content: inline storage
        if content_size < self._size_threshold:
            logger.debug(
                "Content below threshold, using inline storage",
                extra={
                    "artifact_id": artifact_id,
                    "size": content_size,
                    "threshold": self._size_threshold,
                },
            )
            return {
                "storage_type": "inline",
                "storage_key": None,
            }

        # Large content: cloud storage
        content_hash = _compute_content_hash(content_bytes)
        storage_key = _generate_storage_key(artifact_id, content_hash, self._prefix)

        try:
            await self._client.put_object(
                bucket=self._bucket,
                key=storage_key,
                body=content_bytes,
                content_type=content_type,
            )

            logger.info(
                "Uploaded content to cloud storage",
                extra={
                    "artifact_id": artifact_id,
                    "storage_key": storage_key,
                    "size": content_size,
                    "provider": self._provider,
                },
            )

            return {
                "storage_type": self._provider,
                "storage_key": storage_key,
            }

        except Exception as e:
            logger.exception(
                "Failed to upload content to cloud storage",
                extra={
                    "artifact_id": artifact_id,
                    "error": str(e),
                    "provider": self._provider,
                },
            )
            raise

    async def download(self, storage_key: str) -> str | None:
        """
        Download content from cloud storage.

        Args:
            storage_key: Storage key

        Returns:
            Content string or None if not found
        """
        try:
            content_bytes = await self._client.get_object(
                bucket=self._bucket,
                key=storage_key,
            )

            logger.debug(
                "Downloaded content from cloud storage",
                extra={"storage_key": storage_key},
            )

            return content_bytes.decode("utf-8")

        except Exception as e:
            logger.warning(
                "Failed to download content from cloud storage",
                extra={"storage_key": storage_key, "error": str(e)},
            )
            return None

    async def delete(self, storage_key: str) -> bool:
        """
        Delete content from cloud storage.

        Args:
            storage_key: Storage key

        Returns:
            True if deleted, False otherwise
        """
        try:
            await self._client.delete_object(
                bucket=self._bucket,
                key=storage_key,
            )

            logger.info(
                "Deleted content from cloud storage",
                extra={"storage_key": storage_key},
            )

            return True

        except Exception as e:
            logger.warning(
                "Failed to delete content from cloud storage",
                extra={"storage_key": storage_key, "error": str(e)},
            )
            return False
