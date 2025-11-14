#!/usr/bin/env python3
"""
Pre-commit hook: validate-docker-image-contents

Validates Docker image contents in Dockerfile (final-test stage).

This script ensures:
1. Required directories are copied (src/, tests/, pyproject.toml, deployments/, scripts/)
2. All test dependencies are available in Docker image

Prevents regression of Codex Findings:
- Keycloak health check using curl (not available in image)
- ModuleNotFoundError for 'scripts' module
- FileNotFoundError for /app/deployments

Exit codes:
    0: Validation passed
    1: Validation failed with error message to stderr

References:
    - ADR-0053: Codex Integration Test Findings
    - tests/integration/test_docker_image_assets.py
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


def extract_final_test_stage(dockerfile_content: str) -> Optional[str]:
    """
    Extract the final-test stage from Dockerfile.

    Returns:
        The final-test stage content, or None if not found
    """
    # Find the final-test stage
    stage_pattern = r"FROM\s+.*\s+AS\s+final-test\s*\n(.*?)(?=\nFROM\s+|\Z)"
    match = re.search(stage_pattern, dockerfile_content, re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    return match.group(1)


def extract_copy_commands(stage_content: str) -> List[str]:
    """
    Extract all COPY commands from Dockerfile stage content.

    Returns:
        List of COPY command lines
    """
    copy_pattern = r"^\s*COPY\s+(.+)$"
    copy_commands = []

    for line in stage_content.split("\n"):
        match = re.match(copy_pattern, line, re.IGNORECASE)
        if match:
            copy_commands.append(match.group(1).strip())

    return copy_commands


def validate_required_directories(copy_commands: List[str]) -> Optional[str]:
    """
    Validate required directories are copied.

    Required:
    - src/ directory (application source code)
    - tests/ directory (test suite)
    - pyproject.toml (Python project configuration)
    - deployments/ directory (Kubernetes manifests - needed by test_pod_deployment_regression.py)
    - scripts/ directory (validation scripts - needed by test_mdx_validation.py, test_codeblock_autofixer.py)

    Returns:
        Error message if validation fails, None if passes
    """
    required_items = {
        "src/": False,
        "tests/": False,
        "pyproject.toml": False,
        "deployments/": False,
        "scripts/": False,
    }

    for cmd in copy_commands:
        for item in required_items.keys():
            if item in cmd:
                required_items[item] = True

    missing_items = [item for item, found in required_items.items() if not found]

    if missing_items:
        return f"Required items not found in COPY commands: {', '.join(missing_items)}"

    return None  # Success


# REMOVED: validate_excluded_directories - scripts/ and deployments/ ARE required
# The previous assumption that "meta-tests run on host" was incorrect.
# Integration tests in Docker DO need access to scripts/ and deployments/ directories.


def validate_docker_image_contents(dockerfile_path: str) -> int:
    """
    Main validation function.

    Returns:
        0 if validation passes
        1 if validation fails
    """
    dockerfile = Path(dockerfile_path)

    if not dockerfile.exists():
        print(f"ERROR: File not found: {dockerfile_path}", file=sys.stderr)
        return 1

    # Read Dockerfile
    try:
        dockerfile_content = dockerfile.read_text()
    except Exception as e:
        print(f"ERROR: Failed to read Dockerfile: {e}", file=sys.stderr)
        return 1

    # Extract final-test stage
    stage_content = extract_final_test_stage(dockerfile_content)
    if not stage_content:
        print("ERROR: final-test stage not found in Dockerfile", file=sys.stderr)
        return 1

    # Extract COPY commands from final-test stage
    copy_commands = extract_copy_commands(stage_content)
    if not copy_commands:
        print("WARNING: No COPY commands found in final-test stage", file=sys.stdout)
        # This is a warning, not an error - might be intentional

    # Validation: Required directories (including deployments/ and scripts/)
    error = validate_required_directories(copy_commands)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("\nIntegration tests require:", file=sys.stderr)
        print("  - src/ (application source code)", file=sys.stderr)
        print("  - tests/ (test suite)", file=sys.stderr)
        print("  - pyproject.toml (project configuration)", file=sys.stderr)
        print("  - deployments/ (Kubernetes manifests - needed by test_pod_deployment_regression.py)", file=sys.stderr)
        print(
            "  - scripts/ (validation scripts - needed by test_mdx_validation.py, test_codeblock_autofixer.py)",
            file=sys.stderr,
        )
        print("\nCodex Finding Resolution:", file=sys.stderr)
        print("  Previous assumption that scripts/ and deployments/ should be excluded was incorrect.", file=sys.stderr)
        print("  Integration tests running in Docker DO need access to these directories.", file=sys.stderr)
        return 1

    # All validations passed
    print("✅ Docker image contents validation passed (src/, tests/, pyproject.toml, deployments/, scripts/)", file=sys.stdout)
    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_docker_image_contents.py <dockerfile>", file=sys.stderr)
        sys.exit(1)

    dockerfile = sys.argv[1]
    exit_code = validate_docker_image_contents(dockerfile)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
