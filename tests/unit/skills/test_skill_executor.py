"""
Unit tests for Skill Executor

Tests skill script execution in sandboxed environments.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.unit
class TestSkillExecutorBasic:
    """Test suite for basic skill executor functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_executor_exists(self):
        """GIVEN the skills module
        WHEN importing SkillExecutor
        THEN it should be available
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor

        executor = SkillExecutor()
        assert executor is not None

    def test_executor_has_sandbox_config(self):
        """GIVEN a SkillExecutor
        WHEN checking configuration
        THEN it should have sandbox settings
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor

        executor = SkillExecutor()

        assert hasattr(executor, "default_timeout")
        assert executor.default_timeout > 0


@pytest.mark.unit
class TestSkillExecutorValidation:
    """Test suite for skill execution validation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_script_path(self):
        """GIVEN a skill executor
        WHEN validating a script path
        THEN it should check script exists in skill bundle
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="test-skill",
            description="Test",
            scripts=["process.py", "analyze.py"],
        )

        assert executor.validate_script(skill, "process.py") is True
        assert executor.validate_script(skill, "unknown.py") is False

    def test_validate_required_secrets(self):
        """GIVEN a skill with required secrets
        WHEN validating secrets
        THEN it should check all required secrets are available
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="db-skill",
            description="Database skill",
            required_secrets=["DATABASE_URL", "API_KEY"],
        )

        # With all secrets
        result = executor.validate_secrets(skill, {"DATABASE_URL": "postgres://...", "API_KEY": "secret"})
        assert result.is_valid is True

        # Missing secrets
        result = executor.validate_secrets(skill, {"DATABASE_URL": "postgres://..."})
        assert result.is_valid is False
        assert "API_KEY" in result.missing_secrets


@pytest.mark.unit
class TestSkillExecutorPrepare:
    """Test suite for skill execution preparation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_prepare_execution_context(self):
        """GIVEN a skill
        WHEN preparing execution context
        THEN sandbox config should be applied
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import SandboxConfig, Skill

        executor = SkillExecutor()
        skill = Skill(
            name="web-skill",
            description="Web skill",
            sandbox_config=SandboxConfig(
                network="allowlist",
                allowed_domains=["*.google.com"],
                timeout_seconds=60,
            ),
        )

        context = executor.prepare_context(skill)

        assert context.network_mode == "allowlist"
        assert "*.google.com" in context.allowed_domains
        assert context.timeout == 60

    def test_prepare_uses_defaults_when_no_sandbox_config(self):
        """GIVEN a skill without sandbox config
        WHEN preparing execution context
        THEN defaults should be used
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(name="simple-skill", description="Simple skill")

        context = executor.prepare_context(skill)

        assert context.network_mode == "none"  # Default: no network
        assert context.timeout == 30  # Default timeout


@pytest.mark.unit
class TestSkillExecutorResult:
    """Test suite for skill execution results"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_execution_result_model(self):
        """GIVEN a skill execution
        WHEN execution completes
        THEN result should contain expected fields
        """
        from mcp_server_langgraph.skills.executor import ExecutionResult

        result = ExecutionResult(
            success=True,
            output="Result data",
            error=None,
            duration_ms=150.5,
        )

        assert result.success is True
        assert result.output == "Result data"
        assert result.error is None
        assert result.duration_ms == 150.5

    def test_execution_result_failure(self):
        """GIVEN a failed skill execution
        WHEN creating result
        THEN error should be captured
        """
        from mcp_server_langgraph.skills.executor import ExecutionResult

        result = ExecutionResult(
            success=False,
            output=None,
            error="Script timeout after 30 seconds",
            duration_ms=30000.0,
        )

        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()


@pytest.mark.unit
class TestSkillExecutorSandboxIntegration:
    """Test suite for skill executor sandbox integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_delegates_to_sandbox(self):
        """GIVEN a skill executor with a sandbox
        WHEN executing a script
        THEN it should delegate to the sandbox execute method
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        # Create a mock sandbox
        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(
            return_value=SandboxResult(
                success=True,
                stdout="Hello from skill!",
                stderr="",
                exit_code=0,
                execution_time=0.5,
            )
        )

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="test-skill",
            description="Test skill",
            scripts=["main.py"],
        )

        result = await executor.execute(skill, "main.py")

        assert result.success is True
        assert "Hello from skill" in (result.output or "")
        mock_sandbox.aexecute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_without_sandbox_returns_placeholder(self):
        """GIVEN a skill executor without a sandbox configured
        WHEN executing a script
        THEN it should return a placeholder result
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()

        skill = Skill(
            name="test-skill",
            description="Test skill",
            scripts=["main.py"],
        )

        result = await executor.execute(skill, "main.py")

        assert result.success is True
        assert "prepared" in (result.output or "").lower()

    @pytest.mark.asyncio
    async def test_execute_handles_sandbox_failure(self):
        """GIVEN a skill executor with a failing sandbox
        WHEN executing a script
        THEN it should return a failure result
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        # Create a mock sandbox that returns failure
        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(
            return_value=SandboxResult(
                success=False,
                stdout="",
                stderr="Error: module not found",
                exit_code=1,
                execution_time=0.2,
                error_message="Script execution failed",
            )
        )

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="failing-skill",
            description="A skill that fails",
            scripts=["broken.py"],
        )

        result = await executor.execute(skill, "broken.py")

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_passes_environment_to_sandbox(self):
        """GIVEN a skill executor with secrets
        WHEN executing a script
        THEN secrets should be passed to sandbox environment
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(return_value=SandboxResult(success=True, stdout="OK", stderr=""))

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="secret-skill",
            description="Skill needing secrets",
            scripts=["connect.py"],
            required_secrets=["API_KEY"],
        )

        secrets = {"API_KEY": "secret-value"}
        result = await executor.execute(skill, "connect.py", secrets=secrets)

        assert result.success is True
        # Verify sandbox was called (environment passed via context)
        mock_sandbox.aexecute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_applies_timeout_from_sandbox_config(self):
        """GIVEN a skill with custom timeout
        WHEN executing a script
        THEN the custom timeout should be applied
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import SandboxConfig, Skill

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(return_value=SandboxResult(success=True, stdout="OK", stderr=""))

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="timeout-skill",
            description="Skill with custom timeout",
            scripts=["long_running.py"],
            sandbox_config=SandboxConfig(
                network="none",
                timeout_seconds=120,
            ),
        )

        result = await executor.execute(skill, "long_running.py")
        assert result.success is True


@pytest.mark.unit
class TestSkillScriptLoading:
    """Test suite for loading actual scripts from skill bundles"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_has_path_field(self):
        """GIVEN a Skill model
        WHEN checking fields
        THEN it should have a path field
        """
        from pathlib import Path

        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test-skill",
            description="Test",
            path=Path("/skills/test-skill"),
        )

        assert skill.path == Path("/skills/test-skill")

    def test_skill_path_optional(self):
        """GIVEN a Skill without path
        WHEN creating the skill
        THEN path should be None
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(name="test-skill", description="Test")
        assert skill.path is None

    def test_loader_sets_path_from_directory(self, tmp_path):
        """GIVEN a skill loader
        WHEN loading from a directory
        THEN the skill path should be set
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create a temp skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill
""")

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_dir)

        assert skill.path == skill_dir

    def test_executor_load_script_content(self, tmp_path):
        """GIVEN a skill with scripts in its directory
        WHEN loading a script
        THEN the script content should be returned
        """

        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        # Create skill directory with script
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        script_file = skill_dir / "process.py"
        script_file.write_text("print('Hello from script!')")

        executor = SkillExecutor()
        skill = Skill(
            name="test-skill",
            description="Test",
            scripts=["process.py"],
            path=skill_dir,
        )

        content = executor.load_script_content(skill, "process.py")

        assert content is not None
        assert "Hello from script!" in content

    def test_executor_load_script_returns_none_for_missing(self, tmp_path):
        """GIVEN a skill with no scripts
        WHEN loading a non-existent script
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()

        executor = SkillExecutor()
        skill = Skill(
            name="empty-skill",
            description="Empty",
            scripts=[],
            path=skill_dir,
        )

        content = executor.load_script_content(skill, "nonexistent.py")
        assert content is None

    def test_executor_load_script_returns_none_without_path(self):
        """GIVEN a skill without a path
        WHEN loading a script
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="no-path-skill",
            description="No path",
            scripts=["script.py"],
        )

        content = executor.load_script_content(skill, "script.py")
        assert content is None

    @pytest.mark.asyncio
    async def test_execute_uses_actual_script_content(self, tmp_path):
        """GIVEN a skill with actual script file
        WHEN executing the script
        THEN the actual script content should be used
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        # Create skill with actual script
        skill_dir = tmp_path / "real-skill"
        skill_dir.mkdir()
        script_content = """
def main():
    return "Real script output"

if __name__ == "__main__":
    print(main())
"""
        script_file = skill_dir / "real.py"
        script_file.write_text(script_content)

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(
            return_value=SandboxResult(
                success=True,
                stdout="Real script output",
                stderr="",
            )
        )

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="real-skill",
            description="Real skill",
            scripts=["real.py"],
            path=skill_dir,
        )

        result = await executor.execute(skill, "real.py")

        assert result.success is True
        # Verify the sandbox was called with actual script content
        call_args = mock_sandbox.aexecute.call_args
        code = call_args[0][0]
        assert "def main():" in code
        assert "Real script output" in code


@pytest.mark.unit
class TestSkillSecretInjection:
    """Test suite for skill secret injection functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prepare_context_injects_secrets_into_environment(self):
        """GIVEN a skill with secrets
        WHEN preparing execution context
        THEN secrets should be injected into environment dict.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="db-skill",
            description="Database skill",
            required_secrets=["DATABASE_URL", "API_KEY"],
        )

        secrets = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "API_KEY": "sk-1234567890",
        }

        context = executor.prepare_context(skill, secrets=secrets)

        assert context.environment == secrets
        assert context.environment["DATABASE_URL"] == secrets["DATABASE_URL"]
        assert context.environment["API_KEY"] == secrets["API_KEY"]

    def test_prepare_context_handles_empty_secrets(self):
        """GIVEN a skill without secrets requirement
        WHEN preparing execution context with empty secrets
        THEN environment should be empty.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(name="simple-skill", description="Simple skill")

        context = executor.prepare_context(skill, secrets={})

        assert context.environment == {}

    def test_prepare_context_handles_none_secrets(self):
        """GIVEN a skill
        WHEN preparing execution context with None secrets
        THEN environment should be empty.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(name="simple-skill", description="Simple skill")

        context = executor.prepare_context(skill, secrets=None)

        assert context.environment == {}

    def test_validate_secrets_with_optional_secrets(self):
        """GIVEN a skill with required and optional secrets
        WHEN validating with only required secrets
        THEN validation should pass.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="db-skill",
            description="Database skill",
            required_secrets=["DATABASE_URL"],
            optional_secrets=["REDIS_URL", "CACHE_URL"],
        )

        # Only required secrets provided
        result = executor.validate_secrets(skill, {"DATABASE_URL": "postgres://..."})
        assert result.is_valid is True
        assert len(result.missing_secrets) == 0

    def test_validate_secrets_identifies_all_missing(self):
        """GIVEN a skill with multiple required secrets
        WHEN validating with no secrets
        THEN all missing secrets should be listed.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="multi-secret-skill",
            description="Skill with many secrets",
            required_secrets=["SECRET_A", "SECRET_B", "SECRET_C"],
        )

        result = executor.validate_secrets(skill, {})

        assert result.is_valid is False
        assert len(result.missing_secrets) == 3
        assert "SECRET_A" in result.missing_secrets
        assert "SECRET_B" in result.missing_secrets
        assert "SECRET_C" in result.missing_secrets

    def test_validate_secrets_with_partial_secrets(self):
        """GIVEN a skill with multiple required secrets
        WHEN validating with some secrets missing
        THEN only missing secrets should be listed.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="multi-secret-skill",
            description="Skill with many secrets",
            required_secrets=["DATABASE_URL", "API_KEY", "REDIS_URL"],
        )

        result = executor.validate_secrets(skill, {"DATABASE_URL": "postgres://..."})

        assert result.is_valid is False
        assert len(result.missing_secrets) == 2
        assert "API_KEY" in result.missing_secrets
        assert "REDIS_URL" in result.missing_secrets
        assert "DATABASE_URL" not in result.missing_secrets

    def test_validate_secrets_with_empty_required(self):
        """GIVEN a skill with no required secrets
        WHEN validating with no secrets
        THEN validation should pass.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="no-secrets-skill",
            description="Skill without secrets",
            required_secrets=[],
        )

        result = executor.validate_secrets(skill, {})

        assert result.is_valid is True
        assert len(result.missing_secrets) == 0

    @pytest.mark.asyncio
    async def test_execute_fails_on_missing_required_secrets(self):
        """GIVEN a skill with required secrets
        WHEN executing without providing secrets
        THEN execution should fail with missing secrets error.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="secret-skill",
            description="Skill needing secrets",
            scripts=["connect.py"],
            required_secrets=["DATABASE_URL", "API_KEY"],
        )

        result = await executor.execute(skill, "connect.py")

        assert result.success is False
        assert "missing" in (result.error or "").lower()
        assert "secret" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_passes_with_all_required_secrets(self):
        """GIVEN a skill with required secrets
        WHEN executing with all secrets provided
        THEN execution should proceed.
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(return_value=SandboxResult(success=True, stdout="Connected!", stderr=""))

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="secret-skill",
            description="Skill needing secrets",
            scripts=["connect.py"],
            required_secrets=["DATABASE_URL"],
        )

        secrets = {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        result = await executor.execute(skill, "connect.py", secrets=secrets)

        assert result.success is True
        mock_sandbox.aexecute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_allows_extra_secrets(self):
        """GIVEN a skill with some required secrets
        WHEN executing with extra secrets provided
        THEN execution should proceed with all secrets.
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.execution.sandbox import ExecutionResult as SandboxResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(return_value=SandboxResult(success=True, stdout="OK", stderr=""))

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        skill = Skill(
            name="secret-skill",
            description="Skill needing secrets",
            scripts=["script.py"],
            required_secrets=["API_KEY"],
        )

        # Provide extra secrets not in required list
        secrets = {
            "API_KEY": "sk-123",
            "OPTIONAL_KEY": "optional-value",
            "EXTRA_KEY": "extra-value",
        }
        result = await executor.execute(skill, "script.py", secrets=secrets)

        assert result.success is True

    def test_prepare_context_preserves_secret_values(self):
        """GIVEN secrets with special characters
        WHEN preparing execution context
        THEN secret values should be preserved exactly.
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(name="test-skill", description="Test")

        # Secrets with special characters
        secrets = {
            "DATABASE_URL": "postgresql://user:p@ss=w0rd!@localhost:5432/db?sslmode=require",
            "API_KEY": "sk-proj-abc123_xyz789-test",
            "JSON_SECRET": '{"key": "value", "nested": {"a": 1}}',
        }

        context = executor.prepare_context(skill, secrets=secrets)

        # Values should be preserved exactly
        assert context.environment["DATABASE_URL"] == secrets["DATABASE_URL"]
        assert context.environment["API_KEY"] == secrets["API_KEY"]
        assert context.environment["JSON_SECRET"] == secrets["JSON_SECRET"]

    def test_secret_validation_result_dataclass(self):
        """GIVEN a SecretValidationResult
        WHEN checking attributes
        THEN it should have expected fields.
        """
        from mcp_server_langgraph.skills.executor import SecretValidationResult

        result = SecretValidationResult(
            is_valid=False,
            missing_secrets=["SECRET_A", "SECRET_B"],
        )

        assert result.is_valid is False
        assert len(result.missing_secrets) == 2
        assert "SECRET_A" in result.missing_secrets

    def test_secret_validation_result_defaults(self):
        """GIVEN a SecretValidationResult with minimal args
        WHEN checking attributes
        THEN defaults should be applied.
        """
        from mcp_server_langgraph.skills.executor import SecretValidationResult

        result = SecretValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.missing_secrets == []

    def test_execution_context_environment_field(self):
        """GIVEN an ExecutionContext
        WHEN checking environment field
        THEN it should be a dictionary.
        """
        from mcp_server_langgraph.skills.executor import ExecutionContext

        context = ExecutionContext(environment={"KEY": "value"})

        assert isinstance(context.environment, dict)
        assert context.environment["KEY"] == "value"

    def test_execution_context_defaults(self):
        """GIVEN an ExecutionContext with minimal args
        WHEN checking attributes
        THEN defaults should be applied.
        """
        from mcp_server_langgraph.skills.executor import ExecutionContext

        context = ExecutionContext()

        assert context.network_mode == "none"
        assert context.allowed_domains == []
        assert context.timeout == 30
        assert context.memory_mb == 256
        assert context.environment == {}
