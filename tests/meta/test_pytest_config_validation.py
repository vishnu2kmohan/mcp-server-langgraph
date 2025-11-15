"""
Test that pytest configuration (addopts) is compatible with installed plugins.

This test validates the fix for the Codex finding where pytest addopts can
reference flags from plugins that are not installed, causing cryptic CI failures.

The validator checks that:
1. All flags in pytest.addopts have required plugin dependencies
2. All required plugins are actually installed
3. Changes to addopts or dependencies trigger validation

Reference: Codex finding - pytest addopts compatibility validation
"""

import gc
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]


def test_pytest_addopts_flags_have_required_plugins():
    """
    Verify that all pytest flags in addopts have required plugin dependencies.

    This prevents CI failures when someone:
    - Adds a flag to addopts without installing the plugin
    - Removes a plugin without removing dependent flags from addopts
    - Refactors dependencies and accidentally removes required plugins

    Expected mappings:
    - --dist, -n → pytest-xdist
    - --timeout → pytest-timeout
    - --cov → pytest-cov
    - --benchmark → pytest-benchmark
    """
    pyproject_path = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/pyproject.toml")

    assert pyproject_path.exists(), f"pyproject.toml not found: {pyproject_path}"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    # Get pytest addopts
    pytest_config = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    addopts = pytest_config.get("addopts", "")

    assert addopts, "pytest addopts not found in pyproject.toml"

    # Define plugin requirements for pytest flags
    # Flag → Required plugin
    plugin_requirements = {
        "--dist": "pytest-xdist",
        "-n": "pytest-xdist",
        "--timeout": "pytest-timeout",
        "--cov": "pytest-cov",
        "--benchmark": "pytest-benchmark",
    }

    # Extract all dev dependencies
    dev_deps = pyproject_data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    dep_groups_dev = pyproject_data.get("dependency-groups", {}).get("dev", [])
    all_dev_deps = dev_deps + dep_groups_dev

    # Normalize dependency names (handle version specifiers)
    installed_plugins = set()
    for dep in all_dev_deps:
        # Extract package name (before any comparison operators)
        pkg_name = dep.split("[")[0].split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip()
        installed_plugins.add(pkg_name.lower())

    # Check each flag in addopts
    missing_plugins = {}
    for flag, required_plugin in plugin_requirements.items():
        if flag in addopts:
            if required_plugin.lower() not in installed_plugins:
                missing_plugins[flag] = required_plugin

    assert not missing_plugins, (
        "pytest addopts uses flags that require missing plugins:\n"
        + "\n".join(f"  - {flag} requires {plugin}" for flag, plugin in missing_plugins.items())
        + f"\n\nCurrent addopts: {addopts}"
        + f"\n\nInstalled plugins: {sorted(installed_plugins)}"
        + "\n\nFix: Add missing plugins to project.optional-dependencies.dev in pyproject.toml"
    )


def test_validation_script_exists_and_is_executable():
    """
    Verify that the pytest config validation script exists and can be run.

    The validation script should be at: scripts/validate_pytest_config.py
    It should be executable and return exit code 0 when validation passes.
    """
    script_path = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/scripts/validate_pytest_config.py")

    assert script_path.exists(), (
        f"Validation script not found: {script_path}\n"
        "Expected: scripts/validate_pytest_config.py\n"
        "This script should validate pytest addopts against installed plugins."
    )

    # Verify script is a Python file
    assert script_path.suffix == ".py", f"Script must be a Python file, got: {script_path.suffix}"

    # Verify script can be executed
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=script_path.parent.parent,
    )

    assert result.returncode == 0, (
        f"Validation script failed with exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_all_pytest_flags_are_supported_by_installed_plugins():
    """
    Verify that pytest can recognize all flags in addopts.

    This is a smoke test that runs `pytest --help` and checks that
    all flags from addopts appear in the help output.

    This catches cases where:
    - A plugin is installed but the wrong flag is used
    - A flag is misspelled in addopts
    - A plugin is version-incompatible and doesn't provide expected flags
    """
    pyproject_path = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/pyproject.toml")

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    pytest_config = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    addopts = pytest_config.get("addopts", "")

    # Get pytest help output
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"pytest --help failed: {result.stderr}"

    help_output = result.stdout

    # Extract flags from addopts (anything starting with -)
    import re

    flags_in_addopts = re.findall(r"--?[\w-]+", addopts)

    # Check each flag appears in help output
    unsupported_flags = []
    for flag in flags_in_addopts:
        # Strip any values (e.g., --timeout=60 → --timeout)
        flag_name = flag.split("=")[0]

        if flag_name not in help_output:
            unsupported_flags.append(flag_name)

    assert not unsupported_flags, (
        "pytest addopts contains unsupported flags (not found in pytest --help):\n"
        + "\n".join(f"  - {flag}" for flag in unsupported_flags)
        + f"\n\nCurrent addopts: {addopts}"
        + "\n\nPossible causes:"
        + "\n  1. Flag is misspelled"
        + "\n  2. Required plugin is not installed"
        + "\n  3. Plugin version doesn't support this flag"
        + "\n\nRun: uv run pytest --help | grep <flag> to verify"
    )


def test_pre_commit_hook_validates_pytest_config():
    """
    Verify that pre-commit hook is configured to validate pytest config.

    This ensures that changes to pyproject.toml trigger validation
    before they can be committed.
    """
    pre_commit_config = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.pre-commit-config.yaml")

    assert pre_commit_config.exists(), ".pre-commit-config.yaml not found"

    with open(pre_commit_config) as f:
        config_content = f.read()

    # Check for pytest config validation hook
    assert "validate-pytest-config" in config_content or "validate_pytest_config" in config_content, (
        "Pre-commit hook for pytest config validation not found in .pre-commit-config.yaml\n"
        "Expected hook ID: validate-pytest-config\n"
        "This hook should run scripts/validate_pytest_config.py on pyproject.toml changes"
    )

    # Verify it targets pyproject.toml
    assert "pyproject.toml" in config_content or "pyproject\\.toml" in config_content, (
        "Pre-commit hook should target pyproject.toml\n" "Add: files: ^pyproject\\.toml$ to the hook configuration"
    )


def test_ci_workflow_validates_pytest_config():
    """
    Verify that CI workflow includes pytest config validation.

    This ensures validation runs in CI even if pre-commit hooks are bypassed.
    """
    ci_workflows = [
        Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.github/workflows/ci.yaml"),
        Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.github/workflows/quality-tests.yaml"),
        Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.github/workflows/validate-workflows.yaml"),
    ]

    validation_found = False
    for workflow_path in ci_workflows:
        if not workflow_path.exists():
            continue

        with open(workflow_path) as f:
            workflow_content = f.read()

        # Check if this workflow validates pytest config
        if "validate_pytest_config" in workflow_content or "validate-pytest-config" in workflow_content:
            validation_found = True
            break

    assert validation_found, (
        "No CI workflow validates pytest config\n"
        "Expected: ci.yaml, quality-tests.yaml, or validate-workflows.yaml\n"
        "Should include step: uv run python scripts/validate_pytest_config.py\n"
        "This ensures validation runs even if pre-commit hooks are bypassed"
    )


def test_pytest_plugins_are_actually_importable():
    """
    Verify that all required pytest plugins can be imported.

    This is a runtime check that the plugins are not only listed in
    dependencies but are actually installed and importable.
    """
    # Note: Package names (pip install) vs import names are different
    # pytest-xdist → import xdist
    # pytest-timeout → import pytest_timeout
    # pytest-cov → import pytest_cov
    required_plugins = [
        ("xdist", "--dist flag support (from pytest-xdist)"),
        ("pytest_timeout", "--timeout flag support (from pytest-timeout)"),
        ("pytest_cov", "--cov flag support (from pytest-cov)"),
    ]

    import_errors = []
    for module_name, description in required_plugins:
        try:
            __import__(module_name)
        except ImportError as e:
            import_errors.append(f"  - {module_name}: {description} - {e}")

    assert not import_errors, (
        "Required pytest plugins cannot be imported:\n"
        + "\n".join(import_errors)
        + "\n\nFix: uv sync --all-extras to install all dependencies"
    )
