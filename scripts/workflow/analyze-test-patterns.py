#!/usr/bin/env python3
"""
Test Pattern Analyzer - Extract common patterns from test suite

This script:
1. Scans test files for common patterns
2. Identifies fixtures, mocks, and test structures
3. Extracts frequently used patterns
4. Generates pattern documentation
5. Suggests improvements

Usage:
    python scripts/workflow/analyze-test-patterns.py              # Analyze all tests
    python scripts/workflow/analyze-test-patterns.py --dir tests/unit  # Specific directory
    python scripts/workflow/analyze-test-patterns.py --update     # Update testing-patterns.md

Author: Claude Code (Workflow Optimization)
Created: 2025-10-20
"""

import argparse
import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class TestPattern:
    """Represents a test pattern"""

    name: str
    description: str
    examples: List[str] = field(default_factory=list)
    frequency: int = 0
    files: Set[str] = field(default_factory=set)


class TestPatternAnalyzer:
    """Analyzes test files for common patterns"""

    def __init__(self, test_dir: str = "tests"):
        self.test_dir = Path(test_dir)
        self.patterns: Dict[str, TestPattern] = {}
        self.fixture_usage: Counter = Counter()
        self.marker_usage: Counter = Counter()
        self.mock_patterns: Counter = Counter()
        self.test_count = 0

    def analyze(self):
        """Analyze all test files"""
        print(f"Analyzing test files in {self.test_dir}...")

        test_files = list(self.test_dir.rglob("test_*.py"))
        print(f"Found {len(test_files)} test files")

        for test_file in test_files:
            self._analyze_file(test_file)

        print(f"Analyzed {self.test_count} tests")

    def _analyze_file(self, file_path: Path):
        """Analyze a single test file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)

            # Analyze AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("test_"):
                        self.test_count += 1
                        self._analyze_test_function(node, file_path, content)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _analyze_test_function(self, func_node: ast.FunctionDef, file_path: Path, content: str):
        """Analyze a test function"""
        # Check for markers
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Attribute):
                    # pytest.mark.asyncio
                    marker = f"{decorator.value.attr}.{decorator.attr}"
                    self.marker_usage[marker] += 1
                elif isinstance(decorator.value, ast.Name) and decorator.value.id == "pytest":
                    # pytest.mark.unit
                    marker = decorator.attr
                    self.marker_usage[marker] += 1

        # Check for fixtures in parameters
        for arg in func_node.args.args:
            if arg.arg not in ["self", "cls"]:
                self.fixture_usage[arg.arg] += 1

        # Check for mock patterns in function body
        func_source = ast.get_source_segment(content, func_node)
        if func_source:
            self._extract_mock_patterns(func_source)

    def _extract_mock_patterns(self, source: str):
        """Extract mock patterns from source code"""
        # Common mock patterns
        patterns = [
            (r'@patch\(["\'](.+?)["\']\)', "decorator_patch"),
            (r"AsyncMock\(\)", "async_mock"),
            (r"MagicMock\(\)", "magic_mock"),
            (r"Mock\(\)", "basic_mock"),
            (r"mock\.return_value\s*=", "return_value"),
            (r"mock\.side_effect\s*=", "side_effect"),
            (r"with patch\(", "context_patch"),
        ]

        for pattern, name in patterns:
            count = len(re.findall(pattern, source))
            if count > 0:
                self.mock_patterns[name] += count

    def generate_report(self) -> str:
        """Generate analysis report"""
        report = []
        report.append("# Test Pattern Analysis Report\n")
        report.append(f"**Total Tests Analyzed**: {self.test_count}\n")
        report.append("---\n")

        # Marker usage
        report.append("## 🏷️ Test Markers Usage\n")
        for marker, count in self.marker_usage.most_common(15):
            percentage = (count / self.test_count) * 100
            report.append(f"- `@pytest.mark.{marker}`: {count} tests ({percentage:.1f}%)")
        report.append("\n---\n")

        # Fixture usage
        report.append("## 🔧 Most Common Fixtures\n")
        for fixture, count in self.fixture_usage.most_common(15):
            percentage = (count / self.test_count) * 100
            report.append(f"- `{fixture}`: used {count} times ({percentage:.1f}%)")
        report.append("\n---\n")

        # Mock patterns
        report.append("## 🎭 Mock Pattern Usage\n")
        total_mocks = sum(self.mock_patterns.values())
        for pattern, count in self.mock_patterns.most_common():
            percentage = (count / total_mocks) * 100 if total_mocks > 0 else 0
            report.append(f"- `{pattern}`: {count} uses ({percentage:.1f}%)")
        report.append("\n---\n")

        # Insights
        report.append("## 💡 Insights\n")

        asyncio_tests = self.marker_usage.get("asyncio", 0)
        async_percentage = (asyncio_tests / self.test_count) * 100 if self.test_count > 0 else 0
        report.append(
            f"- **Async tests**: {asyncio_tests} ({async_percentage:.1f}%) - {'High' if async_percentage > 50 else 'Moderate'} async usage"
        )

        unit_tests = self.marker_usage.get("unit", 0)
        integration_tests = self.marker_usage.get("integration", 0)
        report.append(f"- **Test distribution**: {unit_tests} unit, {integration_tests} integration")

        # Most reused fixture
        if self.fixture_usage:
            top_fixture = self.fixture_usage.most_common(1)[0]
            report.append(f"- **Most reused fixture**: `{top_fixture[0]}` ({top_fixture[1]} uses)")

        # Mock usage
        if self.mock_patterns:
            total_mock_usage = sum(self.mock_patterns.values())
            mock_per_test = total_mock_usage / self.test_count if self.test_count > 0 else 0
            report.append(f"- **Mock usage**: {total_mock_usage} total ({mock_per_test:.1f} per test average)")

        report.append("\n---\n")

        # Recommendations
        report.append("## 📋 Recommendations\n")

        # Check for good patterns
        if async_percentage > 30:
            report.append("- ✅ Good async test coverage")

        if unit_tests > integration_tests * 3:
            report.append("- ✅ Healthy unit to integration test ratio")

        # Check for potential improvements
        if "parametrize" not in self.marker_usage or self.marker_usage["parametrize"] < self.test_count * 0.1:
            report.append("- 💡 Consider using `@pytest.mark.parametrize` for testing multiple scenarios")

        if "property" in self.marker_usage:
            property_tests = self.marker_usage["property"]
            report.append(f"- ✅ Property-based testing in use ({property_tests} tests)")
        else:
            report.append("- 💡 Consider adding property-based tests with Hypothesis")

        report.append("\n---\n")
        report.append("**Auto-generated by**: `scripts/workflow/analyze-test-patterns.py`\n")

        return "\n".join(report)

    def identify_new_patterns(self) -> List[str]:
        """Identify patterns not yet documented"""
        # This would compare against existing testing-patterns.md
        # For now, return commonly used patterns
        new_patterns = []

        # Check for high-usage patterns
        for fixture, count in self.fixture_usage.most_common(5):
            if count > 10:  # Used more than 10 times
                new_patterns.append(f"Fixture pattern: {fixture}")

        return new_patterns


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Analyze test patterns")
    parser.add_argument("--dir", default="tests", help="Test directory (default: tests)")
    parser.add_argument("--update", action="store_true", help="Update testing-patterns.md")
    parser.add_argument("--output", help="Output file for report (default: stdout)")

    args = parser.parse_args()

    # Create analyzer and run analysis
    analyzer = TestPatternAnalyzer(test_dir=args.dir)
    analyzer.analyze()

    # Generate report
    report = analyzer.generate_report()

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        print(f"\n✅ Report saved to: {args.output}")
    else:
        print("\n" + report)

    # Identify new patterns
    print("\n" + "=" * 60)
    new_patterns = analyzer.identify_new_patterns()
    if new_patterns:
        print("New patterns identified:")
        for pattern in new_patterns:
            print(f"  - {pattern}")
    else:
        print("No new patterns identified")

    # Update testing-patterns.md if requested
    if args.update:
        print("\n📝 Updating testing-patterns.md...")
        # TODO: Implement pattern documentation update
        print("⚠️  Pattern update not yet implemented - manual update required")


if __name__ == "__main__":
    main()
