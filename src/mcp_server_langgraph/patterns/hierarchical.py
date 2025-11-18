"""
Hierarchical Pattern for Multi-Level Agent Delegation

The hierarchical pattern organizes agents in a tree structure where
top-level agents can delegate to sub-agents, creating a chain of command.

Architecture:
    User Query → CEO Agent → [Manager A, Manager B]
                          ↓              ↓
                  [Worker 1, 2, 3] [Worker 4, 5, 6]

Use Cases:
    - Complex project management (CEO → Managers → Workers)
    - Enterprise workflows (Executive → Department → Team → Individual)
    - Cascading decision-making
    - Organizational hierarchies

Example:
    from mcp_server_langgraph.patterns import HierarchicalCoordinator

    hierarchy = HierarchicalCoordinator(
        ceo_agent=executive_agent,
        managers={
            "research_manager": research_mgr,
            "dev_manager": dev_mgr
        },
        workers={
            "research_manager": [researcher1, researcher2],
            "dev_manager": [developer1, developer2, developer3]
        }
    )

    result = hierarchy.invoke({"project": "Build AI feature"})
"""

from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


class HierarchicalState(BaseModel):
    """State for hierarchical pattern."""

    project: str = Field(description="The project or task")
    ceo_decision: str = Field(default="", description="Top-level strategic decision")
    manager_assignments: dict[str, str] = Field(default_factory=dict, description="Tasks assigned to each manager")
    worker_results: dict[str, list[Any]] = Field(default_factory=dict, description="Results from workers by manager")
    manager_reports: dict[str, str] = Field(default_factory=dict, description="Manager summary reports")
    final_report: str = Field(default="", description="Final consolidated report")
    execution_path: list[str] = Field(default_factory=list, description="Execution path through hierarchy")


class HierarchicalCoordinator:
    """
    Hierarchical pattern for multi-level agent delegation.

    Organizes agents in a tree: CEO → Managers → Workers
    """

    def __init__(
        self,
        ceo_agent: Callable[[str], str],
        managers: dict[str, Callable[[str], str]],
        workers: dict[str, list[Callable[[str], Any]]],
        delegation_strategy: str = "balanced",
    ):
        """
        Initialize hierarchical coordinator.

        Args:
            ceo_agent: Top-level decision-making agent
            managers: Dict of {manager_name: manager_function}
            workers: Dict of {manager_name: [worker_functions]}
            delegation_strategy: How to distribute work
                - balanced: Distribute evenly
                - specialized: Route based on expertise
        """
        self.ceo_agent = ceo_agent
        self.managers = managers
        self.workers = workers
        self.delegation_strategy = delegation_strategy
        self._graph: StateGraph[HierarchicalState] | None = None

    def _ceo_node(self, state: HierarchicalState) -> HierarchicalState:
        """
        CEO makes top-level decisions and delegates to managers.

        In production, CEO agent would use LLM to analyze project
        and decide delegation strategy.
        """
        # CEO analyzes the project
        ceo_analysis = self.ceo_agent(state.project)
        state.ceo_decision = ceo_analysis
        state.execution_path.append("CEO")

        # Delegate to managers (simplified delegation logic)
        if self.delegation_strategy == "balanced":
            # Distribute work evenly
            managers_list = list(self.managers.keys())
            for manager_name in managers_list:
                state.manager_assignments[manager_name] = f"Handle aspect of '{state.project}' - assigned by CEO"
        else:
            # Specialized delegation (in production, use LLM)
            for manager_name in self.managers:
                state.manager_assignments[manager_name] = f"Specialized task for {manager_name} regarding '{state.project}'"

        return state

    def _create_manager_node(
        self, manager_name: str, manager_func: Callable[[str], str]
    ) -> Callable[[HierarchicalState], HierarchicalState]:
        """
        Create manager node that delegates to workers.

        Args:
            manager_name: Name of the manager
            manager_func: Manager function

        Returns:
            Manager node function
        """

        def manager_node(state: HierarchicalState) -> HierarchicalState:
            """Manager delegates to workers and summarizes results."""
            state.execution_path.append(f"Manager:{manager_name}")

            # Get assignment from CEO
            assignment = state.manager_assignments.get(manager_name, "")

            # Manager analyzes and delegates to workers
            manager_analysis = manager_func(assignment)

            # Collect worker results
            worker_funcs = self.workers.get(manager_name, [])
            worker_results = []

            for i, worker_func in enumerate(worker_funcs):
                state.execution_path.append(f"Worker:{manager_name}_{i}")
                worker_result = worker_func(assignment)
                worker_results.append(worker_result)

            # Store worker results
            state.worker_results[manager_name] = worker_results

            # Manager creates summary report
            report = f"**{manager_name.replace('_', ' ').title()} Report:**\n\n"
            report += f"Assignment: {assignment}\n\n"
            report += f"Manager Analysis: {manager_analysis}\n\n"
            report += f"Team Results ({len(worker_results)} workers):\n"

            for i, result in enumerate(worker_results, 1):
                report += f"{i}. {result}\n"

            state.manager_reports[manager_name] = report

            return state

        return manager_node

    def _consolidate_node(self, state: HierarchicalState) -> HierarchicalState:
        """
        Consolidate all manager reports into final report.

        In production, CEO agent would synthesize all reports.
        """
        state.execution_path.append("Consolidation")

        # Build final report
        report_parts = []

        report_parts.append(f"# Project: {state.project}\n")
        report_parts.append(f"## CEO Strategic Decision\n{state.ceo_decision}\n")
        report_parts.append("## Execution Summary\n")

        # Add all manager reports
        for _manager_name, report in state.manager_reports.items():
            report_parts.append(f"\n### {report}\n")

        # Add execution path
        report_parts.append("\n## Execution Path\n")
        report_parts.append(" → ".join(state.execution_path))

        # Statistics
        total_workers = sum(len(results) for results in state.worker_results.values())
        report_parts.append("\n## Statistics\n")
        report_parts.append(f"- Managers: {len(self.managers)}\n")
        report_parts.append(f"- Workers: {total_workers}\n")
        report_parts.append("- Hierarchy Depth: 3 levels\n")

        state.final_report = "\n".join(report_parts)

        return state

    def build(self) -> "StateGraph[HierarchicalState]":
        """Build the hierarchical graph."""
        graph: StateGraph[HierarchicalState] = StateGraph(HierarchicalState)

        # Add CEO node
        graph.add_node("ceo", self._ceo_node)

        # Add manager nodes
        for manager_name, manager_func in self.managers.items():
            manager_node = self._create_manager_node(manager_name, manager_func)
            graph.add_node(f"manager_{manager_name}", manager_node)

        # Add consolidation node
        graph.add_node("consolidate", self._consolidate_node)

        # Define edges
        graph.set_entry_point("ceo")

        # CEO delegates to all managers
        for manager_name in self.managers:
            graph.add_edge("ceo", f"manager_{manager_name}")

        # All managers report to consolidation
        for manager_name in self.managers:
            graph.add_edge(f"manager_{manager_name}", "consolidate")

        # Consolidation is the end
        graph.set_finish_point("consolidate")

        return graph

    def compile(self, checkpointer: Any = None) -> Any:
        """
        Compile the hierarchical graph.

        Args:
            checkpointer: Optional checkpointer

        Returns:
            Compiled graph
        """
        if self._graph is None:
            self._graph = self.build()

        return self._graph.compile(checkpointer=checkpointer)

    def invoke(self, project: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute the hierarchical pattern.

        Args:
            project: Project description
            config: Optional configuration

        Returns:
            Final report and execution details
        """
        compiled = self.compile()
        state = HierarchicalState(project=project)

        result = compiled.invoke(state, config=config or {})

        return {
            "project": result.project,
            "final_report": result.final_report,
            "ceo_decision": result.ceo_decision,
            "manager_reports": result.manager_reports,
            "execution_path": result.execution_path,
            "total_agents": len(result.execution_path),
        }


# Example usage and testing
if __name__ == "__main__":
    # Define organizational hierarchy
    def ceo_agent(project: str) -> str:
        """CEO strategic planning."""
        return f"Strategic analysis: {project} requires research and development coordination."

    def research_manager(task: str) -> str:
        """Research manager planning."""
        return "Research plan: Investigate technical requirements and feasibility."

    def dev_manager(task: str) -> str:
        """Development manager planning."""
        return "Development plan: Design architecture and implementation roadmap."

    def researcher_1(task: str) -> str:
        """Research worker."""
        return "Conducted market analysis and competitor research"

    def researcher_2(task: str) -> str:
        """Research worker."""
        return "Reviewed academic papers and technical documentation"

    def developer_1(task: str) -> str:
        """Development worker."""
        return "Designed system architecture and database schema"

    def developer_2(task: str) -> str:
        """Development worker."""
        return "Implemented core features and API endpoints"

    def developer_3(task: str) -> str:
        """Development worker."""
        return "Created tests and deployment configurations"

    # Create hierarchical coordinator
    hierarchy = HierarchicalCoordinator(
        ceo_agent=ceo_agent,
        managers={"research_manager": research_manager, "dev_manager": dev_manager},
        workers={"research_manager": [researcher_1, researcher_2], "dev_manager": [developer_1, developer_2, developer_3]},
    )

    # Test
    print("=" * 80)
    print("HIERARCHICAL PATTERN - TEST RUN")
    print("=" * 80)

    result = hierarchy.invoke("Build AI-powered search feature")

    print(f"\nProject: {result['project']}")
    print(f"Total Agents Involved: {result['total_agents']}")
    print(f"Execution Path: {' → '.join(result['execution_path'][:5])}...")
    print(f"\nFINAL REPORT:\n{result['final_report']}")

    print("\n" + "=" * 80)
