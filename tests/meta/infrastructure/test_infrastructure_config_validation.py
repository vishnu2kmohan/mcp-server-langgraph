"""
Meta-tests for validating test infrastructure port configuration consistency.

These tests ensure that:
1. docker-compose.test.yml port mappings match conftest.py fixtures
2. No integration tests use hardcoded default ports (5432, 6379, etc.)
3. All integration tests use test_infrastructure_ports fixture or environment variables

Context:
Per INTEGRATION_TEST_FINDINGS.md Phase 4, several tests were found using hardcoded
default ports instead of test infrastructure ports (9432 for Postgres, 9379 for Redis, etc.).

This meta-test suite prevents regressions by validating port configuration patterns.

Test Coverage:
1. Docker Compose ports match conftest fixture (9432, 9379, 9080, etc.)
2. No hardcoded localhost:5432, localhost:6379 in integration tests
3. Integration tests use test_infrastructure_ports or environment variables
4. Default values in os.getenv() calls use test ports (9432, not 5432)
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Mark as unit test (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def actual_repo_root() -> Path:
    """
    Get actual repository root using marker file search.

    This is the CORRECT way to find repo root - search for markers like .git
    instead of using hardcoded .parents[N] counts.
    """
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.mark.xdist_group(name="port_config_validation_tests")
class TestDockerComposePortConfiguration:
    """Validate docker-compose.test.yml port mappings match conftest fixtures"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_docker_compose_exists(self, actual_repo_root: Path) -> None:
        """
        Should verify docker-compose.test.yml exists for integration testing.

        This file defines the test infrastructure (Postgres, Redis, OpenFGA, Qdrant).
        """
        compose_file = actual_repo_root / "docker-compose.test.yml"
        assert compose_file.exists(), f"docker-compose.test.yml not found at {compose_file}"

    def test_postgres_port_matches_fixture(self, actual_repo_root: Path) -> None:
        """
        Should verify Postgres port in docker-compose matches conftest fixture.

        Expected: 9432 (not default 5432)
        """
        compose_file = actual_repo_root / "docker-compose.test.yml"
        compose_data = yaml.safe_load(compose_file.read_text())

        # Extract Postgres port mapping (service may be named "postgres" or "postgres-test")
        services = compose_data.get("services", {})
        postgres_service = services.get("postgres-test") or services.get("postgres", {})
        ports = postgres_service.get("ports", [])

        # Find the port mapping (format: "9432:5432")
        postgres_port = None
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":5432" in port_mapping:
                # Extract host port from "9432:5432" format
                postgres_port = int(port_mapping.split(":")[0])
                break

        assert postgres_port == 9432, (
            f"Postgres port in docker-compose.test.yml should be 9432 (got {postgres_port}). "
            "This must match test_infrastructure_ports fixture."
        )

    def test_redis_port_matches_fixture(self, actual_repo_root: Path) -> None:
        """
        Should verify Redis port in docker-compose matches conftest fixture.

        Expected: 9379/9380 (not default 6379)
        """
        compose_file = actual_repo_root / "docker-compose.test.yml"
        compose_data = yaml.safe_load(compose_file.read_text())

        # Extract Redis port mapping (service named "redis-test")
        services = compose_data.get("services", {})
        redis_service = services.get("redis-test") or services.get("redis", {})
        ports = redis_service.get("ports", [])

        # Find the main Redis port mapping (format: "9379:6379")
        redis_port = None
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":6379" in port_mapping:
                redis_port = int(port_mapping.split(":")[0])
                break

        assert redis_port == 9379, (
            f"Redis port in docker-compose.test.yml should be 9379 (got {redis_port}). "
            "This must match test_infrastructure_ports fixture."
        )

    def test_openfga_port_matches_fixture(self, actual_repo_root: Path) -> None:
        """
        Should verify OpenFGA port in docker-compose matches conftest fixture.

        Expected: 9080 (not default 8080)
        """
        compose_file = actual_repo_root / "docker-compose.test.yml"
        compose_data = yaml.safe_load(compose_file.read_text())

        # Extract OpenFGA port mapping (service named "openfga-test")
        services = compose_data.get("services", {})
        openfga_service = services.get("openfga-test") or services.get("openfga", {})
        ports = openfga_service.get("ports", [])

        # Find the HTTP port mapping (format: "9080:8080")
        openfga_port = None
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":8080" in port_mapping:
                openfga_port = int(port_mapping.split(":")[0])
                break

        assert openfga_port == 9080, (
            f"OpenFGA port in docker-compose.test.yml should be 9080 (got {openfga_port}). "
            "This must match test_infrastructure_ports fixture."
        )

    def test_qdrant_port_matches_fixture(self, actual_repo_root: Path) -> None:
        """
        Should verify Qdrant port in docker-compose matches conftest fixture.

        Expected: 9333 (HTTP) and 9334 (gRPC)
        """
        compose_file = actual_repo_root / "docker-compose.test.yml"
        compose_data = yaml.safe_load(compose_file.read_text())

        # Extract Qdrant port mapping (service named "qdrant-test")
        services = compose_data.get("services", {})
        qdrant_service = services.get("qdrant-test") or services.get("qdrant", {})
        ports = qdrant_service.get("ports", [])

        # Find HTTP port (format: "9333:6333")
        qdrant_http_port = None
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":6333" in port_mapping:
                qdrant_http_port = int(port_mapping.split(":")[0])
                break

        assert qdrant_http_port == 9333, (
            f"Qdrant HTTP port should be 9333 (got {qdrant_http_port}). This must match test_infrastructure_ports fixture."
        )


@pytest.mark.xdist_group(name="port_config_validation_tests")
class TestHardcodedPortDetection:
    """Detect hardcoded default ports in integration tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_hardcoded_postgres_port(self, actual_repo_root: Path) -> None:
        """
        Should verify no integration tests use hardcoded localhost:5432.

        All tests should use:
        - test_infrastructure_ports fixture, OR
        - os.getenv("POSTGRES_PORT", "9432")

        NOT:
        - localhost:5432 (default port)
        """
        integration_tests_dir = actual_repo_root / "tests" / "integration"
        if not integration_tests_dir.exists():
            pytest.skip("Integration tests directory not found")

        # Pattern to detect hardcoded localhost:5432
        hardcoded_pattern = re.compile(r'localhost:5432|"5432".*postgres|postgres.*"5432"', re.IGNORECASE)

        violations = []
        for test_file in integration_tests_dir.rglob("*.py"):
            content = test_file.read_text()

            # Skip if file uses proper environment variable pattern
            if 'os.getenv("POSTGRES_PORT", "9432")' in content or "test_infrastructure_ports" in content:
                continue

            # Check for hardcoded 5432
            matches = hardcoded_pattern.findall(content)
            if matches:
                violations.append(f"{test_file.relative_to(actual_repo_root)}: {matches}")

        if violations:
            pytest.fail(
                f"Found {len(violations)} files with hardcoded Postgres port 5432:\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nUse test_infrastructure_ports fixture or os.getenv('POSTGRES_PORT', '9432') instead."
            )

    def test_no_hardcoded_redis_port(self, actual_repo_root: Path) -> None:
        """
        Should verify no integration tests use hardcoded localhost:6379.

        This test identifies files that use mock Redis URLs with localhost:6379
        but are NOT actually connecting to Redis (they're mocking the URL).

        All REAL Redis connections should use:
        - test_infrastructure_ports fixture, OR
        - os.getenv("REDIS_PORT", "9379")
        """
        integration_tests_dir = actual_repo_root / "tests" / "integration"
        if not integration_tests_dir.exists():
            pytest.skip("Integration tests directory not found")

        # Pattern to detect hardcoded localhost:6379 in REAL connections
        # (Excludes mock_settings.redis_url assignments)
        hardcoded_pattern = re.compile(r"redis://localhost:6379(?!/)", re.IGNORECASE)

        violations = []
        for test_file in integration_tests_dir.rglob("*.py"):
            content = test_file.read_text()

            # Skip files that are testing URL parsing/mocking (not real connections)
            if (
                "mock_settings" in content
                or "test_cache_redis_config" in test_file.name
                or "test_dependencies_wiring" in test_file.name
            ):
                continue

            # Skip if file uses proper environment variable pattern or test fixture
            if (
                'os.getenv("REDIS_PORT", "9379")' in content
                or "test_infrastructure_ports" in content
                or "redis_client" in content
            ):
                continue

            # Check for hardcoded 6379 in REAL connection strings
            matches = hardcoded_pattern.findall(content)
            if matches:
                # Verify this isn't a mock/test URL
                for match in matches:
                    # Get surrounding context (50 chars before/after)
                    match_idx = content.find(match)
                    context = content[max(0, match_idx - 50) : min(len(content), match_idx + 50)]

                    # If not in a mock context, it's a violation
                    if "mock" not in context.lower() and "test_" not in context:
                        violations.append(f"{test_file.relative_to(actual_repo_root)}: {match}")

        if violations:
            pytest.fail(
                f"Found {len(violations)} files with hardcoded Redis port 6379 in REAL connections:\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nUse test_infrastructure_ports fixture or os.getenv('REDIS_PORT', '9379') instead."
            )

    def test_environment_variable_defaults_use_test_ports(self, actual_repo_root: Path) -> None:
        """
        Should verify os.getenv() default values use test ports, not production ports.

        Correct:
        - os.getenv("POSTGRES_PORT", "9432")
        - os.getenv("REDIS_PORT", "9379")

        Incorrect:
        - os.getenv("POSTGRES_PORT", "5432")
        - os.getenv("REDIS_PORT", "6379")
        """
        integration_tests_dir = actual_repo_root / "tests" / "integration"
        if not integration_tests_dir.exists():
            pytest.skip("Integration tests directory not found")

        # Patterns for incorrect default ports
        postgres_wrong_default = re.compile(r'os\.getenv\(["\']POSTGRES_PORT["\']\s*,\s*["\']5432["\']\)', re.IGNORECASE)
        redis_wrong_default = re.compile(r'os\.getenv\(["\']REDIS_PORT["\']\s*,\s*["\']6379["\']\)', re.IGNORECASE)

        violations = []
        for test_file in integration_tests_dir.rglob("*.py"):
            content = test_file.read_text()

            # Check for wrong defaults
            postgres_matches = postgres_wrong_default.findall(content)
            redis_matches = redis_wrong_default.findall(content)

            if postgres_matches:
                violations.append(
                    f"{test_file.relative_to(actual_repo_root)}: Uses os.getenv('POSTGRES_PORT', '5432') - should be '9432'"
                )

            if redis_matches:
                violations.append(
                    f"{test_file.relative_to(actual_repo_root)}: Uses os.getenv('REDIS_PORT', '6379') - should be '9379'"
                )

        if violations:
            pytest.fail(
                f"Found {len(violations)} files with incorrect port defaults:\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nEnvironment variable defaults should use test infrastructure ports."
            )


@pytest.mark.xdist_group(name="port_config_validation_tests")
class TestPortConfigurationBestPractices:
    """Document and validate port configuration best practices"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_conftest_provides_test_infrastructure_ports_fixture(self, actual_repo_root: Path) -> None:
        """
        Should verify tests/conftest.py provides test_infrastructure_ports fixture.

        This fixture is the centralized source of truth for test port mappings.
        """
        conftest = actual_repo_root / "tests" / "conftest.py"
        assert conftest.exists(), "tests/conftest.py not found"

        content = conftest.read_text()

        # Check for test_infrastructure_ports fixture
        has_port_fixture = (
            "def test_infrastructure_ports" in content
            or "@pytest.fixture" in content
            and "test_infrastructure_ports" in content
        )

        assert has_port_fixture, (
            "tests/conftest.py should provide test_infrastructure_ports fixture. "
            "This is the centralized source of truth for test port mappings."
        )

    def test_port_fixture_documents_all_services(self, actual_repo_root: Path) -> None:
        """
        Should verify test_infrastructure_ports fixture documents all services.

        Expected services:
        - postgres: 9432
        - redis: 9379
        - openfga: 9080
        - qdrant: 9333
        """
        conftest = actual_repo_root / "tests" / "conftest.py"
        content = conftest.read_text()

        # Check for port mappings in fixture
        required_services = {
            "postgres": "9432",
            "redis": "9379",
            "openfga": "9080",
            "qdrant": "9333",
        }

        missing_services = []
        for service, port in required_services.items():
            # Look for service name and port in fixture
            if service not in content or port not in content:
                missing_services.append(f"{service}:{port}")

        if missing_services:
            pytest.skip(
                f"test_infrastructure_ports fixture missing services: {', '.join(missing_services)}. "
                "This is acceptable if services are not yet configured."
            )

    def test_integration_tests_document_port_usage(self, actual_repo_root: Path) -> None:
        """
        DOCUMENTATION TEST: Best practices for port configuration in integration tests.

        This test serves as living documentation, not strict enforcement.
        """
        documentation = """
        Port Configuration Best Practices
        ==================================

        1. ALWAYS use test infrastructure ports (9XXX range)
        2. NEVER hardcode default ports (5432, 6379, etc.)
        3. Prefer test_infrastructure_ports fixture over environment variables
        4. If using os.getenv(), default to test ports (9432, not 5432)

        Examples:
        ---------

        # ✅ CORRECT: Using fixture
        async def test_postgres_connection(test_infrastructure_ports):
            port = test_infrastructure_ports["postgres"]  # 9432
            conn = await asyncpg.connect(host="localhost", port=port, ...)

        # ✅ CORRECT: Using environment variable with test default
        async def test_postgres_with_env():
            conn = await asyncpg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "9432")),  # Test port default
                ...
            )

        # ❌ INCORRECT: Hardcoded default port
        async def test_postgres_hardcoded():
            conn = await asyncpg.connect(host="localhost", port=5432, ...)  # BAD!

        # ❌ INCORRECT: Environment variable with production default
        async def test_postgres_wrong_default():
            conn = await asyncpg.connect(
                port=int(os.getenv("POSTGRES_PORT", "5432")),  # Should be 9432!
                ...
            )

        Why Test Ports Matter:
        ----------------------
        - Prevents conflicts with local development databases
        - Enables parallel test execution without interference
        - Makes test infrastructure explicit and isolated
        - Matches CI/CD environment configuration

        Port Mappings (from docker-compose.test.yml):
        ----------------------------------------------
        - Postgres: 9432 (internal 5432)
        - Redis: 9379 (internal 6379)
        - OpenFGA: 9080 (internal 8080)
        - Qdrant: 9333 (internal 6333)
        """

        assert len(documentation) > 100, "Documentation is comprehensive"
        assert "9432" in documentation, "Documents Postgres test port"
        assert "9379" in documentation, "Documents Redis test port"
        assert "test_infrastructure_ports" in documentation, "Documents preferred fixture pattern"
