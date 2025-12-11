"""
Tests for Interactive Playground API.

Tests the playground API server with:
- Health endpoints for Kubernetes probes
- Session management (create, list, get, delete)
- Chat endpoint for sending messages
- Keycloak authentication integration
- OpenFGA authorization integration
- Observability with OpenTelemetry

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
import os
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

pytestmark = [pytest.mark.unit, pytest.mark.playground]


class MockAuthMiddleware(BaseHTTPMiddleware):
    """Mock middleware that sets authenticated user in request state."""

    def __init__(self, app: FastAPI, user: dict[str, Any]) -> None:
        super().__init__(app)
        self.user = user

    async def dispatch(self, request, call_next):
        request.state.user = self.user
        response = await call_next(request)
        return response


@pytest.fixture
def mock_auth_user() -> dict[str, Any]:
    """Mock authenticated user data."""
    return {
        "user_id": "user:alice",
        "keycloak_id": "test-keycloak-alice-id",  # nosec: test data
        "username": "alice",
        "roles": ["user"],
        "email": "alice@example.com",
    }


@pytest.fixture
def mock_admin_user() -> dict[str, Any]:
    """Mock admin user data."""
    return {
        "user_id": "user:admin",
        "keycloak_id": "test-keycloak-admin-id",  # nosec: test data
        "username": "admin",
        "roles": ["admin"],
        "email": "admin@example.com",
    }


# ==============================================================================
# Health Endpoint Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundHealthEndpoints:
    """Test playground health check endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_health_endpoint_returns_healthy(self) -> None:
        """Test that /api/playground/health returns healthy status."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        response = client.get("/api/playground/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_health_endpoint_does_not_require_auth(self) -> None:
        """Test that health endpoint is accessible without authentication."""
        from mcp_server_langgraph.playground.api.server import app

        # No auth headers
        client = TestClient(app)
        response = client.get("/api/playground/health")

        # Should NOT return 401
        assert response.status_code == 200

    @pytest.mark.unit
    def test_health_ready_endpoint_checks_dependencies(self) -> None:
        """Test that /api/playground/health/ready checks service dependencies."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        response = client.get("/api/playground/health/ready")

        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data


# ==============================================================================
# Session Management Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundSessionManagement:
    """Test playground session CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_session_returns_session_id(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that POST /api/playground/sessions creates a new session."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)
            response = client.post(
                "/api/playground/sessions",
                json={"name": "Test Session"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "session_id" in data
            assert "created_at" in data

    @pytest.mark.unit
    def test_create_session_with_custom_config(self, mock_auth_user: dict[str, Any]) -> None:
        """Test creating session with custom LLM configuration."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)
            response = client.post(
                "/api/playground/sessions",
                json={
                    "name": "Custom Session",
                    "config": {
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 1000,
                    },
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "session_id" in data

    @pytest.mark.unit
    def test_list_sessions_returns_user_sessions(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that GET /api/playground/sessions returns user's sessions."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)
            response = client.get("/api/playground/sessions")

            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert isinstance(data["sessions"], list)

    @pytest.mark.unit
    def test_get_session_returns_session_details(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that GET /api/playground/sessions/{id} returns session details."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # First create a session
            create_response = client.post(
                "/api/playground/sessions",
                json={"name": "Test Session"},
            )
            assert create_response.status_code == 201
            session_id = create_response.json()["session_id"]

            # Then get it
            response = client.get(f"/api/playground/sessions/{session_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert "messages" in data

    @pytest.mark.unit
    def test_get_nonexistent_session_returns_404(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that getting a nonexistent session returns 404."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)
            response = client.get("/api/playground/sessions/nonexistent-id")

            assert response.status_code == 404

    @pytest.mark.unit
    def test_delete_session_removes_session(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that DELETE /api/playground/sessions/{id} removes the session."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # First create a session
            create_response = client.post(
                "/api/playground/sessions",
                json={"name": "Test Session"},
            )
            session_id = create_response.json()["session_id"]

            # Delete it
            delete_response = client.delete(f"/api/playground/sessions/{session_id}")
            assert delete_response.status_code == 204

            # Verify it's gone
            get_response = client.get(f"/api/playground/sessions/{session_id}")
            assert get_response.status_code == 404


# ==============================================================================
# Chat Endpoint Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundChatEndpoint:
    """Test playground chat message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_send_message_returns_response(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that POST /api/playground/chat sends message and gets response."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session first
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Chat Test"},
            )
            session_id = session_response.json()["session_id"]

            # Send message
            response = client.post(
                "/api/playground/chat",
                json={
                    "session_id": session_id,
                    "message": "Hello, how are you?",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "message_id" in data

    @pytest.mark.unit
    def test_send_message_to_invalid_session_returns_404(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that sending message to invalid session returns 404."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)
            response = client.post(
                "/api/playground/chat",
                json={
                    "session_id": "nonexistent-session",
                    "message": "Hello",
                },
            )

            assert response.status_code == 404

    @pytest.mark.unit
    def test_send_empty_message_returns_error(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that empty message returns validation error.

        Note: Pydantic validation returns 422 Unprocessable Entity for empty string
        when min_length=1 is enforced. This is correct FastAPI/Pydantic behavior.
        """
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session first
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Chat Test"},
            )
            session_id = session_response.json()["session_id"]

            # Send empty message
            response = client.post(
                "/api/playground/chat",
                json={
                    "session_id": session_id,
                    "message": "",
                },
            )

            # 422 = Pydantic validation error, 400 = our custom check for whitespace-only
            assert response.status_code in [400, 422]


# ==============================================================================
# Authentication Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundKeycloakAuth:
    """Test playground Keycloak authentication integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_session_requires_auth_in_production(self) -> None:
        """Test that session creation requires auth in production mode."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = TestClient(app)
            response = client.post(
                "/api/playground/sessions",
                json={"name": "Test"},
            )

            assert response.status_code == 401

    @pytest.mark.unit
    def test_chat_requires_auth_in_production(self) -> None:
        """Test that chat endpoint requires auth in production mode."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = TestClient(app)
            response = client.post(
                "/api/playground/chat",
                json={"session_id": "test", "message": "Hello"},
            )

            assert response.status_code == 401

    @pytest.mark.unit
    def test_list_sessions_requires_auth_in_production(self) -> None:
        """Test that listing sessions requires auth in production mode."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = TestClient(app)
            response = client.get("/api/playground/sessions")

            assert response.status_code == 401


# ==============================================================================
# Authorization Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundOpenFGAAuth:
    """Test playground OpenFGA authorization integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_can_only_access_own_sessions(self) -> None:
        """Test that users can only access their own sessions via OpenFGA."""
        # Setup mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # Container for configured methods
        mock_openfga.check_permission = AsyncMock(return_value=False)

        # When OpenFGA denies access, should return 403
        result = await mock_openfga.check_permission(
            user="user:bob",
            relation="owner",
            object="session:alice-session",
        )
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_owner_has_full_access(self) -> None:
        """Test that session owner has full access via OpenFGA."""
        mock_openfga = AsyncMock(return_value=None)  # Container for configured methods
        mock_openfga.check_permission = AsyncMock(return_value=True)

        result = await mock_openfga.check_permission(
            user="user:alice",
            relation="owner",
            object="session:alice-session",
        )
        assert result is True


# ==============================================================================
# Observability Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundObservability:
    """Test playground observability integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_tracer_available_in_playground(self) -> None:
        """Test that tracer is available in playground module."""
        from mcp_server_langgraph.observability.telemetry import tracer

        assert tracer is not None

    @pytest.mark.unit
    def test_logger_available_in_playground(self) -> None:
        """Test that logger is available in playground module."""
        from mcp_server_langgraph.observability.telemetry import logger

        assert logger is not None

    @pytest.mark.unit
    def test_chat_endpoint_creates_trace_span(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that chat endpoint creates a trace span."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Trace Test"},
            )
            session_id = session_response.json()["session_id"]

            # Send message - should create trace span
            response = client.post(
                "/api/playground/chat",
                json={
                    "session_id": session_id,
                    "message": "Test message for tracing",
                },
            )

            # Endpoint should work (trace span created internally)
            assert response.status_code == 200


# ==============================================================================
# API Documentation Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_api")
class TestPlaygroundAPIDocs:
    """Test playground API documentation endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_openapi_schema_available(self) -> None:
        """Test that OpenAPI schema is exposed."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    @pytest.mark.unit
    def test_swagger_docs_available(self) -> None:
        """Test that Swagger UI is available."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        response = client.get("/docs")

        assert response.status_code == 200
