"""
Tests for Encrypted Session Lifecycle Integration.

TDD tests for wiring EncryptedSessionStore to application startup/shutdown.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestEncryptedSessionLifecycle:
    """Tests for encrypted session lifecycle management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_session_store_returns_store(self) -> None:
        """Test get_session_store returns a session store instance."""
        from mcp_server_langgraph.auth.session import get_session_store

        store = get_session_store()
        assert store is not None

    def test_encrypted_session_enabled_returns_encrypted_store(self) -> None:
        """Test encrypted sessions feature flag returns EncryptedSessionStore."""
        from mcp_server_langgraph.auth.session import get_session_store_for_flags
        from mcp_server_langgraph.auth.encrypted_session_store import EncryptedSessionStore

        with patch("mcp_server_langgraph.auth.session.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_encrypted_sessions=True)

            with patch.dict(
                "os.environ",
                {"SESSION_ENCRYPTION_KEY": "A" * 64},  # 32 bytes hex = 64 chars
            ):
                store = get_session_store_for_flags()
                assert isinstance(store, EncryptedSessionStore)

    def test_encrypted_session_disabled_returns_regular_store(self) -> None:
        """Test disabled flag returns regular SessionStore."""
        from mcp_server_langgraph.auth.session import get_session_store_for_flags, InMemorySessionStore

        with patch("mcp_server_langgraph.auth.session.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_encrypted_sessions=False)

            store = get_session_store_for_flags()
            assert isinstance(store, InMemorySessionStore)


class TestEncryptedSessionSettings:
    """Tests for encrypted session settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_session_encryption_key(self) -> None:
        """Test Settings has session_encryption_key."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert hasattr(settings, "session_encryption_key")

    def test_default_encryption_key_is_none(self) -> None:
        """Test default encryption key is None (must be configured)."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert settings.session_encryption_key is None

    def test_encryption_key_must_be_32_bytes_hex(self) -> None:
        """Test encryption key validation (64 hex chars = 32 bytes)."""
        from mcp_server_langgraph.auth.session import validate_encryption_key

        # Valid key (64 hex chars)
        valid_key = "A" * 64
        assert validate_encryption_key(valid_key) is True

        # Invalid key (too short)
        short_key = "A" * 32
        assert validate_encryption_key(short_key) is False


class TestEncryptedSessionEnvironment:
    """Tests for encrypted session environment configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_missing_encryption_key_logs_warning(self) -> None:
        """Test missing encryption key logs warning when feature enabled."""
        from mcp_server_langgraph.auth.session import check_encryption_config

        with patch("mcp_server_langgraph.auth.session.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_encrypted_sessions=True)

            with patch.dict("os.environ", {}, clear=False):
                # Remove the key if present
                import os

                os.environ.pop("SESSION_ENCRYPTION_KEY", None)

                result = check_encryption_config()
                assert result["enabled"] is True
                assert result["configured"] is False
                assert "warning" in result

    def test_encryption_key_from_env_variable(self) -> None:
        """Test encryption key can be read from environment variable."""
        from mcp_server_langgraph.auth.session import get_encryption_key_from_env

        test_key = "B" * 64  # 32 bytes in hex
        with patch.dict("os.environ", {"SESSION_ENCRYPTION_KEY": test_key}):
            key = get_encryption_key_from_env()
            assert key is not None
            assert len(key) == 32  # bytes
