"""
Write file tools for file creation and modification.

Provides WRITE file system access for the agent with security controls.
All operations are restricted to the workspace directory for security.
"""

import os
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics
from mcp_server_langgraph.execution.sandbox_runner import get_sandbox_runner, SandboxError

# Configuration constants (can be overridden via environment variables)
WRITE_FILE_MAX_SIZE_BYTES = int(os.getenv("WRITE_FILE_MAX_SIZE_BYTES", str(1024 * 1024)))  # 1MB default

# Allowed extensions for writing (security control)
WRITE_FILE_ALLOWED_EXTENSIONS = {
    ext.strip()
    for ext in os.getenv(
        "WRITE_FILE_ALLOWED_EXTENSIONS",
        ".py,.md,.txt,.json,.yaml,.yml,.toml,.csv,.xml,.html,.js,.ts,.css,.rst,.ini,.cfg",
    ).split(",")
}

# Dangerous extensions that are always blocked
DANGEROUS_EXTENSIONS = {".exe", ".sh", ".bat", ".cmd", ".ps1", ".dll", ".so", ".bin", ".run"}
SANDBOX_ENVIRONMENTS = {"test", "sandbox"}


def get_workspace_root() -> Path:
    """
    Get the workspace root directory.

    Returns the current working directory by default.
    Can be overridden via WORKSPACE_ROOT environment variable.

    Returns:
        Path to workspace root directory
    """
    workspace_root = os.getenv("WORKSPACE_ROOT")
    if workspace_root:
        return Path(workspace_root).resolve()
    return Path.cwd().resolve()


def _validate_path_security(file_path: str, workspace_root: Path) -> tuple[bool, str]:
    """
    Validate that a path is safe for writing.

    Args:
        file_path: The path to validate
        workspace_root: The workspace root to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(file_path)

        # Check for path traversal attempts
        if ".." in str(path):
            # Resolve and check if still in workspace
            resolved = (workspace_root / path).resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Path traversal detected - cannot write outside workspace"

        # Handle absolute paths
        if path.is_absolute():
            resolved = path.resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Absolute path outside workspace not allowed"
        else:
            resolved = (workspace_root / path).resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Path resolves outside workspace"

        # Block dangerous system paths
        dangerous_paths = [
            Path("/etc"),
            Path("/sys"),
            Path("/proc"),
            Path("/dev"),
            Path("/boot"),
            Path("/root"),
            Path.home() / ".ssh",
            Path.home() / ".aws",
            Path.home() / ".bashrc",
            Path.home() / ".bash_profile",
            Path.home() / ".profile",
        ]

        for dangerous in dangerous_paths:
            try:
                dangerous_resolved = dangerous.resolve()
                if str(resolved).startswith(str(dangerous_resolved)):
                    return False, f"Error: Cannot write to system path: {dangerous}"
            except (OSError, ValueError):
                continue

        return True, ""

    except Exception as e:
        return False, f"Error: Path validation failed: {e}"


def _validate_extension(file_path: Path) -> tuple[bool, str]:
    """
    Validate that the file extension is allowed.

    Args:
        file_path: Path to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    suffix = file_path.suffix.lower()

    # Always block dangerous extensions
    if suffix in DANGEROUS_EXTENSIONS:
        return False, f"Error: Extension '{suffix}' is blocked for security reasons"

    # If we have an allowlist, check against it
    # Only enforce allowlist if WRITE_FILE_ALLOWED_EXTENSIONS is explicitly set
    if WRITE_FILE_ALLOWED_EXTENSIONS and suffix not in WRITE_FILE_ALLOWED_EXTENSIONS:
        # Allow files without extension (like Makefile, Dockerfile)
        if suffix == "":
            return True, ""
        return False, f"Error: Extension '{suffix}' not in allowed list: {sorted(WRITE_FILE_ALLOWED_EXTENSIONS)}"

    return True, ""


def _validate_content_size(content: str) -> tuple[bool, str]:
    """
    Validate that content size is within limits.

    Args:
        content: Content to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    content_size = len(content.encode("utf-8"))
    if content_size > WRITE_FILE_MAX_SIZE_BYTES:
        return False, f"Error: Content size ({content_size} bytes) exceeds limit ({WRITE_FILE_MAX_SIZE_BYTES} bytes)"
    return True, ""


@tool
def write_file(
    file_path: Annotated[str, Field(description="Relative path within workspace to create or overwrite")],
    content: Annotated[str, Field(description="Content to write to the file")],
    create_directories: Annotated[bool, Field(description="Create parent directories if they don't exist")] = True,
) -> str:
    """
    Create a new file or overwrite an existing file with the given content.

    Security controls:
    - Path must be relative to workspace (no path traversal)
    - Content size limited to 1MB by default
    - Dangerous extensions (.exe, .sh, etc.) are blocked
    - Creates backup of existing files before overwriting

    Use this to:
    - Create new configuration files
    - Write output data
    - Generate code files

    SECURITY: Restricted to workspace directory, blocks dangerous paths.
    """
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return "Error: write_file is restricted to sandbox environments with code execution enabled."

    try:
        logger.info("Write file tool invoked", extra={"file_path": file_path})
        metrics.tool_calls.add(1, {"tool": "write_file"})

        workspace_root = get_workspace_root()

        is_valid, error_msg = _validate_path_security(file_path, workspace_root)
        if not is_valid:
            logger.warning("Path validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        # Resolve the final path
        path = Path(file_path)
        resolved_path = path.resolve() if path.is_absolute() else (workspace_root / path).resolve()

        # Validate extension
        is_valid, error_msg = _validate_extension(resolved_path)
        if not is_valid:
            logger.warning("Extension validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        is_valid, error_msg = _validate_content_size(content)
        if not is_valid:
            logger.warning("Content size validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        try:
            runner = get_sandbox_runner()
            result = runner.run_write_file(file_path, content, create_directories=create_directories)
        except SandboxError as exc:
            logger.error("Sandbox error writing file", extra={"file_path": file_path, "error": str(exc)})
            return f"Sandbox error: {exc}"

        output = result.stdout or ""
        if result.stderr:
            output = (output + "\n\nSTDERR:\n" + result.stderr) if output else result.stderr

        if not output:
            if result.exit_code == 0 and not result.timed_out:
                output = f"File write completed in sandbox: {file_path}"
            else:
                output = f"(sandbox exit code {result.exit_code})"

        if result.timed_out:
            output = f"Error: Sandbox write timed out after {settings.code_execution_timeout}s\n\n{output}"
        if result.error_message:
            output = f"Error: {result.error_message}\n\n{output}"

        return output

    except Exception as e:
        error_msg = f"Error writing file '{file_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
