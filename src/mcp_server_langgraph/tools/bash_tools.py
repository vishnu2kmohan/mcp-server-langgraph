"""
Enhanced Bash Tool for secure command execution (ADR-0079)

Provides a LangChain-compatible tool for executing bash commands with:
- Command allowlist security
- Dangerous command blocking (sudo, rm, curl, wget, etc.)
- Path traversal prevention
- Shell expansion blocking
- Output truncation
- Timeout enforcement
- Feature flag integration

Usage:
    from mcp_server_langgraph.tools.bash_tools import execute_bash

    result = execute_bash.invoke({"command": "ls -la"})
"""

from __future__ import annotations

import re
import shlex
from typing import Annotated

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.execution.sandbox_runner import get_sandbox_runner, SandboxError

# =============================================================================
# Constants
# =============================================================================

# Commands that are always allowed (read-only, safe)
ALLOWED_COMMANDS: set[str] = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "echo",
    "pwd",
    "date",
    "whoami",
    "uname",
    "env",
    "printenv",
    "which",
    "type",
    "file",
    "stat",
    "du",
    "df",
    "uptime",
    "hostname",
    "id",
    "groups",
    "sort",
    "uniq",
    "tr",
    "cut",
    "awk",
    "sed",
    "diff",
    "comm",
    "join",
    "paste",
    "tee",
    "xargs",
    "basename",
    "dirname",
    "realpath",
    "readlink",
}

# Commands that are always blocked (dangerous)
BLOCKED_COMMANDS: set[str] = {
    "sudo",
    "su",
    "rm",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "chgrp",
    "curl",
    "wget",
    "nc",
    "netcat",
    "ncat",
    "ssh",
    "scp",
    "sftp",
    "ftp",
    "telnet",
    "dd",
    "mkfs",
    "fdisk",
    "parted",
    "mount",
    "umount",
    "kill",
    "killall",
    "pkill",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "systemctl",
    "service",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "pip",
    "pip3",
    "npm",
    "yarn",
    "docker",
    "kubectl",
    "eval",
    "exec",
    "source",
    ".",
}

# Dangerous patterns to block
DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\$\("),  # Command substitution $(...)
    re.compile(r"`"),  # Backtick command substitution
    re.compile(r">\s*/"),  # Redirect to absolute path
    re.compile(r"\|\s*sudo"),  # Pipe to sudo
    re.compile(r"\|\s*bash"),  # Pipe to bash
    re.compile(r"\|\s*sh"),  # Pipe to sh
    re.compile(r"&&\s*sudo"),  # Chain with sudo
    re.compile(r";\s*sudo"),  # Semicolon with sudo
    re.compile(r"\.\./"),  # Path traversal
    re.compile(r"/etc/shadow"),  # Shadow file access
    re.compile(r"/etc/passwd.*>"),  # Passwd write
    re.compile(r"^/root"),  # Root directory access
    re.compile(r"\s/root"),  # Root directory in args
]

# Sensitive paths to block
SENSITIVE_PATHS: set[str] = {
    "/root",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/ssh",
    "/proc",
    "/sys",
    "/dev",
}

DEFAULT_TIMEOUT: int = 30
DEFAULT_MAX_OUTPUT_SIZE: int = 10000
SANDBOX_ENVIRONMENTS = {"test", "sandbox"}


# =============================================================================
# Input Schema
# =============================================================================


class ExecuteBashInput(BaseModel):
    """Input schema for execute_bash tool."""

    command: str = Field(
        ...,
        description="The bash command to execute. Must be on the allowlist.",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        ge=1,
        le=300,
        description="Timeout in seconds (1-300). Default is 30.",
    )
    working_directory: str | None = Field(
        default=None,
        description="Optional working directory for command execution.",
    )


# =============================================================================
# Security Functions
# =============================================================================


def is_command_allowed(command: str) -> bool:
    """Check if a command is allowed to execute.

    Validates the command against:
    - Allowlist of safe commands
    - Blocklist of dangerous commands
    - Dangerous shell patterns
    - Path traversal attempts
    - Sensitive path access

    Args:
        command: The bash command to validate

    Returns:
        True if the command is allowed, False otherwise
    """
    # Empty or whitespace-only commands are not allowed
    if not command or not command.strip():
        return False

    command = command.strip()

    # Check for dangerous patterns first
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(command):
            return False

    # Check for sensitive paths
    for path in SENSITIVE_PATHS:
        if path in command:
            return False

    # Split command into parts for analysis
    # Handle pipes and chains
    parts = re.split(r"[|;&]", command)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract the base command
        try:
            tokens = shlex.split(part)
        except ValueError:
            # Invalid shell syntax
            return False

        if not tokens:
            continue

        base_cmd = tokens[0]

        # Remove any path prefix to get the command name
        base_cmd = base_cmd.split("/")[-1]

        # Check if base command is blocked
        if base_cmd in BLOCKED_COMMANDS:
            return False

        # Check if base command is allowed
        if base_cmd not in ALLOWED_COMMANDS:
            return False

    return True


def truncate_output(output: str, max_size: int = DEFAULT_MAX_OUTPUT_SIZE) -> str:
    """Truncate output if it exceeds the maximum size.

    Args:
        output: The output string to potentially truncate
        max_size: Maximum allowed size in characters

    Returns:
        The original output if within limits, or truncated with a message
    """
    if len(output) <= max_size:
        return output

    truncation_message = "\n\n... [OUTPUT TRUNCATED - exceeded maximum size] ..."
    truncated = output[:max_size] + truncation_message
    return truncated


# =============================================================================
# Tool Implementation
# =============================================================================


@tool(args_schema=ExecuteBashInput)
def execute_bash(
    command: Annotated[str, "The bash command to execute"],
    timeout: Annotated[int, "Timeout in seconds"] = DEFAULT_TIMEOUT,
    working_directory: Annotated[str | None, "Working directory"] = None,
) -> str:
    """Execute a bash command in a sandboxed environment.

    This tool executes bash commands with security controls including:
    - Command allowlisting (only safe commands allowed)
    - Dangerous command blocking (no sudo, rm, curl, etc.)
    - Path traversal prevention
    - Output truncation for large outputs
    - Timeout enforcement

    Args:
        command: The bash command to execute
        timeout: Maximum execution time in seconds (default 30)
        working_directory: Optional working directory

    Returns:
        Command output or error message
    """
    # Allow only when sandbox tools are enabled and code execution is on
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return "Error: Bash tool is restricted to sandbox environments with code execution enabled."

    # Check feature flag
    if not feature_flags.enable_bash_tool:
        return "Error: Bash tool is disabled. Enable the 'enable_bash_tool' feature flag to use this tool."

    # Validate command
    if not is_command_allowed(command):
        return f"Error: Command is blocked or not allowed. Only safe, read-only commands are permitted. Blocked: {command}"

    try:
        runner = get_sandbox_runner()
        result = runner.run_bash(command, timeout_override=timeout)

        output = result.stdout
        if result.stderr:
            if output:
                output += "\n\nSTDERR:\n" + result.stderr
            else:
                output = result.stderr

        if not output:
            if result.exit_code == 0 and not result.timed_out:
                output = "(command completed successfully with no output)"
            else:
                output = f"(command failed with exit code {result.exit_code})"

        output = truncate_output(output)
        if result.timed_out:
            output = f"Error: Command timed out after {timeout} seconds\n\n{output}"
        if result.error_message:
            output = f"Error: {result.error_message}\n\n{output}"
        return output

    except SandboxError as e:
        return f"Sandbox error: {e}"
    except Exception as e:
        return f"Error: Command execution failed: {e!s}"


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ALLOWED_COMMANDS",
    "BLOCKED_COMMANDS",
    "DEFAULT_MAX_OUTPUT_SIZE",
    "DEFAULT_TIMEOUT",
    "ExecuteBashInput",
    "execute_bash",
    "is_command_allowed",
    "truncate_output",
]
