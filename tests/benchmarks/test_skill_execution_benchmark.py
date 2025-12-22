"""
Skill Execution Performance Benchmarks

Tests performance characteristics of skill loading, discovery,
and execution to ensure acceptable latency for real-time use.

Performance Targets:
- Skill loading: <10ms per skill
- Skill discovery: <5ms for search
- Registry operations: <1ms per operation
"""

import gc
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Domain marker only - benchmark/performance markers auto-applied by conftest.py
pytestmark = pytest.mark.skills


def create_test_skill(name: str, description: str = "Test skill") -> "Skill":
    """Create a test skill for benchmarking."""
    from mcp_server_langgraph.skills.models import Skill

    return Skill(
        name=name,
        description=description,
        instructions=f"Instructions for {name}. " * 50,
        version="1.0.0",
        tags=["test", "benchmark", name],
    )


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_skill_registry")
class TestSkillRegistryBenchmarks:
    """Benchmark suite for skill registry operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_registry_register(self, benchmark):
        """Benchmark registering skills in registry."""
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        skills = [create_test_skill(f"skill_{i}") for i in range(100)]

        def register_all():
            for skill in skills:
                registry.register(skill)
            return registry

        result = benchmark(register_all)

        assert len(list(result.list_all())) == 100

    def test_benchmark_registry_get(self, benchmark):
        """Benchmark retrieving skills from registry."""
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        for i in range(100):
            registry.register(create_test_skill(f"skill_{i}"))

        def get_all():
            results = []
            for i in range(100):
                results.append(registry.get(f"skill_{i}"))
            return results

        result = benchmark(get_all)

        assert len(result) == 100
        assert all(s is not None for s in result)

    def test_benchmark_registry_list(self, benchmark):
        """Benchmark listing all skills from registry."""
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        for i in range(100):
            registry.register(create_test_skill(f"skill_{i}"))

        result = benchmark(registry.list_all)

        assert len(list(result)) == 100


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_skill_discovery")
class TestSkillDiscoveryBenchmarks:
    """Benchmark suite for skill discovery operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_discovery_search(self, benchmark):
        """Benchmark searching skills."""
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        for i in range(50):
            skill = create_test_skill(
                f"skill_{i}",
                f"Description {i} with keyword{'alpha' if i % 2 == 0 else 'beta'}",
            )
            registry.register(skill)

        discovery = SkillDiscovery(registry)

        result = benchmark(discovery.search, "alpha")

        assert len(result) > 0

    def test_benchmark_discovery_get_summaries(self, benchmark):
        """Benchmark getting skill summaries (progressive disclosure)."""
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        for i in range(100):
            registry.register(create_test_skill(f"skill_{i}"))

        discovery = SkillDiscovery(registry)

        result = benchmark(discovery.get_skill_summaries)

        assert len(result) == 100

    def test_benchmark_discovery_get_skill(self, benchmark):
        """Benchmark getting full skill details."""
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        for i in range(50):
            registry.register(create_test_skill(f"skill_{i}"))

        discovery = SkillDiscovery(registry)

        # Get middle skill
        result = benchmark(discovery.get_skill, "skill_25")

        assert result is not None
        assert result.name == "skill_25"


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_skill_executor")
class TestSkillExecutorBenchmarks:
    """Benchmark suite for skill executor operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_executor_prepare_context(self, benchmark):
        """Benchmark preparing execution context."""
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import SandboxConfig, Skill

        executor = SkillExecutor()
        skill = Skill(
            name="test_skill",
            description="Test skill",
            instructions="Test instructions",
            sandbox_config=SandboxConfig(
                network="allowlist",
                allowed_domains=["api.example.com", "data.example.org"],
                timeout_seconds=30,
                memory_mb=512,
            ),
            required_secrets=["API_KEY", "DB_URL"],
        )
        secrets = {"API_KEY": "test_key", "DB_URL": "postgres://localhost/test"}

        result = benchmark(executor.prepare_context, skill, secrets)

        assert result.network_mode == "allowlist"
        assert len(result.allowed_domains) == 2

    def test_benchmark_executor_validate_secrets(self, benchmark):
        """Benchmark validating secrets."""
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="test_skill",
            description="Test skill",
            instructions="Test instructions",
            required_secrets=["API_KEY", "DB_URL", "CACHE_URL"],
        )
        secrets = {"API_KEY": "key1", "DB_URL": "url1", "CACHE_URL": "url2"}

        result = benchmark(executor.validate_secrets, skill, secrets)

        assert result.is_valid

    def test_benchmark_executor_validate_script(self, benchmark):
        """Benchmark validating script existence."""
        from mcp_server_langgraph.skills.executor import SkillExecutor
        from mcp_server_langgraph.skills.models import Skill

        executor = SkillExecutor()
        skill = Skill(
            name="test_skill",
            description="Test skill",
            instructions="Test instructions",
            scripts=["main.py", "helper.py", "utils.py"],
        )

        def validate_scripts():
            results = []
            for script in ["main.py", "helper.py", "utils.py", "missing.py"]:
                results.append(executor.validate_script(skill, script))
            return results

        result = benchmark(validate_scripts)

        assert result == [True, True, True, False]


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_skill_loader")
class TestSkillLoaderBenchmarks:
    """Benchmark suite for skill loading operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_parse_skill_md(self, benchmark):
        """Benchmark parsing SKILL.md content."""
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skill_md = '''---
name: web-research
description: Research topics using web search
version: "1.0.0"
author: "Test Author"
tags:
  - research
  - web
  - search
---

# Web Research Skill

This skill allows agents to research topics using web search.

## Usage

1. Provide a topic to research
2. The agent will search the web
3. Results are summarized

## Examples

- Research quantum computing advances
- Find latest AI news
'''

        result = benchmark(loader.parse_skill_content, skill_md)

        assert result is not None
        assert result.name == "web-research"

    def test_benchmark_load_from_file(self, benchmark):
        """Benchmark loading skill from file."""
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()

        # Create temporary skill file
        skill_content = '''---
name: benchmark-skill
description: Skill for benchmarking
version: "1.0.0"
---

# Benchmark Skill

Instructions for the benchmark skill.
'''

        with TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "SKILL.md"
            skill_path.write_text(skill_content)

            result = benchmark(loader.load_from_path, str(skill_path))

            assert result is not None
            assert result.name == "benchmark-skill"
