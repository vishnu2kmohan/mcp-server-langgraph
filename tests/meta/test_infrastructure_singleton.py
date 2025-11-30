"""
Meta-tests validating single shared test infrastructure pattern.

This test suite enforces the architectural decision to use a single shared
test infrastructure instance across all pytest-xdist workers, with logical
isolation via PostgreSQL schemas, Redis DB indices, and OpenFGA stores.

Architecture Decision:
- ONE docker-compose instance runs on fixed base ports (9432, 9379, etc.)
- ALL xdist workers (gw0, gw1, gw2, ...) connect to the SAME ports
- Isolation achieved via:
  - PostgreSQL: Separate schemas per worker (test_worker_gw0, test_worker_gw1)
  - Redis: Separate DB indices per worker (DB 1, 2, 3, ...)
  - OpenFGA: Separate stores per worker (test_store_gw0, test_store_gw1)
  - Qdrant: Separate collections per worker
  - Keycloak: Separate realms per worker

This is faster and simpler than per-worker infrastructure with dynamic port allocation.

Related:
- tests/conftest.py:582-619 (test_infrastructure_ports fixture)
- docker-compose.test.yml (fixed port mappings)
- tests/regression/test_pytest_xdist_port_conflicts.py (validates port behavior)
"""

import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.meta
@pytest.mark.xdist_group(name="testinfrastructuresingleton")
class TestInfrastructureSingleton:
    """Validate single shared infrastructure architecture."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_infrastructure_ports_are_fixed_regardless_of_worker(self, test_infrastructure_ports):
        """
        Test that test_infrastructure_ports returns FIXED base ports.

        All xdist workers should connect to the same infrastructure ports,
        regardless of worker ID. This enforces the single-instance architecture.
        """
        # Expected base ports (from docker-compose.test.yml)
        # Test environment uses consolidated Redis (both keys point to same port)
        expected_ports = {
            "postgres": 9432,
            "redis_checkpoints": 9379,
            "redis_sessions": 9379,  # Same as checkpoints (consolidated)
            "qdrant": 9333,
            "qdrant_grpc": 9334,
            "openfga_http": 9080,
            "openfga_grpc": 9081,
            "keycloak": 9082,
            "keycloak_management": 9900,
        }

        # Test current worker's ports
        assert test_infrastructure_ports == expected_ports, (
            f"Current worker should use base ports, got {test_infrastructure_ports}\n"
            f"Expected: {expected_ports}\n"
            f"\n"
            f"All workers must connect to the SAME infrastructure ports.\n"
            f"Isolation is achieved via PostgreSQL schemas, Redis DBs, etc."
        )

    def test_no_worker_offset_calculation(self, test_infrastructure_ports):
        """
        Test that there is NO port offset calculation based on worker ID.

        The old multi-instance approach calculated offsets (gw0=+0, gw1=+100, etc.).
        The new single-instance approach uses fixed ports for all workers.
        """
        # These should be BASE ports, NOT offset ports
        assert test_infrastructure_ports["postgres"] == 9432, (
            f"All workers should use base port 9432, not offset ports\n"
            f"Got: {test_infrastructure_ports['postgres']}\n"
            f"\n"
            f"The single-instance architecture does NOT use port offsets."
        )
        assert test_infrastructure_ports["redis_checkpoints"] == 9379, (
            f"All workers should use base port 9379, not offset ports\n"
            f"Got: {test_infrastructure_ports['redis_checkpoints']}\n"
            f"\n"
            f"Test uses consolidated Redis (9379) for both checkpoints and sessions."
        )
        assert test_infrastructure_ports["redis_sessions"] == 9379, (
            f"All workers should use base port 9379 (same as checkpoints)\n"
            f"Got: {test_infrastructure_ports['redis_sessions']}\n"
            f"\n"
            f"Test consolidates Redis for simplicity (production uses separate instances)."
        )

    def test_docker_compose_ports_match_fixture_ports(self, test_infrastructure_ports):
        """
        Test that docker-compose.test.yml ports match test_infrastructure_ports.

        This ensures consistency between the infrastructure definition and
        the ports tests expect to connect to.
        """
        # Read docker-compose.test.yml
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"
        assert compose_file.exists(), f"docker-compose.test.yml not found at {compose_file}"

        content = compose_file.read_text()

        # Get expected ports from fixture
        ports = test_infrastructure_ports

        # Validate postgres port
        assert f'"{ports["postgres"]}:5432"' in content or f"'{ports['postgres']}:5432'" in content, (
            f"docker-compose.test.yml should map host port {ports['postgres']} to postgres container port 5432"
        )

        # Validate consolidated redis port (used for both checkpoints and sessions)
        assert f'"{ports["redis_checkpoints"]}:6379"' in content or f"'{ports['redis_checkpoints']}:6379'" in content, (
            f"docker-compose.test.yml should map host port {ports['redis_checkpoints']} to redis container port 6379"
        )

        # Verify sessions use same port as checkpoints (consolidated)
        assert ports["redis_sessions"] == ports["redis_checkpoints"], (
            f"Test environment should use consolidated Redis\n"
            f"redis_sessions ({ports['redis_sessions']}) should equal "
            f"redis_checkpoints ({ports['redis_checkpoints']})"
        )

        # Validate OpenFGA HTTP port
        assert f'"{ports["openfga_http"]}:8080"' in content or f"'{ports['openfga_http']}:8080'" in content, (
            f"docker-compose.test.yml should map host port {ports['openfga_http']} to openfga container port 8080"
        )

    def test_logical_isolation_mechanisms_documented(self, test_infrastructure_ports):
        """
        Test that the codebase documents how logical isolation works.

        Since all workers share the same infrastructure, we need clear
        documentation of how they achieve test isolation.
        """
        # This test validates that documentation exists
        # The actual isolation mechanisms are tested elsewhere

        import inspect

        from tests.conftest import test_infrastructure_ports as fixture_func

        # Get the actual function (unwrap pytest decorator)
        func = fixture_func
        while hasattr(func, "__wrapped__"):
            func = func.__wrapped__

        # Check that fixture has docstring explaining architecture
        docstring = inspect.getdoc(func)
        assert docstring is not None, (
            "test_infrastructure_ports fixture must have docstring explaining "
            "single-instance architecture and logical isolation mechanisms"
        )

        docstring_lower = docstring.lower()

        # Should mention key concepts for single-instance architecture
        assert "single" in docstring_lower or "shared" in docstring_lower or "session" in docstring_lower, (
            f"Fixture docstring should explain single/shared infrastructure approach.\n"
            f"Current docstring:\n{docstring}\n\n"
            f"Expected keywords: 'single', 'shared', or 'session'"
        )


@pytest.mark.meta
@pytest.mark.xdist_group(name="testworkerisolationmechanisms")
class TestWorkerIsolationMechanisms:
    """Validate that logical isolation mechanisms work correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_postgres_schema_isolation_exists(self):
        """
        Test that PostgreSQL uses separate schemas per worker.

        This is HOW workers sharing the same PostgreSQL port (9432)
        achieve data isolation.
        """
        # This test validates the isolation mechanism exists in the codebase
        # Actual runtime isolation is tested in integration tests

        from tests.utils.worker_utils import get_worker_id

        # The worker_utils module should provide worker ID for schema naming
        worker_id = get_worker_id()
        assert worker_id.startswith("gw") or worker_id == "master", (
            f"Worker ID should be gw0, gw1, etc. or 'master', got: {worker_id}"
        )

    def test_worker_utils_available(self):
        """
        Test that worker utility functions are available.

        These utilities help tests achieve logical isolation by providing
        worker-specific identifiers for schemas, DB indices, store names, etc.

        NOTE: get_worker_port_offset was removed (2025-11-30) as part of
        Single Shared Infrastructure migration. All workers use fixed ports.
        """
        from tests.utils.worker_utils import get_worker_id, get_worker_num, get_worker_resource_summary

        # All utility functions should be callable
        worker_id = get_worker_id()
        worker_num = get_worker_num()
        resource_summary = get_worker_resource_summary()

        # Worker ID should be string like "gw0", "gw1", etc.
        assert isinstance(worker_id, str), f"Worker ID should be string, got {type(worker_id)}"

        # Worker num should be int (0, 1, 2, ...)
        assert isinstance(worker_num, int), f"Worker num should be int, got {type(worker_num)}"

        # Resource summary should be dict with fixed_ports (Single Shared Infrastructure)
        assert isinstance(resource_summary, dict), f"Resource summary should be dict, got {type(resource_summary)}"
        assert "fixed_ports" in resource_summary, "Resource summary should contain fixed_ports"


@pytest.mark.meta
@pytest.mark.xdist_group(name="testregressiontestcorrectness")
class TestRegressionTestCorrectness:
    """Validate that port conflict regression tests expect correct behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_regression_tests_expect_fixed_ports(self):
        """
        Test that regression tests validate FIXED port behavior.

        After fixing the architecture, the regression tests should assert
        that ports are ALWAYS the base ports (9432, etc.), not worker-offset.

        This test validates that test_pytest_xdist_port_conflicts.py has
        been updated to expect the correct (fixed port) behavior.
        """
        regression_test = Path(__file__).parent.parent / "regression" / "test_pytest_xdist_port_conflicts.py"
        assert regression_test.exists(), f"Regression test not found: {regression_test}"

        content = regression_test.read_text()

        # The test should validate that ports are fixed (base ports)
        # Look for assertions about port values
        assert "9432" in content, "Regression test should check for base postgres port 9432"

        # Should NOT assert that broken behavior is correct
        # (But CAN document old broken behavior for context)
        if "hardcoded" in content.lower() or "broken" in content.lower():
            # Check if assertions validate broken behavior vs document it
            lines = content.split("\n")  # Keep original case for checking
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if "hardcoded" in line_lower or "broken" in line_lower:
                    # Skip if this is explaining/preventing regression (legitimate documentation)
                    if any(
                        keyword in line_lower
                        for keyword in ["old (broken)", "prevents regression", "prevent regression", "was broken"]
                    ):
                        continue

                    # Check if an assertion on this line expects broken values
                    if "assert" in line_lower and not line.strip().startswith("#"):
                        # This is an actual assertion (not a comment) with "broken"/"hardcoded"
                        pytest.fail(
                            f"Regression test appears to validate BROKEN behavior:\n"
                            f"Line {i + 1}: {line}\n\n"
                            f"After fixing the architecture, tests should validate that ports "
                            f"are CORRECTLY fixed to base values, not that they are incorrectly hardcoded."
                        )
