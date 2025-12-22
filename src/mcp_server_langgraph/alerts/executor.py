"""
Remediation Executor.

Executes approved remediation commands in a controlled, secure manner.

Features:
- Only executes approved remediations
- Command validation and sanitization
- Timeout handling
- Execution result tracking
- Audit logging

Security:
- Validates commands against allowlist
- Rejects dangerous patterns
- Sandboxed execution (future: container isolation)

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import logging
import re
import time
from datetime import UTC, datetime

from opentelemetry import trace
from pydantic import BaseModel, Field

from mcp_server_langgraph.alerts.approval_queue import RemediationRequest
from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ExecutionResult(BaseModel):
    """Result of a remediation execution."""

    remediation_id: str = Field(..., description="ID of the executed remediation")
    success: bool = Field(..., description="Whether execution succeeded")
    exit_code: int = Field(0, description="Process exit code")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    executed_at: str = Field(..., description="Execution timestamp")
    duration_ms: int = Field(0, description="Execution duration in milliseconds")
    error_message: str | None = Field(None, description="Error message if failed")


# Allowed command prefixes for remediation
ALLOWED_COMMAND_PREFIXES = [
    "kubectl",
    "helm",
    "docker",
    "aws",
    "gcloud",
    "az",  # Azure CLI
    "echo",  # For testing
]

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r",
    r"rm\s+/",
    r"sudo\s+rm",
    r">\s*/dev",
    r";\s*rm",
    r"&&\s*rm",
    r"\|\s*bash",
    r"\|\s*sh",
    r"curl\s+.*\|\s*",
    r"wget\s+.*\|\s*",
    r"mkfs",
    r"dd\s+if=",
    r"chmod\s+777",
    r"chmod\s+-R\s+777",
    r"chown\s+-R\s+",
    r"iptables\s+-F",
    r"systemctl\s+stop",
    r"service\s+.*\s+stop",
]


class RemediationExecutor:
    """
    Executes approved remediation commands.

    Security-first design:
    - Only executes approved remediations
    - Validates commands against allowlist
    - Blocks dangerous command patterns
    - Enforces execution timeouts
    """

    def __init__(
        self,
        timeout_seconds: int = 300,
        allowed_prefixes: list[str] | None = None,
    ) -> None:
        """
        Initialize the executor.

        Args:
            timeout_seconds: Maximum execution time (default: 5 minutes).
            allowed_prefixes: Custom allowed command prefixes.
        """
        self.timeout_seconds = timeout_seconds
        self.allowed_prefixes = allowed_prefixes or ALLOWED_COMMAND_PREFIXES
        self._dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS
        ]

    def validate_command(self, command: str) -> bool:
        """
        Validate a command before execution.

        Args:
            command: The command to validate.

        Returns:
            True if command is safe to execute, False otherwise.
        """
        if not command or not command.strip():
            return False

        command = command.strip()

        # Check for dangerous patterns
        for pattern in self._dangerous_patterns:
            if pattern.search(command):
                logger.warning(
                    "Command blocked - dangerous pattern detected",
                    extra={"pattern": pattern.pattern, "command": command[:100]},
                )
                return False

        # Check if command starts with allowed prefix
        command_lower = command.lower()
        has_allowed_prefix = any(
            command_lower.startswith(prefix.lower())
            for prefix in self.allowed_prefixes
        )

        if not has_allowed_prefix:
            logger.warning(
                "Command blocked - not in allowed prefixes",
                extra={"command": command[:100], "allowed": self.allowed_prefixes},
            )
            return False

        return True

    async def execute(self, remediation: RemediationRequest) -> ExecutionResult:
        """
        Execute an approved remediation.

        Args:
            remediation: The remediation request to execute.

        Returns:
            ExecutionResult with execution details.

        Raises:
            ValueError: If remediation is not approved.
        """
        with tracer.start_as_current_span(
            "remediation.execute",
            attributes={
                "remediation.id": remediation.remediation_id,
                "remediation.alert_id": remediation.alert_id,
                "remediation.status": remediation.status.value if remediation.status else "unknown",
            },
        ) as span:
            if remediation.status != ApprovalStatus.APPROVED:
                span.set_attribute("remediation.error", "not_approved")
                raise ValueError(
                    f"Cannot execute remediation {remediation.remediation_id}: "
                    f"status is {remediation.status}, must be APPROVED"
                )

            executed_at = datetime.now(UTC).isoformat()
            start_time = time.monotonic()

            # Handle no command case
            if not remediation.command:
                logger.info(
                    f"Remediation {remediation.remediation_id} has no command (manual action)",
                    extra={"remediation_id": remediation.remediation_id},
                )
                span.set_attribute("remediation.manual_action", True)
                return ExecutionResult(
                    remediation_id=remediation.remediation_id,
                    success=True,
                    exit_code=0,
                    stdout="No command to execute - manual action required",
                    stderr="",
                    executed_at=executed_at,
                    duration_ms=0,
                    error_message=None,
                )

            # Validate command
            if not self.validate_command(remediation.command):
                span.set_attribute("remediation.validation_failed", True)
                return ExecutionResult(
                    remediation_id=remediation.remediation_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Command validation failed",
                    executed_at=executed_at,
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                    error_message="Command blocked by security validation",
                )

            # Execute command
            try:
                exit_code, stdout, stderr = await self._run_command(
                    remediation.command, self.timeout_seconds
                )
                duration_ms = int((time.monotonic() - start_time) * 1000)

                success = exit_code == 0

                logger.info(
                    f"Remediation {remediation.remediation_id} executed",
                    extra={
                        "remediation_id": remediation.remediation_id,
                        "exit_code": exit_code,
                        "success": success,
                        "duration_ms": duration_ms,
                    },
                )

                span.set_attribute("remediation.success", success)
                span.set_attribute("remediation.exit_code", exit_code)
                span.set_attribute("remediation.duration_ms", duration_ms)

                return ExecutionResult(
                    remediation_id=remediation.remediation_id,
                    success=success,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    executed_at=executed_at,
                    duration_ms=duration_ms,
                    error_message=None if success else f"Command exited with code {exit_code}",
                )

            except TimeoutError as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                # Timeout is an expected condition, not an exception needing traceback
                logger.warning(  # noqa: TRY400
                    f"Remediation {remediation.remediation_id} timed out",
                    extra={
                        "remediation_id": remediation.remediation_id,
                        "timeout_seconds": self.timeout_seconds,
                    },
                )
                span.set_attribute("remediation.timeout", True)
                span.record_exception(e)
                return ExecutionResult(
                    remediation_id=remediation.remediation_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    executed_at=executed_at,
                    duration_ms=duration_ms,
                    error_message=f"Command timed out after {self.timeout_seconds} seconds",
                )

            except Exception as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                logger.exception(
                    f"Remediation {remediation.remediation_id} failed with exception",
                    extra={"remediation_id": remediation.remediation_id},
                )
                span.record_exception(e)
                return ExecutionResult(
                    remediation_id=remediation.remediation_id,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=str(e),
                    executed_at=executed_at,
                    duration_ms=duration_ms,
                    error_message=f"Execution error: {str(e)}",
                )

    async def _run_command(
        self, command: str, timeout: int
    ) -> tuple[int, str, str]:
        """
        Run a shell command with timeout.

        Args:
            command: The command to run.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (exit_code, stdout, stderr).

        Raises:
            asyncio.TimeoutError: If command times out.
        """
        logger.debug(f"Executing command: {command[:100]}...")

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                process.returncode or 0,
                stdout_bytes.decode("utf-8", errors="replace"),
                stderr_bytes.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
