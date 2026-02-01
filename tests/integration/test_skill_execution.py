"""
Integration tests for E2E Skill Execution

Tests the complete skill execution flow from SKILL.md loading
through Docker sandbox execution.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skills]

# Skip Docker tests if Docker is not available
DOCKER_AVAILABLE = os.path.exists("/var/run/docker.sock")


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_skill_e2e")
class TestSkillE2EExecution:
    """Test suite for end-to-end skill execution"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def skill_directory(self, tmp_path: Path) -> Path:
        """Create a temporary skill directory with SKILL.md and script."""
        skill_dir = tmp_path / "web-research"
        skill_dir.mkdir()

        # Create SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: web-research
description: Research topics using web search
version: 1.0.0
scripts:
  - search.py
sandbox_config:
  network: none
  timeout_seconds: 30
  memory_mb: 256
---

# Web Research Skill

Use this skill to research topics on the web.
""")

        # Create script
        script_file = skill_dir / "search.py"
        script_file.write_text("""
# Simple test script
import json

query = SKILL_ARGS.get("query", "default query")
print(json.dumps({"result": f"Searched for: {query}", "status": "success"}))
""")

        return skill_dir

    def test_load_skill_from_directory(self, skill_directory: Path):
        """GIVEN a skill directory with SKILL.md
        WHEN loading the skill
        THEN the skill should be loaded with correct metadata
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_directory)

        assert skill.name == "web-research"
        assert skill.description == "Research topics using web search"
        assert skill.path == skill_directory

    def test_executor_loads_script_content(self, skill_directory: Path):
        """GIVEN a skill with scripts
        WHEN loading script content
        THEN the actual script content should be returned
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_directory)
        # Ensure scripts list is populated
        skill.scripts = ["search.py"]

        executor = SkillExecutor()
        content = executor.load_script_content(skill, "search.py")

        assert content is not None
        assert "SKILL_ARGS" in content
        assert "json.dumps" in content

    @pytest.mark.asyncio
    async def test_execute_skill_with_mock_sandbox(self, skill_directory: Path):
        """GIVEN a skill and mock sandbox
        WHEN executing the skill
        THEN the sandbox should be called with correct code
        """
        from mcp_server_langgraph.execution.sandbox import ExecutionResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Load skill
        loader = SkillLoader()
        skill = loader.load_from_directory(skill_directory)
        skill.scripts = ["search.py"]

        # Create mock sandbox
        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                stdout='{"result": "Searched for: test query", "status": "success"}',
                stderr="",
            )
        )

        # Execute
        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        result = await executor.execute(skill, "search.py", args={"query": "test query"})

        # Verify
        assert result.success is True
        assert "test query" in (result.output or "")
        mock_sandbox.aexecute.assert_called_once()

        # Verify the code passed to sandbox contains actual script
        call_args = mock_sandbox.aexecute.call_args
        code = call_args[0][0]
        assert "SKILL_ARGS" in code
        assert "test query" in code

    @pytest.mark.asyncio
    async def test_execute_skill_handles_missing_script(self, skill_directory: Path):
        """GIVEN a skill
        WHEN executing a non-existent script
        THEN an error should be returned
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_directory)
        skill.scripts = ["search.py"]

        executor = SkillExecutor()

        # Execute non-existent script
        result = await executor.execute(skill, "nonexistent.py")

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_skill_validates_required_secrets(self, tmp_path: Path):
        """GIVEN a skill with required secrets
        WHEN executing without providing secrets
        THEN an error should be returned
        """
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create skill with required secrets
        skill_dir = tmp_path / "db-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: db-skill
description: Database operations
required_secrets:
  - DATABASE_URL
  - API_KEY
scripts:
  - connect.py
---

# Database Skill
""")
        script = skill_dir / "connect.py"
        script.write_text("print('connecting...')")

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_dir)
        skill.scripts = ["connect.py"]

        executor = SkillExecutor()

        # Execute without secrets
        result = await executor.execute(skill, "connect.py")

        assert result.success is False
        assert "secret" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_skill_injects_args(self, skill_directory: Path):
        """GIVEN a skill with a script
        WHEN executing with args
        THEN args should be available as SKILL_ARGS
        """
        from mcp_server_langgraph.execution.sandbox import ExecutionResult
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_directory)
        skill.scripts = ["search.py"]

        # Create mock sandbox that captures the code
        captured_code = []

        async def capture_code(code: str) -> ExecutionResult:
            captured_code.append(code)
            return ExecutionResult(success=True, stdout="OK")

        mock_sandbox = MagicMock()
        mock_sandbox.aexecute = AsyncMock(side_effect=capture_code)

        executor = SkillExecutor()
        executor.set_sandbox(mock_sandbox)

        await executor.execute(
            skill,
            "search.py",
            args={"query": "test topic", "max_results": 10},
        )

        # Verify args were injected
        assert len(captured_code) == 1
        code = captured_code[0]
        assert "SKILL_ARGS" in code
        assert "test topic" in code
        assert "10" in code


@pytest.mark.integration
@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
@pytest.mark.xdist_group(name="test_skill_docker")
class TestSkillDockerExecution:
    """Test suite for skill execution with real Docker sandbox"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def simple_skill_directory(self, tmp_path: Path) -> Path:
        """Create a simple skill for Docker testing."""
        skill_dir = tmp_path / "simple-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: simple-skill
description: A simple test skill
scripts:
  - hello.py
sandbox_config:
  network: none
  timeout_seconds: 30
  memory_mb: 256
---

# Simple Skill

A test skill that prints a greeting.
""")

        script = skill_dir / "hello.py"
        script.write_text("""
import json

name = SKILL_ARGS.get("name", "World")
result = {"message": f"Hello, {name}!", "status": "success"}
print(json.dumps(result))
""")

        return skill_dir

    @pytest.mark.asyncio
    async def test_execute_skill_in_docker_sandbox(self, simple_skill_directory: Path):
        """GIVEN a skill and Docker sandbox
        WHEN executing the skill
        THEN the script should run in Docker and return output
        """
        from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
        from mcp_server_langgraph.execution.resource_limits import ResourceLimits
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Load skill
        loader = SkillLoader()
        skill = loader.load_from_directory(simple_skill_directory)
        skill.scripts = ["hello.py"]

        # Create Docker sandbox
        limits = ResourceLimits.testing()
        sandbox = DockerSandbox(limits=limits)

        # Execute
        executor = SkillExecutor()
        executor.set_sandbox(sandbox)

        result = await executor.execute(skill, "hello.py", args={"name": "Claude"})

        # Verify
        assert result.success is True
        assert "Claude" in (result.output or "")
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_docker_skill_timeout_handling(self, tmp_path: Path):
        """GIVEN a skill that takes too long
        WHEN executing with a short timeout
        THEN the execution should be terminated
        """
        from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
        from mcp_server_langgraph.execution.resource_limits import ResourceLimits
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create slow skill
        skill_dir = tmp_path / "slow-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: slow-skill
description: A slow skill for testing timeouts
scripts:
  - slow.py
sandbox_config:
  network: none
  timeout_seconds: 2
  memory_mb: 256
---

# Slow Skill
""")

        script = skill_dir / "slow.py"
        script.write_text("""
import time
time.sleep(10)  # noqa: sleep-duration - Intentionally slow to test sandbox timeout
print("Done")
""")

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_dir)
        skill.scripts = ["slow.py"]

        # Create sandbox with short timeout
        limits = ResourceLimits(timeout_seconds=2, memory_limit_mb=256)
        sandbox = DockerSandbox(limits=limits)

        executor = SkillExecutor()
        executor.set_sandbox(sandbox)

        result = await executor.execute(skill, "slow.py")

        # Should fail due to timeout
        assert result.success is False
        # The sandbox should have timed out

    @pytest.mark.asyncio
    async def test_docker_skill_network_isolation(self, tmp_path: Path):
        """GIVEN a skill with network: none
        WHEN executing network operations
        THEN the operations should fail
        """
        from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
        from mcp_server_langgraph.execution.resource_limits import ResourceLimits
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create skill that tries network access
        skill_dir = tmp_path / "network-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: network-skill
description: A skill that tries network access
scripts:
  - fetch.py
sandbox_config:
  network: none
  timeout_seconds: 10
  memory_mb: 256
---

# Network Skill
""")

        script = skill_dir / "fetch.py"
        script.write_text("""
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=5)
    print("Network access succeeded (UNEXPECTED)")
except Exception as e:
    print(f"Network blocked as expected: {type(e).__name__}")
""")

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_dir)
        skill.scripts = ["fetch.py"]

        # Create sandbox with no network
        limits = ResourceLimits(
            timeout_seconds=10,
            memory_limit_mb=256,
            network_mode="none",
        )
        sandbox = DockerSandbox(limits=limits)

        executor = SkillExecutor()
        executor.set_sandbox(sandbox)

        result = await executor.execute(skill, "fetch.py")

        # Should succeed (script handles the error)
        # But verify network was blocked
        assert result.success is True
        assert "blocked" in (result.output or "").lower() or "error" in (result.output or "").lower()
