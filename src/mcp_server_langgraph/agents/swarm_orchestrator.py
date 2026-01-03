"""
Swarm Orchestrator for Multi-Agent Coordination

Provides three coordination strategies for running multiple agents:
- RACE: All agents run in parallel, first successful result wins
- CASCADE: Agents run sequentially, stop on first success
- CONSENSUS: All agents run in parallel, majority answer wins

Usage:
    from mcp_server_langgraph.agents.swarm_orchestrator import (
        SwarmOrchestrator,
        SwarmConfig,
        SwarmStrategy,
    )

    agents = [WorkerAgent(llm_factory) for _ in range(3)]
    config = SwarmConfig(strategy=SwarmStrategy.CONSENSUS)
    orchestrator = SwarmOrchestrator(agents=agents, config=config)

    result = await orchestrator.run(AgentRequest(message="Question"))
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult, BaseAgent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SwarmStrategy(Enum):
    """Swarm coordination strategy.

    - RACE: First successful result wins, others cancelled
    - CASCADE: Sequential fallback, stop on first success
    - CONSENSUS: All run, majority answer wins
    """

    RACE = "race"
    CASCADE = "cascade"
    CONSENSUS = "consensus"


@dataclass
class SwarmConfig:
    """Configuration for swarm orchestration.

    Attributes:
        strategy: Coordination strategy (RACE, CASCADE, CONSENSUS)
        max_agents: Maximum agents to use (default: 3)
        timeout_seconds: Overall timeout in seconds (default: 60.0)
        min_consensus_ratio: Minimum ratio for consensus (default: 0.5)
    """

    strategy: SwarmStrategy
    max_agents: int = 3
    timeout_seconds: float = 60.0
    min_consensus_ratio: float = 0.5


class SwarmOrchestrator:
    """Orchestrator for coordinating multiple agents.

    Runs agents according to the configured strategy and aggregates results.

    Attributes:
        agents: List of BaseAgent instances
        config: SwarmConfig with strategy and parameters
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        config: SwarmConfig,
    ) -> None:
        """Initialize SwarmOrchestrator.

        Args:
            agents: List of BaseAgent instances to coordinate
            config: SwarmConfig with strategy and parameters
        """
        self.agents = agents[: config.max_agents]  # Limit to max_agents
        self.config = config

    async def run(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """Execute swarm with configured strategy.

        Args:
            request: AgentRequest to process
            cancel_event: Optional cancellation event

        Returns:
            AgentResult from the selected strategy
        """
        if not self.agents:
            return AgentResult(
                content="",
                success=False,
                error="No agents configured",
            )

        try:
            if self.config.strategy == SwarmStrategy.RACE:
                return await self._run_race(request, cancel_event)
            elif self.config.strategy == SwarmStrategy.CASCADE:
                return await self._run_cascade(request, cancel_event)
            elif self.config.strategy == SwarmStrategy.CONSENSUS:
                return await self._run_consensus(request, cancel_event)
            # Note: All SwarmStrategy enum values are handled above
            # This is unreachable, but provides type safety
            return AgentResult(  # type: ignore[unreachable]
                content="",
                success=False,
                error=f"Unknown strategy: {self.config.strategy}",
            )
        except TimeoutError:
            return AgentResult(
                content="",
                success=False,
                error=f"Swarm timeout after {self.config.timeout_seconds}s",
            )

    async def _run_race(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """RACE strategy: First successful result wins.

        All agents run in parallel. First to return success wins.
        Remaining agents are cancelled.
        """
        # Create cancel events for each agent
        agent_cancel_events = [asyncio.Event() for _ in self.agents]

        async def run_with_index(
            index: int, agent: BaseAgent, agent_cancel: asyncio.Event
        ) -> tuple[int, AgentResult]:
            """Run agent and return index with result."""
            result = await agent.run(request, cancel_event=agent_cancel)
            return (index, result)

        # Create tasks for all agents
        tasks = [
            asyncio.create_task(run_with_index(i, agent, agent_cancel_events[i]))
            for i, agent in enumerate(self.agents)
        ]

        try:
            # Wait for first successful result with timeout
            async def wait_for_first_success() -> AgentResult:
                done, pending = set(), set(tasks)
                while pending:
                    done_batch, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in done_batch:
                        _, result = task.result()
                        if result.success:
                            # Cancel remaining tasks
                            for p in pending:
                                p.cancel()
                            for event in agent_cancel_events:
                                event.set()
                            return result
                        done.add(task)

                # No successful result found
                return AgentResult(
                    content="",
                    success=False,
                    error="All agents failed in race",
                )

            return await asyncio.wait_for(
                wait_for_first_success(),
                timeout=self.config.timeout_seconds,
            )

        except TimeoutError:
            # Cancel all pending tasks
            for task in tasks:
                task.cancel()
            for event in agent_cancel_events:
                event.set()
            raise

    async def _run_cascade(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """CASCADE strategy: Sequential fallback.

        Agents run one at a time. Stop on first success.
        """
        last_result = AgentResult(
            content="",
            success=False,
            error="No agents to run",
        )

        for agent in self.agents:
            try:
                result = await asyncio.wait_for(
                    agent.run(request, cancel_event=cancel_event),
                    timeout=self.config.timeout_seconds,
                )
                if result.success:
                    return result
                last_result = result
            except TimeoutError:
                last_result = AgentResult(
                    content="",
                    success=False,
                    error="Agent timeout",
                )
                continue

        return last_result

    async def _run_consensus(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """CONSENSUS strategy: Majority answer wins.

        All agents run in parallel. Most common answer wins.
        """
        # Run all agents in parallel
        tasks = [
            asyncio.create_task(agent.run(request, cancel_event=cancel_event))
            for agent in self.agents
        ]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_seconds,
            )
        except TimeoutError:
            for task in tasks:
                task.cancel()
            raise

        # Collect successful results
        successful_results: list[AgentResult] = []
        for result in results:
            if isinstance(result, AgentResult) and result.success:
                successful_results.append(result)

        if not successful_results:
            return AgentResult(
                content="",
                success=False,
                error="All agents failed in consensus",
            )

        # Find majority answer
        answer_counts = Counter(r.content for r in successful_results)
        most_common_content, count = answer_counts.most_common(1)[0]

        # Check if consensus threshold met
        ratio = count / len(self.agents)
        if ratio >= self.config.min_consensus_ratio:
            # Find the first result with this content
            for result in successful_results:
                if result.content == most_common_content:
                    return result

        # Return most common even if threshold not met
        for result in successful_results:
            if result.content == most_common_content:
                return result

        # Fallback to first successful
        return successful_results[0]
