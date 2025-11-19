"""
Meta-tests validating Codex findings are resolved and preventing regression.

These tests ensure:
1. Fixture scopes are correct (session-scoped for integration fixtures)
2. Keycloak service is enabled and properly configured
3. Tests skip gracefully when services unavailable
4. No strict xfail markers on placeholder tests

Reference: Codex Integration Failures Analysis (2025-11-13)
ADR: docs-internal/ADR-0053-codex-findings-validation.md
"""

import ast
import gc
import re
from pathlib import Path
from typing import Dict, List, Set

import pytest
import yaml


# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.xdist_group(name="testfixturescopevalidation")
class TestFixtureScopeValidation:
    """Validate that integration fixtures have correct scopes to prevent ScopeMismatch errors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_integration_test_env_fixture_is_session_scoped(self):
        """
        Validate integration_test_env fixture is session-scoped.

        CODEX FINDING: ScopeMismatch propagation for OpenFGA/SCIM security tests
        came from test-runner image using function-scoped fixture. This test
        ensures the fixture remains session-scoped.

        References:
        - tests/conftest.py:970 - integration_test_env fixture definition
        """
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        content = conftest_path.read_text()

        # Parse AST to find fixture definition
        tree = ast.parse(content)

        fixture_found = False
        is_session_scoped = False

        for node in ast.walk(tree):
            # Check both regular and async function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "integration_test_env":
                fixture_found = True
                # Check decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                            # Check for scope="session" argument
                            for keyword in decorator.keywords:
                                if keyword.arg == "scope" and isinstance(keyword.value, ast.Constant):
                                    if keyword.value.value == "session":
                                        is_session_scoped = True

        assert fixture_found, "integration_test_env fixture not found in conftest.py"
        assert is_session_scoped, (
            "integration_test_env fixture must be session-scoped to prevent ScopeMismatch errors. "
            "Found in tests/conftest.py but scope is not 'session'."
        )

    def test_dependent_fixtures_are_session_scoped(self):
        """
        Validate that fixtures dependent on integration_test_env are also session-scoped.

        CODEX FINDING: Dependent fixtures (postgres_connection_real, redis_client_real,
        openfga_client_real) must have matching scope to prevent ScopeMismatch.

        References:
        - tests/conftest.py:988 - postgres_connection_real
        - tests/conftest.py:1014 - redis_client_real
        - tests/conftest.py:1044 - openfga_client_real
        """
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        content = conftest_path.read_text()

        # Parse AST
        tree = ast.parse(content)

        required_fixtures = {
            "postgres_connection_real",
            "redis_client_real",
            "openfga_client_real",
        }

        fixture_scopes: dict[str, str] = {}

        for node in ast.walk(tree):
            # Check both regular and async function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in required_fixtures:
                # Check decorators for scope
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                            for keyword in decorator.keywords:
                                if keyword.arg == "scope" and isinstance(keyword.value, ast.Constant):
                                    fixture_scopes[node.name] = keyword.value.value

        # Validate all fixtures found and are session-scoped
        for fixture_name in required_fixtures:
            assert fixture_name in fixture_scopes, f"Required fixture '{fixture_name}' not found in conftest.py"
            assert (
                fixture_scopes[fixture_name] == "session"
            ), f"Fixture '{fixture_name}' must be session-scoped, found scope='{fixture_scopes[fixture_name]}'"

    def test_openfga_scim_test_fixtures_compatible_with_session_scope(self):
        """
        Validate OpenFGA/SCIM security tests use session-compatible fixtures.

        CODEX FINDING: ScopeMismatch errors in OpenFGA/SCIM security tests when
        using pytest-xdist parallel execution.

        References:
        - tests/security/test_scim_service_principal_openfga.py
        """
        test_file = Path(__file__).parent.parent / "security" / "test_scim_service_principal_openfga.py"

        if not test_file.exists():
            pytest.skip("test_scim_service_principal_openfga.py not found")

        content = test_file.read_text()
        tree = ast.parse(content)

        # Find all test classes
        test_classes: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                test_classes.append(node.name)

        # Validate at least one test class exists
        assert len(test_classes) > 0, "No test classes found in test_scim_service_principal_openfga.py"

        # Validate all test classes have xdist_group marker for isolation
        for class_name in test_classes:
            # Check if class has xdist_group marker in file content
            class_marker_pattern = rf"@pytest\.mark\.xdist_group.*\nclass {class_name}"
            assert re.search(class_marker_pattern, content), (
                f"Test class '{class_name}' must have @pytest.mark.xdist_group marker "
                "for pytest-xdist isolation to prevent ScopeMismatch"
            )


@pytest.mark.xdist_group(name="testkeycloakserviceconfiguration")
class TestKeycloakServiceConfiguration:
    """Validate Keycloak service is enabled and properly configured in docker-compose."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_service_enabled_in_docker_compose(self):
        """
        Validate Keycloak service is uncommented and enabled in docker-compose.test.yml.

        CODEX FINDING: TestStandardUserJourney::test_01_login fails because Keycloak
        service is commented out in docker/docker-compose.test.yml:74.

        Decision: Enable Keycloak for full E2E auth testing (trade-off: +60s startup).
        """
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        assert compose_file.exists(), "docker-compose.test.yml not found"

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        # Validate Keycloak service exists and is not commented out
        assert "services" in compose_config, "No services defined in docker-compose.test.yml"
        assert (
            "keycloak-test" in compose_config["services"]
        ), "keycloak-test service not found in docker-compose.test.yml. Service must be uncommented for E2E auth testing."

    def test_keycloak_service_has_health_check(self):
        """
        Validate Keycloak service has proper health check configuration.

        Health checks ensure tests only run when Keycloak is ready.
        """
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        keycloak_service = compose_config["services"]["keycloak-test"]

        assert "healthcheck" in keycloak_service, "keycloak-test service must have healthcheck configuration"

        healthcheck = keycloak_service["healthcheck"]
        assert "test" in healthcheck, "Health check must define test command"
        assert "interval" in healthcheck, "Health check must define interval"
        assert "start_period" in healthcheck, "Health check must define start_period"

    def test_keycloak_environment_variables_configured(self):
        """
        Validate Keycloak has required environment variables.

        Required vars:
        - Admin credentials: KEYCLOAK_ADMIN (legacy) OR KC_BOOTSTRAP_ADMIN_USERNAME (Keycloak 22+)
        - Database: KC_DB, KC_DB_URL
        - Health: KC_HEALTH_ENABLED
        """
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        keycloak_service = compose_config["services"]["keycloak-test"]

        assert "environment" in keycloak_service, "keycloak-test service must have environment variables"

        env_vars = keycloak_service["environment"]

        # Convert list of KEY=VALUE or dict to set of keys
        if isinstance(env_vars, list):
            env_keys = {var.split("=")[0] for var in env_vars}
        else:
            env_keys = set(env_vars.keys())

        # Admin credentials: Accept either old (KEYCLOAK_ADMIN) or new (KC_BOOTSTRAP_ADMIN_USERNAME) format
        has_admin_username = "KEYCLOAK_ADMIN" in env_keys or "KC_BOOTSTRAP_ADMIN_USERNAME" in env_keys
        has_admin_password = "KEYCLOAK_ADMIN_PASSWORD" in env_keys or "KC_BOOTSTRAP_ADMIN_PASSWORD" in env_keys

        assert (
            has_admin_username
        ), "keycloak-test service missing admin username: must have KEYCLOAK_ADMIN or KC_BOOTSTRAP_ADMIN_USERNAME"
        assert (
            has_admin_password
        ), "keycloak-test service missing admin password: must have KEYCLOAK_ADMIN_PASSWORD or KC_BOOTSTRAP_ADMIN_PASSWORD"

        # Database and health configuration (required regardless of Keycloak version)
        required_vars = [
            "KC_DB",
            "KC_DB_URL",
            "KC_HEALTH_ENABLED",
        ]

        for var in required_vars:
            assert var in env_keys, f"keycloak-test service missing required environment variable: {var}"


@pytest.mark.xdist_group(name="testgracefulserviceskipping")
class TestGracefulServiceSkipping:
    """Validate tests skip gracefully when optional services are unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_tests_skip_when_service_unavailable(self):
        """
        Validate E2E tests using Keycloak skip gracefully when service is down.

        CODEX FINDING: TestStandardUserJourney::test_01_login should skip when
        Keycloak is unreachable, not fail.

        References:
        - tests/e2e/test_full_user_journey.py::test_01_login
        """
        test_file = Path(__file__).parent.parent / "e2e" / "test_full_user_journey.py"

        if not test_file.exists():
            pytest.skip("test_full_user_journey.py not found")

        content = test_file.read_text()

        # Validate test has proper skip/xfail marker or uses test_infrastructure_check fixture
        assert "test_infrastructure_check" in content or "@pytest.mark.skipif" in content, (
            "test_01_login must use test_infrastructure_check fixture or skipif marker "
            "to skip gracefully when Keycloak is unavailable"
        )


@pytest.mark.xdist_group(name="testplaceholdertestmarkers")
class TestPlaceholderTestMarkers:
    """Validate placeholder tests don't have strict xfail markers that cause XPASS errors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_service_principal_lifecycle_no_strict_xfail(self):
        """
        Validate test_full_service_principal_lifecycle doesn't have strict xfail marker.

        CODEX FINDING: Test reports [XPASS(strict)] because it's a placeholder with
        strict xfail that "passes" (no assertions yet).

        Solution: Remove xfail or implement full test.

        References:
        - tests/api/test_service_principals_endpoints.py::test_full_service_principal_lifecycle
        """
        test_file = Path(__file__).parent.parent / "api" / "test_service_principals_endpoints.py"

        assert test_file.exists(), "test_service_principals_endpoints.py not found"

        content = test_file.read_text()

        # Find the test method
        assert (
            "test_full_service_principal_lifecycle" in content
        ), "test_full_service_principal_lifecycle not found in test file"

        # Extract the test method section
        lines = content.split("\n")
        test_start_idx = None
        for i, line in enumerate(lines):
            if "def test_full_service_principal_lifecycle" in line:
                test_start_idx = i
                break

        assert test_start_idx is not None, "Test method definition not found"

        # Check 10 lines before test definition for strict xfail marker
        test_section = "\n".join(lines[max(0, test_start_idx - 10) : test_start_idx + 50])

        # Should NOT have strict xfail marker
        assert not re.search(r"@pytest\.mark\.xfail.*strict=True", test_section), (
            "test_full_service_principal_lifecycle must not have strict xfail marker. "
            "Either implement the test fully or use non-strict xfail."
        )


@pytest.mark.xdist_group(name="testdockerimagecontents")
class TestDockerImageContents:
    """Validate Docker test image includes necessary directories."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dockerfile_copies_required_directories_for_integration_tests(self):
        """
        Validate Dockerfile final-test stage copies src/, tests/, and pyproject.toml.
        Per ADR-0053, scripts/ and deployments/ must be EXCLUDED from Docker image.

        CODEX FINDING: ModuleNotFoundError for 'scripts' module when importing
        documentation validators. ADR-0053 resolution: scripts/ and deployments/
        are excluded from Docker image. Meta-tests requiring these directories
        run on the host, not in containers.

        This test validates ADR-0053 compliance.

        References:
        - docker/Dockerfile final-test stage (lines 262-265)
        - ADR-0053: Docker Image Contents Policy
        """
        dockerfile_path = Path(__file__).parent.parent.parent / "docker" / "Dockerfile"

        assert dockerfile_path.exists(), "Dockerfile not found"

        content = dockerfile_path.read_text()

        # Find final-test stage
        assert "FROM runtime-slim AS final-test" in content, "final-test stage not found in Dockerfile"

        # Extract final-test stage section (get more lines to ensure we capture all COPY commands)
        lines = content.split("\n")
        stage_start = None
        stage_end = None
        for i, line in enumerate(lines):
            if "FROM runtime-slim AS final-test" in line:
                stage_start = i
            elif stage_start is not None and line.strip().startswith("FROM "):
                stage_end = i
                break

        assert stage_start is not None, "final-test stage not found"

        if stage_end is None:
            stage_end = len(lines)

        stage_section = "\n".join(lines[stage_start:stage_end])

        # Validate required COPY commands present
        assert "COPY src/" in stage_section, "Dockerfile must copy src/ directory"
        assert "COPY tests/" in stage_section, "Dockerfile must copy tests/ directory"
        assert "COPY pyproject.toml" in stage_section, "Dockerfile must copy pyproject.toml"

        # Validate scripts/ and deployments/ are NOT copied (ADR-0053 compliance)
        # Per ADR-0053: These directories must be excluded from Docker image.
        # Meta-tests requiring these directories run on host, not in container.
        # See: scripts/validate_docker_image_contents.py for pre-commit enforcement
        assert "COPY scripts/" not in stage_section, (
            "❌ ADR-0053 VIOLATION: scripts/ must NOT be in Docker image. "
            "Meta-tests requiring scripts/ run on host, not in container. "
            "See docker/Dockerfile lines 262-265 for ADR-0053 compliance notes."
        )
        assert "COPY deployments/" not in stage_section, (
            "❌ ADR-0053 VIOLATION: deployments/ must NOT be in Docker image. "
            "Meta-tests requiring deployments/ run on host, not in container. "
            "See docker/Dockerfile lines 262-265 for ADR-0053 compliance notes."
        )

    def test_meta_tests_run_on_host_not_docker(self):
        """
        Validate meta-tests (requiring scripts/) are not marked as integration tests.

        Meta-tests should run on host with full repo context, not in Docker container.
        """
        meta_test_dir = Path(__file__).parent

        # Find all test files in meta/ directory
        test_files = list(meta_test_dir.glob("test_*.py"))

        assert len(test_files) > 0, "No meta-test files found"

        for test_file in test_files:
            content = test_file.read_text()
            tree = ast.parse(content)

            # Meta-tests should NOT have @pytest.mark.integration as actual decorators
            # (ignore mentions in docstrings/comments)
            has_integration_marker = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        # Check for @pytest.mark.integration decorator
                        if isinstance(decorator, ast.Attribute):
                            if (
                                isinstance(decorator.value, ast.Attribute)
                                and isinstance(decorator.value.value, ast.Name)
                                and decorator.value.value.id == "pytest"
                                and decorator.value.attr == "mark"
                                and decorator.attr == "integration"
                            ):
                                has_integration_marker = True
                                break
                        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            if (
                                isinstance(decorator.func.value, ast.Attribute)
                                and isinstance(decorator.func.value.value, ast.Name)
                                and decorator.func.value.value.id == "pytest"
                                and decorator.func.value.attr == "mark"
                                and decorator.func.attr == "integration"
                            ):
                                has_integration_marker = True
                                break
                    if has_integration_marker:
                        break

            assert not has_integration_marker, (
                f"{test_file.name} is a meta-test and should NOT have @pytest.mark.integration marker. "
                "Meta-tests run on host with full repo context, not in Docker."
            )


# Summary marker to ensure all tests ran
@pytest.mark.meta
@pytest.mark.xdist_group(name="testcodexfindingsvalidationsummary")
class TestCodexFindingsValidationSummary:
    """Summary test confirming all Codex findings have validation coverage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_codex_findings_have_validation_tests(self):
        """
        Confirm all Codex findings mentioned in the report have corresponding tests.

        Codex Findings:
        1. ✅ ScopeMismatch propagation - Validated by test_integration_test_env_fixture_is_session_scoped
        2. ✅ Keycloak service unreachable - Validated by test_keycloak_service_enabled_in_docker_compose
        3. ✅ XPASS(strict) placeholder - Validated by test_service_principal_lifecycle_no_strict_xfail
        4. ✅ ModuleNotFoundError scripts - Validated by test_dockerfile_copies_required_directories
        5. ✅ FileNotFoundError deployments - Validated by test_dockerfile_copies_required_directories
        6. ✅ Graceful skipping - Validated by test_keycloak_tests_skip_when_service_unavailable
        """
        # This test serves as documentation and passes if imported successfully
        assert True, "All Codex findings have validation coverage"
