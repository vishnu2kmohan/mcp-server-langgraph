"""Tests for StudioConfigStorage.

TDD: These tests define the contract for storing and retrieving
STUDIO.md configurations with database and cache support.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from datetime import UTC

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_storage_basic")
class TestStudioConfigStorageBasic:
    """Tests for StudioConfigStorage basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_storage_exists(self) -> None:
        """Test StudioConfigStorage class exists."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        assert StudioConfigStorage is not None

    def test_studio_storage_has_get_method(self) -> None:
        """Test StudioConfigStorage has get method."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()

        assert hasattr(storage, "get")

    def test_studio_storage_has_save_method(self) -> None:
        """Test StudioConfigStorage has save method."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()

        assert hasattr(storage, "save")

    def test_studio_storage_has_delete_method(self) -> None:
        """Test StudioConfigStorage has delete method."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()

        assert hasattr(storage, "delete")


@pytest.mark.unit
@pytest.mark.xdist_group(name="stored_studio_config")
class TestStoredStudioConfig:
    """Tests for StoredStudioConfig dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_stored_config_exists(self) -> None:
        """Test StoredStudioConfig dataclass exists."""
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        assert StoredStudioConfig is not None

    def test_stored_config_has_id(self) -> None:
        """Test StoredStudioConfig has id field."""
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="abc123",
        )

        assert config.id == "config-123"

    def test_stored_config_has_scope(self) -> None:
        """Test StoredStudioConfig has scope field."""
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        config = StoredStudioConfig(
            id="config-123",
            scope="organization",
            scope_id="org-456",
            config={"name": "test"},
            config_hash="abc123",
        )

        assert config.scope == "organization"
        assert config.scope_id == "org-456"

    def test_stored_config_has_config(self) -> None:
        """Test StoredStudioConfig has config field."""
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        config_data = {"name": "test", "tools": {"enabled": ["tool1"]}}
        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config=config_data,
            config_hash="abc123",
        )

        assert config.config == config_data

    def test_stored_config_has_config_hash(self) -> None:
        """Test StoredStudioConfig has config_hash field."""
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="sha256hash",
        )

        assert config.config_hash == "sha256hash"

    def test_stored_config_has_optional_timestamps(self) -> None:
        """Test StoredStudioConfig has optional timestamp fields."""
        from datetime import datetime

        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        now = datetime.now(UTC)
        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="abc123",
            created_at=now,
            updated_at=now,
        )

        assert config.created_at == now
        assert config.updated_at == now


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_storage_get")
class TestStudioConfigStorageGet:
    """Tests for StudioConfigStorage.get() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        """Test get() returns None when config not found."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()

        result = await storage.get(scope="project", scope_id=None)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_scope_and_scope_id(self) -> None:
        """Test get() retrieves by scope and scope_id."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        # Store a config first
        config = StoredStudioConfig(
            id="config-123",
            scope="organization",
            scope_id="org-456",
            config={"name": "test"},
            config_hash="abc123",
        )
        await storage.save(config)

        # Retrieve it
        result = await storage.get(scope="organization", scope_id="org-456")

        assert result is not None
        assert result.scope == "organization"
        assert result.scope_id == "org-456"

    @pytest.mark.asyncio
    async def test_get_checks_cache_first(self) -> None:
        """Test get() checks cache before database."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        mock_cache = MagicMock()
        cached_config = StoredStudioConfig(
            id="cached-123",
            scope="project",
            scope_id=None,
            config={"name": "cached"},
            config_hash="abc",
        )
        mock_cache.get = AsyncMock(return_value=cached_config)

        storage = StudioConfigStorage(cache=mock_cache)

        result = await storage.get(scope="project", scope_id=None)

        mock_cache.get.assert_called_once()
        assert result is not None
        assert result.id == "cached-123"


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_storage_save")
class TestStudioConfigStorageSave:
    """Tests for StudioConfigStorage.save() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_stores_config(self) -> None:
        """Test save() stores a config."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="abc123",
        )

        await storage.save(config)

        # Verify it can be retrieved
        result = await storage.get(scope="project", scope_id=None)
        assert result is not None
        assert result.id == "config-123"

    @pytest.mark.asyncio
    async def test_save_updates_existing_config(self) -> None:
        """Test save() updates existing config with same scope."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        # Save initial config
        config1 = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "original"},
            config_hash="abc123",
        )
        await storage.save(config1)

        # Save updated config with same scope
        config2 = StoredStudioConfig(
            id="config-456",
            scope="project",
            scope_id=None,
            config={"name": "updated"},
            config_hash="def456",
        )
        await storage.save(config2)

        # Should get the updated config
        result = await storage.get(scope="project", scope_id=None)
        assert result is not None
        assert result.config["name"] == "updated"

    @pytest.mark.asyncio
    async def test_save_invalidates_cache(self) -> None:
        """Test save() invalidates cache for the scope."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        mock_cache = MagicMock()
        mock_cache.invalidate = AsyncMock()  # noqa: ARG001
        mock_cache.set = AsyncMock()  # noqa: ARG001

        storage = StudioConfigStorage(cache=mock_cache)

        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="abc123",
        )

        await storage.save(config)

        # Cache should be updated
        mock_cache.set.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_storage_delete")
class TestStudioConfigStorageDelete:
    """Tests for StudioConfigStorage.delete() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_removes_config(self) -> None:
        """Test delete() removes a config."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        # Save a config
        config = StoredStudioConfig(
            id="config-123",
            scope="project",
            scope_id=None,
            config={"name": "test"},
            config_hash="abc123",
        )
        await storage.save(config)

        # Delete it
        await storage.delete(scope="project", scope_id=None)

        # Should no longer exist
        result = await storage.get(scope="project", scope_id=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self) -> None:
        """Test delete() invalidates cache."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        mock_cache = MagicMock()
        mock_cache.invalidate = AsyncMock()  # noqa: ARG001

        storage = StudioConfigStorage(cache=mock_cache)

        await storage.delete(scope="project", scope_id=None)

        mock_cache.invalidate.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_storage_hash")
class TestStudioConfigStorageHashing:
    """Tests for config hash generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compute_hash_returns_string(self) -> None:
        """Test compute_hash returns a hash string."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()
        config_data = {"name": "test", "tools": {"enabled": ["tool1"]}}

        hash_value = storage.compute_hash(config_data)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex length

    def test_compute_hash_is_deterministic(self) -> None:
        """Test compute_hash returns same hash for same input."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()
        config_data = {"name": "test", "tools": {"enabled": ["tool1"]}}

        hash1 = storage.compute_hash(config_data)
        hash2 = storage.compute_hash(config_data)

        assert hash1 == hash2

    def test_compute_hash_different_for_different_input(self) -> None:
        """Test compute_hash returns different hash for different input."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()
        config1 = {"name": "test1"}
        config2 = {"name": "test2"}

        hash1 = storage.compute_hash(config1)
        hash2 = storage.compute_hash(config2)

        assert hash1 != hash2
