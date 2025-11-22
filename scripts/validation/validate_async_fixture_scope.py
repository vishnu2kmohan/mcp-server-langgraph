#!/usr/bin/env python3
"""
Validate pytest-asyncio event loop scope configuration.

CODEX FINDING REGRESSION PREVENTION (2025-11-20):
Ensures asyncio_default_fixture_loop_scope is set to "session" to prevent
ScopeMismatch errors with session-scoped async fixtures.

This hook prevents regression of the fix for 34 failing integration tests.

References:
- pyproject.toml:471 - asyncio_default_fixture_loop_scope configuration
- tests/meta/test_codex_findings_validation.py::test_pytest_asyncio_event_loop_scope_matches_session_fixtures
"""

import sys
from pathlib import Path

try:
    import tomli
except ImportError:
    print("❌ Error: tomli package not installed (required for reading pyproject.toml)")
    print("   Install with: uv pip install tomli")
    sys.exit(1)


def main() -> int:
    """Validate async fixture scope configuration."""
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"❌ Error: pyproject.toml not found at {pyproject_path}")
        return 1

    with open(pyproject_path, "rb") as f:
        config = tomli.load(f)

    # Navigate to pytest configuration
    if "tool" not in config:
        print("❌ Error: No [tool] section in pyproject.toml")
        return 1

    if "pytest" not in config["tool"]:
        print("❌ Error: No [tool.pytest] section in pyproject.toml")
        return 1

    if "ini_options" not in config["tool"]["pytest"]:
        print("❌ Error: No [tool.pytest.ini_options] section in pyproject.toml")
        return 1

    pytest_config = config["tool"]["pytest"]["ini_options"]

    # Validate asyncio_default_fixture_loop_scope
    if "asyncio_default_fixture_loop_scope" not in pytest_config:
        print("❌ Error: asyncio_default_fixture_loop_scope not configured in pyproject.toml")
        print("   Required for session-scoped async fixtures to work with pytest-asyncio 1.2.0+")
        print("   Add to [tool.pytest.ini_options]:")
        print('   asyncio_default_fixture_loop_scope = "session"')
        return 1

    loop_scope = pytest_config["asyncio_default_fixture_loop_scope"]

    if loop_scope != "session":
        print(f"❌ Error: asyncio_default_fixture_loop_scope must be 'session', found '{loop_scope}'")
        print("")
        print("   Session-scoped async fixtures (postgres_connection_real, redis_client_real,")
        print("   openfga_client_real) require session-scoped event loop to prevent ScopeMismatch errors.")
        print("")
        print("   Fix: Change pyproject.toml [tool.pytest.ini_options]:")
        print(f'   asyncio_default_fixture_loop_scope = "{loop_scope}"  # ❌ WRONG')
        print('   asyncio_default_fixture_loop_scope = "session"      # ✅ CORRECT')
        print("")
        print("   References:")
        print("   - tests/conftest.py:1404 - postgres_connection_real (session-scoped)")
        print("   - tests/conftest.py:1453 - redis_client_real (session-scoped)")
        print("   - tests/conftest.py:1483 - openfga_client_real (session-scoped)")
        print("   - Codex Finding: 34 tests failed with ScopeMismatch before this fix")
        return 1

    print("✅ pytest-asyncio configuration is correct (asyncio_default_fixture_loop_scope = 'session')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
