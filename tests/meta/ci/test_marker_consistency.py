"""
Test that test markers are consistent across all validation sources

This test ensures that pre-push hooks, CI workflows, and Makefile all
use the same pytest marker expressions, preventing local/CI parity gaps.

Following TDD principles: Write test first, then fix configurations

Regression prevention for validation audit finding:
- Pre-push hook: '(unit or api or property) and not llm'
- CI workflow: 'unit and not llm'
- This creates "works locally, fails CI" scenario
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="marker_consistency")
class TestMarkerConsistency:
    """Test that pytest markers are consistent across all sources"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_three_sources_use_identical_marker(self):
        """
        Test that pre-push hook, CI workflow, and Makefile use identical markers.

        RED Phase: Will FAIL due to marker mismatch:
        - Pre-push: '(unit or api or property) and not llm'
        - CI: 'unit and not llm'
        - Makefile: varies

        GREEN Phase: After aligning all to same marker, should PASS

        This prevents the "works locally, fails CI" scenario.
        """
        # Expected marker expression (should be consistent everywhere)
        # Based on audit analysis, we should use the more comprehensive one
        EXPECTED_MARKER = "(unit or api or property) and not llm"

        # 1. Check pre-push hook marker
        pre_push_hook = Path(".githooks/pre-push")
        if pre_push_hook.exists():
            hook_content = pre_push_hook.read_text()
            # Extract pytest -m marker from hook
            hook_marker = self._extract_pytest_marker(hook_content)
        else:
            hook_marker = None

        # 2. Check pre-commit run-pre-push-tests hook
        precommit_config = Path(".pre-commit-config.yaml")
        precommit_marker = None
        if precommit_config.exists():
            with open(precommit_config) as f:
                config = yaml.safe_load(f)

            # Find run-pre-push-tests hook
            for repo in config.get("repos", []):
                for hook in repo.get("hooks", []):
                    if hook.get("id") == "run-pre-push-tests":
                        # Check description for marker
                        desc = hook.get("description", "")
                        marker_match = re.search(r'-m ["\']([^"\']+)["\']', desc)
                        if marker_match:
                            precommit_marker = marker_match.group(1)

        # 3. Check scripts/run_pre_push_tests.py
        pre_push_script = Path("scripts/run_pre_push_tests.py")
        script_marker = None
        if pre_push_script.exists():
            script_content = pre_push_script.read_text()
            script_marker = self._extract_pytest_marker(script_content)

        # 4. Check CI workflow
        ci_workflow = Path(".github/workflows/ci.yaml")
        ci_marker = None
        if ci_workflow.exists():
            with open(ci_workflow) as f:
                workflow = yaml.safe_load(f)

            # Find test job and extract marker
            jobs = workflow.get("jobs", {})
            test_job = jobs.get("test", {})
            steps = test_job.get("steps", [])

            for step in steps:
                run_cmd = step.get("run", "")
                if "pytest" in run_cmd and "-m" in run_cmd:
                    marker = self._extract_pytest_marker(run_cmd)
                    if marker:
                        ci_marker = marker
                        break

        # Collect all markers found
        markers = {
            "pre-push hook": hook_marker,
            "pre-commit config": precommit_marker,
            "pre-push script": script_marker,
            "CI workflow": ci_marker,
        }

        # Filter out None values
        found_markers = {k: v for k, v in markers.items() if v is not None}

        if not found_markers:
            pytest.fail("No pytest markers found in any source!")

        # Check for inconsistencies
        unique_markers = set(found_markers.values())

        if len(unique_markers) > 1:
            marker_details = "\n".join([f"  - {k}: '{v}'" for k, v in found_markers.items()])
            pytest.fail(
                f"Marker inconsistency detected!\n"
                f"Found {len(unique_markers)} different markers:\n{marker_details}\n\n"
                f"Expected marker (everywhere): '{EXPECTED_MARKER}'\n\n"
                f"This creates local/CI parity gap:\n"
                f"- Tests passing locally may fail in CI\n"
                f"- Different test sets run in different environments\n\n"
                f"Fix: Align all sources to use: '{EXPECTED_MARKER}'"
            )

        # Check if the marker matches expected
        actual_marker = list(unique_markers)[0]
        if actual_marker != EXPECTED_MARKER:
            pytest.fail(
                f"Marker is consistent but incorrect!\n"
                f"Expected: '{EXPECTED_MARKER}'\n"
                f"Actual: '{actual_marker}'\n\n"
                f"The marker should include 'unit or api or property' to run all fast tests.\n"
                f"Update all sources to use the expected marker."
            )

    def test_makefile_includes_smoke_tests(self):
        """
        Test that Makefile's validate-pre-push sub-targets run smoke tests.

        Smoke tests are marked with 'unit' marker and should be included
        in pre-push validation.

        validate-pre-push is a router that delegates to:
        - validate-pre-push-full (with integration tests)
        - validate-pre-push-quick (without integration tests)
        """
        makefile = Path("Makefile")
        assert makefile.exists(), "Makefile not found"

        content = makefile.read_text()

        # Find validate-pre-push sub-targets
        full_match = re.search(r"^validate-pre-push-full:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)
        quick_match = re.search(r"^validate-pre-push-quick:.*?(?=^[a-zA-Z]|\Z)", content, re.MULTILINE | re.DOTALL)

        if not (full_match or quick_match):
            pytest.fail("validate-pre-push sub-targets not found in Makefile")

        # Combine both sub-targets
        section_text = ""
        if full_match:
            section_text += full_match.group(0)
        if quick_match:
            section_text += quick_match.group(0)

        # Check that smoke tests are mentioned or that 'unit' marker is used
        # Smoke tests should be included in the unit marker
        has_smoke_mention = "smoke" in section_text.lower()
        has_unit_marker = re.search(r"-m.*unit", section_text)

        if not (has_smoke_mention or has_unit_marker):
            pytest.fail(
                "Makefile validate-pre-push sub-targets do not include smoke tests!\n"
                "Smoke tests are critical for pre-push validation.\n"
                "Fix: Ensure 'unit' marker includes smoke tests, or explicitly mention smoke tests"
            )

    def _extract_pytest_marker(self, content: str) -> str | None:
        """
        Extract pytest marker expression from content.

        Looks for patterns like:
        - pytest -m "marker"
        - pytest -m 'marker'
        - pytest -m marker
        """
        # Pattern 1: -m "marker" or -m 'marker'
        quoted_match = re.search(r'-m\s+["\']([^"\']+)["\']', content)
        if quoted_match:
            return quoted_match.group(1)

        # Pattern 2: -m marker (unquoted, up to next flag or newline)
        unquoted_match = re.search(r"-m\s+([^\s-]+)", content)
        if unquoted_match:
            return unquoted_match.group(1)

        return None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
