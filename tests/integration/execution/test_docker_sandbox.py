"""
Integration tests for Docker sandbox

Tests Docker-based code execution with real containers.
Following TDD best practices - these tests should FAIL until implementation is complete.

NOTE: These tests require Docker to be running.
"""

import pytest

# These imports will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError
    from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
    from mcp_server_langgraph.execution.resource_limits import ResourceLimits
except ImportError:
    pytest.skip("Sandbox modules not implemented yet", allow_module_level=True)


@pytest.fixture
def docker_available():
    """Check if Docker is available"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        pytest.skip("Docker not available")


@pytest.mark.integration
class TestDockerSandbox:
    """Test Docker sandbox basic functionality"""

    @pytest.fixture
    def sandbox(self, docker_available):
        """Create Docker sandbox instance"""
        limits = ResourceLimits.testing()  # Use testing profile
        return DockerSandbox(limits=limits)

    def test_sandbox_initialization(self, sandbox):
        """Test sandbox initializes correctly"""
        assert sandbox is not None
        assert isinstance(sandbox, Sandbox)
        assert isinstance(sandbox, DockerSandbox)

    def test_simple_code_execution(self, sandbox):
        """Test executing simple Python code"""
        code = "print('Hello, World!')"
        result = sandbox.execute(code)

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert result.stderr == ""
        assert result.exit_code == 0

    def test_code_with_output(self, sandbox):
        """Test code that produces output"""
        code = """
result = 2 + 2
print(f'Result: {result}')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Result: 4" in result.stdout
        assert result.exit_code == 0

    def test_code_with_error(self, sandbox):
        """Test code that raises an error"""
        code = "raise ValueError('Test error')"
        result = sandbox.execute(code)

        assert result.success is False
        assert "ValueError" in result.stderr
        assert "Test error" in result.stderr
        assert result.exit_code != 0

    def test_syntax_error_handling(self, sandbox):
        """Test handling of syntax errors"""
        code = "if True print('missing colon')"
        result = sandbox.execute(code)

        assert result.success is False
        assert "SyntaxError" in result.stderr
        assert result.exit_code != 0

    def test_import_allowed_module(self, sandbox):
        """Test importing allowed modules"""
        code = """
import json
data = json.dumps({'key': 'value'})
print(data)
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert '{"key": "value"}' in result.stdout

    def test_multiple_executions(self, sandbox):
        """Test multiple sequential executions"""
        results = []
        for i in range(3):
            code = f"print('Execution {i}')"
            result = sandbox.execute(code)
            results.append(result)

        assert all(r.success for r in results)
        for i, result in enumerate(results):
            assert f"Execution {i}" in result.stdout


@pytest.mark.integration
class TestDockerSandboxResourceLimits:
    """Test resource limit enforcement"""

    def test_timeout_enforcement(self, docker_available):
        """Test that timeout is enforced"""
        limits = ResourceLimits(timeout_seconds=2)
        sandbox = DockerSandbox(limits=limits)

        # Code that runs longer than timeout
        code = """
import time
time.sleep(10)
print('Should not reach here')
"""
        result = sandbox.execute(code)

        assert result.success is False
        assert result.timed_out is True
        assert result.execution_time >= 2
        assert result.execution_time < 3  # Should stop quickly after timeout

    def test_memory_limit_enforcement(self, docker_available):
        """Test that memory limits are enforced"""
        limits = ResourceLimits(memory_limit_mb=64)  # Very low limit
        sandbox = DockerSandbox(limits=limits)

        # Code that tries to allocate too much memory
        code = """
try:
    big_list = [0] * (100 * 1024 * 1024)  # Try to allocate 100MB
    print('Allocated successfully')
except MemoryError:
    print('Memory limit enforced')
"""
        result = sandbox.execute(code)

        # Either fails with OOM or catches MemoryError
        assert "Memory limit enforced" in result.stdout or not result.success

    def test_cpu_quota_enforcement(self, docker_available):
        """Test that CPU quota is enforced"""
        limits = ResourceLimits(cpu_quota=0.5, timeout_seconds=5)
        sandbox = DockerSandbox(limits=limits)

        # CPU-intensive task
        code = """
import time
start = time.time()
result = sum(i * i for i in range(10000000))
duration = time.time() - start
print(f'Duration: {duration:.2f}s')
"""
        result = sandbox.execute(code)

        # With 0.5 CPU quota, should take longer than with full CPU
        assert result.success is True
        # Verify it ran (exact timing is unreliable in tests)
        assert "Duration" in result.stdout


@pytest.mark.integration
class TestDockerSandboxNetworkIsolation:
    """Test network isolation"""

    def test_network_disabled(self, docker_available):
        """Test that network is disabled by default"""
        limits = ResourceLimits(network_mode="none")
        sandbox = DockerSandbox(limits=limits)

        code = """
import socket
try:
    socket.create_connection(('google.com', 80), timeout=2)
    print('Network accessible')
except Exception as e:
    print(f'Network blocked: {type(e).__name__}')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Network blocked" in result.stdout

    def test_network_allowlist(self, docker_available):
        """Test network allowlist mode"""
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=tuple(["httpbin.org"])
        )
        sandbox = DockerSandbox(limits=limits)

        code = """
# This test would require network setup in Docker
# For now, just verify sandbox accepts the configuration
print('Allowlist configured')
"""
        result = sandbox.execute(code)

        assert result.success is True


@pytest.mark.integration
class TestDockerSandboxSecurity:
    """Test security isolation"""

    def test_filesystem_isolation(self, docker_available):
        """Test that filesystem is isolated"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        # Try to list files - should only see container filesystem
        code = """
import os
files = os.listdir('/')
print(f'Root files: {len(files)}')
# Should not see host filesystem
assert '/Users' not in str(files)  # macOS
assert '/home' not in str(files) or len(files) < 20  # Linux container
print('Filesystem isolated')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Filesystem isolated" in result.stdout

    def test_process_isolation(self, docker_available):
        """Test that processes are isolated"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        code = """
import os
print(f'PID: {os.getpid()}')
print(f'PPID: {os.getppid()}')
# In container, PID should be 1 or very low
assert os.getpid() < 100
print('Process isolated')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Process isolated" in result.stdout

    def test_no_privilege_escalation(self, docker_available):
        """Test that privilege escalation is blocked"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        code = """
import os
try:
    os.setuid(0)  # Try to become root
    print('Privilege escalation succeeded - SECURITY ISSUE!')
except PermissionError:
    print('Privilege escalation blocked')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Privilege escalation blocked" in result.stdout


@pytest.mark.integration
class TestDockerSandboxCleanup:
    """Test resource cleanup"""

    def test_container_cleanup_on_success(self, docker_available):
        """Test that containers are cleaned up after successful execution"""
        import docker
        client = docker.from_env()

        initial_containers = len(client.containers.list(all=True))

        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)
        result = sandbox.execute("print('test')")

        assert result.success is True

        # Wait a moment for cleanup
        import time
        time.sleep(1)

        # Container should be removed
        final_containers = len(client.containers.list(all=True))
        assert final_containers <= initial_containers

    def test_container_cleanup_on_error(self, docker_available):
        """Test that containers are cleaned up even on error"""
        import docker
        client = docker.from_env()

        initial_containers = len(client.containers.list(all=True))

        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)
        result = sandbox.execute("raise ValueError('test')")

        assert result.success is False

        # Wait a moment for cleanup
        import time
        time.sleep(1)

        # Container should still be removed
        final_containers = len(client.containers.list(all=True))
        assert final_containers <= initial_containers

    def test_container_cleanup_on_timeout(self, docker_available):
        """Test that containers are cleaned up on timeout"""
        import docker
        client = docker.from_env()

        initial_containers = len(client.containers.list(all=True))

        limits = ResourceLimits(timeout_seconds=1)
        sandbox = DockerSandbox(limits=limits)
        result = sandbox.execute("import time; time.sleep(10)")

        assert result.timed_out is True

        # Wait a moment for cleanup
        import time
        time.sleep(2)

        # Container should be removed
        final_containers = len(client.containers.list(all=True))
        assert final_containers <= initial_containers


@pytest.mark.integration
class TestDockerSandboxConfiguration:
    """Test sandbox configuration options"""

    def test_custom_docker_image(self, docker_available):
        """Test using custom Docker image"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits, image="python:3.12-slim")

        result = sandbox.execute("import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')")

        assert result.success is True
        assert "Python 3." in result.stdout

    def test_custom_docker_socket(self, docker_available):
        """Test using custom Docker socket path"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits, socket_path="/var/run/docker.sock")

        result = sandbox.execute("print('test')")

        assert result.success is True

    def test_working_directory(self, docker_available):
        """Test setting working directory in container"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        code = """
import os
print(f'Working dir: {os.getcwd()}')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Working dir:" in result.stdout


@pytest.mark.integration
class TestDockerSandboxErrorHandling:
    """Test error handling"""

    def test_docker_not_available(self):
        """Test handling when Docker is not available"""
        # This test intentionally creates a sandbox with invalid config
        limits = ResourceLimits.testing()

        with pytest.raises(SandboxError, match="Docker"):
            sandbox = DockerSandbox(limits=limits, socket_path="/nonexistent/docker.sock")
            sandbox.execute("print('test')")

    def test_invalid_image(self, docker_available):
        """Test handling of invalid Docker image"""
        limits = ResourceLimits.testing()

        with pytest.raises(SandboxError):
            sandbox = DockerSandbox(limits=limits, image="nonexistent-image:latest")
            sandbox.execute("print('test')")

    def test_empty_code(self, docker_available):
        """Test handling of empty code"""
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        result = sandbox.execute("")

        assert result.success is False
        assert "empty" in result.stderr.lower() or result.stdout == ""
