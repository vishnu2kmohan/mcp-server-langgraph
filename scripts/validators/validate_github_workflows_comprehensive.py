#!/usr/bin/env python3
"""
GitHub Actions Workflow Context Validator

This script validates that GitHub Actions workflows don't reference undefined
context variables based on their triggers.

Prevents bugs like:
- Referencing github.event.workflow_run.* when workflow_run trigger is not enabled
- Referencing github.event.pull_request.* when pull_request trigger is not enabled
- Missing guards for context that may be undefined

Run as:
    python scripts/validate_github_workflows.py [--fix]

Exit codes:
    0 - All validations passed
    1 - Validation errors found
    2 - Invalid workflow YAML
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml


class WorkflowValidator:
    """Validates GitHub Actions workflow files for context usage errors."""

    # Context patterns to detect
    CONTEXT_PATTERNS = {
        "workflow_run": re.compile(r"github\.event\.workflow_run"),
        "pull_request": re.compile(r"github\.event\.pull_request"),
        "issue": re.compile(r"github\.event\.issue"),
        "schedule": re.compile(r"github\.event\.schedule"),
        "deployment": re.compile(r"github\.event\.deployment"),
    }

    # Action version patterns to validate (consolidated from validate-github-action-versions hook)
    # Example: astral-sh/setup-uv@v7, actions/checkout@v5
    ACTION_VERSION_PATTERN = re.compile(r"uses:\s+[\w-]+/[\w-]+@v\d+")

    # Permissions patterns (workflows using github.rest.issues.create must have 'issues: write')
    # Note: Permission validation is a future enhancement
    PERMISSION_PATTERNS = {"issues": "issues: write", "pull_requests": "pull-requests: write"}

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def validate_all(self) -> bool:
        """Validate all workflow files in the directory."""
        workflow_files = list(self.workflow_dir.glob("*.yaml")) + list(self.workflow_dir.glob("*.yml"))

        if not workflow_files:
            print(f"⚠️  No workflow files found in {self.workflow_dir}")
            return True

        print(f"🔍 Validating {len(workflow_files)} workflow files...\n")

        for workflow_file in workflow_files:
            self._validate_workflow(workflow_file)

        return self._print_results()

    def _validate_workflow(self, workflow_file: Path) -> None:
        """Validate a single workflow file."""
        # print(f"Checking {workflow_file.name}...")

        try:
            with open(workflow_file) as f:
                content = f.read()
                workflow = yaml.safe_load(content)
        except yaml.YAMLError as e:
            self.errors.append(
                {
                    "file": workflow_file.name,
                    "error": f"Invalid YAML: {e}",
                    "line": getattr(e, "problem_mark", None),
                }
            )
            return
        except Exception as e:
            self.errors.append({"file": workflow_file.name, "error": f"Failed to read: {e}"})
            return

        # Get enabled triggers
        triggers = self._get_triggers(workflow)

        # Check for context usage
        for context_name, pattern in self.CONTEXT_PATTERNS.items():
            self._check_context_usage(workflow_file, content, context_name, pattern, triggers)

    def _get_triggers(self, workflow: dict) -> set[str]:
        """Extract enabled triggers from workflow."""
        triggers = set()

        if "on" not in workflow:
            return triggers

        on_config = workflow["on"]

        # Handle string trigger (single trigger)
        if isinstance(on_config, str):
            triggers.add(on_config)
        # Handle list of triggers
        elif isinstance(on_config, list):
            triggers.update(on_config)
        # Handle dict of triggers with configuration
        elif isinstance(on_config, dict):
            for trigger, config in on_config.items():
                # Trigger is enabled if:
                # - config is None (simple trigger with no config)
                # - config is a dict (trigger with configuration like branches, paths, etc.)
                # - config is a list (trigger with types)
                # Only skip if explicitly disabled or empty
                if isinstance(config, dict) and len(config) == 0:
                    continue  # Empty dict = disabled
                if isinstance(config, list) and len(config) == 0:
                    continue  # Empty list = disabled
                triggers.add(trigger)

        return triggers

    def _check_context_usage(
        self, workflow_file: Path, content: str, context_name: str, pattern: re.Pattern, triggers: set[str]
    ) -> None:
        """Check if a context is used but the corresponding trigger is not enabled."""
        matches = pattern.findall(content)

        if not matches:
            return  # Context not used, no problem

        # Check if the corresponding trigger is enabled
        if context_name not in triggers:
            # Check if there are guards protecting the context usage
            has_guards = self._check_for_guards(content, context_name)

            if has_guards:
                # Context is guarded, this is OK
                return

            # Context used without trigger or guards
            line_numbers = []
            for i, line in enumerate(content.split("\n"), 1):
                if pattern.search(line):
                    line_numbers.append(i)

            self.errors.append(
                {
                    "file": workflow_file.name,
                    "context": context_name,
                    "lines": line_numbers,
                    "error": f"Uses github.event.{context_name}.* but '{context_name}' trigger is not enabled",
                    "fix": f"Either enable '{context_name}' trigger or add guards: if: github.event_name == '{context_name}'",
                }
            )

    def _check_for_guards(self, content: str, context_name: str) -> bool:
        """Check if there are conditional guards protecting context usage."""
        guard_patterns = [
            # if: github.event_name == 'pull_request'
            re.compile(rf"if:\s+github\.event_name\s+==\s+['\"]{context_name}['\"]"),
            # ${{ github.event_name == 'pull_request' }}
            re.compile(rf"\$\{{\{{\s*github\.event_name\s*==\s*['\"]{context_name}['\"]\s*\}}\}}\}}"),
            # Fallback patterns with || operator (safe because of fallback)
            # github.event.pull_request.number || github.ref
            re.compile(rf"github\.event\.{context_name}\.\w+\s+\|\|"),
        ]

        for pattern in guard_patterns:
            if pattern.search(content):
                return True

        return False

    def _print_results(self) -> bool:
        """Print validation results and return success status."""
        print("\n" + "=" * 80)

        if self.errors:
            print(f"❌ Found {len(self.errors)} validation error(s):\n")
            for error in self.errors:
                print(f"  File: {error['file']}")
                if "context" in error:
                    print(f"  Context: github.event.{error['context']}.*")
                    print(f"  Lines: {', '.join(map(str, error['lines']))}")
                print(f"  Error: {error['error']}")
                if "fix" in error:
                    print(f"  Fix: {error['fix']}")
                print()

        if self.warnings:
            print(f"⚠️  Found {len(self.warnings)} warning(s):\n")
            for warning in self.warnings:
                print(f"  File: {warning['file']}")
                print(f"  Warning: {warning['warning']}")
                print()

        if not self.errors and not self.warnings:
            print("✅ All workflow validations passed!")
            print()

        print("=" * 80)

        return len(self.errors) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate GitHub Actions workflows for context usage errors")
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        help="Path to workflows directory (default: <repo-root>/.github/workflows)",
    )
    parser.add_argument("--fix", action="store_true", help="Automatically fix issues (not yet implemented)")

    args = parser.parse_args()

    # Determine workflow directory
    if args.workflow_dir:
        workflow_dir = args.workflow_dir
    elif args.repo_root:
        workflow_dir = args.repo_root / ".github" / "workflows"
    else:
        workflow_dir = Path(".github/workflows")

    if not workflow_dir.exists():
        print(f"❌ Error: Workflow directory not found: {workflow_dir}")
        return 2

    validator = WorkflowValidator(workflow_dir)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
