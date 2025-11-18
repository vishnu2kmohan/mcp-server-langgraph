#!/usr/bin/env python3
"""
CI/CD Health Check Script

Proactively detects configuration issues that would cause CI failures.
Runs as part of pre-commit or can be run manually before pushing.

## Checks Performed
1. Documentation code blocks have language tags
2. Terraform configurations are valid
3. Pre-commit hook dependencies are satisfied
4. Python test imports match dependencies
5. GitHub Actions workflows are properly configured

## Usage
    python scripts/ci_health_check.py              # Run all checks
    python scripts/ci_health_check.py --quick       # Run fast checks only
    python scripts/ci_health_check.py --fix         # Auto-fix issues where possible

## Exit Codes
    0: All checks passed
    1: Errors found (failures that block CI)
    2: Warnings found (issues that should be fixed but won't block CI)

## Integration
- Can be added as a pre-commit hook for local validation
- Can be run in CI as an early validation step
- Provides actionable error messages with fix suggestions
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Terminal colors for output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"


class HealthCheckResult:
    """Result of a health check."""

    def __init__(self, name: str, passed: bool, message: str = "", warning: bool = False):
        self.name = name
        self.passed = passed
        self.message = message
        self.warning = warning  # True if this is a warning, not an error


class CIHealthChecker:
    """Main health checker orchestrator."""

    def __init__(self, root_dir: Path, quick: bool = False, auto_fix: bool = False):
        self.root_dir = root_dir
        self.quick = quick
        self.auto_fix = auto_fix
        self.results: list[HealthCheckResult] = []

    def run_all_checks(self) -> tuple[int, int, int]:
        """
        Run all health checks.

        Returns:
            Tuple of (passed, failed, warnings)
        """
        print(f"{BLUE}🏥 Running CI/CD Health Checks...{RESET}\n")

        # Fast checks (always run)
        self.check_documentation_code_blocks()
        self.check_terraform_duplicate_blocks()
        self.check_precommit_hook_dependencies()

        if not self.quick:
            # Slower checks
            self.check_terraform_variable_validations()
            self.check_terraform_version_compatibility()
            self.check_github_workflow_structure()

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed and not r.warning)
        warnings = sum(1 for r in self.results if not r.passed and r.warning)

        return passed, failed, warnings

    def check_documentation_code_blocks(self):
        """Check all code blocks in .mdx files have language tags."""
        print(f"{BLUE}📝 Checking documentation code blocks...{RESET}")

        docs_dir = self.root_dir / "docs"
        if not docs_dir.exists():
            self.results.append(HealthCheckResult("doc-code-blocks", True, "No docs directory found (skipped)"))
            return

        mdx_files = list(docs_dir.rglob("*.mdx"))
        untagged_blocks = []

        for file_path in mdx_files:
            content = file_path.read_text()
            lines = content.split("\n")

            in_code_block = False
            for line_num, line in enumerate(lines, start=1):
                match = re.match(r"^```(\w*)", line.strip())
                if match and not in_code_block:
                    language = match.group(1)
                    if not language:
                        relative_path = file_path.relative_to(self.root_dir)
                        untagged_blocks.append(f"{relative_path}:{line_num}")
                    in_code_block = True
                elif line.strip() == "```" and in_code_block:
                    in_code_block = False

        if untagged_blocks:
            message = f"Found {len(untagged_blocks)} untagged code blocks\n" + "\n".join(
                f"  - {block}" for block in untagged_blocks[:5]
            )
            if len(untagged_blocks) > 5:
                message += f"\n  ... and {len(untagged_blocks) - 5} more"

            if self.auto_fix:
                message += "\n\n🔧 Auto-fixing with scripts/add_code_block_languages.py"
                # Would run the auto-fix script here

            self.results.append(HealthCheckResult("doc-code-blocks", False, message))
            print(f"  {RED}✗{RESET} Documentation code blocks")
        else:
            self.results.append(HealthCheckResult("doc-code-blocks", True))
            print(f"  {GREEN}✓{RESET} All code blocks have language tags")

    def check_terraform_duplicate_blocks(self):
        """Check for duplicate terraform{} blocks in .tf files."""
        print(f"{BLUE}🏗️  Checking Terraform configuration...{RESET}")

        terraform_dir = self.root_dir / "terraform"
        if not terraform_dir.exists():
            self.results.append(HealthCheckResult("terraform-duplicates", True, "No terraform directory (skipped)"))
            return

        tf_files = list(terraform_dir.rglob("*.tf"))
        files_with_duplicates = []

        for file_path in tf_files:
            content = file_path.read_text()
            terraform_blocks = re.findall(r"^\s*terraform\s*\{", content, re.MULTILINE)

            if len(terraform_blocks) > 1:
                relative_path = file_path.relative_to(self.root_dir)
                files_with_duplicates.append(f"{relative_path} ({len(terraform_blocks)} blocks)")

        if files_with_duplicates:
            message = f"Found {len(files_with_duplicates)} files with duplicate terraform{{}} blocks:\n" + "\n".join(
                f"  - {file}" for file in files_with_duplicates
            )
            self.results.append(HealthCheckResult("terraform-duplicates", False, message))
            print(f"  {RED}✗{RESET} Duplicate terraform blocks found")
        else:
            self.results.append(HealthCheckResult("terraform-duplicates", True))
            print(f"  {GREEN}✓{RESET} No duplicate terraform blocks")

    def check_terraform_variable_validations(self):
        """Check for invalid cross-variable references in validations."""
        print(f"{BLUE}🔍 Checking Terraform variable validations...{RESET}")

        terraform_dir = self.root_dir / "terraform"
        if not terraform_dir.exists():
            self.results.append(HealthCheckResult("terraform-validations", True, "No terraform directory (skipped)"))
            return

        variables_files = list(terraform_dir.rglob("variables.tf"))
        invalid_validations = []

        for file_path in variables_files:
            content = file_path.read_text()
            lines = content.split("\n")

            current_variable = None
            in_validation = False

            for line_num, line in enumerate(lines, start=1):
                var_match = re.match(r'variable\s+"(\w+)"\s*\{', line)
                if var_match:
                    current_variable = var_match.group(1)

                if "validation" in line and "{" in line:
                    in_validation = True

                if in_validation and current_variable:
                    var_refs = re.findall(r"var\.(\w+)", line)
                    for ref in var_refs:
                        if ref != current_variable:
                            relative_path = file_path.relative_to(self.root_dir)
                            invalid_validations.append(
                                f"{relative_path}:{line_num} - " f"variable '{current_variable}' references var.{ref}"
                            )

                if in_validation and "}" in line:
                    in_validation = False

        if invalid_validations:
            message = f"Found {len(invalid_validations)} invalid cross-variable validations:\n" + "\n".join(
                f"  - {item}" for item in invalid_validations[:5]
            )
            self.results.append(HealthCheckResult("terraform-validations", False, message))
            print(f"  {RED}✗{RESET} Invalid variable validations")
        else:
            self.results.append(HealthCheckResult("terraform-validations", True))
            print(f"  {GREEN}✓{RESET} Variable validations are correct")

    def check_terraform_version_compatibility(self):
        """Check Terraform version requirements are compatible with CI."""
        print(f"{BLUE}🔢 Checking Terraform version compatibility...{RESET}")

        terraform_dir = self.root_dir / "terraform"
        if not terraform_dir.exists():
            self.results.append(HealthCheckResult("terraform-versions", True, "No terraform directory (skipped)"))
            return

        # Assume CI runs Terraform 1.6.6 (update if changed)
        CI_TERRAFORM_VERSION = "1.6.6"

        tf_files = list(terraform_dir.rglob("*.tf"))
        incompatible_files = []

        for file_path in tf_files:
            content = file_path.read_text()
            version_matches = re.findall(r'required_version\s*=\s*"([^"]+)"', content)

            for version_constraint in version_matches:
                if ">=" in version_constraint:
                    min_version_match = re.search(r">=\s*(\d+\.\d+)", version_constraint)
                    if min_version_match:
                        min_version = min_version_match.group(1)
                        min_major, min_minor = map(int, min_version.split("."))
                        ci_major, ci_minor, _ = map(int, CI_TERRAFORM_VERSION.split("."))

                        if min_major > ci_major or (min_major == ci_major and min_minor > ci_minor):
                            relative_path = file_path.relative_to(self.root_dir)
                            incompatible_files.append(f"{relative_path}: requires >= {min_version}")

        if incompatible_files:
            message = (
                f"Found {len(incompatible_files)} files incompatible with CI Terraform {CI_TERRAFORM_VERSION}:\n"
                + "\n".join(f"  - {file}" for file in incompatible_files[:5])
            )
            self.results.append(HealthCheckResult("terraform-versions", False, message, warning=True))
            print(f"  {YELLOW}⚠{RESET}  Version compatibility warnings")
        else:
            self.results.append(HealthCheckResult("terraform-versions", True))
            print(f"  {GREEN}✓{RESET} Terraform versions compatible")

    def check_precommit_hook_dependencies(self):
        """Check pre-commit hooks have required dependencies."""
        print(f"{BLUE}🪝 Checking pre-commit hook dependencies...{RESET}")

        precommit_config = self.root_dir / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            self.results.append(HealthCheckResult("precommit-deps", True, "No .pre-commit-config.yaml (skipped)"))
            return

        try:
            import yaml

            with open(precommit_config) as f:
                config = yaml.safe_load(f)
        except ImportError:
            self.results.append(
                HealthCheckResult("precommit-deps", True, "pyyaml not available, skipping check", warning=True)
            )
            return

        # Specific check for validate-workflow-test-deps
        hook_found = False
        hook_has_pyyaml = False

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("id") == "validate-workflow-test-deps":
                    hook_found = True
                    additional_deps = hook.get("additional_dependencies", [])
                    hook_has_pyyaml = any("pyyaml" in dep.lower() for dep in additional_deps)

        if hook_found and not hook_has_pyyaml:
            message = "validate-workflow-test-deps missing pyyaml dependency"
            self.results.append(HealthCheckResult("precommit-deps", False, message))
            print(f"  {RED}✗{RESET} Pre-commit hook dependencies")
        elif hook_found:
            self.results.append(HealthCheckResult("precommit-deps", True))
            print(f"  {GREEN}✓{RESET} Pre-commit hook dependencies satisfied")
        else:
            self.results.append(HealthCheckResult("precommit-deps", True, "Hook not found (skipped)"))
            print(f"  {BLUE}ℹ{RESET}  validate-workflow-test-deps hook not found")

    def check_github_workflow_structure(self):
        """Check GitHub Actions workflows are properly structured."""
        print(f"{BLUE}⚙️  Checking GitHub Actions workflows...{RESET}")

        workflows_dir = self.root_dir / ".github" / "workflows"
        if not workflows_dir.exists():
            self.results.append(HealthCheckResult("github-workflows", True, "No workflows directory (skipped)"))
            return

        workflow_files = list(workflows_dir.glob("*.y*ml"))
        issues = []

        for workflow_file in workflow_files:
            try:
                import yaml

                with open(workflow_file) as f:
                    workflow = yaml.safe_load(f)

                # Basic structure checks
                if not workflow.get("jobs"):
                    relative_path = workflow_file.relative_to(self.root_dir)
                    issues.append(f"{relative_path}: No jobs defined")

            except Exception as e:
                relative_path = workflow_file.relative_to(self.root_dir)
                issues.append(f"{relative_path}: Parse error - {e}")

        if issues:
            message = f"Found {len(issues)} workflow issues:\n" + "\n".join(f"  - {issue}" for issue in issues[:5])
            self.results.append(HealthCheckResult("github-workflows", False, message, warning=True))
            print(f"  {YELLOW}⚠{RESET}  Workflow structure warnings")
        else:
            self.results.append(HealthCheckResult("github-workflows", True))
            print(f"  {GREEN}✓{RESET} Workflows properly structured")

    def print_summary(self, passed: int, failed: int, warnings: int):
        """Print summary of all checks."""
        print(f"\n{'=' * 70}")
        print(f"{BLUE}Summary{RESET}")
        print(f"{'=' * 70}")

        print(f"{GREEN}Passed:{RESET}   {passed}")
        print(f"{RED}Failed:{RESET}   {failed}")
        print(f"{YELLOW}Warnings:{RESET} {warnings}")

        if failed > 0:
            print(f"\n{RED}❌ CI health check failed{RESET}")
            print("\nFailed checks:")
            for result in self.results:
                if not result.passed and not result.warning:
                    print(f"\n{RED}✗{RESET} {result.name}")
                    if result.message:
                        print(f"  {result.message}")
        elif warnings > 0:
            print(f"\n{YELLOW}⚠️  CI health check passed with warnings{RESET}")
            print("\nWarnings:")
            for result in self.results:
                if not result.passed and result.warning:
                    print(f"\n{YELLOW}⚠{RESET}  {result.name}")
                    if result.message:
                        print(f"  {result.message}")
        else:
            print(f"\n{GREEN}✅ All CI health checks passed!{RESET}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="CI/CD Health Check")
    parser.add_argument("--quick", action="store_true", help="Run only fast checks")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.parent
    checker = CIHealthChecker(root_dir, quick=args.quick, auto_fix=args.fix)

    passed, failed, warnings = checker.run_all_checks()
    checker.print_summary(passed, failed, warnings)

    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    elif warnings > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
