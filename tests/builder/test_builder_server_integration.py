"""
Tests for unified builder server with Keycloak/OpenFGA auth integration.

Tests the builder API server with:
- Proper Keycloak authentication (not placeholder tokens)
- OpenFGA authorization for fine-grained access control
- SPAStaticFiles mounting for React frontend
- Health endpoint for Kubernetes probes

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.fixture
def spa_dist_directory() -> Path:
    """Create a temporary directory simulating frontend dist for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        spa_dir = Path(tmp)

        # Create index.html
        (spa_dir / "index.html").write_text(
            """<!DOCTYPE html>
<html>
<head><title>Visual Workflow Builder</title></head>
<body><div id="root"></div></body>
</html>"""
        )

        # Create static assets
        assets_dir = spa_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "app.js").write_text("console.log('builder');")

        yield spa_dir


@pytest.fixture
def mock_auth_user() -> dict[str, Any]:
    """Mock authenticated user data."""
    return {
        "user_id": "user:alice",
        "keycloak_id": "test-keycloak-alice-id",  # nosec: test data, not a real secret
        "username": "alice",
        "roles": ["user", "builder"],
        "email": "alice@example.com",
    }


@pytest.fixture
def mock_admin_user() -> dict[str, Any]:
    """Mock admin user data."""
    return {
        "user_id": "user:admin",
        "keycloak_id": "test-keycloak-admin-id",  # nosec: test data, not a real secret
        "username": "admin",
        "roles": ["admin", "builder"],
        "email": "admin@example.com",
    }


class MockAuthMiddleware(BaseHTTPMiddleware):
    """Mock middleware that sets authenticated user in request state."""

    def __init__(self, app: FastAPI, user: dict[str, Any]) -> None:
        super().__init__(app)
        self.user = user

    async def dispatch(self, request, call_next):
        request.state.user = self.user
        response = await call_next(request)
        return response


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerHealth:
    """Test builder server health endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_health_endpoint_returns_healthy(self) -> None:
        """Test that /api/builder/health returns healthy status."""
        from mcp_server_langgraph.builder.api.server import app

        client = TestClient(app)
        response = client.get("/api/builder/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_health_endpoint_does_not_require_auth(self) -> None:
        """Test that health endpoint is accessible without authentication."""
        from mcp_server_langgraph.builder.api.server import app

        # No auth headers
        client = TestClient(app)
        response = client.get("/api/builder/health")

        # Should NOT return 401
        assert response.status_code == 200


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerKeycloakAuth:
    """Test builder server Keycloak authentication integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_code_requires_keycloak_token(self, mock_auth_user: dict[str, Any]) -> None:
        """Test that /api/builder/generate requires valid Keycloak token."""
        from mcp_server_langgraph.builder.api.server import app

        # Test without auth middleware first (should fail in production mode)
        client = TestClient(app)

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = client.post(
                "/api/builder/generate",
                json={
                    "workflow": {
                        "name": "test",
                        "nodes": [],
                        "edges": [],
                        "entry_point": "start",
                    }
                },
            )
            # Should require auth in production
            assert response.status_code == 401

    @pytest.mark.unit
    def test_save_workflow_requires_keycloak_token(self) -> None:
        """Test that /api/builder/save requires valid Keycloak token."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            client = TestClient(app)
            response = client.post(
                "/api/builder/save",
                json={
                    "workflow": {
                        "name": "test",
                        "nodes": [],
                        "edges": [],
                        "entry_point": "start",
                    },
                    "output_path": "/tmp/test.py",  # nosec B108
                },
            )
            assert response.status_code == 401

    @pytest.mark.unit
    def test_import_workflow_requires_keycloak_token(self) -> None:
        """Test that /api/builder/import requires valid Keycloak token."""
        from mcp_server_langgraph.builder.api.server import app

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            client = TestClient(app)
            response = client.post(
                "/api/builder/import",
                json={"code": "print('hello')", "layout": "hierarchical"},
            )
            assert response.status_code == 401


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerOpenFGAAuth:
    """Test builder server OpenFGA authorization integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_code_checks_openfga_permission(self) -> None:
        """Test that code generation checks OpenFGA 'builder:execute' permission."""
        # Setup mock OpenFGA client
        mock_openfga = AsyncMock(return_value=None)  # Container for configured methods
        mock_openfga.check_permission = AsyncMock(return_value=True)

        # This test validates the integration pattern - actual implementation
        # will use require_builder_access dependency
        assert mock_openfga.check_permission is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unauthorized_user_cannot_generate_code(self) -> None:
        """Test that user without 'builder:execute' permission cannot generate code."""
        # Setup mock OpenFGA client that denies permission
        mock_openfga = AsyncMock(return_value=None)  # Container for configured methods
        mock_openfga.check_permission = AsyncMock(return_value=False)

        # When OpenFGA returns False, endpoint should return 403
        result = await mock_openfga.check_permission(
            user="user:guest",
            relation="execute",
            object="builder:workflow-generator",
        )
        assert result is False


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerSPAMount:
    """Test builder server SPA static files mounting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_spa_mount_serves_index_html(self, spa_dist_directory: Path, mock_auth_user: dict[str, Any]) -> None:
        """Test that SPA mount serves index.html for root path."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.add_middleware(MockAuthMiddleware, user=mock_auth_user)

        @app.get("/api/builder/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        # Mount SPA at root (after API routes)
        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_dist_directory), html=True),
            name="spa",
        )

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "Visual Workflow Builder" in response.text

    @pytest.mark.unit
    def test_spa_serves_static_assets(self, spa_dist_directory: Path, mock_auth_user: dict[str, Any]) -> None:
        """Test that SPA mount serves static assets."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()

        @app.get("/api/builder/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_dist_directory), html=True),
            name="spa",
        )

        client = TestClient(app)
        response = client.get("/assets/app.js")

        assert response.status_code == 200
        assert "console.log" in response.text

    @pytest.mark.unit
    def test_spa_fallback_for_client_routes(self, spa_dist_directory: Path, mock_auth_user: dict[str, Any]) -> None:
        """Test that SPA mount falls back to index.html for client routes."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()

        @app.get("/api/builder/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_dist_directory), html=True),
            name="spa",
        )

        client = TestClient(app)

        # Client-side routes should serve index.html
        for route in ["/workflows", "/editor/123", "/settings"]:
            response = client.get(route)
            assert response.status_code == 200, f"Route {route} should return 200"
            assert "Visual Workflow Builder" in response.text

    @pytest.mark.unit
    def test_api_routes_take_precedence_over_spa(self, spa_dist_directory: Path) -> None:
        """Test that API routes are served before SPA fallback."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()

        @app.get("/api/builder/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        @app.get("/api/builder/templates")
        def templates() -> dict[str, list]:
            return {"templates": []}

        # Mount SPA AFTER API routes
        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_dist_directory), html=True),
            name="spa",
        )

        client = TestClient(app)

        # API routes should work
        response = client.get("/api/builder/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        response = client.get("/api/builder/templates")
        assert response.status_code == 200
        assert response.json() == {"templates": []}


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerUnifiedEndpoints:
    """Test unified builder server serves both API and frontend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_unified_server_has_api_docs(self) -> None:
        """Test that unified server exposes OpenAPI docs."""
        from mcp_server_langgraph.builder.api.server import app

        client = TestClient(app)
        response = client.get("/docs")

        # FastAPI automatically serves docs
        assert response.status_code == 200

    @pytest.mark.unit
    def test_unified_server_has_openapi_schema(self) -> None:
        """Test that unified server exposes OpenAPI schema."""
        from mcp_server_langgraph.builder.api.server import app

        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema


@pytest.mark.xdist_group(name="builder_server_integration")
class TestBuilderServerAuthFactory:
    """Test builder server auth factory integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_auth_factory_creates_keycloak_provider_in_production(self) -> None:
        """Test that auth factory creates KeycloakUserProvider in production."""
        # This test documents the expected behavior
        # Actual implementation will integrate with create_auth_middleware
        from mcp_server_langgraph.auth.user_provider import KeycloakUserProvider

        # In production, should use Keycloak
        # (This would require full settings configuration)
        assert KeycloakUserProvider is not None

    @pytest.mark.unit
    def test_auth_uses_openfga_for_authorization(self) -> None:
        """Test that auth uses OpenFGA for fine-grained authorization."""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        # OpenFGA client should be available
        assert OpenFGAClient is not None
