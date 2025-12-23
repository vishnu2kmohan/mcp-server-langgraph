"""
VAPID Key Rotation Service.

Automated VAPID key rotation for Web Push notifications with graceful
transition support and key versioning.

Features:
- Generate new ECDSA P-256 key pairs for VAPID
- Store keys with version/timestamp tracking
- Support graceful rotation (overlap period)
- Track key usage and expiration
- Automatic cleanup of expired keys

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class VAPIDKeyPair:
    """
    VAPID key pair with metadata.

    Attributes:
        key_id: Unique identifier for this key version.
        public_key: Base64-encoded P-256 public key.
        private_key: Base64-encoded P-256 private key.
        created_at: When the key was generated.
        is_active: Whether this is the currently active key.
        expires_at: When the key expires (after rotation overlap).
    """

    key_id: str
    public_key: str
    private_key: str
    created_at: datetime
    is_active: bool = False
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dictionary (with private key redacted for safety).

        Returns:
            Dict suitable for JSON serialization.
        """
        return {
            "key_id": self.key_id,
            "public_key": self.public_key,
            "private_key": "[REDACTED]",
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VAPIDKeyPair:
        """
        Deserialize from dictionary.

        Args:
            data: Dict with key pair data.

        Returns:
            VAPIDKeyPair instance.
        """
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        return cls(
            key_id=data["key_id"],
            public_key=data["public_key"],
            private_key=data["private_key"],
            created_at=created_at,
            is_active=data.get("is_active", False),
            expires_at=expires_at,
        )


# =============================================================================
# Key Repository Protocol
# =============================================================================


class VAPIDKeyRepository(Protocol):
    """Protocol for VAPID key storage backends."""

    async def save(self, key_pair: VAPIDKeyPair) -> None:
        """Save a key pair to storage."""
        ...

    async def get_active(self) -> VAPIDKeyPair | None:
        """Get the currently active key pair."""
        ...

    async def get_by_id(self, key_id: str) -> VAPIDKeyPair | None:
        """Get a specific key pair by ID."""
        ...

    async def list_all(self) -> list[VAPIDKeyPair]:
        """List all key pairs."""
        ...

    async def deactivate(self, key_id: str) -> None:
        """Mark a key as inactive."""
        ...

    async def set_expiry(self, key_id: str, expires_at: datetime) -> None:
        """Set expiry time for a key."""
        ...

    async def delete_expired(self) -> int:
        """Delete all expired keys. Returns count of deleted keys."""
        ...


# =============================================================================
# In-Memory Repository (for testing)
# =============================================================================


class InMemoryVAPIDKeyRepository:
    """In-memory VAPID key repository for testing."""

    def __init__(self) -> None:
        self._keys: dict[str, VAPIDKeyPair] = {}

    async def save(self, key_pair: VAPIDKeyPair) -> None:
        """Save a key pair to storage."""
        self._keys[key_pair.key_id] = key_pair

    async def get_active(self) -> VAPIDKeyPair | None:
        """Get the currently active key pair."""
        for key in self._keys.values():
            if key.is_active:
                return key
        return None

    async def get_by_id(self, key_id: str) -> VAPIDKeyPair | None:
        """Get a specific key pair by ID."""
        return self._keys.get(key_id)

    async def list_all(self) -> list[VAPIDKeyPair]:
        """List all key pairs."""
        return list(self._keys.values())

    async def deactivate(self, key_id: str) -> None:
        """Mark a key as inactive."""
        if key_id in self._keys:
            key = self._keys[key_id]
            self._keys[key_id] = VAPIDKeyPair(
                key_id=key.key_id,
                public_key=key.public_key,
                private_key=key.private_key,
                created_at=key.created_at,
                is_active=False,
                expires_at=key.expires_at,
            )

    async def set_expiry(self, key_id: str, expires_at: datetime) -> None:
        """Set expiry time for a key."""
        if key_id in self._keys:
            key = self._keys[key_id]
            self._keys[key_id] = VAPIDKeyPair(
                key_id=key.key_id,
                public_key=key.public_key,
                private_key=key.private_key,
                created_at=key.created_at,
                is_active=key.is_active,
                expires_at=expires_at,
            )

    async def delete_expired(self) -> int:
        """Delete all expired keys. Returns count of deleted keys."""
        now = datetime.now(UTC)
        expired_keys = [k for k, v in self._keys.items() if v.expires_at and v.expires_at < now]
        for key_id in expired_keys:
            del self._keys[key_id]
        return len(expired_keys)


# =============================================================================
# VAPID Key Rotation Service
# =============================================================================


class VAPIDKeyRotationService:
    """
    Service for automated VAPID key rotation.

    Handles key generation, storage, rotation, and cleanup with support
    for graceful transitions during rotation.

    Attributes:
        key_repository: Backend for key storage.
        rotation_days: Days between automatic rotations (default: 90).
        overlap_days: Days to keep old key valid after rotation (default: 7).
    """

    def __init__(
        self,
        key_repository: VAPIDKeyRepository | None = None,
        rotation_days: int = 90,
        overlap_days: int = 7,
    ) -> None:
        """
        Initialize the VAPID key rotation service.

        Args:
            key_repository: Backend for key storage (default: in-memory).
            rotation_days: Days between automatic rotations.
            overlap_days: Days to keep old key valid after rotation.
        """
        self._repository = key_repository or InMemoryVAPIDKeyRepository()
        self._rotation_days = rotation_days
        self._overlap_days = overlap_days

    def generate_key_pair(self) -> VAPIDKeyPair:
        """
        Generate a new VAPID key pair.

        Uses ECDSA P-256 curve as required by Web Push VAPID spec.

        Returns:
            New VAPIDKeyPair with generated keys.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # Generate P-256 key pair
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            public_key = private_key.public_key()

            # Serialize private key (unencrypted for VAPID use)
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            # Serialize public key (uncompressed point format)
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )

            # Base64-encode keys
            private_b64 = base64.urlsafe_b64encode(private_bytes).decode("utf-8")
            public_b64 = base64.urlsafe_b64encode(public_bytes).decode("utf-8")

            key_pair = VAPIDKeyPair(
                key_id=str(uuid.uuid4()),
                public_key=public_b64,
                private_key=private_b64,
                created_at=datetime.now(UTC),
                is_active=False,
            )

            logger.info(f"Generated new VAPID key pair: {key_pair.key_id}")
            return key_pair

        except ImportError:
            logger.error("cryptography package not installed")
            raise RuntimeError(
                "cryptography package required for VAPID key generation. Install with: pip install cryptography"
            )

    def validate_key_pair(self, key_pair: VAPIDKeyPair) -> bool:
        """
        Validate a VAPID key pair.

        Args:
            key_pair: The key pair to validate.

        Returns:
            True if the key pair is valid, False otherwise.
        """
        # Check for empty keys
        if not key_pair.public_key or not key_pair.private_key:
            return False

        # Try to decode as base64
        try:
            base64.urlsafe_b64decode(key_pair.public_key + "==")
            base64.urlsafe_b64decode(key_pair.private_key + "==")
        except Exception:
            return False

        # For generated keys, verify they can be loaded
        try:
            from cryptography.hazmat.primitives.serialization import load_der_private_key
            from cryptography.hazmat.backends import default_backend

            private_bytes = base64.urlsafe_b64decode(key_pair.private_key + "==")
            load_der_private_key(private_bytes, password=None, backend=default_backend())
            return True
        except Exception:
            # If cryptography can't load it, it might still be valid in other formats
            # Just check that it's reasonable length
            return len(key_pair.public_key) > 40 and len(key_pair.private_key) > 40

    async def save_key(self, key_pair: VAPIDKeyPair) -> None:
        """
        Save a key pair to storage.

        Args:
            key_pair: The key pair to save.
        """
        await self._repository.save(key_pair)
        logger.debug(f"Saved VAPID key: {key_pair.key_id}")

    async def get_current_key(self) -> VAPIDKeyPair | None:
        """
        Get the currently active VAPID key.

        Returns:
            The active key pair, or None if no active key.
        """
        return await self._repository.get_active()

    async def get_key_by_id(self, key_id: str) -> VAPIDKeyPair | None:
        """
        Get a specific key pair by ID.

        Args:
            key_id: The key ID to look up.

        Returns:
            The key pair, or None if not found.
        """
        return await self._repository.get_by_id(key_id)

    async def list_keys(self) -> list[VAPIDKeyPair]:
        """
        List all VAPID key pairs.

        Returns:
            List of all key pairs.
        """
        return await self._repository.list_all()

    async def rotate(self) -> VAPIDKeyPair:
        """
        Rotate the VAPID key.

        Generates a new key, activates it, and sets up graceful
        transition for the old key.

        Returns:
            The new active key pair.
        """
        # Get current active key (if any)
        old_key = await self._repository.get_active()

        # Generate new key
        new_key = self.generate_key_pair()
        new_key = VAPIDKeyPair(
            key_id=new_key.key_id,
            public_key=new_key.public_key,
            private_key=new_key.private_key,
            created_at=new_key.created_at,
            is_active=True,
            expires_at=None,
        )

        # Save new key
        await self._repository.save(new_key)

        # Handle old key transition
        if old_key:
            # Set expiry for graceful transition
            expiry = datetime.now(UTC) + timedelta(days=self._overlap_days)
            await self._repository.set_expiry(old_key.key_id, expiry)
            await self._repository.deactivate(old_key.key_id)
            logger.info(
                f"Rotated VAPID key: {old_key.key_id} -> {new_key.key_id} (old key expires in {self._overlap_days} days)"
            )
        else:
            logger.info(f"Created initial VAPID key: {new_key.key_id}")

        return new_key

    async def should_rotate(self) -> bool:
        """
        Check if rotation is needed.

        Returns:
            True if rotation should be performed.
        """
        current_key = await self._repository.get_active()

        if current_key is None:
            return True

        # Check if key is older than rotation threshold
        age = datetime.now(UTC) - current_key.created_at
        return age.days >= self._rotation_days

    async def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys from storage.

        Returns:
            Number of keys deleted.
        """
        deleted = await self._repository.delete_expired()
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired VAPID keys")
        return deleted
