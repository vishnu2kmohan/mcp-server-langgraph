#!/usr/bin/env python3
"""
WebSocket Endpoint Parity Validation Script.

Validates that all WebSocket endpoints defined in the frontend WS_ENDPOINTS
constant have corresponding backend implementations in ws_router.py.

This script is designed to run as a pre-commit hook to prevent frontend-backend
integration gaps from being introduced.

Exit codes:
    0 - All endpoints have matching implementations
    1 - Missing endpoints detected

Usage:
    python scripts/validation/check_websocket_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_frontend_ws_endpoints(project_root: Path) -> dict[str, str]:
    """
    Extract WS_ENDPOINTS from frontend websocket.ts.

    Returns:
        Dict mapping endpoint name to path (e.g., {"DEVTOOLS": "/api/v1/ws/devtools"})
    """
    ws_path = project_root / "src" / "mcp_server_langgraph" / "studio" / "frontend" / "src" / "utils" / "websocket.ts"

    if not ws_path.exists():
        print(f"WARNING: Frontend websocket.ts not found at {ws_path}")
        return {}

    content = ws_path.read_text()

    # Match WS_ENDPOINTS object entries
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


def get_backend_ws_endpoints(project_root: Path) -> set[str]:
    """
    Extract WebSocket endpoints from backend ws_router.py.

    Returns:
        Set of endpoint paths (e.g., {"/api/v1/ws/devtools", "/api/v1/ws/alerts"})
    """
    router_path = project_root / "src" / "mcp_server_langgraph" / "api" / "v1" / "ws_router.py"

    if not router_path.exists():
        print(f"WARNING: Backend ws_router.py not found at {router_path}")
        return set()

    content = router_path.read_text()

    # Match @ws_router.websocket("/path") decorators
    pattern = r'@ws_router\.websocket\s*\(\s*["\']([^"\']+)["\']'

    endpoints: set[str] = set()
    for match in re.finditer(pattern, content):
        relative_path = match.group(1)
        # Convert relative path to full path
        full_path = f"/api/v1/ws{relative_path}"
        endpoints.add(full_path)

    return endpoints


def normalize_ws_path(path: str) -> str:
    """
    Normalize WebSocket path for comparison.

    Converts path parameters to standard format:
    - /api/v1/ws/workflows/:workflowId -> /api/v1/ws/workflows/{id}
    """
    # Replace :param format with {id}
    result = re.sub(r":(\w+)", "{id}", path)
    # Replace {param_name} format with {id}
    result = re.sub(r"\{[^}]+\}", "{id}", result)
    return result


def main() -> int:
    """Run the WebSocket parity check."""
    project_root = get_project_root()

    print("Checking WebSocket endpoint parity...")

    frontend_endpoints = get_frontend_ws_endpoints(project_root)
    backend_endpoints = get_backend_ws_endpoints(project_root)

    if not frontend_endpoints:
        print("WARNING: No frontend WS_ENDPOINTS found")
        return 0

    if not backend_endpoints:
        print("WARNING: No backend WebSocket endpoints found")
        return 0

    # Normalize backend paths for comparison
    normalized_backend = {normalize_ws_path(ep) for ep in backend_endpoints}

    # Find missing endpoints
    missing: list[str] = []
    for name, path in frontend_endpoints.items():
        normalized_path = normalize_ws_path(path)
        if normalized_path not in normalized_backend:
            missing.append(f"  - {name}: {path}")

    if missing:
        print(f"\nERROR: Found {len(missing)} frontend WebSocket endpoints without backend handlers:\n")
        print("\n".join(missing))
        print(
            "\nThese endpoints will fail WebSocket connections at runtime.\n"
            "Add the missing handlers to src/mcp_server_langgraph/api/v1/ws_router.py\n"
            "or remove unused endpoints from frontend websocket.ts WS_ENDPOINTS."
        )
        return 1

    print(f"OK: All {len(frontend_endpoints)} frontend WebSocket endpoints have backend implementations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
