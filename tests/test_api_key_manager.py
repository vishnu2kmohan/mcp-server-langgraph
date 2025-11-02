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
from unittest.mock import AsyncMock, Mock, patch

import bcrypt
import pytest

from mcp_server_langgraph.auth.api_keys import APIKey, APIKeyManager


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
