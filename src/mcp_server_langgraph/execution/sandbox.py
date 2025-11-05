"""
Abstract sandbox interface for secure code execution

Defines the contract for all sandbox implementations (Docker, Kubernetes, Process).
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


class SandboxError(Exception):
    """Raised when sandbox operations fail"""

    pass


@dataclass
class ExecutionResult:
    """
    Result of code execution in a sandbox.

    Attributes:
        success: True if code executed without errors
        stdout: Standard output from execution
        stderr: Standard error from execution
        exit_code: Process exit code (0 = success)
        execution_time: Time taken in seconds
        timed_out: True if execution was terminated due to timeout
        memory_used_mb: Peak memory usage in MB (if available)
        error_message: Human-readable error message (if failed)
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    timed_out: bool = False
    memory_used_mb: Optional[float] = None
    error_message: str = ""

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        if self.timed_out:
            status = "TIMEOUT"
        return f"ExecutionResult(status={status}, exit_code={self.exit_code}, time={self.execution_time:.2f}s)"


class Sandbox(ABC):
    """
    Abstract base class for code execution sandboxes.

    All sandbox implementations (Docker, Kubernetes, Process) must inherit from this
    class and implement the execute() method.

    Example:
        >>> sandbox = DockerSandbox(limits=ResourceLimits.testing())
        >>> result = sandbox.execute("print('Hello, World!')")
        >>> assert result.success
        >>> assert "Hello, World!" in result.stdout
    """

    def __init__(self, limits: "ResourceLimits"):
        """
        Initialize sandbox with resource limits.

        Args:
            limits: Resource limits to enforce (timeout, memory, CPU, etc.)
        """
        self.limits = limits

    @abstractmethod
    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in the sandbox.

        This method must be implemented by all sandbox subclasses.

        Args:
            code: Python source code to execute

        Returns:
            ExecutionResult with execution status and outputs

        Raises:
            SandboxError: If sandbox setup or execution fails
        """
        pass

    def _create_success_result(
        self,
        stdout: str,
        stderr: str,
        execution_time: float,
        memory_used_mb: Optional[float] = None,
    ) -> ExecutionResult:
        """Helper to create successful execution result"""
        return ExecutionResult(
            success=True,
            stdout=stdout,
            stderr=stderr,
            exit_code=0,
            execution_time=execution_time,
            timed_out=False,
            memory_used_mb=memory_used_mb,
        )

    def _create_failure_result(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        execution_time: float,
        timed_out: bool = False,
        error_message: str = "",
    ) -> ExecutionResult:
        """Helper to create failed execution result"""
        return ExecutionResult(
            success=False,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time=execution_time,
            timed_out=timed_out,
            error_message=error_message,
        )

    def _measure_time(self, start_time: float) -> float:
        """Helper to measure execution time"""
        return time.time() - start_time
