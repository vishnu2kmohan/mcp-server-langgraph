"""
Tests for encrypted lookup table with real AES-256-GCM encryption.

These tests verify the security of PII storage through proper encryption,
replacing the placeholder base64 encoding with production-grade encryption.
"""

from __future__ import annotations

import gc
import json
import secrets
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.privacy, pytest.mark.pii]


@pytest.mark.xdist_group(name="test_lookup_table_key_management")
class TestLookupTableKeyManagement:
    """Tests for encryption key generation and management."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_generate_encryption_key_returns_bytes(self) -> None:
        """Test that generate_encryption_key returns proper key bytes."""
        from mcp_server_langgraph.privacy.lookup_table import generate_encryption_key

        key = generate_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) == 32  # AES-256 = 256 bits = 32 bytes

    def test_generate_encryption_key_is_random(self) -> None:
        """Test that each generated key is unique."""
        from mcp_server_langgraph.privacy.lookup_table import generate_encryption_key

        keys = [generate_encryption_key() for _ in range(10)]
        # All keys should be unique
        assert len(set(keys)) == 10

    def test_key_from_passphrase(self) -> None:
        """Test deriving encryption key from passphrase."""
        from mcp_server_langgraph.privacy.lookup_table import key_from_passphrase

        passphrase = "my-secure-passphrase"
        salt = secrets.token_bytes(16)

        key = key_from_passphrase(passphrase, salt)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_key_from_passphrase_deterministic(self) -> None:
        """Test that same passphrase and salt produce same key."""
        from mcp_server_langgraph.privacy.lookup_table import key_from_passphrase

        passphrase = "test-passphrase"
        salt = b"fixed-salt-value"

        key1 = key_from_passphrase(passphrase, salt)
        key2 = key_from_passphrase(passphrase, salt)
        assert key1 == key2

    def test_key_from_passphrase_different_salts(self) -> None:
        """Test that different salts produce different keys."""
        from mcp_server_langgraph.privacy.lookup_table import key_from_passphrase

        passphrase = "same-passphrase"
        salt1 = b"salt-one-value-"
        salt2 = b"salt-two-value-"

        key1 = key_from_passphrase(passphrase, salt1)
        key2 = key_from_passphrase(passphrase, salt2)
        assert key1 != key2


@pytest.mark.xdist_group(name="test_lookup_table_encryption_ops")
class TestLookupTableEncryptionOperations:
    """Tests for encryption/decryption operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_export_encrypted_with_key(self) -> None:
        """Test exporting table with real encryption."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_abc123>>", "john@example.com")
        table.store("<<PII_PHONE_def456>>", "555-1234")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)

        # Encrypted output should be different from plaintext
        assert "john@example.com" not in encrypted
        assert "555-1234" not in encrypted
        # Should be base64-encoded ciphertext
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_from_encrypted_with_key(self) -> None:
        """Test importing table with real decryption."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        original = EncryptedLookupTable()
        original.store("<<PII_EMAIL_abc123>>", "john@example.com")
        original.store("<<PII_PHONE_def456>>", "555-1234")

        key = generate_encryption_key()
        encrypted = original.export_encrypted(key=key)
        restored = EncryptedLookupTable.from_encrypted(encrypted, key=key)

        assert restored.retrieve("<<PII_EMAIL_abc123>>") == "john@example.com"
        assert restored.retrieve("<<PII_PHONE_def456>>") == "555-1234"
        assert len(restored) == 2

    def test_encryption_uses_aes_gcm(self) -> None:
        """Test that encryption uses AES-GCM (authenticated encryption)."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_SSN_test>>", "123-45-6789")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)

        # The encrypted format should include nonce + ciphertext + tag
        # Decode the base64 to check structure
        import base64

        raw = base64.b64decode(encrypted)
        # AES-GCM: 12-byte nonce + ciphertext + 16-byte tag
        # Minimum size: 12 + 1 + 16 = 29 bytes
        assert len(raw) >= 29

    def test_encryption_is_non_deterministic(self) -> None:
        """Test that same data encrypts differently each time (nonce)."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_test>>", "test@example.com")

        key = generate_encryption_key()
        encrypted1 = table.export_encrypted(key=key)
        encrypted2 = table.export_encrypted(key=key)

        # Same data, same key, but different ciphertext due to random nonce
        assert encrypted1 != encrypted2

    def test_decryption_with_wrong_key_fails(self) -> None:
        """Test that decryption fails with incorrect key."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_test>>", "secret@example.com")

        correct_key = generate_encryption_key()
        wrong_key = generate_encryption_key()

        encrypted = table.export_encrypted(key=correct_key)

        with pytest.raises(Exception):  # InvalidTag or similar
            EncryptedLookupTable.from_encrypted(encrypted, key=wrong_key)

    def test_tampered_ciphertext_fails(self) -> None:
        """Test that authentication detects tampered ciphertext."""
        import base64

        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_test>>", "test@example.com")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)

        # Tamper with the ciphertext
        raw = bytearray(base64.b64decode(encrypted))
        raw[20] ^= 0xFF  # Flip bits in the middle
        tampered = base64.b64encode(bytes(raw)).decode("utf-8")

        with pytest.raises(Exception):  # InvalidTag
            EncryptedLookupTable.from_encrypted(tampered, key=key)


@pytest.mark.xdist_group(name="test_lookup_table_backward_compat")
class TestLookupTableBackwardCompatibility:
    """Tests for backward compatibility with legacy format."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_export_without_key_uses_legacy_format(self) -> None:
        """Test that export without key uses base64 encoding (legacy)."""
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_test>>", "test@example.com")

        # No key = legacy base64 encoding
        exported = table.export_encrypted()

        # Verify it's decodable as legacy format
        import base64

        decoded = base64.b64decode(exported).decode("utf-8")
        data = json.loads(decoded)
        assert data["<<PII_EMAIL_test>>"] == "test@example.com"

    def test_import_legacy_format(self) -> None:
        """Test importing legacy base64 format."""
        import base64

        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        # Create legacy format manually
        data = {"<<PII_EMAIL_legacy>>": "legacy@example.com"}
        legacy = base64.b64encode(json.dumps(data).encode()).decode()

        # Import without key
        table = EncryptedLookupTable.from_encrypted(legacy)
        assert table.retrieve("<<PII_EMAIL_legacy>>") == "legacy@example.com"

    def test_encrypted_format_not_importable_as_legacy(self) -> None:
        """Test that encrypted format is distinct from legacy."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_EMAIL_test>>", "test@example.com")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)

        # Trying to import encrypted data without key should fail
        # (it's not valid JSON when base64 decoded)
        with pytest.raises(Exception):
            EncryptedLookupTable.from_encrypted(encrypted)  # No key


@pytest.mark.xdist_group(name="test_lookup_table_edge_cases")
class TestLookupTableEncryptionEdgeCases:
    """Edge case tests for encryption."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_encrypt_empty_table(self) -> None:
        """Test encrypting an empty table."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        key = generate_encryption_key()

        encrypted = table.export_encrypted(key=key)
        restored = EncryptedLookupTable.from_encrypted(encrypted, key=key)

        assert len(restored) == 0
        assert restored.to_dict() == {}

    def test_encrypt_unicode_values(self) -> None:
        """Test encrypting unicode content."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_NAME_test>>", "日本語テスト")
        table.store("<<PII_EMAIL_emoji>>", "user+🎉@example.com")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)
        restored = EncryptedLookupTable.from_encrypted(encrypted, key=key)

        assert restored.retrieve("<<PII_NAME_test>>") == "日本語テスト"
        assert restored.retrieve("<<PII_EMAIL_emoji>>") == "user+🎉@example.com"

    def test_encrypt_large_table(self) -> None:
        """Test encrypting a table with many entries."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        for i in range(1000):
            table.store(f"<<PII_EMAIL_{i}>>", f"user{i}@example.com")

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)
        restored = EncryptedLookupTable.from_encrypted(encrypted, key=key)

        assert len(restored) == 1000
        assert restored.retrieve("<<PII_EMAIL_500>>") == "user500@example.com"

    def test_encrypt_special_characters(self) -> None:
        """Test encrypting values with special characters."""
        from mcp_server_langgraph.privacy.lookup_table import (
            EncryptedLookupTable,
            generate_encryption_key,
        )

        table = EncryptedLookupTable()
        table.store("<<PII_DATA_test>>", '{"key": "value", "special": "\n\t\r"}')
        table.store("<<PII_DATA_quotes>>", 'He said "hello"')

        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)
        restored = EncryptedLookupTable.from_encrypted(encrypted, key=key)

        assert restored.retrieve("<<PII_DATA_test>>") == '{"key": "value", "special": "\n\t\r"}'
        assert restored.retrieve("<<PII_DATA_quotes>>") == 'He said "hello"'
