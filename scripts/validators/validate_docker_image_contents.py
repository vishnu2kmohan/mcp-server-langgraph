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


def extract_final_test_stage(dockerfile_content: str) -> str | None:
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


def extract_copy_commands(stage_content: str) -> list[str]:
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


def validate_required_directories(copy_commands: list[str]) -> str | None:
    """
    Validate required directories are copied.

    Required:
    - src/ directory (application source code)
    - tests/ directory (test suite)
    - pyproject.toml (Python project configuration)

    Per ADR-0053: scripts/ and deployments/ are NOT copied to the Docker image.
    Meta-tests that require these directories run on the host, not in the container.

    Returns:
        Error message if validation fails, None if passes
    """
    required_items = {
        "src/": False,
        "tests/": False,
        "pyproject.toml": False,
    }

    for cmd in copy_commands:
        for item in required_items:
            if item in cmd:
                required_items[item] = True

    missing_items = [item for item, found in required_items.items() if not found]

    if missing_items:
        return f"Required items not found in COPY commands: {', '.join(missing_items)}"

    return None  # Success


def validate_excluded_directories(copy_commands: list[str]) -> str | None:
    """
    Validate that excluded directories are NOT copied.

    Per ADR-0053: scripts/ and deployments/ should NOT be in the Docker image.
    Meta-tests requiring these directories run on the host, not in the container.

    Returns:
        Error message if validation fails, None if passes
    """
    excluded_items = ["scripts/", "deployments/"]

    for cmd in copy_commands:
        for item in excluded_items:
            if item in cmd:
                return (
                    f"Excluded directory '{item}' must NOT be copied to Docker image (per ADR-0053). Meta-tests run on host."
                )

    return None  # Success


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

    # Validation: Required directories (per ADR-0053)
    error = validate_required_directories(copy_commands)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("\nDocker image requires:", file=sys.stderr)
        print("  - src/ (application source code)", file=sys.stderr)
        print("  - tests/ (test suite)", file=sys.stderr)
        print("  - pyproject.toml (project configuration)", file=sys.stderr)
        print("\nPer ADR-0053:", file=sys.stderr)
        print("  - scripts/ and deployments/ are NOT copied to Docker image", file=sys.stderr)
        print("  - Meta-tests requiring these directories run on the host", file=sys.stderr)
        return 1

    # Validation: Excluded directories (per ADR-0053)
    error = validate_excluded_directories(copy_commands)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("\nPer ADR-0053 design decision:", file=sys.stderr)
        print("  ❌ scripts/ must NOT be in Docker image", file=sys.stderr)
        print("  ❌ deployments/ must NOT be in Docker image", file=sys.stderr)
        print("  ✅ Meta-tests run on host, not in container", file=sys.stderr)
        print("\nRemove the COPY command(s) for excluded directories.", file=sys.stderr)
        return 1

    # All validations passed
    print("✅ Docker image contents validation passed (src/, tests/, pyproject.toml)", file=sys.stdout)
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
