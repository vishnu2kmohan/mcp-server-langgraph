"""Validate CI workflow hook IDs match .pre-commit-config.yaml.

This meta-test ensures that hook IDs referenced in GitHub Actions workflows
actually exist in the pre-commit configuration with the correct stage.

This prevents CI failures like:
  "No hook with id `trivy-k8s-scan` in stage `pre-push`"

Run with: pytest tests/meta/ci/test_workflow_hook_ids.py -v
"""

import gc
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.meta, pytest.mark.unit]


def get_pre_push_hook_ids() -> set[str]:
    """Extract all hook IDs that are in the pre-push stage."""
    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        pytest.skip("No .pre-commit-config.yaml found")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    pre_push_hooks = set()
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id")
            if not hook_id:
                continue
            # Default stage is pre-commit, so only include if explicitly pre-push
            stages = hook.get("stages", ["pre-commit"])
            if "pre-push" in stages:
                pre_push_hooks.add(hook_id)

    return pre_push_hooks


def get_ci_workflow_hook_references() -> dict[str, list[str]]:
    """Extract hook IDs referenced in CI workflow push-validators job."""
    ci_path = Path(".github/workflows/ci.yaml")
    if not ci_path.exists():
        pytest.skip("No ci.yaml workflow found")

    with open(ci_path) as f:
        content = f.read()

    # Find the push-validators matrix section
    # Look for hooks: field values in the matrix
    hook_refs = {}

    # Parse as YAML to get structured data
    workflow = yaml.safe_load(content)
    jobs = workflow.get("jobs", {})
    push_validators = jobs.get("push-validators", {})
    strategy = push_validators.get("strategy", {})
    matrix = strategy.get("matrix", {})
    includes = matrix.get("include", [])

    for include in includes:
        category = include.get("category", "unknown")
        hooks_str = include.get("hooks", "")
        # Split by whitespace to get individual hook IDs
        hooks = hooks_str.split() if hooks_str else []
        hook_refs[category] = hooks

    return hook_refs


@pytest.mark.xdist_group(name="workflow_hook_ids")
class TestWorkflowHookIds:
    """Test that CI workflow hook IDs are valid."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_ci_hook_ids_exist_in_pre_push_stage(self):
        """Verify all hook IDs in CI workflow exist in pre-push stage.

        This test prevents CI failures like:
          "No hook with id `trivy-k8s-scan` in stage `pre-push`"
        """
        pre_push_hooks = get_pre_push_hook_ids()
        ci_hooks = get_ci_workflow_hook_references()

        errors = []
        for category, hooks in ci_hooks.items():
            for hook in hooks:
                if hook not in pre_push_hooks:
                    # Find similar hooks to suggest
                    similar = [
                        h
                        for h in pre_push_hooks
                        if hook.replace("-", "_") in h.replace("-", "_") or hook.split("-")[0] in h or h.split("-")[0] in hook
                    ]
                    suggestion = f" (similar: {similar})" if similar else ""
                    errors.append(f"{category}: '{hook}' not in pre-push stage{suggestion}")

        if errors:
            error_msg = "CI workflow references hooks not in pre-push stage:\n"
            error_msg += "\n".join(f"  - {e}" for e in errors)
            error_msg += "\n\nFix: Update .github/workflows/ci.yaml push-validators matrix"
            error_msg += " to use correct hook IDs from .pre-commit-config.yaml"
            pytest.fail(error_msg)

    def test_no_typos_in_hook_ids(self):
        """Check for common typos in hook IDs (hyphen vs underscore)."""
        pre_push_hooks = get_pre_push_hook_ids()
        ci_hooks = get_ci_workflow_hook_references()

        # Flatten all CI hooks
        all_ci_hooks = []
        for hooks in ci_hooks.values():
            all_ci_hooks.extend(hooks)

        typo_warnings = []
        for hook in all_ci_hooks:
            if hook not in pre_push_hooks:
                # Check if underscore/hyphen variant exists
                alt_hook = hook.replace("-", "_")
                if alt_hook in pre_push_hooks:
                    typo_warnings.append(f"'{hook}' should be '{alt_hook}' (underscore)")

                alt_hook = hook.replace("_", "-")
                if alt_hook in pre_push_hooks:
                    typo_warnings.append(f"'{hook}' should be '{alt_hook}' (hyphen)")

        if typo_warnings:
            pytest.fail("Hook ID typos detected:\n" + "\n".join(f"  - {w}" for w in typo_warnings))

    def test_pre_push_hooks_coverage(self):
        """Verify most pre-push hooks are covered by CI workflow.

        This is a soft check - we don't require 100% coverage, but we should
        cover at least 80% of pre-push hooks.
        """
        pre_push_hooks = get_pre_push_hook_ids()
        ci_hooks = get_ci_workflow_hook_references()

        # Flatten all CI hooks
        all_ci_hooks = set()
        for hooks in ci_hooks.values():
            all_ci_hooks.update(hooks)

        # Also include hooks from tests category that are in ci.yaml
        # (run-pre-push-tests, python-version-smoke-test, etc.)
        covered = all_ci_hooks & pre_push_hooks
        coverage = len(covered) / len(pre_push_hooks) * 100 if pre_push_hooks else 0

        # We expect at least 80% coverage
        min_coverage = 80
        if coverage < min_coverage:
            missing = pre_push_hooks - all_ci_hooks
            pytest.fail(
                f"CI workflow covers only {coverage:.1f}% of pre-push hooks "
                f"(minimum: {min_coverage}%)\n"
                f"Missing hooks: {sorted(missing)}"
            )
