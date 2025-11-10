#!/usr/bin/env python3
"""
Scan test suite for resource-intensive patterns.

Usage:
    python scripts/scan_test_resource_usage.py

Detects:
1. bcrypt.gensalt() without rounds parameter
2. range(N) where N > 100 (potential memory issue)
3. asyncio.sleep(N) where N > 1.0 (time waste)
4. subprocess.run in unit tests
5. Missing xdist_group on tests with AsyncMock
6. Missing teardown_method with gc.collect()

Returns:
- Exit 0: No issues found
- Exit 1: Issues found (lists violations)
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class ResourcePatternDetector:
    """Detect resource-intensive patterns in test files"""

    def __init__(self, tests_dir: Path):
        self.tests_dir = tests_dir
        self.violations: List[Tuple[str, int, str, str]] = []  # (file, line, severity, message)

    def scan_all_tests(self) -> List[Tuple[str, int, str, str]]:
        """Scan all test files for resource-intensive patterns"""
        for test_file in self.tests_dir.rglob("test_*.py"):
            # Skip meta tests (they scan other tests)
            if "meta" in test_file.parts:
                continue

            try:
                self._scan_file(test_file)
            except Exception as e:
                print(f"Warning: Could not scan {test_file}: {e}", file=sys.stderr)

        return self.violations

    def _scan_file(self, file_path: Path):
        """Scan single file for patterns"""
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        self._check_bcrypt_patterns(tree, file_path)
        self._check_large_ranges(tree, file_path)
        self._check_long_sleeps(tree, file_path)
        self._check_subprocess_usage(tree, file_path, content)
        self._check_memory_safety_patterns(tree, file_path, content)

    def _check_bcrypt_patterns(self, tree: ast.AST, file_path: Path):
        """Detect bcrypt.gensalt() without rounds parameter"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for bcrypt.gensalt() or gensalt()
                if hasattr(node.func, "attr") and node.func.attr == "gensalt":
                    has_rounds = any(kw.arg == "rounds" for kw in node.keywords)
                    if not has_rounds:
                        self.violations.append(
                            (
                                str(file_path.relative_to(self.tests_dir.parent)),
                                node.lineno,
                                "PERFORMANCE",
                                "bcrypt.gensalt() missing rounds parameter - use rounds=4 for tests (8x faster)",
                            )
                        )

    def _check_large_ranges(self, tree: ast.AST, file_path: Path):
        """Detect range(N) where N > 100 (potential memory issue)"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "range":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        n = node.args[0].value
                        if isinstance(n, int) and n > 100:
                            self.violations.append(
                                (
                                    str(file_path.relative_to(self.tests_dir.parent)),
                                    node.lineno,
                                    "MEMORY",
                                    f"range({n}) may cause memory issues with mocks - consider: reduce N, use dicts, or add skip marker",
                                )
                            )

    def _check_long_sleeps(self, tree: ast.AST, file_path: Path):
        """Detect asyncio.sleep(N) where N >= 1.0"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for asyncio.sleep() or time.sleep()
                is_async_sleep = (
                    hasattr(node.func, "attr")
                    and node.func.attr == "sleep"
                    and hasattr(node.func, "value")
                    and hasattr(node.func.value, "id")
                    and node.func.value.id == "asyncio"
                )

                if is_async_sleep:
                    if node.args and isinstance(node.args[0], ast.Constant):
                        sleep_time = node.args[0].value
                        if isinstance(sleep_time, (int, float)) and sleep_time >= 1.0:
                            self.violations.append(
                                (
                                    str(file_path.relative_to(self.tests_dir.parent)),
                                    node.lineno,
                                    "PERFORMANCE",
                                    f"asyncio.sleep({sleep_time}) too long - use <0.5s with proportional timeout ratios",
                                )
                            )

    def _check_subprocess_usage(self, tree: ast.AST, file_path: Path, content: str):
        """Detect subprocess usage in unit tests"""
        has_unit_marker = "@pytest.mark.unit" in content or "pytest.mark.unit" in content

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == "subprocess" for alias in node.names):
                    if has_unit_marker and "meta" not in str(file_path):
                        # subprocess in unit tests is suspicious (except meta-tests)
                        self.violations.append(
                            (
                                str(file_path.relative_to(self.tests_dir.parent)),
                                node.lineno,
                                "PERFORMANCE",
                                "subprocess in unit test - consider mocking or moving to @pytest.mark.integration",
                            )
                        )

    def _check_memory_safety_patterns(self, tree: ast.AST, file_path: Path, content: str):
        """Detect missing memory safety patterns for AsyncMock tests"""
        has_asyncmock = "AsyncMock" in content
        has_magicmock = "MagicMock" in content

        if has_asyncmock or has_magicmock:
            # Check for xdist_group marker
            has_xdist_group = "@pytest.mark.xdist_group" in content

            # Check for teardown_method with gc.collect()
            has_teardown = "def teardown_method" in content
            has_gc_collect = "gc.collect()" in content

            if not has_xdist_group:
                self.violations.append(
                    (
                        str(file_path.relative_to(self.tests_dir.parent)),
                        1,
                        "MEMORY",
                        f"Uses {'AsyncMock' if has_asyncmock else 'MagicMock'} but missing @pytest.mark.xdist_group - prevents parallel isolation",
                    )
                )

            if not (has_teardown and has_gc_collect):
                self.violations.append(
                    (
                        str(file_path.relative_to(self.tests_dir.parent)),
                        1,
                        "MEMORY",
                        f"Uses {'AsyncMock' if has_asyncmock else 'MagicMock'} but missing teardown_method() with gc.collect()",
                    )
                )


def main():
    """Main entry point"""
    tests_dir = Path(__file__).parent.parent / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found: {tests_dir}", file=sys.stderr)
        sys.exit(1)

    print("Scanning test suite for resource-intensive patterns...")
    print(f"Tests directory: {tests_dir}\n")

    detector = ResourcePatternDetector(tests_dir)
    violations = detector.scan_all_tests()

    if violations:
        # Group by severity
        by_severity = {"MEMORY": [], "PERFORMANCE": [], "OTHER": []}
        for file_path, line_num, severity, message in violations:
            by_severity.get(severity, by_severity["OTHER"]).append((file_path, line_num, message))

        print(f"❌ Found {len(violations)} resource-intensive patterns:\n")

        for severity in ["MEMORY", "PERFORMANCE", "OTHER"]:
            issues = by_severity[severity]
            if issues:
                print(f"\n{'=' * 70}")
                print(f"{severity} ISSUES ({len(issues)} found)")
                print(f"{'=' * 70}\n")

                for file_path, line_num, message in issues:
                    print(f"  📁 {file_path}:{line_num}")
                    print(f"     {message}\n")

        print(f"\n{'=' * 70}")
        print(f"Total: {len(violations)} issues found")
        print(f"{'=' * 70}")
        print("\nRecommended actions:")
        print("1. Review each violation")
        print("2. Apply fixes from tests/RESOURCE_INTENSIVE_TEST_PATTERNS.md")
        print("3. Re-run this scanner to verify fixes")
        print("4. Add to pre-commit hooks to prevent future violations")

        sys.exit(1)
    else:
        print("✅ No resource-intensive patterns detected")
        print("\nTest suite follows best practices for:")
        print("  - Memory safety (xdist_group, gc.collect)")
        print("  - Performance (optimized bcrypt, short sleeps)")
        print("  - Resource management (lightweight mocks)")
        sys.exit(0)


if __name__ == "__main__":
    main()
