#!/usr/bin/env python3
"""
Validate that .git/hooks/pre-push is configured correctly.

This script ensures that the pre-push hook:
1. Exists and is executable
2. Contains all required validation steps
3. Matches expected configuration

This prevents regressions where the pre-push hook might be accidentally
modified or removed, causing local validation to diverge from requirements.
"""

import os
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

    # Check 3: Required validation steps
    required_validations = {
        "uv lock --check": "Lockfile validation",
        "test_workflow_syntax.py": "Workflow syntax validation",
        "test_workflow_security.py": "Workflow security validation",
        "test_workflow_dependencies.py": "Workflow dependencies validation",
        "test_docker_paths.py": "Docker paths validation",
        "mypy src/mcp_server_langgraph": "MyPy type checking",
        "pre-commit run --all-files": "Pre-commit hooks (all files)",
        "HYPOTHESIS_PROFILE=ci": "Property tests with CI profile",
        "pytest -m property": "Property tests",
    }

    missing_validations = []
    for validation_cmd, description in required_validations.items():
        if validation_cmd not in content:
            missing_validations.append(f"   - {description} ({validation_cmd})")

    if missing_validations:
        errors.append(
            "❌ Pre-push hook is missing required validation steps:\n"
            + "\n".join(missing_validations)
            + "\n   Fix: Restore .git/hooks/pre-push from template or run 'make git-hooks'"
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
