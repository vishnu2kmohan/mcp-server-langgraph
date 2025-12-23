"""
Write file tools for file creation and modification.

Provides WRITE file system access for the agent with security controls.
All operations are restricted to the workspace directory for security.
"""

import os
import shutil
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.observability.telemetry import logger, metrics

# Configuration constants (can be overridden via environment variables)
WRITE_FILE_MAX_SIZE_BYTES = int(os.getenv("WRITE_FILE_MAX_SIZE_BYTES", str(1024 * 1024)))  # 1MB default
WRITE_FILE_CREATE_BACKUP = os.getenv("WRITE_FILE_CREATE_BACKUP", "true").lower() == "true"

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


def _create_backup(file_path: Path) -> Path | None:
    """
    Create a backup of an existing file.

    Args:
        file_path: Path to the file to backup

    Returns:
        Path to backup file, or None if no backup was created
    """
    if not file_path.exists():
        return None

    backup_path = file_path.parent / f"{file_path.name}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info("Backup created", extra={"original": str(file_path), "backup": str(backup_path)})
        return backup_path
    except Exception as e:
        logger.warning("Failed to create backup", extra={"file_path": str(file_path), "error": str(e)})
        return None


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
    try:
        logger.info("Write file tool invoked", extra={"file_path": file_path})
        metrics.tool_calls.add(1, {"tool": "write_file"})

        workspace_root = get_workspace_root()

        # Validate path security
        is_valid, error_msg = _validate_path_security(file_path, workspace_root)
        if not is_valid:
            logger.warning("Path validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        # Resolve the final path
        path = Path(file_path)
        if path.is_absolute():
            resolved_path = path.resolve()
        else:
            resolved_path = (workspace_root / path).resolve()

        # Validate extension
        is_valid, error_msg = _validate_extension(resolved_path)
        if not is_valid:
            logger.warning("Extension validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        # Validate content size
        is_valid, error_msg = _validate_content_size(content)
        if not is_valid:
            logger.warning("Content size validation failed", extra={"file_path": file_path, "error": error_msg})
            return error_msg

        # Create parent directories if requested
        if create_directories:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
        elif not resolved_path.parent.exists():
            return f"Error: Parent directory does not exist: {resolved_path.parent}"

        # Create backup if file exists and backup is enabled
        file_existed = resolved_path.exists()
        if file_existed and WRITE_FILE_CREATE_BACKUP:
            _create_backup(resolved_path)

        # Write the file
        resolved_path.write_text(content, encoding="utf-8")

        action = "overwritten" if file_existed else "created"
        result = f"File {action} successfully: {file_path}"
        logger.info(f"File {action}", extra={"file_path": file_path, "size": len(content)})

        return result

    except PermissionError:
        error_msg = f"Error: Permission denied writing to '{file_path}'"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error writing file '{file_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
