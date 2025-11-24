"""
Meta-test to enforce strict xfail usage in test suite.

This test validates that all @pytest.mark.xfail decorators use strict=True
to prevent regressions where expected failures silently start passing.

RATIONALE (OpenAI Codex Finding #3):
- Non-strict xfail tests (strict=False or omitted) fail silently when fixed
- This can hide improvements or mask test logic errors
- strict=True ensures we're notified when expected failures start passing
- 3 tests initially violated this rule (finding #3)

VALIDATION CRITERIA:
- All @pytest.mark.xfail decorators must include strict=True
- Files can opt-out via XFAIL_STRICT_EXEMPT_FILES (with justification)
- Provides clear error messages with file paths and line numbers

References:
- pytest docs: https://docs.pytest.org/en/stable/how-to/skipping.html#strict-parameter
- OpenAI Codex validation report (2025-11-15)
- tests/test_feature_flags.py:197 (fixed example)
- tests/integration/test_gdpr_endpoints.py:360 (fixed example)
- tests/integration/execution/test_docker_sandbox.py:611 (fixed example)
"""

import ast
import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta

# Test files intentionally exempt from strict xfail requirement
# Each entry must have a documented reason
XFAIL_STRICT_EXEMPT_FILES: set[str] = {
    # Add exempt files here with justification comments
    # Example: "tests/examples/demo.py",  # Educational demo, strict not required
    "tests/regression/test_fastapi_auth_override_sanity.py",  # Non-deterministic xdist pollution test (strict=False required)
}


@pytest.mark.meta
@pytest.mark.meta
@pytest.mark.xdist_group(name="xfail_strict_enforcement")
class TestXfailStrictEnforcement:
    """Enforce strict=True on all xfail markers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _get_all_test_files(self) -> list[Path]:
        """Get all Python test files in the tests/ directory."""
        tests_dir = Path(__file__).parent.parent  # tests/
        test_files = list(tests_dir.rglob("test_*.py"))
        test_files.extend(tests_dir.rglob("*_test.py"))
        return sorted(set(test_files))

    def _find_non_strict_xfails(self, file_path: Path) -> list[tuple[int, str]]:
        """
        Find @pytest.mark.xfail decorators without strict=True.

        Returns:
            List of (line_number, decorator_text) tuples for violations
        """
        violations = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # Skip files with syntax errors (pytest won't collect them anyway)
            return violations

        # Walk AST to find all function/class decorators
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    # Check if this is a pytest.mark.xfail decorator
                    is_xfail = False
                    has_strict = False

                    # Handle @pytest.mark.xfail or @pytest.mark.xfail(...)
                    if isinstance(decorator, ast.Attribute):
                        # @pytest.mark.xfail (no arguments - defaults to strict=False)
                        if (
                            isinstance(decorator.value, ast.Attribute)
                            and decorator.value.attr == "mark"
                            and decorator.attr == "xfail"
                        ):
                            is_xfail = True
                            has_strict = False

                    elif isinstance(decorator, ast.Call):
                        # @pytest.mark.xfail(...)
                        if isinstance(decorator.func, ast.Attribute):
                            if (
                                isinstance(decorator.func.value, ast.Attribute)
                                and decorator.func.value.attr == "mark"
                                and decorator.func.attr == "xfail"
                            ):
                                is_xfail = True

                                # Check for strict=True in keyword arguments
                                for keyword in decorator.keywords:
                                    if keyword.arg == "strict":
                                        if isinstance(keyword.value, ast.Constant) or hasattr(keyword.value, "value"):
                                            has_strict = keyword.value.value is True

                    # Report violation if xfail without strict=True
                    if is_xfail and not has_strict:
                        line_num = decorator.lineno
                        # Get source line for context
                        source_line = content.splitlines()[line_num - 1].strip()
                        violations.append((line_num, source_line))

        return violations

    def test_all_xfail_markers_use_strict_true(self):
        """
        RED PHASE TEST: Validates all xfail markers use strict=True.

        This test will FAIL initially if any non-strict xfails exist,
        proving it works. After fixing all violations, it will pass.

        WHY strict=True MATTERS:
        - Without strict=True, xfail tests that start passing are silently ignored
        - This can hide bug fixes or improvements
        - strict=True makes pytest fail when an expected failure passes
        - Forces developers to remove xfail when test is fixed

        EXPECTED BEHAVIOR:
        - @pytest.mark.xfail(strict=True, reason="...")  ✅ PASS
        - @pytest.mark.xfail(reason="...")               ❌ FAIL (missing strict)
        - @pytest.mark.xfail()                           ❌ FAIL (missing strict)
        """
        test_files = self._get_all_test_files()
        all_violations = {}

        for test_file in test_files:
            # Skip exempt files
            relative_path = str(test_file.relative_to(Path.cwd()))
            if relative_path in XFAIL_STRICT_EXEMPT_FILES:
                continue

            # Skip conftest.py files (not test files)
            if test_file.name == "conftest.py":
                continue

            # Find violations in this file
            violations = self._find_non_strict_xfails(test_file)

            if violations:
                all_violations[relative_path] = violations

        # Build error message if violations found
        if all_violations:
            error_lines = [
                f"Found {len(all_violations)} test files with non-strict xfail markers.",
                "",
                "WHY THIS MATTERS:",
                "- Non-strict xfail tests fail silently when they start passing",
                "- This can hide bug fixes or test improvements",
                "- strict=True ensures you're notified when expected failures pass",
                "",
                "VIOLATIONS:",
                "",
            ]

            for file_path, violations in sorted(all_violations.items()):
                error_lines.append(f"File: {file_path}")
                for line_num, source_line in violations:
                    error_lines.append(f"  Line {line_num}: {source_line}")
                error_lines.append("")

            error_lines.extend(
                [
                    "TO FIX:",
                    "Add strict=True to each xfail marker:",
                    "",
                    "Before:",
                    "  @pytest.mark.xfail(reason='Not implemented')",
                    "",
                    "After:",
                    "  @pytest.mark.xfail(strict=True, reason='Not implemented')",
                    "",
                    "Or if xfail is no longer needed, remove the marker entirely.",
                ]
            )

            raise AssertionError("\n".join(error_lines))

    def test_xfail_strict_enforcement_statistics(self):
        """
        Reports statistics on xfail usage (informational, always passes).

        Provides visibility into:
        - Total xfail markers in codebase
        - How many use strict=True
        - Coverage percentage
        """
        test_files = self._get_all_test_files()
        total_xfails = 0
        strict_xfails = 0
        non_strict_xfails = 0

        for test_file in test_files:
            if test_file.name == "conftest.py":
                continue

            violations = self._find_non_strict_xfails(test_file)
            non_strict_xfails += len(violations)

            # Count total xfails (strict + non-strict)
            # We need to count strict ones separately
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        for decorator in node.decorator_list:
                            # Check for xfail markers
                            is_xfail = False

                            if isinstance(decorator, ast.Attribute):
                                if (
                                    isinstance(decorator.value, ast.Attribute)
                                    and decorator.value.attr == "mark"
                                    and decorator.attr == "xfail"
                                ):
                                    is_xfail = True

                            elif isinstance(decorator, ast.Call):
                                if isinstance(decorator.func, ast.Attribute):
                                    if (
                                        isinstance(decorator.func.value, ast.Attribute)
                                        and decorator.func.value.attr == "mark"
                                        and decorator.func.attr == "xfail"
                                    ):
                                        is_xfail = True

                            if is_xfail:
                                total_xfails += 1

            except SyntaxError:
                continue

        strict_xfails = total_xfails - non_strict_xfails
        coverage = (strict_xfails / total_xfails * 100) if total_xfails > 0 else 100.0

        print("\n" + "=" * 60)
        print("Xfail Strict Enforcement Statistics")
        print("=" * 60)
        print(f"Total xfail markers: {total_xfails}")
        print(f"Strict xfails (strict=True): {strict_xfails}")
        print(f"Non-strict xfails: {non_strict_xfails}")
        print(f"Strict coverage: {coverage:.1f}%")
        print("=" * 60 + "\n")

        # This test always passes - it's informational only
        assert True
