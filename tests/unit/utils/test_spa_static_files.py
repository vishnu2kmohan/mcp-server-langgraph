"""
Unit tests for SPAStaticFiles utility.

Tests the single-page application static file handler that serves React SPA
with fallback to index.html for client-side routing.

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
import tempfile
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def spa_directory() -> Path:
    """Create a temporary directory with SPA files for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        spa_dir = Path(tmp)

        # Create index.html
        (spa_dir / "index.html").write_text(
            """<!DOCTYPE html>
<html>
<head><title>Test SPA</title></head>
<body><div id="root"></div></body>
</html>"""
        )

        # Create static assets
        assets_dir = spa_dir / "assets"
        assets_dir.mkdir()

        (assets_dir / "app.js").write_text("console.log('app');")
        (assets_dir / "style.css").write_text("body { margin: 0; }")

        # Create a nested static file
        img_dir = spa_dir / "images"
        img_dir.mkdir()
        (img_dir / "logo.svg").write_text("<svg></svg>")

        yield spa_dir


@pytest.fixture
def empty_spa_directory() -> Path:
    """Create an empty temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.mark.xdist_group(name="spa_static_files")
class TestSPAStaticFiles:
    """Test SPAStaticFiles class for serving React SPA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_serves_index_html_at_root(self, spa_directory: Path) -> None:
        """Test that root path serves index.html."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "Test SPA" in response.text
        assert '<div id="root">' in response.text

    @pytest.mark.unit
    def test_serves_static_js_files(self, spa_directory: Path) -> None:
        """Test that JavaScript files are served correctly."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)
        response = client.get("/assets/app.js")

        assert response.status_code == 200
        assert "console.log" in response.text
        assert "javascript" in response.headers.get("content-type", "").lower()

    @pytest.mark.unit
    def test_serves_static_css_files(self, spa_directory: Path) -> None:
        """Test that CSS files are served correctly."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)
        response = client.get("/assets/style.css")

        assert response.status_code == 200
        assert "margin: 0" in response.text
        assert "css" in response.headers.get("content-type", "").lower()

    @pytest.mark.unit
    def test_serves_nested_static_files(self, spa_directory: Path) -> None:
        """Test that nested static files (e.g., images) are served correctly."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)
        response = client.get("/images/logo.svg")

        assert response.status_code == 200
        assert "<svg>" in response.text

    @pytest.mark.unit
    def test_fallback_to_index_html_for_client_routes(self, spa_directory: Path) -> None:
        """Test that non-existent routes fall back to index.html for SPA routing."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)

        # Test various SPA routes that should all serve index.html
        routes = [
            "/dashboard",
            "/users/123",
            "/settings/profile",
            "/some/deep/nested/route",
        ]

        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, f"Route {route} should return 200"
            assert "Test SPA" in response.text, f"Route {route} should serve index.html"

    @pytest.mark.unit
    def test_returns_404_for_missing_static_file_with_extension(self, spa_directory: Path) -> None:
        """Test that missing static files with extensions return 404."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)

        # Missing files with extensions should return 404, not index.html
        missing_files = [
            "/assets/missing.js",
            "/assets/notfound.css",
            "/images/nope.png",
        ]

        for path in missing_files:
            response = client.get(path)
            assert response.status_code == 404, f"Missing file {path} should return 404"

    @pytest.mark.unit
    def test_api_routes_not_affected_when_mounted_at_root(self, spa_directory: Path) -> None:
        """Test that API routes take precedence over SPA when properly ordered."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()

        @app.get("/api/health")
        def health() -> dict[str, str]:
            return {"status": "healthy"}

        @app.get("/api/builder/templates")
        def templates() -> dict[str, Any]:
            return {"templates": []}

        # Mount SPA AFTER API routes
        app.mount("/", SPAStaticFiles(directory=str(spa_directory), html=True), name="spa")

        client = TestClient(app)

        # API routes should work
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        response = client.get("/api/builder/templates")
        assert response.status_code == 200
        assert response.json() == {"templates": []}

        # SPA routes should still work
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Test SPA" in response.text

    @pytest.mark.unit
    def test_raises_error_for_missing_directory(self) -> None:
        """Test that creating SPAStaticFiles with missing directory raises error."""
        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        with pytest.raises(RuntimeError, match="does not exist"):
            SPAStaticFiles(directory="/nonexistent/path", html=True)

    @pytest.mark.unit
    def test_raises_error_for_missing_index_html(self, empty_spa_directory: Path) -> None:
        """Test that creating SPAStaticFiles without index.html raises error."""
        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        with pytest.raises(RuntimeError, match="index.html"):
            SPAStaticFiles(directory=str(empty_spa_directory), html=True)


@pytest.mark.xdist_group(name="spa_static_files")
class TestSPAStaticFilesWithCaching:
    """Test SPAStaticFiles caching behavior for production performance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_static_assets_have_cache_headers(self, spa_directory: Path) -> None:
        """Test that static assets include cache control headers."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_directory), html=True, caching=True),
            name="spa",
        )

        client = TestClient(app)

        # Static assets should have cache headers
        response = client.get("/assets/app.js")
        assert response.status_code == 200

        # Check for cache-control header (immutable for hashed assets)
        cache_control = response.headers.get("cache-control", "")
        assert "max-age" in cache_control.lower() or cache_control == ""

    @pytest.mark.unit
    def test_index_html_has_no_cache_header(self, spa_directory: Path) -> None:
        """Test that index.html has no-cache to ensure fresh content."""
        from fastapi import FastAPI

        from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

        app = FastAPI()
        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_directory), html=True, caching=True),
            name="spa",
        )

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        # index.html should not be aggressively cached
        cache_control = response.headers.get("cache-control", "")
        assert "immutable" not in cache_control.lower()


@pytest.mark.xdist_group(name="spa_static_files")
class TestSPAStaticFilesFactory:
    """Test the create_spa_static_files factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_factory_creates_spa_handler(self, spa_directory: Path) -> None:
        """Test that factory function creates a valid SPA handler."""
        from mcp_server_langgraph.utils.spa_static_files import create_spa_static_files

        handler = create_spa_static_files(str(spa_directory))

        assert handler is not None

    @pytest.mark.unit
    def test_factory_returns_none_for_missing_directory(self) -> None:
        """Test that factory returns None for missing directory."""
        from mcp_server_langgraph.utils.spa_static_files import create_spa_static_files

        handler = create_spa_static_files("/nonexistent/path")

        assert handler is None

    @pytest.mark.unit
    def test_factory_with_caching_enabled(self, spa_directory: Path) -> None:
        """Test factory with caching parameter."""
        from mcp_server_langgraph.utils.spa_static_files import create_spa_static_files

        handler = create_spa_static_files(str(spa_directory), caching=True)

        assert handler is not None
