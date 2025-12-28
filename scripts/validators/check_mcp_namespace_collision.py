#!/usr/bin/env python3
"""
Validation script to prevent MCP package namespace collision.

This script prevents `__init__.py` files from being created in test directories
that would shadow the installed `mcp` SDK package.

Background:
The `mcp` package (Model Context Protocol SDK) is an installed dependency.
If `tests/unit/mcp/__init__.py` exists, Python's import system may resolve
`import mcp` to the test directory instead of the installed package, causing:
- ImportError: No module named 'mcp.server'
- Mock pollution from conftest.py being loaded unexpectedly
- Test failures that only appear when running the full test suite

Forbidden paths:
- tests/unit/mcp/__init__.py
- tests/unit/mcp/client/__init__.py
- tests/unit/mcp/websocket/__init__.py (if using real mcp.websocket)

Usage:
    python scripts/validators/check_mcp_namespace_collision.py [file1 file2 ...]

Exit codes:
    0: No forbidden files found
    1: Forbidden __init__.py files detected

See: ADR-0073 for MCP WebSocket migration details
"""

import sys
from pathlib import Path

# Paths that would cause namespace collision with installed mcp package
FORBIDDEN_INIT_FILES = [
    "tests/unit/mcp/__init__.py",
    "tests/unit/mcp/client/__init__.py",
    # Note: tests/unit/mcp/websocket/ is for our mcp_server_langgraph.mcp.websocket
    # tests, not the mcp SDK, so __init__.py there is less problematic.
    # But we still forbid it to be safe.
    "tests/unit/mcp/websocket/__init__.py",
]


def check_files(files_to_check: list[str], repo_root: Path) -> list[str]:
    """Check if any forbidden __init__.py files exist or are being added.

    Args:
        files_to_check: List of file paths to check (from pre-commit or CLI)
        repo_root: Repository root path

    Returns:
        List of violations (forbidden files that exist or are being added)
    """
    violations = []

    # Normalize forbidden paths
    forbidden_absolute = {repo_root / f for f in FORBIDDEN_INIT_FILES}

    for file_path in files_to_check:
        path = Path(file_path)
        if not path.is_absolute():
            path = repo_root / path

        if path in forbidden_absolute:
            violations.append(str(path.relative_to(repo_root)))

    return violations


def check_existing_files(repo_root: Path) -> list[str]:
    """Check if any forbidden __init__.py files currently exist.

    Args:
        repo_root: Repository root path

    Returns:
        List of existing forbidden files
    """
    violations = []

    for forbidden_path in FORBIDDEN_INIT_FILES:
        full_path = repo_root / forbidden_path
        if full_path.exists():
            violations.append(forbidden_path)

    return violations


def print_violations(violations: list[str]) -> None:
    """Print violations in a user-friendly format."""
    if not violations:
        return

    print("\n" + "=" * 70)
    print("MCP NAMESPACE COLLISION DETECTED")
    print("=" * 70)
    print(
        """
The following __init__.py files would shadow the installed 'mcp' SDK package:
"""
    )

    for v in violations:
        print(f"  - {v}")

    print(
        """
Why this matters:
  - The 'mcp' package (Model Context Protocol SDK) is an installed dependency
  - Having __init__.py in tests/unit/mcp/ makes Python treat it as a package
  - This causes 'import mcp.server' to fail with ImportError
  - Tests pass individually but fail when run together

Fix:
  - Delete the __init__.py file(s) listed above
  - Tests in these directories don't need __init__.py (pytest finds them anyway)

See: ADR-0073 for MCP WebSocket migration details
"""
    )
    print("=" * 70 + "\n")


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent

    if len(sys.argv) > 1:
        # Pre-commit mode: check specific files being committed
        files_to_check = sys.argv[1:]
        violations = check_files(files_to_check, repo_root)
    else:
        # Standalone mode: check if forbidden files exist
        violations = check_existing_files(repo_root)

    print_violations(violations)

    if violations:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
