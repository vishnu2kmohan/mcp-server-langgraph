"""
Filesystem tools for file operations

Provides READ-ONLY file system access for the agent.
All tools are restricted to safe operations for security.
"""

from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

# Observability placeholder
logger = type("StubLogger", (), {"info": lambda *a, **kw: None, "error": lambda *a, **kw: None})()
metrics = type("StubMetrics", (), {"tool_calls": type("Counter", (), {"add": lambda *a, **kw: None})()})()

# Maximum file size to read (1MB for safety)
MAX_FILE_SIZE = 1024 * 1024

# Allowed file extensions (read-only, safe formats)
SAFE_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".log", ".csv", ".xml", ".html", ".py", ".js", ".ts"}


def _is_safe_path(path: str) -> bool:
    """
    Check if path is safe to access.

    Args:
        path: File or directory path

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve to absolute path and check it exists
        abs_path = Path(path).resolve()

        # Block access to system directories
        dangerous_paths = [
            "/etc",
            "/sys",
            "/proc",
            "/dev",
            "/boot",
            "/root",
            Path.home() / ".ssh",
            Path.home() / ".aws",
        ]

        for dangerous in dangerous_paths:
            dangerous_path = Path(dangerous) if isinstance(dangerous, str) else dangerous
            if abs_path.is_relative_to(dangerous_path):  # type: ignore[arg-type]
                return False

        return True

    except Exception:
        return False


@tool  # type: ignore[misc]
def read_file(
    file_path: Annotated[str, Field(description="Path to file to read")],
    max_bytes: Annotated[int, Field(ge=100, le=MAX_FILE_SIZE, description="Maximum bytes to read (100-1048576)")] = 10000,
) -> str:
    """
    Read contents of a text file.

    Supports: .txt, .md, .json, .yaml, .yml, .log, .csv, .xml, .html, .py, .js, .ts
    Maximum file size: 1MB for safety.

    Use this to:
    - Read configuration files
    - View log files
    - Inspect code or documentation

    SECURITY: Read-only access, blocks system directories.
    """
    try:
        logger.info("Read file tool invoked", extra={"file_path": file_path})
        metrics.tool_calls.add(1, {"tool": "read_file"})

        # Validate path safety
        if not _is_safe_path(file_path):
            return f"Error: Access denied - path '{file_path}' is not safe to read"

        path = Path(file_path).resolve()

        # Check file exists
        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not path.is_file():
            return f"Error: Path '{file_path}' is not a file"

        # Check file extension
        if path.suffix.lower() not in SAFE_EXTENSIONS:
            return f"Error: File type '{path.suffix}' not allowed. Allowed: {', '.join(SAFE_EXTENSIONS)}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({file_size} bytes). Maximum: {MAX_FILE_SIZE} bytes"

        # Read file (up to max_bytes)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)

        truncated = len(content) >= max_bytes
        result = f"File: {file_path}\nSize: {file_size} bytes\n"
        if truncated:
            result += f"Content (first {max_bytes} bytes):\n"
        else:
            result += "Content:\n"
        result += "-" * 40 + "\n"
        result += content
        if truncated:
            result += f"\n\n[... truncated at {max_bytes} bytes ...]"

        logger.info("File read successfully", extra={"file_path": file_path, "bytes_read": len(content)})
        return result

    except Exception as e:
        error_msg = f"Error reading file '{file_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"


@tool  # type: ignore[misc]
def list_directory(
    directory_path: Annotated[str, Field(description="Path to directory to list")],
    show_hidden: Annotated[bool, Field(description="Whether to show hidden files (starting with .)")] = False,
) -> str:
    """
    List contents of a directory.

    Returns file and directory names with types and sizes.

    Use this to:
    - Explore directory structure
    - Find available files
    - Check what exists before reading

    SECURITY: Read-only access, blocks system directories.
    """
    try:
        logger.info("List directory tool invoked", extra={"directory_path": directory_path})
        metrics.tool_calls.add(1, {"tool": "list_directory"})

        # Validate path safety
        if not _is_safe_path(directory_path):
            return f"Error: Access denied - path '{directory_path}' is not safe to access"

        path = Path(directory_path).resolve()

        # Check directory exists
        if not path.exists():
            return f"Error: Directory '{directory_path}' does not exist"

        if not path.is_dir():
            return f"Error: Path '{directory_path}' is not a directory"

        # List contents
        items = []
        for item in sorted(path.iterdir()):
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith("."):
                continue

            item_type = "DIR" if item.is_dir() else "FILE"
            size = ""
            if item.is_file():
                try:
                    file_size = item.stat().st_size
                    if file_size < 1024:
                        size = f" ({file_size} B)"
                    elif file_size < 1024 * 1024:
                        size = f" ({file_size / 1024:.1f} KB)"
                    else:
                        size = f" ({file_size / (1024 * 1024):.1f} MB)"
                except Exception:
                    size = " (size unknown)"

            items.append(f"  [{item_type}] {item.name}{size}")

        result = f"Directory: {directory_path}\n"
        result += f"Items: {len(items)}\n"
        result += "-" * 40 + "\n"
        result += "\n".join(items) if items else "  (empty)"

        logger.info("Directory listed successfully", extra={"directory_path": directory_path, "item_count": len(items)})
        return result

    except Exception as e:
        error_msg = f"Error listing directory '{directory_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"


@tool  # type: ignore[misc]
def search_files(
    directory_path: Annotated[str, Field(description="Directory to search in")],
    pattern: Annotated[str, Field(description="Filename pattern to search for (e.g., '*.py', 'config.yaml')")],
    max_results: Annotated[int, Field(ge=1, le=100, description="Maximum number of results (1-100)")] = 20,
) -> str:
    """
    Search for files matching a pattern in a directory (recursive).

    Supports wildcards: * (any characters), ? (single character)

    Use this to:
    - Find files by name or extension
    - Locate configuration files
    - Search for specific file patterns

    SECURITY: Read-only access, blocks system directories.
    """
    try:
        logger.info("Search files tool invoked", extra={"directory_path": directory_path, "pattern": pattern})
        metrics.tool_calls.add(1, {"tool": "search_files"})

        # Validate path safety
        if not _is_safe_path(directory_path):
            return f"Error: Access denied - path '{directory_path}' is not safe to access"

        path = Path(directory_path).resolve()

        # Check directory exists
        if not path.exists():
            return f"Error: Directory '{directory_path}' does not exist"

        if not path.is_dir():
            return f"Error: Path '{directory_path}' is not a directory"

        # Search for files
        matches = []
        for match in path.rglob(pattern):
            if match.is_file():
                # Check each match is in a safe location
                if _is_safe_path(str(match)):
                    rel_path = match.relative_to(path)
                    file_size = match.stat().st_size
                    if file_size < 1024:
                        size = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size = f"{file_size / 1024:.1f} KB"
                    else:
                        size = f"{file_size / (1024 * 1024):.1f} MB"

                    matches.append(f"  {rel_path} ({size})")

                    if len(matches) >= max_results:
                        break

        result = f"Search: {pattern} in {directory_path}\n"
        result += f"Found: {len(matches)} files\n"
        result += "-" * 40 + "\n"
        result += "\n".join(matches) if matches else "  (no matches)"

        if len(matches) >= max_results:
            result += f"\n\n[... limited to {max_results} results ...]"

        logger.info(
            "File search completed", extra={"directory_path": directory_path, "pattern": pattern, "matches": len(matches)}
        )
        return result

    except Exception as e:
        error_msg = f"Error searching files in '{directory_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"
