"""
Meta-test for Router Registration Completeness.

Validates that all routers defined in api/v1/*.py files are properly
registered in the main v1_router via include_router() calls.

This test catches the common bug where a router file is created and
imported but never actually registered, leading to 404 errors at runtime.

Why this matters:
- Router files can exist with fully implemented endpoints
- They can be imported in router.py
- But if include_router() is never called, endpoints are invisible
- No existing tests catch this gap - endpoints just return 404
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = pytest.mark.meta


class RouterDefinition(NamedTuple):
    """A router defined in a source file."""

    file_path: Path
    variable_name: str
    has_prefix: bool


class RouterImport(NamedTuple):
    """A router imported in router.py."""

    module_path: str
    original_name: str
    alias: str | None


class RouterInclusion(NamedTuple):
    """A router included via include_router()."""

    router_name: str
    has_prefix: bool


# Files that use factory patterns or are intentionally not auto-registered
EXCLUDED_FILES = {
    # Uses create_marketplace_router() factory pattern requiring DI
    "marketplace_admin.py",
    # Main router file itself
    "router.py",
    # WebSocket-only routers consolidated in ws_router (ADR-0068)
    # Note: Deprecated files (agent_request_websocket, alert_websocket, audit_websocket,
    # connection_health_ws, mcp_task_websocket, workflow_execution_ws) have been removed
    "connections_realtime_ws.py",
    "cost_tracking_ws.py",
    "heart_metrics_ws.py",
    # ws_router is included directly, its handlers are internal
    "ws_router.py",
}

# Routers that are intentionally not in v1_router (registered elsewhere)
EXCLUDED_ROUTERS = {
    # Registered in ws_router, not v1_router directly
    "mcp_task_ws_router",
    "connection_health_router",
}


def get_api_v1_path() -> Path:
    """Get the path to the api/v1 directory."""
    # Navigate from tests/meta to src/mcp_server_langgraph/api/v1
    current = Path(__file__).parent
    src_root = current.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1"
    if not src_root.exists():
        pytest.skip(f"API v1 directory not found at {src_root}")
    return src_root


def find_router_definitions(api_v1_path: Path) -> list[RouterDefinition]:
    """Find all APIRouter definitions in api/v1/*.py files."""
    routers: list[RouterDefinition] = []

    for py_file in api_v1_path.glob("*.py"):
        if py_file.name in EXCLUDED_FILES:
            continue

        content = py_file.read_text()

        # Pattern: variable_name = APIRouter(...)
        # Captures the variable name and checks for prefix= argument
        pattern = r"^(\w+)\s*=\s*APIRouter\s*\("
        for match in re.finditer(pattern, content, re.MULTILINE):
            var_name = match.group(1)
            # Check if this definition includes a prefix
            # Look ahead for prefix= in the same APIRouter call
            start = match.end()
            # Find matching closing paren
            paren_count = 1
            end = start
            while paren_count > 0 and end < len(content):
                if content[end] == "(":
                    paren_count += 1
                elif content[end] == ")":
                    paren_count -= 1
                end += 1

            router_call = content[start:end]
            has_prefix = "prefix=" in router_call

            routers.append(
                RouterDefinition(
                    file_path=py_file,
                    variable_name=var_name,
                    has_prefix=has_prefix,
                )
            )

    return routers


def parse_router_imports(router_py_path: Path) -> list[RouterImport]:
    """Parse all router imports from router.py."""
    content = router_py_path.read_text()
    tree = ast.parse(content)

    imports: list[RouterImport] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "mcp_server_langgraph.api.v1" in node.module:
                for alias in node.names:
                    # Check if this looks like a router import
                    name = alias.name
                    asname = alias.asname
                    if "router" in name.lower() or (asname and "router" in asname.lower()):
                        imports.append(
                            RouterImport(
                                module_path=node.module,
                                original_name=name,
                                alias=asname,
                            )
                        )

    return imports


def parse_router_inclusions(router_py_path: Path) -> list[RouterInclusion]:
    """Parse all include_router() calls from router.py."""
    content = router_py_path.read_text()

    inclusions: list[RouterInclusion] = []

    # Pattern: v1_router.include_router(router_name, ...)
    pattern = r"v1_router\.include_router\s*\(\s*(\w+)"
    for match in re.finditer(pattern, content):
        router_name = match.group(1)
        # Check if this include has a prefix argument
        # Look ahead for the full call
        start = match.start()
        end = content.find(")", start) + 1
        call_text = content[start:end]
        has_prefix = "prefix=" in call_text

        inclusions.append(
            RouterInclusion(
                router_name=router_name,
                has_prefix=has_prefix,
            )
        )

    return inclusions


@pytest.mark.meta
@pytest.mark.unit
class TestRouterRegistrationCompleteness:
    """Validate that all defined routers are properly registered."""

    def test_all_imported_routers_are_included(self) -> None:
        """Every router imported in router.py must have a corresponding include_router() call."""
        api_v1_path = get_api_v1_path()
        router_py = api_v1_path / "router.py"

        imports = parse_router_imports(router_py)
        inclusions = parse_router_inclusions(router_py)

        # Build set of included router names
        included_names = {inc.router_name for inc in inclusions}

        # Check each import
        missing = []
        for imp in imports:
            # The name used in include_router is either the alias or original name
            expected_name = imp.alias if imp.alias else imp.original_name
            if expected_name not in included_names and expected_name not in EXCLUDED_ROUTERS:
                missing.append(f"{imp.original_name} (as {expected_name})")

        assert not missing, (
            f"The following routers are imported but not included via v1_router.include_router():\n"
            f"  - {chr(10).join(missing)}\n\n"
            f"This will cause 404 errors for their endpoints. "
            f"Add v1_router.include_router({missing[0].split()[0]}) to router.py"
        )

    def test_all_router_files_have_router_imported(self) -> None:
        """Every router file should have its router imported in router.py."""
        api_v1_path = get_api_v1_path()
        router_py = api_v1_path / "router.py"

        # Find all router definitions
        definitions = find_router_definitions(api_v1_path)

        # Parse imports from router.py
        imports = parse_router_imports(router_py)
        router_py_content = router_py.read_text()

        # Build set of imported module files
        imported_files: set[str] = set()
        for imp in imports:
            # Extract filename from module path like mcp_server_langgraph.api.v1.features
            if imp.module_path:
                parts = imp.module_path.split(".")
                if parts:
                    imported_files.add(parts[-1] + ".py")

        # Check each router definition
        not_imported = []
        for defn in definitions:
            filename = defn.file_path.name
            if filename not in imported_files and filename not in EXCLUDED_FILES:
                # Double-check by looking for any import from this module
                module_name = filename.replace(".py", "")
                if f"from mcp_server_langgraph.api.v1.{module_name}" not in router_py_content:
                    not_imported.append(f"{filename}:{defn.variable_name}")

        assert not not_imported, (
            f"The following router files are not imported in router.py:\n"
            f"  - {chr(10).join(not_imported)}\n\n"
            f"Add: from mcp_server_langgraph.api.v1.<module> import <router>"
        )

    def test_no_duplicate_router_inclusions(self) -> None:
        """Each router should only be included once."""
        api_v1_path = get_api_v1_path()
        router_py = api_v1_path / "router.py"

        inclusions = parse_router_inclusions(router_py)

        # Count occurrences
        counts: dict[str, int] = {}
        for inc in inclusions:
            counts[inc.router_name] = counts.get(inc.router_name, 0) + 1

        duplicates = [name for name, count in counts.items() if count > 1]

        assert not duplicates, (
            f"The following routers are included multiple times:\n"
            f"  - {', '.join(duplicates)}\n\n"
            f"Remove duplicate v1_router.include_router() calls"
        )

    def test_router_count_sanity_check(self) -> None:
        """Sanity check that we have a reasonable number of routers."""
        api_v1_path = get_api_v1_path()
        router_py = api_v1_path / "router.py"

        inclusions = parse_router_inclusions(router_py)

        # We expect at least 30 routers based on current codebase
        # This catches accidental mass deletions
        assert len(inclusions) >= 30, (
            f"Only {len(inclusions)} routers are included. Expected at least 30. Did something get accidentally removed?"
        )

        # We expect no more than 100 routers (sanity upper bound)
        assert len(inclusions) <= 100, f"{len(inclusions)} routers included. This seems excessive - consider consolidating."
