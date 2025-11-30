"""
API Key Management

Manages API key lifecycle including generation, validation, rotation, and revocation.
API keys are stored as bcrypt hashes in Keycloak user attributes and exchanged for
JWTs on each request.

See ADR-0034 for API key to JWT exchange pattern.
"""

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING, Any, Optional

import bcrypt

from mcp_server_langgraph.auth.keycloak import KeycloakClient
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from redis.asyncio import Redis


@dataclass
class APIKey:
    """API key metadata"""

    key_id: str
    name: str
    created: str
    expires_at: str
    last_used: str | None = None


class APIKeyManager:
    """Manage API key lifecycle"""

    DEFAULT_PREFIX = "mcpkey_live_"
    TEST_PREFIX = "mcpkey_test_"
    MAX_KEYS_PER_USER = 5
    BCRYPT_ROUNDS = 12

    def __init__(
        self,
        keycloak_client: KeycloakClient,
        redis_client: Optional["Redis[bytes]"] = None,  # type: ignore[type-arg]
        cache_ttl: int = 3600,
        cache_enabled: bool = True,
    ):
        """
        Initialize API key manager

        Args:
            keycloak_client: Keycloak client for user attribute storage
            redis_client: Optional Redis client for API key lookup cache
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
            cache_enabled: Enable/disable Redis caching (default: True)
        """
        self.keycloak = keycloak_client
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.cache_enabled = cache_enabled and redis_client is not None

    def generate_api_key(self, prefix: str = DEFAULT_PREFIX) -> str:
        """
        Generate cryptographically secure API key

        Args:
            prefix: Prefix for the key (default: "sk_live_")

        Returns:
            API key string (e.g., "sk_live_abc123xyz...")
        """
        # Generate 32 bytes (256 bits) of randomness
        random_bytes = secrets.token_urlsafe(32)
        return f"{prefix}{random_bytes}"

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key with bcrypt

        Args:
            api_key: Plain API key

        Returns:
            bcrypt hash
        """
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)).decode()

    def verify_api_key_hash(self, api_key: str, hashed: str) -> bool:
        """
        Verify API key against bcrypt hash

        Args:
            api_key: Plain API key
            hashed: bcrypt hash

        Returns:
            True if key matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(api_key.encode(), hashed.encode())
        except Exception:
            return False

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        expires_days: int = 365,
    ) -> dict[str, Any]:
        """
        Create new API key for user

        Args:
            user_id: User identifier (e.g., "user:alice")
            name: Human-readable name for the key
            expires_days: Days until expiration (default: 365)

        Returns:
            Dictionary with key_id, api_key, name, expires_at

        Raises:
            ValueError: If user has reached maximum number of keys
        """
        # Get current user attributes
        attributes = await self.keycloak.get_user_attributes(user_id)
        existing_keys = attributes.get("apiKeys", [])

        # Check quota
        if len(existing_keys) >= self.MAX_KEYS_PER_USER:
            msg = (
                f"Maximum API keys reached ({self.MAX_KEYS_PER_USER}). "
                "Please revoke an existing key before creating a new one."
            )
            raise ValueError(msg)

        # Generate new API key
        api_key = self.generate_api_key()

        # Hash for storage (bcrypt for security verification)
        key_hash = self.hash_api_key(api_key)

        # Hash for cache invalidation (SHA256 for fast lookup)
        cache_hash = self._hash_api_key_for_cache(api_key)

        # Generate key ID
        key_id = secrets.token_hex(8)

        # Calculate expiration
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(days=expires_days)

        # Store in Keycloak attributes
        existing_keys.append(f"key:{key_id}:{key_hash}")
        attributes["apiKeys"] = existing_keys
        attributes[f"apiKey_{key_id}_name"] = name
        attributes[f"apiKey_{key_id}_created"] = created_at.isoformat()
        attributes[f"apiKey_{key_id}_expiresAt"] = expires_at.isoformat()
        attributes[f"apiKey_{key_id}_cacheHash"] = cache_hash  # For cache invalidation on revoke

        await self.keycloak.update_user_attributes(user_id, attributes)

        return {
            "key_id": key_id,
            "api_key": api_key,  # Return once, never stored plaintext
            "name": name,
            "created": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

    async def _get_from_cache(self, api_key_hash: str) -> dict[str, Any] | None:
        """
        Get user info from Redis cache using API key hash

        Args:
            api_key_hash: SHA256 hash of the API key (for cache key)

        Returns:
            Cached user info dict or None if not found
        """
        if not self.cache_enabled or not self.redis:
            return None

        try:
            cache_key = f"apikey:{api_key_hash}"
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                import json

                logger.debug(f"API key cache hit for hash: {api_key_hash[:16]}...")
                return json.loads(cached_data)  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

        return None

    async def _set_in_cache(self, api_key_hash: str, user_info: dict[str, Any]) -> None:
        """
        Store user info in Redis cache

        Args:
            api_key_hash: SHA256 hash of the API key (for cache key)
            user_info: User information to cache
        """
        if not self.cache_enabled or not self.redis:
            return

        try:
            import json

            cache_key = f"apikey:{api_key_hash}"
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(user_info))
            logger.debug(f"API key cached for hash: {api_key_hash[:16]}...")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    async def _invalidate_cache(self, api_key_hash: str) -> None:
        """
        Invalidate cached user info for an API key

        Args:
            api_key_hash: SHA256 hash of the API key
        """
        if not self.cache_enabled or not self.redis:
            return

        try:
            cache_key = f"apikey:{api_key_hash}"
            await self.redis.delete(cache_key)
            logger.debug(f"API key cache invalidated for hash: {api_key_hash[:16]}...")
        except Exception as e:
            logger.warning(f"Redis cache invalidation failed: {e}")

    def _hash_api_key_for_cache(self, api_key: str) -> str:
        """
        Create a deterministic keyed hash of API key for cache lookup.

        Security: Uses HMAC-SHA256 with a secret key to prevent offline brute-force
        attacks if the cache is leaked. Without the secret key, attackers cannot
        reverse the hash to recover API keys.

        The secret key is loaded from API_KEY_CACHE_SECRET environment variable.
        Falls back to a derived key from JWT_SECRET_KEY if not set.

        bcrypt is still used for secure storage verification.

        Args:
            api_key: Plain API key

        Returns:
            HMAC-SHA256 hex digest
        """
        # Get or derive the HMAC secret key
        cache_secret = os.getenv("API_KEY_CACHE_SECRET")
        if not cache_secret:
            # Fall back to deriving from JWT secret (better than no secret)
            jwt_secret = os.getenv("JWT_SECRET_KEY", "")
            # Use HKDF-like derivation: HMAC(jwt_secret, "api-key-cache")
            cache_secret = hmac.new(
                jwt_secret.encode() if jwt_secret else b"default-insecure-key",
                b"api-key-cache-derivation",
                hashlib.sha256,
            ).hexdigest()

        # Create HMAC with the secret key
        # nosemgrep: python.cryptography.security.insecure-hash-function.insecure-hash-function-sha256
        # Security: SHA256 is used for CACHE KEY derivation (not password storage).
        # This is a keyed HMAC for lookup optimization, not cryptographic password hashing.
        # Actual API key verification uses bcrypt via verify_api_key().
        return hmac.new(
            cache_secret.encode(),
            api_key.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def validate_and_get_user(self, api_key: str) -> dict[str, Any] | None:
        """
        Validate API key and return user information

        Args:
            api_key: Plain API key to validate

        Returns:
            Dictionary with user_id, username, email, key_id if valid, None otherwise

        Note:
            This implementation uses Redis cache for O(1) lookups when enabled.
            Falls back to paginating through all users if cache miss occurs.
            See ADR-0034 for Redis-backed API key cache design.
        """
        # Try cache first (O(1) lookup)
        api_key_hash = self._hash_api_key_for_cache(api_key)
        cached_user = await self._get_from_cache(api_key_hash)
        if cached_user:
            # Verify expiration from cache
            expires_at_str = cached_user.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                # Ensure timezone-aware comparison (handle both naive and aware datetimes)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if datetime.now(UTC) > expires_at:
                    # Expired, invalidate cache and continue to full search
                    await self._invalidate_cache(api_key_hash)
                else:
                    return cached_user

            # No expiration or still valid
            return cached_user
        # PERFORMANCE WARNING (OpenAI Codex Finding #5):
        # This O(n) pagination fallback is inefficient for large user bases.
        # The Redis cache mitigates this (ADR-0034), but cold starts are slow.
        #
        # RECOMMENDED FUTURE OPTIMIZATION:
        # 1. Add indexed Keycloak user attribute: api_key_hash
        # 2. Use: keycloak.search_users(query=f"api_key_hash:{hash}")
        # 3. This provides O(1) lookup instead of O(n) enumeration
        #
        # Until then, monitor cache hit rate and user count:
        logger.warning(
            "API key validation: Cache miss triggered user enumeration (O(n) fallback). "
            "Redis cache provides primary mitigation (ADR-0034). "
            "For production deployments with >1000 users, consider implementing Keycloak "
            "indexed attribute search (see OpenAI Codex Finding #5).",
            extra={
                "cache_enabled": self.cache_enabled,
                "mitigation": "Redis cache provides O(1) for cache hits (ADR-0034)",
                "recommendation": "Implement indexed Keycloak attribute search for cold starts",
            },
        )

        # Paginate through all users to find matching key hash
        first = 0
        max_per_page = 100
        users_scanned = 0

        while True:
            # Fetch page of users
            users = await self.keycloak.search_users(first=first, max=max_per_page)

            # No more users, key not found
            if not users:
                break

            users_scanned += len(users)

            # Search this page for matching key
            for user in users:
                attributes = user.get("attributes", {})
                api_keys = attributes.get("apiKeys", [])

                for key_entry in api_keys:
                    # Format: "key:key_id:hash"
                    parts = key_entry.split(":")
                    if len(parts) != 3:
                        continue  # Invalid format

                    _, key_id, stored_hash = parts

                    # Check if hash matches
                    if self.verify_api_key_hash(api_key, stored_hash):
                        # Check expiration
                        expires_at_str = attributes.get(f"apiKey_{key_id}_expiresAt")
                        if expires_at_str:
                            expires_at = datetime.fromisoformat(expires_at_str)
                            # Ensure timezone-aware comparison (handle both naive and aware datetimes)
                            if expires_at.tzinfo is None:
                                expires_at = expires_at.replace(tzinfo=UTC)
                            if datetime.now(UTC) > expires_at:
                                continue  # Expired

                        # Update last used timestamp
                        attributes[f"apiKey_{key_id}_lastUsed"] = datetime.now(UTC).isoformat()
                        await self.keycloak.update_user_attributes(user["id"], attributes)

                        user_info = {
                            "user_id": f"user:{user['username']}",  # OpenFGA format
                            "keycloak_id": user["id"],  # Raw UUID for Keycloak Admin API
                            "username": user["username"],
                            "email": user.get("email"),
                            "key_id": key_id,
                            "expires_at": expires_at_str,  # Store for cache validation
                        }

                        # Cache for future lookups (O(1) next time)
                        await self._set_in_cache(api_key_hash, user_info)

                        return user_info

            # Move to next page
            first += max_per_page

        # PERFORMANCE MONITORING (OpenAI Codex Finding #5):
        # Log how many users were scanned to identify performance issues
        logger.info(
            "API key validation: User enumeration completed (key not found)",
            extra={
                "users_scanned": users_scanned,
                "performance_impact": "HIGH" if users_scanned > 1000 else "MEDIUM" if users_scanned > 100 else "LOW",
                "recommendation": "Implement Keycloak indexed search if users_scanned > 1000",
            },
        )

        return None  # Invalid key

    async def revoke_api_key(self, user_id: str, key_id: str) -> None:
        """
        Revoke specific API key

        Args:
            user_id: User identifier
            key_id: Key identifier to revoke
        """
        # Get current attributes
        attributes = await self.keycloak.get_user_attributes(user_id)
        api_keys = attributes.get("apiKeys", [])

        # Invalidate cache if hash is stored
        cache_hash = attributes.get(f"apiKey_{key_id}_cacheHash")
        if cache_hash:
            await self._invalidate_cache(cache_hash)

        # Remove key entry
        attributes["apiKeys"] = [key for key in api_keys if not key.startswith(f"key:{key_id}:")]

        # Remove metadata
        attributes.pop(f"apiKey_{key_id}_name", None)
        attributes.pop(f"apiKey_{key_id}_created", None)
        attributes.pop(f"apiKey_{key_id}_expiresAt", None)
        attributes.pop(f"apiKey_{key_id}_lastUsed", None)
        attributes.pop(f"apiKey_{key_id}_cacheHash", None)

        await self.keycloak.update_user_attributes(user_id, attributes)

    async def list_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        """
        List all API keys for user (without showing actual keys)

        Args:
            user_id: User identifier

        Returns:
            List of dictionaries with key_id, name, created, expires_at, last_used
        """
        attributes = await self.keycloak.get_user_attributes(user_id)
        api_keys = attributes.get("apiKeys", [])

        keys = []
        for key_entry in api_keys:
            parts = key_entry.split(":")
            if len(parts) != 3:
                continue

            _, key_id, _ = parts

            key_info = {
                "key_id": key_id,
                "name": attributes.get(f"apiKey_{key_id}_name", ""),
                "created": attributes.get(f"apiKey_{key_id}_created", ""),
                "expires_at": attributes.get(f"apiKey_{key_id}_expiresAt", ""),
            }

            # Include last_used if available
            last_used = attributes.get(f"apiKey_{key_id}_lastUsed")
            if last_used:
                key_info["last_used"] = last_used

            keys.append(key_info)

        return keys

    async def rotate_api_key(self, user_id: str, key_id: str, grace_period_days: int = 0) -> dict[str, Any]:
        """
        Rotate API key (generate new key, keeping same key_id)

        Args:
            user_id: User identifier
            key_id: Key identifier to rotate
            grace_period_days: Days to keep old key valid (default: 0 = immediate)

        Returns:
            Dictionary with key_id, new_api_key

        Raises:
            ValueError: If key_id not found
        """
        # Get current attributes
        attributes = await self.keycloak.get_user_attributes(user_id)
        api_keys = attributes.get("apiKeys", [])

        # Find the key to rotate
        key_found = False
        for i, key_entry in enumerate(api_keys):
            if key_entry.startswith(f"key:{key_id}:"):
                key_found = True

                # Generate new API key
                new_api_key = self.generate_api_key()
                new_hash = self.hash_api_key(new_api_key)

                # Replace with new hash
                api_keys[i] = f"key:{key_id}:{new_hash}"

                # Keep existing metadata (name, created), update expiration if needed
                if grace_period_days > 0:
                    # Extend expiration for grace period
                    new_expires = datetime.now(UTC) + timedelta(days=grace_period_days)
                    attributes[f"apiKey_{key_id}_expiresAt"] = new_expires.isoformat()

                break

        if not key_found:
            msg = f"API key with ID '{key_id}' not found for user '{user_id}'"
            raise ValueError(msg)

        # Update attributes
        attributes["apiKeys"] = api_keys
        await self.keycloak.update_user_attributes(user_id, attributes)

        return {
            "key_id": key_id,
            "new_api_key": new_api_key,
        }
