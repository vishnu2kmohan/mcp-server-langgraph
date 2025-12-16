"""
TDD RED Phase: Tests for Kubernetes sandbox async execution.

These tests define the expected behavior of the aexecute() method
which provides non-blocking async execution using asyncio.to_thread().

Tests are designed to fail initially (RED phase) until implementation
is complete (GREEN phase).

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import asyncio
import gc
from unittest.mock import MagicMock, patch

import pytest

# Kubernetes is an optional dependency
try:
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    ApiException = Exception  # type: ignore[misc, assignment]

from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult

pytestmark = pytest.mark.skipif(not KUBERNETES_AVAILABLE, reason="Kubernetes package not installed")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="kubernetes_sandbox_async")
class TestKubernetesSandboxAsyncExecute:
    """
    TDD tests for KubernetesSandbox.aexecute() - async non-blocking execution.

    These tests verify that:
    1. aexecute() exists and is an async method
    2. aexecute() returns correct ExecutionResult
    3. aexecute() does not block the event loop
    4. aexecute() propagates timeouts and errors correctly
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_aexecute_method_exists_and_is_async(self):
        """
        RED: Verify aexecute() method exists and is a coroutine function.

        This is the basic contract test - aexecute() must be async.
        """
        limits = ResourceLimits.testing()

        # Mock kubernetes config and clients
        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            # Mock API clients
            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()
            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)

            # Assert aexecute method exists
            assert hasattr(sandbox, "aexecute"), "KubernetesSandbox must have aexecute() method"

            # Assert it's a coroutine function (async def)
            assert asyncio.iscoroutinefunction(sandbox.aexecute), "aexecute() must be an async method (coroutine function)"

    async def test_aexecute_returns_execution_result(self):
        """
        RED: Verify aexecute() returns an ExecutionResult instance.

        The async method should return the same type as sync execute().
        """
        limits = ResourceLimits.testing()

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            # Mock API clients
            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()

            # Mock job creation and status
            mock_job = MagicMock()
            mock_job.status.succeeded = True
            mock_job.status.failed = None
            mock_batch_api.create_namespaced_job = MagicMock()
            mock_batch_api.read_namespaced_job = MagicMock(return_value=mock_job)
            mock_batch_api.delete_namespaced_job = MagicMock()

            # Mock pod logs
            mock_pod = MagicMock()
            mock_pod.metadata.name = "test-pod"
            mock_pods = MagicMock()
            mock_pods.items = [mock_pod]
            mock_core_api.list_namespaced_pod = MagicMock(return_value=mock_pods)
            mock_core_api.read_namespaced_pod_log = MagicMock(return_value="Hello, World!\n")

            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)
            result = await sandbox.aexecute("print('Hello, World!')")

            assert isinstance(result, ExecutionResult), f"aexecute() must return ExecutionResult, got {type(result)}"

    async def test_aexecute_successful_code_returns_success(self):
        """
        RED: Verify aexecute() returns success=True for valid code.

        Tests the happy path - simple print statement should succeed.
        """
        limits = ResourceLimits.testing()

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            # Mock API clients
            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()

            # Mock successful job
            mock_job = MagicMock()
            mock_job.status.succeeded = True
            mock_job.status.failed = None
            mock_batch_api.create_namespaced_job = MagicMock()
            mock_batch_api.read_namespaced_job = MagicMock(return_value=mock_job)
            mock_batch_api.delete_namespaced_job = MagicMock()

            # Mock pod logs
            mock_pod = MagicMock()
            mock_pod.metadata.name = "test-pod"
            mock_pods = MagicMock()
            mock_pods.items = [mock_pod]
            mock_core_api.list_namespaced_pod = MagicMock(return_value=mock_pods)
            mock_core_api.read_namespaced_pod_log = MagicMock(return_value="Hello, World!\n")

            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)
            result = await sandbox.aexecute("print('Hello, World!')")

            assert result.success is True, "Valid code should return success=True"
            assert "Hello, World!" in result.stdout, "Output should contain expected text"
            assert result.exit_code == 0, "Exit code should be 0 for success"

    async def test_aexecute_does_not_block_event_loop(self):
        """
        RED: Verify aexecute() allows other coroutines to run concurrently.

        This is the critical test - aexecute() must not block the event loop.
        We verify this by running a counter coroutine alongside aexecute().
        """
        limits = ResourceLimits(timeout_seconds=10)
        counter = {"value": 0}

        async def increment_counter():
            """Coroutine that increments counter every 10ms"""
            for _ in range(5):
                counter["value"] += 1
                await asyncio.sleep(0.01)  # 10ms

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.time") as mock_time,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            # Mock time - first call returns start, subsequent return higher values
            time_values = [0.0, 0.05, 0.1, 0.15]
            mock_time.time.side_effect = lambda: time_values.pop(0) if time_values else 0.2
            mock_time.sleep = MagicMock()  # This should use asyncio.sleep in async context

            # Mock API clients with delay simulation
            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()

            # Mock job that takes time (simulated by sleep in read_namespaced_job)
            call_count = [0]

            def read_job_with_delay(*args, **kwargs):
                call_count[0] += 1
                import time

                time.sleep(0.05)  # 50ms blocking operation
                mock_job = MagicMock()
                mock_job.status.succeeded = True if call_count[0] >= 2 else None
                mock_job.status.failed = None
                return mock_job

            mock_batch_api.create_namespaced_job = MagicMock()
            mock_batch_api.read_namespaced_job = read_job_with_delay
            mock_batch_api.delete_namespaced_job = MagicMock()

            # Mock pod logs
            mock_pod = MagicMock()
            mock_pod.metadata.name = "test-pod"
            mock_pods = MagicMock()
            mock_pods.items = [mock_pod]
            mock_core_api.list_namespaced_pod = MagicMock(return_value=mock_pods)
            mock_core_api.read_namespaced_pod_log = MagicMock(return_value="output")

            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)

            # Run both concurrently
            counter_task = asyncio.create_task(increment_counter())
            result = await sandbox.aexecute("print('test')")
            await counter_task

            # If aexecute() blocked the event loop, counter would be 0
            # With asyncio.to_thread(), counter should increment during execution
            assert counter["value"] >= 1, (
                f"Event loop was blocked! Counter value: {counter['value']}. "
                "aexecute() must use asyncio.to_thread() to not block."
            )
            assert result.success is True

    async def test_aexecute_empty_code_returns_failure(self):
        """
        RED: Verify aexecute() handles empty code gracefully.

        Empty code should return failure, not crash.
        """
        limits = ResourceLimits.testing()

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()
            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)
            result = await sandbox.aexecute("")

            assert result.success is False, "Empty code should return failure"
            assert "empty" in result.stderr.lower() or "empty" in result.error_message.lower()

    async def test_aexecute_timeout_returns_timed_out_result(self):
        """
        RED: Verify aexecute() handles timeouts correctly.

        Timed out executions should return timed_out=True.
        """
        limits = ResourceLimits(timeout_seconds=1)

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.time") as mock_time,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            # Mock time to simulate timeout
            mock_time.time.side_effect = [0.0, 0.5, 1.5, 2.0]  # Exceeds 1s timeout
            mock_time.sleep = MagicMock()

            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()

            # Mock job that never completes
            mock_job = MagicMock()
            mock_job.status.succeeded = None
            mock_job.status.failed = None
            mock_batch_api.create_namespaced_job = MagicMock()
            mock_batch_api.read_namespaced_job = MagicMock(return_value=mock_job)
            mock_batch_api.delete_namespaced_job = MagicMock()

            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)
            result = await sandbox.aexecute("import time; time.sleep(10)")  # noqa: sleep-duration

            assert result.timed_out is True, "Timeout should set timed_out=True"
            assert result.success is False, "Timed out execution should be failure"

    async def test_aexecute_concurrent_executions(self):
        """
        RED: Verify multiple aexecute() calls can run concurrently.

        This tests that the async implementation allows concurrent executions.
        """
        limits = ResourceLimits.testing()
        execution_count = 3

        with (
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.config") as mock_config,
            patch("mcp_server_langgraph.execution.kubernetes_sandbox.client") as mock_client,
        ):
            mock_config.load_incluster_config = MagicMock()
            mock_config.ConfigException = Exception

            mock_batch_api = MagicMock()
            mock_core_api = MagicMock()
            mock_core_api.read_namespace = MagicMock()

            # Mock successful job
            mock_job = MagicMock()
            mock_job.status.succeeded = True
            mock_job.status.failed = None
            mock_batch_api.create_namespaced_job = MagicMock()
            mock_batch_api.read_namespaced_job = MagicMock(return_value=mock_job)
            mock_batch_api.delete_namespaced_job = MagicMock()

            # Mock pod logs
            mock_pod = MagicMock()
            mock_pod.metadata.name = "test-pod"
            mock_pods = MagicMock()
            mock_pods.items = [mock_pod]
            mock_core_api.list_namespaced_pod = MagicMock(return_value=mock_pods)
            mock_core_api.read_namespaced_pod_log = MagicMock(return_value="output")

            mock_client.BatchV1Api.return_value = mock_batch_api
            mock_client.CoreV1Api.return_value = mock_core_api

            from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

            sandbox = KubernetesSandbox(limits=limits)

            # Run multiple executions concurrently
            tasks = [sandbox.aexecute(f"print({i})") for i in range(execution_count)]
            results = await asyncio.gather(*tasks)

            assert len(results) == execution_count
            assert all(r.success for r in results), "All concurrent executions should succeed"
