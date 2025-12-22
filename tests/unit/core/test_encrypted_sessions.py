"""
Unit tests for Encrypted Sessions (ADR-0083 / OpenAI Agents SDK parity)

TDD: GREEN phase - Tests for the encrypted session implementation.

Encrypted sessions provide:
- At-rest encryption for sensitive session data
- Key rotation support
- Compliance with data protection requirements (GDPR, HIPAA)
- Feature flag control (enable_encrypted_sessions)

Reference: OpenAI Agents SDK Encrypted Sessions pattern
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.security]


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_encrypted_sessions_flag")
class TestEncryptedSessionsFeatureFlag:
    """Test encrypted sessions feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_encrypted_sessions_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN accessing enable_encrypted_sessions
        THEN it should exist as a boolean field with default=False
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_encrypted_sessions")
        assert isinstance(flags.enable_encrypted_sessions, bool)
        # Default should be False (opt-in for security features)
        assert flags.enable_encrypted_sessions is False

    def test_encrypted_sessions_disabled_skips_encryption(self) -> None:
        """GIVEN encrypted sessions feature flag is disabled
        WHEN storing session data
        THEN data should be stored without encryption
        """
        from mcp_server_langgraph.auth.encrypted_session_store import (
            ENCRYPTED_MARKER,
            EncryptedSessionStore,
        )

        store = EncryptedSessionStore(
            encryption_key=b"test-key-32-bytes-for-aes256!!!!",
            backend="memory",
        )

        # With flag disabled, metadata should not be encrypted
        with patch(
            "mcp_server_langgraph.auth.encrypted_session_store.feature_flags"
        ) as mock_flags:
            mock_flags.enable_encrypted_sessions = False
            result = store._encrypt_metadata({"sensitive": "data"})
            assert ENCRYPTED_MARKER not in result


# =============================================================================
# Encryption Module Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_session_encryption")
class TestSessionEncryptionModule:
    """Test the session encryption module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_encryptor_exists(self) -> None:
        """GIVEN the auth module
        WHEN importing SessionEncryptor
        THEN it should be available
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        assert SessionEncryptor is not None

    def test_session_encryptor_has_encrypt_method(self) -> None:
        """GIVEN a SessionEncryptor instance
        WHEN checking for encrypt method
        THEN it should have encrypt method
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        encryptor = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        assert hasattr(encryptor, "encrypt")
        assert callable(encryptor.encrypt)

    def test_session_encryptor_has_decrypt_method(self) -> None:
        """GIVEN a SessionEncryptor instance
        WHEN checking for decrypt method
        THEN it should have decrypt method
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        encryptor = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        assert hasattr(encryptor, "decrypt")
        assert callable(encryptor.decrypt)


# =============================================================================
# Encryption/Decryption Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_encrypt_decrypt")
class TestEncryptDecrypt:
    """Test encryption and decryption operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_encrypt_returns_bytes(self) -> None:
        """GIVEN plaintext session data
        WHEN encrypting the data
        THEN it should return encrypted bytes
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        encryptor = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        plaintext = b'{"session_id": "test-123", "user_id": "user-456"}'

        encrypted = encryptor.encrypt(plaintext)

        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext

    def test_decrypt_returns_original_plaintext(self) -> None:
        """GIVEN encrypted session data
        WHEN decrypting the data
        THEN it should return the original plaintext
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        encryptor = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        plaintext = b'{"session_id": "test-123", "user_id": "user-456"}'

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self) -> None:
        """GIVEN the same plaintext
        WHEN encrypting multiple times
        THEN each ciphertext should be different (due to random IV/nonce)
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        encryptor = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        plaintext = b'{"session_id": "test-123"}'

        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        assert encrypted1 != encrypted2  # IVs should differ

    def test_decrypt_with_wrong_key_fails(self) -> None:
        """GIVEN encrypted data
        WHEN decrypting with a different key
        THEN it should raise an error
        """
        from mcp_server_langgraph.auth.session_encryptor import (
            DecryptionError,
            SessionEncryptor,
        )

        encryptor1 = SessionEncryptor(key=b"test-key-32-bytes-for-aes256!!!!")
        encryptor2 = SessionEncryptor(key=b"different-key-32-bytes-aes256!!!")
        plaintext = b'{"session_id": "test-123"}'

        encrypted = encryptor1.encrypt(plaintext)

        with pytest.raises(DecryptionError):
            encryptor2.decrypt(encrypted)


# =============================================================================
# Key Management Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_key_management")
class TestKeyManagement:
    """Test encryption key management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_key_derivation_from_password(self) -> None:
        """GIVEN a password string
        WHEN deriving an encryption key
        THEN it should produce a valid 256-bit key
        """
        from mcp_server_langgraph.auth.session_encryptor import derive_key

        password = "my-secure-session-password"
        salt = b"unique-salt-value-16"

        key = derive_key(password, salt)

        assert isinstance(key, bytes)
        assert len(key) == 32  # 256 bits

    def test_key_rotation_support(self) -> None:
        """GIVEN encrypted data with old key
        WHEN rotating to a new key
        THEN data should be re-encrypted successfully
        """
        from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

        old_key = b"old-key-32-bytes-for-aes256-!!!!"
        new_key = b"new-key-32-bytes-for-aes256-!!!!"
        plaintext = b'{"session_id": "test-123"}'

        old_encryptor = SessionEncryptor(key=old_key)
        encrypted_old = old_encryptor.encrypt(plaintext)

        # Decrypt with old key, encrypt with new key (rotation)
        decrypted = old_encryptor.decrypt(encrypted_old)
        new_encryptor = SessionEncryptor(key=new_key)
        encrypted_new = new_encryptor.encrypt(decrypted)

        # Verify new encryption works
        decrypted_new = new_encryptor.decrypt(encrypted_new)
        assert decrypted_new == plaintext


# =============================================================================
# Session Store Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_encrypted_session_store")
class TestEncryptedSessionStore:
    """Test encrypted session storage integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_encrypted_session_store_create(self) -> None:
        """GIVEN an encrypted session store
        WHEN creating a new session
        THEN session data should be encrypted at rest
        """
        from mcp_server_langgraph.auth.encrypted_session_store import (
            EncryptedSessionStore,
        )

        store = EncryptedSessionStore(
            encryption_key=b"test-key-32-bytes-for-aes256!!!!",
            backend="memory",
        )

        with patch(
            "mcp_server_langgraph.auth.encrypted_session_store.feature_flags"
        ) as mock_flags:
            mock_flags.enable_encrypted_sessions = True

            session = await store.create(
                user_id="user-123",
                username="testuser",
                roles=["user"],
                metadata={"sensitive": "data"},
                ttl=3600,
            )

            assert session is not None
            assert session.session_id is not None

    @pytest.mark.asyncio
    async def test_encrypted_session_store_get_decrypts(self) -> None:
        """GIVEN an encrypted session in storage
        WHEN retrieving the session
        THEN data should be decrypted transparently
        """
        from mcp_server_langgraph.auth.encrypted_session_store import (
            EncryptedSessionStore,
        )

        store = EncryptedSessionStore(
            encryption_key=b"test-key-32-bytes-for-aes256!!!!",
            backend="memory",
        )

        with patch(
            "mcp_server_langgraph.auth.encrypted_session_store.feature_flags"
        ) as mock_flags:
            mock_flags.enable_encrypted_sessions = True

            created = await store.create(
                user_id="user-123",
                username="testuser",
                roles=["user"],
                metadata={"sensitive": "data"},
                ttl=3600,
            )

            retrieved = await store.get(created.session_id)

            assert retrieved is not None
            assert retrieved.user_id == "user-123"
            assert retrieved.metadata == {"sensitive": "data"}


# =============================================================================
# Module Exports Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_encrypted_sessions_exports")
class TestEncryptedSessionsExports:
    """Test module exports for encrypted sessions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exports_session_encryptor(self) -> None:
        """GIVEN the auth module
        WHEN checking exports
        THEN SessionEncryptor should be exported
        """
        from mcp_server_langgraph.auth import SessionEncryptor

        assert SessionEncryptor is not None

    def test_exports_encrypted_session_store(self) -> None:
        """GIVEN the auth module
        WHEN checking exports
        THEN EncryptedSessionStore should be exported
        """
        from mcp_server_langgraph.auth import EncryptedSessionStore

        assert EncryptedSessionStore is not None

    def test_exports_derive_key(self) -> None:
        """GIVEN the auth module
        WHEN checking exports
        THEN derive_key should be exported
        """
        from mcp_server_langgraph.auth import derive_key

        assert derive_key is not None

    def test_exports_decryption_error(self) -> None:
        """GIVEN the auth module
        WHEN checking exports
        THEN DecryptionError should be exported
        """
        from mcp_server_langgraph.auth import DecryptionError

        assert DecryptionError is not None
