"""
Meta-tests validating CI workflow efficiency and preventing redundant test execution.

These tests ensure:
1. No duplicate pytest invocations across workflows
2. Test markers are used efficiently
3. CI resources are not wasted on redundant test runs

Reference: Testing Infrastructure Validation (2025-11-21)
Finding: CI/CD redundancy - API tests run twice (ci.yaml + e2e-tests.yaml)
"""

import gc
import re
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates CI workflows)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testciworkflowredundancy")
class TestCIWorkflowRedundancy:
    """Validate that CI workflows don't have redundant test executions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_duplicate_pytest_invocations_across_workflows(self):
        """
        Validate that pytest commands with same markers don't run in multiple workflows.

        FINDING: API tests (-m "api and unit") were running in both ci.yaml and
        e2e-tests.yaml, wasting ~2-3 minutes per CI run.

        References:
        - .github/workflows/ci.yaml - Main CI pipeline
        - .github/workflows/e2e-tests.yaml - E2E test pipeline
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Parse all workflow files and extract pytest commands
        pytest_commands = self._extract_pytest_commands_from_workflows(workflows_dir)

        # Group by marker combination to detect duplicates
        marker_to_workflows = defaultdict(list)

        for workflow_name, commands in pytest_commands.items():
            for cmd in commands:
                # Extract marker expression (e.g., "api and unit", "unit and not llm", "e2e")
                marker = self._extract_marker_from_pytest_command(cmd)
                if marker:
                    marker_to_workflows[marker].append((workflow_name, cmd))

        # Detect redundancies
        redundancies = []
        for marker, occurrences in marker_to_workflows.items():
            if len(occurrences) > 1:
                # Multiple workflows running same marker
                workflow_names = [wf for wf, _ in occurrences]

                # Special case: It's okay for different workflows to run different test types
                # Only flag if the SAME workflow type (ci.yaml, e2e-tests.yaml) runs the same tests
                if self._is_actual_redundancy(workflow_names, marker):
                    redundancies.append(
                        {"marker": marker, "workflows": workflow_names, "commands": [cmd for _, cmd in occurrences]}
                    )

        # Assert no redundancies found
        if redundancies:
            error_msg = "❌ Redundant pytest invocations detected:\n\n"
            for r in redundancies:
                error_msg += f"  Marker: {r['marker']}\n"
                error_msg += f"  Workflows: {', '.join(r['workflows'])}\n"
                error_msg += "  Commands:\n"
                for cmd in r["commands"]:
                    error_msg += f"    - {cmd}\n"
                error_msg += "\n"
            error_msg += "💡 Recommendation: Remove duplicate test runs to save CI time\n"

            assert False, error_msg

    def test_e2e_workflow_only_runs_e2e_tests(self):
        """
        Validate that e2e-tests.yaml workflow only runs E2E tests, not unit/API tests.

        FINDING: e2e-tests.yaml was running API tests that already ran in ci.yaml.

        References:
        - .github/workflows/e2e-tests.yaml
        """
        e2e_workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "e2e-tests.yaml"

        if not e2e_workflow_path.exists():
            pytest.skip("e2e-tests.yaml workflow not found")

        with open(e2e_workflow_path) as f:
            workflow = yaml.safe_load(f)

        # Extract pytest commands
        pytest_commands = []
        self._extract_pytest_from_jobs(workflow.get("jobs", {}), pytest_commands)

        # Validate that only e2e marker is used
        non_e2e_commands = []
        for cmd in pytest_commands:
            marker = self._extract_marker_from_pytest_command(cmd)

            # E2E workflow should ONLY run e2e marker tests
            if marker and marker != "e2e":
                # Check if it's an api/unit test
                if "api" in marker or "unit" in marker:
                    non_e2e_commands.append({"command": cmd, "marker": marker})

        if non_e2e_commands:
            error_msg = "❌ E2E workflow running non-E2E tests:\n\n"
            for cmd_info in non_e2e_commands:
                error_msg += f"  Marker: {cmd_info['marker']}\n"
                error_msg += f"  Command: {cmd_info['command']}\n\n"
            error_msg += "💡 E2E workflow should only run -m e2e tests\n"
            error_msg += "💡 Unit/API tests should run in ci.yaml workflow only\n"

            assert False, error_msg

    def test_ci_workflow_has_comprehensive_test_coverage(self):
        """
        Validate that ci.yaml runs all fast test types (unit, API).

        This ensures the main CI pipeline catches issues quickly.
        """
        ci_workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yaml"

        if not ci_workflow_path.exists():
            pytest.skip("ci.yaml workflow not found")

        with open(ci_workflow_path) as f:
            workflow = yaml.safe_load(f)

        # Extract pytest commands
        pytest_commands = []
        self._extract_pytest_from_jobs(workflow.get("jobs", {}), pytest_commands)

        markers_found = set()
        for cmd in pytest_commands:
            marker = self._extract_marker_from_pytest_command(cmd)
            if marker:
                markers_found.add(marker)

        # CI should run at minimum: unit tests and API tests
        expected_markers = ["unit", "api"]

        missing_markers = []
        for expected in expected_markers:
            # Check if marker appears in any of the found markers
            if not any(expected in m for m in markers_found):
                missing_markers.append(expected)

        if missing_markers:
            error_msg = f"⚠️ CI workflow missing test types: {', '.join(missing_markers)}\n"
            error_msg += f"Found markers: {', '.join(sorted(markers_found))}\n"
            error_msg += "💡 Ensure ci.yaml runs all fast test types for quick feedback\n"

            # This is a warning, not a failure (informational only)
            pytest.skip(error_msg)

    # Helper methods

    def _extract_pytest_commands_from_workflows(self, workflows_dir: Path) -> dict:
        """
        Extract all pytest commands from workflow YAML files.

        Returns:
            dict: {workflow_name: [list of pytest commands]}
        """
        pytest_commands = {}

        for workflow_file in workflows_dir.glob("*.yaml"):
            with open(workflow_file) as f:
                workflow = yaml.safe_load(f)

            commands = []
            self._extract_pytest_from_jobs(workflow.get("jobs", {}), commands)

            if commands:
                pytest_commands[workflow_file.name] = commands

        return pytest_commands

    def _extract_pytest_from_jobs(self, jobs: dict, commands: list) -> None:
        """Recursively extract pytest commands from workflow jobs."""
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            # Check steps for pytest commands
            steps = job_config.get("steps", [])
            for step in steps:
                if not isinstance(step, dict):
                    continue

                # Check run commands
                run_cmd = step.get("run", "")
                if isinstance(run_cmd, str) and "pytest" in run_cmd:
                    # Extract individual pytest commands (may be multi-line)
                    for line in run_cmd.split("\n"):
                        line = line.strip()
                        if line.startswith("pytest") or line.startswith("uv run pytest"):
                            commands.append(line)

    def _extract_marker_from_pytest_command(self, cmd: str) -> str:
        """
        Extract marker expression from pytest command.

        Examples:
            pytest -m "unit and not llm" -> "unit and not llm"
            pytest -n auto -m "api and unit" -> "api and unit"
            pytest -m e2e -> "e2e"

        Returns:
            str: Marker expression, or empty string if no marker found
        """
        # Match -m "marker" or -m 'marker' or -m marker
        match = re.search(r'-m\s+["\']?([^"\']+)["\']?', cmd)
        if match:
            marker = match.group(1).strip()
            # Normalize whitespace and quotes
            marker = " ".join(marker.split())
            return marker
        return ""

    def _is_actual_redundancy(self, workflow_names: list, marker: str) -> bool:
        """
        Determine if multiple occurrences of the same marker is actually redundant.

        Rules:
        - If e2e-tests.yaml runs unit/api tests: REDUNDANT (they run in ci.yaml)
        - If both ci.yaml and e2e-tests.yaml run e2e: OK (intentional)
        - If same workflow file appears twice: REDUNDANT

        Returns:
            bool: True if redundancy should be flagged
        """
        # Check for same workflow running same marker twice
        if len(workflow_names) != len(set(workflow_names)):
            return True  # Same file appears multiple times

        # Check for e2e-tests.yaml running non-e2e tests
        if "e2e-tests.yaml" in workflow_names:
            if "unit" in marker or "api" in marker:
                return True  # E2E workflow shouldn't run unit/api tests

        # If e2e marker runs in multiple workflows, that's intentional (not redundant)
        if marker == "e2e":
            return False

        # Multiple workflows running the same non-e2e marker is redundant
        if len(workflow_names) > 1:
            return True

        return False
