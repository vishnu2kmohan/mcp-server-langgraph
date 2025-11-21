"""
Meta-tests for pre-commit hook: validate-keycloak-config

Tests ensure the Keycloak configuration validation hook works correctly
and prevents regression of Codex findings related to Keycloak service availability.

TDD Cycle: RED → GREEN → REFACTOR

Reference: ADR-0053 Future Work - Pre-commit hook: validate-keycloak-config
"""

import gc
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testkeycloakconfigvalidationhook")
class TestKeycloakConfigValidationHook:
    """Test suite for validate_keycloak_config.py pre-commit hook"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_hook_script_exists(self):
        """
        Validate that the validation script exists.

        GIVEN: The scripts directory
        WHEN: Checking for validate_keycloak_config.py
        THEN: The script should exist and be executable
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "validate_keycloak_config.py"
        assert script_path.exists(), f"Hook script not found: {script_path}"
        assert script_path.is_file(), "Hook script must be a file"

    def test_hook_detects_keycloak_service_enabled(self):
        """
        Validate hook passes when Keycloak service is enabled.

        GIVEN: A docker-compose.test.yml with Keycloak service enabled
        WHEN: Running the validation hook
        THEN: Hook should exit with code 0 (success)
        """
        # Create temp docker-compose.test.yml with Keycloak enabled
        compose_content = {
            "services": {
                "keycloak-test": {
                    "image": "quay.io/keycloak/keycloak:26.4.2",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health/ready"],
                        "interval": "5s",
                        "start_period": "60s",
                    },
                    "environment": [
                        "KEYCLOAK_ADMIN=admin",
                        "KEYCLOAK_ADMIN_PASSWORD=admin",
                        "KC_DB=postgres",
                        "KC_DB_URL=jdbc:postgresql://postgres-test:5432/testdb",
                        "KC_HEALTH_ENABLED=true",
                    ],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(compose_content, f)
            temp_file = Path(f.name)

        try:
            # Run validation script
            result = subprocess.run(
                ["python", "scripts/validate_keycloak_config.py", str(temp_file)], capture_output=True, text=True, timeout=60
            )

            assert result.returncode == 0, f"Hook should pass with Keycloak enabled. stderr: {result.stderr}"
        finally:
            temp_file.unlink()

    def test_hook_fails_when_keycloak_service_missing(self):
        """
        Validate hook fails when Keycloak service is missing.

        GIVEN: A docker-compose.test.yml without Keycloak service
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        compose_content = {
            "services": {
                "postgres-test": {"image": "postgres:16-alpine"},
                "redis-test": {"image": "redis:7-alpine"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(compose_content, f)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validate_keycloak_config.py", str(temp_file)], capture_output=True, text=True, timeout=60
            )

            assert result.returncode == 1, "Hook should fail when Keycloak service missing"
            assert "keycloak-test service not found" in result.stderr.lower() or "keycloak" in result.stdout.lower()
        finally:
            temp_file.unlink()

    def test_hook_validates_health_check_exists(self):
        """
        Validate hook checks for health check configuration.

        GIVEN: A docker-compose.test.yml with Keycloak but no health check
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        compose_content = {
            "services": {
                "keycloak-test": {
                    "image": "quay.io/keycloak/keycloak:26.4.2",
                    # Missing healthcheck
                    "environment": ["KEYCLOAK_ADMIN=admin"],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(compose_content, f)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validate_keycloak_config.py", str(temp_file)], capture_output=True, text=True, timeout=60
            )

            assert result.returncode == 1, "Hook should fail when health check missing"
            assert "healthcheck" in result.stderr.lower() or "health" in result.stdout.lower()
        finally:
            temp_file.unlink()

    def test_hook_validates_environment_variables(self):
        """
        Validate hook checks for required environment variables.

        GIVEN: A docker-compose.test.yml with Keycloak but missing env vars
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        compose_content = {
            "services": {
                "keycloak-test": {
                    "image": "quay.io/keycloak/keycloak:26.4.2",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health/ready"],
                        "interval": "5s",
                        "start_period": "60s",
                    },
                    # Missing required environment variables
                    "environment": [],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(compose_content, f)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validate_keycloak_config.py", str(temp_file)], capture_output=True, text=True, timeout=60
            )

            assert result.returncode == 1, "Hook should fail when required env vars missing"
            assert (
                "keycloak_admin" in result.stderr.lower()
                or "environment" in result.stdout.lower()
                or "kc_health" in result.stderr.lower()
            )
        finally:
            temp_file.unlink()

    def test_hook_validates_start_period(self):
        """
        Validate hook checks for adequate start_period (60s for Keycloak).

        GIVEN: A docker-compose.test.yml with Keycloak but short start_period
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (warning/failure)
        """
        compose_content = {
            "services": {
                "keycloak-test": {
                    "image": "quay.io/keycloak/keycloak:26.4.2",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health/ready"],
                        "interval": "5s",
                        "start_period": "5s",  # Too short! Should be 60s
                    },
                    "environment": [
                        "KEYCLOAK_ADMIN=admin",
                        "KEYCLOAK_ADMIN_PASSWORD=admin",
                        "KC_DB=postgres",
                        "KC_DB_URL=jdbc:postgresql://postgres-test:5432/testdb",
                        "KC_HEALTH_ENABLED=true",
                    ],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(compose_content, f)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validate_keycloak_config.py", str(temp_file)], capture_output=True, text=True, timeout=60
            )

            # Hook should warn or fail about inadequate start_period
            assert (
                result.returncode == 1 or "start_period" in result.stdout.lower() or "60s" in result.stdout.lower()
            ), "Hook should warn about inadequate start_period"
        finally:
            temp_file.unlink()

    def test_hook_with_production_docker_compose_file(self):
        """
        Validate hook works with the actual docker-compose.test.yml.

        GIVEN: The actual docker-compose.test.yml file
        WHEN: Running the validation hook
        THEN: Hook should pass (Keycloak is enabled per ADR-0053)
        """
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        assert compose_file.exists(), "docker-compose.test.yml not found"

        result = subprocess.run(
            ["python", "scripts/validate_keycloak_config.py", str(compose_file)], capture_output=True, text=True, timeout=60
        )

        assert result.returncode == 0, (
            f"Hook should pass with production docker-compose.test.yml. "
            f"Per ADR-0053, Keycloak service should be enabled. "
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
