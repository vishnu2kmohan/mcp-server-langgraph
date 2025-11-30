#!/usr/bin/env python3
"""
Pre-commit hook: Check test environment isolation patterns.

Detects direct os.environ mutations in test files and suggests using
monkeypatch.setenv() or centralized fixtures instead.

This prevents environment variable pollution in pytest-xdist workers.

References:
- OpenAI Codex Finding: 15+ test files with direct os.environ mutations (RESOLVED)
- tests/meta/test_environment_isolation_enforcement.py
- tests/conftest.py: disable_auth_skip, isolated_environment fixtures
"""

import re
import sys
from pathlib import Path


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """
    Check a test file for direct os.environ mutations.

    Returns:
        List of (line_number, line_content) tuples for violations
    """
    violations = []

    # Only check test files
    if not file_path.name.startswith("test_") and not file_path.name.endswith("_test.py"):
        return violations

    # Skip conftest.py (fixtures are allowed to set env vars)
    if file_path.name == "conftest.py":
        return violations

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, start=1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Detect os.environ[...] = ...
            if re.search(r"os\.environ\[.*\]\s*=", line):
                violations.append((i, line.strip()))

            # Detect os.environ.pop/del without try/finally or teardown context
            # (This is a simplified check - full implementation would need AST parsing)

    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)

    return violations


def main() -> int:
    """Main entry point."""
    files_to_check = sys.argv[1:]

    if not files_to_check:
        return 0

    all_violations = []

    for file_str in files_to_check:
        file_path = Path(file_str)
        if file_path.suffix == ".py" and "tests/" in str(file_path):
            violations = check_file(file_path)
            if violations:
                all_violations.append((file_path, violations))

    if all_violations:
        print("❌ Environment isolation violations detected:\n")

        for file_path, violations in all_violations:
            print(f"File: {file_path}")
            for line_num, line_content in violations:
                print(f"  Line {line_num}: {line_content}")
            print()

        print("💡 Suggested fixes:\n")
        print("  1. Use centralized fixtures:")
        print("     - disable_auth_skip: For MCP_SKIP_AUTH=false")
        print("     - isolated_environment: For general env isolation\n")
        print("  2. Or use monkeypatch.setenv() (auto-cleanup):\n")
        print("     def test_something(self, monkeypatch):")
        print('         monkeypatch.setenv("MCP_SKIP_AUTH", "false")')
        print("         # Auto-cleanup after test\n")
        print("📖 Documentation:")
        print("   - tests/meta/test_environment_isolation_enforcement.py")
        print("   - tests/conftest.py (disable_auth_skip, isolated_environment)\n")

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
