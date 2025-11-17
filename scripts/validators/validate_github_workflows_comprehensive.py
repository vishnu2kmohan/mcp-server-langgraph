#!/usr/bin/env python3
"""
GitHub Actions Workflow Comprehensive Validator

This script consolidates multiple GitHub Actions workflow validations:
1. Context usage validation (github.event.* against enabled triggers)
2. Action version validation (ensure versions are published tags)
3. Permissions validation (workflows creating issues have 'issues: write')
4. YAML syntax validation

This is the SINGLE SOURCE OF TRUTH for GitHub workflow validation.

Usage:
    python scripts/validators/validate_github_workflows_comprehensive.py [--repo-root PATH] [--verbose]

Exit Codes:
    0: All validations passed
    1: Validation errors found
    2: Script execution error (invalid arguments, etc.)

Integration:
- Pre-commit hook: validate-github-workflows-comprehensive
- Meta-test: tests/meta/test_consolidated_workflow_validator.py
- Replaces: scripts/validate_github_workflows.py + tests/meta/test_github_actions_validation.py

References:
- OpenAI Codex Phase 5: Action version validation findings
- DUPLICATE_VALIDATOR_ANALYSIS_2025-11-16.md: Consolidation strategy
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


class WorkflowValidator:
    """
    Comprehensive GitHub Actions workflow validator.

    Consolidates:
    - Context usage validation (WorkflowContextValidator from validate_github_workflows.py)
    - Action version validation (from test_github_actions_validation.py)
    - Permissions validation (from test_github_actions_validation.py)
    - YAML syntax validation (from test_github_actions_validation.py)
    """

    # Context patterns to validate (from validate_github_workflows.py)
    CONTEXT_PATTERNS = {
        "workflow_run": re.compile(r"github\.event\.workflow_run\."),
        "pull_request": re.compile(r"github\.event\.pull_request\."),
        "issue": re.compile(r"github\.event\.issue\."),
        "schedule": re.compile(r"github\.event\.schedule\."),
        "deployment": re.compile(r"github\.event\.deployment\."),
    }

    # Invalid action versions (from test_github_actions_validation.py)
    INVALID_ACTION_VERSIONS = {
        "astral-sh/setup-uv@v7.1.1": "should be v7.1.0 or v7 (v7.1.1 does not exist)",
        "actions/cache@v4.3.0": "should be v4.2.0 or v4 (v4.3.0 not confirmed to exist)",
    }

    # Maximum reasonable major versions for known actions
    MAX_MAJOR_VERSIONS = {
        "actions/checkout": 5,
        "actions/setup-python": 6,
        "actions/upload-artifact": 5,
        "actions/download-artifact": 6,
        "actions/cache": 4,
        "actions/github-script": 8,
        "docker/setup-buildx-action": 3,
        "docker/build-push-action": 6,
        "docker/login-action": 3,
        "docker/setup-qemu-action": 3,
        "codecov/codecov-action": 6,
        "google-github-actions/auth": 3,
        "google-github-actions/get-gke-credentials": 3,
        "google-github-actions/setup-gcloud": 3,
        "astral-sh/setup-uv": 7,
    }

    def __init__(self, repo_root: Path, verbose: bool = False):
        """
        Initialize validator.

        Args:
            repo_root: Repository root directory
            verbose: Enable verbose output
        """
        self.repo_root = repo_root
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []

        self.workflows_dir = repo_root / ".github" / "workflows"
        self.actions_dir = repo_root / ".github" / "actions"

    def validate_all(self) -> bool:
        """
        Run all validations.

        Returns:
            True if all validations passed, False otherwise
        """
        if not self.workflows_dir.exists():
            self._error(f"Workflows directory not found: {self.workflows_dir}")
            return False

        # Get all workflow and composite action files
        workflow_files = self._get_workflow_files()
        composite_action_files = self._get_composite_action_files()
        all_files = workflow_files + composite_action_files

        if not all_files:
            self._error(f"No workflow or action files found in {self.workflows_dir}")
            return False

        # Run all validations
        self._validate_yaml_syntax(all_files)
        self._validate_context_usage(workflow_files)
        self._validate_action_versions(all_files)
        self._validate_permissions(workflow_files)

        # Print summary
        self._print_summary()

        return len(self.errors) == 0

    def _get_workflow_files(self) -> List[Path]:
        """Get all GitHub workflow files."""
        if not self.workflows_dir.exists():
            return []

        return sorted(list(self.workflows_dir.glob("*.yaml")) + list(self.workflows_dir.glob("*.yml")))

    def _get_composite_action_files(self) -> List[Path]:
        """Get all composite action files."""
        if not self.actions_dir.exists():
            return []

        action_files = []
        for action_dir in self.actions_dir.iterdir():
            if action_dir.is_dir():
                action_file = action_dir / "action.yml"
                if action_file.exists():
                    action_files.append(action_file)
        return sorted(action_files)

    def _validate_yaml_syntax(self, files: List[Path]) -> None:
        """Validate YAML syntax for all workflow files."""
        if self.verbose:
            print(f"\n🔍 Validating YAML syntax for {len(files)} file(s)...")

        for file_path in files:
            try:
                with open(file_path) as f:
                    yaml.safe_load(f)
                if self.verbose:
                    print(f"  ✓ {file_path.name}")
            except yaml.YAMLError as e:
                self._error(f"{file_path.name}: Invalid YAML syntax - {e}")

    def _validate_context_usage(self, workflow_files: List[Path]) -> None:
        """
        Validate GitHub context usage against enabled triggers.

        Prevents bugs like using github.event.pull_request.* when
        pull_request trigger is not enabled.

        Logic from: scripts/validate_github_workflows.py
        """
        if self.verbose:
            print(f"\n🔍 Validating context usage for {len(workflow_files)} workflow(s)...")

        for workflow_file in workflow_files:
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                if not workflow_data:
                    continue

                # Get enabled triggers
                # NOTE: YAML parsers interpret 'on:' as boolean True, not string 'on'
                on_config = workflow_data.get("on") or workflow_data.get(True, {})
                enabled_triggers = self._parse_triggers(on_config)

                # Check context usage
                workflow_str = yaml.dump(workflow_data)
                self._check_context_usage(workflow_file.name, workflow_str, enabled_triggers)

                if self.verbose:
                    print(f"  ✓ {workflow_file.name}")

            except yaml.YAMLError:
                # Already reported by YAML validation
                pass
            except Exception as e:
                self._error(f"{workflow_file.name}: Context validation error - {e}")

    def _parse_triggers(self, on_config) -> Set[str]:
        """Parse trigger configuration to get enabled triggers."""
        if isinstance(on_config, str):
            return {on_config}
        elif isinstance(on_config, list):
            return set(on_config)
        elif isinstance(on_config, dict):
            return set(on_config.keys())
        return set()

    def _check_context_usage(self, file_name: str, content: str, enabled_triggers: Set[str]) -> None:
        """Check if context usage matches enabled triggers."""
        for context_type, pattern in self.CONTEXT_PATTERNS.items():
            matches = pattern.finditer(content)

            for match in matches:
                # Context is used - check if trigger is enabled
                if context_type not in enabled_triggers:
                    # Check if usage has a fallback (e.g., github.event.pull_request.number || github.ref)
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]

                    has_fallback = "||" in context or "??" in context

                    # Check for guards protecting the usage
                    guard_pattern = rf'if:.*github\.event_name\s*==\s*["\']?{context_type}["\']?'
                    has_guard = re.search(guard_pattern, content, re.IGNORECASE)

                    # Only error if no fallback AND no guard
                    if not has_fallback and not has_guard:
                        self._error(
                            f"{file_name}: Uses github.event.{context_type}.* "
                            f"but '{context_type}' trigger is not enabled.\n"
                            f"  Fix: Add '{context_type}' to 'on:' triggers OR "
                            f"add guard: if: github.event_name == '{context_type}' OR "
                            f"add fallback: github.event.{context_type}.field || default_value"
                        )
                        break  # Only report once per context type

    def _validate_action_versions(self, files: List[Path]) -> None:
        """
        Validate action version tags are published and valid.

        Prevents bugs like using non-existent version tags.

        Logic from: tests/meta/test_github_actions_validation.py
        """
        if self.verbose:
            print(f"\n🔍 Validating action versions for {len(files)} file(s)...")

        action_pattern = re.compile(r"uses:\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)@(v?\d+(?:\.\d+)*)")

        for file_path in files:
            content = file_path.read_text()

            # Check for known invalid versions
            for invalid_version, fix_msg in self.INVALID_ACTION_VERSIONS.items():
                if invalid_version in content:
                    lines = content.split("\n")
                    line_numbers = [i + 1 for i, line in enumerate(lines) if invalid_version in line]
                    self._error(
                        f"{file_path.name}:{line_numbers[0]}: " f"Invalid action version '{invalid_version}' ({fix_msg})"
                    )

            # Check for suspicious versions (major version too high)
            for match in action_pattern.finditer(content):
                action = match.group(1)
                version = match.group(2)

                if action in self.MAX_MAJOR_VERSIONS:
                    major = int(version.lstrip("v").split(".")[0])
                    max_major = self.MAX_MAJOR_VERSIONS[action]

                    if major > max_major:
                        line_num = content[: match.start()].count("\n") + 1
                        self._error(
                            f"{file_path.name}:{line_num}: "
                            f"Suspicious action version {action}@{version} "
                            f"(major v{major} > known max v{max_major})"
                        )

            if self.verbose and file_path.name not in [e for e in self.errors if file_path.name in e]:
                print(f"  ✓ {file_path.name}")

    def _validate_permissions(self, workflow_files: List[Path]) -> None:
        """
        Validate workflow permissions are correctly configured.

        Ensures workflows creating issues have 'issues: write' permission.

        Logic from: tests/meta/test_github_actions_validation.py
        """
        if self.verbose:
            print(f"\n🔍 Validating permissions for {len(workflow_files)} workflow(s)...")

        for workflow_file in workflow_files:
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                if not workflow_data:
                    continue

                workflow_str = yaml.dump(workflow_data)

                # Check if workflow creates issues
                creates_issues = (
                    "github.rest.issues.create" in workflow_str
                    or "octokit.rest.issues.create" in workflow_str
                    or "octokit.issues.create" in workflow_str
                )

                if creates_issues:
                    permissions = workflow_data.get("permissions", {})
                    has_issues_write = permissions.get("issues") == "write" or permissions == "write-all"

                    if not has_issues_write:
                        self._error(
                            f"{workflow_file.name}: Creates GitHub issues but lacks 'issues: write' permission.\n"
                            f"  Fix: Add 'permissions: {{issues: write}}' to workflow"
                        )

                if self.verbose:
                    print(f"  ✓ {workflow_file.name}")

            except yaml.YAMLError:
                # Already reported by YAML validation
                pass
            except Exception as e:
                self._error(f"{workflow_file.name}: Permission validation error - {e}")

    def _error(self, message: str) -> None:
        """Record an error."""
        self.errors.append(message)

    def _warning(self, message: str) -> None:
        """Record a warning."""
        self.warnings.append(message)

    def _print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("GitHub Workflow Validation Summary")
        print("=" * 80)

        if self.errors:
            print(f"\n❌ {len(self.errors)} ERROR(S) FOUND:\n")
            for error in self.errors:
                print(f"  ❌ {error}\n")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNING(S):\n")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}\n")

        if not self.errors and not self.warnings:
            print("\n✅ All GitHub workflow validations passed!")

        print("=" * 80)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0=success, 1=validation errors, 2=script error)
    """
    parser = argparse.ArgumentParser(
        description="Comprehensive GitHub Actions workflow validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate workflows in current repository
  %(prog)s

  # Validate workflows with verbose output
  %(prog)s --verbose

  # Validate workflows in specific repository
  %(prog)s --repo-root /path/to/repo

Validations performed:
  1. YAML syntax validation
  2. Context usage validation (github.event.* against triggers)
  3. Action version validation (published tags, no invalid versions)
  4. Permissions validation (workflows creating issues have 'issues: write')

Exit codes:
  0 - All validations passed
  1 - Validation errors found
  2 - Script execution error
        """,
    )

    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Repository root directory (default: current directory)"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit(0) for --help, sys.exit(2) for errors
        return e.code if e.code is not None else 2

    # Validate repo root exists
    if not args.repo_root.exists():
        print(f"ERROR: Repository root does not exist: {args.repo_root}", file=sys.stderr)
        return 2

    # Run validation
    validator = WorkflowValidator(args.repo_root, verbose=args.verbose)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
