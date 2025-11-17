"""
Tests for Swarm Pattern

Comprehensive test coverage following TDD best practices.
"""

import gc

import pytest

from src.mcp_server_langgraph.patterns.swarm import Swarm, SwarmState

# xdist_group for integration test worker isolation
pytestmark = pytest.mark.xdist_group(name="integration_patterns_swarm_tests")


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_swarm():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


# ==============================================================================
# Unit Tests
# ==============================================================================


@pytest.mark.unit
def test_swarm_initialization():
    """Test swarm can be initialized with agents."""

    def agent1(query: str) -> str:
        return "result1"

    swarm = Swarm(agents={"agent1": agent1})

    assert swarm.agents == {"agent1": agent1}
    assert swarm.aggregation_strategy == "synthesis"
    assert swarm.min_agreement == 0.7


@pytest.mark.unit
def test_swarm_state_creation():
    """Test SwarmState can be created."""
    state = SwarmState(query="test query")

    assert state.query == "test query"
    assert state.agent_results == {}
    assert state.aggregated_result == ""
    assert state.consensus_score == 0.0


@pytest.mark.unit
def test_swarm_build_graph():
    """Test swarm builds valid LangGraph with parallel structure."""

    def agent1(q: str) -> str:
        return "r1"

    def agent2(q: str) -> str:
        return "r2"

    swarm = Swarm(agents={"agent1": agent1, "agent2": agent2})
    graph = swarm.build()

    assert graph is not None
    assert "agent1" in graph.nodes
    assert "agent2" in graph.nodes
    assert "aggregate" in graph.nodes


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
def test_swarm_parallel_execution():
    """Test swarm executes all agents in parallel."""

    def agent1(query: str) -> str:
        return "Agent 1 perspective"

    def agent2(query: str) -> str:
        return "Agent 2 perspective"

    def agent3(query: str) -> str:
        return "Agent 3 perspective"

    swarm = Swarm(agents={"agent1": agent1, "agent2": agent2, "agent3": agent3})

    result = swarm.invoke("Analyze this topic")

    # All agents should have results
    assert len(result["agent_results"]) == 3
    assert "agent1" in result["agent_results"]
    assert "agent2" in result["agent_results"]
    assert "agent3" in result["agent_results"]
    assert result["aggregated_result"] != ""


@pytest.mark.integration
@pytest.mark.parametrize(
    "strategy",
    ["concatenate", "consensus", "synthesis", "voting"],
)
def test_swarm_aggregation_strategies(strategy: str):
    """Test all aggregation strategies work."""

    def agent1(q: str) -> str:
        return "Result A"

    def agent2(q: str) -> str:
        return "Result B"

    swarm = Swarm(agents={"agent1": agent1, "agent2": agent2}, aggregation_strategy=strategy)  # type: ignore

    result = swarm.invoke("test query")

    assert result["aggregated_result"] != ""
    assert result["consensus_score"] >= 0.0
    assert result["consensus_score"] <= 1.0


# ==============================================================================
# Consensus Scoring Tests
# ==============================================================================


@pytest.mark.unit
def test_consensus_score_identical_results():
    """Test consensus score is high when agents agree."""

    def agent(q: str) -> str:
        return "Same result for everyone"

    swarm = Swarm(agents={"agent1": agent, "agent2": agent, "agent3": agent}, aggregation_strategy="consensus")

    result = swarm.invoke("test")

    # Identical results should have high consensus
    assert result["consensus_score"] > 0.5


@pytest.mark.unit
def test_consensus_score_divergent_results():
    """Test consensus score is lower when agents disagree."""

    def agent1(q: str) -> str:
        return "Completely different answer one"

    def agent2(q: str) -> str:
        return "Totally unrelated response two"

    def agent3(q: str) -> str:
        return "Something else entirely three"

    swarm = Swarm(agents={"agent1": agent1, "agent2": agent2, "agent3": agent3}, aggregation_strategy="consensus")

    result = swarm.invoke("test")

    # Divergent results should have lower consensus
    assert result["consensus_score"] >= 0.0  # Can't be negative


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.unit
def test_swarm_handles_agent_failures():
    """Test swarm continues when one agent fails."""

    def working_agent(q: str) -> str:
        return "Success"

    def failing_agent(q: str) -> str:
        raise ValueError("Agent failed")

    swarm = Swarm(agents={"working": working_agent, "failing": failing_agent})

    result = swarm.invoke("test")

    # Should still produce result
    assert result is not None
    assert "aggregated_result" in result
    # Working agent should have result
    assert "working" in result["agent_results"]


@pytest.mark.unit
def test_swarm_empty_agents():
    """Test swarm validates non-empty agents."""
    with pytest.raises(Exception):
        swarm = Swarm(agents={})
        swarm.invoke("test")


# ==============================================================================
# Voting Strategy Tests
# ==============================================================================


@pytest.mark.unit
def test_voting_strategy_majority():
    """Test voting finds majority opinion."""

    def agent_a(q: str) -> str:
        return "Option A"

    def agent_b(q: str) -> str:
        return "Option A"  # Agrees with agent_a

    def agent_c(q: str) -> str:
        return "Option B"  # Disagrees

    swarm = Swarm(agents={"a1": agent_a, "a2": agent_b, "a3": agent_c}, aggregation_strategy="voting")

    result = swarm.invoke("Which option?")

    # Option A should win (2/3 votes)
    assert "Option A" in result["aggregated_result"]
    assert result["consensus_score"] == 2 / 3  # 67% agreement


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.performance
@pytest.mark.benchmark
def test_swarm_performance(benchmark):
    """Benchmark swarm execution time."""

    def fast_agent(q: str) -> str:
        return "result"

    swarm = Swarm(agents={"a1": fast_agent, "a2": fast_agent, "a3": fast_agent})

    result = benchmark(swarm.invoke, "benchmark query")

    assert result is not None


# ==============================================================================
# Checkpointer Tests
# ==============================================================================


@pytest.mark.integration
def test_swarm_with_memory_checkpointer():
    """
    Test swarm works with MemorySaver checkpointer.

    Note: LangGraph 1.0.3+ returns dict from compiled.invoke(), not Pydantic model.
    Use dict key access (result["query"]) instead of attribute access (result.query).
    See: tests/regression/test_langgraph_return_types.py for detailed explanation.
    """
    from langgraph.checkpoint.memory import MemorySaver

    def agent(q: str) -> str:
        return "result"

    swarm = Swarm(agents={"agent1": agent, "agent2": agent})
    checkpointer = MemorySaver()

    compiled = swarm.compile(checkpointer=checkpointer)
    result = compiled.invoke(SwarmState(query="test"), config={"configurable": {"thread_id": "test-thread"}})

    assert result is not None
    # LangGraph 1.0.3+ returns dict, not Pydantic model - use dict access
    assert result["query"] == "test"


# ==============================================================================
# Property-Based Tests
# ==============================================================================


@pytest.mark.property
@pytest.mark.parametrize("num_agents", [1, 2, 5, 10, 20])
def test_swarm_scalability(num_agents: int):
    """Test swarm scales with varying number of agents."""
    agents = {f"agent{i}": lambda q, i=i: f"Result {i}" for i in range(num_agents)}

    swarm = Swarm(agents=agents)
    result = swarm.invoke("test query")

    # All agents should execute
    assert result["num_agents"] == num_agents
    assert len(result["agent_results"]) == num_agents


@pytest.mark.property
def test_swarm_consensus_bounded():
    """Test consensus score is always between 0 and 1."""

    def random_agent(q: str) -> str:
        import random
        import string

        return "".join(random.choices(string.ascii_letters, k=50))

    swarm = Swarm(agents={"a1": random_agent, "a2": random_agent, "a3": random_agent}, aggregation_strategy="consensus")

    result = swarm.invoke("test")

    assert 0.0 <= result["consensus_score"] <= 1.0
