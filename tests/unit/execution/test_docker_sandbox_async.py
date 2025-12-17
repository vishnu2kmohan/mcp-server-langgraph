"""
TDD RED Phase: Tests for Docker sandbox async execution.

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

# Docker is an optional dependency - skip tests if not available
try:
    from docker.errors import ImageNotFound, NotFound

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    ImageNotFound = Exception  # type: ignore[misc, assignment]
    NotFound = Exception  # type: ignore[misc, assignment]

from mcp_server_langgraph.execution import docker_sandbox
from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult, SandboxError

pytestmark = pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not installed")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="docker_sandbox_async")
class TestDockerSandboxAsyncExecute:
    """
    TDD tests for DockerSandbox.aexecute() - async non-blocking execution.

    These tests verify that:
    1. aexecute() exists and is an async method
    2. aexecute() returns correct ExecutionResult
    3. aexecute() does not block the event loop
    4. aexecute() propagates timeouts and errors correctly

    PYTEST-XDIST FIX (2025-12-16):
    ==============================
    Added setup_method to reset singleton state and clear any polluted mocks
    from other xdist workers (e.g., GCP/Vertex AI tests that mock global state).
    """

    def setup_method(self) -> None:
        """Reset state to prevent xdist pollution.

        PYTEST-XDIST FIX (2025-12-16):
        Reset singleton dependencies before each test. Note: We don't reload
        modules here as that can interfere with patch.object() in tests.
        """
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_aexecute_method_exists_and_is_async(self):
        """
        RED: Verify aexecute() method exists and is a coroutine function.

        This is the basic contract test - aexecute() must be async.
        """
        limits = ResourceLimits.testing()

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = MagicMock()
            mock_client.images.get = MagicMock()
            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)

            # Assert aexecute method exists
            assert hasattr(sandbox, "aexecute"), "DockerSandbox must have aexecute() method"

            # Assert it's a coroutine function (async def)
            assert asyncio.iscoroutinefunction(sandbox.aexecute), "aexecute() must be an async method (coroutine function)"

    async def test_aexecute_returns_execution_result(self):
        """
        RED: Verify aexecute() returns an ExecutionResult instance.

        The async method should return the same type as sync execute().

        PYTEST-XDIST FIX (2025-12-16):
        Use lambda functions instead of MagicMock for return values to prevent
        mock pollution from other tests in xdist workers.
        """
        limits = ResourceLimits.testing()

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = lambda: None
            mock_client.images.get = lambda *args: MagicMock()

            # Mock container operations - use lambdas to prevent xdist pollution
            mock_container = MagicMock()
            mock_container.start = lambda: None
            mock_container.wait = lambda **kwargs: {"StatusCode": 0}
            mock_container.logs = lambda **kwargs: b"Hello, World!\n"
            mock_container.stats = lambda **kwargs: {}
            mock_container.remove = lambda **kwargs: None
            mock_container.reload = lambda: None
            mock_container.status = "exited"
            mock_client.containers.create = lambda **kwargs: mock_container

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)
            result = await sandbox.aexecute("print('Hello, World!')")

            assert isinstance(result, ExecutionResult), f"aexecute() must return ExecutionResult, got {type(result)}"

    async def test_aexecute_successful_code_returns_success(self):
        """
        RED: Verify aexecute() returns success=True for valid code.

        Tests the happy path - simple print statement should succeed.

        PYTEST-XDIST FIX (2025-12-16):
        Use lambda functions instead of MagicMock for return values to prevent
        mock pollution from other tests in xdist workers. MagicMock's auto-attribute
        creation can leak state across tests.
        """
        limits = ResourceLimits.testing()

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = MagicMock()
            mock_client.images.get = MagicMock()

            # Mock successful execution - use lambda to avoid MagicMock return_value pollution
            mock_container = MagicMock()
            mock_container.start = MagicMock()
            mock_container.wait = lambda **kwargs: {"StatusCode": 0}
            mock_container.logs = lambda **kwargs: b"Hello, World!\n"
            mock_container.stats = lambda **kwargs: {}
            mock_container.remove = MagicMock()
            mock_container.reload = MagicMock()
            mock_container.status = "exited"
            mock_client.containers.create = lambda **kwargs: mock_container

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)
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

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = MagicMock()
            mock_client.images.get = MagicMock()

            # Mock execution that takes 100ms (simulated)
            def slow_wait(timeout=None):
                import time

                time.sleep(0.1)  # 100ms blocking operation
                return {"StatusCode": 0}

            # PYTEST-XDIST FIX (2025-12-16): Use lambdas instead of MagicMock return_value
            # to prevent mock pollution from leaking between xdist workers
            mock_container = MagicMock()
            mock_container.start = lambda: None
            mock_container.wait = slow_wait
            mock_container.logs = lambda **kwargs: b"output"
            mock_container.stats = lambda **kwargs: {}
            mock_container.remove = lambda **kwargs: None
            mock_container.reload = lambda: None
            mock_container.status = "exited"
            mock_client.containers.create = lambda **kwargs: mock_container

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)

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

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = MagicMock()
            mock_client.images.get = MagicMock()
            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)
            result = await sandbox.aexecute("")

            assert result.success is False, "Empty code should return failure"
            assert "empty" in result.stderr.lower() or "empty" in result.error_message.lower()

    async def test_aexecute_failed_code_returns_failure(self):
        """
        RED: Verify aexecute() returns success=False for code that errors.

        Tests error handling for code that raises exceptions.

        PYTEST-XDIST FIX (2025-12-16):
        Use lambda functions instead of MagicMock for return values to prevent
        mock pollution from other tests in xdist workers.
        """
        limits = ResourceLimits.testing()

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = lambda: None
            mock_client.images.get = lambda *args: MagicMock()

            # Mock failed execution (non-zero exit code) - use lambdas
            mock_container = MagicMock()
            mock_container.start = lambda: None
            mock_container.wait = lambda **kwargs: {"StatusCode": 1}
            mock_container.logs = lambda **kwargs: b"Traceback (most recent call last):\nRuntimeError: test error"
            mock_container.stats = lambda **kwargs: {}
            mock_container.remove = lambda **kwargs: None
            mock_container.reload = lambda: None
            mock_container.status = "exited"
            mock_client.containers.create = lambda **kwargs: mock_container

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)
            result = await sandbox.aexecute("raise RuntimeError('test error')")

            assert result.success is False, "Error code should return success=False"
            assert result.exit_code != 0, "Exit code should be non-zero for errors"

    async def test_aexecute_timeout_returns_timed_out_result(self):
        """
        RED: Verify aexecute() handles timeouts correctly.

        Timed out executions should return timed_out=True.

        PYTEST-XDIST FIX (2025-12-16):
        Use lambda functions instead of MagicMock for return values to prevent
        mock pollution from other tests in xdist workers.
        """
        limits = ResourceLimits(timeout_seconds=1)

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = lambda: None
            mock_client.images.get = lambda *args: MagicMock()

            # Mock timeout (wait raises exception) - use lambdas
            def raise_timeout(**kwargs):
                raise Exception("Timeout")

            mock_container = MagicMock()
            mock_container.start = lambda: None
            mock_container.wait = raise_timeout
            mock_container.stop = lambda **kwargs: None
            mock_container.kill = lambda **kwargs: None
            mock_container.logs = lambda **kwargs: b""
            mock_container.remove = lambda **kwargs: None
            mock_container.reload = lambda: None
            mock_container.status = "running"
            mock_client.containers.create = lambda **kwargs: mock_container

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)
            result = await sandbox.aexecute("import time; time.sleep(10)")  # noqa: sleep-duration

            assert result.timed_out is True, "Timeout should set timed_out=True"
            assert result.success is False, "Timed out execution should be failure"

    async def test_aexecute_propagates_sandbox_error(self):
        """
        RED: Verify aexecute() propagates SandboxError exceptions.

        Sandbox setup failures should raise SandboxError.
        """
        limits = ResourceLimits.testing()

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = MagicMock()
            mock_client.images.get = MagicMock()

            # Mock container creation failure
            mock_client.containers.create = MagicMock(side_effect=Exception("Container creation failed"))

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)

            with pytest.raises(SandboxError):
                await sandbox.aexecute("print('test')")

    async def test_aexecute_concurrent_executions(self):
        """
        RED: Verify multiple aexecute() calls can run concurrently.

        This tests that the async implementation allows concurrent executions.

        PYTEST-XDIST FIX (2025-12-16):
        Use lambda functions instead of MagicMock for return values to prevent
        mock pollution from other tests in xdist workers.
        """
        limits = ResourceLimits.testing()
        execution_count = 3

        with patch.object(docker_sandbox.docker, "DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.ping = lambda: None
            mock_client.images.get = lambda *args: MagicMock()

            # Mock successful execution - use lambdas to prevent xdist pollution
            def create_mock_container():
                mock_container = MagicMock()
                mock_container.start = lambda: None
                mock_container.wait = lambda **kwargs: {"StatusCode": 0}
                mock_container.logs = lambda **kwargs: b"output"
                mock_container.stats = lambda **kwargs: {}
                mock_container.remove = lambda **kwargs: None
                mock_container.reload = lambda: None
                mock_container.status = "exited"
                return mock_container

            mock_client.containers.create = lambda **kwargs: create_mock_container()

            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)

            # Run multiple executions concurrently
            tasks = [sandbox.aexecute(f"print({i})") for i in range(execution_count)]
            results = await asyncio.gather(*tasks)

            assert len(results) == execution_count
            assert all(r.success for r in results), "All concurrent executions should succeed"
