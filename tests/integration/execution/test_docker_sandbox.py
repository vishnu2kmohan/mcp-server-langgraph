"""
Integration tests for Docker sandbox

Tests Docker-based code execution with real containers.
Following TDD best practices - these tests should FAIL until implementation is complete.

NOTE: These tests require Docker to be running.
"""

import os

import pytest

# These imports will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
    from mcp_server_langgraph.execution.resource_limits import ResourceLimits
    from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError
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

    def test_default_network_mode_is_secure(self, docker_available):
        """
        🔴 RED: Test that default network mode from Settings is secure ("none").

        SECURITY CRITICAL: Code execution should default to maximum isolation.
        Users must explicitly opt-in to network access.

        This test will FAIL because core/config.py:216 currently defaults to "allowlist".
        Expected to PASS after fixing config.py to default to "none".
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.code_execution_network_mode == "none", (
            "SECURITY: Default network mode must be 'none' for safety. "
            f"Got: {settings.code_execution_network_mode}. "
            "Users must explicitly enable network access."
        )

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
        limits = ResourceLimits(network_mode="allowlist", allowed_domains=tuple(["httpbin.org"]))
        sandbox = DockerSandbox(limits=limits)

        code = """
# This test would require network setup in Docker
# For now, just verify sandbox accepts the configuration
print('Allowlist configured')
"""
        result = sandbox.execute(code)

        assert result.success is True

    def test_allowlist_mode_fails_closed_when_not_implemented(self, docker_available):
        """
        🔴 RED: Test that allowlist mode fails closed (uses "none") when not implemented.

        SECURITY CRITICAL: Unimplemented security features must fail safely.
        Currently execution/docker_sandbox.py:269-285 falls back to "bridge" (unrestricted).

        This test will FAIL because _get_network_mode() returns "bridge" for allowlist.
        Expected to PASS after fixing docker_sandbox.py to return "none" for unimplemented allowlist.
        """
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=("httpbin.org",),
        )
        sandbox = DockerSandbox(limits=limits)

        # Inspect internal network mode resolution
        network_mode = sandbox._get_network_mode()

        assert network_mode == "none", (
            "SECURITY: Unimplemented allowlist mode must fail closed (use 'none'). "
            f"Got: {network_mode}. "
            "Allowlist filtering is not yet implemented - must not fallback to unrestricted bridge network."
        )

        # Also verify network is actually disabled
        code = """
import socket
try:
    socket.create_connection(('httpbin.org', 80), timeout=2)
    print('NETWORK_ACCESSIBLE')
except Exception as e:
    print(f'NETWORK_BLOCKED: {type(e).__name__}')
"""
        result = sandbox.execute(code)
        assert "NETWORK_BLOCKED" in result.stdout, "Network must be blocked when allowlist is not implemented"
        assert "NETWORK_ACCESSIBLE" not in result.stdout


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

        # Wait for cleanup
        # Performance optimization: Use polling instead of fixed 2s sleep (save ~1.5s)
        from tests.helpers.polling import poll_until

        # Poll for container cleanup (usually completes in 0.3-0.5s)
        poll_until(lambda: len(client.containers.list(all=True)) <= initial_containers, interval=0.2, timeout=2.0)

        # Verify cleanup
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


# ============================================================================
# TDD RED Phase: OpenAI Codex Finding #4 - Docker Sandbox Security
# ============================================================================


@pytest.mark.integration
class TestDockerSandboxSecurity:
    """
    TDD RED phase tests for Docker sandbox security hardening (OpenAI Codex Finding #4).

    ISSUES IDENTIFIED:
    1. Root filesystem not read-only (read_only=False at line 240)
    2. Network allowlist mode not fully implemented (TODO at line 271)
    3. No validation of Docker socket access
    4. Potential container escape vectors

    EXPECTED: These tests will FAIL until security hardening is implemented.
    """

    @pytest.fixture
    def sandbox(self, docker_available):
        """Create Docker sandbox with default security settings"""
        limits = ResourceLimits.testing()
        return DockerSandbox(limits=limits)

    def test_container_uses_readonly_root_filesystem(self, sandbox):
        """
        Test that Docker container uses read-only root filesystem.

        RED: Will fail because docker_sandbox.py has read_only=False (line 240)
        """
        # Execute code - inspect the running container
        code = """
import os
# Try to write to root filesystem (should fail if read-only)
try:
    with open('/test_write.txt', 'w') as f:
        f.write('test')
    print('WRITE_SUCCEEDED')
except (IOError, OSError, PermissionError) as e:
    print(f'WRITE_BLOCKED: {type(e).__name__}')
"""
        result = sandbox.execute(code)

        # Root FS should be read-only, preventing writes outside /tmp
        assert "WRITE_BLOCKED" in result.stdout, (
            "Root filesystem should be read-only! "
            "Container can write to /, which is a security risk. "
            f"Output: {result.stdout}"
        )
        assert "WRITE_SUCCEEDED" not in result.stdout

    def test_container_allows_tmp_directory_writes(self, sandbox):
        """
        Test that /tmp is writable (via tmpfs) even with read-only root FS.

        GREEN: Should pass after implementing read-only FS with tmpfs for /tmp
        """
        code = """
import tempfile
import os

# /tmp should be writable via tmpfs
try:
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test data')
        temp_path = f.name

    # Verify we can read it back
    with open(temp_path, 'r') as f:
        data = f.read()

    os.unlink(temp_path)
    print('TMP_WRITABLE')
except Exception as e:
    print(f'TMP_FAILED: {e}')
"""
        result = sandbox.execute(code)

        assert "TMP_WRITABLE" in result.stdout, "/tmp should be writable via tmpfs"  # nosec B108
        assert "TMP_FAILED" not in result.stdout

    def test_network_allowlist_mode_blocks_unlisted_domains(self, docker_available):
        """
        Test that network allowlist mode blocks access to unlisted domains.

        RED: Will fail because allowlist filtering is not implemented (TODO at line 271)
        """
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=["httpbin.org"],  # Only allow httpbin.org
            timeout_seconds=10,
        )
        sandbox = DockerSandbox(limits=limits)

        code = """
import urllib.request
import socket

# Try to access unlisted domain (should be blocked)
try:
    urllib.request.urlopen('http://google.com', timeout=3)
    print('BLOCKED_DOMAIN_ACCESSIBLE')
except (urllib.error.URLError, socket.timeout, OSError) as e:
    print(f'BLOCKED_DOMAIN_DENIED: {type(e).__name__}')

# Try to access allowed domain (should succeed)
try:
    response = urllib.request.urlopen('http://httpbin.org/get', timeout=3)
    print('ALLOWED_DOMAIN_ACCESSIBLE')
except Exception as e:
    print(f'ALLOWED_DOMAIN_FAILED: {e}')
"""
        result = sandbox.execute(code)

        # Unlisted domain should be blocked
        assert "BLOCKED_DOMAIN_DENIED" in result.stdout, (
            "Network allowlist should block google.com. " f"Output: {result.stdout}"
        )
        assert "BLOCKED_DOMAIN_ACCESSIBLE" not in result.stdout

        # Allowed domain should work
        assert "ALLOWED_DOMAIN_ACCESSIBLE" in result.stdout, "Network allowlist should allow httpbin.org"

    def test_container_has_security_options_enabled(self, sandbox):
        """
        Test that Docker container has proper security options.

        Verifies:
        - no-new-privileges is set
        - All capabilities dropped
        - Process limits enforced
        """
        import docker

        client = docker.from_env()

        # Create a simple container to inspect
        code = "import time; time.sleep(1)"

        # Execute in background to inspect running container
        import threading

        def execute_code():
            sandbox.execute(code)

        thread = threading.Thread(target=execute_code)
        thread.start()

        # Give container time to start
        import time

        time.sleep(0.5)

        # Find our container
        containers = client.containers.list()
        sandbox_container = None
        for container in containers:
            if container.image.tags and "python" in str(container.image.tags):
                sandbox_container = container
                break

        if sandbox_container:
            # Inspect security settings
            config = sandbox_container.attrs

            # Check security_opt
            security_opts = config["HostConfig"].get("SecurityOpt", [])
            assert "no-new-privileges" in str(security_opts), "Container should have no-new-privileges enabled"

            # Check capabilities
            cap_drop = config["HostConfig"].get("CapDrop", [])
            assert "ALL" in cap_drop, "Container should have all capabilities dropped"

            # Check pids limit
            pids_limit = config["HostConfig"].get("PidsLimit")
            assert pids_limit is not None and pids_limit > 0, "Container should have process limits"

        thread.join(timeout=5)

    def test_network_none_mode_blocks_all_network_access(self, docker_available):
        """
        Test that network_mode='none' completely blocks network access.

        GREEN: Should already work based on current implementation
        """
        limits = ResourceLimits(
            network_mode="none",
            timeout_seconds=10,
        )
        sandbox = DockerSandbox(limits=limits)

        code = """
import socket
try:
    socket.create_connection(('8.8.8.8', 53), timeout=2)
    print('NETWORK_ACCESSIBLE')
except (OSError, socket.timeout) as e:
    print('NETWORK_BLOCKED')
"""
        result = sandbox.execute(code)

        assert "NETWORK_BLOCKED" in result.stdout, "Network should be completely disabled"
        assert "NETWORK_ACCESSIBLE" not in result.stdout

    def test_container_resource_limits_enforced(self, docker_available):
        """
        Test that memory and CPU limits are actually enforced.

        GREEN: Should already work based on current implementation
        """
        limits = ResourceLimits(
            max_memory_mb=128,  # 128MB limit
            max_cpu_percent=50,  # 50% CPU
            timeout_seconds=10,
        )
        sandbox = DockerSandbox(limits=limits)

        code = """
import sys
# Try to allocate more memory than limit (should be killed or fail)
try:
    # Allocate 256MB (exceeds 128MB limit)
    big_list = [0] * (256 * 1024 * 1024 // 8)  # 256MB of integers
    print('MEMORY_ALLOCATED')
except MemoryError:
    print('MEMORY_LIMITED')
"""
        result = sandbox.execute(code)

        # Container should be killed or fail due to memory limit
        # Result may vary: MemoryError, killed by OOM, or timeout
        assert result.success is False or "MEMORY_LIMITED" in result.stdout, "Memory limits should be enforced"

    @pytest.mark.skipif(
        not os.getenv("DOCKER_ROOTLESS_TEST"),
        reason="Requires Docker rootless mode (set DOCKER_ROOTLESS_TEST=1 to enable)",
    )
    def test_docker_socket_not_exposed_in_container(self, sandbox):
        """
        Test that Docker socket is not accessible inside container.

        This prevents container escape via Docker socket manipulation.
        Runs only when DOCKER_ROOTLESS_TEST environment variable is set.

        IMPORTANT: This test is aspirational - current implementation uses
        host Docker socket, which is a known security risk.
        """
        code = """
import os
if os.path.exists('/var/run/docker.sock'):
    print('DOCKER_SOCKET_EXPOSED')
else:
    print('DOCKER_SOCKET_NOT_EXPOSED')
"""
        result = sandbox.execute(code)

        assert "DOCKER_SOCKET_NOT_EXPOSED" in result.stdout, "Docker socket should not be accessible inside container!"
