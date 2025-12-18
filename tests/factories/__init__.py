"""
Test Factories Package.

Provides factory classes for creating test data objects.

Available factories:
- UserFactory: Create test user objects
- SessionFactory: Create test session objects
- MessageFactory: Create test message objects
- AgentStateFactory: Create test agent state objects
- WorkflowFactory: Create test workflow objects
- NodeFactory: Create test workflow node objects
- EdgeFactory: Create test workflow edge objects
- ConnectionFactory: Create test MCP connection objects
- ProjectFactory: Create test project objects
- ProjectMemberFactory: Create test project member objects

Usage:
    from tests.factories import UserFactory, MessageFactory, WorkflowFactory
    from tests.factories import ConnectionFactory, ProjectFactory

    user = UserFactory.create(username="alice")
    messages = MessageFactory.conversation(turns=3)
    workflow = WorkflowFactory.create_with_nodes(node_count=5)
    connection = ConnectionFactory.create_with_oauth2()
    project = ProjectFactory.create_full()
"""

from tests.factories.user_factory import UserFactory, alice, bob
from tests.factories.session_factory import (
    SessionFactory,
    MessageFactory,
    AgentStateFactory,
)
from tests.factories.workflow_factory import (
    WorkflowFactory,
    NodeFactory,
    EdgeFactory,
    simple_workflow,
    agent_with_tools_workflow,
)
from tests.factories.connection_factory import (
    ConnectionFactory,
    mcp_streamable_connection,
    mcp_stdio_connection,
    mcp_oauth2_connection,
    mcp_disconnected_connection,
)
from tests.factories.project_factory import (
    ProjectFactory,
    ProjectWorkflowRefFactory,
    ProjectSessionRefFactory,
    ProjectConnectionFactory,
    ProjectMemberFactory,
    empty_project,
    team_project,
    full_project,
)

__all__ = [
    # User factories
    "UserFactory",
    "alice",
    "bob",
    # Session factories
    "SessionFactory",
    "MessageFactory",
    "AgentStateFactory",
    # Workflow factories
    "WorkflowFactory",
    "NodeFactory",
    "EdgeFactory",
    "simple_workflow",
    "agent_with_tools_workflow",
    # Connection factories
    "ConnectionFactory",
    "mcp_streamable_connection",
    "mcp_stdio_connection",
    "mcp_oauth2_connection",
    "mcp_disconnected_connection",
    # Project factories
    "ProjectFactory",
    "ProjectWorkflowRefFactory",
    "ProjectSessionRefFactory",
    "ProjectConnectionFactory",
    "ProjectMemberFactory",
    "empty_project",
    "team_project",
    "full_project",
]
