"""
Multi-Agent Orchestration Performance Benchmarks

Tests performance characteristics of multi-agent patterns including
orchestrator-worker, parallel execution, and coordination.

Performance Targets:
- Agent creation: <50ms per agent
- Task delegation: <10ms per task
- Coordinator operations: <5ms per operation
- Model selection: <1ms per selection
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.agents.artifacts import ArtifactStorage
from mcp_server_langgraph.agents.coordinator import Coordinator
from mcp_server_langgraph.agents.model_selector import ModelSelector
from mcp_server_langgraph.agents.orchestrator import Orchestrator, Subtask, TaskDecomposition
from mcp_server_langgraph.agents.subagent import Subagent, SubagentStatus

# Domain marker only - benchmark/performance markers auto-applied by conftest.py
pytestmark = pytest.mark.agents


def create_mock_subagent(
    task_id: str,
    status: SubagentStatus = SubagentStatus.PENDING,
) -> MagicMock:
    """Create a mock subagent for benchmarking.

    Args:
        task_id: Unique task identifier
        status: Subagent status

    Returns:
        Mock subagent instance
    """
    subagent = MagicMock(spec=Subagent)
    subagent.task_id = task_id
    subagent.status = status
    subagent.execute = AsyncMock(return_value={"status": "completed", "result": f"Result from {task_id}"})
    subagent.cancel = MagicMock()
    return subagent


def create_mock_task(task_id: str, complexity: str = "simple") -> dict[str, Any]:
    """Create a mock task for benchmarking.

    Args:
        task_id: Unique task identifier
        complexity: Task complexity (simple, complicated, complex)

    Returns:
        Task dictionary
    """
    return {
        "id": task_id,
        "type": "research",
        "complexity": complexity,
        "input": f"Research task {task_id}",
        "metadata": {"priority": 1, "timeout": 30},
    }


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_orchestrator")
class TestOrchestratorBenchmarks:
    """Benchmark suite for orchestrator operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_orchestrator_creation(self, benchmark):
        """Benchmark creating an orchestrator agent."""

        def create_orchestrator():
            return Orchestrator()

        result = benchmark(create_orchestrator)
        assert result is not None
        assert result.coordinator is not None
        assert result.model_selector is not None

    def test_benchmark_task_decomposition(self, benchmark):
        """Benchmark decomposing a task into subtasks."""
        orchestrator = Orchestrator()

        def create_decomposition():
            return TaskDecomposition(
                original_task="Complex research task about AI agents",
                subtasks=[
                    Subtask(
                        task_id=f"subtask-{i}",
                        title=f"Subtask {i}",
                        instructions=f"Research aspect {i} of the topic",
                        complexity="simple",
                    )
                    for i in range(5)
                ],
                synthesis_instructions="Combine all subtask results",
            )

        result = benchmark(create_decomposition)
        assert len(result.subtasks) == 5

    def test_benchmark_scale_effort(self, benchmark):
        """Benchmark the scale_effort calculation."""
        orchestrator = Orchestrator()

        task = "Comprehensive thorough detailed analyze research investigate compare multiple"

        def scale():
            return orchestrator.scale_effort(task)

        result = benchmark(scale)
        assert result >= 1
        assert result <= 10


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_subagent")
class TestSubagentBenchmarks:
    """Benchmark suite for subagent operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_subagent_creation(self, benchmark):
        """Benchmark creating a worker subagent."""

        def create_subagent():
            return Subagent(
                task_id="bench_worker",
                instructions="Perform a research task",
            )

        result = benchmark(create_subagent)
        assert result is not None
        assert result.task_id == "bench_worker"

    def test_benchmark_subagent_batch_creation(self, benchmark):
        """Benchmark creating multiple subagents."""

        def create_batch():
            return [
                Subagent(
                    task_id=f"worker_{i}",
                    instructions=f"Task {i} instructions",
                )
                for i in range(10)
            ]

        result = benchmark(create_batch)
        assert len(result) == 10


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_coordinator")
class TestCoordinatorBenchmarks:
    """Benchmark suite for task coordination."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_coordinator_creation(self, benchmark):
        """Benchmark creating a coordinator."""

        def create_coordinator():
            return Coordinator()

        result = benchmark(create_coordinator)
        assert result is not None
        assert result.artifact_storage is not None

    def test_benchmark_register_subagents(self, benchmark):
        """Benchmark registering subagents."""
        coordinator = Coordinator()

        # Pre-create subagents
        subagents = [create_mock_subagent(f"task-{i}") for i in range(50)]

        def register_all():
            for sa in subagents:
                coordinator.register_subagent(sa)
            return coordinator.list_subagents()

        result = benchmark(register_all)
        assert len(result) >= 50

    def test_benchmark_status_summary(self, benchmark):
        """Benchmark getting status summary."""
        coordinator = Coordinator()

        # Register subagents with mixed statuses
        for i in range(20):
            sa = create_mock_subagent(f"task-{i}", SubagentStatus.PENDING)
            coordinator.register_subagent(sa)
        for i in range(20, 40):
            sa = create_mock_subagent(f"task-{i}", SubagentStatus.COMPLETED)
            coordinator.register_subagent(sa)

        def get_summary():
            return coordinator.get_status_summary()

        result = benchmark(get_summary)
        assert "pending" in result or "completed" in result


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_model_selector")
class TestModelSelectorBenchmarks:
    """Benchmark suite for model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_model_selection(self, benchmark):
        """Benchmark selecting model based on task complexity."""
        selector = ModelSelector()

        def select():
            return selector.select_model("complicated")

        result = benchmark(select)
        assert result is not None

    def test_benchmark_model_selection_batch(self, benchmark):
        """Benchmark selecting models for multiple tasks."""
        selector = ModelSelector()

        complexities = ["simple"] * 30 + ["complicated"] * 15 + ["complex"] * 5

        def select_all():
            return [selector.select_model(c) for c in complexities]

        result = benchmark(select_all)
        assert len(result) == 50

    def test_benchmark_verifier_selection(self, benchmark):
        """Benchmark selecting verifier model."""
        selector = ModelSelector()

        def select_verifier():
            return selector.select_verifier("auto")

        result = benchmark(select_verifier)
        assert result is not None


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_artifacts")
class TestArtifactBenchmarks:
    """Benchmark suite for artifact storage operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_artifact_store(self, benchmark):
        """Benchmark storing artifacts from subagents."""
        storage = ArtifactStorage()

        def store_artifacts():
            for i in range(50):
                storage.store(
                    task_id=f"task-{i % 5}",
                    name=f"artifact_{i}",
                    data=f"Result content for artifact {i}" * 100,
                    metadata={"type": "research", "size": 1000},
                )
            return storage

        result = benchmark(store_artifacts)
        assert result is not None

    def test_benchmark_artifact_retrieve(self, benchmark):
        """Benchmark retrieving artifacts."""
        storage = ArtifactStorage()

        # Pre-populate
        for i in range(50):
            storage.store(
                task_id=f"task-{i % 10}",
                name=f"artifact_{i}",
                data=f"Content {i}",
            )

        def retrieve_all():
            return [storage.retrieve(f"task-{i % 10}", f"artifact_{i}") for i in range(50)]

        result = benchmark(retrieve_all)
        assert len(result) == 50
        assert all(r is not None for r in result)

    def test_benchmark_list_artifacts(self, benchmark):
        """Benchmark listing artifacts for a task."""
        storage = ArtifactStorage()

        # Pre-populate with artifacts for one task
        for i in range(20):
            storage.store(
                task_id="main-task",
                name=f"artifact_{i}",
                data=f"Research findings {i}: " + "Lorem ipsum " * 50,
                metadata={"type": "research"},
            )

        def list_all():
            return storage.list_for_task("main-task")

        result = benchmark(list_all)
        assert len(result) == 20


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_parallel_execution")
class TestParallelExecutionBenchmarks:
    """Benchmark suite for parallel agent execution patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_parallel_task_creation(self, benchmark):
        """Benchmark creating parallel task decomposition."""

        def create_parallel_decomposition():
            return TaskDecomposition(
                original_task="Multi-perspective analysis",
                subtasks=[
                    Subtask(
                        task_id=f"perspective-{i}",
                        title=f"Analysis from {focus} perspective",
                        instructions=f"Analyze the topic from a {focus} perspective",
                        complexity="complicated",
                    )
                    for i, focus in enumerate(
                        [
                            "security",
                            "performance",
                            "usability",
                            "reliability",
                            "scalability",
                        ]
                    )
                ],
            )

        result = benchmark(create_parallel_decomposition)
        assert len(result.subtasks) == 5

    def test_benchmark_coordinator_batch_register(self, benchmark):
        """Benchmark batch registration and listing."""
        coordinator = Coordinator()

        def batch_operations():
            # Register 10 subagents
            for i in range(10):
                sa = create_mock_subagent(f"parallel-{i}")
                coordinator.register_subagent(sa)

            # Get summary
            summary = coordinator.get_status_summary()

            # List all
            agents = coordinator.list_subagents()

            return {"summary": summary, "agents": agents}

        result = benchmark(batch_operations)
        assert len(result["agents"]) >= 10
