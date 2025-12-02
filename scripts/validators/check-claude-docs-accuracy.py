#!/usr/bin/env python3
"""
Verify Claude Code documentation accuracy.

This script checks that metrics and versions in .github/CLAUDE.md match
actual values in the codebase. Prevents documentation drift.

Usage:
    python scripts/validators/check-claude-docs-accuracy.py
    python scripts/validators/check-claude-docs-accuracy.py --fix  # Show suggested fixes

Exit codes:
    0 - All checks passed
    1 - Some checks failed (documentation drift detected)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Fallback to script location
        return Path(__file__).parent.parent.parent


def count_test_functions(repo_root: Path) -> int:
    """Count total test functions in tests/ directory."""
    count = 0
    tests_dir = repo_root / "tests"
    if tests_dir.exists():
        for test_file in tests_dir.rglob("test_*.py"):
            content = test_file.read_text()
            count += len(re.findall(r"def test_", content))
    return count


def count_pytest_markers(repo_root: Path) -> int:
    """Count pytest markers in pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return 0

    content = pyproject.read_text()
    # Find markers section
    markers = re.findall(r'^\s+"([a-z_]+):\s', content, re.MULTILINE)
    return len(markers)


def count_precommit_hooks(repo_root: Path) -> int:
    """Count pre-commit hooks."""
    config = repo_root / ".pre-commit-config.yaml"
    if not config.exists():
        return 0

    content = config.read_text()
    hooks = re.findall(r"^\s+-\s+id:", content, re.MULTILINE)
    return len(hooks)


def count_make_targets(repo_root: Path) -> int:
    """Count Make targets."""
    makefile = repo_root / "Makefile"
    if not makefile.exists():
        return 0

    content = makefile.read_text()
    # Match target definitions (name followed by colon)
    targets = re.findall(r"^[a-zA-Z][a-zA-Z0-9_-]*:", content, re.MULTILINE)
    return len(targets)


def count_slash_commands(repo_root: Path) -> int:
    """Count slash commands in .claude/commands/."""
    commands_dir = repo_root / ".claude" / "commands"
    if not commands_dir.exists():
        return 0

    count = 0
    for md_file in commands_dir.glob("*.md"):
        if md_file.name != "README.md":
            count += 1
    return count


def get_python_version(repo_root: Path) -> str:
    """Get Python version from .python-version."""
    version_file = repo_root / ".python-version"
    if version_file.exists():
        return version_file.read_text().strip()
    return ""


def get_langgraph_version(repo_root: Path) -> str:
    """Get LangGraph version requirement from pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return ""

    content = pyproject.read_text()
    match = re.search(r'"langgraph([>=<]+[\d.]+)"', content)
    if match:
        return match.group(0).strip('"')
    return ""


def get_coverage_threshold(repo_root: Path) -> int:
    """Get coverage threshold from pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return 0

    content = pyproject.read_text()
    match = re.search(r"fail_under\s*=\s*(\d+)", content)
    if match:
        return int(match.group(1))
    return 0


def extract_claude_md_value(content: str, pattern: str) -> str | None:
    """Extract value from CLAUDE.md using regex pattern."""
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description="Check Claude docs accuracy")
    parser.add_argument("--fix", action="store_true", help="Show suggested fixes")
    args = parser.parse_args()

    repo_root = get_repo_root()
    claude_md = repo_root / ".github" / "CLAUDE.md"

    if not claude_md.exists():
        print("ERROR: .github/CLAUDE.md not found")
        return 1

    claude_content = claude_md.read_text()

    print("🔍 Checking Claude Code documentation accuracy...\n")

    checks = []
    all_passed = True

    # 1. Test count
    actual_tests = count_test_functions(repo_root)
    claimed_tests = extract_claude_md_value(claude_content, r"(\d+(?:,\d+)?)\+?\s*tests")
    if claimed_tests:
        claimed_num = int(claimed_tests.replace(",", ""))
        passed = abs(actual_tests - claimed_num) < 100  # Allow 100 variance
        status = "✅" if passed else "❌"
        checks.append((status, f"Test count: claimed {claimed_tests}, actual {actual_tests:,}"))
        if not passed:
            all_passed = False

    # 2. Pytest markers
    actual_markers = count_pytest_markers(repo_root)
    claimed_markers = extract_claude_md_value(claude_content, r"(\d+)\s*(?:pytest\s*)?markers")
    if claimed_markers:
        claimed_num = int(claimed_markers)
        passed = actual_markers == claimed_num
        status = "✅" if passed else "❌"
        checks.append((status, f"Pytest markers: claimed {claimed_markers}, actual {actual_markers}"))
        if not passed:
            all_passed = False

    # 3. Pre-commit hooks
    actual_hooks = count_precommit_hooks(repo_root)
    claimed_hooks = extract_claude_md_value(claude_content, r"(\d+)\s*hooks")
    if claimed_hooks:
        claimed_num = int(claimed_hooks)
        passed = actual_hooks == claimed_num
        status = "✅" if passed else "❌"
        checks.append((status, f"Pre-commit hooks: claimed {claimed_hooks}, actual {actual_hooks}"))
        if not passed:
            all_passed = False

    # 4. Make targets
    actual_targets = count_make_targets(repo_root)
    claimed_targets = extract_claude_md_value(claude_content, r"(\d+)\s*(?:Make\s*)?targets")
    if claimed_targets:
        claimed_num = int(claimed_targets)
        passed = abs(actual_targets - claimed_num) < 5  # Allow 5 variance
        status = "✅" if passed else "❌"
        checks.append((status, f"Make targets: claimed {claimed_targets}, actual {actual_targets}"))
        if not passed:
            all_passed = False

    # 5. Slash commands
    actual_commands = count_slash_commands(repo_root)
    claimed_commands = extract_claude_md_value(claude_content, r"(\d+)\s*slash\s*commands")
    if claimed_commands:
        claimed_num = int(claimed_commands)
        passed = actual_commands == claimed_num
        status = "✅" if passed else "❌"
        checks.append((status, f"Slash commands: claimed {claimed_commands}, actual {actual_commands}"))
        if not passed:
            all_passed = False

    # 6. Python version
    actual_python = get_python_version(repo_root)
    claimed_python = extract_claude_md_value(claude_content, r"Python\s*Version[:\s]+(\d+\.\d+(?:\.\d+)?)")
    if claimed_python and actual_python:
        # Check if major.minor match
        actual_major_minor = ".".join(actual_python.split(".")[:2])
        passed = claimed_python.startswith(actual_major_minor)
        status = "✅" if passed else "❌"
        checks.append((status, f"Python version: claimed {claimed_python}, actual {actual_python}"))
        if not passed:
            all_passed = False

    # 7. LangGraph version
    actual_langgraph = get_langgraph_version(repo_root)
    claimed_langgraph = extract_claude_md_value(claude_content, r"LangGraph.*?([>=<]+\d+\.\d+\.\d+)")
    if claimed_langgraph and actual_langgraph:
        passed = claimed_langgraph in actual_langgraph or actual_langgraph in claimed_langgraph
        status = "✅" if passed else "❌"
        checks.append((status, f"LangGraph version: claimed {claimed_langgraph}, actual {actual_langgraph}"))
        if not passed:
            all_passed = False

    # 8. Coverage threshold
    actual_coverage = get_coverage_threshold(repo_root)
    claimed_coverage = extract_claude_md_value(claude_content, r"(\d+)%\s*\(?(?:targeting|target)")
    if claimed_coverage:
        claimed_num = int(claimed_coverage)
        passed = actual_coverage == claimed_num
        status = "✅" if passed else "❌"
        checks.append((status, f"Coverage threshold: claimed {claimed_coverage}%, actual {actual_coverage}%"))
        if not passed:
            all_passed = False

    # Print results
    for status, message in checks:
        print(f"  {status} {message}")

    print()

    if all_passed:
        print("✅ All documentation checks passed!")
        return 0
    else:
        print("❌ Documentation drift detected!")
        if args.fix:
            print("\nSuggested fixes:")
            print("  1. Update .github/CLAUDE.md with actual values")
            print("  2. Run: python scripts/validators/check-claude-docs-accuracy.py")
        else:
            print("\nRun with --fix for suggestions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
