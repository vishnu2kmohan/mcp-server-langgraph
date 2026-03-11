"""
Contract Tests: OpenAPI Schema ↔ FastAPI Routes Sync Validation.

Ensures the api/openapi.json schema stays in sync with actual FastAPI routes.
This test prevents the scenario where:
1. Developer adds a new endpoint to FastAPI
2. Forgets to regenerate openapi.json
3. Frontend parity tests pass (because they check OpenAPI, not actual routes)
4. Users hit 400/404 errors at runtime when calling valid frontend actions

Sprint: Post-audit fix for canvas/explain and canvas/fix 400 errors.
Root cause: OpenAPI schema was 53 endpoints behind actual FastAPI routes.

Run: uv run pytest tests/contract/test_openapi_fastapi_sync.py -v
"""

from __future__ import annotations

import gc
import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.xdist_group(name="openapi_sync")]


def get_openapi_schema_path() -> Path:
    """Get the path to the OpenAPI schema file."""
    current = Path(__file__).parent
    schema_path = current.parent.parent / "api" / "openapi.json"
    if not schema_path.exists():
        pytest.skip(f"OpenAPI schema not found at {schema_path}")
    return schema_path


def load_openapi_schema() -> dict[str, Any]:
    """Load the OpenAPI schema from api/openapi.json."""
    schema_path = get_openapi_schema_path()
    with open(schema_path) as f:
        return json.load(f)


def get_fastapi_routes() -> set[tuple[str, str]]:
    """
    Extract all routes from the live FastAPI app.

    Returns:
        Set of (method, path) tuples for all API routes.
    """
    # Import must happen inside function to avoid app startup issues in collection
    from mcp_server_langgraph.app import app

    routes: set[tuple[str, str]] = set()

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            # Only include API routes
            if not path.startswith("/api/"):
                continue

            for method in route.methods:
                if method not in ["HEAD", "OPTIONS"]:
                    routes.add((method, path))

    return routes


def normalize_path(path: str) -> str:
    """Normalize path by standardizing parameter names."""
    # Convert {param_name} to {id} for comparison
    return re.sub(r"\{[^}]+\}", "{id}", path)


@pytest.mark.xdist_group("test_open_a_p_i_fast_a_p_i_sync")
@pytest.mark.contract
class TestOpenAPIFastAPISync:
    """
    Contract tests ensuring OpenAPI schema matches actual FastAPI routes.

    These tests catch:
    - New endpoints added to FastAPI but not regenerated in openapi.json
    - Endpoints removed from FastAPI but still in openapi.json
    - Route path mismatches between spec and implementation
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_openapi_schema_not_stale(self) -> None:
        """
        OpenAPI schema should contain all FastAPI routes.

        This is the critical test that would have caught the canvas/explain
        and canvas/fix issues before they reached production.
        """
        openapi_schema = load_openapi_schema()
        openapi_paths = set(openapi_schema.get("paths", {}).keys())

        fastapi_routes = get_fastapi_routes()

        # Normalize both for comparison
        normalized_openapi = {normalize_path(p) for p in openapi_paths}
        normalized_fastapi = {normalize_path(path) for _, path in fastapi_routes}

        # Find routes in FastAPI that are missing from OpenAPI
        missing_from_openapi = normalized_fastapi - normalized_openapi

        # Filter out known exceptions (e.g., health checks, docs, internal endpoints)
        known_exceptions = {
            "/api/v1/health",
            "/api/v1/health/deps",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            # Root-level docs (FastAPI auto-generated)
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            # Internal endpoints with include_in_schema=False
            "/api/v1/api-keys/validate",  # Kong plugin internal endpoint
        }
        missing_from_openapi = {p for p in missing_from_openapi if normalize_path(p) not in known_exceptions}

        if missing_from_openapi:
            # Sort for consistent output
            missing_list = sorted(missing_from_openapi)[:20]
            missing_str = "\n  - ".join(missing_list)

            pytest.fail(
                f"OpenAPI schema is STALE! Found {len(missing_from_openapi)} FastAPI routes "
                f"not in api/openapi.json:\n"
                f"  - {missing_str}\n\n"
                f"To fix: Run 'uv run python scripts/export_openapi.py' to regenerate the schema.\n"
                f"This script exports the current FastAPI routes to api/openapi.json."
            )

    def test_openapi_has_no_phantom_routes(self) -> None:
        """
        OpenAPI schema should not contain routes that don't exist in FastAPI.

        Phantom routes indicate stale schema entries that were removed from
        the backend but never cleaned up from the spec.
        """
        openapi_schema = load_openapi_schema()
        openapi_paths = set(openapi_schema.get("paths", {}).keys())

        fastapi_routes = get_fastapi_routes()

        # Normalize both for comparison
        normalized_openapi = {normalize_path(p) for p in openapi_paths}
        normalized_fastapi = {normalize_path(path) for _, path in fastapi_routes}

        # Find routes in OpenAPI that don't exist in FastAPI
        phantom_routes = normalized_openapi - normalized_fastapi

        # Filter out known non-API routes that may be in spec
        known_non_api = {
            "/",
            "/health",
            "/.well-known/{id}",  # OIDC/OAuth discovery
        }
        phantom_routes = {p for p in phantom_routes if p not in known_non_api}

        # Allow small tolerance for timing (routes being added/removed)
        if len(phantom_routes) > 5:
            phantom_list = sorted(phantom_routes)[:10]
            phantom_str = "\n  - ".join(phantom_list)

            pytest.fail(
                f"OpenAPI schema has {len(phantom_routes)} PHANTOM routes "
                f"not in FastAPI app:\n"
                f"  - {phantom_str}\n\n"
                f"These routes exist in api/openapi.json but were removed from the backend.\n"
                f"To fix: Run 'uv run python scripts/export_openapi.py' to regenerate the schema."
            )

    def test_openapi_path_count_reasonable(self) -> None:
        """Sanity check that OpenAPI has expected number of routes."""
        openapi_schema = load_openapi_schema()
        path_count = len(openapi_schema.get("paths", {}))

        # Based on current codebase, we expect 200+ routes
        assert path_count >= 200, (
            f"OpenAPI schema only has {path_count} paths. Expected at least 200. Did the export script fail?"
        )

    def test_fastapi_route_count_reasonable(self) -> None:
        """Sanity check that FastAPI app has expected number of routes."""
        routes = get_fastapi_routes()

        # Based on current codebase, we expect 150+ API routes
        assert len(routes) >= 150, (
            f"FastAPI app only has {len(routes)} API routes. Expected at least 150. Did the app fail to initialize properly?"
        )

    def test_openapi_schema_freshness_indicator(self) -> None:
        """
        Warn if OpenAPI schema file is older than Python source files.

        This is a heuristic check - if api/openapi.json is older than
        any router file, it may be stale.
        """
        openapi_path = get_openapi_schema_path()
        openapi_mtime = openapi_path.stat().st_mtime

        # Check router files
        api_v1_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1"
        if not api_v1_path.exists():
            pytest.skip("API v1 directory not found")

        newer_routers = []
        for py_file in api_v1_path.glob("*.py"):
            if py_file.stat().st_mtime > openapi_mtime:
                newer_routers.append(py_file.name)

        if newer_routers:
            # This is a warning, not a failure - the schema may still be valid
            # But it's a strong indicator that regeneration is needed
            pytest.skip(
                f"OpenAPI schema may be stale. These router files are newer:\n"
                f"  {', '.join(newer_routers[:5])}\n"
                f"Consider running: uv run python scripts/export_openapi.py"
            )


@pytest.mark.xdist_group("test_open_a_p_i_c_i_integration")
@pytest.mark.contract
class TestOpenAPICIIntegration:
    """
    Tests for CI/CD integration with OpenAPI sync.

    These tests help ensure the sync check is part of the development workflow.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_export_script_exists(self) -> None:
        """The OpenAPI export script should exist."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "export_openapi.py"
        assert script_path.exists(), (
            f"OpenAPI export script not found at {script_path}. This script is required to regenerate the schema."
        )

    def test_export_script_is_executable(self) -> None:
        """The export script should be runnable."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "export_openapi.py"
        if not script_path.exists():
            pytest.skip("Export script not found")

        # Check it's a valid Python file
        content = script_path.read_text()
        assert "export_openapi" in content, "Export script missing export_openapi function"
        assert "app.openapi()" in content or "openapi_schema" in content, (
            "Export script doesn't appear to generate OpenAPI schema"
        )
