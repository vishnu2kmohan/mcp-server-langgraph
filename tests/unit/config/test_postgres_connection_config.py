"""
Test to prevent PostgreSQL connection configuration regressions.

TDD Context:
- RED (2025-01-17): Integration tests failing with connection errors to port 9432
- Root cause: Password mismatch between docker-compose.test.yml and conftest.py fixtures
- GREEN: Ensure all fixtures use consistent PostgreSQL connection parameters
- REFACTOR: This test prevents configuration drift between docker-compose and test fixtures

Following TDD: This test written FIRST to catch configuration mismatches.
"""

import gc
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.precommit
@pytest.mark.xdist_group(name="testpostgresconnectionconfig")
class TestPostgresConnectionConfig:
    """Validate PostgreSQL connection configuration consistency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_docker_compose_and_conftest_use_same_password(self):
        """
        Test: Docker-compose and conftest fixtures must use same PostgreSQL password.

        RED (Before Fix - 2025-01-17):
        - docker-compose.test.yml: POSTGRES_PASSWORD: postgres
        - conftest.py postgres_connection_clean: password default "test" (MISMATCH)
        - Integration tests fail: [Errno 111] Connect call failed

        GREEN (After Fix):
        - Both use "postgres" password
        - Integration tests connect successfully
        """
        # Read docker-compose configuration
        compose_file = Path("docker-compose.test.yml")
        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        postgres_password = compose_config["services"]["postgres-test"]["environment"]["POSTGRES_PASSWORD"]

        # Read conftest.py to check default password
        # Read database_fixtures.py to check default password
        conftest_file = Path("tests/fixtures/database_fixtures.py")
        conftest_content = conftest_file.read_text()

        # Check for password defaults in asyncpg.connect and create_pool calls
        # Both should match docker-compose password (accept both single and double quotes)
        password_patterns = [
            f'password="{postgres_password}"',
            f"password='{postgres_password}'",
            f'password=os.getenv("POSTGRES_PASSWORD", "{postgres_password}")',
            f"password=os.getenv('POSTGRES_PASSWORD', '{postgres_password}')",
        ]

        has_correct_password = any(pattern in conftest_content for pattern in password_patterns)

        assert has_correct_password, (
            f"conftest.py fixtures must use same password as docker-compose.test.yml ({postgres_password}).\n"
            f"Expected one of these patterns:\n" + "\n".join(f"  - {p}" for p in password_patterns) + "\n"
            f"Fix: Update POSTGRES_PASSWORD defaults in conftest.py to '{postgres_password}'"
        )

    def test_docker_compose_and_conftest_use_same_port(self):
        """Test: Docker-compose and conftest fixtures must use same port (9432)."""
        compose_file = Path("docker-compose.test.yml")
        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        # Extract port mapping (format: "9432:5432")
        port_mapping = compose_config["services"]["postgres-test"]["ports"][0]
        host_port = int(port_mapping.split(":")[0])

        # Check conftest.py uses same port
        # Read database_fixtures.py to check default password
        conftest_file = Path("tests/fixtures/database_fixtures.py")
        conftest_content = conftest_file.read_text()

        assert (
            f'port=int(os.getenv("POSTGRES_PORT", "{host_port}"))' in conftest_content
            or f"port={host_port}" in conftest_content
        ), (
            f"conftest.py fixtures must use same port as docker-compose.test.yml ({host_port}).\n"
            f"Fix: Update POSTGRES_PORT defaults in conftest.py to {host_port}"
        )

    def test_docker_compose_and_conftest_use_same_user(self):
        """Test: Docker-compose and conftest fixtures must use same user (postgres)."""
        compose_file = Path("docker-compose.test.yml")
        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        postgres_user = compose_config["services"]["postgres-test"]["environment"]["POSTGRES_USER"]

        # Read database_fixtures.py to check default password
        conftest_file = Path("tests/fixtures/database_fixtures.py")
        conftest_content = conftest_file.read_text()

        user_patterns = [
            f'user="{postgres_user}"',
            f"user='{postgres_user}'",
            f'user=os.getenv("POSTGRES_USER", "{postgres_user}")',
            f"user=os.getenv('POSTGRES_USER', '{postgres_user}')",
        ]

        has_correct_user = any(pattern in conftest_content for pattern in user_patterns)

        assert has_correct_user, (
            f"conftest.py fixtures must use same user as docker-compose.test.yml ({postgres_user}).\n"
            f"Expected one of these patterns:\n" + "\n".join(f"  - {p}" for p in user_patterns) + "\n"
            f"Fix: Update POSTGRES_USER defaults in conftest.py to '{postgres_user}'"
        )

    def test_docker_compose_and_conftest_use_same_database(self):
        """Test: Docker-compose creates databases that conftest fixtures connect to."""
        # Docker-compose creates openfga_test initially, but migration script creates gdpr_test
        # Conftest should use gdpr_test for GDPR compliance tests
        expected_db = "gdpr_test"

        # Read database_fixtures.py to check default password
        conftest_file = Path("tests/fixtures/database_fixtures.py")
        conftest_content = conftest_file.read_text()

        # Check that gdpr_test is used as default in connection pool
        assert (
            f'database=os.getenv("POSTGRES_DB", "{expected_db}")' in conftest_content
            or f'database="{expected_db}"' in conftest_content
        ), (
            f"conftest.py fixtures must use {expected_db} database created by migration script.\n"
            f"Fix: Update POSTGRES_DB defaults in conftest.py to '{expected_db}'"
        )

    def test_integration_test_script_sets_postgres_env_vars(self):
        """Test: Integration test script must set all required PostgreSQL environment variables."""
        script_file = Path("scripts/test-integration.sh")
        script_content = script_file.read_text()

        # At minimum, POSTGRES_DB should be set
        assert "POSTGRES_DB=" in script_content, (
            "Integration test script must set POSTGRES_DB environment variable.\n"
            "Fix: Add POSTGRES_DB definition to scripts/test-integration.sh"
        )
