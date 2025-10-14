"""
Tests for session timeout middleware (HIPAA 164.312(a)(2)(iii))

Tests automatic logoff after period of inactivity.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from starlette.responses import JSONResponse

from mcp_server_langgraph.auth.session import InMemorySessionStore, SessionData
from mcp_server_langgraph.middleware.session_timeout import (
    SessionTimeoutMiddleware,
    create_session_timeout_middleware,
)


@pytest.fixture
def mock_session_store():
    """Create mock session store"""
    # Disable sliding_window since the middleware handles it
    return InMemorySessionStore(sliding_window=False)


@pytest.fixture
def app():
    """Create test FastAPI app"""
    return FastAPI()


@pytest.fixture
def sample_session():
    """Create sample session data factory"""

    async def _create_session(store):
        # Create session using the store's create method
        session_id = await store.create(
            user_id="user:test",
            username="testuser",
            roles=["user"],
            metadata={},
        )
        # Return the created session
        return await store.get(session_id)

    return _create_session


@pytest.mark.unit
class TestSessionTimeoutMiddleware:
    """Test SessionTimeoutMiddleware functionality"""

    @pytest.mark.asyncio
    async def test_middleware_initialization(self, app, mock_session_store):
        """Test middleware initialization"""
        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=900, session_store=mock_session_store)

        assert middleware.timeout_seconds == 900
        assert middleware.session_store == mock_session_store

    @pytest.mark.asyncio
    async def test_middleware_with_default_timeout(self, app):
        """Test middleware with default 15-minute timeout"""
        middleware = SessionTimeoutMiddleware(app=app)

        assert middleware.timeout_seconds == 900  # 15 minutes

    @pytest.mark.asyncio
    async def test_public_endpoint_bypasses_timeout(self, app, mock_session_store):
        """Test that public endpoints bypass timeout check"""
        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=60, session_store=mock_session_store)

        # Mock request to public endpoint
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health"

        # Mock call_next
        async def mock_call_next(request):
            return Response(status_code=200, content="OK")

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_without_session_continues(self, app, mock_session_store):
        """Test that requests without session continue normally"""
        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=60, session_store=mock_session_store)

        # Mock request without session
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = None

        # Mock call_next
        async def mock_call_next(request):
            return Response(status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_active_session_continues(self, app, mock_session_store, sample_session):
        """Test that active session (within timeout) continues"""
        # Create session
        session = await sample_session(mock_session_store)

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=900, session_store=mock_session_store)

        # Mock request with session
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session.session_id

        # Mock call_next
        async def mock_call_next(request):
            return Response(status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inactive_session_times_out(self, app, mock_session_store):
        """Test that inactive session (beyond timeout) is terminated"""
        # Create session and manually set old last_accessed time
        session_id = await mock_session_store.create(
            user_id="user:inactive",
            username="inactive",
            roles=["user"],
            metadata={},
        )

        # Manually update the last_accessed to make it old
        old_session = await mock_session_store.get(session_id)
        old_session.last_accessed = (datetime.utcnow() - timedelta(minutes=20)).isoformat() + "Z"
        mock_session_store.sessions[session_id] = old_session

        middleware = SessionTimeoutMiddleware(
            app=app, timeout_seconds=600, session_store=mock_session_store  # 10 minute timeout
        )

        # Mock request with old session
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session_id
        mock_request.client.host = "192.168.1.100"

        # Mock call_next (should not be called)
        async def mock_call_next(request):
            return Response(status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401 Unauthorized
        assert response.status_code == 401

        # Verify session was deleted
        deleted_session = await mock_session_store.get(session_id)
        assert deleted_session is None

    @pytest.mark.asyncio
    async def test_sliding_window_updates_last_accessed(self, app, mock_session_store, sample_session):
        """Test that session activity updates last_accessed (sliding window)"""
        # Create session
        session = await sample_session(mock_session_store)
        original_last_accessed = session.last_accessed

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=900, session_store=mock_session_store)

        # Mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session.session_id

        async def mock_call_next(request):
            return Response(status_code=200)

        # Make request
        await middleware.dispatch(mock_request, mock_call_next)

        # Check that last_accessed was updated
        updated_session = await mock_session_store.get(session.session_id)
        assert updated_session.last_accessed != original_last_accessed

    @pytest.mark.asyncio
    async def test_timeout_response_format(self, app, mock_session_store):
        """Test timeout response has proper format"""
        # Create session and make it old
        session_id = await mock_session_store.create(
            user_id="user:test",
            username="test",
            roles=[],
            metadata={},
        )

        # Update last_accessed to make it old
        old_session = await mock_session_store.get(session_id)
        old_session.last_accessed = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
        mock_session_store.sessions[session_id] = old_session

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=300, session_store=mock_session_store)  # 5 minutes

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session_id
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            return Response(status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        # JSONResponse should have proper content
        assert hasattr(response, "body")


@pytest.mark.unit
class TestSessionTimeoutHelpers:
    """Test helper methods"""

    def test_get_session_id_from_cookie(self, app, mock_session_store):
        """Test extracting session ID from cookie"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = "session-from-cookie"

        session_id = middleware._get_session_id(mock_request)

        assert session_id == "session-from-cookie"

    def test_get_session_id_from_state(self, app, mock_session_store):
        """Test extracting session ID from request state"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = None
        mock_request.state.session_id = "session-from-state"

        session_id = middleware._get_session_id(mock_request)

        assert session_id == "session-from-state"

    def test_get_session_id_none(self, app, mock_session_store):
        """Test when no session ID is found"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = None
        # No state.session_id

        # Delete the session_id attribute if it exists
        if hasattr(mock_request.state, "session_id"):
            delattr(mock_request.state, "session_id")

        session_id = middleware._get_session_id(mock_request)

        assert session_id is None

    def test_is_public_endpoint_health(self, app, mock_session_store):
        """Test /health is recognized as public"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        assert middleware._is_public_endpoint("/health") is True

    def test_is_public_endpoint_metrics(self, app, mock_session_store):
        """Test /metrics is recognized as public"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        assert middleware._is_public_endpoint("/metrics") is True

    def test_is_public_endpoint_login(self, app, mock_session_store):
        """Test /api/v1/auth/login is recognized as public"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        assert middleware._is_public_endpoint("/api/v1/auth/login") is True

    def test_is_public_endpoint_docs(self, app, mock_session_store):
        """Test /docs is recognized as public"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        assert middleware._is_public_endpoint("/docs") is True

    def test_is_public_endpoint_private(self, app, mock_session_store):
        """Test private endpoints are not public"""
        middleware = SessionTimeoutMiddleware(app=app, session_store=mock_session_store)

        assert middleware._is_public_endpoint("/api/private/data") is False
        assert middleware._is_public_endpoint("/api/v1/users") is False


@pytest.mark.unit
class TestCreateSessionTimeoutMiddleware:
    """Test middleware factory function"""

    def test_create_middleware_with_minutes(self, app, mock_session_store):
        """Test creating middleware with timeout in minutes"""
        middleware = create_session_timeout_middleware(app=app, timeout_minutes=30, session_store=mock_session_store)

        assert middleware.timeout_seconds == 1800  # 30 minutes * 60

    def test_create_middleware_default_timeout(self, app):
        """Test creating middleware with default timeout"""
        middleware = create_session_timeout_middleware(app=app)

        assert middleware.timeout_seconds == 900  # 15 minutes * 60


@pytest.mark.unit
class TestSessionTimeoutEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_session_not_found_continues(self, app, mock_session_store):
        """Test that missing session (deleted/expired) continues normally"""
        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=900, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = "nonexistent-session"

        async def mock_call_next(request):
            return Response(status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should continue (fail open)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_store_error_continues(self, app):
        """Test that session store errors don't break requests"""
        # Create mock store that raises exception
        mock_store = AsyncMock()
        mock_store.get.side_effect = Exception("Database connection error")

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=900, session_store=mock_store)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = "test-session"

        async def mock_call_next(request):
            return Response(status_code=200)

        # Should continue despite error (fail open for availability)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_timeout_values(self, app, mock_session_store):
        """Test various timeout values"""
        # Very short timeout
        middleware1 = SessionTimeoutMiddleware(app=app, timeout_seconds=60, session_store=mock_session_store)  # 1 minute
        assert middleware1.timeout_seconds == 60

        # Long timeout
        middleware2 = SessionTimeoutMiddleware(app=app, timeout_seconds=3600, session_store=mock_session_store)  # 1 hour
        assert middleware2.timeout_seconds == 3600

    @pytest.mark.asyncio
    async def test_request_without_client_info(self, app, mock_session_store):
        """Test handling request without client information"""
        # Create session and make it old
        session_id = await mock_session_store.create(
            user_id="user:test",
            username="test",
            roles=[],
            metadata={},
        )

        # Update last_accessed to make it old
        old_session = await mock_session_store.get(session_id)
        old_session.last_accessed = (datetime.utcnow() - timedelta(minutes=20)).isoformat() + "Z"
        mock_session_store.sessions[session_id] = old_session

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=300, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session_id
        mock_request.client = None  # No client info

        async def mock_call_next(request):
            return Response(status_code=200)

        # Should handle gracefully
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401  # Still timeout


@pytest.mark.unit
class TestHIPAACompliance:
    """Test HIPAA compliance aspects"""

    @pytest.mark.asyncio
    async def test_logs_timeout_events(self, app, mock_session_store):
        """Test that timeout events are logged (audit requirement)"""
        # Create session and make it old
        session_id = await mock_session_store.create(
            user_id="user:test",
            username="test",
            roles=[],
            metadata={},
        )

        # Update last_accessed to make it old
        old_session = await mock_session_store.get(session_id)
        old_session.last_accessed = (datetime.utcnow() - timedelta(minutes=20)).isoformat() + "Z"
        mock_session_store.sessions[session_id] = old_session

        middleware = SessionTimeoutMiddleware(app=app, timeout_seconds=300, session_store=mock_session_store)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/phi/patient/123"
        mock_request.headers.get.return_value = ""
        mock_request.cookies.get.return_value = session_id
        mock_request.client.host = "192.168.1.50"

        async def mock_call_next(request):
            return Response(status_code=200)

        with patch("mcp_server_langgraph.middleware.session_timeout.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            # Verify warning was logged
            mock_logger.warning.assert_called()

    def test_default_timeout_meets_hipaa(self, app):
        """Test that default timeout meets HIPAA recommendation (15 minutes)"""
        middleware = SessionTimeoutMiddleware(app=app)

        # HIPAA recommends 15 minutes or less
        assert middleware.timeout_seconds <= 900
        assert middleware.timeout_seconds == 900  # Exactly 15 minutes
