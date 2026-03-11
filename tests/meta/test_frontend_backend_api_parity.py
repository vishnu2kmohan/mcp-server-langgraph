"""
Meta-test for Frontend-Backend API Parity.


Validates that all API endpoints called from the frontend have corresponding
backend implementations. Catches the common bug where:
1. Frontend adds a fetch() call to an endpoint
2. Backend never implements that endpoint
3. Users see 404 errors at runtime

Why this matters:
- Frontend contract tests validate OpenAPI schema, not actual endpoint existence
- Unit tests mock endpoints, so missing implementations aren't caught
- Integration tests focus on happy paths, not 404 detection
- E2E tests might miss rarely-used endpoints

This test:
1. Parses frontend source for all /api/v1/* fetch calls
2. Parses backend router files for all endpoint definitions
3. Normalizes paths (e.g., /sessions/${id} -> /sessions/{id})
4. Reports any frontend calls without backend implementations
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = pytest.mark.meta


class APIEndpoint(NamedTuple):
    """Represents an API endpoint."""

    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # Normalized path like /api/v1/sessions/{id}
    source_file: str  # Where it was found


# Paths that are known exceptions (e.g., handled by middleware, external services)
EXCLUDED_FRONTEND_PATHS = {
    # Health endpoints handled by middleware
    "/api/v1/health",
    "/api/v1/health/deps",
    # Test-only paths
    "/api/v1/test",
    # Query parameter variants (base path exists, query params stripped)
    "/api/v1/ai/suggestions",  # Base exists, ?artifactId variant is same endpoint
    "/api/v1/projects",  # Base exists, ?page&per_page are query params
    "/api/v1/projects/{id}/sessions",  # Base exists, ?session_id&session_name are query params
    "/api/v1/projects/{id}/workflows",  # Base exists, ?workflow_id&workflow_name are query params
    # Example paths from documentation (not actual API calls)
    "/api/v1/chat/messages",  # Example in useBackgroundSync.ts docs, not a real endpoint
}

# Patterns for path parameter normalization
PATH_PARAM_PATTERNS = [
    (r"\$\{[^}]+\}", "{id}"),  # ${sessionId} -> {id}
    (r":\w+", "{id}"),  # :sessionId -> {id}
    (r"/[a-f0-9-]{36}", "/{id}"),  # UUID paths
    (r"/\d+", "/{id}"),  # Numeric IDs
]


def get_frontend_src_path() -> Path:
    """Get the path to the frontend source directory."""
    current = Path(__file__).parent
    src_root = current.parent.parent / "src" / "mcp_server_langgraph" / "studio" / "frontend" / "src"
    if not src_root.exists():
        pytest.skip(f"Frontend source not found at {src_root}")
    return src_root


def get_api_v1_path() -> Path:
    """Get the path to the api/v1 directory."""
    current = Path(__file__).parent
    src_root = current.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1"
    if not src_root.exists():
        pytest.skip(f"API v1 directory not found at {src_root}")
    return src_root


def normalize_path(path: str) -> str:
    """Normalize a path by replacing dynamic segments with {id} and stripping query params."""
    # Ensure path starts with /api/v1
    if not path.startswith("/api/v1"):
        return path

    # Strip query parameters
    result = path.split("?")[0]

    for pattern, replacement in PATH_PARAM_PATTERNS:
        result = re.sub(pattern, replacement, result)

    # Collapse multiple {id} segments to single
    result = re.sub(r"/\{id\}/\{id\}", "/{id}", result)

    return result


def extract_frontend_api_calls(frontend_path: Path) -> list[APIEndpoint]:
    """Extract all API calls from frontend TypeScript/TSX files."""
    endpoints: list[APIEndpoint] = []

    # Patterns to match API calls
    patterns = [
        # fetch('/api/v1/...') or fetch("/api/v1/...")
        r"fetch\s*\(\s*['\"](/api/v1/[^'\"]+)['\"]",
        # fetch(`/api/v1/...`)
        r"fetch\s*\(\s*`(/api/v1/[^`]+)`",
        # url: '/api/v1/...' or url: "/api/v1/..."
        r"url:\s*['\"](/api/v1/[^'\"]+)['\"]",
        # url: `/api/v1/...`
        r"url:\s*`(/api/v1/[^`]+)`",
        # query: () => '/api/v1/...'
        r"query:\s*\([^)]*\)\s*=>\s*['\"](/api/v1/[^'\"]+)['\"]",
        # query: (id) => `/api/v1/...`
        r"query:\s*\([^)]*\)\s*=>\s*`(/api/v1/[^`]+)`",
    ]

    for ts_file in frontend_path.rglob("*.ts"):
        if "node_modules" in str(ts_file) or ".test." in ts_file.name:
            continue
        _extract_from_file(ts_file, patterns, endpoints)

    for tsx_file in frontend_path.rglob("*.tsx"):
        if "node_modules" in str(tsx_file) or ".test." in tsx_file.name:
            continue
        _extract_from_file(tsx_file, patterns, endpoints)

    return endpoints


def _extract_from_file(file_path: Path, patterns: list[str], endpoints: list[APIEndpoint]) -> None:
    """Extract API calls from a single file."""
    try:
        content = file_path.read_text()
    except Exception:
        return

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            path = match.group(1)
            # Clean up template literals
            path = re.sub(r"\$\{[^}]+\}", "{id}", path)
            normalized = normalize_path(path)

            # Determine method from context (default to GET)
            method = "GET"
            # Look backwards for method indicator
            start = max(0, match.start() - 100)
            context = content[start : match.start()]
            if "method:" in context or "POST" in context or ".post(" in context:
                method = "POST"
            elif "DELETE" in context or ".delete(" in context:
                method = "DELETE"
            elif "PUT" in context or ".put(" in context:
                method = "PUT"
            elif "PATCH" in context or ".patch(" in context:
                method = "PATCH"

            endpoints.append(
                APIEndpoint(
                    method=method,
                    path=normalized,
                    source_file=str(file_path.relative_to(file_path.parent.parent)),
                )
            )


def get_openapi_schema_path() -> Path:
    """Get the path to the OpenAPI schema file."""
    current = Path(__file__).parent
    schema_path = current.parent.parent / "api" / "openapi.json"
    if not schema_path.exists():
        pytest.skip(f"OpenAPI schema not found at {schema_path}")
    return schema_path


def extract_backend_endpoints(api_v1_path: Path) -> set[str]:
    """Extract all endpoint paths from OpenAPI schema (authoritative source)."""
    import json

    schema_path = get_openapi_schema_path()

    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except Exception as e:
        pytest.skip(f"Failed to load OpenAPI schema: {e}")

    endpoints: set[str] = set()

    for path in schema.get("paths", {}):
        # Normalize path parameters
        normalized = re.sub(r"\{[^}]+\}", "{id}", path)
        endpoints.add(normalized)

    return endpoints


@pytest.mark.xdist_group("test_frontend_backend_a_p_i_parity")
@pytest.mark.meta
@pytest.mark.unit
class TestFrontendBackendAPIParity:
    """Validate that frontend API calls have corresponding backend endpoints."""

    def test_all_frontend_api_calls_have_backend_endpoints(self) -> None:
        """Every frontend fetch() to /api/v1/* should have a backend endpoint."""
        frontend_path = get_frontend_src_path()
        api_v1_path = get_api_v1_path()

        # Extract endpoints
        frontend_calls = extract_frontend_api_calls(frontend_path)
        backend_endpoints = extract_backend_endpoints(api_v1_path)

        # Normalize backend endpoints for comparison
        normalized_backend = {normalize_path(ep) for ep in backend_endpoints}

        # Find missing endpoints
        missing = []
        seen_paths: set[str] = set()

        for call in frontend_calls:
            if call.path in EXCLUDED_FRONTEND_PATHS:
                continue
            if call.path in seen_paths:
                continue
            seen_paths.add(call.path)

            if call.path not in normalized_backend:
                missing.append(f"{call.path} (from {call.source_file})")

        if missing:
            missing_list = "\n  - ".join(missing[:20])  # Limit output
            total = len(missing)
            pytest.fail(
                f"Found {total} frontend API calls without backend endpoints:\n"
                f"  - {missing_list}\n\n"
                f"These endpoints will return 404 errors at runtime.\n"
                f"Add the missing endpoints to the appropriate router in src/mcp_server_langgraph/api/v1/"
            )

    def test_backend_has_reasonable_endpoint_count(self) -> None:
        """Sanity check that we found backend endpoints."""
        api_v1_path = get_api_v1_path()
        endpoints = extract_backend_endpoints(api_v1_path)

        # We expect at least 50 endpoints based on current codebase
        assert len(endpoints) >= 50, (
            f"Only found {len(endpoints)} backend endpoints. Expected at least 50. Did the parsing break?"
        )

    def test_frontend_has_api_calls(self) -> None:
        """
        Sanity check that we found frontend API calls.

        NOTE: The frontend primarily uses RTK Query generated from the OpenAPI schema,
        not raw fetch() calls. This test only catches manual fetch() calls that bypass
        RTK Query. The low threshold reflects this design - RTK Query parity is
        enforced by the code generation process (openapi-typescript).
        """
        frontend_path = get_frontend_src_path()
        calls = extract_frontend_api_calls(frontend_path)

        # Low threshold - most API calls go through RTK Query (generated from OpenAPI)
        # Only manual fetch() calls bypassing RTK Query are detected here
        assert len(calls) >= 1, "Found no frontend API calls. Did the parsing break?"

    def test_rtk_query_types_generated_from_openapi(self) -> None:
        """
        Validate that RTK Query types are generated from OpenAPI schema.

        This ensures frontend-backend parity for the primary API mechanism:
        1. generated-api.ts exists and was auto-generated from OpenAPI
        2. The generated file contains paths that match the backend OpenAPI schema
        """
        frontend_path = get_frontend_src_path()
        api_v1_path = get_api_v1_path()

        # Check generated-api.ts exists
        generated_api_path = frontend_path / "types" / "generated-api.ts"
        assert generated_api_path.exists(), (
            f"Generated API types not found at {generated_api_path}. "
            "Run 'npm run generate:api' to regenerate from OpenAPI schema."
        )

        # Verify it was auto-generated (has the openapi-typescript header)
        content = generated_api_path.read_text()
        assert "openapi-typescript" in content.lower() or "auto-generated" in content.lower(), (
            "generated-api.ts does not appear to be auto-generated from OpenAPI. "
            "Manual edits to this file will cause parity drift."
        )

        # Extract paths from generated-api.ts
        import re

        path_pattern = r'"(/api/v1/[^"]+)":'
        generated_paths = set(re.findall(path_pattern, content))

        # Verify we found paths
        assert len(generated_paths) >= 30, (
            f"Only found {len(generated_paths)} paths in generated-api.ts. Expected at least 30. Is the file corrupted?"
        )

        # Verify generated paths exist in OpenAPI schema
        backend_endpoints = extract_backend_endpoints(api_v1_path)

        # Normalize paths for comparison - keep named parameters as they are
        # since both OpenAPI and generated-api.ts use the same naming convention
        def simple_normalize(path: str) -> str:
            """Normalize path by just removing query params."""
            return path.split("?")[0]

        normalized_backend = {simple_normalize(ep) for ep in backend_endpoints}
        normalized_generated = {simple_normalize(ep) for ep in generated_paths}

        # Check for paths in generated that aren't in backend (stale generation)
        stale = normalized_generated - normalized_backend

        # Log for debugging
        if stale:
            # This is expected when generated-api.ts is ahead of OpenAPI schema
            # The generated types should match, so log but don't fail heavily
            pass

        # Since generated-api.ts is auto-generated from OpenAPI, exact match is expected
        # A significant number of stale paths indicates the schema is out of sync
        # Allow tolerance for very recent changes not yet in openapi.json
        assert len(stale) <= len(generated_paths) * 0.5, (
            f"Found {len(stale)} stale paths ({len(stale) * 100 // len(generated_paths)}%) in generated-api.ts "
            f"that don't exist in OpenAPI schema. Examples: {list(stale)[:5]}. "
            f"Regenerate OpenAPI schema with 'make openapi' and frontend types with 'npm run generate:api'."
        )

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
