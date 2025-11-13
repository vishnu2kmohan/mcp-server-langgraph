#!/usr/bin/env python3
"""
Validate that .git/hooks/pre-push is configured correctly.

This script ensures that the pre-push hook:
1. Exists and is executable
2. Contains all required validation steps
3. Matches expected configuration with 4 phases:
   - Phase 1: Fast checks (lockfile, workflows)
   - Phase 2: Type checking (MyPy - warning only)
   - Phase 3: Test suite validation (unit, smoke, integration, property)
   - Phase 4: Pre-commit hooks (push stage - comprehensive validators)

This prevents regressions where the pre-push hook might be accidentally
modified or removed, causing local validation to diverge from requirements.

Updated 2025-11-13: Added comprehensive test suite validation to match CI exactly.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def get_repo_root() -> Path:
    """Get repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def check_pre_push_hook() -> Tuple[bool, List[str]]:
    """
    Validate pre-push hook configuration.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    repo_root = get_repo_root()
    pre_push_path = repo_root / ".git" / "hooks" / "pre-push"

    # Check 1: File exists
    if not pre_push_path.exists():
        errors.append(
            "❌ Pre-push hook does not exist at .git/hooks/pre-push\n"
            "   Fix: Run 'make git-hooks' or 'pre-commit install --hook-type pre-push'"
        )
        return False, errors

    # Check 2: Is executable
    if not os.access(pre_push_path, os.X_OK):
        errors.append(f"❌ Pre-push hook exists but is not executable\n" f"   Fix: chmod +x .git/hooks/pre-push")

    # Read hook content
    with open(pre_push_path, "r") as f:
        content = f.read()

    # Check 3: Required validation steps (using regex patterns to handle "uv run" wrappers)
    required_validations = {
        # Phase 1: Fast checks
        r"uv lock --check": "Lockfile validation",
        r"test_workflow_syntax\.py": "Workflow syntax validation",
        r"test_workflow_security\.py": "Workflow security validation",
        r"test_workflow_dependencies\.py": "Workflow dependencies validation",
        r"test_docker_paths\.py": "Docker paths validation",
        # Phase 2: Type checking
        r"(uv run )?mypy src/mcp_server_langgraph": "MyPy type checking",
        # Phase 3: Test suite validation (handles "uv run pytest" or just "pytest")
        r"(uv run )?pytest.*tests/.*-m.*unit": "Unit tests",
        r"(uv run )?pytest.*tests/smoke/": "Smoke tests",
        r"(uv run )?pytest.*tests/integration/": "Integration tests",
        r"(uv run )?pytest.*-m.*['\"]api and unit": "API endpoint tests",
        r"(uv run )?pytest.*test_mcp_stdio_server\.py": "MCP server tests",
        r"HYPOTHESIS_PROFILE=ci": "Property tests with CI profile",
        r"(uv run )?pytest.*-m.*property": "Property tests",
        r"(uv run )?pytest.*test_pytest_xdist_enforcement\.py": "pytest-xdist enforcement meta-tests",
        # Phase 4: Pre-commit hooks (push stage)
        r"pre-commit run --all-files.*--hook-stage push": "Pre-commit hooks (push stage)",
    }

    missing_validations = []
    for validation_pattern, description in required_validations.items():
        if not re.search(validation_pattern, content):
            missing_validations.append(f"   - {description} (pattern: {validation_pattern})")

    if missing_validations:
        errors.append(
            "❌ Pre-push hook is missing required validation steps:\n"
            + "\n".join(missing_validations)
            + "\n   Fix: Restore .git/hooks/pre-push from template or run 'make git-hooks'"
        )

    # Check 4: Parallel execution with pytest-xdist (-n auto)
    # All test commands should use -n auto to match CI and catch isolation bugs
    pytest_commands = [
        ("Unit tests", "pytest tests/ -m", "-n auto"),
        ("Smoke tests", "pytest tests/smoke/", "-n auto"),
        ("Integration tests", "pytest tests/integration/", "-n auto"),
        ("API tests", "pytest -n auto -m 'api", "-n auto"),
        ("MCP tests", "test_mcp_stdio_server.py", "-n auto"),
        ("Property tests", "pytest -m property", "-n auto"),
    ]

    missing_n_auto = []
    for test_name, test_cmd, flag in pytest_commands:
        # Find lines containing the test command
        lines = [line for line in content.split("\n") if test_cmd in line]
        if lines:
            # Check if any of those lines have -n auto
            if not any(flag in line for line in lines):
                missing_n_auto.append(f"   - {test_name} (missing '-n auto')")

    if missing_n_auto:
        errors.append(
            "❌ Pre-push hook must use '-n auto' for parallel execution to match CI:\n"
            + "\n".join(missing_n_auto)
            + "\n   Fix: Add '-n auto' to all pytest commands in .git/hooks/pre-push"
        )

    # Check 5: OTEL_SDK_DISABLED=true environment variable
    # All test commands should set this to match CI environment
    otel_commands = [
        ("Unit tests", "pytest tests/ -m", "OTEL_SDK_DISABLED=true"),
        ("Smoke tests", "pytest tests/smoke/", "OTEL_SDK_DISABLED=true"),
        ("Integration tests", "pytest tests/integration/", "OTEL_SDK_DISABLED=true"),
        ("API tests", "pytest -n auto -m 'api", "OTEL_SDK_DISABLED=true"),
        ("MCP tests", "test_mcp_stdio_server.py", "OTEL_SDK_DISABLED=true"),
        ("Property tests", "pytest -m property", "OTEL_SDK_DISABLED=true"),
    ]

    missing_otel = []
    for test_name, test_cmd, env_var in otel_commands:
        # Find lines containing the test command
        lines = [line for line in content.split("\n") if test_cmd in line]
        if lines:
            # Check if any of those lines have OTEL_SDK_DISABLED=true
            if not any(env_var in line for line in lines):
                missing_otel.append(f"   - {test_name} (missing 'OTEL_SDK_DISABLED=true')")

    if missing_otel:
        errors.append(
            "❌ Pre-push hook must set 'OTEL_SDK_DISABLED=true' to match CI environment:\n"
            + "\n".join(missing_otel)
            + "\n   Fix: Add 'OTEL_SDK_DISABLED=true' to all pytest commands in .git/hooks/pre-push"
        )

    # Check 4: Has proper structure (phases)
    required_phases = ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4"]
    missing_phases = [phase for phase in required_phases if phase not in content]

    if missing_phases:
        errors.append(
            "⚠️  Pre-push hook is missing clear phase markers:\n"
            + "\n".join(f"   - {phase}" for phase in missing_phases)
            + "\n   This may indicate the hook has been modified"
        )

    # Check 5: Has helpful error messages
    if "--no-verify" not in content:
        errors.append("⚠️  Pre-push hook should document emergency bypass (--no-verify)")

    return len(errors) == 0, errors


def main() -> int:
    """Main validation function."""
    try:
        is_valid, errors = check_pre_push_hook()

        if is_valid:
            print("✅ Pre-push hook configuration is valid")
            return 0
        else:
            print("Pre-push Hook Validation Failed")
            print("=" * 60)
            for error in errors:
                print(error)
                print()

            print("=" * 60)
            print("\n💡 Quick Fix:")
            print("   make git-hooks")
            print("\nOr manually:")
            print("   pre-commit install --hook-type pre-commit --hook-type pre-push")
            print()

            return 1

    except Exception as e:
        print(f"❌ Error validating pre-push hook: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
