"""
Session Encryptor for encrypted at-rest session storage.

Provides AES-256-GCM authenticated encryption for session data with:
- Random nonce per encryption (prevents ciphertext analysis)
- Authentication tag (detects tampering)
- Key derivation from passwords using PBKDF2
- Support for key rotation

Usage:
    from mcp_server_langgraph.auth.session_encryptor import SessionEncryptor

    encryptor = SessionEncryptor(key=encryption_key)
    encrypted = encryptor.encrypt(plaintext_bytes)
    decrypted = encryptor.decrypt(encrypted)

Security Notes:
- Keys must be 32 bytes (256 bits) for AES-256
- Use derive_key() to generate keys from passwords
- Store keys securely (e.g., environment variables, secrets manager)
- Rotate keys periodically for compliance
"""

from __future__ import annotations

import os
import struct
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

if TYPE_CHECKING:
    pass


# =============================================================================
# Constants
# =============================================================================

# Nonce size for AES-GCM (96 bits recommended by NIST)
NONCE_SIZE = 12

# Key size for AES-256 (256 bits = 32 bytes)
KEY_SIZE = 32

# PBKDF2 iterations (OWASP recommends 600,000+ for PBKDF2-HMAC-SHA256)
PBKDF2_ITERATIONS = 600_000

# Salt size for key derivation
SALT_SIZE = 16


# =============================================================================
# Exceptions
# =============================================================================


class EncryptionError(Exception):
    """Raised when encryption fails."""

    pass


class DecryptionError(Exception):
    """Raised when decryption fails (wrong key, corrupted data, tampering)."""

    pass


class KeyDerivationError(Exception):
    """Raised when key derivation fails."""

    pass


# =============================================================================
# Key Derivation
# =============================================================================


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from a password using PBKDF2.

    Uses PBKDF2-HMAC-SHA256 with 600,000 iterations as recommended by OWASP.

    Args:
        password: The password to derive the key from
        salt: A unique salt value (must be stored with encrypted data)

    Returns:
        A 32-byte (256-bit) encryption key

    Raises:
        KeyDerivationError: If key derivation fails
    """
    if not password:
        raise KeyDerivationError("Password cannot be empty")

    if not salt or len(salt) < SALT_SIZE:
        raise KeyDerivationError(f"Salt must be at least {SALT_SIZE} bytes")

    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))
    except Exception as e:
        raise KeyDerivationError(f"Key derivation failed: {e}") from e


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt.

    Returns:
        A 16-byte random salt
    """
    return os.urandom(SALT_SIZE)


# =============================================================================
# Session Encryptor
# =============================================================================


class SessionEncryptor:
    """AES-256-GCM encryptor for session data.

    Provides authenticated encryption with automatic nonce generation.
    Each encryption produces a unique ciphertext even for identical plaintext.

    Format of encrypted data:
        [4-byte nonce length][nonce][ciphertext with auth tag]

    Attributes:
        key: The 256-bit encryption key
    """

    def __init__(self, key: bytes) -> None:
        """Initialize the encryptor with an encryption key.

        Args:
            key: A 32-byte (256-bit) encryption key

        Raises:
            ValueError: If key is not 32 bytes
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")

        self._key = key
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext data using AES-256-GCM.

        Generates a random nonce for each encryption, ensuring that
        identical plaintexts produce different ciphertexts.

        Args:
            plaintext: The data to encrypt

        Returns:
            Encrypted data with prepended nonce

        Raises:
            EncryptionError: If encryption fails
        """
        if not isinstance(plaintext, bytes):
            raise EncryptionError("Plaintext must be bytes")

        try:
            # Generate random nonce for each encryption
            nonce = os.urandom(NONCE_SIZE)

            # Encrypt with authentication
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data=None)

            # Pack: [nonce_length (4 bytes)][nonce][ciphertext]
            packed = struct.pack(">I", len(nonce)) + nonce + ciphertext

            return packed

        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, encrypted: bytes) -> bytes:
        """Decrypt data that was encrypted with encrypt().

        Args:
            encrypted: The encrypted data (including nonce)

        Returns:
            The original plaintext

        Raises:
            DecryptionError: If decryption fails (wrong key, tampering, corruption)
        """
        if not isinstance(encrypted, bytes):
            raise DecryptionError("Encrypted data must be bytes")

        if len(encrypted) < 4 + NONCE_SIZE:
            raise DecryptionError("Encrypted data too short")

        try:
            # Unpack: [nonce_length (4 bytes)][nonce][ciphertext]
            nonce_length = struct.unpack(">I", encrypted[:4])[0]

            if nonce_length != NONCE_SIZE:
                raise DecryptionError(f"Invalid nonce length: {nonce_length}")

            nonce = encrypted[4 : 4 + nonce_length]
            ciphertext = encrypted[4 + nonce_length :]

            # Decrypt and verify authentication tag
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, associated_data=None)

            return plaintext

        except DecryptionError:
            raise
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}") from e


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DecryptionError",
    "EncryptionError",
    "KEY_SIZE",
    "KeyDerivationError",
    "NONCE_SIZE",
    "PBKDF2_ITERATIONS",
    "SALT_SIZE",
    "SessionEncryptor",
    "derive_key",
    "generate_salt",
]
