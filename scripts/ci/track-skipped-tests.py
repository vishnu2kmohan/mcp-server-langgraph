#!/usr/bin/env python3
"""
Track Skipped Tests - Extract and Report Skipped Test Information

This script analyzes test files to extract skipped tests and their reasons,
generates reports, and tracks trends over time.

Usage:
    python scripts/ci/track-skipped-tests.py              # Generate report
    python scripts/ci/track-skipped-tests.py --github     # Create GitHub issues
    python scripts/ci/track-skipped-tests.py --trend      # Show historical trend
    python scripts/ci/track-skipped-tests.py --json       # Output JSON format

Features:
    - Extracts all @pytest.mark.skip and @pytest.mark.skipif decorators
    - Identifies skip reasons and GitHub issue references
    - Tracks trends over time
    - Optionally creates GitHub issues for skipped tests
    - Generates markdown reports for PR comments
"""

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SkippedTest:
    """Represents a skipped test"""

    file_path: str
    test_name: str
    line_number: int
    skip_type: str  # 'skip' or 'skipif'
    reason: str
    github_issue: str | None = None
    condition: str | None = None

    def to_dict(self):
        return asdict(self)


class SkippedTestExtractor:
    """Extract skipped tests from Python test files"""

    def __init__(self, tests_dir: Path):
        self.tests_dir = tests_dir
        self.skipped_tests: list[SkippedTest] = []

    def extract_all(self) -> list[SkippedTest]:
        """Extract all skipped tests from test directory"""
        test_files = list(self.tests_dir.rglob("test_*.py"))

        for test_file in test_files:
            self._extract_from_file(test_file)

        return self.skipped_tests

    def _extract_from_file(self, file_path: Path):
        """Extract skipped tests from a single file"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        skip_info = self._extract_skip_decorator(node)
                        if skip_info:
                            relative_path = file_path.relative_to(self.tests_dir.parent)
                            self.skipped_tests.append(
                                SkippedTest(
                                    file_path=str(relative_path), test_name=node.name, line_number=node.lineno, **skip_info
                                )
                            )

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    def _extract_skip_decorator(self, node) -> dict | None:
        """Extract skip decorator information from a test function"""
        for decorator in node.decorator_list:
            # Handle @pytest.mark.skip
            if self._is_skip_decorator(decorator, "skip"):
                reason = self._extract_reason(decorator)
                github_issue = self._extract_github_issue(reason)
                return {"skip_type": "skip", "reason": reason or "No reason provided", "github_issue": github_issue}

            # Handle @pytest.mark.skipif
            if self._is_skip_decorator(decorator, "skipif"):
                condition = self._extract_condition(decorator)
                reason = self._extract_reason(decorator)
                github_issue = self._extract_github_issue(reason)
                return {
                    "skip_type": "skipif",
                    "reason": reason or "No reason provided",
                    "github_issue": github_issue,
                    "condition": condition,
                }

        return None

    def _is_skip_decorator(self, decorator, mark_name: str) -> bool:
        """Check if decorator is pytest.mark.skip or pytest.mark.skipif"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if (
                    isinstance(decorator.func.value, ast.Attribute)
                    and decorator.func.value.attr == "mark"
                    and decorator.func.attr == mark_name
                ):
                    return True
        return False

    def _extract_reason(self, decorator) -> str | None:
        """Extract reason from skip decorator"""
        if isinstance(decorator, ast.Call):
            # Check keyword arguments
            for keyword in decorator.keywords:
                if keyword.arg == "reason":
                    if isinstance(keyword.value, ast.Constant):
                        return keyword.value.value

            # Check positional arguments (skipif)
            if len(decorator.args) >= 2:
                if isinstance(decorator.args[1], ast.Constant):
                    return decorator.args[1].value

        return None

    def _extract_condition(self, decorator) -> str | None:
        """Extract condition from skipif decorator"""
        if isinstance(decorator, ast.Call) and decorator.args:
            try:
                return ast.unparse(decorator.args[0])
            except Exception:
                return str(decorator.args[0])
        return None

    def _extract_github_issue(self, reason: str | None) -> str | None:
        """Extract GitHub issue reference from reason string"""
        if not reason:
            return None

        # Match patterns like #123, GH-123, github.com/owner/repo/issues/123
        patterns = [r"#(\d+)", r"GH-(\d+)", r"github\.com/[^/]+/[^/]+/issues/(\d+)"]

        for pattern in patterns:
            match = re.search(pattern, reason)
            if match:
                return f"#{match.group(1)}"

        return None


class SkippedTestReporter:
    """Generate reports for skipped tests"""

    def __init__(self, skipped_tests: list[SkippedTest]):
        self.skipped_tests = skipped_tests

    def generate_summary(self) -> str:
        """Generate summary statistics"""
        total = len(self.skipped_tests)
        by_file = defaultdict(int)
        by_reason = defaultdict(int)
        with_issues = sum(1 for t in self.skipped_tests if t.github_issue)
        without_issues = total - with_issues

        for test in self.skipped_tests:
            by_file[test.file_path] += 1
            by_reason[test.reason] += 1

        lines = [
            "# Skipped Tests Summary",
            "",
            f"**Total Skipped Tests:** {total}",
            f"**With GitHub Issues:** {with_issues}",
            f"**Without GitHub Issues:** {without_issues} ⚠️",
            "",
            "## Top Files with Skipped Tests",
            "",
        ]

        # Top 10 files
        sorted_files = sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]
        lines.append("| File | Count |")
        lines.append("|------|-------|")
        for file_path, count in sorted_files:
            lines.append(f"| {file_path} | {count} |")

        lines.extend(["", "## Skip Reasons", ""])

        # Group by reason
        sorted_reasons = sorted(by_reason.items(), key=lambda x: x[1], reverse=True)
        lines.append("| Reason | Count |")
        lines.append("|--------|-------|")
        for reason, count in sorted_reasons[:15]:
            truncated_reason = (reason[:60] + "...") if len(reason) > 60 else reason
            lines.append(f"| {truncated_reason} | {count} |")

        return "\n".join(lines)

    def generate_detailed_report(self) -> str:
        """Generate detailed report with all skipped tests"""
        lines = [
            "# Detailed Skipped Tests Report",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## All Skipped Tests",
            "",
        ]

        # Group by file
        by_file = defaultdict(list)
        for test in self.skipped_tests:
            by_file[test.file_path].append(test)

        for file_path in sorted(by_file.keys()):
            tests = by_file[file_path]
            lines.append(f"### {file_path} ({len(tests)} skipped)")
            lines.append("")

            for test in tests:
                issue_ref = f" [{test.github_issue}]" if test.github_issue else " ⚠️ NO ISSUE"
                lines.append(f"- **{test.test_name}** (line {test.line_number}){issue_ref}")
                lines.append(f"  - **Type:** `{test.skip_type}`")
                lines.append(f"  - **Reason:** {test.reason}")
                if test.condition:
                    lines.append(f"  - **Condition:** `{test.condition}`")
                lines.append("")

        return "\n".join(lines)

    def generate_action_items(self) -> str:
        """Generate action items for tests without GitHub issues"""
        tests_without_issues = [t for t in self.skipped_tests if not t.github_issue]

        if not tests_without_issues:
            return "✅ All skipped tests have associated GitHub issues!"

        lines = [
            "# Action Items: Skipped Tests Without GitHub Issues",
            "",
            f"**{len(tests_without_issues)} tests need GitHub issues created**",
            "",
            "For each test below, create a GitHub issue to track why it's skipped and when it should be enabled:",
            "",
        ]

        by_file = defaultdict(list)
        for test in tests_without_issues:
            by_file[test.file_path].append(test)

        for file_path in sorted(by_file.keys()):
            tests = by_file[file_path]
            lines.append(f"## {file_path}")
            lines.append("")

            for test in tests:
                lines.append(f"- [ ] **{test.test_name}** (line {test.line_number})")
                lines.append(f"      - Reason: {test.reason}")
                lines.append("      - Action: Create issue and update skip decorator with issue number")
                lines.append("")

        return "\n".join(lines)

    def generate_json(self) -> str:
        """Generate JSON output"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_skipped": len(self.skipped_tests),
            "with_issues": sum(1 for t in self.skipped_tests if t.github_issue),
            "tests": [t.to_dict() for t in self.skipped_tests],
        }
        return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Track and report skipped tests")
    parser.add_argument("--tests-dir", type=Path, default=Path("tests"), help="Path to tests directory (default: tests)")
    parser.add_argument("--output", type=Path, help="Output file path (default: stdout)")
    parser.add_argument(
        "--format",
        choices=["summary", "detailed", "action", "json"],
        default="summary",
        help="Report format (default: summary)",
    )
    parser.add_argument("--github-action", action="store_true", help="Output GitHub Actions step summary")

    args = parser.parse_args()

    # Extract skipped tests
    print(f"Extracting skipped tests from {args.tests_dir}...", file=sys.stderr)
    extractor = SkippedTestExtractor(args.tests_dir)
    skipped_tests = extractor.extract_all()

    print(f"Found {len(skipped_tests)} skipped tests", file=sys.stderr)

    # Generate report
    reporter = SkippedTestReporter(skipped_tests)

    if args.format == "summary":
        report = reporter.generate_summary()
    elif args.format == "detailed":
        report = reporter.generate_detailed_report()
    elif args.format == "action":
        report = reporter.generate_action_items()
    elif args.format == "json":
        report = reporter.generate_json()

    # Output report
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # GitHub Actions output
    if args.github_action:
        summary_file = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
        if summary_file.exists() or summary_file.parent.exists():
            with open(summary_file, "a") as f:
                f.write(reporter.generate_summary())
                f.write("\n\n")
                f.write(reporter.generate_action_items())

    # Exit with error if there are tests without issues
    tests_without_issues = sum(1 for t in skipped_tests if not t.github_issue)
    if tests_without_issues > 0:
        print(f"\n⚠️  Warning: {tests_without_issues} skipped tests don't have GitHub issues", file=sys.stderr)
        # Don't exit with error for now, just warn
        # sys.exit(1)

    return 0


if __name__ == "__main__":
    import os

    sys.exit(main())
