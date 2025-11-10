"""
Tests for API Key Manager

Following TDD principles - these tests are written BEFORE implementation.
Tests cover:
- API key generation and creation
- bcrypt hashing and validation
- Key rotation and revocation
- Expiration handling
- Listing keys per user
- Keycloak attribute storage
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import bcrypt
import pytest

from mcp_server_langgraph.auth.api_keys import APIKeyManager


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client for testing"""
    client = AsyncMock()
    client.get_user_attributes = AsyncMock(return_value={})
    client.update_user_attributes = AsyncMock()
    client.search_users = AsyncMock(return_value=[])
    return client


@pytest.fixture
def api_key_manager(mock_keycloak_client):
    """API Key Manager instance for testing"""
    return APIKeyManager(keycloak_client=mock_keycloak_client)


class TestAPIKeyGeneration:
    """Test API key generation"""

    @pytest.mark.unit
    def test_generate_api_key_format(self, api_key_manager):
        """Test that generated API keys have correct format"""
        api_key = api_key_manager.generate_api_key()

        assert api_key.startswith("mcpkey_live_")
        # Key should be long enough (32 bytes base64)
        assert len(api_key) > 40

    @pytest.mark.unit
    def test_generate_api_key_uniqueness(self, api_key_manager):
        """Test that generated keys are cryptographically unique"""
        keys = {api_key_manager.generate_api_key() for _ in range(100)}

        # All keys should be unique
        assert len(keys) == 100

    @pytest.mark.unit
    def test_generate_api_key_test_prefix(self, api_key_manager):
        """Test generating API key with test prefix"""
        api_key = api_key_manager.generate_api_key(prefix="mcpkey_test_")

        assert api_key.startswith("mcpkey_test_")


class TestAPIKeyCreation:
    """Test API key creation"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_api_key_success(self, api_key_manager, mock_keycloak_client):
        """Test successful API key creation"""
        # Arrange
        user_id = "user:alice"
        name = "Production Key"
        mock_keycloak_client.get_user_attributes.return_value = {}

        # Act
        result = await api_key_manager.create_api_key(
            user_id=user_id,
            name=name,
            expires_days=365,
        )

        # Assert
        assert result["key_id"] is not None
        assert result["api_key"].startswith("mcpkey_live_")
        assert result["name"] == name
        assert "expires_at" in result

        # Verify Keycloak attributes updated
        mock_keycloak_client.update_user_attributes.assert_called_once()
        call_args = mock_keycloak_client.update_user_attributes.call_args[0][1]
        assert "apiKeys" in call_args
        assert len(call_args["apiKeys"]) == 1

        # Verify key is hashed in storage
        key_entry = call_args["apiKeys"][0]
        assert key_entry.startswith("key:")
        assert "$2b$" in key_entry  # bcrypt hash

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_api_key_returns_created_timestamp(self, api_key_manager, mock_keycloak_client):
        """
        REGRESSION TEST for Codex finding: API key creation must return 'created' timestamp.

        The CreateAPIKeyResponse schema requires 'created' field, but create_api_key()
        was only returning key_id, api_key, name, and expires_at, causing the API
        endpoint to fill 'created' with an empty string.

        This violates the API contract and breaks clients expecting the created timestamp.
        """
        # Arrange
        user_id = "user:bob"
        name = "Test Key"
        mock_keycloak_client.get_user_attributes.return_value = {}

        # Act
        result = await api_key_manager.create_api_key(
            user_id=user_id,
            name=name,
            expires_days=365,
        )

        # Assert - CRITICAL: Verify 'created' field is present in return value
        assert "created" in result, (
            "create_api_key() must return 'created' timestamp to satisfy API contract. "
            "The CreateAPIKeyResponse schema requires this field."
        )
        assert result["created"] != "", "created timestamp must not be empty"

        # Verify it's a valid ISO format timestamp
        from datetime import datetime

        try:
            created_dt = datetime.fromisoformat(result["created"])
            # Should be recent (within last minute)
            assert abs((datetime.utcnow() - created_dt).total_seconds()) < 60
        except ValueError:
            pytest.fail(f"created field must be valid ISO format timestamp, got: {result['created']}")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_api_key_enforces_max_limit(self, api_key_manager, mock_keycloak_client):
        """Test that creating more than max keys raises error"""
        # Arrange
        user_id = "user:bob"
        existing_keys = [f"key:id{i}:hash{i}" for i in range(5)]  # 5 existing keys
        mock_keycloak_client.get_user_attributes.return_value = {"apiKeys": existing_keys}

        # Act & Assert
        with pytest.raises(ValueError, match="Maximum API keys reached"):
            await api_key_manager.create_api_key(
                user_id=user_id,
                name="Sixth Key",
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_api_key_stores_metadata(self, api_key_manager, mock_keycloak_client):
        """Test that API key metadata is stored correctly"""
        # Arrange
        user_id = "user:charlie"
        name = "Test Key"
        mock_keycloak_client.get_user_attributes.return_value = {}

        # Act
        result = await api_key_manager.create_api_key(
            user_id=user_id,
            name=name,
            expires_days=90,
        )

        # Assert
        call_args = mock_keycloak_client.update_user_attributes.call_args[0][1]
        key_id = result["key_id"]

        # Check metadata attributes
        assert call_args[f"apiKey_{key_id}_name"] == name
        assert f"apiKey_{key_id}_created" in call_args
        assert f"apiKey_{key_id}_expiresAt" in call_args

        # Verify expiration is ~90 days from now
        expires_at = datetime.fromisoformat(call_args[f"apiKey_{key_id}_expiresAt"])
        expected_expiry = datetime.utcnow() + timedelta(days=90)
        assert abs((expires_at - expected_expiry).total_seconds()) < 60  # Within 1 minute


class TestAPIKeyValidation:
    """Test API key validation"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_success(self, api_key_manager, mock_keycloak_client):
        """Test successful API key validation"""
        # Arrange
        api_key = "mcpkey_live_testkeyvalue123"
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        mock_keycloak_client.search_users.return_value = [
            {
                "id": "user-123",
                "username": "alice",
                "email": "alice@example.com",
                "attributes": {
                    "apiKeys": [f"key:abc123:{key_hash}"],
                    "apiKey_abc123_name": "Production Key",
                    "apiKey_abc123_expiresAt": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                },
            }
        ]

        # Act
        user_info = await api_key_manager.validate_and_get_user(api_key)

        # Assert
        assert user_info is not None
        assert user_info["user_id"] == "user:alice"
        assert user_info["username"] == "alice"
        assert user_info["key_id"] == "abc123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_invalid_key(self, api_key_manager, mock_keycloak_client):
        """Test that invalid API key returns None"""
        # Arrange
        mock_keycloak_client.search_users.return_value = []

        # Act
        user_info = await api_key_manager.validate_and_get_user("mcpkey_live_invalid")

        # Assert
        assert user_info is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_expired_key(self, api_key_manager, mock_keycloak_client):
        """Test that expired API key is rejected"""
        # Arrange
        api_key = "mcpkey_live_expiredkey"
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        mock_keycloak_client.search_users.return_value = [
            {
                "id": "user-123",
                "username": "alice",
                "attributes": {
                    "apiKeys": [f"key:old123:{key_hash}"],
                    "apiKey_old123_expiresAt": (datetime.utcnow() - timedelta(days=1)).isoformat(),  # Expired yesterday
                },
            }
        ]

        # Act
        user_info = await api_key_manager.validate_and_get_user(api_key)

        # Assert
        assert user_info is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_updates_last_used(self, api_key_manager, mock_keycloak_client):
        """Test that successful validation updates last_used timestamp"""
        # Arrange
        api_key = "mcpkey_live_testkey"
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

        mock_keycloak_client.search_users.return_value = [
            {
                "id": "user-123",
                "username": "alice",
                "attributes": {
                    "apiKeys": [f"key:xyz:{key_hash}"],
                    "apiKey_xyz_expiresAt": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                },
            }
        ]

        # Act
        await api_key_manager.validate_and_get_user(api_key)

        # Assert
        # Verify last_used was updated
        mock_keycloak_client.update_user_attributes.assert_called_once()
        call_args = mock_keycloak_client.update_user_attributes.call_args[0][1]
        assert "apiKey_xyz_lastUsed" in call_args


class TestAPIKeyRevocation:
    """Test API key revocation"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_revoke_api_key_success(self, api_key_manager, mock_keycloak_client):
        """Test successful API key revocation"""
        # Arrange
        user_id = "user:dave"
        key_id = "abc123"

        mock_keycloak_client.get_user_attributes.return_value = {
            "apiKeys": [
                "key:abc123:hash1",
                "key:xyz789:hash2",
            ],
            "apiKey_abc123_name": "Key to Revoke",
            "apiKey_xyz789_name": "Keep This Key",
        }

        # Act
        await api_key_manager.revoke_api_key(user_id, key_id)

        # Assert
        call_args = mock_keycloak_client.update_user_attributes.call_args[0][1]

        # Only one key remaining
        assert len(call_args["apiKeys"]) == 1
        assert call_args["apiKeys"][0] == "key:xyz789:hash2"

        # Metadata for revoked key should be removed
        assert "apiKey_abc123_name" not in call_args
        assert "apiKey_xyz789_name" in call_args  # Other key metadata preserved

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_revoke_nonexistent_key_no_error(self, api_key_manager, mock_keycloak_client):
        """Test revoking non-existent key doesn't raise error"""
        # Arrange
        user_id = "user:eve"
        mock_keycloak_client.get_user_attributes.return_value = {"apiKeys": ["key:other:hash"]}

        # Act - should not raise
        await api_key_manager.revoke_api_key(user_id, "nonexistent")

        # Assert - update still called (idempotent)
        mock_keycloak_client.update_user_attributes.assert_called_once()


class TestAPIKeyListing:
    """Test listing API keys"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_api_keys_success(self, api_key_manager, mock_keycloak_client):
        """Test listing API keys for a user"""
        # Arrange
        user_id = "user:frank"
        now = datetime.utcnow()

        mock_keycloak_client.get_user_attributes.return_value = {
            "apiKeys": [
                "key:key1:hash1",
                "key:key2:hash2",
            ],
            "apiKey_key1_name": "Production Key",
            "apiKey_key1_created": now.isoformat(),
            "apiKey_key1_lastUsed": now.isoformat(),
            "apiKey_key1_expiresAt": (now + timedelta(days=365)).isoformat(),
            "apiKey_key2_name": "Test Key",
            "apiKey_key2_created": now.isoformat(),
            "apiKey_key2_expiresAt": (now + timedelta(days=90)).isoformat(),
        }

        # Act
        keys = await api_key_manager.list_api_keys(user_id)

        # Assert
        assert len(keys) == 2

        # Check first key
        assert keys[0]["key_id"] == "key1"
        assert keys[0]["name"] == "Production Key"
        assert keys[0]["created"] == now.isoformat()
        assert keys[0]["last_used"] == now.isoformat()

        # Check second key
        assert keys[1]["key_id"] == "key2"
        assert keys[1]["name"] == "Test Key"
        assert "last_used" not in keys[1]  # Never used

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_api_keys_empty(self, api_key_manager, mock_keycloak_client):
        """Test listing API keys when user has none"""
        # Arrange
        mock_keycloak_client.get_user_attributes.return_value = {}

        # Act
        keys = await api_key_manager.list_api_keys("user:nobody")

        # Assert
        assert keys == []


class TestAPIKeyRotation:
    """Test API key rotation"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_api_key_success(self, api_key_manager, mock_keycloak_client):
        """Test successful API key rotation"""
        # Arrange
        user_id = "user:george"
        key_id = "old123"
        old_hash = bcrypt.hashpw(b"old_key", bcrypt.gensalt()).decode()

        mock_keycloak_client.get_user_attributes.return_value = {
            "apiKeys": [f"key:old123:{old_hash}"],
            "apiKey_old123_name": "Production Key",
            "apiKey_old123_created": datetime.utcnow().isoformat(),
        }

        # Act
        result = await api_key_manager.rotate_api_key(user_id, key_id)

        # Assert
        assert result["new_api_key"].startswith("mcpkey_live_")
        assert result["key_id"] == key_id

        # Verify new hash is different from old hash
        call_args = mock_keycloak_client.update_user_attributes.call_args[0][1]
        new_key_entry = call_args["apiKeys"][0]
        assert old_hash not in new_key_entry  # Different hash
        assert "$2b$" in new_key_entry  # Still bcrypt

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_nonexistent_key_raises_error(self, api_key_manager, mock_keycloak_client):
        """Test rotating non-existent key raises error"""
        # Arrange
        mock_keycloak_client.get_user_attributes.return_value = {"apiKeys": []}

        # Act & Assert
        with pytest.raises(ValueError, match="API key.*not found"):
            await api_key_manager.rotate_api_key("user:harry", "missing")


class TestBcryptHashing:
    """Test bcrypt hashing functionality"""

    @pytest.mark.unit
    def test_hash_api_key(self, api_key_manager):
        """Test that API keys are hashed with bcrypt"""
        api_key = "mcpkey_live_test123"

        hashed = api_key_manager.hash_api_key(api_key)

        # Should be bcrypt hash
        assert hashed.startswith("$2b$")
        # Should verify correctly
        assert bcrypt.checkpw(api_key.encode(), hashed.encode())

    @pytest.mark.unit
    def test_verify_api_key_hash(self, api_key_manager):
        """Test API key hash verification"""
        api_key = "mcpkey_live_verify_test"
        hashed = api_key_manager.hash_api_key(api_key)

        # Correct key should verify
        assert api_key_manager.verify_api_key_hash(api_key, hashed) is True

        # Incorrect key should not verify
        assert api_key_manager.verify_api_key_hash("wrong_key", hashed) is False


class TestAPIKeyValidationPagination:
    """Test API key validation with pagination (>100 users)

    Regression test for Finding #4 from OpenAI Codex security audit.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_beyond_first_page(self, api_key_manager, mock_keycloak_client):
        """Test that API key validation works for users beyond first 100"""
        # Arrange - Create 150 mock users, target user at index 120
        api_key = "mcpkey_live_user120_key"
        key_hash = api_key_manager.hash_api_key(api_key)

        def mock_search_users(first=0, max=100):
            """Mock paginated user search"""
            all_users = []
            # Create 150 users
            for i in range(150):
                user = {
                    "id": f"uuid-{i}",
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "attributes": {},
                }
                # User 120 has the API key we're looking for
                if i == 120:
                    user["attributes"] = {
                        "apiKeys": [f"key:target_key:{key_hash}"],
                        "apiKey_target_key_name": "Target User Key",
                        "apiKey_target_key_created": datetime.utcnow().isoformat(),
                        "apiKey_target_key_expiresAt": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    }
                all_users.append(user)

            # Return the requested page
            return all_users[first : first + max]

        mock_keycloak_client.search_users.side_effect = mock_search_users
        mock_keycloak_client.update_user_attributes = AsyncMock()

        # Act
        result = await api_key_manager.validate_and_get_user(api_key)

        # Assert
        assert result is not None, "Should find API key on user 120 (beyond first page of 100)"
        assert result["username"] == "user120"
        assert result["user_id"] == "user:user120"
        assert result["keycloak_id"] == "uuid-120"
        assert result["key_id"] == "target_key"

        # Verify pagination happened (should have called search_users multiple times)
        assert mock_keycloak_client.search_users.call_count >= 2, "Should paginate through users"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_not_found_after_pagination(self, api_key_manager, mock_keycloak_client):
        """Test that validation returns None after checking all pages"""

        # Arrange - Create 150 users, none with matching key
        def mock_search_users(first=0, max=100):
            """Mock paginated user search"""
            all_users = []
            for i in range(150):
                user = {
                    "id": f"uuid-{i}",
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "attributes": {},  # No API keys
                }
                all_users.append(user)

            # Return the requested page
            return all_users[first : first + max]

        mock_keycloak_client.search_users.side_effect = mock_search_users

        # Act
        result = await api_key_manager.validate_and_get_user("mcpkey_live_nonexistent")

        # Assert
        assert result is None, "Should return None when key not found in any page"

        # Verify all pages were checked
        assert mock_keycloak_client.search_users.call_count >= 2, "Should check all pages"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_api_key_pagination_stops_on_match(self, api_key_manager, mock_keycloak_client):
        """Test that pagination stops immediately when key is found"""
        # Arrange - Create 250 users, target at index 50 (first page)
        api_key = "mcpkey_live_user50_key"
        key_hash = api_key_manager.hash_api_key(api_key)

        def mock_search_users(first=0, max=100):
            """Mock paginated user search"""
            all_users = []
            for i in range(250):
                user = {
                    "id": f"uuid-{i}",
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "attributes": {},
                }
                # User 50 has the API key (first page)
                if i == 50:
                    user["attributes"] = {
                        "apiKeys": [f"key:early_key:{key_hash}"],
                        "apiKey_early_key_name": "Early User Key",
                        "apiKey_early_key_created": datetime.utcnow().isoformat(),
                        "apiKey_early_key_expiresAt": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    }
                all_users.append(user)

            return all_users[first : first + max]

        mock_keycloak_client.search_users.side_effect = mock_search_users
        mock_keycloak_client.update_user_attributes = AsyncMock()

        # Act
        result = await api_key_manager.validate_and_get_user(api_key)

        # Assert
        assert result is not None
        assert result["username"] == "user50"

        # Should only call search_users once (found on first page)
        assert mock_keycloak_client.search_users.call_count == 1, "Should stop on first match"


@pytest.mark.unit
class TestAPIKeyRedisCache:
    """Test Redis caching for API key validation (performance optimization)"""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()
        redis_mock.delete = AsyncMock()
        return redis_mock

    @pytest.fixture
    def api_key_manager_with_cache(self, mock_keycloak_client, mock_redis_client):
        """Create APIKeyManager with Redis cache enabled"""
        return APIKeyManager(
            keycloak_client=mock_keycloak_client,
            redis_client=mock_redis_client,
            cache_ttl=3600,
            cache_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_cache_hit_skips_keycloak_lookup(self, api_key_manager_with_cache, mock_keycloak_client, mock_redis_client):
        """Test that cache hit avoids expensive Keycloak pagination"""
        import json

        # Arrange
        api_key = "mcpkey_live_test123"
        cached_user_info = {
            "user_id": "user:alice",
            "keycloak_id": "uuid-123",
            "username": "alice",
            "email": "alice@example.com",
            "key_id": "abc123",
            "expires_at": "2099-12-31T23:59:59",
        }

        # Mock Redis cache hit
        mock_redis_client.get.return_value = json.dumps(cached_user_info).encode()

        # Act
        result = await api_key_manager_with_cache.validate_and_get_user(api_key)

        # Assert - should return cached data
        assert result == cached_user_info
        # Should NOT call Keycloak
        mock_keycloak_client.search_users.assert_not_called()
        # Should have called Redis get
        mock_redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_falls_back_to_keycloak(
        self, api_key_manager_with_cache, mock_keycloak_client, mock_redis_client
    ):
        """Test that cache miss falls back to Keycloak and caches result"""
        # Arrange
        api_key = "mcpkey_live_test123"
        key_hash = api_key_manager_with_cache.hash_api_key(api_key)

        # Mock Keycloak user with API key
        mock_user = {
            "id": "uuid-123",
            "username": "alice",
            "email": "alice@example.com",
            "attributes": {
                "apiKeys": [f"key:abc123:{key_hash}"],
                "apiKey_abc123_expiresAt": "2099-12-31T23:59:59",
            },
        }

        # Mock Redis cache miss
        mock_redis_client.get.return_value = None

        # Mock Keycloak search
        mock_keycloak_client.search_users = AsyncMock(return_value=[mock_user])
        mock_keycloak_client.update_user_attributes = AsyncMock()

        # Act
        result = await api_key_manager_with_cache.validate_and_get_user(api_key)

        # Assert
        assert result is not None
        assert result["username"] == "alice"
        # Should have called Keycloak
        mock_keycloak_client.search_users.assert_called()
        # Should have cached the result
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_invalidates_cache(self, api_key_manager_with_cache, mock_keycloak_client, mock_redis_client):
        """Test that revoking API key invalidates Redis cache"""
        # Arrange
        user_id = "user:alice"
        key_id = "abc123"
        cache_hash = "sha256hash123"

        mock_keycloak_client.get_user_attributes = AsyncMock(
            return_value={
                "apiKeys": [f"key:{key_id}:bcrypthash"],
                f"apiKey_{key_id}_cacheHash": cache_hash,
                f"apiKey_{key_id}_name": "Test Key",
                f"apiKey_{key_id}_created": "2024-01-01T00:00:00",
                f"apiKey_{key_id}_expiresAt": "2025-01-01T00:00:00",
            }
        )
        mock_keycloak_client.update_user_attributes = AsyncMock()

        # Act
        await api_key_manager_with_cache.revoke_api_key(user_id, key_id)

        # Assert - should have invalidated cache
        mock_redis_client.delete.assert_called_once_with(f"apikey:{cache_hash}")

    @pytest.mark.asyncio
    async def test_cache_disabled_skips_redis(self, mock_keycloak_client, mock_redis_client):
        """Test that disabling cache skips Redis operations"""
        # Arrange - cache disabled
        manager = APIKeyManager(
            keycloak_client=mock_keycloak_client,
            redis_client=mock_redis_client,
            cache_enabled=False,
        )

        api_key = "mcpkey_live_test123"
        key_hash = manager.hash_api_key(api_key)

        mock_user = {
            "id": "uuid-123",
            "username": "alice",
            "attributes": {
                "apiKeys": [f"key:abc123:{key_hash}"],
                "apiKey_abc123_expiresAt": "2099-12-31T23:59:59",
            },
        }

        mock_keycloak_client.search_users = AsyncMock(return_value=[mock_user])
        mock_keycloak_client.update_user_attributes = AsyncMock()

        # Act
        result = await manager.validate_and_get_user(api_key)

        # Assert
        assert result is not None
        # Should NOT have called Redis
        mock_redis_client.get.assert_not_called()
        mock_redis_client.setex.assert_not_called()


# ============================================================================
# TDD RED Phase: OpenAI Codex Finding #5 - Redis API Key Cache Not Wired
# ============================================================================


class TestRedisAPICacheConfiguration:
    """
    TDD RED phase tests for Redis API key cache configuration (OpenAI Codex Finding #5).

    ISSUE: get_api_key_manager() in core/dependencies.py creates APIKeyManager
    without passing redis_client, even though settings.api_key_cache_enabled=True
    and settings.api_key_cache_ttl are configured.

    IMPACT: API key cache is disabled, causing performance degradation and
    unnecessary Keycloak queries on every API key validation.

    These tests will FAIL until dependencies.py wires Redis client.
    """

    @pytest.mark.unit
    def test_get_api_key_manager_uses_redis_when_enabled(self):
        """
        Test that get_api_key_manager passes Redis client when caching is enabled.
        """
        from unittest.mock import MagicMock

        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Reset global state
        deps_module._api_key_manager = None

        mock_keycloak = MagicMock()

        # Patch settings module to enable caching
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.api_key_cache_db = 2
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False

            with patch("redis.asyncio.from_url") as mock_redis_from_url:
                mock_redis_client = AsyncMock()
                mock_redis_from_url.return_value = mock_redis_client

                # Act - get manager instance
                manager = get_api_key_manager(keycloak=mock_keycloak)

                # Assert - Redis client should be wired
                assert manager.redis is not None, (
                    "APIKeyManager.redis should be set when caching is enabled. "
                    "This proves dependencies.py is wiring Redis client correctly."
                )
                assert manager.cache_enabled is True, "Caching should be enabled"
                assert manager.cache_ttl == 3600, "Cache TTL should match settings"

        # Cleanup
        deps_module._api_key_manager = None

    @pytest.mark.unit
    def test_get_api_key_manager_respects_cache_ttl_from_settings(self):
        """
        Test that cache TTL from settings is passed to APIKeyManager.
        """
        from unittest.mock import MagicMock

        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Reset global state
        deps_module._api_key_manager = None

        custom_ttl = 7200  # 2 hours
        mock_keycloak = MagicMock()

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.api_key_cache_ttl = custom_ttl
            mock_settings.api_key_cache_db = 2
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False

            with patch("redis.asyncio.from_url"):
                manager = get_api_key_manager(keycloak=mock_keycloak)

                assert (
                    manager.cache_ttl == custom_ttl
                ), f"Cache TTL should be {custom_ttl} from settings, got {manager.cache_ttl}"

        # Cleanup
        deps_module._api_key_manager = None

    @pytest.mark.unit
    def test_get_api_key_manager_uses_correct_redis_database(self):
        """
        Test that Redis client connects to correct database number.
        """
        from unittest.mock import MagicMock

        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Reset global state
        deps_module._api_key_manager = None

        mock_keycloak = MagicMock()

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.api_key_cache_db = 5  # Custom database number
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False

            with patch("redis.asyncio.from_url") as mock_from_url:
                get_api_key_manager(keycloak=mock_keycloak)

                # Verify from_url was called with correct database
                mock_from_url.assert_called_once()
                call_args = mock_from_url.call_args
                redis_url_arg = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")

                assert "/5" in redis_url_arg or redis_url_arg.endswith(
                    "/5"
                ), f"Redis URL should include database /5, got: {redis_url_arg}"

        # Cleanup
        deps_module._api_key_manager = None

    @pytest.mark.unit
    def test_get_api_key_manager_disables_cache_when_redis_url_missing(self):
        """
        Test that caching is disabled when redis_url is not configured.

        GREEN: This should already work (graceful degradation)
        """
        from unittest.mock import MagicMock

        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Reset global state
        deps_module._api_key_manager = None

        mock_keycloak = MagicMock()

        # Patch settings with no redis_url (using empty string since None fails validation)
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True  # Enabled, but no redis_url
            mock_settings.redis_url = ""  # Empty string instead of None

            manager = get_api_key_manager(keycloak=mock_keycloak)

            # Should gracefully disable caching
            assert manager.cache_enabled is False, "Caching should be disabled without redis_url"
            assert manager.redis is None, "Redis client should be None without redis_url"

        # Cleanup
        deps_module._api_key_manager = None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_api_key_validation_uses_redis_cache(self, mock_keycloak_client):
        """
        Integration test: Verify API key validation actually uses Redis cache.
        """
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Reset global state
        deps_module._api_key_manager = None

        # Create manager with Redis
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.api_key_cache_db = 2
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False

            with patch("redis.asyncio.from_url") as mock_from_url:
                mock_redis = AsyncMock()
                mock_redis.get.return_value = None  # Cache miss first time
                mock_redis.setex = AsyncMock()
                mock_from_url.return_value = mock_redis

                manager = get_api_key_manager(keycloak=mock_keycloak_client)

                # Setup Keycloak to return a user with API key
                api_key = manager.generate_api_key()
                key_hash = manager.hash_api_key(api_key)

                mock_user = {
                    "id": "uuid-test",
                    "username": "testuser",
                    "attributes": {
                        "apiKeys": [f"key:testkey:{key_hash}"],
                        "apiKey_testkey_name": "Test Key",
                        "apiKey_testkey_expiresAt": "2099-12-31T23:59:59",
                    },
                }
                mock_keycloak_client.search_users.return_value = [mock_user]

                # Act - validate API key (should cache result)
                result = await manager.validate_and_get_user(api_key)

                # Assert
                assert result is not None, "Validation should succeed"

                # CRITICAL: Verify Redis was used for caching
                assert mock_redis.get.called, (
                    "Redis get() should be called to check cache. " "This proves dependencies.py wired Redis client correctly."
                )
                assert mock_redis.setex.called, (
                    "Redis setex() should be called to cache result. " "This proves caching is active."
                )

        # Cleanup
        deps_module._api_key_manager = None
