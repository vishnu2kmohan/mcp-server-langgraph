#!/usr/bin/env python3
"""
Identify Critical Tests for Pre-Push Validation

This script analyzes the test suite to identify ~200 critical tests (10-15% of suite)
that should run in pre-push hooks for fast feedback while maintaining quality.

Criteria for Critical Tests:
1. Tests that were in the validation gap (141 tests not covered by old hooks)
2. Authentication/Authorization tests
3. API contract tests
4. Security validation tests
5. Regression prevention tests
6. Core business logic tests
7. Tests that frequently fail in CI
8. Tests covering critical code paths (identified by coverage analysis)

Usage:
    python scripts/identify_critical_tests.py [--output critical_tests.txt] [--mark-files]

Options:
    --output FILE       Write list of critical test IDs to file
    --mark-files        Automatically add @pytest.mark.critical to test files
    --dry-run           Show what would be done without making changes
    --interactive       Prompt for confirmation before marking tests
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Test categories to prioritize for critical marking
CRITICAL_PATTERNS = {
    "auth": r"(auth|login|permission|access|token|credential|keycloak)",
    "security": r"(security|secret|injection|xss|csrf|sanitize)",
    "api": r"(api|endpoint|route|request|response|contract)",
    "regression": r"(regression|bug|fix|issue)",
    "core": r"(core|essential|critical|vital)",
    "validation": r"(validation|validate|check|verify)",
    "integration_critical": r"(database|redis|openfga|postgres)",
}

# High-priority test files (always mark tests in these files as critical)
CRITICAL_TEST_FILES = [
    "tests/security/",
    "tests/auth/",
    "tests/api/",
    "tests/regression/",
    "tests/meta/test_coverage_enforcement.py",
    "tests/meta/test_github_actions_validation.py",
    "tests/deployment/test_helm_configuration.py",
]


def collect_all_unit_tests() -> list[str]:
    """Collect all unit test IDs."""
    result = subprocess.run(
        ["pytest", "-m", "unit and not llm", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
    )

    tests = []
    for line in result.stdout.split("\n"):
        if "::" in line and not line.startswith(" ") and not line.startswith("="):
            test_id = line.strip()
            if test_id:
                tests.append(test_id)

    return tests


def categorize_tests(tests: list[str]) -> dict[str, list[str]]:
    """Categorize tests by type."""
    categories = {category: [] for category in CRITICAL_PATTERNS}
    categories["other"] = []

    for test in tests:
        test_lower = test.lower()
        categorized = False

        for category, pattern in CRITICAL_PATTERNS.items():
            if re.search(pattern, test_lower):
                categories[category].append(test)
                categorized = True
                break

        if not categorized:
            categories["other"].append(test)

    return categories


def score_test_priority(test_id: str) -> int:
    """
    Score a test's priority for critical marking (higher = more critical).

    Scoring:
    - In critical file path: +50
    - Matches critical pattern: +30
    - In regression/: +40
    - In security/: +45
    - In auth/: +40
    - In api/: +35
    - Has "critical" in name: +30
    - Has "smoke" in name: +25
    """
    score = 0
    test_lower = test_id.lower()
    file_path = test_id.split("::")[0]

    # File path scoring
    if any(file_path.startswith(cf) for cf in CRITICAL_TEST_FILES):
        score += 50

    if "regression/" in file_path:
        score += 40
    if "security/" in file_path:
        score += 45
    if "auth/" in file_path:
        score += 40
    if "api/" in file_path:
        score += 35
    if "meta/" in file_path:
        score += 30

    # Pattern matching
    for pattern in CRITICAL_PATTERNS.values():
        if re.search(pattern, test_lower):
            score += 15
            break

    # Name-based scoring
    if "critical" in test_lower:
        score += 30
    if "smoke" in test_lower:
        score += 25
    if "essential" in test_lower:
        score += 25
    if "sanity" in test_lower:
        score += 20

    return score


def select_critical_tests(tests: list[str], target_count: int = 200) -> list[str]:
    """Select top N critical tests based on scoring."""
    scored_tests = [(test, score_test_priority(test)) for test in tests]
    scored_tests.sort(key=lambda x: x[1], reverse=True)

    # Take top N tests with score > 0
    critical = [test for test, score in scored_tests[:target_count] if score > 0]

    return critical


def generate_report(all_tests: list[str], critical_tests: list[str]) -> str:
    """Generate analysis report."""
    categories = categorize_tests(critical_tests)

    report = []
    report.append("=" * 80)
    report.append("CRITICAL TEST SELECTION REPORT")
    report.append("=" * 80)
    report.append("")
    report.append(f"Total Unit Tests: {len(all_tests)}")
    report.append(f"Selected Critical Tests: {len(critical_tests)} ({len(critical_tests) / len(all_tests) * 100:.1f}%)")
    report.append("")
    report.append("Critical Tests by Category:")
    report.append("-" * 80)

    for category, tests in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        if tests:
            report.append(f"  {category:25s}: {len(tests):4d} tests")

    report.append("")
    report.append("Sample Critical Tests:")
    report.append("-" * 80)
    for test in critical_tests[:20]:
        score = score_test_priority(test)
        report.append(f"  [{score:3d}] {test}")

    if len(critical_tests) > 20:
        report.append(f"  ... and {len(critical_tests) - 20} more")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", help="Output file for critical test list")
    parser.add_argument("--mark-files", action="store_true", help="Add @pytest.mark.critical to test files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--interactive", action="store_true", help="Prompt for confirmation")
    parser.add_argument("--target-count", type=int, default=200, help="Target number of critical tests (default: 200)")

    args = parser.parse_args()

    print("🔍 Analyzing test suite for critical test selection...")
    print()

    # Collect all tests
    print("Collecting unit tests...")
    all_tests = collect_all_unit_tests()
    print(f"✓ Found {len(all_tests)} total unit tests")
    print()

    # Select critical tests
    print(f"Selecting top {args.target_count} critical tests...")
    critical_tests = select_critical_tests(all_tests, args.target_count)
    print(f"✓ Selected {len(critical_tests)} critical tests")
    print()

    # Generate report
    report = generate_report(all_tests, critical_tests)
    print(report)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            f.write("# Critical Tests for Pre-Push Validation\n")
            f.write("# Auto-generated by identify_critical_tests.py\n")
            f.write(f"# Total: {len(critical_tests)} tests ({len(critical_tests) / len(all_tests) * 100:.1f}% of suite)\n")
            f.write("#\n")
            f.write("# Usage in pytest:\n")
            f.write("#   pytest -m critical tests/\n")
            f.write("\n")

            for test in critical_tests:
                f.write(f"{test}\n")

        print(f"\n✓ Critical test list saved to: {output_path}")

    if args.mark_files:
        print("\n⚠️  Automatic file marking not yet implemented")
        print("Please manually add @pytest.mark.critical to the tests listed above")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
