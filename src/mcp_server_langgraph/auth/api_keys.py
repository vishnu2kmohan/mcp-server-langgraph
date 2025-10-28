"""
API Key Management

Manages API key lifecycle including generation, validation, rotation, and revocation.
API keys are stored as bcrypt hashes in Keycloak user attributes and exchanged for
JWTs on each request.

See ADR-0034 for API key to JWT exchange pattern.
"""

import secrets
import bcrypt
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from mcp_server_langgraph.auth.keycloak import KeycloakClient


@dataclass
class APIKey:
    """API key metadata"""

    key_id: str
    name: str
    created: str
    expires_at: str
    last_used: Optional[str] = None


class APIKeyManager:
    """Manage API key lifecycle"""

    DEFAULT_PREFIX = "mcpkey_live_"
    TEST_PREFIX = "mcpkey_test_"
    MAX_KEYS_PER_USER = 5
    BCRYPT_ROUNDS = 12

    def __init__(self, keycloak_client: KeycloakClient):
        """
        Initialize API key manager

        Args:
            keycloak_client: Keycloak client for user attribute storage
        """
        self.keycloak = keycloak_client

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
    ) -> Dict[str, Any]:
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
            raise ValueError(
                f"Maximum API keys reached ({self.MAX_KEYS_PER_USER}). "
                "Please revoke an existing key before creating a new one."
            )

        # Generate new API key
        api_key = self.generate_api_key()

        # Hash for storage
        key_hash = self.hash_api_key(api_key)

        # Generate key ID
        key_id = secrets.token_hex(8)

        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expires_days)

        # Store in Keycloak attributes
        existing_keys.append(f"key:{key_id}:{key_hash}")
        attributes["apiKeys"] = existing_keys
        attributes[f"apiKey_{key_id}_name"] = name
        attributes[f"apiKey_{key_id}_created"] = created_at.isoformat()
        attributes[f"apiKey_{key_id}_expiresAt"] = expires_at.isoformat()

        await self.keycloak.update_user_attributes(user_id, attributes)

        return {
            "key_id": key_id,
            "api_key": api_key,  # Return once, never stored plaintext
            "name": name,
            "expires_at": expires_at.isoformat(),
        }

    async def validate_and_get_user(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return user information

        Args:
            api_key: Plain API key to validate

        Returns:
            Dictionary with user_id, username, email, key_id if valid, None otherwise
        """
        # Search all users for matching key hash
        users = await self.keycloak.search_users()

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
                        if datetime.utcnow() > expires_at:
                            continue  # Expired

                    # Update last used timestamp
                    attributes[f"apiKey_{key_id}_lastUsed"] = datetime.utcnow().isoformat()
                    await self.keycloak.update_user_attributes(user["id"], attributes)

                    return {
                        "user_id": f"user:{user['username']}",
                        "username": user["username"],
                        "email": user.get("email"),
                        "key_id": key_id,
                    }

        return None  # Invalid key

    async def revoke_api_key(self, user_id: str, key_id: str):
        """
        Revoke specific API key

        Args:
            user_id: User identifier
            key_id: Key identifier to revoke
        """
        # Get current attributes
        attributes = await self.keycloak.get_user_attributes(user_id)
        api_keys = attributes.get("apiKeys", [])

        # Remove key entry
        attributes["apiKeys"] = [
            key for key in api_keys if not key.startswith(f"key:{key_id}:")
        ]

        # Remove metadata
        attributes.pop(f"apiKey_{key_id}_name", None)
        attributes.pop(f"apiKey_{key_id}_created", None)
        attributes.pop(f"apiKey_{key_id}_expiresAt", None)
        attributes.pop(f"apiKey_{key_id}_lastUsed", None)

        await self.keycloak.update_user_attributes(user_id, attributes)

    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
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

    async def rotate_api_key(
        self, user_id: str, key_id: str, grace_period_days: int = 0
    ) -> Dict[str, Any]:
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
                    new_expires = datetime.utcnow() + timedelta(days=grace_period_days)
                    attributes[f"apiKey_{key_id}_expiresAt"] = new_expires.isoformat()

                break

        if not key_found:
            raise ValueError(f"API key with ID '{key_id}' not found for user '{user_id}'")

        # Update attributes
        attributes["apiKeys"] = api_keys
        await self.keycloak.update_user_attributes(user_id, attributes)

        return {
            "key_id": key_id,
            "new_api_key": new_api_key,
        }
