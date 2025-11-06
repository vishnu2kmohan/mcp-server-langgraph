"""
Docker-based sandbox for code execution

Provides secure isolated Python code execution using Docker containers.
Supports resource limits, network isolation, and automatic cleanup.
"""

import logging
import time

from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container

import docker
from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError

logger = logging.getLogger(__name__)


class DockerSandbox(Sandbox):
    """
    Docker-based sandbox for executing Python code in isolated containers.

    Features:
    - Ephemeral containers (created and destroyed per execution)
    - Resource limits (CPU, memory, timeout)
    - Network isolation (none/allowlist/unrestricted)
    - Read-only root filesystem
    - No privilege escalation
    - Automatic cleanup

    Example:
        >>> limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        >>> sandbox = DockerSandbox(limits=limits)
        >>> result = sandbox.execute("print('Hello')")
        >>> assert result.success
        >>> assert "Hello" in result.stdout
    """

    def __init__(
        self,
        limits: ResourceLimits,
        image: str = "python:3.12-slim",
        socket_path: str = "/var/run/docker.sock",
    ):
        """
        Initialize Docker sandbox.

        Args:
            limits: Resource limits to enforce
            image: Docker image to use (default: python:3.12-slim)
            socket_path: Path to Docker socket

        Raises:
            SandboxError: If Docker is not available
        """
        super().__init__(limits)
        self.image = image
        self.socket_path = socket_path

        try:
            self.client = docker.DockerClient(base_url=f"unix://{socket_path}")
            # Test connection
            self.client.ping()
        except Exception as e:
            raise SandboxError(f"Docker not available: {e}")

        # Ensure image exists
        self._ensure_image()

    def _ensure_image(self) -> None:
        """Ensure Docker image is available, pull if necessary"""
        try:
            self.client.images.get(self.image)
            logger.debug(f"Docker image {self.image} already available")
        except ImageNotFound:
            logger.info(f"Pulling Docker image {self.image}...")
            try:
                self.client.images.pull(self.image)
                logger.info(f"Successfully pulled {self.image}")
            except Exception as e:
                raise SandboxError(f"Failed to pull Docker image {self.image}: {e}")

    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in a Docker container.

        Args:
            code: Python source code to execute

        Returns:
            ExecutionResult with execution status and outputs

        Raises:
            SandboxError: If container creation or execution fails
        """
        if not code or not code.strip():
            return self._create_failure_result(
                stdout="",
                stderr="Error: Empty code provided",
                exit_code=1,
                execution_time=0.0,
                error_message="Empty code provided",
            )

        container = None
        start_time = time.time()

        try:
            # Create container with resource limits
            container = self._create_container(code)

            # Start container
            container.start()

            # Wait for completion with timeout
            timed_out = False
            try:
                exit_code = container.wait(timeout=self.limits.timeout_seconds)
                if isinstance(exit_code, dict):
                    exit_code = exit_code.get("StatusCode", 1)
            except Exception:
                # Timeout occurred
                timed_out = True
                exit_code = 124  # Standard timeout exit code

                # Stop container
                try:
                    container.stop(timeout=1)
                except Exception:
                    container.kill()

            execution_time = self._measure_time(start_time)

            # Get logs
            try:
                logs = container.logs(stdout=True, stderr=True).decode("utf-8")
                # Docker combines stdout and stderr
                # Separate them based on content
                if exit_code != 0 and not timed_out:
                    # If there was an error, look for Python error output
                    if "Traceback" in logs or "Error" in logs or "SyntaxError" in logs:
                        # Put error output in stderr
                        stderr = logs
                        stdout = ""
                    else:
                        # No traceback, might be a simple error
                        stderr = logs
                        stdout = ""
                else:
                    # Success - everything is stdout
                    stdout = logs
                    stderr = ""
            except Exception as e:
                stdout = ""
                stderr = f"Error retrieving logs: {e}"

            # Get memory usage (if available)
            memory_used_mb = None
            try:
                stats = container.stats(stream=False)
                if "memory_stats" in stats and "max_usage" in stats["memory_stats"]:
                    memory_used_mb = stats["memory_stats"]["max_usage"] / (1024 * 1024)
            except Exception:
                pass  # Memory stats not critical

            # Cleanup container
            self._cleanup_container(container)

            # Create result
            if timed_out:
                return self._create_failure_result(
                    stdout=stdout,
                    stderr=stderr or f"Execution timed out after {self.limits.timeout_seconds}s",
                    exit_code=exit_code,
                    execution_time=execution_time,
                    timed_out=True,
                    error_message=f"Timeout after {self.limits.timeout_seconds}s",
                )
            elif exit_code == 0:
                return self._create_success_result(
                    stdout=stdout,
                    stderr=stderr,
                    execution_time=execution_time,
                    memory_used_mb=memory_used_mb,
                )
            else:
                return self._create_failure_result(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    error_message=f"Process exited with code {exit_code}",
                )

        except Exception as e:
            execution_time = self._measure_time(start_time)

            # Cleanup on error
            if container:
                self._cleanup_container(container)

            logger.error(f"Docker execution failed: {e}", exc_info=True)
            raise SandboxError(f"Docker execution failed: {e}")

    def _create_container(self, code: str) -> Container:
        """
        Create Docker container with resource limits and security settings.

        Args:
            code: Python code to execute

        Returns:
            Docker container (not started)

        Raises:
            SandboxError: If container creation fails
        """
        try:
            # Configure resource limits
            mem_limit = f"{self.limits.memory_limit_mb}m"
            nano_cpus = int(self.limits.cpu_quota * 1_000_000_000)  # Convert to nano CPUs

            # Configure network
            network_mode = self._get_network_mode()

            # Create container
            # Note: We don't use auto_remove=True because we need to get logs after execution
            container = self.client.containers.create(
                image=self.image,
                command=["python", "-c", code],
                detach=True,
                mem_limit=mem_limit,
                memswap_limit=mem_limit,  # Disable swap
                nano_cpus=nano_cpus,
                network_mode=network_mode,
                network_disabled=(network_mode == "none"),
                read_only=True,  # Read-only root FS for security (OpenAI Codex Finding #4)
                security_opt=["no-new-privileges"],  # Prevent privilege escalation
                cap_drop=["ALL"],  # Drop all capabilities
                pids_limit=self.limits.max_processes,
                # Tmpfs for writable directories (ephemeral, in-memory)
                # Python needs /tmp and /var/tmp for tempfile module
                tmpfs={  # nosec B108 - tmpfs is ephemeral in-memory, not persistent storage
                    "/tmp": f"size={self.limits.disk_quota_mb}m",  # nosec B108
                    "/var/tmp": f"size={self.limits.disk_quota_mb}m",  # nosec B108
                },
            )

            return container

        except Exception as e:
            logger.error(f"Failed to create Docker container: {e}", exc_info=True)
            raise SandboxError(f"Failed to create Docker container: {e}")

    def _get_network_mode(self) -> str:
        """
        Get Docker network mode from resource limits.

        Returns:
            Docker network mode string
        """
        if self.limits.network_mode == "none":
            return "none"
        elif self.limits.network_mode == "unrestricted":
            return "bridge"  # Default Docker network
        elif self.limits.network_mode == "allowlist":
            # WARNING (OpenAI Codex Finding #4): Network allowlist mode is NOT fully implemented!
            # For proper security, this requires:
            # 1. Docker network policies or firewall rules (iptables/nftables)
            # 2. DNS filtering to resolve allowed domains to IPs
            # 3. egress filtering to block unlisted destinations
            #
            # Current behavior: Falls back to bridge (unrestricted) if domains are specified
            # For production use, consider using network_mode="none" until this is implemented
            if not self.limits.allowed_domains:
                return "none"
            else:
                # TODO: Implement proper allowlist with network policies
                logger.warning(
                    "Network allowlist mode requested but not fully implemented. "
                    "Using bridge network (unrestricted). For security, use network_mode='none'"
                )
                return "bridge"
        else:
            return "none"  # Fail closed

    def _cleanup_container(self, container: Container) -> None:
        """
        Clean up Docker container.

        Args:
            container: Container to remove
        """
        try:
            # Stop container if still running
            try:
                container.reload()  # Refresh container state
                if container.status == "running":
                    container.stop(timeout=1)
            except NotFound:
                pass  # Already removed
            except Exception:
                # Force kill if stop fails
                try:
                    container.kill()
                except Exception:
                    pass

            # Remove container
            try:
                container.remove(force=True)
                logger.debug(f"Removed container {container.id[:12]}")
            except NotFound:
                pass  # Already removed
            except Exception as e:
                logger.warning(f"Failed to remove container {container.id[:12]}: {e}")

        except Exception as e:
            logger.warning(f"Error during container cleanup: {e}")

    def __del__(self) -> None:
        """Cleanup on garbage collection"""
        try:
            if hasattr(self, "client"):
                self.client.close()
        except Exception:
            pass
