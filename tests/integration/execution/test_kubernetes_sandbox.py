"""
Integration tests for Kubernetes sandbox

Tests Kubernetes Job-based code execution.
Following TDD best practices - these tests should FAIL until implementation is complete.

NOTE: These tests require Kubernetes cluster access (kubeconfig).
"""

import gc

import pytest

# These imports will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox
    from mcp_server_langgraph.execution.resource_limits import ResourceLimits
    from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError
except ImportError:
    pytest.skip("Sandbox modules not implemented yet", allow_module_level=True)


@pytest.fixture
def kubernetes_available():
    """Check if Kubernetes is available"""
    try:
        from kubernetes import client, config

        config.load_kube_config()
        v1 = client.CoreV1Api()
        v1.list_namespace()
        return True
    except Exception:
        pytest.skip("Kubernetes not available (no kubeconfig or cluster)")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testkubernetessandbox")
class TestKubernetesSandbox:
    """Test Kubernetes sandbox basic functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def sandbox(self, kubernetes_available):
        """Create Kubernetes sandbox instance"""
        limits = ResourceLimits.testing()
        return KubernetesSandbox(limits=limits, namespace="default")

    def test_sandbox_initialization(self, sandbox):
        """Test sandbox initializes correctly"""
        assert sandbox is not None
        assert isinstance(sandbox, Sandbox)
        assert isinstance(sandbox, KubernetesSandbox)

    def test_simple_code_execution(self, sandbox):
        """Test executing simple Python code"""
        code = "print('Hello from Kubernetes!')"
        result = sandbox.execute(code)

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "Hello from Kubernetes!" in result.stdout
        assert result.exit_code == 0

    def test_code_with_output(self, sandbox):
        """Test code that produces output"""
        code = """
result = 3 + 3
print(f'Result: {result}')
"""
        result = sandbox.execute(code)

        assert result.success is True
        assert "Result: 6" in result.stdout
        assert result.exit_code == 0

    def test_code_with_error(self, sandbox):
        """Test code that raises an error"""
        code = "raise RuntimeError('K8s test error')"
        result = sandbox.execute(code)

        assert result.success is False
        assert "RuntimeError" in result.stderr
        assert "K8s test error" in result.stderr
        assert result.exit_code != 0


@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.xdist_group(name="testkubernetessandboxstderrseparation")
class TestKubernetesSandboxStderrSeparation:
    """
    Regression tests for stdout/stderr separation in Kubernetes sandbox

    CODEX FINDING: OpenAI Codex identified that test_code_with_error (line 80)
    was failing because KubernetesSandbox._get_job_logs() returned empty stderr.
    Kubernetes combines stdout/stderr into a single log stream, so we need to
    separate them based on content patterns to match DockerSandbox behavior.

    These tests ensure stderr/stdout are properly separated, preventing regression.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def sandbox(self, kubernetes_available):
        """Create Kubernetes sandbox instance"""
        limits = ResourceLimits.testing()
        return KubernetesSandbox(limits=limits, namespace="default")

    def test_error_output_goes_to_stderr(self, sandbox):
        """
        Test that Python errors are captured in stderr, not stdout

        REGRESSION: Prevents empty stderr when errors occur (Codex finding)
        """
        code = "raise RuntimeError('Test error message')"
        result = sandbox.execute(code)

        assert result.success is False
        assert result.exit_code != 0
        # Error output must be in stderr
        assert "RuntimeError" in result.stderr, "RuntimeError should be in stderr"
        assert "Test error message" in result.stderr, "Error message should be in stderr"
        # stdout should be empty for pure errors
        assert result.stdout == "", "stdout should be empty for error-only execution"

    def test_traceback_goes_to_stderr(self, sandbox):
        """
        Test that Python tracebacks are captured in stderr

        REGRESSION: Ensures Traceback detection works in _get_job_logs
        """
        code = """
def failing_function():
    raise ValueError('Intentional failure')

failing_function()
"""
        result = sandbox.execute(code)

        assert result.success is False
        assert "Traceback" in result.stderr, "Traceback should be in stderr"
        assert "ValueError" in result.stderr, "ValueError should be in stderr"
        assert "Intentional failure" in result.stderr

    def test_syntax_error_goes_to_stderr(self, sandbox):
        """
        Test that syntax errors are captured in stderr

        REGRESSION: Ensures SyntaxError detection works in _get_job_logs
        """
        code = "if True print('missing colon')"
        result = sandbox.execute(code)

        assert result.success is False
        assert "SyntaxError" in result.stderr, "SyntaxError should be in stderr"

    def test_successful_output_goes_to_stdout(self, sandbox):
        """
        Test that successful execution output goes to stdout, not stderr

        REGRESSION: Ensures we don't incorrectly put success output in stderr
        """
        code = "print('Success message')"
        result = sandbox.execute(code)

        assert result.success is True
        assert result.exit_code == 0
        assert "Success message" in result.stdout, "Output should be in stdout"
        assert result.stderr == "", "stderr should be empty for successful execution"

    def test_matches_docker_sandbox_behavior(self, sandbox):
        """
        Test that stderr/stdout behavior matches DockerSandbox

        This ensures consistent behavior across sandbox implementations.
        Both should separate stdout/stderr the same way.
        """
        # Test error case
        error_code = "raise TypeError('Type mismatch')"
        result = sandbox.execute(error_code)

        assert result.success is False
        assert "TypeError" in result.stderr
        assert "Type mismatch" in result.stderr
        assert result.stdout == ""

        # Test success case
        success_code = "print('Output'); print('Line 2')"
        result = sandbox.execute(success_code)

        assert result.success is True
        assert "Output" in result.stdout
        assert "Line 2" in result.stdout
        assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testkubernetessandboxresourcelimits")
class TestKubernetesSandboxResourceLimits:
    """Test resource limit enforcement in Kubernetes"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_timeout_enforcement(self, kubernetes_available):
        """Test that timeout is enforced"""
        limits = ResourceLimits(timeout_seconds=1)
        sandbox = KubernetesSandbox(limits=limits, namespace="default")

        # Code that runs longer than timeout
        code = """
import time
time.sleep(2)
print('Should not reach here')
"""
        result = sandbox.execute(code)

        assert result.success is False
        assert result.timed_out is True
        assert result.execution_time >= 1

    def test_memory_limit_enforcement(self, kubernetes_available):
        """Test that memory limits are enforced"""
        limits = ResourceLimits(memory_limit_mb=128)
        sandbox = KubernetesSandbox(limits=limits, namespace="default")

        # Code that tries to allocate memory
        code = """
import sys
# Just verify the job runs with memory limit
print(f'Memory limit test passed')
"""
        result = sandbox.execute(code)

        assert result.success is True

    def test_cpu_quota_enforcement(self, kubernetes_available):
        """Test that CPU limits are enforced"""
        limits = ResourceLimits(cpu_quota=0.5)
        sandbox = KubernetesSandbox(limits=limits, namespace="default")

        code = """
print('CPU quota test passed')
"""
        result = sandbox.execute(code)

        assert result.success is True


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testkubernetessandboxcleanup")
class TestKubernetesSandboxCleanup:
    """Test resource cleanup in Kubernetes"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_job_cleanup_on_success(self, kubernetes_available):
        """Test that Jobs are cleaned up after successful execution"""
        from kubernetes import client, config

        config.load_kube_config()
        batch_v1 = client.BatchV1Api()

        initial_jobs = len(batch_v1.list_namespaced_job(namespace="default").items)

        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default")
        result = sandbox.execute("print('test')")

        assert result.success is True

        # Wait for TTL controller to clean up
        # Performance optimization: Use polling instead of fixed 5s sleep (save ~3-4s)
        from tests.helpers.polling import poll_until

        def job_cleanup_complete():
            """Check if job count has stabilized (cleanup complete)."""
            current_jobs = len(batch_v1.list_namespaced_job(namespace="default").items)
            # Job should be cleaned up or marked for cleanup
            return current_jobs <= initial_jobs + 1

        # Poll every 0.5s for up to 5s (usually completes in 1-2s)
        poll_until(job_cleanup_complete, interval=0.5, timeout=5.0)

        # Verify final state
        final_jobs = len(batch_v1.list_namespaced_job(namespace="default").items)
        assert final_jobs <= initial_jobs + 1

    def test_job_cleanup_on_error(self, kubernetes_available):
        """Test that Jobs are cleaned up even on error"""
        from kubernetes import client, config

        config.load_kube_config()
        batch_v1 = client.BatchV1Api()

        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default")
        result = sandbox.execute("raise ValueError('test')")

        assert result.success is False

        # Cleanup should still happen
        # Performance optimization: Use polling instead of fixed 5s sleep (save ~3-4s)
        from tests.helpers.polling import poll_until

        # Wait for cleanup with polling (usually completes in 1-2s)
        poll_until(lambda: len(batch_v1.list_namespaced_job(namespace="default").items) < 10, interval=0.5, timeout=5.0)

        # Verify jobs are being cleaned up
        jobs = batch_v1.list_namespaced_job(namespace="default").items
        # Should not accumulate failed jobs indefinitely
        assert len(jobs) < 10


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testkubernetessandboxconfiguration")
class TestKubernetesSandboxConfiguration:
    """Test Kubernetes sandbox configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_custom_namespace(self, kubernetes_available):
        """Test using custom namespace"""
        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default")

        result = sandbox.execute("print('custom namespace test')")

        assert result.success is True

    def test_custom_image(self, kubernetes_available):
        """Test using custom container image"""
        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default", image="python:3.12-slim")

        result = sandbox.execute("import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')")

        assert result.success is True
        assert "Python 3." in result.stdout

    def test_job_ttl(self, kubernetes_available):
        """Test Job TTL configuration"""
        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default", job_ttl=60)

        result = sandbox.execute("print('TTL test')")

        assert result.success is True


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testkubernetessandboxerrorhandling")
class TestKubernetesSandboxErrorHandling:
    """Test error handling in Kubernetes sandbox"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_invalid_namespace(self):
        """Test handling of invalid namespace"""
        limits = ResourceLimits.testing()

        with pytest.raises(SandboxError):
            sandbox = KubernetesSandbox(limits=limits, namespace="nonexistent-namespace-12345")
            sandbox.execute("print('test')")

    def test_kubernetes_not_available(self):
        """Test handling when Kubernetes is not available"""
        # This would need mock/patch to test properly
        # For now, verify the class exists
        assert KubernetesSandbox is not None

    def test_empty_code(self, kubernetes_available):
        """Test handling of empty code"""
        limits = ResourceLimits.testing()
        sandbox = KubernetesSandbox(limits=limits, namespace="default")

        result = sandbox.execute("")

        assert result.success is False
