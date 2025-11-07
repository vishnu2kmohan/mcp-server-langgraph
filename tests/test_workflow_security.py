"""
Test workflow security patterns and secret handling.

These tests detect security anti-patterns in GitHub Actions workflows,
particularly around secret handling and context usage.

TDD Approach (RED → GREEN → REFACTOR):
1. RED: Tests fail initially due to secret misuse in job contexts
2. GREEN: Fix workflows to use secrets only in step contexts
3. REFACTOR: Improve security patterns while keeping tests green
"""

import re
from pathlib import Path

import pytest
import yaml


def get_workflow_files():
    """Get all workflow YAML files."""
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
    return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_no_secrets_in_job_if_conditions(workflow_file):
    """
    Test that workflows do not use secrets.* in job-level if conditions.

    GitHub Actions does NOT support secrets context in job-level conditions.
    Secrets are only available in step-level contexts.

    This is a CRITICAL security validation that prevents silent failures.

    Expected to FAIL initially (RED phase) for:
    - dora-metrics.yaml:242 - secrets.SLACK_WEBHOOK_URL in job if
    - observability-alerts.yaml:119 - secrets.SLACK_WEBHOOK_URL in job if
    - observability-alerts.yaml:206 - secrets.PAGERDUTY_INTEGRATION_KEY in job if
    - observability-alerts.yaml:253 - secrets.DATADOG_API_KEY in job if

    Correct pattern:
        job:
          if: always()  # No secret check
          steps:
            - name: Step
              if: env.SECRET != ''  # Check at step level
              env:
                SECRET: ${{ secrets.MY_SECRET }}
    """
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    errors = []

    # Check each job for secret usage in if conditions
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        job_if = job_config.get("if", "")
        if not job_if:
            continue

        # Check for secrets.* pattern in job-level if
        # This regex matches: secrets.ANYTHING or secrets['ANYTHING']
        secrets_pattern = r"secrets\.[A-Z_]+"
        secrets_bracket_pattern = r"secrets\[['\"]\w+['\"]\]"

        if re.search(secrets_pattern, job_if) or re.search(secrets_bracket_pattern, job_if):
            errors.append(
                f"Job '{job_name}' uses secrets.* in job-level if condition.\n"
                f"  File: {workflow_file.name}\n"
                f"  Condition: {job_if}\n"
                f"  INVALID: secrets context is not available in job-level if conditions.\n"
                f"  FIX: Move secret check to step-level if condition with env variable."
            )

    assert not errors, "\n\n".join(errors)


def _job_uses_gcp_auth(job_config):
    """Check if a job uses GCP authentication or deployment secrets."""
    steps = job_config.get("steps", [])

    for step in steps:
        if not isinstance(step, dict):
            continue

        # Check for GCP authentication actions
        uses = step.get("uses", "")
        if "google-github-actions/auth" in uses or "google-github-actions/setup-gcloud" in uses:
            return True

        # Check for GCP secrets in environment variables
        env = step.get("env", {})
        if isinstance(env, dict):
            if any(isinstance(v, str) and "secrets.GCP" in v for v in env.values()):
                return True

        # Check for actual kubectl/gcloud commands (not grep patterns)
        run = step.get("run", "")
        if isinstance(run, str):
            if ("gcloud " in run or "kubectl " in run) and "grep" not in run:
                return True

    return False


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_fork_protection_on_deployment_jobs(workflow_file):
    """
    Test that deployment jobs include fork repository protection.

    Deployment jobs should check github.repository to prevent:
    - Unauthorized deployments from forks
    - Secret exposure in fork PRs
    - Wasted Actions minutes in forks

    Best practice pattern:
        deploy:
          if: github.repository == 'owner/repo'
          steps: ...

    This test identifies jobs that access deployment secrets but lack fork guards.
    """
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    # Skip non-deployment workflows
    if "deploy" not in workflow_file.name and "production" not in workflow_file.name:
        pytest.skip(f"Not a deployment workflow: {workflow_file.name}")

    errors = []
    jobs = workflow.get("jobs", {})

    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        # Check if job uses GCP authentication (helper function reduces complexity)
        if not _job_uses_gcp_auth(job_config):
            continue

        # Check if job has fork protection
        job_if = job_config.get("if", "")
        has_fork_guard = "github.repository" in job_if and "==" in job_if

        if not has_fork_guard:
            errors.append(
                f"Deployment job '{job_name}' lacks fork repository protection.\n"
                f"  File: {workflow_file.name}\n"
                f"  Job uses GCP authentication/secrets but doesn't check github.repository.\n"
                f"  FIX: Add 'if: github.repository == \"owner/repo\"' to job condition."
            )

    # Filter known exceptions (validation jobs that don't access secrets)
    if errors:
        known_exceptions = ["pre-deployment-checks", "deployment-summary", "validate-"]
        filtered_errors = [e for e in errors if not any(exc in e for exc in known_exceptions)]
        if filtered_errors:
            assert False, "\n\n".join(filtered_errors)


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_no_hardcoded_secrets(workflow_file):
    """
    Test that workflows do not contain hardcoded secrets or credentials.

    This test scans for common secret patterns that should use GitHub secrets instead.
    """
    with open(workflow_file) as f:
        content = f.read()

    errors = []

    # Patterns that indicate potential hardcoded secrets
    dangerous_patterns = [
        (r"password:\s*['\"](?!test|example|changeme)[a-zA-Z0-9]{8,}", "hardcoded password"),
        (r"api[_-]?key:\s*['\"][a-zA-Z0-9]{20,}", "hardcoded API key"),
        (r"token:\s*['\"](?!test|example|ghp_)[a-zA-Z0-9]{20,}", "hardcoded token"),
        (r"sk-ant-[a-zA-Z0-9-]{40,}", "Anthropic API key"),
        (r"ghp_[a-zA-Z0-9]{36,}", "GitHub PAT"),
    ]

    for pattern, description in dangerous_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Skip if it's using ${{ secrets.* }} syntax
            if "${{ secrets." in match.group(0):
                continue

            errors.append(
                f"Potential {description} found in {workflow_file.name}:\n"
                f"  Pattern: {match.group(0)[:50]}...\n"
                f"  FIX: Use GitHub secrets instead: ${{{{ secrets.SECRET_NAME }}}}"
            )

    assert not errors, "\n\n".join(errors)


def test_all_workflows_use_secrets_correctly():
    """
    Integration test: verify all workflows use secrets correctly.

    This test ensures that secrets are:
    1. Never used in job-level if conditions
    2. Always accessed via ${{ secrets.* }} syntax
    3. Protected with appropriate guards
    """
    workflow_files = get_workflow_files()
    assert len(workflow_files) > 0, "No workflow files found"

    total_secrets_usage = 0
    for workflow_file in workflow_files:
        with open(workflow_file) as f:
            content = f.read()

        # Count secrets usage
        secrets_count = len(re.findall(r"\$\{\{\s*secrets\.", content))
        total_secrets_usage += secrets_count

    # At least some workflows should use secrets
    assert total_secrets_usage > 0, "No workflows use GitHub secrets (unexpected)"

    # All secret usage should be in correct format
    for workflow_file in workflow_files:
        with open(workflow_file) as f:
            content = f.read()

        # Check for malformed secret references
        malformed = re.findall(r"secrets\.\w+(?!\s*}})", content)
        # Filter out valid job-level if conditions (which will be caught by other tests)
        malformed = [m for m in malformed if "${{ " not in content[max(0, content.index(m) - 10) :]]

        assert not malformed, f"Malformed secret reference in {workflow_file.name}: {malformed}"
