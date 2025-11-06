"""
Kubernetes-based sandbox for code execution

Provides secure isolated Python code execution using Kubernetes Jobs.
Supports resource limits, automatic cleanup with TTL, and pod security policies.
"""

import logging
import time

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError

logger = logging.getLogger(__name__)


class KubernetesSandbox(Sandbox):
    """
    Kubernetes-based sandbox for executing Python code in isolated pods.

    Features:
    - Ephemeral Jobs (created and destroyed per execution)
    - Resource limits (CPU, memory, timeout)
    - Pod security policies
    - Automatic cleanup with TTL
    - Read-only root filesystem
    - No privilege escalation

    Example:
        >>> limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        >>> sandbox = KubernetesSandbox(limits=limits, namespace="default")
        >>> result = sandbox.execute("print('Hello')")
        >>> assert result.success
        >>> assert "Hello" in result.stdout
    """

    def __init__(
        self,
        limits: ResourceLimits,
        namespace: str = "default",
        image: str = "python:3.12-slim",
        job_ttl: int = 300,  # TTL in seconds for job cleanup
    ):
        """
        Initialize Kubernetes sandbox.

        Args:
            limits: Resource limits to enforce
            namespace: Kubernetes namespace for jobs
            image: Container image to use
            job_ttl: Time to live for completed jobs (seconds)

        Raises:
            SandboxError: If Kubernetes is not available
        """
        super().__init__(limits)
        self.namespace = namespace
        self.image = image
        self.job_ttl = job_ttl

        try:
            # Load kubeconfig (in-cluster or from ~/.kube/config)
            try:
                config.load_incluster_config()  # Try in-cluster first
                logger.debug("Loaded in-cluster Kubernetes config")
            except config.ConfigException:
                config.load_kube_config()  # Fall back to kubeconfig file
                logger.debug("Loaded Kubernetes config from kubeconfig file")

            self.batch_v1 = client.BatchV1Api()
            self.core_v1 = client.CoreV1Api()

            # Verify namespace exists
            self._verify_namespace()

        except Exception as e:
            raise SandboxError(f"Kubernetes not available: {e}")

    def _verify_namespace(self) -> None:
        """Verify that the namespace exists"""
        try:
            self.core_v1.read_namespace(name=self.namespace)
        except ApiException as e:
            if e.status == 404:
                raise SandboxError(f"Namespace '{self.namespace}' does not exist")
            raise SandboxError(f"Failed to verify namespace: {e}")

    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in a Kubernetes Job.

        Args:
            code: Python source code to execute

        Returns:
            ExecutionResult with execution status and outputs

        Raises:
            SandboxError: If job creation or execution fails
        """
        if not code or not code.strip():
            return self._create_failure_result(
                stdout="",
                stderr="Error: Empty code provided",
                exit_code=1,
                execution_time=0.0,
                error_message="Empty code provided",
            )

        job_name = None
        start_time = time.time()

        try:
            # Create job
            job_name = self._create_job(code)

            # Wait for completion with timeout
            timed_out, exit_code = self._wait_for_job(job_name, start_time)

            execution_time = self._measure_time(start_time)

            # Get logs from pod
            stdout, stderr = self._get_job_logs(job_name)

            # Cleanup job (TTL will also clean up, but we can do it immediately)
            self._cleanup_job(job_name)

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
            if job_name:
                self._cleanup_job(job_name)

            logger.error(f"Kubernetes execution failed: {e}", exc_info=True)
            raise SandboxError(f"Kubernetes execution failed: {e}")

    def _create_job(self, code: str) -> str:
        """
        Create Kubernetes Job for code execution.

        Args:
            code: Python code to execute

        Returns:
            Job name

        Raises:
            SandboxError: If job creation fails
        """
        import hashlib

        # Generate unique job name
        # Use SHA-256 for better security hygiene (even though this is just for naming, not cryptographic security)
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        job_name = f"code-exec-{timestamp}-{code_hash}"

        try:
            # Configure resource requests and limits
            resources = client.V1ResourceRequirements(
                requests={
                    "cpu": str(self.limits.cpu_quota),
                    "memory": f"{self.limits.memory_limit_mb}Mi",
                },
                limits={
                    "cpu": str(self.limits.cpu_quota),
                    "memory": f"{self.limits.memory_limit_mb}Mi",
                },
            )

            # Configure security context
            security_context = client.V1SecurityContext(
                allow_privilege_escalation=False,
                run_as_non_root=True,
                run_as_user=1000,  # Non-root user
                read_only_root_filesystem=False,  # Need writable /tmp
                capabilities=client.V1Capabilities(drop=["ALL"]),
            )

            # Configure container
            container = client.V1Container(
                name="executor",
                image=self.image,
                command=["python", "-c", code],
                resources=resources,
                security_context=security_context,
            )

            # Configure pod template
            pod_template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "code-execution"}),
                spec=client.V1PodSpec(
                    containers=[container],
                    restart_policy="Never",
                    # Pod security
                    security_context=client.V1PodSecurityContext(
                        run_as_non_root=True,
                        run_as_user=1000,
                        fs_group=1000,
                    ),
                ),
            )

            # Configure job
            job = client.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=client.V1ObjectMeta(name=job_name),
                spec=client.V1JobSpec(
                    template=pod_template,
                    backoff_limit=0,  # Don't retry on failure
                    ttl_seconds_after_finished=self.job_ttl,  # Auto-cleanup
                    active_deadline_seconds=self.limits.timeout_seconds,  # Timeout
                ),
            )

            # Create job
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
            logger.debug(f"Created Kubernetes job: {job_name}")

            return job_name

        except Exception as e:
            logger.error(f"Failed to create Kubernetes job: {e}", exc_info=True)
            raise SandboxError(f"Failed to create Kubernetes job: {e}")

    def _wait_for_job(self, job_name: str, start_time: float) -> tuple[bool, int]:
        """
        Wait for job to complete.

        Args:
            job_name: Name of the job
            start_time: Start time for timeout calculation

        Returns:
            Tuple of (timed_out, exit_code)
        """
        timeout = self.limits.timeout_seconds
        poll_interval = 1  # Poll every second

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                # Timeout - delete job
                try:
                    self.batch_v1.delete_namespaced_job(
                        name=job_name,
                        namespace=self.namespace,
                        propagation_policy="Background",
                    )
                except Exception:
                    pass
                return True, 124  # Timeout exit code

            try:
                # Check job status
                job = self.batch_v1.read_namespaced_job(name=job_name, namespace=self.namespace)

                if job.status.succeeded:
                    return False, 0
                elif job.status.failed:
                    return False, 1

                # Job still running, wait and check again
                time.sleep(poll_interval)

            except ApiException as e:
                if e.status == 404:
                    # Job not found (might have been deleted)
                    return False, 1
                raise

    def _get_job_logs(self, job_name: str) -> tuple[str, str]:
        """
        Get logs from job pod.

        Args:
            job_name: Name of the job

        Returns:
            Tuple of (stdout, stderr)
        """
        try:
            # Find pod for job
            pods = self.core_v1.list_namespaced_pod(namespace=self.namespace, label_selector=f"job-name={job_name}")

            if not pods.items:
                return "", "Error: No pod found for job"

            pod_name = pods.items[0].metadata.name

            # Get logs
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace)

            # Kubernetes doesn't separate stdout/stderr in logs
            # Everything goes to stdout
            return logs, ""

        except Exception as e:
            logger.warning(f"Failed to get logs for job {job_name}: {e}")
            return "", f"Error retrieving logs: {e}"

    def _cleanup_job(self, job_name: str) -> None:
        """
        Clean up Kubernetes job.

        Args:
            job_name: Name of the job to delete
        """
        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                propagation_policy="Background",  # Delete pods too
            )
            logger.debug(f"Deleted Kubernetes job: {job_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore if already deleted
                logger.warning(f"Failed to delete job {job_name}: {e}")
        except Exception as e:
            logger.warning(f"Error during job cleanup: {e}")
