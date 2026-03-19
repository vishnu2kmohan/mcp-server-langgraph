"""
Repository Implementations

Provides concrete implementations of storage repositories for:
- Projects (Unified Workspace Paradigm)
- MCP Connections (OAuth2 and API Key authentication)
- Database Connections (SQL execution - ADR-0107)
- Execution Plans (approval workflows)
- Decision Traces (Context Graphs - ADR-0101)
"""

from mcp_server_langgraph.repositories.connections import (
    ConnectionRepository,
    PostgresConnectionRepository,
)
from mcp_server_langgraph.repositories.database_connections import (
    DatabaseConnectionRepository,
    PostgresDatabaseConnectionRepository,
)
from mcp_server_langgraph.repositories.decision_trace import (
    DecisionTraceRepositoryBase,
    PostgresDecisionTraceRepository,
)
from mcp_server_langgraph.repositories.execution_plan import (
    ExecutionPlanRepository,
    InMemoryExecutionPlanRepository,
)
from mcp_server_langgraph.repositories.agent_state import (
    AgentStateRepository,
    InMemoryAgentStateRepository,
)
from mcp_server_langgraph.repositories.checkpoint import (
    CheckpointRepository,
    InMemoryCheckpointRepository,
)
from mcp_server_langgraph.repositories.evidence import (
    EvidenceRepository,
    InMemoryEvidenceRepository,
)
from mcp_server_langgraph.repositories.notes import (
    InMemoryNotesRepository,
    NotesRepository,
)
from mcp_server_langgraph.repositories.projects import PostgresProjectRepository

__all__ = [
    "AgentStateRepository",
    "CheckpointRepository",
    "ConnectionRepository",
    "DatabaseConnectionRepository",
    "DecisionTraceRepositoryBase",
    "EvidenceRepository",
    "ExecutionPlanRepository",
    "InMemoryAgentStateRepository",
    "InMemoryCheckpointRepository",
    "InMemoryEvidenceRepository",
    "InMemoryExecutionPlanRepository",
    "InMemoryNotesRepository",
    "NotesRepository",
    "PostgresConnectionRepository",
    "PostgresDatabaseConnectionRepository",
    "PostgresDecisionTraceRepository",
    "PostgresProjectRepository",
]
