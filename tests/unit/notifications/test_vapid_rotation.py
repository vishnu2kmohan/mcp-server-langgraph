"""
VAPID Key Rotation Service Tests.

TDD tests for automated VAPID key rotation for Web Push notifications.

Features:
- Generate new VAPID key pairs
- Store keys with version/timestamp tracking
- Support graceful rotation (overlap period)
- Track key usage and expiration

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyGeneration:
    """Tests for VAPID key pair generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_generate_key_pair_creates_valid_keys(self) -> None:
        """Test that generate_key_pair creates valid VAPID keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        service = VAPIDKeyRotationService()
        key_pair = service.generate_key_pair()

        assert key_pair.public_key is not None
        assert key_pair.private_key is not None
        # Keys should be base64-encoded strings
        assert isinstance(key_pair.public_key, str)
        assert isinstance(key_pair.private_key, str)
        # Public key should be longer than private key for VAPID
        assert len(key_pair.public_key) > 40
        assert len(key_pair.private_key) > 40

    def test_generate_key_pair_creates_unique_keys(self) -> None:
        """Test that each call generates unique key pairs."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        service = VAPIDKeyRotationService()
        key_pair_1 = service.generate_key_pair()
        key_pair_2 = service.generate_key_pair()

        assert key_pair_1.public_key != key_pair_2.public_key
        assert key_pair_1.private_key != key_pair_2.private_key

    def test_generate_key_pair_includes_metadata(self) -> None:
        """Test that generated key pairs include metadata."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        service = VAPIDKeyRotationService()
        key_pair = service.generate_key_pair()

        assert key_pair.key_id is not None
        assert key_pair.created_at is not None
        assert isinstance(key_pair.created_at, datetime)
        assert key_pair.created_at.tzinfo is not None  # Should be timezone-aware


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyStorage:
    """Tests for VAPID key storage operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_key_stores_in_repository(self) -> None:
        """Test that save_key stores key pair in repository."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.save = AsyncMock(return_value=None)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        key_pair = VAPIDKeyPair(
            key_id="key-001",
            public_key="public-key-base64",
            private_key="private-key-base64",
            created_at=datetime.now(UTC),
        )

        await service.save_key(key_pair)

        mock_repo.save.assert_called_once_with(key_pair)

    @pytest.mark.asyncio
    async def test_get_current_key_returns_active_key(self) -> None:
        """Test that get_current_key returns the currently active key."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        current_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="current-public-key",
            private_key="current-private-key",
            created_at=datetime.now(UTC),
            is_active=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=current_key)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        result = await service.get_current_key()

        assert result == current_key
        mock_repo.get_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_by_id_returns_specific_key(self) -> None:
        """Test that get_key_by_id returns a specific key version."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        key = VAPIDKeyPair(
            key_id="key-002",
            public_key="specific-public-key",
            private_key="specific-private-key",
            created_at=datetime.now(UTC),
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=key)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        result = await service.get_key_by_id("key-002")

        assert result == key
        mock_repo.get_by_id.assert_called_once_with("key-002")

    @pytest.mark.asyncio
    async def test_list_keys_returns_all_versions(self) -> None:
        """Test that list_keys returns all key versions."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        keys = [
            VAPIDKeyPair(
                key_id=f"key-{i:03d}",
                public_key=f"public-{i}",
                private_key=f"private-{i}",
                created_at=datetime.now(UTC) - timedelta(days=i),
            )
            for i in range(3)
        ]

        mock_repo = AsyncMock(return_value=None)
        mock_repo.list_all = AsyncMock(return_value=keys)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        result = await service.list_keys()

        assert len(result) == 3
        mock_repo.list_all.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyRotation:
    """Tests for VAPID key rotation operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rotate_creates_new_key_and_deactivates_old(self) -> None:
        """Test that rotate creates a new key and deactivates the old one."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        old_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="old-public",
            private_key="old-private",
            created_at=datetime.now(UTC) - timedelta(days=90),
            is_active=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=old_key)
        mock_repo.save = AsyncMock(return_value=None)
        mock_repo.deactivate = AsyncMock(return_value=None)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        new_key = await service.rotate()

        assert new_key.is_active is True
        assert new_key.key_id != old_key.key_id
        mock_repo.save.assert_called_once()
        mock_repo.deactivate.assert_called_once_with(old_key.key_id)

    @pytest.mark.asyncio
    async def test_rotate_sets_overlap_period(self) -> None:
        """Test that rotation maintains overlap period for graceful transition."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        old_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="old-public",
            private_key="old-private",
            created_at=datetime.now(UTC) - timedelta(days=90),
            is_active=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=old_key)
        mock_repo.save = AsyncMock(return_value=None)
        mock_repo.deactivate = AsyncMock(return_value=None)
        mock_repo.set_expiry = AsyncMock(return_value=None)

        service = VAPIDKeyRotationService(
            key_repository=mock_repo,
            overlap_days=7,  # Keep old key valid for 7 days
        )
        await service.rotate()

        # Old key should have expiry set
        mock_repo.set_expiry.assert_called_once()
        call_args = mock_repo.set_expiry.call_args
        assert call_args[0][0] == old_key.key_id

    @pytest.mark.asyncio
    async def test_rotate_handles_no_existing_key(self) -> None:
        """Test that rotate works when no existing key (first rotation)."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=None)
        mock_repo.save = AsyncMock(return_value=None)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        new_key = await service.rotate()

        assert new_key.is_active is True
        mock_repo.save.assert_called_once()
        # Should not try to deactivate when there's no old key
        mock_repo.deactivate.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyExpiration:
    """Tests for VAPID key expiration handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys_removes_old_keys(self) -> None:
        """Test that cleanup removes expired keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        mock_repo = AsyncMock(return_value=None)
        mock_repo.delete_expired = AsyncMock(return_value=3)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        deleted_count = await service.cleanup_expired_keys()

        assert deleted_count == 3
        mock_repo.delete_expired.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_rotate_returns_true_when_key_is_old(self) -> None:
        """Test that should_rotate returns True for old keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        # Key created 100 days ago
        old_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="old-public",
            private_key="old-private",
            created_at=datetime.now(UTC) - timedelta(days=100),
            is_active=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=old_key)

        service = VAPIDKeyRotationService(
            key_repository=mock_repo,
            rotation_days=90,  # Rotate every 90 days
        )
        should_rotate = await service.should_rotate()

        assert should_rotate is True

    @pytest.mark.asyncio
    async def test_should_rotate_returns_false_when_key_is_new(self) -> None:
        """Test that should_rotate returns False for recent keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        # Key created 30 days ago
        new_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="new-public",
            private_key="new-private",
            created_at=datetime.now(UTC) - timedelta(days=30),
            is_active=True,
        )

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=new_key)

        service = VAPIDKeyRotationService(
            key_repository=mock_repo,
            rotation_days=90,  # Rotate every 90 days
        )
        should_rotate = await service.should_rotate()

        assert should_rotate is False

    @pytest.mark.asyncio
    async def test_should_rotate_returns_true_when_no_key_exists(self) -> None:
        """Test that should_rotate returns True when no key exists."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_active = AsyncMock(return_value=None)

        service = VAPIDKeyRotationService(key_repository=mock_repo)
        should_rotate = await service.should_rotate()

        assert should_rotate is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyValidation:
    """Tests for VAPID key validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_validate_key_pair_returns_true_for_valid_keys(self) -> None:
        """Test that validate_key_pair returns True for valid keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyRotationService

        service = VAPIDKeyRotationService()
        # Generate a real key pair
        key_pair = service.generate_key_pair()

        is_valid = service.validate_key_pair(key_pair)

        assert is_valid is True

    def test_validate_key_pair_returns_false_for_empty_keys(self) -> None:
        """Test that validate_key_pair returns False for empty keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        service = VAPIDKeyRotationService()
        invalid_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="",
            private_key="",
            created_at=datetime.now(UTC),
        )

        is_valid = service.validate_key_pair(invalid_key)

        assert is_valid is False

    def test_validate_key_pair_returns_false_for_malformed_keys(self) -> None:
        """Test that validate_key_pair returns False for malformed keys."""
        from mcp_server_langgraph.notifications.vapid_rotation import (
            VAPIDKeyRotationService,
            VAPIDKeyPair,
        )

        service = VAPIDKeyRotationService()
        invalid_key = VAPIDKeyPair(
            key_id="key-001",
            public_key="not-a-valid-base64-key!!!",
            private_key="also-not-valid!!!",
            created_at=datetime.now(UTC),
        )

        is_valid = service.validate_key_pair(invalid_key)

        assert is_valid is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="vapid_rotation")
class TestVAPIDKeyPairModel:
    """Tests for the VAPIDKeyPair data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_create_key_pair_with_defaults(self) -> None:
        """Test creating a key pair with default values."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyPair

        key_pair = VAPIDKeyPair(
            key_id="key-001",
            public_key="public-key-base64",
            private_key="private-key-base64",
            created_at=datetime.now(UTC),
        )

        assert key_pair.is_active is False  # Default
        assert key_pair.expires_at is None  # Default

    def test_key_pair_to_dict(self) -> None:
        """Test serializing key pair to dict."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyPair

        now = datetime.now(UTC)
        key_pair = VAPIDKeyPair(
            key_id="key-001",
            public_key="public-key-base64",
            private_key="private-key-base64",
            created_at=now,
            is_active=True,
        )

        data = key_pair.to_dict()

        assert data["key_id"] == "key-001"
        assert data["public_key"] == "public-key-base64"
        assert data["is_active"] is True
        # Private key should be masked in dict representation for safety
        assert "private_key" not in data or data["private_key"] == "[REDACTED]"

    def test_key_pair_from_dict(self) -> None:
        """Test deserializing key pair from dict."""
        from mcp_server_langgraph.notifications.vapid_rotation import VAPIDKeyPair

        now = datetime.now(UTC)
        data = {
            "key_id": "key-001",
            "public_key": "public-key-base64",
            "private_key": "private-key-base64",
            "created_at": now.isoformat(),
            "is_active": True,
            "expires_at": None,
        }

        key_pair = VAPIDKeyPair.from_dict(data)

        assert key_pair.key_id == "key-001"
        assert key_pair.public_key == "public-key-base64"
        assert key_pair.private_key == "private-key-base64"
        assert key_pair.is_active is True
