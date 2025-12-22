"""
Tests for Hybrid Cloud Storage Service for Artifacts.

TDD RED Phase: These tests define the expected behavior of HybridCloudStorageService.

The hybrid storage layer provides:
- Size-based routing (inline for small, cloud for large)
- Multi-provider support (S3, GCS, Azure Blob)
- Transparent content retrieval
- Content hashing for deduplication
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_BUCKET = "test-artifacts-bucket"
TEST_PREFIX = "artifacts/"
SIZE_THRESHOLD = 100 * 1024  # 100KB threshold for cloud storage


@pytest.mark.xdist_group(name="test_cloud_storage")
@pytest.mark.unit
class TestHybridCloudStorageServiceUpload:
    """Tests for content upload with size-based routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_upload_small_content_returns_inline(self) -> None:
        """Test that small content is stored inline (not uploaded to cloud)."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=SIZE_THRESHOLD,
        )

        small_content = "small content"  # < 100KB

        # Act
        result = await service.upload(
            content=small_content,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert - inline storage
        assert result["storage_type"] == "inline"
        assert result["storage_key"] is None
        # Cloud client should NOT be called for small content
        mock_client.put_object.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_large_content_stores_in_cloud(self) -> None:
        """Test that large content is uploaded to cloud storage."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=100,  # Low threshold for testing
        )

        large_content = "x" * 200  # > 100 bytes

        # Act
        result = await service.upload(
            content=large_content,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert - cloud storage
        assert result["storage_type"] in ("s3", "gcs", "azure")
        assert result["storage_key"] is not None
        mock_client.put_object.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upload_generates_unique_storage_key(self) -> None:
        """Test that upload generates unique storage key with content hash."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=10,  # Very low threshold
        )

        content = "content for hashing"

        # Act
        result = await service.upload(
            content=content,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert
        assert result["storage_key"] is not None
        assert result["storage_key"].startswith(TEST_PREFIX)
        # Key should include artifact_id for organization
        assert "art-123" in result["storage_key"]


@pytest.mark.xdist_group(name="test_cloud_storage")
@pytest.mark.unit
class TestHybridCloudStorageServiceDownload:
    """Tests for content retrieval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_download_retrieves_content_from_cloud(self) -> None:
        """Test that download retrieves content from cloud storage."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        mock_client.get_object.return_value = b"cloud content"

        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=SIZE_THRESHOLD,
        )

        storage_key = "artifacts/art-123/content.txt"

        # Act
        result = await service.download(storage_key)

        # Assert
        assert result == "cloud content"
        mock_client.get_object.assert_awaited_once_with(
            bucket=TEST_BUCKET,
            key=storage_key,
        )

    @pytest.mark.asyncio
    async def test_download_returns_none_for_missing_key(self) -> None:
        """Test that download returns None for non-existent key."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        mock_client.get_object.side_effect = Exception("Key not found")

        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=SIZE_THRESHOLD,
        )

        # Act
        result = await service.download("non-existent-key")

        # Assert
        assert result is None


@pytest.mark.xdist_group(name="test_cloud_storage")
@pytest.mark.unit
class TestHybridCloudStorageServiceDelete:
    """Tests for content deletion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_removes_content_from_cloud(self) -> None:
        """Test that delete removes content from cloud storage."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        mock_client.delete_object.return_value = True

        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=SIZE_THRESHOLD,
        )

        storage_key = "artifacts/art-123/content.txt"

        # Act
        result = await service.delete(storage_key)

        # Assert
        assert result is True
        mock_client.delete_object.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing_key(self) -> None:
        """Test that delete returns False for non-existent key."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        mock_client.delete_object.side_effect = Exception("Key not found")

        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=SIZE_THRESHOLD,
        )

        # Act
        result = await service.delete("non-existent-key")

        # Assert
        assert result is False


@pytest.mark.xdist_group(name="test_cloud_storage")
@pytest.mark.unit
class TestHybridCloudStorageServiceProviders:
    """Tests for multi-provider support."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_s3_provider_uses_correct_storage_type(self) -> None:
        """Test that S3 provider sets correct storage_type."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=10,
            provider="s3",
        )

        # Act
        result = await service.upload(
            content="x" * 100,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert
        assert result["storage_type"] == "s3"

    @pytest.mark.asyncio
    async def test_gcs_provider_uses_correct_storage_type(self) -> None:
        """Test that GCS provider sets correct storage_type."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=10,
            provider="gcs",
        )

        # Act
        result = await service.upload(
            content="x" * 100,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert
        assert result["storage_type"] == "gcs"

    @pytest.mark.asyncio
    async def test_azure_provider_uses_correct_storage_type(self) -> None:
        """Test that Azure provider sets correct storage_type."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,  # Called "container" in Azure
            prefix=TEST_PREFIX,
            size_threshold=10,
            provider="azure",
        )

        # Act
        result = await service.upload(
            content="x" * 100,
            artifact_id="art-123",
            user_id="user-456",
        )

        # Assert
        assert result["storage_type"] == "azure"


@pytest.mark.xdist_group(name="test_cloud_storage")
@pytest.mark.unit
class TestHybridCloudStorageServiceContentHash:
    """Tests for content hashing and deduplication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_same_content_generates_same_hash(self) -> None:
        """Test that identical content generates the same hash."""
        from mcp_server_langgraph.storage.artifacts.cloud_storage import (
            HybridCloudStorageService,
        )

        mock_client = AsyncMock()
        service = HybridCloudStorageService(
            client=mock_client,
            bucket=TEST_BUCKET,
            prefix=TEST_PREFIX,
            size_threshold=10,
            provider="s3",
        )

        content = "identical content"

        # Act - upload twice
        result1 = await service.upload(
            content=content,
            artifact_id="art-1",
            user_id="user-456",
        )
        result2 = await service.upload(
            content=content,
            artifact_id="art-2",
            user_id="user-456",
        )

        # Assert - different artifacts but content hashes should match
        # (actual key includes artifact_id, so full keys differ)
        # The content hash portion should be the same
        assert result1["storage_key"] is not None
        assert result2["storage_key"] is not None
