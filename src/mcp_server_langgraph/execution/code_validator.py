"""
Code validator for secure Python code execution

Uses AST-based validation to detect dangerous patterns and enforce import whitelists.
Security-first design following defense-in-depth principles.
"""

import ast
from dataclasses import dataclass, field


class CodeValidationError(Exception):
    """Raised when code validation fails"""


@dataclass
class ValidationResult:
    """Result of code validation"""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        "valid" if self.is_valid else "invalid"
        return f"ValidationResult(is_valid={self.is_valid}, errors={len(self.errors)}, warnings={len(self.warnings)})"


class CodeValidator:
    """
    Validates Python code for safe execution in sandboxed environments.

    Uses AST analysis to detect:
    - Dangerous imports (os, subprocess, sys, etc.)
    - Dangerous builtin calls (eval, exec, compile, etc.)
    - Reflection/introspection abuse (globals, locals, getattr, etc.)
    - File access (open)
    - Network access (socket, urllib, requests)

    Example:
        >>> validator = CodeValidator(allowed_imports=["json", "math"])
        >>> result = validator.validate("import json\\ndata = json.dumps({})")
        >>> assert result.is_valid is True
    """

    # Dangerous modules that should never be allowed
    BLOCKED_MODULES = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pickle",
        "marshal",
        "ctypes",
        "importlib",
        "pty",
        "fcntl",
        "termios",
        "tty",
        "shutil",
        "tempfile",
        "urllib",
        "urllib.request",
        "urllib2",
        "httplib",
        "http.client",
        "requests",
        "ptrace",
        "resource",  # Can modify resource limits
        "signal",  # Can send signals to processes
        "multiprocessing",  # Can spawn processes
        "threading",  # Excessive threading can DoS
        "asyncio.subprocess",  # Subprocess via asyncio
        "code",  # Interactive interpreter
        "pdb",  # Debugger
        "inspect",  # Introspection
        "gc",  # Garbage collector manipulation
        "weakref",  # Weak reference manipulation
        "ast",  # Can be used to bypass restrictions
        "dis",  # Disassembler (introspection)
        "imp",  # Import hooks (deprecated but dangerous)
        "importlib.util",  # Dynamic imports
        "importlib.machinery",  # Import machinery
        "pkgutil",  # Package utilities
        "modulefinder",  # Module finding
        "runpy",  # Run Python modules
        "platform",  # System information disclosure
    }

    # Dangerous builtin functions
    BLOCKED_BUILTINS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "open",
        "input",
        "raw_input",  # Python 2
        "execfile",  # Python 2
        "reload",  # Reload modules
        "breakpoint",  # Debugger
        "help",  # Interactive help (can leak info)
        "dir",  # Introspection
        "id",  # Object ID (info disclosure)
        "memoryview",  # Direct memory access
    }

    # Patterns that suggest malicious intent
    SUSPICIOUS_PATTERNS = {
        "__builtins__",
        "__globals__",
        "__dict__",
        "__class__",
        "__bases__",
        "__subclasses__",
        "__init__",
        "__code__",
        "func_code",  # Python 2
        "func_globals",  # Python 2
    }

    def __init__(self, allowed_imports: list[str] | None = None):
        """
        Initialize code validator.

        Args:
            allowed_imports: List of allowed module names (e.g., ["json", "math", "pandas"])
        """
        self.allowed_imports = set(allowed_imports or [])

    def validate(self, code: str) -> ValidationResult:
        """
        Validate Python code for security issues.

        Args:
            code: Python source code to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for empty code
        if not code or not code.strip():
            errors.append("Code is empty or contains only whitespace")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        except Exception as e:
            errors.append(f"Failed to parse code: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Analyze AST for security issues
        visitor = SecurityVisitor(self.allowed_imports, self.BLOCKED_MODULES, self.BLOCKED_BUILTINS)
        visitor.visit(tree)

        errors.extend(visitor.errors)
        warnings.extend(visitor.warnings)

        is_valid = len(errors) == 0

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


class SecurityVisitor(ast.NodeVisitor):
    """AST visitor that detects security issues in Python code"""

    def __init__(
        self,
        allowed_imports: set[str],
        blocked_modules: set[str],
        blocked_builtins: set[str],
    ):
        self.allowed_imports = allowed_imports
        self.blocked_modules = blocked_modules
        self.blocked_builtins = blocked_builtins
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements"""
        for alias in node.names:
            module_name = alias.name

            # Check if module is explicitly blocked
            if self._is_blocked_module(module_name):
                self.errors.append(f"Import of blocked module '{module_name}' not allowed")
                continue

            # Check if module is in allowed list
            if module_name not in self.allowed_imports:
                self.errors.append(f"Import of module '{module_name}' not in allowed list")

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from ... import statements"""
        if node.module:
            # Check if module is explicitly blocked
            if self._is_blocked_module(node.module):
                self.errors.append(f"Import from blocked module '{node.module}' not allowed")
                self.generic_visit(node)
                return

            # Check if module is in allowed list
            if node.module not in self.allowed_imports:
                self.errors.append(f"Import from module '{node.module}' not in allowed list")

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for dangerous builtins"""
        func_name = self._get_call_name(node)

        if func_name:
            # Check for blocked builtin functions
            if func_name in self.blocked_builtins:
                self.errors.append(f"Call to blocked builtin '{func_name}' not allowed")

            # Check for dangerous attribute access patterns
            if func_name == "system":
                self.errors.append("Call to 'system' function not allowed")

        # Check for suspicious patterns in call arguments
        self._check_suspicious_patterns(node)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute access for suspicious patterns"""
        attr_name = node.attr

        # Check for dangerous attribute access
        if attr_name in ["system", "popen", "spawn", "exec"]:
            self.errors.append(f"Access to attribute '{attr_name}' not allowed")

        # Check for introspection patterns
        if attr_name in CodeValidator.SUSPICIOUS_PATTERNS:
            self.warnings.append(f"Suspicious attribute access '{attr_name}' detected")

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check variable/name access for suspicious patterns"""
        name = node.id

        # Check for direct access to dangerous builtins
        if name in self.blocked_builtins:
            self.errors.append(f"Access to blocked name '{name}' not allowed")

        # Check for suspicious patterns
        if name in CodeValidator.SUSPICIOUS_PATTERNS:
            self.warnings.append(f"Suspicious name '{name}' detected")

        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Check while loops for obvious infinite loops"""
        # Detect 'while True:' or 'while 1:'
        if isinstance(node.test, ast.Constant) and (node.test.value is True or node.test.value == 1):
            self.warnings.append("Infinite loop detected: 'while True' or 'while 1'")

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Extract function name from call node"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _is_blocked_module(self, module_name: str) -> bool:
        """Check if module or any of its parents are blocked"""
        # Check exact match
        if module_name in self.blocked_modules:
            return True

        # Check parent modules (e.g., 'os.path' should be blocked if 'os' is blocked)
        parts = module_name.split(".")
        for i in range(len(parts)):
            parent = ".".join(parts[: i + 1])
            if parent in self.blocked_modules:
                return True

        return False

    def _check_suspicious_patterns(self, node: ast.Call) -> None:
        """Check for suspicious patterns in call arguments"""
        # Check for eval/exec with string formatting (code injection)
        func_name = self._get_call_name(node)
        if func_name in ["eval", "exec", "compile"]:
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):  # f-string
                    self.errors.append(f"Dangerous pattern: {func_name} with f-string")
                elif isinstance(arg, ast.BinOp):  # String concatenation
                    self.errors.append(f"Dangerous pattern: {func_name} with string concatenation")
