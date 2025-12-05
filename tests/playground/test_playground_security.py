"""
Playground Security Tests (TDD Red Phase)

Tests for authentication and authorization in the Interactive Playground.
Following TDD: These tests are written BEFORE the implementation.

Test Coverage:
- JWT token validation
- User isolation (users can only access their own sessions)
- Rate limiting
- Input validation
"""

import gc
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

# Mark all tests in this module for xdist memory safety
pytestmark = [
    pytest.mark.unit,
    pytest.mark.playground,
    pytest.mark.security,
    pytest.mark.xdist_group(name="playground_security"),
]

# Fixtures are provided by conftest.py:
# - mock_redis
# - mock_session_manager
# - app_with_mock_manager


class TestJWTAuthentication:
    """Tests for JWT token authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_valid_jwt_token_allows_access(self, app_with_mock_manager) -> None:
        """Valid JWT token should allow access to protected endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                "/api/playground/sessions",
                headers={"Authorization": "Bearer valid-test-token"},
            )

        # Should not be 401
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_expired_jwt_token_returns_401(self, app_with_mock_manager) -> None:
        """Expired JWT token should return 401 Unauthorized."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                "/api/playground/sessions",
                headers={"Authorization": "Bearer expired-token"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_malformed_jwt_token_returns_401(self, app_with_mock_manager) -> None:
        """Malformed JWT token should return 401 Unauthorized."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                "/api/playground/sessions",
                headers={"Authorization": "Bearer not.a.valid.jwt"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_missing_authorization_header_returns_401(self, app_with_mock_manager) -> None:
        """Missing Authorization header should return 401."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get("/api/playground/sessions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserIsolation:
    """Tests for user session isolation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_session(self, mock_session_manager, app_with_mock_manager) -> None:
        """Users should not be able to access sessions belonging to other users."""
        from mcp_server_langgraph.playground.session.manager import Session
        from datetime import datetime, timedelta, UTC

        # Mock session owned by different user
        other_session = Session(
            id="session-owned-by-user-456",
            user_id="user-456",  # Different user
            name="Other User Session",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            message_count=0,
        )
        mock_session_manager.get_session = AsyncMock(return_value=other_session)

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            # Try to access with user-123's token
            response = await client.get(
                "/api/playground/sessions/session-owned-by-user-456",
                headers={"Authorization": "Bearer token-for-user-123"},
            )

        # Should be forbidden or not found
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_session(self, mock_session_manager, app_with_mock_manager) -> None:
        """Users should not be able to delete sessions belonging to other users."""
        from mcp_server_langgraph.playground.session.manager import Session
        from datetime import datetime, timedelta, UTC

        # Mock session owned by different user
        other_session = Session(
            id="session-owned-by-user-456",
            user_id="user-456",  # Different user
            name="Other User Session",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            message_count=0,
        )
        mock_session_manager.get_session = AsyncMock(return_value=other_session)

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.delete(
                "/api/playground/sessions/session-owned-by-user-456",
                headers={"Authorization": "Bearer token-for-user-123"},
            )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestInputValidation:
    """Tests for input validation and sanitization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_name_length_validation(self, app_with_mock_manager) -> None:
        """Session names should have maximum length validation."""
        # 1000 character name should be rejected
        long_name = "x" * 1000

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/sessions",
                json={"name": long_name},
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="XSS sanitization not yet implemented - placeholder for future")
    async def test_message_content_sanitization(self, app_with_mock_manager) -> None:
        """Message content should be sanitized (no script injection)."""
        malicious_content = "<script>alert('xss')</script>"

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/chat",
                json={
                    "session_id": "test-session-123",
                    "message": malicious_content,
                },
                headers={"Authorization": "Bearer test-token"},
            )

        # Should accept but sanitize, or reject
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # If accepted, content should be sanitized
            assert "<script>" not in str(data)

    @pytest.mark.asyncio
    async def test_session_id_path_traversal_prevention(self, app_with_mock_manager) -> None:
        """Session IDs should not allow path traversal."""
        malicious_id = "../../../etc/passwd"

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                f"/api/playground/sessions/{malicious_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        # Should be rejected or not found (not a server error)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Rate limiting not yet implemented - placeholder for future")
    async def test_excessive_requests_are_rate_limited(self, app_with_mock_manager) -> None:
        """Excessive requests should be rate limited."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            # Make many requests rapidly
            responses = []
            for _ in range(100):
                response = await client.post(
                    "/api/playground/chat",
                    json={
                        "session_id": "test-session-123",
                        "message": "Hello!",
                    },
                    headers={"Authorization": "Bearer test-token"},
                )
                responses.append(response.status_code)

        # At least some should be rate limited (429)
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses


class TestCORS:
    """Tests for CORS configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origins(self, app_with_mock_manager) -> None:
        """CORS should allow requests from configured origins."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.options(
                "/api/playground/sessions",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_blocks_unauthorized_origins(self, app_with_mock_manager) -> None:
        """CORS should block requests from unauthorized origins."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.options(
                "/api/playground/sessions",
                headers={
                    "Origin": "http://malicious-site.com",
                    "Access-Control-Request-Method": "GET",
                },
            )

        # Should not include the malicious origin in allowed origins
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert "malicious-site.com" not in allow_origin
