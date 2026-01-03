"""
Tests for SwarmOrchestrator

TDD: These tests define the contract for multi-agent orchestration with
race, cascade, and consensus strategies.
"""

from __future__ import annotations

import asyncio
import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="swarm_strategy")
class TestSwarmStrategy:
    """Tests for SwarmStrategy enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_swarm_strategy_exists(self) -> None:
        """Test that SwarmStrategy enum exists."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmStrategy

        assert SwarmStrategy is not None

    def test_swarm_strategy_has_race(self) -> None:
        """Test SwarmStrategy has RACE value."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmStrategy

        assert SwarmStrategy.RACE is not None
        assert SwarmStrategy.RACE.value == "race"

    def test_swarm_strategy_has_cascade(self) -> None:
        """Test SwarmStrategy has CASCADE value."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmStrategy

        assert SwarmStrategy.CASCADE is not None
        assert SwarmStrategy.CASCADE.value == "cascade"

    def test_swarm_strategy_has_consensus(self) -> None:
        """Test SwarmStrategy has CONSENSUS value."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmStrategy

        assert SwarmStrategy.CONSENSUS is not None
        assert SwarmStrategy.CONSENSUS.value == "consensus"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="swarm_config")
class TestSwarmConfig:
    """Tests for SwarmConfig model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_swarm_config_exists(self) -> None:
        """Test that SwarmConfig class exists."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmConfig

        assert SwarmConfig is not None

    def test_swarm_config_has_strategy_field(self) -> None:
        """Test SwarmConfig has strategy field."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.RACE)

        assert config.strategy == SwarmStrategy.RACE

    def test_swarm_config_has_max_agents_field(self) -> None:
        """Test SwarmConfig has max_agents field."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.RACE, max_agents=5)

        assert config.max_agents == 5

    def test_swarm_config_max_agents_defaults_to_3(self) -> None:
        """Test max_agents defaults to 3."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.RACE)

        assert config.max_agents == 3

    def test_swarm_config_has_timeout_seconds_field(self) -> None:
        """Test SwarmConfig has timeout_seconds field."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.RACE, timeout_seconds=120.0)

        assert config.timeout_seconds == 120.0

    def test_swarm_config_has_min_consensus_ratio_field(self) -> None:
        """Test SwarmConfig has min_consensus_ratio for consensus strategy."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(
            strategy=SwarmStrategy.CONSENSUS,
            min_consensus_ratio=0.7,
        )

        assert config.min_consensus_ratio == 0.7

    def test_swarm_config_min_consensus_ratio_defaults_to_0_5(self) -> None:
        """Test min_consensus_ratio defaults to 0.5."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.CONSENSUS)

        assert config.min_consensus_ratio == 0.5


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="swarm_orchestrator_class")
class TestSwarmOrchestrator:
    """Tests for SwarmOrchestrator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_swarm_orchestrator_exists(self) -> None:
        """Test that SwarmOrchestrator class exists."""
        from mcp_server_langgraph.agents.swarm_orchestrator import SwarmOrchestrator

        assert SwarmOrchestrator is not None

    def test_swarm_orchestrator_requires_agents(self) -> None:
        """Test SwarmOrchestrator requires list of agents."""
        from mcp_server_langgraph.agents.base_agent import BaseAgent
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        mock_agent1 = MagicMock(spec=BaseAgent)
        mock_agent2 = MagicMock(spec=BaseAgent)

        config = SwarmConfig(strategy=SwarmStrategy.RACE)
        orchestrator = SwarmOrchestrator(
            agents=[mock_agent1, mock_agent2],
            config=config,
        )

        assert len(orchestrator.agents) == 2

    def test_swarm_orchestrator_requires_config(self) -> None:
        """Test SwarmOrchestrator requires SwarmConfig."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.CASCADE)
        orchestrator = SwarmOrchestrator(agents=[], config=config)

        assert orchestrator.config == config
        assert orchestrator.config.strategy == SwarmStrategy.CASCADE

    def test_swarm_orchestrator_has_run_method(self) -> None:
        """Test SwarmOrchestrator has run method."""
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        config = SwarmConfig(strategy=SwarmStrategy.RACE)
        orchestrator = SwarmOrchestrator(agents=[], config=config)

        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="swarm_race_strategy")
class TestSwarmRaceStrategy:
    """Tests for RACE strategy execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_race_returns_first_successful_result(self) -> None:
        """Test RACE strategy returns first successful result."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        # Create agents with different response times
        async def slow_response(req, cancel_event=None):
            await asyncio.sleep(2.0)  # noqa: S101 - intentional for timeout test
            return AgentResult(content="Slow", success=True)

        slow_agent = MagicMock()
        slow_agent.run = slow_response

        fast_agent = MagicMock()
        fast_agent.run = AsyncMock(return_value=AgentResult(content="Fast", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.RACE, timeout_seconds=5.0)
        orchestrator = SwarmOrchestrator(
            agents=[slow_agent, fast_agent],
            config=config,
        )

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        assert result.success is True
        assert result.content == "Fast"

    async def test_race_cancels_remaining_agents(self) -> None:
        """Test RACE strategy cancels remaining agents after first completes."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        agent1 = MagicMock()
        agent1.run = AsyncMock(return_value=AgentResult(content="First", success=True))

        agent2 = MagicMock()
        agent2.run = AsyncMock(return_value=AgentResult(content="Second", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.RACE)
        orchestrator = SwarmOrchestrator(agents=[agent1, agent2], config=config)

        request = AgentRequest(message="Test")
        await orchestrator.run(request)

        # First agent should complete, second might be cancelled
        assert agent1.run.called


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="swarm_cascade_strategy")
class TestSwarmCascadeStrategy:
    """Tests for CASCADE strategy execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_cascade_tries_agents_in_order(self) -> None:
        """Test CASCADE strategy tries agents in order until success."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        failing_agent = MagicMock()
        failing_agent.run = AsyncMock(return_value=AgentResult(content="", success=False, error="Failed"))

        succeeding_agent = MagicMock()
        succeeding_agent.run = AsyncMock(return_value=AgentResult(content="Success", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.CASCADE)
        orchestrator = SwarmOrchestrator(
            agents=[failing_agent, succeeding_agent],
            config=config,
        )

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        assert result.success is True
        assert result.content == "Success"
        assert failing_agent.run.called
        assert succeeding_agent.run.called

    async def test_cascade_stops_on_first_success(self) -> None:
        """Test CASCADE strategy stops after first successful agent."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        agent1 = MagicMock()
        agent1.run = AsyncMock(return_value=AgentResult(content="First", success=True))

        agent2 = MagicMock()
        agent2.run = AsyncMock(return_value=AgentResult(content="Second", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.CASCADE)
        orchestrator = SwarmOrchestrator(agents=[agent1, agent2], config=config)

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        assert result.content == "First"
        assert agent1.run.called
        assert not agent2.run.called  # Should not be called


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="swarm_consensus_strategy")
class TestSwarmConsensusStrategy:
    """Tests for CONSENSUS strategy execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_consensus_runs_all_agents(self) -> None:
        """Test CONSENSUS strategy runs all agents."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        agent1 = MagicMock()
        agent1.run = AsyncMock(return_value=AgentResult(content="A", success=True))

        agent2 = MagicMock()
        agent2.run = AsyncMock(return_value=AgentResult(content="A", success=True))

        agent3 = MagicMock()
        agent3.run = AsyncMock(return_value=AgentResult(content="B", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.CONSENSUS)
        orchestrator = SwarmOrchestrator(
            agents=[agent1, agent2, agent3],
            config=config,
        )

        request = AgentRequest(message="Test")
        await orchestrator.run(request)

        assert agent1.run.called
        assert agent2.run.called
        assert agent3.run.called

    async def test_consensus_returns_majority_answer(self) -> None:
        """Test CONSENSUS strategy returns the majority answer."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        agent1 = MagicMock()
        agent1.run = AsyncMock(return_value=AgentResult(content="Majority", success=True))

        agent2 = MagicMock()
        agent2.run = AsyncMock(return_value=AgentResult(content="Majority", success=True))

        agent3 = MagicMock()
        agent3.run = AsyncMock(return_value=AgentResult(content="Minority", success=True))

        config = SwarmConfig(strategy=SwarmStrategy.CONSENSUS, min_consensus_ratio=0.5)
        orchestrator = SwarmOrchestrator(
            agents=[agent1, agent2, agent3],
            config=config,
        )

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        # 2/3 agree on "Majority"
        assert result.success is True
        assert result.content == "Majority"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="swarm_error_handling")
class TestSwarmErrorHandling:
    """Tests for SwarmOrchestrator error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_handles_timeout(self) -> None:
        """Test SwarmOrchestrator handles timeout gracefully."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        async def slow_run(req, cancel_event=None):
            await asyncio.sleep(10.0)  # noqa: S101 - intentional for timeout test
            return AgentResult(content="Slow", success=True)

        slow_agent = MagicMock()
        slow_agent.run = slow_run

        config = SwarmConfig(strategy=SwarmStrategy.RACE, timeout_seconds=0.1)
        orchestrator = SwarmOrchestrator(agents=[slow_agent], config=config)

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        assert result.success is False
        assert "timeout" in result.error.lower()

    async def test_handles_all_agents_failing(self) -> None:
        """Test SwarmOrchestrator handles all agents failing."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )

        failing_agent = MagicMock()
        failing_agent.run = AsyncMock(return_value=AgentResult(content="", success=False, error="Failed"))

        config = SwarmConfig(strategy=SwarmStrategy.CASCADE)
        orchestrator = SwarmOrchestrator(agents=[failing_agent], config=config)

        request = AgentRequest(message="Test")
        result = await orchestrator.run(request)

        assert result.success is False
        assert result.error is not None
