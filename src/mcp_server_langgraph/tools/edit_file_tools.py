"""
Edit file tools for precise file modifications.

Provides diff-based file editing for the agent with security controls.
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

# Configuration constants
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
    Validate that a path is safe for editing.

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
            resolved = (workspace_root / path).resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Path traversal detected - cannot edit outside workspace"

        # Handle absolute paths
        if path.is_absolute():
            resolved = path.resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Absolute path outside workspace not allowed"
        else:
            resolved = (workspace_root / path).resolve()
            if not str(resolved).startswith(str(workspace_root)):
                return False, "Error: Path resolves outside workspace"

        return True, ""

    except Exception as e:
        return False, f"Error: Path validation failed: {e}"


@tool
def edit_file(
    file_path: Annotated[str, Field(description="Path to the file to edit")],
    old_string: Annotated[str, Field(description="Exact text to find and replace")],
    new_string: Annotated[str, Field(description="Replacement text")],
    replace_all: Annotated[bool, Field(description="Replace all occurrences (default: replace only first)")] = False,
    create_backup: Annotated[bool, Field(description="Create .bak backup before editing")] = False,
) -> str:
    """
    Make precise edits to an existing file by replacing text in the sandbox.

    Use this to:
    - Make targeted code changes
    - Update configuration values
    - Fix specific text in files

    Security controls:
    - Path must be relative to workspace (no path traversal)
    - Optionally creates backup of file before editing

    SECURITY: Delegated to the sandbox runner (Docker/K8s).
    """
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return "Error: edit_file is restricted to sandbox environments with code execution enabled."

    try:
        logger.info(
            "Edit file tool invoked",
            extra={
                "file_path": file_path,
                "old_string_len": len(old_string),
                "new_string_len": len(new_string),
                "replace_all": replace_all,
            },
        )
        metrics.tool_calls.add(1, {"tool": "edit_file"})

        if not old_string:
            return "Error: old_string cannot be empty"

        workspace_root = get_workspace_root()

        is_valid, error_msg = _validate_path_security(file_path, workspace_root)
        if not is_valid:
            logger.warning("Path validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        # Resolve the file path for backup
        path = Path(file_path)
        resolved_path = path.resolve() if path.is_absolute() else (workspace_root / path).resolve()

        # Create backup if requested and file exists
        if create_backup and resolved_path.exists():
            try:
                backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")
                original_content = resolved_path.read_text(encoding="utf-8")
                backup_path.write_text(original_content, encoding="utf-8")
                logger.info(
                    "Created backup before edit",
                    extra={"original": str(resolved_path), "backup": str(backup_path)},
                )
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}", extra={"file_path": file_path})
                # Continue with edit even if backup fails - backup is optional safety feature

        try:
            runner = get_sandbox_runner()
            result = runner.run_edit_file(file_path, old_string, new_string, replace_all)
        except SandboxError as exc:
            logger.error("Sandbox error editing file", extra={"file_path": file_path, "error": str(exc)})
            return f"Sandbox error: {exc}"

        output = result.stdout or ""
        if result.stderr:
            output = (output + "\n\nSTDERR:\n" + result.stderr) if output else result.stderr

        if not output:
            if result.exit_code == 0 and not result.timed_out:
                output = f"Edit completed in sandbox for {file_path}"
            else:
                output = f"(sandbox exit code {result.exit_code})"

        if result.timed_out:
            output = f"Error: Sandbox edit timed out after {settings.code_execution_timeout}s\n\n{output}"
        if result.error_message:
            output = f"Error: {result.error_message}\n\n{output}"

        return output

    except Exception as e:
        error_msg = f"Error editing file '{file_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
