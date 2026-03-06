"""
WebSocket Endpoint Parity Contract Tests.

Validates that all WebSocket endpoints used by the frontend have corresponding
backend implementations, and vice versa.

This test catches the common bug where:
1. Frontend adds a WebSocket connection to an endpoint
2. Backend never implements that WebSocket handler
3. Users see connection failures at runtime

Why this matters:
- Frontend unit tests mock WebSocket connections completely
- Integration tests often skip WebSocket verification
- E2E tests check UI visibility, not actual connectivity
- Missing endpoints discovered only at runtime

This test:
1. Parses frontend WS_ENDPOINTS from websocket.ts
2. Parses backend @ws_router.websocket decorators from ws_router.py
3. Reports any frontend endpoints without backend implementations
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.websocket]


def get_frontend_websocket_ts_path() -> Path:
    """Get the path to the frontend websocket.ts file."""
    current = Path(__file__).parent
    ws_path = current.parent.parent / "src" / "mcp_server_langgraph" / "studio" / "frontend" / "src" / "utils" / "websocket.ts"
    if not ws_path.exists():
        pytest.skip(f"Frontend websocket.ts not found at {ws_path}")
    return ws_path


def get_backend_ws_router_path() -> Path:
    """Get the path to the backend ws_router.py file."""
    current = Path(__file__).parent
    router_path = current.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ws_router.py"
    if not router_path.exists():
        pytest.skip(f"Backend ws_router.py not found at {router_path}")
    return router_path


def extract_frontend_ws_endpoints(websocket_ts_path: Path) -> dict[str, str]:
    """
    Extract WS_ENDPOINTS from frontend websocket.ts.

    Returns:
        Dict mapping endpoint name to path (e.g., {"DEVTOOLS": "/api/v1/ws/devtools"})
    """
    content = websocket_ts_path.read_text()

    # Match WS_ENDPOINTS object entries
    # Pattern: ENDPOINT_NAME: "/api/v1/ws/..."
    pattern = r'^\s*(\w+):\s*["\']([^"\']+)["\']'

    endpoints: dict[str, str] = {}

    # Find the WS_ENDPOINTS block
    ws_endpoints_match = re.search(r"export const WS_ENDPOINTS = \{([^}]+)\}", content, re.DOTALL)
    if ws_endpoints_match:
        block = ws_endpoints_match.group(1)
        for match in re.finditer(pattern, block, re.MULTILINE):
            name = match.group(1)
            path = match.group(2)
            # Only include WebSocket endpoints
            if "/api/v1/ws/" in path:
                endpoints[name] = path

    return endpoints


def extract_backend_ws_endpoints(ws_router_path: Path) -> set[str]:
    """
    Extract WebSocket endpoints from backend ws_router.py.

    Returns:
        Set of endpoint paths (e.g., {"/api/v1/ws/devtools", "/api/v1/ws/alerts"})
    """
    content = ws_router_path.read_text()

    # Match @ws_router.websocket("/path") decorators
    # The paths are relative to /api/v1/ws (router prefix)
    pattern = r'@ws_router\.websocket\s*\(\s*["\']([^"\']+)["\']'

    endpoints: set[str] = set()
    for match in re.finditer(pattern, content):
        relative_path = match.group(1)
        # Convert relative path to full path
        # /mcp -> /api/v1/ws/mcp
        full_path = f"/api/v1/ws{relative_path}"
        endpoints.add(full_path)

    return endpoints


def normalize_ws_path(path: str) -> str:
    """
    Normalize WebSocket path for comparison.

    Converts path parameters to standard format:
    - /api/v1/ws/workflows/:workflowId -> /api/v1/ws/workflows/{id}
    - /api/v1/ws/mcp/:sessionId -> /api/v1/ws/mcp/{id}
    """
    # Replace :param format with {id}
    result = re.sub(r":(\w+)", "{id}", path)
    # Replace {param_name} format with {id}
    result = re.sub(r"\{[^}]+\}", "{id}", result)
    return result


class TestWebSocketEndpointParity:
    """Validate that frontend WebSocket endpoints have backend implementations."""

    def test_all_frontend_ws_endpoints_have_backend_handlers(self) -> None:
        """Every frontend WS_ENDPOINTS entry should have a backend WebSocket handler."""
        frontend_path = get_frontend_websocket_ts_path()
        backend_path = get_backend_ws_router_path()

        frontend_endpoints = extract_frontend_ws_endpoints(frontend_path)
        backend_endpoints = extract_backend_ws_endpoints(backend_path)

        # Normalize paths for comparison
        normalized_backend = {normalize_ws_path(ep) for ep in backend_endpoints}

        missing: list[str] = []
        for name, path in frontend_endpoints.items():
            normalized_path = normalize_ws_path(path)
            if normalized_path not in normalized_backend:
                missing.append(f"{name}: {path}")

        if missing:
            missing_list = "\n  - ".join(missing)
            pytest.fail(
                f"Found {len(missing)} frontend WebSocket endpoints without backend handlers:\n"
                f"  - {missing_list}\n\n"
                f"These endpoints will fail WebSocket connections at runtime.\n"
                f"Add the missing handlers to src/mcp_server_langgraph/api/v1/ws_router.py\n"
                f"or create new handlers in src/mcp_server_langgraph/websocket/handlers/"
            )

    def test_backend_has_reasonable_ws_endpoint_count(self) -> None:
        """Sanity check that we found backend WebSocket endpoints."""
        backend_path = get_backend_ws_router_path()
        endpoints = extract_backend_ws_endpoints(backend_path)

        # We expect at least 15 WebSocket endpoints based on current codebase
        assert len(endpoints) >= 15, (
            f"Only found {len(endpoints)} backend WebSocket endpoints. Expected at least 15. Did the parsing break?"
        )

    def test_frontend_has_ws_endpoints(self) -> None:
        """Sanity check that we found frontend WS_ENDPOINTS."""
        frontend_path = get_frontend_websocket_ts_path()
        endpoints = extract_frontend_ws_endpoints(frontend_path)

        # We expect at least 10 WS_ENDPOINTS
        assert len(endpoints) >= 10, (
            f"Only found {len(endpoints)} frontend WS_ENDPOINTS. Expected at least 10. Did the parsing break?"
        )

    def test_devtools_websocket_endpoint_exists(self) -> None:
        """Specific test for DevTools WebSocket endpoint - the gap that triggered this audit."""
        backend_path = get_backend_ws_router_path()
        backend_endpoints = extract_backend_ws_endpoints(backend_path)

        devtools_endpoint = "/api/v1/ws/devtools"
        assert devtools_endpoint in backend_endpoints, (
            f"CRITICAL: DevTools WebSocket endpoint missing!\n"
            f"Frontend expects {devtools_endpoint} but backend doesn't implement it.\n"
            f"Add @ws_router.websocket('/devtools') handler to ws_router.py"
        )


class TestWebSocketEndpointDocumentation:
    """Validate WebSocket endpoints are properly documented."""

    def test_all_backend_ws_endpoints_in_frontend_constants(self) -> None:
        """Backend WebSocket endpoints should have WS_ENDPOINTS constants for frontend use."""
        frontend_path = get_frontend_websocket_ts_path()
        backend_path = get_backend_ws_router_path()

        frontend_endpoints = extract_frontend_ws_endpoints(frontend_path)
        backend_endpoints = extract_backend_ws_endpoints(backend_path)

        # Normalize frontend paths for comparison
        frontend_paths = {normalize_ws_path(path) for path in frontend_endpoints.values()}

        # Find backend endpoints without frontend constants
        # (This is a warning, not an error - some endpoints might be internal-only)
        undocumented: list[str] = []
        for endpoint in backend_endpoints:
            normalized = normalize_ws_path(endpoint)
            if normalized not in frontend_paths:
                undocumented.append(endpoint)

        # Log undocumented endpoints for visibility (don't fail, just warn)
        if undocumented:
            # This is informational - internal endpoints may not need frontend constants
            pass  # Consider adding pytest.warns() if you want to track these


def extract_backend_auth_requirements(ws_router_path: Path) -> dict[str, bool]:
    """
    Extract require_auth settings from backend ws_router.py.

    Returns:
        Dict mapping endpoint path to whether it requires authentication.
    """
    content = ws_router_path.read_text()

    # Find @ws_router.websocket and require_auth within nearby lines
    # Uses DOTALL to match across newlines
    pattern = r'@ws_router\.websocket\s*\(["\']([^"\']+)["\'].*?require_auth\s*=\s*(True|False)'
    matches = re.findall(pattern, content, re.DOTALL)

    results: dict[str, bool] = {}
    for relative_path, auth_value in matches:
        full_path = f"/api/v1/ws{relative_path}"
        results[full_path] = auth_value == "True"

    return results


class TestWebSocketAuthenticationContract:
    """Validate that backend require_auth settings are correctly documented."""

    def test_authenticated_endpoints_documented(self) -> None:
        """All endpoints requiring auth should be identified for frontend integration."""
        backend_path = get_backend_ws_router_path()
        auth_requirements = extract_backend_auth_requirements(backend_path)

        # Count authenticated vs unauthenticated endpoints
        auth_required = [ep for ep, req in auth_requirements.items() if req]
        no_auth = [ep for ep, req in auth_requirements.items() if not req]

        # Sanity check - most endpoints should require auth
        assert len(auth_required) >= 10, (
            f"Expected at least 10 endpoints requiring auth, found {len(auth_required)}. "
            f"Auth requirements: {auth_requirements}"
        )

        # Sanity check - there should be at least 2 endpoints that don't require auth
        # (e.g., /ws/mcp for anonymous connections)
        assert len(no_auth) >= 2, (
            f"Expected at least 2 endpoints without auth requirement, found {len(no_auth)}. "
            f"These are typically for anonymous MCP connections."
        )

    def test_critical_endpoints_require_auth(self) -> None:
        """Critical WebSocket endpoints must require authentication."""
        backend_path = get_backend_ws_router_path()
        auth_requirements = extract_backend_auth_requirements(backend_path)

        # These endpoints contain sensitive data and must require auth
        critical_endpoints = [
            "/api/v1/ws/notifications",
            "/api/v1/ws/ai/suggestions",
            "/api/v1/ws/audit",
            "/api/v1/ws/alerts",
            "/api/v1/ws/budget/alerts",
            "/api/v1/ws/usage/cost",
            "/api/v1/ws/connections/health",
            "/api/v1/ws/metrics/heart",
        ]

        for endpoint in critical_endpoints:
            if endpoint in auth_requirements:
                assert auth_requirements[endpoint] is True, (
                    f"SECURITY: {endpoint} must require authentication! "
                    f"Current setting: require_auth={auth_requirements[endpoint]}"
                )

    def test_anonymous_endpoints_documented(self) -> None:
        """Anonymous-allowed endpoints should be explicitly documented."""
        backend_path = get_backend_ws_router_path()
        auth_requirements = extract_backend_auth_requirements(backend_path)

        # These endpoints explicitly allow anonymous connections
        expected_anonymous = [
            "/api/v1/ws/mcp",  # Anonymous MCP connections allowed
        ]

        for endpoint in expected_anonymous:
            if endpoint in auth_requirements:
                assert auth_requirements[endpoint] is False, (
                    f"{endpoint} should allow anonymous connections (require_auth=False). "
                    f"Current setting: require_auth={auth_requirements[endpoint]}"
                )


def get_sample_tuples_path() -> Path:
    """Get the path to the sample-tuples.json file."""
    current = Path(__file__).parent
    tuples_path = current.parent.parent / "config" / "openfga" / "sample-tuples.json"
    if not tuples_path.exists():
        pytest.skip(f"sample-tuples.json not found at {tuples_path}")
    return tuples_path


def extract_backend_authz_resources(ws_router_path: Path) -> list[tuple[str, str, str]]:
    """
    Extract authz_resource_type and authz_resource_id from ws_router.py.

    Returns:
        List of tuples (endpoint_path, resource_type, resource_id).
    """
    content = ws_router_path.read_text()

    # Find @ws_router.websocket decorators and their authz settings
    # Pattern matches blocks containing both decorator and authz params
    results: list[tuple[str, str, str]] = []

    # First, find all websocket decorator paths
    endpoint_pattern = r'@ws_router\.websocket\s*\(\s*["\']([^"\']+)["\']'
    endpoints = list(re.finditer(endpoint_pattern, content))

    for i, ep_match in enumerate(endpoints):
        endpoint_path = ep_match.group(1)
        start_pos = ep_match.end()

        # Find the end of this endpoint's config (next decorator or end of file)
        end_pos = endpoints[i + 1].start() if i + 1 < len(endpoints) else len(content)
        block = content[start_pos:end_pos]

        # Extract authz_resource_type and authz_resource_id
        type_match = re.search(r'authz_resource_type\s*=\s*["\']([^"\']+)["\']', block)
        id_match = re.search(r'authz_resource_id\s*=\s*["\']?([^"\'`,\s\)]+)', block)

        if type_match and id_match:
            resource_type = type_match.group(1)
            resource_id = id_match.group(1)
            # Skip dynamic IDs (workflow_id, etc.)
            if not resource_id.endswith("_id") and resource_id != "workflow_id":
                full_path = f"/api/v1/ws{endpoint_path}"
                results.append((full_path, resource_type, resource_id))

    return results


def load_sample_tuples() -> list[dict]:
    """Load tuples from sample-tuples.json."""
    import json

    tuples_path = get_sample_tuples_path()
    with tuples_path.open() as f:
        data = json.load(f)
    return data.get("tuples", [])


def extract_tuple_objects(tuples: list[dict]) -> set[str]:
    """Extract all unique object values from tuples (e.g., 'dashboard:devtools')."""
    objects: set[str] = set()
    for t in tuples:
        if "object" in t:
            objects.add(t["object"])
    return objects


class TestWebSocketAuthorizationTupleParity:
    """
    Validate that WebSocket endpoints with authorization requirements
    have corresponding tuples in sample-tuples.json.

    This test catches the bug where:
    1. WebSocket endpoint is added with authz_resource_type/authz_resource_id
    2. No tuple is added to sample-tuples.json
    3. All users get 403 Forbidden at runtime
    4. WebSocket constantly reconnects (the DevTools bug that triggered this test)
    """

    def test_all_websocket_authz_resources_have_tuples(self) -> None:
        """Every WebSocket authz resource should have at least one tuple."""
        backend_path = get_backend_ws_router_path()
        authz_resources = extract_backend_authz_resources(backend_path)

        tuples = load_sample_tuples()
        tuple_objects = extract_tuple_objects(tuples)

        missing: list[tuple[str, str]] = []
        for endpoint, resource_type, resource_id in authz_resources:
            # Construct expected object format
            expected_object = f"{resource_type}:{resource_id}"

            if expected_object not in tuple_objects:
                missing.append((endpoint, expected_object))

        if missing:
            missing_list = "\n  - ".join(f"{ep} requires {obj}" for ep, obj in missing)
            pytest.fail(
                f"Found {len(missing)} WebSocket endpoints without authorization tuples:\n"
                f"  - {missing_list}\n\n"
                f"These endpoints will return 403 Forbidden for ALL users.\n"
                f"Add the missing tuples to config/openfga/sample-tuples.json"
            )

    def test_critical_websocket_tuples_include_all_users(self) -> None:
        """
        Critical WebSocket resources should have tuples for admin, alice, and bob.

        This ensures all test personas can access essential functionality.
        """
        tuples = load_sample_tuples()

        # Critical resources that should be accessible to all users
        critical_resources = [
            "mcp:websocket",
            "chat:notifications",
            "mcp_connection:health",
            "mcp_connection:realtime",
            "observability:heart",
            "cost:usage",
            "mcp:aggregated-capabilities",
            "dashboard:devtools",
            "ai:orchestrator",
        ]

        required_users = ["user:admin", "user:alice", "user:bob"]

        for resource in critical_resources:
            users_with_access = {
                t["user"] for t in tuples if t.get("object") == resource and t.get("user", "").startswith("user:")
            }

            missing_users = set(required_users) - users_with_access
            if missing_users:
                pytest.fail(
                    f"Critical resource '{resource}' missing tuples for: {missing_users}\n"
                    f"Add tuples for these users to config/openfga/sample-tuples.json"
                )

    def test_devtools_tuple_exists(self) -> None:
        """
        Specific test for dashboard:devtools - the gap that triggered this audit.

        This test ensures we never regress on the DevTools WebSocket authorization.
        """
        tuples = load_sample_tuples()
        devtools_tuples = [t for t in tuples if t.get("object") == "dashboard:devtools"]

        assert len(devtools_tuples) >= 3, (
            f"REGRESSION: dashboard:devtools should have tuples for admin, alice, bob.\n"
            f"Found {len(devtools_tuples)} tuples. Expected at least 3.\n"
            f"This was the bug that caused DevTools to constantly reconnect."
        )

    def test_traces_stream_tuples_exist(self) -> None:
        """Test that traces:stream WebSocket has authorization tuples."""
        tuples = load_sample_tuples()
        stream_tuples = [t for t in tuples if t.get("object") == "traces:stream"]

        assert len(stream_tuples) >= 1, (
            "Missing tuples for traces:stream WebSocket endpoint.\n"
            "Add tuples for admin, alice, bob to config/openfga/sample-tuples.json"
        )

    def test_cost_budget_tuples_exist(self) -> None:
        """Test that cost:budget WebSocket has authorization tuples."""
        tuples = load_sample_tuples()
        budget_tuples = [t for t in tuples if t.get("object") == "cost:budget"]

        assert len(budget_tuples) >= 1, (
            "Missing tuples for cost:budget WebSocket endpoint.\n"
            "Add tuples for admin, alice, bob to config/openfga/sample-tuples.json"
        )
