"""
Supervisor Pattern for Multi-Agent Coordination

The supervisor pattern uses one coordinating agent that delegates tasks
to specialized worker agents based on the task requirements.

Architecture:
    User Query → Supervisor → Routes to Worker → Result → Supervisor → Response

Use Cases:
    - Customer support (routing to billing, technical, sales specialists)
    - Research (delegating to search, analysis, writing specialists)
    - Code review (routing to security, performance, style checkers)

Example:
    from mcp_server_langgraph.patterns import Supervisor

    supervisor = Supervisor(
        agents={
            "research": research_agent,
            "writer": writer_agent,
            "reviewer": reviewer_agent
        },
        routing_strategy="sequential"
    )

    result = supervisor.invoke({"task": "Write a research report"})
"""

from typing import Any, Callable, Dict, List, Literal, Optional

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


class SupervisorState(BaseModel):
    """State for supervisor pattern."""

    task: str = Field(description="The task to accomplish")
    current_agent: Optional[str] = Field(default=None, description="Currently active agent")
    agent_history: List[str] = Field(default_factory=list, description="Sequence of agents executed")
    agent_results: Dict[str, Any] = Field(default_factory=dict, description="Results from each agent")
    next_agent: Optional[str] = Field(default=None, description="Next agent to execute")
    final_result: str = Field(default="", description="Final aggregated result")
    routing_decision: str = Field(default="", description="Supervisor's routing decision")
    completed: bool = Field(default=False, description="Whether task is completed")


class Supervisor:
    """
    Supervisor pattern for multi-agent coordination.

    One coordinating agent delegates work to specialized workers.
    """

    def __init__(
        self,
        agents: Dict[str, Callable[[str], Any]],
        routing_strategy: Literal["sequential", "conditional", "parallel"] = "conditional",
        supervisor_prompt: Optional[str] = None,
    ):
        """
        Initialize supervisor.

        Args:
            agents: Dictionary of {agent_name: agent_function}
            routing_strategy: How to route between agents
                - sequential: Execute all agents in order
                - conditional: Supervisor decides next agent
                - parallel: Execute agents in parallel (future)
            supervisor_prompt: Custom prompt for supervisor's routing logic
        """
        self.agents = agents
        self.routing_strategy = routing_strategy
        self.supervisor_prompt = supervisor_prompt or self._default_supervisor_prompt()
        self._graph: Optional[StateGraph[SupervisorState]] = None

    def _default_supervisor_prompt(self) -> str:
        """Default supervisor prompt."""
        agent_list = ", ".join(self.agents.keys())
        return f"""You are a supervisor coordinating a team of AI agents: {agent_list}.

Your job is to:
1. Analyze the user's task
2. Decide which agent(s) should handle it
3. Route the task to the appropriate agent
4. Aggregate results from multiple agents if needed
5. Provide a final response to the user

Available agents: {agent_list}

Choose the best agent for each sub-task."""

    def _create_supervisor_node(self, state: SupervisorState) -> SupervisorState:
        """
        Supervisor decision node.

        Analyzes task and decides which agent to route to.
        In production, this would use an LLM for intelligent routing.
        """
        # Simplified routing logic (in production, use LLM)
        task_lower = state.task.lower()

        # Simple keyword-based routing
        if "research" in task_lower or "search" in task_lower or "find" in task_lower:
            state.next_agent = "research" if "research" in self.agents else list(self.agents.keys())[0]
        elif "write" in task_lower or "create" in task_lower or "draft" in task_lower:
            state.next_agent = "writer" if "writer" in self.agents else list(self.agents.keys())[0]
        elif "review" in task_lower or "check" in task_lower or "analyze" in task_lower:
            state.next_agent = "reviewer" if "reviewer" in self.agents else list(self.agents.keys())[0]
        else:
            # Default to first available agent
            state.next_agent = list(self.agents.keys())[0]

        state.routing_decision = f"Routing to {state.next_agent} based on task analysis"

        return state

    def _create_worker_wrapper(
        self, agent_name: str, agent_func: Callable[[str], Any]
    ) -> Callable[[SupervisorState], SupervisorState]:
        """
        Create a wrapper for worker agent.

        Args:
            agent_name: Name of the agent
            agent_func: Agent function to wrap

        Returns:
            Wrapped function that updates SupervisorState
        """

        def worker_node(state: SupervisorState) -> SupervisorState:
            """Execute worker agent."""
            # Call the actual agent function
            result = agent_func(state.task)

            # Store result
            state.agent_results[agent_name] = result
            state.agent_history.append(agent_name)
            state.current_agent = agent_name

            # In sequential mode, move to next agent
            if self.routing_strategy == "sequential":
                agent_keys = list(self.agents.keys())
                current_idx = agent_keys.index(agent_name)
                if current_idx < len(agent_keys) - 1:
                    state.next_agent = agent_keys[current_idx + 1]
                else:
                    state.next_agent = "aggregate"
            else:
                # In conditional mode, return to supervisor
                state.next_agent = "aggregate"

            return state

        return worker_node

    def _create_aggregator_node(self, state: SupervisorState) -> SupervisorState:
        """
        Aggregate results from all workers.

        In production, use LLM to synthesize results.
        """
        # Simple aggregation: combine all results
        results_summary = []
        for agent_name in state.agent_history:
            result = state.agent_results.get(agent_name, "")
            results_summary.append(f"**{agent_name.title()}:** {result}")

        state.final_result = "\n\n".join(results_summary)
        state.completed = True

        return state

    def _routing_function(self, state: SupervisorState) -> str:
        """Determine next node based on state."""
        if state.next_agent == "aggregate":
            return "aggregate"
        elif state.next_agent:
            return state.next_agent
        else:
            return "supervisor"

    def build(self) -> "StateGraph[SupervisorState]":
        """Build the supervisor graph."""
        graph: StateGraph[SupervisorState] = StateGraph(SupervisorState)

        # Add supervisor node
        graph.add_node("supervisor", self._create_supervisor_node)

        # Add worker nodes
        for agent_name, agent_func in self.agents.items():
            worker_node = self._create_worker_wrapper(agent_name, agent_func)
            graph.add_node(agent_name, worker_node)  # type: ignore[arg-type]

        # Add aggregator node
        graph.add_node("aggregate", self._create_aggregator_node)

        # Define edges
        graph.set_entry_point("supervisor")

        # Supervisor routes to workers
        graph.add_conditional_edges("supervisor", self._routing_function)

        # Workers route based on strategy
        for agent_name in self.agents.keys():
            graph.add_conditional_edges(agent_name, self._routing_function)

        # Aggregator is the end
        graph.set_finish_point("aggregate")

        return graph

    def compile(self, checkpointer: Any = None) -> Any:
        """
        Compile the supervisor graph.

        Args:
            checkpointer: Optional checkpointer for state persistence

        Returns:
            Compiled LangGraph application
        """
        if self._graph is None:
            self._graph = self.build()

        return self._graph.compile(checkpointer=checkpointer)

    def invoke(self, task: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the supervisor pattern.

        Args:
            task: Task description
            config: Optional configuration

        Returns:
            Results including final_result and agent_history
        """
        compiled = self.compile()
        state = SupervisorState(task=task)

        result = compiled.invoke(state, config=config or {})

        return {
            "task": result["task"],
            "final_result": result["final_result"],
            "agent_history": result["agent_history"],
            "agent_results": result["agent_results"],
            "routing_decision": result["routing_decision"],
        }


# Example usage and testing
if __name__ == "__main__":
    # Define simple worker agents
    def research_agent(task: str) -> str:
        """Research agent."""
        return f"Research findings for: {task}\n- Found relevant papers\n- Analyzed data sources"

    def writer_agent(task: str) -> str:
        """Writer agent."""
        return f"Written content for: {task}\n- Created outline\n- Drafted sections"

    def reviewer_agent(task: str) -> str:
        """Reviewer agent."""
        return f"Review feedback for: {task}\n- Checked accuracy\n- Suggested improvements"

    # Create supervisor
    supervisor = Supervisor(
        agents={"research": research_agent, "writer": writer_agent, "reviewer": reviewer_agent},
        routing_strategy="sequential",
    )

    # Test cases
    test_tasks = [
        "Research the latest AI trends",
        "Write a blog post about LangGraph",
        "Review this code for security issues",
    ]

    print("=" * 80)
    print("SUPERVISOR PATTERN - TEST RUN")
    print("=" * 80)

    for task in test_tasks:
        print(f"\n{'=' * 80}")
        print(f"TASK: {task}")
        print(f"{'=' * 80}")

        result = supervisor.invoke(task)

        print(f"\nRouting Decision: {result['routing_decision']}")
        print(f"Agent History: {' → '.join(result['agent_history'])}")
        print(f"\nFINAL RESULT:\n{result['final_result']}")

    print(f"\n{'=' * 80}\n")
