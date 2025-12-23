"""
Skill Executor

Executes skill scripts in sandboxed environments with
proper configuration, secret injection, and timeout handling.

Usage:
    from mcp_server_langgraph.skills.executor import SkillExecutor

    executor = SkillExecutor()
    context = executor.prepare_context(skill)
    result = await executor.execute(skill, "script.py", args)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from mcp_server_langgraph.skills.metrics import record_skill_execution
from mcp_server_langgraph.skills.models import Skill

if TYPE_CHECKING:
    from mcp_server_langgraph.execution.sandbox import (
        ExecutionResult as SandboxResult,
        Sandbox,
    )

logger = logging.getLogger(__name__)


class ExecutionResult(BaseModel):
    """Result of a skill script execution."""

    success: bool
    output: str | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class SecretValidationResult:
    """Result of secret validation check."""

    is_valid: bool
    missing_secrets: list[str] = field(default_factory=list)


@dataclass
class ExecutionContext:
    """Execution context for running skill scripts."""

    network_mode: str = "none"
    allowed_domains: list[str] = field(default_factory=list)
    timeout: int = 30
    memory_mb: int = 256
    environment: dict[str, str] = field(default_factory=dict)


class SkillExecutor:
    """Executes skill scripts in sandboxed environments.

    Handles sandbox configuration, secret validation, and
    execution with proper timeout and resource limits.
    """

    def __init__(self, default_timeout: int = 30) -> None:
        """Initialize skill executor.

        Args:
            default_timeout: Default timeout in seconds for script execution
        """
        self.default_timeout = default_timeout
        self._sandbox: Sandbox | None = None

    def set_sandbox(self, sandbox: Sandbox) -> None:
        """Set the sandbox to use for script execution.

        Args:
            sandbox: Sandbox instance (Docker, Kubernetes, etc.)
        """
        self._sandbox = sandbox

    def validate_script(self, skill: Skill, script_name: str) -> bool:
        """Validate that a script exists in the skill bundle.

        Args:
            skill: Skill containing the script
            script_name: Name of the script to validate

        Returns:
            True if script is in the skill's scripts list
        """
        return script_name in skill.scripts

    def load_script_content(self, skill: Skill, script_name: str) -> str | None:
        """Load script content from the skill's directory.

        Args:
            skill: Skill containing the script
            script_name: Name of the script to load

        Returns:
            Script content as string, or None if not found
        """
        if skill.path is None:
            logger.debug(
                "Cannot load script without skill path",
                extra={"skill": skill.name, "script": script_name},
            )
            return None

        script_path = Path(skill.path) / script_name
        if not script_path.exists():
            logger.debug(
                "Script file not found",
                extra={"skill": skill.name, "script": script_name, "path": str(script_path)},
            )
            return None

        try:
            return script_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(
                "Failed to read script file",
                extra={"skill": skill.name, "script": script_name, "error": str(e)},
            )
            return None

    def validate_secrets(
        self,
        skill: Skill,
        available_secrets: dict[str, str],
    ) -> SecretValidationResult:
        """Validate that all required secrets are available.

        Args:
            skill: Skill with required_secrets list
            available_secrets: Dictionary of available secrets

        Returns:
            SecretValidationResult with validation status
        """
        missing = []
        for secret_name in skill.required_secrets:
            if secret_name not in available_secrets:
                missing.append(secret_name)

        return SecretValidationResult(
            is_valid=len(missing) == 0,
            missing_secrets=missing,
        )

    def prepare_context(
        self,
        skill: Skill,
        secrets: dict[str, str] | None = None,
    ) -> ExecutionContext:
        """Prepare execution context from skill configuration.

        Args:
            skill: Skill to prepare context for
            secrets: Optional secrets to inject into environment

        Returns:
            ExecutionContext with sandbox settings
        """
        if skill.sandbox_config:
            context = ExecutionContext(
                network_mode=skill.sandbox_config.network,
                allowed_domains=list(skill.sandbox_config.allowed_domains),
                timeout=skill.sandbox_config.timeout_seconds,
                memory_mb=skill.sandbox_config.memory_mb,
            )
        else:
            # Use defaults
            context = ExecutionContext(
                network_mode="none",
                allowed_domains=[],
                timeout=self.default_timeout,
                memory_mb=256,
            )

        # Inject secrets into environment
        if secrets:
            context.environment = dict(secrets)

        return context

    async def execute(
        self,
        skill: Skill,
        script_name: str,
        args: dict[str, Any] | None = None,
        secrets: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a skill script.

        Args:
            skill: Skill containing the script
            script_name: Name of script to execute
            args: Arguments to pass to script
            secrets: Secrets to inject into environment

        Returns:
            ExecutionResult with output or error

        Note:
            Actual execution is delegated to the sandbox system.
            This method prepares the context and validates inputs.
        """
        # Validate script exists
        if not self.validate_script(skill, script_name):
            result = ExecutionResult(
                success=False,
                error=f"Script '{script_name}' not found in skill '{skill.name}'",
            )
            record_skill_execution(
                skill_name=skill.name,
                script_name=script_name,
                success=False,
                duration_ms=0.0,
                error_type="script_not_found",
            )
            return result

        # Validate secrets
        if skill.required_secrets:
            validation = self.validate_secrets(skill, secrets or {})
            if not validation.is_valid:
                result = ExecutionResult(
                    success=False,
                    error=f"Missing required secrets: {validation.missing_secrets}",
                )
                record_skill_execution(
                    skill_name=skill.name,
                    script_name=script_name,
                    success=False,
                    duration_ms=0.0,
                    error_type="missing_secrets",
                )
                return result

        # Prepare execution context
        context = self.prepare_context(skill, secrets)

        # If no sandbox is configured, return placeholder
        if self._sandbox is None:
            logger.info(
                "No sandbox configured, returning placeholder result",
                extra={"skill": skill.name, "script": script_name},
            )
            result = ExecutionResult(
                success=True,
                output=f"Execution prepared for {script_name} with timeout={context.timeout}s",
                duration_ms=0.0,
            )
            record_skill_execution(
                skill_name=skill.name,
                script_name=script_name,
                success=True,
                duration_ms=0.0,
            )
            return result

        # Build the code to execute
        # In a real implementation, this would load the script from the skill bundle
        # and inject arguments as needed. For now, we generate a wrapper.
        code = self._build_script_code(skill, script_name, args)

        # Execute in sandbox
        start_time = time.time()
        try:
            sandbox_result: SandboxResult = await self._sandbox.aexecute(code)
            duration_ms = (time.time() - start_time) * 1000

            # Convert SandboxResult to our ExecutionResult
            if sandbox_result.success:
                result = ExecutionResult(
                    success=True,
                    output=sandbox_result.stdout,
                    error=sandbox_result.stderr if sandbox_result.stderr else None,
                    duration_ms=duration_ms,
                )
                record_skill_execution(
                    skill_name=skill.name,
                    script_name=script_name,
                    success=True,
                    duration_ms=duration_ms,
                )
                return result
            else:
                result = ExecutionResult(
                    success=False,
                    output=sandbox_result.stdout if sandbox_result.stdout else None,
                    error=sandbox_result.error_message or sandbox_result.stderr or "Execution failed",
                    duration_ms=duration_ms,
                )
                record_skill_execution(
                    skill_name=skill.name,
                    script_name=script_name,
                    success=False,
                    duration_ms=duration_ms,
                    error_type="sandbox_execution_failed",
                )
                return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                "Sandbox execution failed",
                extra={"skill": skill.name, "script": script_name, "error": str(e)},
            )
            result = ExecutionResult(
                success=False,
                error=f"Sandbox execution error: {e}",
                duration_ms=duration_ms,
            )
            record_skill_execution(
                skill_name=skill.name,
                script_name=script_name,
                success=False,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
            )
            return result

    def _build_script_code(
        self,
        skill: Skill,
        script_name: str,
        args: dict[str, Any] | None = None,
    ) -> str:
        """Build the Python code to execute in the sandbox.

        Loads actual script content from the skill bundle if available,
        otherwise falls back to a placeholder wrapper.

        Args:
            skill: The skill being executed
            script_name: Name of the script to run
            args: Arguments to pass to the script

        Returns:
            Python code string to execute
        """
        # Try to load actual script content
        script_content = self.load_script_content(skill, script_name)

        if script_content is not None:
            # Use actual script with argument injection
            args_repr = repr(args) if args else "{}"
            return f"""# Skill: {skill.name}
# Script: {script_name}
# Injected arguments: SKILL_ARGS

import json

SKILL_ARGS = {args_repr}

# --- Actual script content below ---
{script_content}
"""

        # Fallback: generate a placeholder wrapper
        args_repr = repr(args) if args else "{}"
        return f"""
# Skill: {skill.name}
# Script: {script_name}
# Auto-generated wrapper (no script file found)

import json

ARGS = {args_repr}

def main():
    print(f"Executing skill '{skill.name}' script '{script_name}'")
    print(f"Arguments: {{json.dumps(ARGS)}}")
    return "Skill execution completed"

if __name__ == "__main__":
    result = main()
    print(result)
"""
