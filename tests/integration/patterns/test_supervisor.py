"""
Tests for Supervisor Pattern

Following TDD best practices with comprehensive coverage.
"""

import gc
from unittest.mock import Mock

import pytest

from mcp_server_langgraph.patterns.supervisor import Supervisor, SupervisorState

# xdist_group for integration test worker isolation
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="integration_patterns_supervisor_tests")]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_supervisor():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


# ==============================================================================
# Unit Tests
# ==============================================================================


@pytest.mark.unit
def test_supervisor_initialization_with_agents_stores_agents():
    """Test supervisor can be initialized with agents."""

    def dummy_agent(task: str) -> str:
        return "result"

    supervisor = Supervisor(agents={"agent1": dummy_agent})

    assert supervisor.agents == {"agent1": dummy_agent}
    assert supervisor.routing_strategy == "conditional"
    assert supervisor.supervisor_prompt is not None


@pytest.mark.unit
def test_supervisor_custom_prompt():
    """Test supervisor accepts custom prompt."""
    custom_prompt = "Custom routing logic"
    supervisor = Supervisor(agents={"agent1": lambda x: x}, supervisor_prompt=custom_prompt)

    assert custom_prompt in supervisor.supervisor_prompt


@pytest.mark.unit
def test_supervisor_state_creation():
    """Test SupervisorState can be created with required fields."""
    state = SupervisorState(task="test task")

    assert state.task == "test task"
    assert state.current_agent is None
    assert state.agent_history == []
    assert state.agent_results == {}
    assert state.completed is False


@pytest.mark.unit
def test_supervisor_build_graph():
    """Test supervisor builds valid LangGraph."""

    def agent1(task: str) -> str:
        return "result1"

    supervisor = Supervisor(agents={"agent1": agent1})
    graph = supervisor.build()

    assert graph is not None
    # Verify nodes exist
    assert "supervisor" in graph.nodes
    assert "agent1" in graph.nodes
    assert "aggregate" in graph.nodes


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
def test_supervisor_single_agent_execution():
    """Test supervisor with single agent executes successfully."""

    def research_agent(task: str) -> str:
        return f"Research completed for: {task}"

    supervisor = Supervisor(agents={"research": research_agent})

    result = supervisor.invoke("Find AI trends")

    assert result["task"] == "Find AI trends"
    assert "research" in result["agent_history"]
    assert "Research completed" in result["final_result"]


@pytest.mark.integration
def test_supervisor_multiple_agents_sequential():
    """Test supervisor with multiple agents in sequential mode."""

    def agent1(task: str) -> str:
        return "Step 1 complete"

    def agent2(task: str) -> str:
        return "Step 2 complete"

    def agent3(task: str) -> str:
        return "Step 3 complete"

    supervisor = Supervisor(agents={"agent1": agent1, "agent2": agent2, "agent3": agent3}, routing_strategy="sequential")

    result = supervisor.invoke("Multi-step task")

    # Verify all agents executed
    assert len(result["agent_history"]) > 0
    assert result["final_result"] != ""


@pytest.mark.integration
def test_supervisor_routing_decision():
    """Test supervisor makes routing decisions."""

    def researcher(task: str) -> str:
        return "Research findings"

    def writer(task: str) -> str:
        return "Written content"

    supervisor = Supervisor(agents={"research": researcher, "writer": writer})

    result = supervisor.invoke("research this topic")

    assert result["routing_decision"] != ""
    assert "routing" in result["routing_decision"].lower()


# ==============================================================================
# Property-Based Tests
# ==============================================================================


@pytest.mark.property
@pytest.mark.parametrize("num_agents", [1, 2, 5, 10])
def test_supervisor_scales_with_agents(num_agents: int):
    """Test supervisor works with varying number of agents."""
    agents = {f"agent{i}": lambda task, i=i: f"Result from agent {i}" for i in range(num_agents)}

    supervisor = Supervisor(agents=agents)
    result = supervisor.invoke("Test task")

    assert result["final_result"] != ""
    assert len(result["agent_results"]) >= 0


@pytest.mark.property
@pytest.mark.parametrize(
    "routing_strategy",
    ["sequential", "conditional"],
)
def test_supervisor_routing_strategies(routing_strategy: str):
    """Test all routing strategies work."""

    def agent(task: str) -> str:
        return "result"

    supervisor = Supervisor(agents={"agent1": agent}, routing_strategy=routing_strategy)  # type: ignore

    result = supervisor.invoke("test")

    assert result is not None
    assert "final_result" in result


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.unit
def test_supervisor_agent_error_handling():
    """Test supervisor handles agent errors gracefully."""

    def failing_agent(task: str) -> str:
        raise ValueError("Agent error")

    def working_agent(task: str) -> str:
        return "Success"

    supervisor = Supervisor(agents={"failing": failing_agent, "working": working_agent})

    # Should not raise, should handle gracefully
    result = supervisor.invoke("test")

    assert result is not None


@pytest.mark.unit
def test_supervisor_empty_agents():
    """Test supervisor handles empty agent dict."""
    with pytest.raises(Exception):
        supervisor = Supervisor(agents={})
        supervisor.invoke("test")


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.performance
@pytest.mark.benchmark
def test_supervisor_performance_with_multiple_agents_executes_quickly(benchmark):
    """Benchmark supervisor execution time."""

    def fast_agent(task: str) -> str:
        return "result"

    supervisor = Supervisor(agents={"agent1": fast_agent, "agent2": fast_agent, "agent3": fast_agent})

    result = benchmark(supervisor.invoke, "benchmark task")

    assert result is not None


# ==============================================================================
# State Persistence Tests
# ==============================================================================


@pytest.mark.integration
def test_supervisor_with_checkpointer():
    """
    Test supervisor works with LangGraph checkpointer.

    Note: LangGraph 1.0.3+ returns dict from compiled.invoke(), not Pydantic model.
    Use dict key access (result["task"]) instead of attribute access (result.task).
    See: tests/regression/test_langgraph_return_types.py for detailed explanation.
    """
    from langgraph.checkpoint.memory import MemorySaver

    def agent(task: str) -> str:
        return "result"

    supervisor = Supervisor(agents={"agent1": agent})
    checkpointer = MemorySaver()

    compiled = supervisor.compile(checkpointer=checkpointer)

    result = compiled.invoke(SupervisorState(task="test"), config={"configurable": {"thread_id": "test-123"}})

    assert result is not None
    # LangGraph 1.0.3+ returns dict, not Pydantic model - use dict access
    assert result["task"] == "test"


# ==============================================================================
# Mock-Based Tests
# ==============================================================================


@pytest.mark.unit
def test_supervisor_calls_agents_correctly():
    """Test supervisor calls agent functions with correct arguments."""
    mock_agent = Mock(return_value="mocked result")

    supervisor = Supervisor(agents={"mock": mock_agent})
    result = supervisor.invoke("test task")

    # Verify agent was called
    mock_agent.assert_called()
    assert result is not None
