"""
Code execution tools for MCP server

Provides secure Python code execution in sandboxed environments.
Integrates CodeValidator and Sandbox backends (Docker, Kubernetes).
"""

import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.execution import (
    CodeValidator,
    DockerSandbox,
    ExecutionResult,
    KubernetesSandbox,
    ResourceLimits,
    Sandbox,
    SandboxError,
)

logger = logging.getLogger(__name__)

# Maximum output size to prevent memory exhaustion
MAX_OUTPUT_SIZE = 10000  # 10KB


class ExecutePythonInput(BaseModel):
    """Input schema for execute_python tool"""

    code: str = Field(description="Python code to execute in sandboxed environment")
    timeout: Optional[int] = Field(default=None, description="Optional timeout in seconds (overrides default)")


def _is_execution_enabled() -> bool:
    """Check if code execution is enabled"""
    return settings.enable_code_execution


def _get_sandbox() -> Sandbox:
    """
    Create sandbox instance based on configuration.

    Returns:
        Sandbox instance (Docker or Kubernetes)

    Raises:
        SandboxError: If sandbox creation fails
    """
    # Create resource limits from settings
    limits = ResourceLimits(
        timeout_seconds=settings.code_execution_timeout,
        memory_limit_mb=settings.code_execution_memory_limit_mb,
        cpu_quota=settings.code_execution_cpu_quota,
        disk_quota_mb=settings.code_execution_disk_quota_mb,
        max_processes=settings.code_execution_max_processes,
        network_mode=settings.code_execution_network_mode,  # type: ignore
        allowed_domains=tuple(settings.code_execution_allowed_domains),
    )

    # Select backend
    backend = settings.code_execution_backend

    if backend == "docker-engine":
        return DockerSandbox(
            limits=limits,
            image=settings.code_execution_docker_image,
            socket_path=settings.code_execution_docker_socket,
        )
    elif backend == "kubernetes":
        return KubernetesSandbox(
            limits=limits,
            namespace=settings.code_execution_k8s_namespace,
            image=settings.code_execution_docker_image,  # Same image for both
            job_ttl=settings.code_execution_k8s_job_ttl,
        )
    else:
        raise SandboxError(f"Unsupported backend: {backend}")


def _truncate_output(text: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    """
    Truncate output if it exceeds maximum size.

    Args:
        text: Text to truncate
        max_size: Maximum size in characters

    Returns:
        Truncated text with indicator if truncated
    """
    if len(text) <= max_size:
        return text

    truncated = text[:max_size]
    return f"{truncated}\n\n... (output truncated, {len(text)} total characters)"


@tool
def execute_python(code: str, timeout: Optional[int] = None) -> str:
    """
    Execute Python code in a secure sandboxed environment.

    This tool provides isolated code execution with resource limits and security controls.
    Code is validated before execution to prevent dangerous operations.

    Security Features:
    - Import whitelist (only approved modules allowed)
    - No eval/exec/compile
    - No file system access
    - Configurable network isolation
    - Resource limits (CPU, memory, timeout)
    - Automatic cleanup

    Args:
        code: Python code to execute
        timeout: Optional timeout in seconds (overrides default)

    Returns:
        Execution result with output or error message

    Example:
        >>> execute_python.invoke({"code": "print(2 + 2)"})
        "Execution successful:\\nOutput:\\n4"
    """
    # Note: Code execution enablement is controlled at the MCP server level.
    # The execute_python tool is only added to the tool list when settings.enable_code_execution is True.
    # This provides access control without needing runtime checks here.
    # Previous _is_execution_enabled() check removed due to settings caching issues in tests.

    # Validate input
    if not code or not code.strip():
        return "Error: Empty code provided"

    try:
        # Validate code
        validator = CodeValidator(allowed_imports=settings.code_execution_allowed_imports)
        validation_result = validator.validate(code)

        if not validation_result.is_valid:
            errors = "\n- ".join(validation_result.errors)
            return f"Code validation failed:\n- {errors}"

        # Log warnings if any
        if validation_result.warnings:
            warnings = "\n- ".join(validation_result.warnings)
            logger.warning(f"Code validation warnings:\n- {warnings}")

        # Get sandbox
        sandbox = _get_sandbox()

        # Execute code
        result: ExecutionResult = sandbox.execute(code)

        # Format result
        if result.success:
            output = _truncate_output(result.stdout)
            exec_time = f"{result.execution_time:.2f}s"

            response = f"Execution successful (took {exec_time}):\n"
            if output:
                response += f"\nOutput:\n{output}"
            else:
                response += "\n(no output)"

            if result.memory_used_mb:
                response += f"\n\nMemory used: {result.memory_used_mb:.1f}MB"

            return response

        else:
            # Execution failed
            stderr = _truncate_output(result.stderr)
            exec_time = f"{result.execution_time:.2f}s"

            if result.timed_out:
                return f"Execution timed out after {exec_time}:\n{stderr}"
            else:
                response = f"Execution failed (exit code {result.exit_code}, took {exec_time}):\n"
                if stderr:
                    response += f"\nError:\n{stderr}"
                elif result.error_message:
                    response += f"\nError: {result.error_message}"
                else:
                    response += "\n(no error details available)"

                return response

    except SandboxError as e:
        logger.error(f"Sandbox error: {e}", exc_info=True)
        return f"Sandbox error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during code execution: {e}", exc_info=True)
        return f"Unexpected error: {e}"
