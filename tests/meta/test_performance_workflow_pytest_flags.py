"""
Test that performance regression workflow correctly handles pytest flags.

This test validates the fix for the issue where performance benchmarks fail because:
1. Workflow disables xdist with `-p no:xdist` to avoid pytest-benchmark conflicts
2. But `--dist loadscope` from pyproject.toml addopts is still applied
3. Without xdist plugin, `--dist` flag is unrecognized causing: "pytest: error: unrecognized arguments: --dist"

The fix ensures addopts is overridden to exclude xdist-specific flags when running benchmarks.

Reference: Performance Regression Detection workflow failures (runs 19250359776, 19250511465, etc.)
"""

from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]


def test_performance_workflow_overrides_addopts_to_exclude_xdist_flags():
    """
    Verify that the performance regression workflow overrides addopts to exclude --dist flag.

    When using `-p no:xdist` to disable xdist (required for pytest-benchmark),
    the --dist flag from pyproject.toml addopts must be removed, otherwise pytest fails with:
    "pytest: error: unrecognized arguments: --dist"

    Expected solution: Use `-o addopts="..."` to override addopts without --dist flag
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github/workflows/performance-regression.yaml"

    assert workflow_path.exists(), f"Performance workflow not found: {workflow_path}"

    with open(workflow_path) as f:
        workflow_yaml = yaml.safe_load(f)

    jobs = workflow_yaml.get("jobs", {})
    run_benchmarks_job = jobs.get("run-benchmarks")

    assert run_benchmarks_job is not None, "run-benchmarks job not found"

    # Find the step that runs pytest benchmarks
    pytest_step = None
    for step in run_benchmarks_job.get("steps", []):
        step_name = step.get("name", "").lower()
        run_cmd = step.get("run", "")

        if "benchmark" in step_name and "pytest" in run_cmd:
            pytest_step = step
            break

    assert pytest_step is not None, "pytest benchmark step not found"

    run_cmd = pytest_step.get("run", "")

    # Verify pytest command structure
    assert "pytest" in run_cmd, "Step doesn't run pytest"
    assert "-p no:xdist" in run_cmd, "Missing '-p no:xdist' to disable xdist"
    assert "--benchmark-only" in run_cmd, "Missing '--benchmark-only' flag"

    # CRITICAL: Verify addopts is overridden to exclude --dist
    # Either method works:
    # 1. Use -o addopts="..." to override (preferred)
    # 2. Use PYTEST_ADDOPTS environment variable
    # 3. Use --override-ini addopts="..."

    has_addopts_override = "-o addopts=" in run_cmd or "--override-ini addopts=" in run_cmd or "PYTEST_ADDOPTS=" in run_cmd

    assert has_addopts_override, (
        "pytest benchmark step must override addopts to exclude --dist flag.\n"
        "\n"
        "Problem: pyproject.toml has 'addopts = --dist loadscope', but workflow uses '-p no:xdist'.\n"
        "When xdist is disabled, --dist is unrecognized, causing:\n"
        "  pytest: error: unrecognized arguments: --dist\n"
        "\n"
        "Solution: Override addopts to exclude --dist:\n"
        "  pytest tests/performance/ \\\n"
        "    -p no:xdist \\\n"
        '    -o addopts="-v --strict-markers --tb=short --timeout=60" \\\n'
        "    --benchmark-only \\\n"
        "    --benchmark-json=benchmark-results.json\n"
        "\n"
        f"Current command:\n{run_cmd}"
    )

    # Verify --dist is NOT in the overridden addopts
    if "-o addopts=" in run_cmd or "--override-ini addopts=" in run_cmd:
        # Extract the addopts value
        import re

        match = re.search(r'(?:-o|--override-ini)\s+addopts=["\'](.*?)["\']', run_cmd)
        if match:
            overridden_addopts = match.group(1)
            assert "--dist" not in overridden_addopts, (
                f"Overridden addopts still contains --dist flag: {overridden_addopts}\n"
                "This will cause pytest to fail when xdist is disabled."
            )


def test_performance_workflow_disables_xdist_for_benchmark_compatibility():
    """
    Verify that the performance workflow disables xdist to avoid pytest-benchmark conflicts.

    pytest-benchmark auto-disables when xdist is active, which conflicts with --benchmark-only,
    causing: "Can't have both --benchmark-only and --benchmark-disable options"

    The workflow must use `-p no:xdist` to prevent this.
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github/workflows/performance-regression.yaml"

    with open(workflow_path) as f:
        workflow_yaml = yaml.safe_load(f)

    jobs = workflow_yaml.get("jobs", {})
    run_benchmarks_job = jobs.get("run-benchmarks")

    pytest_step = None
    for step in run_benchmarks_job.get("steps", []):
        run_cmd = step.get("run", "")
        if "pytest" in run_cmd and "--benchmark-only" in run_cmd:
            pytest_step = step
            break

    assert pytest_step is not None

    run_cmd = pytest_step.get("run", "")

    assert "-p no:xdist" in run_cmd, (
        "Performance benchmarks must disable xdist with '-p no:xdist'.\n"
        "\n"
        "Reason: pytest-benchmark auto-disables when xdist is active, causing:\n"
        "  Can't have both --benchmark-only and --benchmark-disable options\n"
        "\n"
        "Solution: Add '-p no:xdist' before --benchmark-only"
    )


def test_performance_workflow_uses_benchmark_only_mode():
    """
    Verify that the performance workflow runs only benchmark tests, skipping regular tests.

    This ensures performance tests are isolated and run with proper benchmark configuration.
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github/workflows/performance-regression.yaml"

    with open(workflow_path) as f:
        workflow_yaml = yaml.safe_load(f)

    jobs = workflow_yaml.get("jobs", {})
    run_benchmarks_job = jobs.get("run-benchmarks")

    pytest_step = None
    for step in run_benchmarks_job.get("steps", []):
        run_cmd = step.get("run", "")
        # Look for the step that actually runs pytest (not just mentions benchmark)
        if "pytest" in run_cmd and "--benchmark" in run_cmd:
            pytest_step = step
            break

    assert pytest_step is not None, "Could not find pytest benchmark step in workflow"

    run_cmd = pytest_step.get("run", "")

    assert "--benchmark-only" in run_cmd, "Performance workflow must use --benchmark-only to run only benchmark tests"

    assert "tests/performance/" in run_cmd, "Performance workflow should target tests/performance/ directory"


def test_pyproject_toml_addopts_includes_dist_flag():
    """
    Verify that pyproject.toml addopts includes --dist flag (for normal test runs).

    This confirms that the --dist flag exists in the default config,
    which is why the performance workflow needs to override it.
    """
    # Python 3.10 compatibility: tomllib added in 3.11, use tomli backport for <3.11
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    repo_root = Path(__file__).parent.parent.parent
    pyproject_path = repo_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    addopts = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")

    assert "--dist" in addopts or "-n" in addopts, (
        "pyproject.toml addopts should include xdist flags (--dist or -n) for normal test runs.\n"
        "This test documents why the performance workflow needs to override addopts."
    )
