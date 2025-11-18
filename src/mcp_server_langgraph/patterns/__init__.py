"""
Multi-Agent Patterns for MCP Server with LangGraph

Production-ready multi-agent coordination patterns:
- Supervisor: One agent delegates to specialized workers
- Swarm: Parallel execution with result aggregation
- Hierarchical: Multi-level delegation chains
- Sequential: Ordered agent pipeline

These patterns enable complex agent workflows and team-based AI systems.
"""

from .hierarchical import HierarchicalCoordinator
from .supervisor import Supervisor
from .swarm import Swarm


__all__ = ["Supervisor", "Swarm", "HierarchicalCoordinator"]
