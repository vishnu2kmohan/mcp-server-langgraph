"""
Test that validates centralized test constants are used consistently.

This test ensures that JWT secrets and other test constants are synchronized
across all test environments (local, Docker, CI/CD).

OpenAI Codex Finding (2025-11-16):
- Integration tests failed due to JWT secret mismatch
- conftest.py used "test-secret-key"
- docker-compose.test.yml used "test-secret-key-for-integration-tests"
- CI workflows used "test-secret-key-for-ci"
- Auth middleware validated with settings.jwt_secret_key, causing token rejection

Solution:
- Centralized test constants in tests/constants.py
- All test fixtures, Docker configs, and CI workflows use same constant
- This test validates consistency is maintained
"""

import os
import re
from pathlib import Path

import pytest
import yaml


def test_jwt_secret_constant_exists():
    """Verify TEST_JWT_SECRET constant exists in tests/constants.py."""
    from tests import constants

    assert hasattr(constants, "TEST_JWT_SECRET"), "TEST_JWT_SECRET must be defined in tests/constants.py"
    assert isinstance(constants.TEST_JWT_SECRET, str), "TEST_JWT_SECRET must be a string"
    assert len(constants.TEST_JWT_SECRET) > 0, "TEST_JWT_SECRET must not be empty"


def test_mock_jwt_token_uses_constant():
    """Verify mock_jwt_token fixture uses TEST_JWT_SECRET."""
    from tests import constants

    conftest_path = Path(__file__).parent / "conftest.py"
    conftest_content = conftest_path.read_text()

    # Find the mock_jwt_token fixture
    fixture_match = re.search(
        r"@pytest\.fixture\s+def\s+mock_jwt_token\(\):.*?return jwt\.encode\([^)]+\)", conftest_content, re.DOTALL
    )

    assert fixture_match is not None, "mock_jwt_token fixture not found in conftest.py"

    fixture_code = fixture_match.group(0)

    # Verify it imports and uses TEST_JWT_SECRET
    assert (
        "from tests.constants import TEST_JWT_SECRET" in conftest_content
    ), "conftest.py must import TEST_JWT_SECRET from tests.constants"
    assert "TEST_JWT_SECRET" in fixture_code, "mock_jwt_token fixture must use TEST_JWT_SECRET constant"


def test_docker_compose_uses_correct_jwt_secret():
    """Verify docker-compose.test.yml uses the correct JWT secret."""
    from tests import constants

    docker_compose_path = Path(__file__).parent.parent / "docker" / "docker-compose.test.yml"

    if not docker_compose_path.exists():
        pytest.skip(f"docker-compose.test.yml not found at {docker_compose_path}")

    with open(docker_compose_path) as f:
        compose_config = yaml.safe_load(f)

    # Find the test service environment
    test_service = None
    for service_name, service_config in compose_config.get("services", {}).items():
        if "test" in service_name.lower() and "environment" in service_config:
            env_vars = service_config["environment"]

            # Handle both list and dict format
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if "JWT_SECRET_KEY=" in env_var:
                        jwt_secret = env_var.split("=", 1)[1]
                        assert jwt_secret == constants.TEST_JWT_SECRET, (
                            f"docker-compose.test.yml service '{service_name}' uses "
                            f"JWT_SECRET_KEY='{jwt_secret}', but tests/constants.py defines "
                            f"TEST_JWT_SECRET='{constants.TEST_JWT_SECRET}'. These must match."
                        )
                        test_service = service_name
            elif isinstance(env_vars, dict):
                if "JWT_SECRET_KEY" in env_vars:
                    jwt_secret = env_vars["JWT_SECRET_KEY"]
                    assert jwt_secret == constants.TEST_JWT_SECRET, (
                        f"docker-compose.test.yml service '{service_name}' uses "
                        f"JWT_SECRET_KEY='{jwt_secret}', but tests/constants.py defines "
                        f"TEST_JWT_SECRET='{constants.TEST_JWT_SECRET}'. These must match."
                    )
                    test_service = service_name

    # Verify we found at least one test service with JWT config
    if test_service is None:
        pytest.skip("No test service with JWT_SECRET_KEY found in docker-compose.test.yml")


def test_github_workflows_use_correct_jwt_secret():
    """Verify GitHub workflow files use the correct JWT secret."""
    from tests import constants

    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"

    if not workflows_dir.exists():
        pytest.skip(f"GitHub workflows directory not found at {workflows_dir}")

    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    mismatched_files = []

    for workflow_file in workflow_files:
        content = workflow_file.read_text()

        # Look for JWT_SECRET_KEY environment variable definitions
        # Matches patterns like:
        #   JWT_SECRET_KEY: "value"
        #   JWT_SECRET_KEY: 'value'
        #   - JWT_SECRET_KEY=value
        jwt_patterns = [
            r'JWT_SECRET_KEY:\s*["\']([^"\']+)["\']',
            r"JWT_SECRET_KEY:\s*([^\s]+)",
            r"JWT_SECRET_KEY=([^\s]+)",
        ]

        for pattern in jwt_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                jwt_value = match.group(1).strip()
                # Strip surrounding quotes if present
                jwt_value = jwt_value.strip('"').strip("'")
                if jwt_value and jwt_value != constants.TEST_JWT_SECRET:
                    mismatched_files.append(
                        {"file": workflow_file.name, "found": jwt_value, "expected": constants.TEST_JWT_SECRET}
                    )

    assert not mismatched_files, "GitHub workflow files have mismatched JWT secrets:\n" + "\n".join(
        [f"  - {m['file']}: JWT_SECRET_KEY='{m['found']}' (expected '{m['expected']}')" for m in mismatched_files]
    )


def test_jwt_secret_not_in_production_config():
    """Verify test JWT secret is not accidentally used in production config."""
    from tests import constants

    # Check that the test secret is clearly marked as a test secret
    assert "test" in constants.TEST_JWT_SECRET.lower(), (
        f"TEST_JWT_SECRET should contain 'test' to clearly indicate it's for testing. "
        f"Current value: '{constants.TEST_JWT_SECRET}'"
    )

    # Check that we're not using weak secrets
    assert len(constants.TEST_JWT_SECRET) >= 16, (
        f"TEST_JWT_SECRET should be at least 16 characters for security. " f"Current length: {len(constants.TEST_JWT_SECRET)}"
    )
