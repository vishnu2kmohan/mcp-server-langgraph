#!/usr/bin/env python3
"""
Validate pytest configuration (addopts) against installed plugins.

This script prevents CI failures caused by pytest addopts referencing flags
from plugins that are not installed in the environment.

Common failure scenario:
1. Developer adds --timeout to pytest addopts
2. Developer forgets to add pytest-timeout to dependencies
3. CI runs pytest and fails with: "pytest: error: unrecognized arguments: --timeout"
4. Build breaks without clear indication of the root cause

This validator:
- Parses pytest addopts from pyproject.toml
- Maps flags to required plugin dependencies
- Checks that all required plugins are installed
- Exits with code 1 if any plugins are missing

Usage:
    python scripts/validate_pytest_config.py

Exit codes:
    0 - All pytest addopts flags have required plugins installed
    1 - One or more required plugins are missing

Reference: Codex finding - pytest addopts compatibility validation
"""

import sys
import tomllib
from pathlib import Path

# Map pytest flags to required plugin packages
# Flag → Required package name (as in pyproject.toml dependencies)
PLUGIN_REQUIREMENTS = {
    "--dist": "pytest-xdist",
    "-n": "pytest-xdist",
    "--timeout": "pytest-timeout",
    "--cov": "pytest-cov",
    "--cov-report": "pytest-cov",
    "--benchmark": "pytest-benchmark",
    "--benchmark-only": "pytest-benchmark",
    "--hypothesis": "hypothesis",
    "--schemathesis": "schemathesis",
}


def load_pyproject_toml(repo_root: Path) -> dict:
    """Load and parse pyproject.toml."""
    pyproject_path = repo_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"❌ pyproject.toml not found at: {pyproject_path}", file=sys.stderr)
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def get_pytest_addopts(pyproject_data: dict) -> str:
    """Extract pytest addopts from pyproject.toml."""
    pytest_config = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    addopts = pytest_config.get("addopts", "")

    if not addopts:
        print("⚠️  No pytest addopts found in pyproject.toml", file=sys.stderr)
        return ""

    return addopts


def get_installed_plugins(pyproject_data: dict) -> set[str]:
    """
    Extract all installed plugin package names from dependencies.

    Checks both:
    - project.optional-dependencies.dev
    - dependency-groups.dev
    """
    dev_deps = pyproject_data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    dep_groups_dev = pyproject_data.get("dependency-groups", {}).get("dev", [])

    all_deps = dev_deps + dep_groups_dev

    # Normalize package names (strip version specifiers)
    installed = set()
    for dep in all_deps:
        # Extract package name before any version specifiers
        # Examples:
        #   "pytest-timeout>=2.2.0" → "pytest-timeout"
        #   "pytest-xdist[psutil]>=3.0" → "pytest-xdist"
        pkg_name = dep.split("[")[0].split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip()
        installed.add(pkg_name.lower())

    return installed


def validate_pytest_config(repo_root: Path) -> tuple[bool, list[tuple[str, str]]]:
    """
    Validate that all pytest addopts flags have required plugins installed.

    Args:
        repo_root: Path to repository root

    Returns:
        Tuple of (is_valid, missing_plugins)
        - is_valid: True if all required plugins are installed
        - missing_plugins: List of (flag, required_plugin) tuples for missing plugins
    """
    pyproject_data = load_pyproject_toml(repo_root)
    addopts = get_pytest_addopts(pyproject_data)

    if not addopts:
        # No addopts configured - nothing to validate
        return True, []

    installed_plugins = get_installed_plugins(pyproject_data)

    # Check each flag in addopts
    missing_plugins = []
    for flag, required_plugin in PLUGIN_REQUIREMENTS.items():
        if flag in addopts:
            if required_plugin.lower() not in installed_plugins:
                missing_plugins.append((flag, required_plugin))

    is_valid = len(missing_plugins) == 0
    return is_valid, missing_plugins


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent

    print("🔍 Validating pytest configuration...")
    print(f"   Repository: {repo_root}")

    is_valid, missing_plugins = validate_pytest_config(repo_root)

    if is_valid:
        print("✅ All pytest addopts flags have required plugins installed")
        return 0

    # Print detailed error message
    print("\n❌ pytest addopts validation FAILED", file=sys.stderr)
    print("\nMissing required plugins:", file=sys.stderr)

    for flag, plugin in missing_plugins:
        print(f"  - Flag '{flag}' requires plugin: {plugin}", file=sys.stderr)

    print("\n📝 Fix instructions:", file=sys.stderr)
    print("  1. Add missing plugins to pyproject.toml [project.optional-dependencies.dev]", file=sys.stderr)
    print("  2. Run: uv sync --all-extras", file=sys.stderr)
    print("  3. Verify: uv run pytest --help | grep <flag>", file=sys.stderr)

    print("\nAlternatively, if the flag is no longer needed:", file=sys.stderr)
    print("  - Remove the flag from [tool.pytest.ini_options] addopts", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
