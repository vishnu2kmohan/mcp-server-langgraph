#!/usr/bin/env python3
"""
Add comprehensive test execution hooks to .pre-commit-config.yaml

This script adds the missing comprehensive test suite hooks that match CI execution.
These hooks prevent the validation gap where individual test files pass but
comprehensive test suite fails.

Added: 2025-11-16 after discovering 141 tests not covered by pre-push hooks.
"""

import sys
from pathlib import Path

import yaml


def add_comprehensive_test_hooks():
    """Add comprehensive test hooks to pre-commit config."""
    repo_root = Path(__file__).parent.parent
    config_path = repo_root / ".pre-commit-config.yaml"

    # Load existing config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Find the local hooks repo
    local_repo = None
    for repo in config.get("repos", []):
        if repo.get("repo") == "local":
            local_repo = repo
            break

    if not local_repo:
        print("ERROR: Could not find 'local' repo in .pre-commit-config.yaml")
        return False

    # Check if hooks already exist
    existing_ids = {hook.get("id") for hook in local_repo.get("hooks", [])}
    if "run-unit-tests" in existing_ids:
        print("✅ Comprehensive test hooks already exist")
        return True

    # Define comprehensive test hooks
    comprehensive_hooks = [
        {
            "id": "run-unit-tests",
            "name": "Run Unit Tests (comprehensive suite)",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci uv run pytest -n auto -m \"unit and not llm\" tests/ -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/.*\.py|pyproject\.toml)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs comprehensive unit test suite to match CI exactly.\n"
            "\n"
            'Executes: pytest -n auto -m "unit and not llm" tests/\n'
            "- Parallel execution with pytest-xdist\n"
            "- OTEL_SDK_DISABLED=true (matches CI environment)\n"
            "- HYPOTHESIS_PROFILE=ci (100 examples for property tests)\n"
            "- Excludes LLM tests (require API keys)\n"
            "\n"
            "This hook prevents the validation gap where individual test files\n"
            "pass but comprehensive suite fails. Added 2025-11-16 after finding\n"
            "141 tests not covered by individual file hooks.\n",
        },
        {
            "id": "run-smoke-tests",
            "name": "Run Smoke Tests",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true uv run pytest -n auto tests/smoke/ -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/smoke/.*\.py)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs smoke tests to validate critical paths.\n",
        },
        {
            "id": "run-integration-tests",
            "name": "Run Integration Tests",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true uv run pytest -n auto tests/integration/ -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/integration/.*\.py)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs integration tests with real infrastructure.\n",
        },
        {
            "id": "run-api-tests",
            "name": "Run API Endpoint Tests",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true uv run pytest -n auto -m \"api and unit and not llm\" tests/ -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/api/.*\.py)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs API endpoint tests to match CI.\n"
            "\n"
            'Executes: pytest -n auto -m "api and unit and not llm"\n'
            "Prevents API regressions from reaching CI.\n",
        },
        {
            "id": "run-mcp-server-tests",
            "name": "Run MCP Server Tests",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true uv run pytest -n auto tests/unit/test_mcp_stdio_server.py -m \"not llm\" -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/unit/test_mcp_stdio_server\.py)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs MCP protocol server tests to match CI.\n" "\n" "Prevents MCP protocol regressions.\n",
        },
        {
            "id": "run-property-tests",
            "name": "Run Property-Based Tests",
            "entry": "bash -c 'OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci uv run pytest -n auto -m property tests/ -v --tb=short'",
            "language": "system",
            "pass_filenames": False,
            "files": r"^(src/.*\.py|tests/.*\.py)$",
            "always_run": False,
            "stages": ["pre-push"],
            "description": "Runs Hypothesis property-based tests with CI profile (100 examples).\n"
            "\n"
            "Executes: HYPOTHESIS_PROFILE=ci pytest -m property\n"
            "Validates code properties across many generated test cases.\n",
        },
    ]

    # Find insertion point (before validate-minimum-coverage hook)
    hooks = local_repo.get("hooks", [])
    insertion_index = None
    for i, hook in enumerate(hooks):
        if hook.get("id") == "validate-minimum-coverage":
            insertion_index = i
            break

    if insertion_index is None:
        # Append to end if we can't find the marker
        hooks.extend(comprehensive_hooks)
    else:
        # Insert before the marker
        for hook in reversed(comprehensive_hooks):
            hooks.insert(insertion_index, hook)

    # Save updated config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120)

    print(f"✅ Added {len(comprehensive_hooks)} comprehensive test hooks to .pre-commit-config.yaml")
    print("\nAdded hooks:")
    for hook in comprehensive_hooks:
        print(f"  - {hook['id']}")

    print("\nNext steps:")
    print("  1. Run: pre-commit install --hook-type pre-push")
    print("  2. Verify: python scripts/validate_pre_push_hook.py")

    return True


if __name__ == "__main__":
    success = add_comprehensive_test_hooks()
    sys.exit(0 if success else 1)
