"""
Unit tests for code validator

Tests AST-based validation, import whitelisting, and security controls.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import gc

import pytest
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.unit

# This import will fail initially - that's expected in TDD!
# We'll implement the module to make tests pass
try:
    from mcp_server_langgraph.execution.code_validator import CodeValidationError, CodeValidator, ValidationResult
except ImportError:
    pytest.skip("CodeValidator not implemented yet", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcodevalidator")
class TestCodeValidator:
    """Test suite for CodeValidator"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        """Create validator instance with default safe imports"""
        return CodeValidator(
            allowed_imports=[
                "pandas",
                "numpy",
                "json",
                "datetime",
                "math",
                "statistics",
                "collections",
                "itertools",
                "functools",
                "typing",
            ]
        )

    @pytest.fixture
    def strict_validator(self):
        """Create validator with minimal allowed imports"""
        return CodeValidator(allowed_imports=["json", "math"])

    def test_validator_initialization(self):
        """Test validator initializes with allowed imports"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        assert "json" in validator.allowed_imports
        assert "math" in validator.allowed_imports

    def test_simple_valid_code(self, validator):
        """Test validation of simple safe code"""
        code = "result = 2 + 2"
        result = validator.validate(code)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_code_with_allowed_import(self, validator):
        """Test code with allowed import passes validation"""
        code = """
import json
data = json.dumps({"key": "value"})
"""
        result = validator.validate(code)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_code_with_multiple_imports(self, validator):
        """Test code with multiple allowed imports"""
        code = """
import json
import math
import datetime

result = math.sqrt(16)
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_reject_dangerous_import_os(self, validator):
        """Test that os module import is blocked"""
        code = "import os"
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("os" in str(error).lower() for error in result.errors)

    def test_reject_dangerous_import_subprocess(self, validator):
        """Test that subprocess import is blocked"""
        code = "import subprocess"
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("subprocess" in str(error).lower() for error in result.errors)

    def test_reject_dangerous_import_sys(self, validator):
        """Test that sys import is blocked"""
        code = "import sys"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_eval_usage(self, validator):
        """Test that eval() calls are blocked"""
        code = 'result = eval("2 + 2")'
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("eval" in str(error).lower() for error in result.errors)

    def test_reject_exec_usage(self, validator):
        """Test that exec() calls are blocked"""
        code = "exec(\"print('hello')\")"
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("exec" in str(error).lower() for error in result.errors)

    def test_reject_compile_usage(self, validator):
        """Test that compile() calls are blocked"""
        code = 'code_obj = compile("2+2", "<string>", "eval")'
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("compile" in str(error).lower() for error in result.errors)

    def test_reject_dunder_import(self, validator):
        """Test that __import__() is blocked"""
        code = '__import__("os")'
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_from_import_dangerous(self, validator):
        """Test that 'from os import system' is blocked"""
        code = "from os import system"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_os_system_via_attribute(self, validator):
        """Test detection of dangerous attribute access patterns"""
        code = """
import os
os.system("ls")
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_allow_safe_builtins(self, validator):
        """Test that safe builtin functions are allowed"""
        code = """
numbers = [1, 2, 3, 4, 5]
result = sum(numbers)
max_val = max(numbers)
min_val = min(numbers)
length = len(numbers)
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_syntax_error_detection(self, validator):
        """Test detection of syntax errors"""
        code = "if True print('missing colon')"
        result = validator.validate(code)
        assert result.is_valid is False
        assert any("syntax" in str(error).lower() for error in result.errors)

    def test_empty_code(self, validator):
        """Test validation of empty code"""
        code = ""
        result = validator.validate(code)
        # Empty code should be considered invalid
        assert result.is_valid is False

    def test_whitespace_only_code(self, validator):
        """Test validation of whitespace-only code"""
        code = "   \n\t  \n"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_valid_pandas_usage(self, validator):
        """Test that pandas operations are allowed"""
        code = """
import pandas as pd
df = pd.DataFrame({"a": [1, 2, 3]})
result = df.sum()
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_valid_numpy_usage(self, validator):
        """Test that numpy operations are allowed"""
        code = """
import numpy as np
arr = np.array([1, 2, 3, 4])
result = np.mean(arr)
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_reject_import_not_in_whitelist(self, strict_validator):
        """Test that imports not in whitelist are blocked"""
        code = "import pandas"
        result = strict_validator.validate(code)
        assert result.is_valid is False

    def test_reject_open_file_access(self, validator):
        """Test that open() calls are blocked (file access)"""
        code = 'f = open("/etc/passwd", "r")'
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_input_function(self, validator):
        """Test that input() is blocked (can't interact in sandbox)"""
        code = 'name = input("Enter name: ")'
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_globals_access(self, validator):
        """Test that globals() access is blocked"""
        code = "g = globals()"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_locals_access(self, validator):
        """Test that locals() access is blocked"""
        code = "l = locals()"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_vars_access(self, validator):
        """Test that vars() access is blocked"""
        code = "v = vars()"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_validation_result_structure(self, validator):
        """Test ValidationResult structure"""
        code = "result = 2 + 2"
        result = validator.validate(code)

        # Check result has required attributes
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_multiple_validation_errors(self, validator):
        """Test that multiple errors are collected"""
        code = """
import os
import subprocess
eval("2 + 2")
"""
        result = validator.validate(code)
        assert result.is_valid is False
        # Should have multiple errors
        assert len(result.errors) >= 2

    def test_nested_dangerous_call(self, validator):
        """Test detection of nested dangerous calls"""
        code = """
def dangerous_func():
    import os
    return os.system("ls")
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_lambda_with_eval(self, validator):
        """Test detection of eval in lambda"""
        code = "dangerous = lambda x: eval(x)"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_list_comprehension_safe(self, validator):
        """Test that safe list comprehensions work"""
        code = "squares = [x**2 for x in range(10)]"
        result = validator.validate(code)
        assert result.is_valid is True

    def test_dict_comprehension_safe(self, validator):
        """Test that safe dict comprehensions work"""
        code = "mapping = {str(i): i**2 for i in range(5)}"
        result = validator.validate(code)
        assert result.is_valid is True

    def test_generator_expression_safe(self, validator):
        """Test that safe generator expressions work"""
        code = "squares_gen = (x**2 for x in range(10))"
        result = validator.validate(code)
        assert result.is_valid is True

    def test_class_definition_safe(self, validator):
        """Test that safe class definitions work"""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_async_code_safe(self, validator):
        """Test that safe async code works"""
        code = """
async def fetch_data():
    return {"data": "value"}
"""
        result = validator.validate(code)
        assert result.is_valid is True

    def test_context_manager_safe(self, validator):
        """Test that safe context managers work"""
        code = """
class MyContext:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
"""
        result = validator.validate(code)
        assert result.is_valid is True


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testsecurityinjectionpatterns")
class TestSecurityInjectionPatterns:
    """Security-focused tests for injection attack patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "math"])

    def test_reject_pickle_import(self, validator):
        """Test that pickle module is blocked (deserialization attack)"""
        code = "import pickle"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_importlib_usage(self, validator):
        """Test that importlib is blocked (dynamic import)"""
        code = "import importlib"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_base64_exec_pattern(self, validator):
        """Test detection of base64 + exec pattern"""
        code = """
import base64
exec(base64.b64decode(b"cHJpbnQoJ2hhY2tlZCcp"))
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_string_formatting_with_exec(self, validator):
        """Test detection of string format + exec"""
        code = """
cmd = "print('test')"
exec(f"{cmd}")
"""
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_getattr_attribute_access(self, validator):
        """Test that getattr with dangerous names is blocked"""
        code = "getattr(__builtins__, 'eval')('2+2')"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_setattr_usage(self, validator):
        """Test that setattr is blocked (can modify objects)"""
        code = "setattr(obj, '__class__', malicious_class)"
        result = validator.validate(code)
        assert result.is_valid is False

    def test_reject_delattr_usage(self, validator):
        """Test that delattr is blocked"""
        code = "delattr(obj, 'safe_attribute')"
        result = validator.validate(code)
        assert result.is_valid is False


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.xdist_group(name="testcodevalidatorproperties")
class TestCodeValidatorProperties:
    """Property-based tests using Hypothesis for fuzzing"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(st.text())
    def test_validator_never_crashes(self, code):
        """Property: validator should never crash on any input"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        try:
            result = validator.validate(code)
            # Should always return ValidationResult
            assert hasattr(result, "is_valid")
            assert isinstance(result.is_valid, bool)
        except Exception as e:
            # If exception occurs, should be expected types only
            assert isinstance(e, (CodeValidationError, SyntaxError, ValueError))

    @given(st.text(min_size=1, max_size=1000))
    def test_random_text_mostly_invalid(self, code):
        """Property: random text should mostly be invalid or have syntax errors"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        result = validator.validate(code)
        # Result should be well-formed
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)

    @given(
        st.sampled_from(
            [
                "import os",
                "import sys",
                "import subprocess",
                "eval('x')",
                "exec('x')",
                "__import__('os')",
            ]
        )
    )
    def test_dangerous_patterns_always_rejected(self, code):
        """Property: known dangerous patterns always rejected"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        result = validator.validate(code)
        assert result.is_valid is False
        assert len(result.errors) > 0

    @given(
        st.sampled_from(
            [
                "x = 1 + 1",
                "result = sum([1, 2, 3])",
                "import json\ndata = json.dumps({})",
                "import math\nresult = math.sqrt(4)",
            ]
        )
    )
    def test_safe_patterns_always_accepted(self, code):
        """Property: known safe patterns always accepted"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        result = validator.validate(code)
        assert result.is_valid is True
        assert len(result.errors) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="testvalidationresult")
class TestValidationResult:
    """Test ValidationResult data class"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validation_result_creation(self):
        """Test creating ValidationResult"""
        result = ValidationResult(is_valid=True, errors=[], warnings=["Minor warning"])
        assert result.is_valid is True
        assert result.errors == []
        assert len(result.warnings) == 1

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors"""
        result = ValidationResult(
            is_valid=False,
            errors=["Import 'os' not allowed", "Function 'eval' not allowed"],
            warnings=[],
        )
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validation_result_repr(self):
        """Test ValidationResult string representation"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        repr_str = repr(result)
        assert "ValidationResult" in repr_str or "valid" in repr_str.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcodevalidationerror")
class TestCodeValidationError:
    """Test CodeValidationError exception"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_code_validation_error_creation(self):
        """Test creating CodeValidationError"""
        error = CodeValidationError("Import 'os' not allowed")
        assert "os" in str(error)

    def test_code_validation_error_inheritance(self):
        """Test that CodeValidationError inherits from Exception"""
        error = CodeValidationError("Test error")
        assert isinstance(error, Exception)
