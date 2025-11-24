"""Test subprocess safety enforcement in test files.

This module validates that all subprocess.run() calls in test files include
timeout parameters to prevent test hangs on CI runners.

Related: OpenAI Codex Finding #6 - Subprocess test safeguards
"""

import ast
import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="meta_subprocess_safety")
class TestSubprocessSafety:
    """Validate subprocess calls in tests have appropriate safeguards."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def test_files(self) -> list[Path]:
        """Get all Python test files in the tests/ directory."""
        tests_dir = Path(__file__).parent.parent
        test_files = list(tests_dir.rglob("test_*.py"))

        # Exclude this file itself
        test_files = [f for f in test_files if f.name != "test_subprocess_safety.py"]

        return test_files

    def _find_subprocess_calls(self, file_path: Path) -> list[tuple[int, str, dict]]:
        """Parse file and find all subprocess.run() calls.

        Returns:
            List of tuples: (line_number, function_name, keyword_args_dict)
        """
        with open(file_path) as f:
            try:
                tree = ast.parse(f.read(), filename=str(file_path))
            except SyntaxError:
                # Skip files with syntax errors
                return []

        calls = []

        class SubprocessVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check if this is a subprocess.run() call
                is_subprocess_run = False

                # Handle subprocess.run()
                if isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr == "run"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "subprocess"
                    ):
                        is_subprocess_run = True

                if is_subprocess_run:
                    # Extract keyword arguments
                    kwargs = {}
                    for keyword in node.keywords:
                        if keyword.arg:  # Skip **kwargs
                            kwargs[keyword.arg] = keyword.value

                    calls.append((node.lineno, "subprocess.run", kwargs))

                self.generic_visit(node)

        visitor = SubprocessVisitor()
        visitor.visit(tree)

        return calls

    def test_subprocess_calls_have_timeout(self, test_files):
        """Verify all subprocess.run() calls include timeout parameter.

        Long-running subprocess calls without timeout can hang test suites,
        especially on CI runners. All subprocess calls should have explicit
        timeout parameter.
        """
        violations = []

        for test_file in test_files:
            calls = self._find_subprocess_calls(test_file)

            for line_num, func_name, kwargs in calls:
                # Check if timeout parameter is present
                if "timeout" not in kwargs:
                    relative_path = test_file.relative_to(Path(__file__).parent.parent)
                    violations.append(f"{relative_path}:{line_num} - {func_name}() missing timeout parameter")

        assert not violations, (
            f"Found {len(violations)} subprocess.run() call(s) without timeout parameter:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\n"
            "All subprocess calls must include timeout parameter to prevent hangs.\n"
            "Example: subprocess.run([...], timeout=60)\n"
            "Recommended: Use tests/helpers/subprocess_helpers.py::run_cli_tool() wrapper."
        )

    def test_subprocess_timeout_values_are_reasonable(self, test_files):
        """Verify subprocess timeout values are >= 30 seconds.

        Timeouts that are too short can cause flaky tests on slow CI runners.
        Minimum recommended timeout is 30 seconds for CLI tools like kubectl,
        helm, kustomize.
        """
        MINIMUM_TIMEOUT = 30  # seconds

        violations = []

        for test_file in test_files:
            calls = self._find_subprocess_calls(test_file)

            for line_num, func_name, kwargs in calls:
                if "timeout" in kwargs:
                    timeout_node = kwargs["timeout"]

                    # Extract timeout value if it's a simple constant
                    timeout_value = None
                    if isinstance(timeout_node, ast.Constant):
                        timeout_value = timeout_node.value
                    # Note: ast.Num removed in Python 3.8+, replaced by ast.Constant

                    if timeout_value is not None and timeout_value < MINIMUM_TIMEOUT:
                        relative_path = test_file.relative_to(Path(__file__).parent.parent)
                        violations.append(
                            f"{relative_path}:{line_num} - "
                            f"{func_name}() timeout={timeout_value}s is too short "
                            f"(minimum: {MINIMUM_TIMEOUT}s)"
                        )

        assert not violations, (
            f"Found {len(violations)} subprocess.run() call(s) with timeout < {MINIMUM_TIMEOUT}s:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\n"
            f"Subprocess timeouts should be >= {MINIMUM_TIMEOUT}s to prevent flaky tests on slow CI runners."
        )

    def test_subprocess_helper_function_exists(self):
        """Verify subprocess helper function exists for consistent usage."""
        helper_path = Path(__file__).parent.parent / "helpers" / "subprocess_helpers.py"

        assert helper_path.exists(), (
            "Subprocess helper module not found at tests/helpers/subprocess_helpers.py. "
            "Create this module to provide consistent subprocess.run() wrapper with "
            "timeout, check, and error handling defaults."
        )

    def test_subprocess_helper_has_run_cli_tool_function(self):
        """Verify subprocess helper exports run_cli_tool() function."""
        helper_path = Path(__file__).parent.parent / "helpers" / "subprocess_helpers.py"

        if not helper_path.exists():
            pytest.skip("Subprocess helper module doesn't exist yet")

        with open(helper_path) as f:
            content = f.read()

        # Parse and find run_cli_tool function
        tree = ast.parse(content, filename=str(helper_path))

        function_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_names.append(node.name)

        assert "run_cli_tool" in function_names, (
            "tests/helpers/subprocess_helpers.py must export run_cli_tool() function. "
            "This function should provide consistent subprocess.run() wrapper with "
            "timeout and error handling defaults."
        )

    def test_subprocess_helper_run_cli_tool_has_timeout_default(self):
        """Verify run_cli_tool() has reasonable timeout default."""
        helper_path = Path(__file__).parent.parent / "helpers" / "subprocess_helpers.py"

        if not helper_path.exists():
            pytest.skip("Subprocess helper module doesn't exist yet")

        with open(helper_path) as f:
            content = f.read()

        # Parse and find run_cli_tool function
        tree = ast.parse(content, filename=str(helper_path))

        run_cli_tool_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run_cli_tool":
                run_cli_tool_node = node
                break

        assert run_cli_tool_node is not None, "run_cli_tool() function not found"

        # Check if timeout parameter has default value
        timeout_arg = None
        for arg in run_cli_tool_node.args.args:
            if arg.arg == "timeout":
                # Find corresponding default value
                arg_index = run_cli_tool_node.args.args.index(arg)
                defaults_start = len(run_cli_tool_node.args.args) - len(run_cli_tool_node.args.defaults)

                if arg_index >= defaults_start:
                    default_index = arg_index - defaults_start
                    timeout_arg = run_cli_tool_node.args.defaults[default_index]
                break

        assert timeout_arg is not None, (
            "run_cli_tool() must have timeout parameter with default value. " "Example: def run_cli_tool(..., timeout=60)"
        )

        # Extract default value
        if isinstance(timeout_arg, ast.Constant):
            timeout_default = timeout_arg.value
        else:
            timeout_default = None
        # Note: ast.Num removed in Python 3.8+, replaced by ast.Constant

        if timeout_default is not None:
            assert timeout_default >= 30, (
                f"run_cli_tool() timeout default ({timeout_default}s) should be >= 30s. "
                "CLI tools like kubectl, helm can be slow on CI runners."
            )
