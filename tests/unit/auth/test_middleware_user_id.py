"""Tests for UserContextMiddleware user_id extraction hardening.

TDD: Tests written FIRST to define behavior when JWT is valid but
user_id extraction fails.

RC2 Fix (Part B): Middleware should log a warning when user_id extraction
produces an empty/None value from a valid JWT, making the issue visible
without silently propagating empty strings.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from mcp_server_langgraph.middleware.user_context import UserContextMiddleware

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="test_middleware_user_id"),
]


def _make_request(user: dict | None = None) -> Request:
    """Create a mock request with optional user state."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope)
    if user is not None:
        request.state.user = user
    return request


class TestUserContextMiddlewareUserIdExtraction:
    """Tests for _extract_user_id hardening in UserContextMiddleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_user_id_from_sub(self) -> None:
        """GIVEN a request with user dict containing 'sub'
        WHEN _extract_user_id is called
        THEN it returns the 'sub' value
        """
        app = MagicMock()
        middleware = UserContextMiddleware(app)
        request = _make_request(user={"sub": "alice", "user_id": "alice"})

        result = middleware._extract_user_id(request)

        assert result == "alice"

    def test_extract_user_id_from_user_id_key(self) -> None:
        """GIVEN a request with user dict containing only 'user_id'
        WHEN _extract_user_id is called
        THEN it returns the 'user_id' value
        """
        app = MagicMock()
        middleware = UserContextMiddleware(app)
        request = _make_request(user={"user_id": "bob"})

        result = middleware._extract_user_id(request)

        assert result == "bob"

    def test_extract_user_id_returns_none_when_no_user(self) -> None:
        """GIVEN a request with no user state
        WHEN _extract_user_id is called
        THEN it returns None
        """
        app = MagicMock()
        middleware = UserContextMiddleware(app)
        request = _make_request(user=None)

        result = middleware._extract_user_id(request)

        assert result is None

    def test_extract_user_id_logs_warning_when_user_dict_has_no_id_fields(
        self,
    ) -> None:
        """GIVEN a request with user dict but no sub/user_id/id fields
        WHEN _extract_user_id is called
        THEN it logs a warning and returns None
        """
        app = MagicMock()
        middleware = UserContextMiddleware(app)
        # User dict exists but has no identifiable user ID fields
        request = _make_request(user={"email": "alice@example.com", "roles": ["admin"]})

        with patch("mcp_server_langgraph.middleware.user_context.logger") as mock_logger:
            result = middleware._extract_user_id(request)

        assert result is None
        mock_logger.warning.assert_called_once()
        warning_msg = str(mock_logger.warning.call_args)
        assert "user_id" in warning_msg.lower() or "extract" in warning_msg.lower()

    def test_extract_user_id_logs_warning_when_all_id_fields_empty(self) -> None:
        """GIVEN a request with user dict where sub/user_id/id are all empty strings
        WHEN _extract_user_id is called
        THEN it logs a warning and returns None (not empty string)
        """
        app = MagicMock()
        middleware = UserContextMiddleware(app)
        request = _make_request(user={"sub": "", "user_id": "", "id": ""})

        with patch("mcp_server_langgraph.middleware.user_context.logger") as mock_logger:
            result = middleware._extract_user_id(request)

        # Should return None, not empty string, to prevent contextvar from being
        # set to empty which causes downstream history loss
        assert result is None
        mock_logger.warning.assert_called_once()
