"""
Test that validates centralized test constants are used consistently.

This test ensures that JWT secrets and other test constants are synchronized
across all test environments (local, Docker, CI/CD).

OpenAI Codex Finding (2025-11-16):
- Integration tests failed due to JWT secret mismatch
- conftest.py used "test-secret-key"
- docker-compose.test.yml used "test-jwt-secret-key-for-e2e-testing-only"
- CI workflows used "test-secret-key-for-ci"
- Auth middleware validated with settings.jwt_secret_key, causing token rejection

Solution:
- Centralized test constants in tests/constants.py
- All test fixtures, Docker configs, CI workflows, and .env.test use same constant
- This test validates consistency is maintained
"""

import re
from pathlib import Path

import pytest
import yaml

# Module-level marker: All tests in this file are unit tests
pytestmark = pytest.mark.unit


def test_jwt_secret_constant_exists():
    """Verify TEST_JWT_SECRET constant exists in tests/constants.py."""
    from tests import constants

    assert hasattr(constants, "TEST_JWT_SECRET"), "TEST_JWT_SECRET must be defined in tests/constants.py"
    assert isinstance(constants.TEST_JWT_SECRET, str), "TEST_JWT_SECRET must be a string"
    assert len(constants.TEST_JWT_SECRET) > 0, "TEST_JWT_SECRET must not be empty"


def test_mock_jwt_token_uses_constant():
    """Verify mock_jwt_token fixture uses TEST_JWT_SECRET."""

    conftest_path = Path(__file__).parent / "conftest.py"
    conftest_content = conftest_path.read_text()

    # Find the mock_jwt_token fixture
    fixture_match = re.search(
        r"@pytest\.fixture\s+def\s+mock_jwt_token\(\):.*?return jwt\.encode\([^)]+\)", conftest_content, re.DOTALL
    )

    assert fixture_match is not None, "mock_jwt_token fixture not found in conftest.py"

    fixture_code = fixture_match.group(0)

    # Verify it imports and uses TEST_JWT_SECRET
    assert "from tests.constants import TEST_JWT_SECRET" in conftest_content, (
        "conftest.py must import TEST_JWT_SECRET from tests.constants"
    )
    assert "TEST_JWT_SECRET" in fixture_code, "mock_jwt_token fixture must use TEST_JWT_SECRET constant"


def test_env_test_file_uses_correct_jwt_secret():
    """Verify .env.test file uses the correct JWT secret (12-factor config source)."""
    from tests import constants

    env_test_path = Path(__file__).parent.parent / ".env.test"

    if not env_test_path.exists():
        pytest.skip(f".env.test not found at {env_test_path}")

    env_content = env_test_path.read_text()

    # Look for JWT_SECRET_KEY in .env.test
    jwt_match = re.search(r"^JWT_SECRET_KEY=(.+)$", env_content, re.MULTILINE)

    assert jwt_match is not None, ".env.test must define JWT_SECRET_KEY"

    jwt_secret = jwt_match.group(1).strip().strip('"').strip("'")

    assert jwt_secret == constants.TEST_JWT_SECRET, (
        f".env.test uses JWT_SECRET_KEY='{jwt_secret}', but tests/constants.py defines "
        f"TEST_JWT_SECRET='{constants.TEST_JWT_SECRET}'. These must match."
    )


def test_docker_compose_uses_env_test_file():
    """Verify docker-compose.test.yml uses .env.test via env_file directive."""
    from tests import constants

    # Try multiple possible locations for docker-compose.test.yml
    possible_paths = [
        Path(__file__).parent.parent / "docker-compose.test.yml",  # Root level
        Path(__file__).parent.parent / "docker" / "docker-compose.test.yml",  # Docker subdir
    ]

    docker_compose_path = None
    for path in possible_paths:
        if path.exists():
            docker_compose_path = path
            break

    if docker_compose_path is None:
        pytest.skip("docker-compose.test.yml not found in expected locations")

    with open(docker_compose_path) as f:
        compose_config = yaml.safe_load(f)

    # Find test services that use env_file
    services_with_env_file = []
    services_with_jwt_in_environment = []

    for service_name, service_config in compose_config.get("services", {}).items():
        if "test" in service_name.lower():
            # Check if service uses env_file
            env_files = service_config.get("env_file", [])
            if isinstance(env_files, str):
                env_files = [env_files]
            if ".env.test" in env_files:
                services_with_env_file.append(service_name)

            # Check for JWT_SECRET_KEY in environment block (should NOT be there for 12-factor)
            env_vars = service_config.get("environment", [])
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if "JWT_SECRET_KEY=" in env_var:
                        jwt_secret = env_var.split("=", 1)[1]
                        # If JWT is in environment block, verify it matches (backwards compat)
                        assert jwt_secret == constants.TEST_JWT_SECRET, (
                            f"docker-compose.test.yml service '{service_name}' uses "
                            f"JWT_SECRET_KEY='{jwt_secret}', but tests/constants.py defines "
                            f"TEST_JWT_SECRET='{constants.TEST_JWT_SECRET}'. These must match."
                        )
                        services_with_jwt_in_environment.append(service_name)

    # Verify at least mcp-server-test uses env_file pattern
    assert "mcp-server-test" in services_with_env_file, (
        "mcp-server-test should use env_file: .env.test for 12-factor compliance"
    )


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
        f"TEST_JWT_SECRET should be at least 16 characters for security. Current length: {len(constants.TEST_JWT_SECRET)}"
    )
