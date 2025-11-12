#!/usr/bin/env python3
"""
CI/CD Validation Script

Comprehensive pre-commit validation to catch issues before they reach CI.
Run this before committing to prevent CI failures.

Usage:
    python scripts/validate_ci_cd.py
    python scripts/validate_ci_cd.py --fix  # Auto-fix issues where possible

This script prevents issues like:
- Lockfile out of sync (commit 67f8942)
- YAML syntax errors
- Python version mismatches in CI
- Missing test markers
- FastAPI dependency mocking issues

Created after 2025-11-12 CI/CD failure incident.
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import yaml


class Color:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(message: str) -> None:
    """Print a colored header"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{message}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}\n")


def print_success(message: str) -> None:
    """Print a success message"""
    print(f"{Color.GREEN}✓{Color.END} {message}")


def print_error(message: str) -> None:
    """Print an error message"""
    print(f"{Color.RED}✗{Color.END} {message}")


def print_warning(message: str) -> None:
    """Print a warning message"""
    print(f"{Color.YELLOW}⚠{Color.END} {message}")


def print_info(message: str) -> None:
    """Print an info message"""
    print(f"{Color.BLUE}ℹ{Color.END} {message}")


class ValidationResult:
    """Result of a validation check"""
    def __init__(self, passed: bool, message: str, fix_command: str = None):
        self.passed = passed
        self.message = message
        self.fix_command = fix_command


class CICDValidator:
    """Validates CI/CD configuration and catches common issues"""

    def __init__(self, project_root: Path, auto_fix: bool = False):
        self.project_root = project_root
        self.auto_fix = auto_fix
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []
        self.successes: List[ValidationResult] = []

    def validate_lockfile_sync(self) -> ValidationResult:
        """
        Validate uv.lock is synchronized with pyproject.toml

        REGRESSION: Commit 67f8942 - lockfile out of sync blocked all CI/CD
        """
        result = subprocess.run(
            ["uv", "lock", "--check"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return ValidationResult(
                passed=True,
                message="uv.lock is synchronized with pyproject.toml"
            )
        else:
            return ValidationResult(
                passed=False,
                message=(
                    f"uv.lock is OUT OF SYNC with pyproject.toml\n"
                    f"  This blocks all CI/CD workflows (see commit 67f8942)\n"
                    f"  Output: {result.stderr.strip()}"
                ),
                fix_command="uv lock && git add uv.lock"
            )

    def validate_yaml_files(self) -> ValidationResult:
        """Validate all YAML files have correct syntax"""
        yaml_files = list(self.project_root.glob("**/*.yaml")) + \
                     list(self.project_root.glob("**/*.yml"))

        # Exclude certain paths (Helm templates have Go syntax, not pure YAML)
        exclude_patterns = [
            "node_modules", ".venv", "venv", ".git",
            "/helm/", "/templates/",  # Helm templates use Go templating
        ]
        yaml_files = [
            f for f in yaml_files
            if not any(pattern in str(f) for pattern in exclude_patterns)
        ]

        errors = []
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    # Use safe_load_all for multi-document YAML files (Kubernetes manifests)
                    list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                errors.append(f"{yaml_file.relative_to(self.project_root)}: {str(e)}")

        if not errors:
            return ValidationResult(
                passed=True,
                message=f"All {len(yaml_files)} YAML files are valid"
            )
        else:
            return ValidationResult(
                passed=False,
                message=(
                    f"YAML syntax errors in {len(errors)} files:\n" +
                    "\n".join(f"  - {e}" for e in errors[:5])  # Show first 5
                ),
                fix_command="yamllint --fix <file> or manually fix syntax errors"
            )

    def validate_ci_python_versions(self) -> ValidationResult:
        """
        Validate CI workflow uses correct Python version setup

        REGRESSION: uv sync without --python flag caused all jobs to run Python 3.12
        """
        ci_workflow = self.project_root / ".github" / "workflows" / "ci.yaml"

        if not ci_workflow.exists():
            return ValidationResult(
                passed=False,
                message="CI workflow file not found at .github/workflows/ci.yaml"
            )

        with open(ci_workflow) as f:
            content = f.read()

        # Check for correct uv sync pattern
        issues = []

        if "uv sync --python" not in content:
            issues.append(
                "Missing 'uv sync --python' flag - will cause Python version mismatch"
            )

        if "matrix.python-version" in content and "uv sync --python ${{ matrix.python-version }}" not in content:
            issues.append(
                "Python matrix exists but uv sync doesn't use matrix.python-version"
            )

        if issues:
            return ValidationResult(
                passed=False,
                message=(
                    "CI Python version configuration issues:\n" +
                    "\n".join(f"  - {issue}" for issue in issues) +
                    "\n  See commits: c193936, ba5296f"
                )
            )

        return ValidationResult(
            passed=True,
            message="CI workflow uses correct Python version setup"
        )

    def validate_test_markers(self) -> ValidationResult:
        """
        Validate all pytest markers used in tests are registered

        REGRESSION: Commit 67f8942 had to add 5 missing markers
        """
        # Read registered markers from pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        with open(pyproject) as f:
            content = f.read()

        # Extract markers (simple regex approach)
        import re
        marker_matches = re.findall(r'"(\w+):[^"]*"', content)
        registered_markers = set(marker_matches)

        # Find all test files
        test_files = list(self.project_root.glob("tests/**/*.py"))

        # Extract used markers
        used_markers = set()
        for test_file in test_files:
            with open(test_file) as f:
                content = f.read()

            # Remove all comments and docstrings before scanning
            # This prevents false positives from examples in comments
            lines = content.split('\n')
            in_docstring = False
            code_lines = []

            for line in lines:
                stripped = line.strip()

                # Track docstring state
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    continue

                # Skip if in docstring or comment
                if in_docstring or stripped.startswith('#'):
                    continue

                code_lines.append(line)

            # Find markers only in actual code
            code_content = '\n'.join(code_lines)
            matches = re.findall(r'@pytest\.mark\.(\w+)', code_content)
            used_markers.update(matches)

        # Check for unregistered markers
        # Exclude built-in pytest markers and common patterns
        builtin_markers = {
            'parametrize', 'skip', 'skipif', 'xfail', 'filterwarnings',
            'timeout', 'usefixtures', 'asyncio', 'fixture', 'tryfirst',
            'trylast', 'hookwrapper', 'optionalhook', 'first', 'last'
        }

        # Filter out markers that are just partial matches (like 'foo' from conftest, 'requires_' prefix)
        # Only consider markers that appear as full @pytest.mark.marker_name decorators
        valid_used_markers = {
            m for m in used_markers
            if len(m) > 2 and not m.startswith('requires_')  # requires_ is a pattern, not a marker
        }

        unregistered = valid_used_markers - registered_markers - builtin_markers

        if unregistered:
            return ValidationResult(
                passed=False,
                message=(
                    f"Unregistered pytest markers found: {sorted(unregistered)}\n"
                    f"  Add to pyproject.toml [tool.pytest.ini_options] markers list"
                ),
                fix_command=f"Add markers to pyproject.toml: {', '.join(sorted(unregistered))}"
            )

        return ValidationResult(
            passed=True,
            message=f"All {len(used_markers)} used markers are registered"
        )

    def validate_dependency_overrides_pattern(self) -> ValidationResult:
        """
        Validate FastAPI tests use dependency_overrides instead of monkeypatch

        REGRESSION: monkeypatch + reload caused 422 errors due to parameter collision
        """
        api_test_files = list((self.project_root / "tests" / "api").glob("test_*.py"))

        issues = []
        for test_file in api_test_files:
            with open(test_file) as f:
                content = f.read()

            # Check if file has FastAPI tests
            if "FastAPI" not in content and "TestClient" not in content:
                continue

            # If it uses monkeypatch for get_current_user or dependencies, that's wrong
            if "monkeypatch.setattr" in content and ("get_current_user" in content or "get_service_principal_manager" in content or "get_api_key_manager" in content):
                if "app.dependency_overrides" not in content:
                    issues.append(
                        f"{test_file.name}: Uses monkeypatch instead of dependency_overrides"
                    )

        if issues:
            return ValidationResult(
                passed=False,
                message=(
                    "FastAPI tests using monkeypatch (should use dependency_overrides):\n" +
                    "\n".join(f"  - {issue}" for issue in issues) +
                    "\n  See commit 709adda for correct pattern"
                )
            )

        return ValidationResult(
            passed=True,
            message="FastAPI tests use correct dependency_overrides pattern"
        )

    def run_all_validations(self) -> Tuple[int, int, int]:
        """Run all validations and return (passed, warned, failed) counts"""
        print_header("CI/CD Pre-Commit Validation")
        print_info("Catching issues before they reach CI...")
        print()

        validations = [
            ("Lockfile Sync", self.validate_lockfile_sync),
            ("YAML Syntax", self.validate_yaml_files),
            ("CI Python Versions", self.validate_ci_python_versions),
            ("Test Markers", self.validate_test_markers),
            ("Dependency Overrides Pattern", self.validate_dependency_overrides_pattern),
        ]

        for name, validator in validations:
            print(f"{Color.BOLD}Checking: {name}{Color.END}")
            result = validator()

            if result.passed:
                print_success(result.message)
                self.successes.append(result)
            else:
                print_error(result.message)
                if result.fix_command:
                    print_info(f"  Fix: {result.fix_command}")
                self.errors.append(result)

                # Auto-fix if requested
                if self.auto_fix and result.fix_command:
                    print_info(f"  Attempting auto-fix...")
                    try:
                        subprocess.run(
                            result.fix_command,
                            shell=True,
                            cwd=self.project_root,
                            check=True
                        )
                        print_success("  Auto-fix completed")
                    except subprocess.CalledProcessError:
                        print_error("  Auto-fix failed - manual intervention required")

            print()

        # Print summary
        print_header("Validation Summary")
        print(f"{Color.GREEN}✓ Passed:{Color.END}  {len(self.successes)}")
        print(f"{Color.YELLOW}⚠ Warnings:{Color.END} {len(self.warnings)}")
        print(f"{Color.RED}✗ Failed:{Color.END}  {len(self.errors)}")
        print()

        if self.errors:
            print_error(f"{Color.BOLD}VALIDATION FAILED - Fix errors before committing{Color.END}")
            return len(self.successes), len(self.warnings), len(self.errors)

        if self.warnings:
            print_warning("Warnings detected - consider addressing before commit")

        print_success(f"{Color.BOLD}✓ ALL VALIDATIONS PASSED - Safe to commit!{Color.END}")
        return len(self.successes), len(self.warnings), len(self.errors)


def main():
    parser = argparse.ArgumentParser(
        description="Validate CI/CD configuration before committing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_ci_cd.py              # Run all validations
    python scripts/validate_ci_cd.py --fix        # Auto-fix issues where possible

This script prevents CI failures by catching issues locally.
See tests/regression/test_uv_lockfile_sync.py for documented regressions.
        """
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix issues where possible"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    validator = CICDValidator(project_root, auto_fix=args.fix)

    passed, warned, failed = validator.run_all_validations()

    # Exit with error code if validations failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
