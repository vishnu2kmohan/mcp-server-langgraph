"""
Unit tests for GKE Autopilot compliance validator.

TDD Context:
- RED (2025-11-12): 7 CI/CD workflows failing due to GKE Autopilot violations
- GREEN: Created validator and fixed all violations
- REFACTOR: These tests prevent regression of validation logic

Following TDD: Tests ensure validator correctly identifies non-compliant resources.
"""

import gc
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for importing validator
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validators"))


from validate_gke_autopilot_compliance import GKEAutopilotValidator  # noqa: E402

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testcpuparsing")
class TestCPUParsing:
    """Test CPU string parsing to millicores"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_parse_cpu_millicores(self):
        """Test parsing CPU values in millicores format"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_cpu("100m") == 100.0
        assert validator.parse_cpu("250m") == 250.0
        assert validator.parse_cpu("500m") == 500.0
        assert validator.parse_cpu("1000m") == 1000.0

    def test_parse_cpu_cores(self):
        """Test parsing CPU values in cores format"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_cpu("1") == 1000.0
        assert validator.parse_cpu("2") == 2000.0
        assert validator.parse_cpu("0.5") == 500.0
        assert validator.parse_cpu("0.25") == 250.0

    def test_parse_cpu_empty(self):
        """Test parsing empty/None CPU values"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_cpu("") == 0.0
        assert validator.parse_cpu(None) == 0.0


@pytest.mark.xdist_group(name="testmemoryparsing")
class TestMemoryParsing:
    """Test memory string parsing to MiB"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_parse_memory_mebibytes(self):
        """Test parsing memory in MiB format"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_memory("256Mi") == 256.0
        assert validator.parse_memory("512Mi") == 512.0
        assert validator.parse_memory("1024Mi") == 1024.0

    def test_parse_memory_gibibytes(self):
        """Test parsing memory in GiB format"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_memory("1Gi") == 1024.0
        assert validator.parse_memory("2Gi") == 2048.0
        assert validator.parse_memory("0.5Gi") == 512.0

    def test_parse_memory_kibibytes(self):
        """Test parsing memory in KiB format"""
        validator = GKEAutopilotValidator(".")
        # KiB to MiB conversion
        assert validator.parse_memory("1024Ki") == 1.0
        assert validator.parse_memory("512Ki") == 0.5

    def test_parse_memory_empty(self):
        """Test parsing empty/None memory values"""
        validator = GKEAutopilotValidator(".")
        assert validator.parse_memory("") == 0.0
        assert validator.parse_memory(None) == 0.0


@pytest.mark.xdist_group(name="testcpuratiovalidation")
class TestCPURatioValidation:
    """Test CPU limit/request ratio validation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cpu_ratio_compliant(self):
        """Test that compliant CPU ratios pass validation"""
        validator = GKEAutopilotValidator(".")

        # Ratio = 4.0 (exactly at limit)
        validator.validate_cpu_ratio("test-deployment", "test-container", "250m", "1000m")
        assert len(validator.errors) == 0

        # Ratio = 2.0 (well below limit)
        validator.validate_cpu_ratio("test-deployment", "test-container", "500m", "1000m")
        assert len(validator.errors) == 0

    def test_cpu_ratio_violation_5x(self):
        """Test that 5.0x CPU ratio is flagged as violation"""
        validator = GKEAutopilotValidator(".")

        # Ratio = 5.0 (exceeds max 4.0)
        validator.validate_cpu_ratio("otel-collector", "otel-collector", "200m", "1000m")
        assert len(validator.errors) == 1
        assert "CPU limit/request ratio 5.00 exceeds max 4.0" in validator.errors[0]
        assert "otel-collector/otel-collector" in validator.errors[0]

    def test_cpu_ratio_violation_10x(self):
        """Test that 10.0x CPU ratio is flagged as violation"""
        validator = GKEAutopilotValidator(".")

        # Ratio = 10.0 (significantly exceeds limit)
        validator.validate_cpu_ratio("qdrant", "qdrant", "100m", "1000m")
        assert len(validator.errors) == 1
        assert "CPU limit/request ratio 10.00 exceeds max 4.0" in validator.errors[0]

    def test_cpu_ratio_violation_8x(self):
        """Test that 8.0x CPU ratio is flagged as violation"""
        validator = GKEAutopilotValidator(".")

        # Ratio = 8.0 (postgres original config)
        validator.validate_cpu_ratio("postgres", "postgres", "250m", "2000m")
        assert len(validator.errors) == 1
        assert "CPU limit/request ratio 8.00 exceeds max 4.0" in validator.errors[0]

    def test_cpu_ratio_fixed_values(self):
        """Test that fixed CPU ratios (4.0x) pass validation"""
        validator = GKEAutopilotValidator(".")

        # All fixed ratios should be 4.0 or less
        test_cases = [
            ("otel-collector", "250m", "1000m"),  # 4.0
            ("qdrant", "250m", "1000m"),  # 4.0
            ("postgres", "500m", "2000m"),  # 4.0
            ("redis-session", "125m", "500m"),  # 4.0
            ("mcp-server", "125m", "500m"),  # 4.0
        ]

        for name, request, limit in test_cases:
            validator.validate_cpu_ratio(name, name, request, limit)

        assert len(validator.errors) == 0, "All fixed ratios should pass validation"


@pytest.mark.xdist_group(name="testgkeautopilotconstants")
class TestGKEAutopilotConstants:
    """Test that GKE Autopilot constants are correctly defined"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_max_cpu_ratio(self):
        """Ensure MAX_CPU_RATIO is set to 4.0"""
        assert GKEAutopilotValidator.MAX_CPU_RATIO == 4.0

    def test_max_memory_ratio(self):
        """Ensure MAX_MEMORY_RATIO is set to 4.0"""
        assert GKEAutopilotValidator.MAX_MEMORY_RATIO == 4.0

    def test_cpu_limits_validation_with_constants_matches_expected_values(self):
        """Ensure CPU limit constants are correctly defined"""
        # Updated 2025-12-04: Aligned with staging-mcp-staging-limits LimitRange
        assert GKEAutopilotValidator.MIN_CPU_REQUEST == "100m"
        assert GKEAutopilotValidator.MAX_CPU_LIMIT == "4"

    def test_memory_limits_validation_with_constants_matches_expected_values(self):
        """Ensure memory limit constants are correctly defined"""
        # Updated 2025-12-04: Aligned with staging-mcp-staging-limits LimitRange
        assert GKEAutopilotValidator.MIN_MEMORY_REQUEST == "128Mi"
        assert GKEAutopilotValidator.MAX_MEMORY_LIMIT == "8Gi"


@pytest.mark.xdist_group(name="testregressionprevention")
class TestRegressionPrevention:
    """
    Regression tests to prevent the specific failures we encountered.

    These tests encode the exact violations that occurred in the CI/CD runs.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_prevent_otel_collector_regression(self):
        """Prevent regression of otel-collector CPU ratio (was 5.0, now 4.0)"""
        validator = GKEAutopilotValidator(".")

        # OLD (failing): 200m/1000m = 5.0
        validator.validate_cpu_ratio("otel-collector", "otel-collector", "200m", "1000m")
        assert len(validator.errors) == 1, "Old config should fail"

        validator = GKEAutopilotValidator(".")
        # NEW (fixed): 250m/1000m = 4.0
        validator.validate_cpu_ratio("otel-collector", "otel-collector", "250m", "1000m")
        assert len(validator.errors) == 0, "Fixed config should pass"

    def test_prevent_qdrant_regression(self):
        """Prevent regression of qdrant CPU ratio (was 10.0, now 4.0)"""
        validator = GKEAutopilotValidator(".")

        # OLD (failing): 100m/1000m = 10.0
        validator.validate_cpu_ratio("qdrant", "qdrant", "100m", "1000m")
        assert len(validator.errors) == 1

        validator = GKEAutopilotValidator(".")
        # NEW (fixed): 250m/1000m = 4.0
        validator.validate_cpu_ratio("qdrant", "qdrant", "250m", "1000m")
        assert len(validator.errors) == 0

    def test_prevent_postgres_regression(self):
        """Prevent regression of postgres CPU ratio (was 8.0, now 4.0)"""
        validator = GKEAutopilotValidator(".")

        # OLD (failing): 250m/2000m = 8.0
        validator.validate_cpu_ratio("postgres", "postgres", "250m", "2000m")
        assert len(validator.errors) == 1

        validator = GKEAutopilotValidator(".")
        # NEW (fixed): 500m/2000m = 4.0
        validator.validate_cpu_ratio("postgres", "postgres", "500m", "2000m")
        assert len(validator.errors) == 0

    def test_prevent_redis_session_regression(self):
        """Prevent regression of redis-session CPU ratio (was 5.0, now 4.0)"""
        validator = GKEAutopilotValidator(".")

        # OLD (failing): 100m/500m = 5.0
        validator.validate_cpu_ratio("redis-session", "redis", "100m", "500m")
        assert len(validator.errors) == 1

        validator = GKEAutopilotValidator(".")
        # NEW (fixed): 125m/500m = 4.0
        validator.validate_cpu_ratio("redis-session", "redis", "125m", "500m")
        assert len(validator.errors) == 0
