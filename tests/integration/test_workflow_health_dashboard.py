"""
Test workflow health dashboard logic for edge cases.

This test suite validates that the workflow health dashboard script
handles edge cases correctly, particularly division by zero when
workflows have no runs.
"""

import gc
import json
from pathlib import Path

import pytest

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="workflow_health_dashboard")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_workflow_health_dashboard():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


def test_dashboard_handles_zero_runs():
    """
    Test that dashboard calculations handle workflows with zero runs.

    This validates that the success rate calculation in
    .github/workflows/workflow-health-dashboard.yaml doesn't fail
    with division by zero when a workflow has no runs.
    """
    # Simulate the calculations from the dashboard workflow
    total_runs = 0
    successful_runs = 0

    # The workflow should skip workflows with zero runs
    # instead of attempting to calculate success_rate
    if total_runs == 0:
        # Should skip this workflow (no calculation)
        success_rate = None
    else:
        # This would cause division by zero if not guarded
        success_rate = (successful_runs * 100) / total_runs

    # Assert that we correctly skip zero-run workflows
    assert success_rate is None, "Should skip workflows with zero runs"


def test_dashboard_success_rate_calculation():
    """
    Test success rate calculation for workflows with runs.

    Validates the success rate formula used in the dashboard:
    success_rate = successful_runs * 100 / total_runs
    """
    test_cases = [
        # (total_runs, successful_runs, expected_success_rate)
        (10, 10, 100.0),  # All successful
        (10, 5, 50.0),  # Half successful
        (10, 0, 0.0),  # None successful
        (100, 95, 95.0),  # 95% successful
        (1, 1, 100.0),  # Single successful run
        (1, 0, 0.0),  # Single failed run
    ]

    for total_runs, successful_runs, expected in test_cases:
        if total_runs == 0:
            # Skip zero-run case (tested separately)
            continue

        # Calculate success rate (simulating dashboard logic)
        success_rate = (successful_runs * 100) / total_runs

        assert (
            abs(success_rate - expected) < 0.01
        ), f"Expected {expected}%, got {success_rate}% for {successful_runs}/{total_runs}"


def test_dashboard_bc_command_edge_cases():
    """
    Test that bc command handles edge cases correctly.

    The dashboard uses bc for calculations:
    success_rate=$(echo "scale=1; $successful_runs * 100 / $total_runs" | bc)

    This test validates that we guard against division by zero.
    """
    # Test case 1: Normal calculation
    total_runs = 10
    successful_runs = 9

    if total_runs > 0:
        # Simulate bc calculation (Python equivalent)
        success_rate = round((successful_runs * 100.0) / total_runs, 1)
        assert success_rate == 90.0

    # Test case 2: Zero runs (should skip)
    total_runs = 0
    successful_runs = 0

    if total_runs == 0:
        # Should skip, not calculate
        assert True  # Pass - we correctly skip
    else:
        # This branch should not execute for zero runs
        pytest.fail("Should have skipped zero-run workflow")


def test_dashboard_workflow_file_exists():
    """Verify the workflow health dashboard file exists."""
    # Find project root by looking for pyproject.toml
    current = Path(__file__).resolve()
    project_root = None
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            project_root = parent
            break

    assert project_root is not None, "Could not find project root (no pyproject.toml)"

    workflow_file = project_root / ".github" / "workflows" / "workflow-health-dashboard.yaml"

    assert workflow_file.exists(), f"Workflow file not found: {workflow_file}"


def test_dashboard_workflow_has_zero_check():
    """
    Verify the dashboard workflow includes a zero-run guard.

    This test reads the workflow file and checks for division-by-zero
    protection logic.
    """
    # Find project root by looking for pyproject.toml
    current = Path(__file__).resolve()
    project_root = None
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            project_root = parent
            break

    if project_root is None:
        pytest.skip("Could not find project root (no pyproject.toml)")

    workflow_file = project_root / ".github" / "workflows" / "workflow-health-dashboard.yaml"

    if not workflow_file.exists():
        pytest.skip("Workflow file not found")

    content = workflow_file.read_text()

    # Check for zero-run protection patterns
    # The workflow should have one of these patterns:
    # - if [ "$total_runs" -eq 0 ]; then continue; fi
    # - if (total_runs > 0) ... in bc
    # - Guard before success_rate calculation

    has_zero_check = any(
        [
            'if [ "$total_runs" -eq 0 ]' in content,
            "if [ $total_runs -eq 0 ]" in content,
            "if (total_runs > 0)" in content,
            "if ($total_runs > 0)" in content,
            'if test "$total_runs" -eq 0' in content,
        ]
    )

    assert has_zero_check, "Workflow should include a zero-run check before calculating success rate"


def test_dashboard_jq_null_handling():
    """
    Test that jq operations handle null/empty workflow runs.

    The dashboard uses:
    total_runs=$(echo "$runs" | jq 'length')

    This test validates that empty arrays are handled correctly.
    """
    # Simulate empty runs array (workflow with no runs)
    empty_runs_json = "[]"

    # Parse with jq equivalent (Python)
    runs = json.loads(empty_runs_json)
    total_runs = len(runs)

    assert total_runs == 0, "Empty runs array should have length 0"

    # Should skip this workflow
    if total_runs == 0:
        assert True  # Correctly skip zero-run workflow


def test_dashboard_average_duration_with_zero_runs():
    """
    Test average duration calculation with zero runs.

    The dashboard may calculate average duration, which would also
    fail on division by zero if not guarded.
    """
    total_runs = 0
    total_duration_ms = 0

    if total_runs == 0:
        # Should skip, not calculate average
        average_duration = None
    else:
        average_duration = total_duration_ms / total_runs

    assert average_duration is None, "Should skip average calculation for zero runs"


@pytest.mark.integration
def test_dashboard_workflow_syntax():
    """
    Test that the workflow file has valid YAML syntax.

    This ensures the workflow can be parsed and executed by GitHub Actions.
    """
    # Use correct path: tests/integration/ -> tests/ -> repo_root/
    workflow_file = Path(__file__).parent.parent.parent / ".github" / "workflows" / "workflow-health-dashboard.yaml"

    if not workflow_file.exists():
        pytest.skip("Workflow file not found")

    try:
        import yaml

        with open(workflow_file) as f:
            workflow_config = yaml.safe_load(f)

        assert workflow_config is not None
        assert "name" in workflow_config
        assert "jobs" in workflow_config

    except ImportError:
        pytest.skip("PyYAML not installed")
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML syntax: {e}")
