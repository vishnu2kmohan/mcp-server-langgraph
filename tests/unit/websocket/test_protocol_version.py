"""
Tests for WebSocket Protocol Version Validation Functions.

TDD tests for extract_protocol_version, is_version_compatible, and
validate_protocol_version functions.
"""

import gc

import pytest

from mcp_server_langgraph.websocket.protocols import (
    PROTOCOL_VERSION,
    extract_protocol_version,
    is_version_compatible,
    validate_protocol_version,
)

# Module-level pytest marker for test categorization
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="websocket_protocol_version")
class TestExtractProtocolVersion:
    """Test extract_protocol_version function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_valid_version(self) -> None:
        """Should extract components from valid semver string."""
        result = extract_protocol_version("1.0.0")
        assert result == (1, 0, 0)

    def test_extract_version_with_different_numbers(self) -> None:
        """Should extract correct components for various versions."""
        assert extract_protocol_version("2.1.3") == (2, 1, 3)
        assert extract_protocol_version("10.20.30") == (10, 20, 30)
        assert extract_protocol_version("0.0.1") == (0, 0, 1)

    def test_extract_none_returns_none(self) -> None:
        """Should return None for None input."""
        assert extract_protocol_version(None) is None

    def test_extract_empty_string_returns_none(self) -> None:
        """Should return None for empty string."""
        assert extract_protocol_version("") is None

    def test_extract_invalid_format_returns_none(self) -> None:
        """Should return None for invalid formats."""
        assert extract_protocol_version("1.0") is None  # Missing patch
        assert extract_protocol_version("1") is None  # Only major
        assert extract_protocol_version("1.0.0.0") is None  # Too many parts
        assert extract_protocol_version("v1.0.0") is None  # Prefix
        assert extract_protocol_version("1.0.0-beta") is None  # Pre-release

    def test_extract_non_numeric_returns_none(self) -> None:
        """Should return None for non-numeric components."""
        assert extract_protocol_version("a.b.c") is None
        assert extract_protocol_version("1.x.0") is None


@pytest.mark.xdist_group(name="websocket_protocol_version")
class TestIsVersionCompatible:
    """Test is_version_compatible function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_same_version_is_compatible(self) -> None:
        """Same version should be compatible."""
        assert is_version_compatible("1.0.0", "1.0.0") is True

    def test_different_major_version_not_compatible(self) -> None:
        """Different major versions should NOT be compatible."""
        assert is_version_compatible("2.0.0", "1.0.0") is False
        assert is_version_compatible("1.0.0", "2.0.0") is False

    def test_client_lower_minor_is_compatible(self) -> None:
        """Client with lower minor version should be compatible."""
        assert is_version_compatible("1.0.0", "1.1.0") is True
        assert is_version_compatible("1.0.0", "1.5.0") is True

    def test_client_higher_minor_not_compatible(self) -> None:
        """Client with higher minor version should NOT be compatible."""
        assert is_version_compatible("1.2.0", "1.1.0") is False
        assert is_version_compatible("1.5.0", "1.0.0") is False

    def test_patch_version_doesnt_affect_compatibility(self) -> None:
        """Patch version differences should not affect compatibility."""
        assert is_version_compatible("1.0.0", "1.0.5") is True
        assert is_version_compatible("1.0.5", "1.0.0") is True
        assert is_version_compatible("1.0.99", "1.0.1") is True

    def test_none_client_version_not_compatible(self) -> None:
        """None client version should NOT be compatible."""
        assert is_version_compatible(None, "1.0.0") is False

    def test_invalid_version_not_compatible(self) -> None:
        """Invalid version strings should NOT be compatible."""
        assert is_version_compatible("invalid", "1.0.0") is False
        assert is_version_compatible("1.0.0", "invalid") is False

    def test_default_server_version(self) -> None:
        """Should use PROTOCOL_VERSION as default server version."""
        assert is_version_compatible("1.0.0") is True


@pytest.mark.xdist_group(name="websocket_protocol_version")
class TestValidateProtocolVersion:
    """Test validate_protocol_version function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_valid_version_returns_true(self) -> None:
        """Valid compatible version should return (True, '')."""
        is_valid, error = validate_protocol_version("1.0.0")
        assert is_valid is True
        assert error == ""

    def test_none_version_returns_error(self) -> None:
        """None version should return (False, error_message)."""
        is_valid, error = validate_protocol_version(None)
        assert is_valid is False
        assert "Missing protocol version" in error
        assert "?v=1.0.0" in error

    def test_invalid_format_returns_error(self) -> None:
        """Invalid format should return (False, error_message)."""
        is_valid, error = validate_protocol_version("invalid")
        assert is_valid is False
        assert "Invalid protocol version format" in error

    def test_incompatible_version_returns_error(self) -> None:
        """Incompatible version should return (False, error_message)."""
        is_valid, error = validate_protocol_version("2.0.0")
        assert is_valid is False
        assert "Protocol version mismatch" in error
        assert "Client: 2.0.0" in error
        assert f"Server: {PROTOCOL_VERSION}" in error

    def test_compatible_older_minor_returns_true(self) -> None:
        """Older minor version should be valid (backwards compatible)."""
        is_valid, error = validate_protocol_version("1.0.0")
        assert is_valid is True
