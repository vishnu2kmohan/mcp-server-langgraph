"""
Sandbox runner endpoint.

Provides a generic /api/v1/sandbox/run endpoint to execute high-risk
operations (starting with bash commands) inside the configured sandbox
backend (docker/k8s), keeping them out of the main app container.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.execution.sandbox_runner import (
    SandboxRunner,
    SandboxRunResult,
    get_sandbox_runner,
)
from mcp_server_langgraph.execution.sandbox import SandboxError

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


class SandboxRunRequest(BaseModel):
    """Request payload for sandbox operations."""

    type: str = Field(
        ...,
        description="Operation type. Supported: bash, web_fetch, write_file, edit_file, screenshot, computer_use",
    )
    command: str | None = Field(default=None, description="Command to execute (for bash)")
    timeout: int | None = Field(default=None, description="Optional timeout override in seconds")
    url: str | None = Field(default=None, description="URL for web_fetch")
    file_path: str | None = Field(default=None, description="Path for file ops")
    content: str | None = Field(default=None, description="Content for write_file")
    old_string: str | None = Field(default=None, description="Old string for edit_file replace")
    new_string: str | None = Field(default=None, description="New string for edit_file replace")
    replace_all: bool = Field(default=False, description="Replace all occurrences (edit_file)")
    payload: dict | None = Field(default=None, description="Additional payload for future operations")


class SandboxRunResponse(BaseModel):
    """Response payload for sandbox operations."""

    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    duration_ms: float | None = None
    timed_out: bool | None = None
    error: str | None = None


@router.post("/run")
async def run_sandbox(
    request: SandboxRunRequest,
    _user: CurrentUser,
) -> SandboxRunResponse:
    if not settings.enable_code_execution:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sandbox execution is disabled by configuration.",
        )

    runner: SandboxRunner = get_sandbox_runner()

    try:
        if request.type == "bash":
            if not request.command:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="command is required for bash operation",
                )
            result: SandboxRunResult = runner.run_bash(request.command, timeout_override=request.timeout)
        elif request.type == "web_fetch":
            if not request.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="url is required for web_fetch operation",
                )
            result = runner.run_web_fetch(
                request.url,
                timeout_override=request.timeout,
                max_bytes=(request.payload or {}).get("max_bytes"),
            )
        elif request.type == "write_file":
            if not request.file_path or request.content is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="file_path and content are required for write_file",
                )
            result = runner.run_write_file(request.file_path, request.content)
        elif request.type == "edit_file":
            if not request.file_path or request.old_string is None or request.new_string is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="file_path, old_string, new_string are required for edit_file",
                )
            result = runner.run_edit_file(
                request.file_path,
                request.old_string,
                request.new_string,
                request.replace_all,
            )
        elif request.type == "screenshot":
            payload = request.payload or {}
            if request.url:
                payload.setdefault("url", request.url)
            result = runner.run_screenshot(payload)
        elif request.type == "computer_use":
            result = runner.run_computer_use(
                request.payload.get("action") if request.payload else "unknown",
                request.payload or {},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported sandbox operation type.",
            )
    except SandboxError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox error: {exc}",
        ) from exc

    return SandboxRunResponse(
        stdout=result.stdout or None,
        stderr=result.stderr or None,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
        error=result.error_message,
    )
