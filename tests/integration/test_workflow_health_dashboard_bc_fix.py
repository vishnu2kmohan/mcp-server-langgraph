"""
Test workflow health dashboard calculations without bc dependency.

This test ensures the workflow can perform calculations using awk
instead of bc, which is not available in Ubuntu 24.04 GitHub Actions runners.
"""

import gc
import subprocess
from pathlib import Path

import pytest

# Mark as integration test with xdist_group for worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="workflow_health_dashboard_bc")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_workflow_health_dashboard_bc_fix():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


def test_awk_percentage_calculation():
    """
    Test that awk can calculate success rate percentages.

    This replaces the bc calculation:
    success_rate=$(echo "scale=1; $successful_runs * 100 / $total_runs" | bc)

    With awk:
    success_rate=$(awk "BEGIN {printf \"%.1f\", $successful_runs * 100 / $total_runs}")
    """
    test_cases = [
        # (total_runs, successful_runs, expected_success_rate)
        (10, 10, "100.0"),
        (10, 5, "50.0"),
        (10, 9, "90.0"),
        (100, 95, "95.0"),
        (1, 1, "100.0"),
        (7, 3, "42.9"),
    ]

    for total_runs, successful_runs, expected in test_cases:
        # Simulate awk calculation
        cmd = f'awk "BEGIN {{printf \\"%.1f\\", {successful_runs} * 100 / {total_runs}}}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, timeout=60)  # nosec B602
        success_rate = result.stdout.strip()

        assert success_rate == expected, (
            f"Expected {expected}%, got {success_rate}% " f"for {successful_runs}/{total_runs} using awk"
        )


def test_awk_comparison_calculations():
    """
    Test that awk can perform comparison calculations.

    This replaces bc comparison:
    if (( $(echo "$success_rate >= 95" | bc -l) )); then

    With awk:
    if (( $(awk "BEGIN {print ($success_rate >= 95)}") )); then
    """
    test_cases = [
        # (success_rate, threshold, expected_result)
        ("100.0", "95", "1"),  # 100 >= 95 -> true (1)
        ("95.0", "95", "1"),  # 95 >= 95 -> true (1)
        ("94.9", "95", "0"),  # 94.9 >= 95 -> false (0)
        ("80.0", "80", "1"),  # 80 >= 80 -> true (1)
        ("79.9", "80", "0"),  # 79.9 >= 80 -> false (0)
    ]

    for success_rate, threshold, expected in test_cases:
        cmd = f'awk "BEGIN {{print ({success_rate} >= {threshold})}}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, timeout=60)  # nosec B602
        comparison_result = result.stdout.strip()

        assert comparison_result == expected, (
            f"Expected {expected} for {success_rate} >= {threshold}, " f"got {comparison_result} using awk"
        )


def test_awk_duration_formatting():
    """
    Test that awk can format durations correctly.

    This replaces bc duration calculation:
    duration_str="$(echo "scale=1; $avg_duration / 3600" | bc)h"

    With awk:
    duration_str="$(awk "BEGIN {printf \"%.1f\", $avg_duration / 3600}")h"
    """
    test_cases = [
        # (avg_duration_seconds, divisor, expected_result)
        (7200, 3600, "2.0"),  # 2 hours
        (5400, 3600, "1.5"),  # 1.5 hours
        (180, 60, "3.0"),  # 3 minutes
        (150, 60, "2.5"),  # 2.5 minutes
    ]

    for duration, divisor, expected in test_cases:
        cmd = f'awk "BEGIN {{printf \\"%.1f\\", {duration} / {divisor}}}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, timeout=60)  # nosec B602
        formatted_duration = result.stdout.strip()

        assert formatted_duration == expected, (
            f"Expected {expected} for {duration} / {divisor}, " f"got {formatted_duration} using awk"
        )


def test_awk_integer_formatting():
    """
    Test that awk can format integers correctly.

    This replaces bc integer calculation:
    duration_str="$(echo "scale=0; $avg_duration / 60" | bc)m"

    With awk:
    duration_str="$(awk "BEGIN {printf \"%d\", $avg_duration / 60}")m"
    """
    test_cases = [
        # (avg_duration_seconds, divisor, expected_result)
        (120, 60, "2"),  # 2 minutes
        (180, 60, "3"),  # 3 minutes
        (150, 60, "2"),  # 2.5 minutes -> 2 (integer)
        (45, 1, "45"),  # 45 seconds
    ]

    for duration, divisor, expected in test_cases:
        cmd = f'awk "BEGIN {{printf \\"%d\\", {duration} / {divisor}}}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, timeout=60)  # nosec B602
        formatted_duration = result.stdout.strip()

        assert formatted_duration == expected, (
            f"Expected {expected} for {duration} / {divisor}, " f"got {formatted_duration} using awk"
        )


@pytest.mark.integration
def test_workflow_uses_awk_not_bc():
    """
    Verify the workflow file uses awk instead of bc.

    This ensures we don't depend on bc which is not available
    in Ubuntu 24.04 GitHub Actions runners.
    """
    workflow_file = Path(__file__).parent.parent / ".github" / "workflows" / "workflow-health-dashboard.yaml"

    if not workflow_file.exists():
        pytest.skip("Workflow file not found")

    content = workflow_file.read_text()

    # Should NOT use bc
    assert "| bc" not in content, "Workflow should not use 'bc' command"
    assert "bc -l" not in content, "Workflow should not use 'bc -l' command"

    # SHOULD use awk for calculations
    has_awk = "awk" in content and "printf" in content

    assert has_awk, "Workflow should use 'awk' for calculations instead of 'bc'"


def test_awk_available_in_shell():
    """
    Verify that awk is available in the current shell.

    awk is part of POSIX and available in all Unix-like systems,
    including GitHub Actions runners.
    """
    result = subprocess.run(["which", "awk"], capture_output=True, text=True, check=False, timeout=60)

    assert result.returncode == 0, "awk should be available in PATH"
    assert result.stdout.strip(), "awk path should be returned"
