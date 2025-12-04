#!/usr/bin/env python3
"""
Validate repository root path calculations in test files.

This script prevents hardcoded path calculations that break
when files are moved between directories.

Validates:
1. No hardcoded .parents[N] without marker file validation
2. No hardcoded Path(__file__).parent.parent... chains for REPO_ROOT
3. Use of project_root fixture or get_repo_root() function
4. Marker file validation (.git, pyproject.toml) when using .parents[N]

Exit codes:
- 0: All checks passed
- 1: Violations found
- 2: Script error

Usage:
    python scripts/validators/validate_repo_root_calculations.py
    python scripts/validators/validate_repo_root_calculations.py --fix  # Auto-fix violations (not implemented)

References:
- tests/helpers/path_helpers.py: get_repo_root() implementation
- tests/meta/test_path_helpers.py: Meta-tests for path calculations
- INTEGRATION_TEST_FINDINGS.md: Path calculation errors

Bug Fixed (2025-12-04):
- test_helm_templates.py moved from tests/deployment/ to tests/integration/deployment/
- Path(__file__).parent.parent.parent was wrong after move (resolved to tests/)
- Now recommends using get_repo_root() from tests.helpers.path_helpers
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """Path calculation violation"""

    file_path: Path
    line_number: int
    code: str
    message: str
    severity: str  # "error" or "warning"


class PathCalculationVisitor(ast.NodeVisitor):
    """AST visitor to detect .parents[N] path calculations"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations: list[Violation] = []
        self.has_marker_validation = False
        self.has_project_root_fixture = False
        self.has_get_repo_root = False

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript operations like .parents[N]"""
        # Check if this is .parents[N] pattern
        if isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            # Get the line of code
            line_number = node.lineno
            # This is a .parents[N] access
            # Check if there's marker validation nearby (within 10 lines)
            self.violations.append(
                Violation(
                    file_path=self.file_path,
                    line_number=line_number,
                    code=f".parents[{ast.unparse(node.slice)}]",
                    message="Hardcoded .parents[N] without marker validation",
                    severity="warning",  # Warning until we check context
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for get_repo_root() function or project_root fixture"""
        if node.name == "get_repo_root":
            self.has_get_repo_root = True
        elif node.name == "project_root":
            # Check if it's a pytest fixture
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "fixture":
                            self.has_project_root_fixture = True
                elif isinstance(decorator, ast.Name):
                    if decorator.id == "fixture":
                        self.has_project_root_fixture = True
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Check for marker file strings"""
        if isinstance(node.value, str):
            if node.value in [".git", "pyproject.toml", "setup.py"]:
                self.has_marker_validation = True
        self.generic_visit(node)


# Pattern to detect REPO_ROOT = Path(__file__).parent.parent... assignments
# This fragile pattern breaks when files are moved between directories
REPO_ROOT_PATTERN = re.compile(
    r"^(?P<varname>\w*ROOT\w*)\s*=\s*Path\(__file__\)(?:\.parent)+\s*$",
    re.MULTILINE,
)

# Pattern to detect get_repo_root() import (correct usage)
GET_REPO_ROOT_IMPORT = re.compile(r"from\s+tests\.helpers\.path_helpers\s+import.*get_repo_root")


def validate_file(file_path: Path) -> list[Violation]:
    """
    Validate a single Python file for path calculation issues.

    Args:
        file_path: Path to Python file

    Returns:
        List of violations found
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except SyntaxError:
        # Skip files with syntax errors (might be incomplete)
        return []
    except Exception as e:
        return [
            Violation(
                file_path=file_path,
                line_number=0,
                code="",
                message=f"Failed to parse: {e}",
                severity="error",
            )
        ]

    visitor = PathCalculationVisitor(file_path)
    visitor.visit(tree)

    # Also check for regex pattern violations
    real_violations = []

    # Check for REPO_ROOT = Path(__file__).parent.parent... pattern
    # But only if file doesn't import get_repo_root()
    if not GET_REPO_ROOT_IMPORT.search(content):
        for line_num, line in enumerate(content.split("\n"), 1):
            match = REPO_ROOT_PATTERN.match(line.strip())
            if match:
                var_name = match.group("varname")
                real_violations.append(
                    Violation(
                        file_path=file_path,
                        line_number=line_num,
                        code=line.strip(),
                        message=f"Fragile {var_name} calculation using .parent chain. Use get_repo_root() instead.",
                        severity="warning",  # Warning for now, as many files use this pattern
                    )
                )

    # Filter AST violations based on context
    for violation in visitor.violations:
        # If file has marker validation or proper fixtures, downgrade to info
        if visitor.has_marker_validation or visitor.has_get_repo_root or visitor.has_project_root_fixture:
            # This is acceptable - file validates with markers
            continue
        else:
            # Real violation - no marker validation
            real_violations.append(
                Violation(
                    file_path=violation.file_path,
                    line_number=violation.line_number,
                    code=violation.code,
                    message="Uses .parents[N] without marker file validation (.git, pyproject.toml)",
                    severity="error",
                )
            )

    return real_violations


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for validation script.

    Args:
        argv: Command-line arguments. If None, uses sys.argv (CLI mode).
              Pass [] for module import mode with defaults.

    Returns:
        Exit code (0 = success, 1 = violations found, 2 = error)
    """
    parser = argparse.ArgumentParser(description="Validate repo root path calculations")
    parser.add_argument("--fix", action="store_true", help="Auto-fix violations (not implemented)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args(argv if argv is not None else None)

    # Find repository root
    script_dir = Path(__file__).parent
    # Navigate up from scripts/validation/ to repo root
    repo_root = script_dir.parent.parent

    # Validate we're at repo root
    if not (repo_root / ".git").exists() and not (repo_root / "pyproject.toml").exists():
        print("ERROR: Cannot find repository root", file=sys.stderr)
        return 2

    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        print("ERROR: tests/ directory not found", file=sys.stderr)
        return 2

    # Find all Python test files
    test_files = list(tests_dir.rglob("*.py"))

    if args.verbose:
        print(f"Checking {len(test_files)} test files...")

    all_violations: list[Violation] = []

    for test_file in test_files:
        violations = validate_file(test_file)
        all_violations.extend(violations)

    # Report violations
    if all_violations:
        print(f"\n❌ Found {len(all_violations)} path calculation violations:\n")

        for violation in all_violations:
            rel_path = violation.file_path.relative_to(repo_root)
            severity_icon = "🔴" if violation.severity == "error" else "⚠️"
            print(f"{severity_icon} {rel_path}:{violation.line_number}")
            print(f"   Code: {violation.code}")
            print(f"   Issue: {violation.message}")
            print()

        print("\nRecommendations:")
        print("1. Use get_repo_root() from tests/helpers/path_helpers.py (PREFERRED):")
        print("   from tests.helpers.path_helpers import get_repo_root")
        print()
        print("   # ❌ OLD (fragile - breaks when file moves):")
        print("   REPO_ROOT = Path(__file__).parent.parent.parent")
        print()
        print("   # ✅ NEW (robust - works from any file location):")
        print("   REPO_ROOT = get_repo_root()")
        print()
        print("2. For test functions, use the project_root fixture:")
        print("   def test_something(project_root):")
        print('       config_path = project_root / "config.yaml"')
        print()
        print("3. See tests/meta/test_path_helpers.py for usage examples")
        print()

        return 1

    if args.verbose:
        print(f"✅ All {len(test_files)} test files passed path calculation validation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
