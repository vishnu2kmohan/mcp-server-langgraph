"""
Edit file tools for precise file modifications.

Provides diff-based file editing for the agent with security controls.
All operations are restricted to the workspace directory for security.
"""

import os
import shutil
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.observability.telemetry import logger, metrics

# Configuration constants
EDIT_FILE_CREATE_BACKUP = os.getenv("EDIT_FILE_CREATE_BACKUP", "true").lower() == "true"
EDIT_FILE_MAX_DIFF_SIZE = int(os.getenv("EDIT_FILE_MAX_DIFF_SIZE", "10000"))  # characters


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
def edit_file(
    file_path: Annotated[str, Field(description="Path to the file to edit")],
    old_string: Annotated[str, Field(description="Exact text to find and replace")],
    new_string: Annotated[str, Field(description="Replacement text")],
    replace_all: Annotated[
        bool, Field(description="Replace all occurrences (default: replace only first)")
    ] = False,
) -> str:
    """
    Make precise edits to an existing file by replacing text.

    The old_string must exist in the file. By default, only the first occurrence
    is replaced. Use replace_all=True to replace all occurrences.

    Creates a backup before editing.

    Use this to:
    - Make targeted code changes
    - Update configuration values
    - Fix specific text in files

    SECURITY: Restricted to workspace directory.
    """
    try:
        logger.info("Edit file tool invoked", extra={
            "file_path": file_path,
            "old_string_len": len(old_string),
            "new_string_len": len(new_string),
            "replace_all": replace_all,
        })
        metrics.tool_calls.add(1, {"tool": "edit_file"})

        # Validate old_string is not empty
        if not old_string:
            return "Error: old_string cannot be empty"

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

        # Check file exists
        if not resolved_path.exists():
            return f"Error: File not found: {file_path}"

        if not resolved_path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content
        try:
            content = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with fallback encoding
            content = resolved_path.read_text(encoding="latin-1")

        # Check if old_string exists in file
        if old_string not in content:
            return f"Error: old_string not found in file. The text '{old_string[:50]}...' does not exist in {file_path}"

        # Count occurrences
        occurrence_count = content.count(old_string)

        # Create backup if enabled
        if EDIT_FILE_CREATE_BACKUP:
            _create_backup(resolved_path)

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements_made = occurrence_count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements_made = 1

        # Handle no-op case (old_string == new_string)
        if old_string == new_string:
            return f"No changes made: old_string and new_string are identical"

        # Write the modified content
        resolved_path.write_text(new_content, encoding="utf-8")

        # Build result message
        result = f"File edited successfully: {file_path}"
        result += f"\nReplacements made: {replacements_made}"

        if not replace_all and occurrence_count > 1:
            result += f"\nNote: {occurrence_count - 1} additional occurrence(s) were not replaced. Use replace_all=True to replace all."

        logger.info("File edited", extra={
            "file_path": file_path,
            "replacements": replacements_made,
            "total_occurrences": occurrence_count,
        })

        return result

    except PermissionError:
        error_msg = f"Error: Permission denied editing '{file_path}'"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error editing file '{file_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
