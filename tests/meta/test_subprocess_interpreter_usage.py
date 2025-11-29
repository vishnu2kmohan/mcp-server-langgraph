"""
Meta-test: Prevent subprocess Python interpreter hardcoding regression.

This test ensures all test files use sys.executable instead of hardcoded 'python'
in subprocess calls. Hardcoded interpreters fail in multi-Python CI matrices
where subprocess.run(['python', ...]) resolves to /usr/bin/python3 instead of
the venv interpreter.

Background:
-----------
PR #121 CI failures on Python 3.11/3.13 caused by subprocess.run(['python', ...])
calls that bypassed the virtual environment interpreter.

Prevention:
-----------
This meta-test scans all test files for subprocess calls with hardcoded 'python'
and fails if any are found, providing clear guidance for fixes.

Correct usage:
```python
import sys
import subprocess

# ✅ Correct: Uses current interpreter
subprocess.run([sys.executable, 'script.py'])

# ❌ Wrong: Hardcoded interpreter
subprocess.run(['python', 'script.py'])
```
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.xdist_group(name="subprocess_interpreter_usage")
class TestSubprocessInterpreterUsage:
    """Prevent regression of subprocess(['python', ...]) anti-pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def tests_directory(self) -> Path:
        """Get the tests directory."""
        return Path(__file__).parent.parent

    def _is_code_line(self, line: str) -> bool:
        """Check if line is actual code (not comment, docstring marker, or string)."""
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            return False
        # Skip comment lines
        if stripped.startswith("#"):
            return False
        # Skip docstring markers
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return False
        # Skip lines that are part of docstrings (heuristic: high indentation + text)
        # Skip lines that look like documentation examples
        if "# ❌" in line or "# ✅" in line or "Fix by" in line or "Replace:" in line:
            return False
        return True

    def test_no_hardcoded_python_in_subprocess_run(self, tests_directory: Path) -> None:
        """
        Ensure no test files use hardcoded 'python' in subprocess.run() calls.

        GIVEN: All Python test files in the tests directory
        WHEN: Scanning for subprocess calls with hardcoded python interpreter
        THEN: No matches should be found (all should use sys.executable)
        """
        # Pattern for actual code using hardcoded python
        # Only matches if the line starts with code (not in a string/comment)
        hardcoded_pattern = re.compile(r"subprocess\.(run|Popen|call|check_call|check_output)\(\s*\[\s*['\"]python['\"]")

        violations: list[tuple[Path, int, str]] = []

        for py_file in tests_directory.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            lines = content.splitlines()
            in_docstring = False

            for line_num, line in enumerate(lines, start=1):
                # Track docstring state
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    # Toggle docstring state (opening or closing)
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_docstring = not in_docstring
                    continue

                if in_docstring:
                    continue

                # Skip comments
                if stripped.startswith("#"):
                    continue

                # Check for hardcoded pattern in actual code
                if hardcoded_pattern.search(line):
                    violations.append((py_file.relative_to(tests_directory), line_num, line.strip()))

        if violations:
            error_msg = [
                "Found hardcoded 'python' interpreter in subprocess calls:",
                "",
                "These will fail in multi-Python CI matrices (3.11, 3.12, 3.13).",
                "",
                "Violations found:",
            ]

            for file_path, line_num, line in violations:
                error_msg.append(f"  {file_path}:{line_num}: {line[:80]}")

            # Note: Example uses string concatenation to avoid matching our own pattern
            bad_example = "  subprocess" + ".run([" + "'python'" + ", script])"
            good_example = "  subprocess.run([sys.executable, script])"
            error_msg.extend(
                [
                    "",
                    "Fix by replacing with sys.executable:",
                    "",
                    "  # Add at top of file:",
                    "  import sys",
                    "",
                    "  # Replace:",
                    bad_example,
                    "",
                    "  # With:",
                    good_example,
                ]
            )

            pytest.fail("\n".join(error_msg))

    def test_sys_executable_usage_in_subprocess_calls(self, tests_directory: Path) -> None:
        """
        Verify tests that use subprocess actually import sys.

        GIVEN: Test files using subprocess with sys.executable
        WHEN: Checking for sys import
        THEN: sys module should be imported
        """
        # Pattern for sys.executable usage
        sys_executable_pattern = re.compile(r"sys\.executable")
        import_sys_pattern = re.compile(r"^import sys|^from sys import")

        files_missing_import: list[tuple[Path, int]] = []

        for py_file in tests_directory.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            lines = content.splitlines()
            has_sys_executable = any(sys_executable_pattern.search(line) for line in lines)

            if not has_sys_executable:
                continue

            has_sys_import = any(import_sys_pattern.match(line) for line in lines)

            if not has_sys_import:
                # Find line with sys.executable usage
                for line_num, line in enumerate(lines, start=1):
                    if sys_executable_pattern.search(line):
                        files_missing_import.append((py_file.relative_to(tests_directory), line_num))
                        break

        if files_missing_import:
            error_msg = [
                "Files using sys.executable without importing sys:",
                "",
            ]

            for file_path, line_num in files_missing_import:
                error_msg.append(f"  {file_path}:{line_num}")

            error_msg.extend(
                [
                    "",
                    "Fix by adding at the top of the file:",
                    "  import sys",
                ]
            )

            pytest.fail("\n".join(error_msg))
