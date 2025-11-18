"""
Swarm Pattern for Parallel Multi-Agent Execution

The swarm pattern executes multiple agents in parallel on the same task
and aggregates their results for a comprehensive answer.

Architecture:
    User Query → [Agent 1, Agent 2, Agent 3, ...] (parallel) → Aggregator → Response

Use Cases:
    - Consensus building (multiple agents analyze same problem)
    - Diverse perspectives (different approaches to same task)
    - Redundancy and validation (cross-checking results)
    - Parallel research (multiple sources simultaneously)

Example:
    from mcp_server_langgraph.patterns import Swarm

    swarm = Swarm(
        agents={
            "gemini": gemini_agent,
            "claude": claude_agent,
            "gpt4": gpt4_agent
        },
        aggregation_strategy="consensus"
    )

    result = swarm.invoke({"query": "What is the capital of France?"})
"""

from collections.abc import Callable
from typing import Annotated, Any, Literal

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


def merge_agent_results(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Merge agent results dictionaries for concurrent updates."""
    result = left.copy()
    result.update(right)
    return result


class SwarmState(BaseModel):
    """State for swarm pattern."""

    query: str = Field(description="The query/task for all agents")
    agent_results: Annotated[dict[str, Any], merge_agent_results] = Field(
        default_factory=dict, description="Results from each agent"
    )
    aggregated_result: str = Field(default="", description="Aggregated final result")
    consensus_score: float = Field(default=0.0, description="Agreement level between agents (0-1)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Swarm:
    """
    Swarm pattern for parallel multi-agent execution.

    All agents work on the same task simultaneously, results are aggregated.
    """

    def __init__(
        self,
        agents: dict[str, Callable[[str], Any]],
        aggregation_strategy: Literal["consensus", "voting", "synthesis", "concatenate"] = "synthesis",
        min_agreement: float = 0.7,
    ):
        """
        Initialize swarm.

        Args:
            agents: Dictionary of {agent_name: agent_function}
            aggregation_strategy: How to combine results
                - consensus: Find common ground between all agents
                - voting: Majority vote on discrete choices
                - synthesis: LLM synthesizes all perspectives
                - concatenate: Simple combination of all outputs
            min_agreement: Minimum agreement threshold for consensus (0-1)
        """
        self.agents = agents
        self.aggregation_strategy = aggregation_strategy
        self.min_agreement = min_agreement
        self._graph: StateGraph[SwarmState] | None = None

    def _create_agent_wrapper(
        self, agent_name: str, agent_func: Callable[[str], Any]
    ) -> Callable[[SwarmState], dict[str, Any]]:
        """
        Create wrapper for agent execution.

        Args:
            agent_name: Name of the agent
            agent_func: Agent function

        Returns:
            Wrapped function that stores result in state
        """

        def agent_node(state: SwarmState) -> dict[str, Any]:
            """Execute agent and store result."""
            try:
                result = agent_func(state.query)
                # Return only the updated field to avoid concurrent update conflicts
                updated_results = state.agent_results.copy()
                updated_results[agent_name] = result
                return {"agent_results": updated_results}
            except Exception as e:
                updated_results = state.agent_results.copy()
                updated_results[agent_name] = f"Error: {str(e)}"
                return {"agent_results": updated_results}

        return agent_node

    def _calculate_consensus(self, results: list[str]) -> float:
        """
        Calculate consensus score between results.

        Simple implementation based on common words.
        In production, use semantic similarity with embeddings.

        Args:
            results: List of agent results

        Returns:
            Consensus score (0-1)
        """
        if len(results) < 2:
            return 1.0

        # Extract words from all results
        all_words = []
        for result in results:
            words = set(result.lower().split())
            all_words.append(words)

        # Calculate pairwise similarity
        similarities = []
        for i in range(len(all_words)):
            for j in range(i + 1, len(all_words)):
                intersection = all_words[i] & all_words[j]
                union = all_words[i] | all_words[j]
                similarity = len(intersection) / len(union) if union else 0
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _aggregate_results(self, state: SwarmState) -> dict[str, Any]:
        """
        Aggregate results from all agents.

        Args:
            state: Current state with agent results

        Returns:
            Dict with updated aggregated_result and consensus_score fields
        """
        results = list(state.agent_results.values())
        aggregated_result = ""
        consensus_score = 0.0

        if self.aggregation_strategy == "concatenate":
            # Simple concatenation
            formatted_results = []
            for agent_name, result in state.agent_results.items():
                formatted_results.append(f"**{agent_name.title()}:**\n{result}")
            aggregated_result = "\n\n".join(formatted_results)

        elif self.aggregation_strategy == "consensus":
            # Find consensus
            consensus_score = self._calculate_consensus(results)

            if consensus_score >= self.min_agreement:
                # High agreement - present consensus
                aggregated_result = f"**Consensus (agreement: {consensus_score:.0%}):**\n\n"
                aggregated_result += f"All agents agree:\n{results[0]}"
            else:
                # Low agreement - present all viewpoints
                aggregated_result = f"**Multiple Perspectives (agreement: {consensus_score:.0%}):**\n\n"
                for agent_name, result in state.agent_results.items():
                    aggregated_result += f"**{agent_name.title()}:** {result}\n\n"

        elif self.aggregation_strategy == "synthesis":
            # Synthesize all results (simplified - in production use LLM)
            aggregated_result = "**Synthesized Response:**\n\n"
            aggregated_result += "Based on analysis from multiple agents:\n\n"

            for agent_name, result in state.agent_results.items():
                # Extract key points (simplified)
                aggregated_result += f"• From {agent_name}: {result[:100]}...\n"

            consensus_score = self._calculate_consensus(results)

        elif self.aggregation_strategy == "voting":
            # Simple voting (count identical responses)
            from collections import Counter

            vote_counter = Counter(results)
            winner, count = vote_counter.most_common(1)[0]

            aggregated_result = f"**Voting Result ({count}/{len(results)} agents agree):**\n\n{winner}"
            consensus_score = count / len(results)

        return {"aggregated_result": aggregated_result, "consensus_score": consensus_score}

    def build(self) -> "StateGraph[SwarmState]":
        """Build the swarm graph."""
        from langgraph.graph import END, START

        graph: StateGraph[SwarmState] = StateGraph(SwarmState)

        # Add all agent nodes
        for agent_name, agent_func in self.agents.items():
            agent_wrapper = self._create_agent_wrapper(agent_name, agent_func)
            graph.add_node(agent_name, agent_wrapper)

        # Add aggregator
        graph.add_node("aggregate", self._aggregate_results)

        # All agents run in parallel from start
        for agent_name in self.agents:
            graph.add_edge(START, agent_name)

        # All agents feed into aggregator
        for agent_name in self.agents:
            graph.add_edge(agent_name, "aggregate")

        # Aggregator is the end
        graph.add_edge("aggregate", END)

        return graph

    def compile(self, checkpointer: Any = None) -> Any:
        """
        Compile the swarm graph.

        Args:
            checkpointer: Optional checkpointer

        Returns:
            Compiled graph
        """
        if self._graph is None:
            self._graph = self.build()

        return self._graph.compile(checkpointer=checkpointer)

    def invoke(self, query: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute the swarm pattern.

        Args:
            query: Query for all agents
            config: Optional configuration

        Returns:
            Aggregated results
        """
        compiled = self.compile()
        state = SwarmState(query=query)

        result = compiled.invoke(state, config=config or {})

        return {
            "query": result["query"],
            "aggregated_result": result["aggregated_result"],
            "agent_results": result["agent_results"],
            "consensus_score": result["consensus_score"],
            "num_agents": len(result["agent_results"]),
        }


# Example usage and testing
if __name__ == "__main__":
    # Define diverse agents with different perspectives
    def optimistic_agent(query: str) -> str:
        """Optimistic perspective."""
        return f"Analysis of '{query}': This is a great opportunity with many positive aspects and potential benefits."

    def pessimistic_agent(query: str) -> str:
        """Pessimistic perspective."""
        return f"Analysis of '{query}': There are significant risks and challenges that need careful consideration."

    def neutral_agent(query: str) -> str:
        """Balanced perspective."""
        return f"Analysis of '{query}': There are both advantages and disadvantages that should be weighed carefully."

    # Test different aggregation strategies
    strategies = ["concatenate", "consensus", "synthesis", "voting"]

    for strategy in strategies:
        print("=" * 80)
        print(f"SWARM PATTERN - {strategy.upper()} STRATEGY")
        print("=" * 80)

        swarm = Swarm(
            agents={"optimist": optimistic_agent, "pessimist": pessimistic_agent, "neutral": neutral_agent},
            aggregation_strategy=strategy,  # type: ignore
        )

        result = swarm.invoke("Adopting AI in our business")

        print(f"\nQuery: {result['query']}")
        print(f"Number of Agents: {result['num_agents']}")
        print(f"Consensus Score: {result['consensus_score']:.0%}")
        print(f"\nAGGREGATED RESULT:\n{result['aggregated_result']}")
        print()

    print("=" * 80)
