"""Subprocess helper functions for safe and consistent CLI tool execution.

This module provides wrapper functions for subprocess.run() with built-in safety
features to prevent common issues in test execution:
- Timeout protection (prevents hanging tests)
- Consistent error handling
- Structured logging of command failures
- Better diagnostics for debugging

Related: OpenAI Codex Finding #6 - Subprocess test safeguards
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Union


def run_cli_tool(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 60,
    check_returncode: bool = True,
    capture_output: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run a CLI tool with safety defaults.

    This wrapper provides consistent subprocess.run() behavior across all tests:
    - Default timeout prevents hanging (especially on CI runners)
    - Captures output by default for better error messages
    - Returns text output (decoded strings) by default

    Args:
        cmd: Command and arguments as list (e.g., ["helm", "lint", "chart/"])
        cwd: Working directory for command execution
        timeout: Maximum execution time in seconds (default: 60s)
        check_returncode: Whether to assert returncode==0 (default: True)
        capture_output: Whether to capture stdout/stderr (default: True)
        text: Whether to decode output as text (default: True)

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        subprocess.TimeoutExpired: If command exceeds timeout
        AssertionError: If check_returncode=True and command fails

    Example:
        >>> result = run_cli_tool(["kubectl", "get", "pods"], timeout=30)
        >>> assert result.returncode == 0
        >>> print(result.stdout)

        >>> # For commands expected to fail:
        >>> result = run_cli_tool(["helm", "lint", "invalid/"], check_returncode=False)
        >>> assert result.returncode != 0
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
        )
    except subprocess.TimeoutExpired as e:
        # Provide helpful diagnostic when timeout occurs
        raise AssertionError(
            f"Command timed out after {timeout}s: {' '.join(cmd)}\n"
            f"Working directory: {cwd}\n"
            f"This usually indicates a hung process. Consider:\n"
            f"- Increasing timeout if command is legitimately slow\n"
            f"- Checking for interactive prompts (use --non-interactive flags)\n"
            f"- Investigating if tool is waiting for input\n"
            f"Timeout exception: {e}"
        ) from e

    if check_returncode and result.returncode != 0:
        # Provide structured error message with command details
        raise AssertionError(
            f"Command failed with exit code {result.returncode}: {' '.join(cmd)}\n"
            f"Working directory: {cwd}\n"
            f"Stdout:\n{result.stdout}\n"
            f"Stderr:\n{result.stderr}"
        )

    return result


def run_helm_command(
    subcmd: str,
    args: list[str],
    timeout: int = 90,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run helm command with appropriate timeout.

    Helm operations can be slow, especially template rendering and dependency updates.
    This wrapper provides helm-specific defaults.

    Args:
        subcmd: Helm subcommand (e.g., "lint", "template", "dependency")
        args: Additional arguments
        timeout: Timeout in seconds (default: 90s for helm operations)
        **kwargs: Additional arguments passed to run_cli_tool()

    Returns:
        CompletedProcess with command results

    Example:
        >>> result = run_helm_command("lint", [str(chart_dir)])
        >>> result = run_helm_command("template", [str(chart_dir), "--values", str(values_file)])
    """
    cmd = ["helm", subcmd] + args
    return run_cli_tool(cmd, timeout=timeout, **kwargs)


def run_kustomize_command(
    subcmd: str,
    args: list[str],
    timeout: int = 60,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run kustomize command with appropriate timeout.

    Args:
        subcmd: Kustomize subcommand (e.g., "build", "edit")
        args: Additional arguments
        timeout: Timeout in seconds (default: 60s)
        **kwargs: Additional arguments passed to run_cli_tool()

    Returns:
        CompletedProcess with command results

    Example:
        >>> result = run_kustomize_command("build", [str(overlay_dir)])
    """
    cmd = ["kustomize", subcmd] + args
    return run_cli_tool(cmd, timeout=timeout, **kwargs)


def run_kubectl_command(
    subcmd: str,
    args: list[str],
    timeout: int = 60,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run kubectl command with appropriate timeout.

    Args:
        subcmd: Kubectl subcommand (e.g., "get", "apply", "delete")
        args: Additional arguments
        timeout: Timeout in seconds (default: 60s)
        **kwargs: Additional arguments passed to run_cli_tool()

    Returns:
        CompletedProcess with command results

    Example:
        >>> result = run_kubectl_command("get", ["pods", "-n", "default"])
    """
    cmd = ["kubectl", subcmd] + args
    return run_cli_tool(cmd, timeout=timeout, **kwargs)


def run_git_command(
    subcmd: str,
    args: list[str],
    timeout: int = 30,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run git command with appropriate timeout.

    Args:
        subcmd: Git subcommand (e.g., "status", "diff", "log")
        args: Additional arguments
        timeout: Timeout in seconds (default: 30s)
        **kwargs: Additional arguments passed to run_cli_tool()

    Returns:
        CompletedProcess with command results

    Example:
        >>> result = run_git_command("status", ["--porcelain"])
    """
    cmd = ["git", subcmd] + args
    return run_cli_tool(cmd, timeout=timeout, **kwargs)
