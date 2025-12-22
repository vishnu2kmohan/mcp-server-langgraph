"""
Encrypted Lookup Table for PII Storage

Provides secure storage for PII mappings during tokenization/untokenization.
The lookup table can be encrypted for safe transmission between services.

Usage:
    from mcp_server_langgraph.privacy.lookup_table import (
        EncryptedLookupTable,
        generate_encryption_key,
    )

    table = EncryptedLookupTable()
    table.store("<<PII_EMAIL_abc123>>", "john@example.com")
    value = table.retrieve("<<PII_EMAIL_abc123>>")

    # Export with real encryption (production)
    key = generate_encryption_key()
    encrypted = table.export_encrypted(key=key)

    # Import on receiving end
    table2 = EncryptedLookupTable.from_encrypted(encrypted, key=key)

    # Legacy mode (no encryption, for backward compatibility)
    legacy_export = table.export_encrypted()  # No key = base64 only
"""

from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def generate_encryption_key() -> bytes:
    """Generate a secure random encryption key for AES-256.

    Returns:
        32 bytes (256 bits) of cryptographically secure random data.

    Example:
        key = generate_encryption_key()
        encrypted = table.export_encrypted(key=key)
    """
    return secrets.token_bytes(32)


def key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """Derive an encryption key from a passphrase using PBKDF2.

    Uses PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2023 recommendation).

    Args:
        passphrase: User-provided passphrase
        salt: Random salt (should be stored with ciphertext)

    Returns:
        32-byte derived key suitable for AES-256

    Example:
        salt = secrets.token_bytes(16)
        key = key_from_passphrase("my-passphrase", salt)
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,  # OWASP 2023 recommendation
    )
    return kdf.derive(passphrase.encode("utf-8"))


class EncryptedLookupTable:
    """Secure storage for PII token-to-value mappings.

    Supports encryption for safe transmission between services.
    In production, use proper key management (e.g., AWS KMS, Vault).
    """

    def __init__(self) -> None:
        """Initialize an empty lookup table."""
        self._data: dict[str, str] = {}

    def store(self, token: str, value: str) -> None:
        """Store a token-to-value mapping.

        Args:
            token: The PII token (e.g., <<PII_EMAIL_abc123>>)
            value: The original PII value
        """
        self._data[token] = value

    def retrieve(self, token: str) -> str | None:
        """Retrieve the original value for a token.

        Args:
            token: The PII token to look up

        Returns:
            Original value if found, None otherwise
        """
        return self._data.get(token)

    def to_dict(self) -> dict[str, str]:
        """Convert to plain dictionary.

        Returns:
            Copy of the internal data dictionary
        """
        return self._data.copy()

    def export_encrypted(self, key: bytes | None = None) -> str:
        """Export the lookup table in an encrypted format.

        When a key is provided, uses AES-256-GCM authenticated encryption.
        Without a key, falls back to legacy base64 encoding for compatibility.

        Args:
            key: 32-byte encryption key from generate_encryption_key() or
                 key_from_passphrase(). If None, uses legacy base64 mode.

        Returns:
            Encrypted string representation of the lookup table.
            With encryption: base64(nonce || ciphertext || tag)
            Without: base64(json)

        Example:
            # With encryption (production)
            key = generate_encryption_key()
            encrypted = table.export_encrypted(key=key)

            # Without encryption (legacy/testing)
            legacy = table.export_encrypted()
        """
        json_str = json.dumps(self._data)

        if key is None:
            # Legacy mode: base64 encoding only (backward compatible)
            return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

        # Production mode: AES-256-GCM authenticated encryption
        # Generate random 12-byte nonce (recommended for GCM)
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)

        # Encrypt and authenticate
        ciphertext = aesgcm.encrypt(nonce, json_str.encode("utf-8"), None)

        # Combine nonce + ciphertext (tag is appended by AESGCM)
        encrypted_data = nonce + ciphertext

        return base64.b64encode(encrypted_data).decode("utf-8")

    @classmethod
    def from_encrypted(
        cls, encrypted: str, key: bytes | None = None
    ) -> EncryptedLookupTable:
        """Create a lookup table from an encrypted export.

        Args:
            encrypted: Encrypted string from export_encrypted()
            key: 32-byte decryption key. Required if data was encrypted
                 with a key. If None, assumes legacy base64 format.

        Returns:
            New EncryptedLookupTable with restored data

        Raises:
            cryptography.exceptions.InvalidTag: If decryption fails
                (wrong key or tampered data)
            json.JSONDecodeError: If legacy format data is corrupted

        Example:
            # With encryption
            table = EncryptedLookupTable.from_encrypted(encrypted, key=key)

            # Legacy format
            table = EncryptedLookupTable.from_encrypted(legacy_data)
        """
        raw_data = base64.b64decode(encrypted.encode("utf-8"))

        if key is None:
            # Legacy mode: assume it's just JSON
            decoded = raw_data.decode("utf-8")
            data: dict[str, Any] = json.loads(decoded)
        else:
            # Production mode: AES-256-GCM decryption
            # Extract nonce (first 12 bytes) and ciphertext (rest)
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]

            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            data = json.loads(decrypted.decode("utf-8"))

        table = cls()
        table._data = data
        return table

    def __len__(self) -> int:
        """Return number of entries in the table."""
        return len(self._data)

    def clear(self) -> None:
        """Clear all entries from the table."""
        self._data.clear()

    def remove(self, token: str) -> bool:
        """Remove a specific token from the table.

        Supports GDPR Article 17 right to erasure by allowing
        removal of individual PII mappings.

        Args:
            token: The PII token to remove

        Returns:
            True if token was found and removed, False otherwise
        """
        if token in self._data:
            del self._data[token]
            return True
        return False
