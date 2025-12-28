"""
Unit tests for WebSocket Token Validation.

Tests token expiration checking functions used for periodic token validation
during active WebSocket connections.
"""

import gc
from datetime import UTC, datetime, timedelta

import jwt
import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_token_validation"),
]


@pytest.mark.xdist_group(name="websocket_token_validation")
class TestIsTokenExpired:
    """Tests for is_token_expired function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_token_expired_returns_true_for_expired_token(self) -> None:
        """GIVEN expired JWT WHEN checking expiration THEN returns True."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expired

        # Create token that expired 1 hour ago
        expired_time = datetime.now(UTC) - timedelta(hours=1)
        token = jwt.encode(
            {"exp": expired_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expired(token)

        assert result is True

    def test_is_token_expired_returns_false_for_valid_token(self) -> None:
        """GIVEN valid JWT WHEN checking expiration THEN returns False."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expired

        # Create token that expires in 1 hour
        future_time = datetime.now(UTC) + timedelta(hours=1)
        token = jwt.encode(
            {"exp": future_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expired(token)

        assert result is False

    def test_is_token_expired_returns_true_for_token_without_exp(self) -> None:
        """GIVEN JWT without exp claim WHEN checking expiration THEN returns True (fail-safe)."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expired

        # Create token without exp claim
        token = jwt.encode(
            {"sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expired(token)

        assert result is True

    def test_is_token_expired_returns_true_for_invalid_token(self) -> None:
        """GIVEN invalid JWT WHEN checking expiration THEN returns True (fail-safe)."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expired

        result = is_token_expired("not-a-valid-jwt-token")

        assert result is True


@pytest.mark.xdist_group(name="websocket_token_validation")
class TestIsTokenExpiringSoon:
    """Tests for is_token_expiring_soon function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_token_expiring_soon_returns_true_within_buffer(self) -> None:
        """GIVEN token expiring in 2 minutes WHEN checking with 5min buffer THEN returns True."""
        from mcp_server_langgraph.websocket.token_validation import (
            is_token_expiring_soon,
        )

        # Token expires in 2 minutes (within 5 minute buffer)
        exp_time = datetime.now(UTC) + timedelta(minutes=2)
        token = jwt.encode(
            {"exp": exp_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expiring_soon(token, buffer_seconds=300)

        assert result is True

    def test_is_token_expiring_soon_returns_false_outside_buffer(self) -> None:
        """GIVEN token expiring in 10 minutes WHEN checking with 5min buffer THEN returns False."""
        from mcp_server_langgraph.websocket.token_validation import (
            is_token_expiring_soon,
        )

        # Token expires in 10 minutes (outside 5 minute buffer)
        exp_time = datetime.now(UTC) + timedelta(minutes=10)
        token = jwt.encode(
            {"exp": exp_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expiring_soon(token, buffer_seconds=300)

        assert result is False

    def test_is_token_expiring_soon_returns_true_for_expired_token(self) -> None:
        """GIVEN already expired token WHEN checking expiring soon THEN returns True."""
        from mcp_server_langgraph.websocket.token_validation import (
            is_token_expiring_soon,
        )

        # Token already expired
        exp_time = datetime.now(UTC) - timedelta(minutes=5)
        token = jwt.encode(
            {"exp": exp_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expiring_soon(token, buffer_seconds=300)

        assert result is True

    def test_is_token_expiring_soon_uses_default_buffer(self) -> None:
        """GIVEN no buffer specified WHEN checking expiring soon THEN uses 300s default."""
        from mcp_server_langgraph.websocket.token_validation import (
            is_token_expiring_soon,
        )

        # Token expires in 4 minutes (within default 5 minute buffer)
        exp_time = datetime.now(UTC) + timedelta(minutes=4)
        token = jwt.encode(
            {"exp": exp_time, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = is_token_expiring_soon(token)  # Default 300 seconds

        assert result is True


@pytest.mark.xdist_group(name="websocket_token_validation")
class TestGetTokenExpiration:
    """Tests for get_token_expiration function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_token_expiration_extracts_exp_claim(self) -> None:
        """GIVEN JWT with exp claim WHEN getting expiration THEN returns datetime."""
        from mcp_server_langgraph.websocket.token_validation import (
            get_token_expiration,
        )

        exp_time = datetime.now(UTC) + timedelta(hours=1)
        # JWT exp is stored as Unix timestamp (integer seconds)
        exp_timestamp = int(exp_time.timestamp())
        token = jwt.encode(
            {"exp": exp_timestamp, "sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = get_token_expiration(token)

        assert result is not None
        # Compare timestamps (allow 1 second tolerance for rounding)
        assert abs(result.timestamp() - exp_timestamp) < 1

    def test_get_token_expiration_returns_none_for_no_exp(self) -> None:
        """GIVEN JWT without exp claim WHEN getting expiration THEN returns None."""
        from mcp_server_langgraph.websocket.token_validation import (
            get_token_expiration,
        )

        token = jwt.encode(
            {"sub": "test-user"},
            "secret",
            algorithm="HS256",
        )

        result = get_token_expiration(token)

        assert result is None

    def test_get_token_expiration_returns_none_for_invalid_token(self) -> None:
        """GIVEN invalid JWT WHEN getting expiration THEN returns None."""
        from mcp_server_langgraph.websocket.token_validation import (
            get_token_expiration,
        )

        result = get_token_expiration("invalid-token")

        assert result is None
