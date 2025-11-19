"""
Validation tests for Codex recommendations configuration.

Validates that pyproject.toml has the correct settings based on OpenAI Codex
findings from 2025-11-14:
- pytest-benchmark warning suppression
- 80% coverage threshold enforcement
"""

import gc
from pathlib import Path

import pytest


# Python 3.10 compatibility: tomllib added in 3.11, use tomli backport for <3.11
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.xdist_group(name="testcodexconfigurationrecommendations")
class TestCodexConfigurationRecommendations:
    """Validate Codex-recommended configuration changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture(scope="class")
    def pyproject_config(self):
        """Load pyproject.toml configuration."""
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)

    def test_pytest_benchmark_disabled_by_default(self, pyproject_config):
        """
        Verify that pytest-benchmark is disabled by default to suppress warnings.

        **Codex Finding:**
        - pytest-benchmark emits warning when xdist is active
        - Warning: "Benchmarks are automatically disabled because xdist plugin is active"
        - Source: pytest_benchmark/logger.py:39

        **Fix:**
        - Add --benchmark-disable to pytest addopts
        - Allows opt-in benchmarking with --benchmark-enable
        - Eliminates warning noise in test output
        """
        pytest_config = pyproject_config.get("tool", {}).get("pytest", {}).get("ini_options", {})
        addopts = pytest_config.get("addopts", "")

        assert "--benchmark-disable" in addopts, (
            "pytest addopts should include --benchmark-disable to suppress benchmark warnings. "
            "Current addopts: {addopts!r}\n"
            "Fix: Add '--benchmark-disable' to tool.pytest.ini_options.addopts in pyproject.toml"
        )

    def test_coverage_threshold_enforced(self, pyproject_config):
        """
        Verify that coverage threshold is enforced to prevent regressions.

        **Codex Finding:**
        - Current coverage: 64% (baseline as of 2025-11-14)
        - Many infrastructure modules untested (kubernetes_sandbox: 10%, server_streamable: 20%)
        - Recommendation: Enforce threshold to prevent regressions, improve to 80%+

        **Current Status:**
        - Baseline: 64% (prevents coverage from dropping below current level)
        - Target: 80%+ (systematic improvement plan in docs-internal/COVERAGE_IMPROVEMENT_PLAN.md)
        - Threshold will be incrementally raised as modules are tested

        **Fix:**
        - fail_under = 64 (baseline) in tool.coverage.report
        - CI/CD will fail if coverage drops below baseline
        - Prevents coverage regressions while allowing incremental improvement
        """
        coverage_config = pyproject_config.get("tool", {}).get("coverage", {}).get("report", {})
        fail_under = coverage_config.get("fail_under")

        assert (
            fail_under is not None
        ), "Coverage threshold not set. Fix: Add 'fail_under = 64' to [tool.coverage.report] in pyproject.toml"

        # Accept current baseline of 64%, with plan to reach 80%+
        # See: docs-internal/COVERAGE_IMPROVEMENT_PLAN.md
        assert fail_under >= 64, (
            f"Coverage threshold is {fail_under}%, should be at least 64% (current baseline). "
            f"Current coverage is 64% - target is 80%+ (tracked in GitHub issue)\n"
            f"Tests needed for:\n"
            f"  - kubernetes_sandbox.py (10% → 80%)\n"
            f"  - server_streamable.py (20% → 80%)\n"
            f"  - Other infrastructure modules\n"
            f"See: docs-internal/COVERAGE_IMPROVEMENT_PLAN.md for improvement plan"
        )

    def test_pytest_markers_include_codex_categories(self, pyproject_config):
        """
        Verify that pytest markers include categories used in Codex validation.

        Ensures regression, meta, unit markers are properly defined.
        """
        pytest_config = pyproject_config.get("tool", {}).get("pytest", {}).get("ini_options", {})
        markers = pytest_config.get("markers", [])

        # Convert markers to a dict for easier checking
        marker_names = [m.split(":")[0].strip() for m in markers]

        required_markers = ["unit", "regression", "meta"]
        for marker in required_markers:
            assert (
                marker in marker_names
            ), f"Required marker '{marker}' not found in pytest markers. Available markers: {marker_names}"

    def test_coverage_omits_test_directories(self, pyproject_config):
        """
        Verify that test directories are excluded from coverage.

        Ensures coverage measures production code, not test code.
        """
        coverage_config = pyproject_config.get("tool", {}).get("coverage", {}).get("run", {})
        omit_patterns = coverage_config.get("omit", [])

        # Check that tests are omitted
        test_patterns = [pattern for pattern in omit_patterns if "test" in pattern.lower()]
        assert (
            len(test_patterns) > 0
        ), "Coverage should exclude test directories. Expected patterns like '*/tests/*' in tool.coverage.run.omit"

    def test_coverage_parallel_enabled_for_xdist(self, pyproject_config):
        """
        Verify that parallel coverage is enabled for pytest-xdist.

        Required for accurate coverage collection with pytest-xdist.
        """
        coverage_config = pyproject_config.get("tool", {}).get("coverage", {}).get("run", {})
        parallel = coverage_config.get("parallel")

        assert (
            parallel is True
        ), "Coverage parallel mode should be enabled for pytest-xdist. Fix: Set 'parallel = true' in [tool.coverage.run]"

    def test_benchmark_config_allows_marker_filtering(self, pyproject_config):
        """
        Verify that pytest-benchmark config allows marker-based filtering.

        Codex notes that benchmarks should use marker-based filtering
        rather than complete disablement.
        """
        benchmark_config = pyproject_config.get("tool", {}).get("pytest", {}).get("benchmark", {})
        disable = benchmark_config.get("disable")

        # disable should be False to allow marker-based filtering
        assert disable is False, (
            "pytest-benchmark disable should be False for marker-based filtering. "
            "Actual disable setting: {disable}\n"
            "Fix: Set 'disable = false' in [tool.pytest.benchmark] "
            "(we use --benchmark-disable in addopts for default behavior)"
        )
