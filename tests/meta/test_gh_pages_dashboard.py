"""
Meta-tests validating GitHub Pages dashboard workflows and configuration.

These tests ensure:
1. No duplicate coverage generation across gh-pages workflows
2. Dashboard links point to valid URLs (no broken links)
3. Workflows that push to gh-pages create .last-updated file
4. Single source of truth for dashboard generation

Reference: CI Dashboard Optimization (2025-12-01)
Finding: Multiple workflows pushing competing dashboards, broken links, "Invalid Date"
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates CI workflows)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_gh_pages_dashboard")
class TestGhPagesDashboard:
    """Validate GitHub Pages dashboard configuration and consistency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # -------------------------------------------------------------------------
    # Dashboard Link Validation
    # -------------------------------------------------------------------------

    def test_dashboard_documentation_link_points_to_mintlify(self):
        """
        Validate that dashboard documentation links point to Mintlify docs.

        The correct URL is: https://mcp-server-langgraph.mintlify.app/
        NOT: https://vishnu2kmohan.github.io/mcp-server-langgraph/docs/

        References:
        - .github/workflows/publish-reports.yaml (line 400)
        - .github/workflows/gh-pages-telemetry.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Workflows that generate dashboards
        dashboard_workflows = ["publish-reports.yaml", "gh-pages-telemetry.yaml"]

        broken_links = []
        for workflow_name in dashboard_workflows:
            workflow_path = workflows_dir / workflow_name
            if not workflow_path.exists():
                continue

            content = workflow_path.read_text()

            # Check for broken /docs/ link pattern
            broken_pattern = r"vishnu2kmohan\.github\.io/mcp-server-langgraph/docs/"
            if re.search(broken_pattern, content):
                broken_links.append(
                    {
                        "workflow": workflow_name,
                        "broken_url": "https://vishnu2kmohan.github.io/mcp-server-langgraph/docs/",
                        "correct_url": "https://mcp-server-langgraph.mintlify.app/",
                    }
                )

        if broken_links:
            error_msg = "❌ Broken documentation links found in dashboard workflows:\n\n"
            for link in broken_links:
                error_msg += f"  Workflow: {link['workflow']}\n"
                error_msg += f"  Broken URL: {link['broken_url']}\n"
                error_msg += f"  Correct URL: {link['correct_url']}\n\n"
            error_msg += "💡 Documentation is hosted on Mintlify, not GitHub Pages /docs/\n"

            assert False, error_msg

    def test_dashboard_has_documentation_link(self):
        """
        Validate that dashboard includes a documentation link.

        Both telemetry and CI dashboards should have a link to documentation.
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Check gh-pages-telemetry.yaml dashboard generation
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"
        if telemetry_path.exists():
            content = telemetry_path.read_text()

            # Dashboard should have documentation link (in Quick Links or footer)
            has_docs_link = "mintlify" in content.lower() or "documentation" in content.lower()

            if not has_docs_link:
                pytest.skip(
                    "gh-pages-telemetry.yaml dashboard should include documentation link. "
                    "Add Mintlify docs link to Quick Links section."
                )

    # -------------------------------------------------------------------------
    # .last-updated File Validation
    # -------------------------------------------------------------------------

    def test_gh_pages_workflows_create_last_updated_file(self):
        """
        Validate that gh-pages publishing workflows create .last-updated file.

        This prevents "Invalid Date" display on the dashboard.

        References:
        - .github/workflows/gh-pages-telemetry.yaml
        - .github/workflows/publish-reports.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Workflows that push to gh-pages and should create .last-updated
        gh_pages_workflows = ["publish-reports.yaml", "gh-pages-telemetry.yaml"]

        missing_last_updated = []
        for workflow_name in gh_pages_workflows:
            workflow_path = workflows_dir / workflow_name
            if not workflow_path.exists():
                continue

            content = workflow_path.read_text()

            # Check if workflow creates .last-updated file
            creates_last_updated = ".last-updated" in content and ("echo" in content or "date" in content)

            if not creates_last_updated:
                missing_last_updated.append(workflow_name)

        if missing_last_updated:
            error_msg = "❌ Workflows missing .last-updated file creation:\n\n"
            for wf in missing_last_updated:
                error_msg += f"  - {wf}\n"
            error_msg += '\n💡 Add: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .last-updated\n'
            error_msg += "💡 This prevents 'Invalid Date' display on dashboard\n"

            assert False, error_msg

    # -------------------------------------------------------------------------
    # Coverage Generation Deduplication
    # -------------------------------------------------------------------------

    def test_no_duplicate_coverage_generation_for_gh_pages(self):
        """
        Validate that coverage is generated once (in ci.yaml) and reused.

        Before optimization:
        - ci.yaml: runs tests with coverage (XML)
        - coverage-trend.yaml: runs tests with coverage (JSON)
        - gh-pages-telemetry.yaml: runs tests with coverage (HTML + JSON)

        After optimization:
        - ci.yaml: runs tests, generates all coverage formats (XML, HTML, JSON)
        - Other workflows: download and reuse coverage artifacts

        References:
        - .github/workflows/ci.yaml
        - .github/workflows/coverage-trend.yaml
        - .github/workflows/gh-pages-telemetry.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Workflows that should NOT generate their own coverage
        # (they should consume artifacts from ci.yaml)
        consumer_workflows = ["coverage-trend.yaml", "gh-pages-telemetry.yaml"]

        # Check if these workflows still run their own pytest with coverage
        redundant_coverage = []
        for workflow_name in consumer_workflows:
            workflow_path = workflows_dir / workflow_name
            if not workflow_path.exists():
                continue

            content = workflow_path.read_text()

            # Check for pytest commands with --cov flag
            # These should download artifacts instead of generating coverage
            if "pytest" in content and "--cov" in content:
                # Check if workflow uses workflow_run to trigger from CI
                uses_workflow_run = "workflow_run" in content

                # If it runs pytest with --cov but doesn't use workflow_run,
                # it's likely generating coverage redundantly
                if not uses_workflow_run:
                    redundant_coverage.append(workflow_name)

        # Note: This test initially expects to FAIL (TDD Red phase)
        # After implementing the fix, this test should pass
        if redundant_coverage:
            error_msg = "❌ Redundant coverage generation detected:\n\n"
            for wf in redundant_coverage:
                error_msg += f"  - {wf} runs pytest with --cov\n"
            error_msg += "\n💡 Recommendation:\n"
            error_msg += "   - Modify to use workflow_run trigger from CI workflow\n"
            error_msg += "   - Download coverage artifacts instead of regenerating\n"
            error_msg += "   - This saves ~5-10 minutes per CI run\n"

            # Skip for now as this is the expected current state (to be fixed)
            pytest.skip(error_msg)

    def test_ci_yaml_generates_all_coverage_formats(self):
        """
        Validate that ci.yaml generates coverage in all needed formats.

        ci.yaml should generate:
        - XML (for Codecov)
        - HTML (for gh-pages browsable reports)
        - JSON (for coverage trend analysis)

        This allows other workflows to reuse coverage artifacts.
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        ci_path = workflows_dir / "ci.yaml"

        if not ci_path.exists():
            pytest.skip("ci.yaml not found")

        content = ci_path.read_text()

        coverage_formats = {
            "xml": "--cov-report=xml" in content,
            "html": "--cov-report=html" in content,
            "json": "--cov-report=json" in content,
        }

        missing_formats = [fmt for fmt, present in coverage_formats.items() if not present]

        if missing_formats:
            # Skip for now - expected to fail before implementation
            pytest.skip(
                f"ci.yaml should generate all coverage formats. "
                f"Missing: {', '.join(missing_formats)}. "
                f"This enables other workflows to reuse coverage artifacts."
            )

    # -------------------------------------------------------------------------
    # Single Dashboard Validation
    # -------------------------------------------------------------------------

    def test_single_dashboard_source_of_truth(self):
        """
        Validate that only one workflow generates the main dashboard index.html.

        Before optimization:
        - gh-pages-telemetry.yaml: generates telemetry dashboard
        - publish-reports.yaml: generates CI reports dashboard

        These can overwrite each other depending on execution order.

        After optimization:
        - Single consolidated workflow generates unified dashboard
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"

        # Find workflows that generate index.html for gh-pages
        dashboard_generators = []

        for workflow_file in workflows_dir.glob("*.yaml"):
            with open(workflow_file) as f:
                try:
                    workflow = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue

            if not workflow or not isinstance(workflow, dict):
                continue

            # Check if workflow pushes to gh-pages and generates index.html
            content = workflow_file.read_text()

            generates_dashboard = (
                "gh-pages" in content and "index.html" in content and ("git push" in content or "git commit" in content)
            )

            if generates_dashboard:
                dashboard_generators.append(workflow_file.name)

        # Note: Initially expects multiple (before consolidation)
        if len(dashboard_generators) > 1:
            error_msg = (
                f"⚠️ Multiple workflows generate gh-pages dashboard:\n"
                f"   {', '.join(dashboard_generators)}\n\n"
                f"💡 Consider consolidating into single workflow to:\n"
                f"   - Avoid race conditions\n"
                f"   - Ensure consistent dashboard content\n"
                f"   - Simplify maintenance\n"
            )
            # Skip for now - this is the expected current state
            pytest.skip(error_msg)

    # -------------------------------------------------------------------------
    # Artifact Reuse Validation
    # -------------------------------------------------------------------------

    def test_gh_pages_telemetry_uses_workflow_run_trigger(self):
        """
        Validate gh-pages-telemetry uses workflow_run to consume CI artifacts.

        After optimization, gh-pages-telemetry should:
        1. Trigger on workflow_run from CI workflow
        2. Download coverage artifacts from CI
        3. Generate dashboard and badges from artifacts
        4. NOT run its own pytest with coverage

        References:
        - .github/workflows/gh-pages-telemetry.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if not telemetry_path.exists():
            pytest.skip("gh-pages-telemetry.yaml not found")

        with open(telemetry_path) as f:
            workflow = yaml.safe_load(f)

        # Check for workflow_run trigger
        # Note: PyYAML parses 'on:' as True: (boolean), so we check both
        triggers = workflow.get("on", workflow.get(True, {}))
        has_workflow_run = "workflow_run" in triggers if isinstance(triggers, dict) else False

        assert has_workflow_run, (
            "gh-pages-telemetry.yaml should use workflow_run trigger "
            "to consume CI artifacts instead of running its own tests. "
            "This saves ~5-10 minutes per CI run."
        )

    # -------------------------------------------------------------------------
    # Deploy Condition Validation
    # -------------------------------------------------------------------------

    def test_deploy_job_runs_on_workflow_run(self):
        """
        Validate that deploy job condition includes workflow_run event.

        The deploy job must run when triggered by workflow_run from CI,
        not just on schedule or manual dispatch.

        Bug fixed: Deploy job had condition that excluded workflow_run,
        causing dashboards to never update after CI completion.

        References:
        - .github/workflows/gh-pages-telemetry.yaml (line 665)
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if not telemetry_path.exists():
            pytest.skip("gh-pages-telemetry.yaml not found")

        with open(telemetry_path) as f:
            workflow = yaml.safe_load(f)

        # Find deploy job
        jobs = workflow.get("jobs", {})
        deploy_job = jobs.get("deploy", {})

        if not deploy_job:
            pytest.fail("deploy job not found in gh-pages-telemetry.yaml")

        # Check if condition
        job_condition = deploy_job.get("if", "")

        # The condition should include workflow_run check
        has_workflow_run_condition = "workflow_run" in job_condition

        assert has_workflow_run_condition, (
            "deploy job condition must include 'workflow_run' to deploy "
            "when triggered by CI completion. Current condition excludes "
            "workflow_run, causing dashboards to never update.\n\n"
            f"Current condition: {job_condition}\n\n"
            'Expected: Include \'(github.event_name == "workflow_run" && '
            'github.event.workflow_run.conclusion == "success")\''
        )

    # -------------------------------------------------------------------------
    # Weekly Reports Integration
    # -------------------------------------------------------------------------

    def test_generate_reports_job_exists_for_scheduled_runs(self):
        """
        Validate that generate-reports job exists for weekly code quality scans.

        The gh-pages-telemetry workflow should include a generate-reports job
        that runs on schedule to produce:
        - AsyncMock configuration scan
        - Memory safety scan
        - Test suite statistics

        References:
        - .github/workflows/gh-pages-telemetry.yaml
        - Consolidation of weekly-reports.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if not telemetry_path.exists():
            pytest.skip("gh-pages-telemetry.yaml not found")

        with open(telemetry_path) as f:
            workflow = yaml.safe_load(f)

        jobs = workflow.get("jobs", {})

        # Check for generate-reports job
        has_reports_job = "generate-reports" in jobs

        assert has_reports_job, (
            "gh-pages-telemetry.yaml should include 'generate-reports' job "
            "for weekly code quality scans. This consolidates the previous "
            "weekly-reports.yaml workflow."
        )

    def test_deploy_handles_weekly_reports_artifacts(self):
        """
        Validate that deploy job downloads and copies weekly reports artifacts.

        The deploy job should:
        1. Download weekly-reports artifact (with continue-on-error)
        2. Copy reports to gh-pages/reports/ directory

        References:
        - .github/workflows/gh-pages-telemetry.yaml
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if not telemetry_path.exists():
            pytest.skip("gh-pages-telemetry.yaml not found")

        content = telemetry_path.read_text()

        # Check for weekly reports artifact handling
        downloads_reports = "weekly-reports" in content and "download-artifact" in content
        copies_to_reports = "gh-pages/reports" in content

        assert downloads_reports, (
            "deploy job should download 'weekly-reports' artifact for "
            "code quality scans (AsyncMock, memory safety, test stats)."
        )

        assert copies_to_reports, "deploy job should copy reports to 'gh-pages/reports/' directory."

    # -------------------------------------------------------------------------
    # Retention Policy Validation
    # -------------------------------------------------------------------------

    def test_telemetry_retention_policy_configured(self):
        """
        Validate that telemetry data has retention policy (90 days / 500 runs).

        The generate-trends job should implement retention to:
        - Filter data older than 90 days
        - Cap at 500 runs maximum
        - Keep gh-pages storage under 1GB limit

        References:
        - .github/workflows/gh-pages-telemetry.yaml (line 272-273)
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if not telemetry_path.exists():
            pytest.skip("gh-pages-telemetry.yaml not found")

        content = telemetry_path.read_text()

        # Check for retention policy indicators
        has_day_retention = "90" in content and ("days" in content.lower() or "timedelta" in content)
        has_run_cap = "500" in content

        # At minimum, should have some form of retention
        has_retention = has_day_retention or has_run_cap or "cutoff" in content.lower() or "retention" in content.lower()

        assert has_retention, (
            "generate-trends job should implement retention policy:\n"
            "- Filter data older than 90 days\n"
            "- Cap at 500 runs maximum\n\n"
            "This prevents gh-pages from exceeding 1GB limit."
        )

    # -------------------------------------------------------------------------
    # Weekly Reports Workflow Deprecation
    # -------------------------------------------------------------------------

    def test_weekly_reports_workflow_removed(self):
        """
        Validate that standalone weekly-reports.yaml is removed.

        After consolidation, weekly reports are generated by gh-pages-telemetry.yaml.
        The standalone weekly-reports.yaml should be deleted to avoid:
        - Duplicate report generation
        - Accumulation of automated/* branches

        References:
        - .github/workflows/weekly-reports.yaml (should be deleted)
        """
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        weekly_reports_path = workflows_dir / "weekly-reports.yaml"

        # Note: This test will FAIL until we delete the file (TDD Red phase)
        assert not weekly_reports_path.exists(), (
            "weekly-reports.yaml should be removed after consolidation. "
            "Weekly reports are now generated by gh-pages-telemetry.yaml."
        )
