"""
AsyncMock Validation for Test Quality Enforcement.

This module provides two types of validation for AsyncMock usage:

1. Configuration Validation: Ensures AsyncMock instances have explicit return_value,
   side_effect, or spec configuration to prevent authorization bypass bugs.

2. Usage Validation: Ensures async methods are mocked with AsyncMock (not regular Mock)
   to prevent hanging tests.

Background - Configuration:
Unconfigured AsyncMock returns truthy values, causing authorization checks to incorrectly
pass. This was the root cause of the SCIM security bug (commit abb04a6a).

Background - Usage:
Regular Mock (without AsyncMock) on async methods causes tests to hang because awaiting
a regular Mock returns the Mock object itself, not the expected value.

Version: 1.0.0
See: tests/ASYNC_MOCK_GUIDELINES.md for complete documentation
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Global cache for function signatures to avoid re-parsing files
_function_signature_cache: Dict[str, Optional[bool]] = {}


def is_async_function_in_source(module_path: str, function_name: str) -> Optional[bool]:
    """
    Check if a function is async by parsing its source file.

    Args:
        module_path: Dotted module path (e.g., "mcp_server_langgraph.monitoring.budget_monitor")
        function_name: Function name to check

    Returns:
        True if async, False if sync, None if not found or error
    """
    cache_key = f"{module_path}.{function_name}"
    if cache_key in _function_signature_cache:
        return _function_signature_cache[cache_key]

    # Convert module path to file path
    potential_paths = [
        Path(module_path.replace(".", "/") + ".py"),
        Path("src") / (module_path.replace(".", "/") + ".py"),
        Path("mcp_server_langgraph") / (module_path.replace("mcp_server_langgraph.", "").replace(".", "/") + ".py"),
    ]

    for file_path in potential_paths:
        if not file_path.exists():
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Search for the function definition
            for node in ast.walk(tree):
                # Check top-level functions
                if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
                    _function_signature_cache[cache_key] = True
                    return True
                elif isinstance(node, ast.FunctionDef) and node.name == function_name:
                    _function_signature_cache[cache_key] = False
                    return False

                # Check class methods
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.AsyncFunctionDef) and item.name == function_name:
                            _function_signature_cache[cache_key] = True
                            return True
                        elif isinstance(item, ast.FunctionDef) and item.name == function_name:
                            _function_signature_cache[cache_key] = False
                            return False
        except Exception:
            continue

    _function_signature_cache[cache_key] = None
    return None


class AsyncMockConfigChecker(ast.NodeVisitor):
    """AST visitor to detect unconfigured AsyncMock instances."""

    def __init__(self, filepath: str, source_lines: List[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.issues: List[Tuple[int, str]] = []
        self.async_mock_vars: Dict[str, int] = {}  # var_name -> line_number

    def has_noqa_comment(self, lineno: int) -> bool:
        """Check if a line has # noqa: async-mock-config comment."""
        if lineno <= 0 or lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]
        return "# noqa: async-mock-config" in line or "#noqa: async-mock-config" in line or "# noqa" in line

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment nodes to detect AsyncMock() creation."""
        if isinstance(node.value, ast.Call):
            if self._is_async_mock_call(node.value):
                is_configured_in_constructor = self._has_config_kwargs(node.value)

                if not is_configured_in_constructor:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.async_mock_vars[target.id] = node.lineno
                        elif isinstance(target, ast.Attribute):
                            var_name = self._get_full_attr_name(target)
                            if var_name:
                                self.async_mock_vars[var_name] = node.lineno

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        prev_async_mock_vars = self.async_mock_vars.copy()

        self.generic_visit(node)

        for var_name, line_num in self.async_mock_vars.items():
            if self.has_noqa_comment(line_num):
                continue

            configured = self._check_if_configured_in_scope(node, var_name)
            if not configured:
                self.issues.append((line_num, f"AsyncMock '{var_name}' created but not configured"))

        self.async_mock_vars = prev_async_mock_vars

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def _is_async_mock_call(self, node: ast.Call) -> bool:
        """Check if node is AsyncMock() call."""
        if isinstance(node.func, ast.Name) and node.func.id == "AsyncMock":
            return True
        return False

    def _has_config_kwargs(self, node: ast.Call) -> bool:
        """Check if AsyncMock() call has return_value or side_effect kwargs."""
        for keyword in node.keywords:
            if keyword.arg in ("return_value", "side_effect", "spec", "spec_set"):
                return True
        return False

    def _get_full_attr_name(self, node: ast.Attribute) -> Optional[str]:
        """Get full attribute name like 'mock.method'."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _get_base_name(self, node: ast.expr) -> Optional[str]:
        """Get base variable name from expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_base_name(node.value)
        return None

    def _check_if_configured_in_scope(self, scope_node: ast.FunctionDef, var_name: str) -> bool:
        """Check if AsyncMock variable is configured with return_value/side_effect in scope."""
        for stmt in ast.walk(scope_node):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Attribute):
                        base = self._get_base_name(target.value)
                        if base == var_name and target.attr in ("return_value", "side_effect"):
                            return True
        return False


class AsyncMockUsageChecker(ast.NodeVisitor):
    """AST visitor to detect potential async mock issues."""

    # Common async method patterns that should use AsyncMock
    ASYNC_PATTERNS = [
        "send_",  # Unambiguous async operation (network send)
        "async_",  # Explicit async naming
        "_async",  # Explicit async naming
        "fetch_",  # Unambiguous async operation (fetch data)
        "aclose",  # Async close
        "aenter",  # Async enter
        "aexit",  # Async exit
        "ainvoke",  # Async invoke (LangChain pattern)
    ]

    # Whitelist of known synchronous functions that match async patterns
    SYNC_FUNCTION_WHITELIST = [
        "_get_sandbox",
        "get_agent_graph",
        "create_auth_middleware",
        "create_summarization_model",
        "get_admin_token",
        "_get_user_realm_roles",
        "_get_user_client_roles",
        "_get_user_groups",
        "get_cache",
        "_send_smtp",
    ]

    def __init__(self, filename: str, source_lines: List[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.issues: List[Tuple[int, str]] = []
        self.has_asyncmock_import = False
        self.in_xfail_function = False

    def has_noqa_comment(self, lineno: int) -> bool:
        """Check if a line has # noqa: async-mock comment."""
        if lineno <= 0 or lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]
        return "# noqa: async-mock" in line or "#noqa: async-mock" in line

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check if AsyncMock is imported."""
        if node.module == "unittest.mock":
            for alias in node.names:
                if alias.name == "AsyncMock":
                    self.has_asyncmock_import = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track if we're inside a function with @pytest.mark.xfail decorator."""
        has_xfail = self._has_xfail_decorator(node)

        prev_in_xfail = self.in_xfail_function
        self.in_xfail_function = has_xfail
        self.generic_visit(node)
        self.in_xfail_function = prev_in_xfail

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track if we're inside an async function with @pytest.mark.xfail decorator."""
        has_xfail = self._has_xfail_decorator(node)

        prev_in_xfail = self.in_xfail_function
        self.in_xfail_function = has_xfail
        self.generic_visit(node)
        self.in_xfail_function = prev_in_xfail

    def visit_Call(self, node: ast.Call):
        """Check for patch.object() or patch() calls without AsyncMock."""
        patch_info = self._is_patch_call(node)
        if not patch_info:
            self.generic_visit(node)
            return

        func_name = patch_info

        if self._has_async_mock_callable(node):
            self.generic_visit(node)
            return

        method_name, module_path = self._extract_method_info(node)

        if method_name and self._should_flag_method(method_name, module_path):
            if not self.in_xfail_function and not self.has_noqa_comment(node.lineno):
                self.issues.append(
                    (
                        node.lineno,
                        f"Method '{method_name}' mocked without AsyncMock - use: {func_name}(..., new_callable=AsyncMock)",
                    )
                )

        self.generic_visit(node)

    def _is_patch_call(self, node: ast.Call) -> Optional[str]:
        """Check if node is a patch() or patch.object() call. Returns patch name or None."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("object", "__call__"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "patch":
                    return f"patch.{node.func.attr}"
        elif isinstance(node.func, ast.Name) and node.func.id == "patch":
            return "patch"
        return None

    def _has_async_mock_callable(self, node: ast.Call) -> bool:
        """Check if patch call has new_callable=AsyncMock."""
        for keyword in node.keywords:
            if keyword.arg == "new_callable":
                if isinstance(keyword.value, ast.Name) and keyword.value.id == "AsyncMock":
                    return True
        return False

    def _extract_method_info(self, node: ast.Call) -> Tuple[Optional[str], Optional[str]]:
        """Extract method name and module path from patch call."""
        method_name = None
        module_path = None

        if len(node.args) >= 2:
            if isinstance(node.args[1], ast.Constant):
                method_name = node.args[1].value
        elif len(node.args) >= 1:
            if isinstance(node.args[0], ast.Constant):
                full_path = node.args[0].value
                parts = full_path.split(".")
                method_name = parts[-1]
                if len(parts) > 1:
                    module_path = ".".join(parts[:-1])

        return method_name, module_path

    def _should_flag_method(self, method_name: str, module_path: Optional[str]) -> bool:
        """Determine if method should be flagged for missing AsyncMock."""
        if method_name in self.SYNC_FUNCTION_WHITELIST:
            return False

        if module_path:
            is_async = is_async_function_in_source(module_path, method_name)
            if is_async is True:
                return True
            elif is_async is False:
                return False
            # Fall through to pattern matching if can't determine from source

        # Pattern-based detection
        for pattern in self.ASYNC_PATTERNS:
            if pattern in method_name.lower():
                return True

        return False

    def _has_xfail_decorator(self, node) -> bool:
        """Check if node has @pytest.mark.xfail decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr == "xfail"
                ):
                    return True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "xfail"
                    ):
                        return True
        return False


def check_async_mock_configuration(filepath: str) -> List[Tuple[int, str]]:
    """
    Check a file for unconfigured AsyncMock instances.

    Args:
        filepath: Path to the test file to check

    Returns:
        List of (line_number, message) tuples for violations found
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        source_lines = content.splitlines()
        tree = ast.parse(content, filename=filepath)

        detector = AsyncMockConfigChecker(filepath, source_lines)
        detector.visit(tree)
        return detector.issues

    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"⚠️  Error checking {filepath}: {e}", file=sys.stderr)
        return []


def check_async_mock_usage(filepath: str) -> List[Tuple[int, str]]:
    """
    Check a file for async methods mocked without AsyncMock.

    Args:
        filepath: Path to the test file to check

    Returns:
        List of (line_number, message) tuples for violations found
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        source_lines = content.splitlines()
        tree = ast.parse(content, filename=filepath)

        checker = AsyncMockUsageChecker(filepath, source_lines)
        checker.visit(tree)

        return checker.issues
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"⚠️  Error processing {filepath}: {e}", file=sys.stderr)
        return []
