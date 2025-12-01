#!/usr/bin/env python3
"""
GitHub Actions Workflow File Reference Validator

Validates that files referenced in workflows actually exist.

Prevents errors like:
- Script paths that moved but workflows not updated
- Test paths that reorganized but workflows still reference old locations
- Missing files that cause silent failures with || true patterns

Run as:
    python scripts/validation/validate_workflow_file_references.py

Exit codes:
    0 - All file references valid
    1 - Missing file references found
    2 - Invalid workflow YAML
"""

import re
import sys
from pathlib import Path
from typing import Any

import yaml


class WorkflowFileReferenceValidator:
    """Validates file references in GitHub Actions workflows."""

    # Patterns to extract file references from workflows
    FILE_REFERENCE_PATTERNS = [
        # Script execution patterns
        (r"python3?\s+([^\s]+\.py)", "Python script"),
        (r"pytest\s+([^\s]+\.py)", "Pytest test file"),
        (r"uv\s+run\s+python\s+([^\s]+\.py)", "Python script (uv run)"),
        (r"uv\s+run\s+pytest\s+([^\s]+\.py)", "Pytest test file (uv run)"),
        (r"bash\s+([^\s]+\.sh)", "Bash script"),
        (r"sh\s+([^\s]+\.sh)", "Shell script"),
        # Direct file references
        (r"'([^']+\.(py|sh|yaml|yml|json|toml))'", "Quoted file"),
        (r'"([^"]+\.(py|sh|yaml|yml|json|toml))"', "Double-quoted file"),
    ]

    def __init__(self, workflow_dir: Path, repo_root: Path):
        self.workflow_dir = workflow_dir
        self.repo_root = repo_root
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.checked_files: set[str] = set()

    def validate_all(self) -> bool:
        """Validate all workflow files in the directory."""
        workflow_files = list(self.workflow_dir.glob("*.yaml")) + list(self.workflow_dir.glob("*.yml"))

        if not workflow_files:
            print(f"⚠️  No workflow files found in {self.workflow_dir}")
            return True

        print(f"🔍 Validating file references in {len(workflow_files)} workflow files...\n")

        for workflow_file in workflow_files:
            self._validate_workflow(workflow_file)

        return self._print_results()

    def _validate_workflow(self, workflow_file: Path) -> None:
        """Validate file references in a single workflow file."""
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

        # Check paths: trigger conditions
        self._check_path_triggers(workflow_file, workflow)

        # Check file references in run commands
        self._check_run_commands(workflow_file, content)

    def _check_path_triggers(self, workflow_file: Path, workflow: dict[str, Any]) -> None:
        """Check file paths in pull_request/push path triggers."""
        if "on" not in workflow:
            return

        on_config = workflow["on"]
        if isinstance(on_config, str):
            return

        for trigger_name, trigger_config in on_config.items():
            if trigger_name not in ["pull_request", "push"]:
                continue

            if not isinstance(trigger_config, dict):
                continue

            if "paths" not in trigger_config:
                continue

            paths = trigger_config["paths"]
            if not isinstance(paths, list):
                continue

            for path_pattern in paths:
                if not isinstance(path_pattern, str):
                    continue

                # Skip glob patterns - they're patterns, not exact files
                if "*" in path_pattern or "**" in path_pattern:
                    continue

                # Check if file/directory exists
                full_path = self.repo_root / path_pattern
                if not full_path.exists():
                    self.errors.append(
                        {
                            "file": workflow_file.name,
                            "error": f"Path trigger references non-existent path: {path_pattern}",
                            "path": path_pattern,
                            "trigger": trigger_name,
                        }
                    )

    def _check_run_commands(self, workflow_file: Path, content: str) -> None:
        """Check file references in run: commands."""
        for line_num, line in enumerate(content.split("\n"), start=1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Skip echo commands (they contain text, not file references)
            if "echo " in line.lower():
                continue

            # Skip temporary file paths
            if "/tmp/" in line or "tmp/" in line:
                continue

            # Skip HTTP/HTTPS URLs
            if "http://" in line or "https://" in line:
                continue

            # Extract file references using patterns
            for pattern, ref_type in self.FILE_REFERENCE_PATTERNS:
                for match in re.finditer(pattern, line):
                    file_ref = match.group(1)

                    # Skip variables and expressions
                    if "$" in file_ref or "{" in file_ref:
                        continue

                    # Skip if already checked
                    if file_ref in self.checked_files:
                        continue
                    self.checked_files.add(file_ref)

                    # Normalize path (remove leading ./ but preserve .github)
                    if file_ref.startswith("./") and not file_ref.startswith("./.github"):
                        file_ref = file_ref[2:]

                    # Skip test patterns (pytest supports patterns)
                    if "::" in file_ref:  # pytest::test_name syntax
                        file_ref = file_ref.split("::")[0]

                    # Skip runtime-created paths (created by workflow during execution)
                    # These are checked out or created in the workflow, not pre-existing
                    runtime_prefixes = [
                        "gh-pages",  # Checked out gh-pages branch
                        "artifacts",  # Downloaded artifacts
                        "trends",  # Created during workflow
                        "dashboard",  # Created during workflow
                        "badges",  # Created during workflow
                        "coverage-html",  # Generated coverage reports
                    ]
                    if any(file_ref.startswith(prefix) for prefix in runtime_prefixes):
                        continue

                    # Check if file exists
                    full_path = self.repo_root / file_ref
                    if not full_path.exists():
                        # Check if it's a pattern or directory
                        if "*" not in file_ref and not (self.repo_root / Path(file_ref).parent).exists():
                            self.errors.append(
                                {
                                    "file": workflow_file.name,
                                    "line": line_num,
                                    "error": f"Referenced file does not exist: {file_ref}",
                                    "path": file_ref,
                                    "type": ref_type,
                                    "content": line.strip(),
                                }
                            )

    def _print_results(self) -> bool:
        """Print validation results."""
        if self.warnings:
            print("\n⚠️  WARNINGS:\n")
            for warning in self.warnings:
                print(f"  {warning['file']}:{warning.get('line', '?')}")
                print(f"    {warning['error']}")
                if "content" in warning:
                    print(f"    → {warning['content']}")
                print()

        if self.errors:
            print("\n❌ ERRORS:\n")
            for error in self.errors:
                print(f"  {error['file']}:{error.get('line', '?')}")
                print(f"    {error['error']}")
                if "path" in error:
                    print(f"    Missing: {error['path']}")
                if "content" in error:
                    print(f"    → {error['content']}")
                print()

            print(f"❌ Found {len(self.errors)} file reference error(s)\n")
            return False

        print("✅ All workflow file references are valid\n")
        return True


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent
    workflow_dir = repo_root / ".github" / "workflows"

    if not workflow_dir.exists():
        print(f"❌ Workflow directory not found: {workflow_dir}")
        return 2

    validator = WorkflowFileReferenceValidator(workflow_dir, repo_root)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
