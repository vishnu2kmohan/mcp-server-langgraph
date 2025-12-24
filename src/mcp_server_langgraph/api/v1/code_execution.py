"""
Code Execution Router

Exposes a thin REST wrapper over the sandboxed code execution backend
so the Studio Canvas can execute code server-side (Docker/K8s sandbox).
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
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

router = APIRouter(prefix="/code", tags=["code"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


class CodeExecutionRequest(BaseModel):
    """Request payload for sandboxed code execution."""

    language: str = Field(..., description="Programming language (currently python only)")
    code: str = Field(..., min_length=1, description="Source code to execute")
    runtime: Literal["sandbox", "pyodide", "auto"] = Field(
        default="sandbox",
        description="Execution runtime (sandbox executes on server; pyodide is client-side fallback)",
    )
    timeout: int | None = Field(default=None, description="Optional timeout override in seconds")


class CodeExecutionResponse(BaseModel):
    """Structured response for sandbox execution results."""

    runtime: Literal["sandbox"]
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    duration_ms: float | None = None
    timed_out: bool | None = None
    error: str | None = None


def _build_sandbox(timeout_override: int | None = None) -> Sandbox:
    """Construct a sandbox instance using settings and optional timeout override."""
    limits = ResourceLimits(
        timeout_seconds=timeout_override or settings.code_execution_timeout,
        memory_limit_mb=settings.code_execution_memory_limit_mb,
        cpu_quota=settings.code_execution_cpu_quota,
        disk_quota_mb=settings.code_execution_disk_quota_mb,
        max_processes=settings.code_execution_max_processes,
        network_mode=settings.code_execution_network_mode,  # type: ignore
        allowed_domains=tuple(settings.code_execution_allowed_domains),
    )

    backend = settings.code_execution_backend
    if backend == "docker-engine":
        return DockerSandbox(
            limits=limits,
            image=settings.code_execution_docker_image,
            socket_path=settings.code_execution_docker_socket,
        )
    if backend == "kubernetes":
        return KubernetesSandbox(
            limits=limits,
            namespace=settings.code_execution_k8s_namespace,
            image=settings.code_execution_docker_image,
            job_ttl=settings.code_execution_k8s_job_ttl,
        )

    raise SandboxError(f"Unsupported backend: {backend}")


@router.post("/execute")
async def execute_code(request: CodeExecutionRequest, current_user: CurrentUser) -> CodeExecutionResponse:
    """
    Execute code in the configured sandbox backend.

    Currently supports Python code execution; runtime must be "sandbox".
    """
    if not settings.enable_code_execution:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Code execution is disabled by server configuration",
        )

    if request.runtime != "sandbox":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only sandbox runtime is handled server-side; use pyodide in-browser instead.",
        )

    if request.language.lower() not in ("python", "py"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Python execution is supported in the server sandbox.",
        )

    # Validate code before execution
    validator = CodeValidator(allowed_imports=settings.code_execution_allowed_imports)
    validation = validator.validate(request.code)
    if not validation.is_valid:
        errors = "\n- ".join(validation.errors)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Code validation failed:\n- {errors}",
        )

    try:
        sandbox = _build_sandbox(timeout_override=request.timeout)
        result: ExecutionResult = sandbox.execute(request.code)
    except SandboxError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox error: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected execution error: {exc}",
        ) from exc

    return CodeExecutionResponse(
        runtime="sandbox",
        stdout=result.stdout or None,
        stderr=result.stderr or None,
        exit_code=result.exit_code,
        duration_ms=(result.execution_time * 1000.0) if result.execution_time else None,
        timed_out=result.timed_out,
        error=result.error_message or None,
    )
