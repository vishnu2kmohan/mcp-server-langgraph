"""
Project Factory for Test Data Generation.

Provides factory functions for creating test project objects.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class ProjectFactory:
    """Factory for creating test project objects."""

    @staticmethod
    def create(
        project_id: str | None = None,
        name: str = "Test Project",
        description: str = "A test project",
        owner_id: str = "alice",
        organization_id: str | None = None,
        status: str = "active",
        workflows: list[dict[str, Any]] | None = None,
        sessions: list[dict[str, Any]] | None = None,
        connections: list[dict[str, Any]] | None = None,
        members: list[dict[str, Any]] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a test project dictionary.

        Args:
            project_id: Project ID (auto-generated if not provided)
            name: Project name
            description: Project description
            owner_id: Owner user ID
            organization_id: Organization ID
            status: Project status (active, archived, deleted)
            workflows: List of workflow references
            sessions: List of session references
            connections: List of connection references
            members: List of project members
            created_at: Creation timestamp

        Returns:
            Dictionary with project data matching Project model
        """
        now = created_at or datetime.now(UTC)
        return {
            "id": project_id or f"proj-{uuid4().hex[:8]}",
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "organization_id": organization_id,
            "status": status,
            "workflows": workflows or [],
            "sessions": sessions or [],
            "connections": connections or [],
            "members": members or [ProjectMemberFactory.create_owner(owner_id)],
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def create_with_workflows(
        workflow_count: int = 3,
        name: str = "Project with Workflows",
        owner_id: str = "alice",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a project with workflow references.

        Args:
            workflow_count: Number of workflows to add
            name: Project name
            owner_id: Owner user ID
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with project containing workflow references
        """
        workflows = [
            ProjectWorkflowRefFactory.create(
                workflow_id=f"wf-{i}",
                name=f"Workflow {i + 1}",
            )
            for i in range(workflow_count)
        ]
        return ProjectFactory.create(
            name=name,
            owner_id=owner_id,
            workflows=workflows,
            **kwargs,
        )

    @staticmethod
    def create_with_sessions(
        session_count: int = 3,
        name: str = "Project with Sessions",
        owner_id: str = "alice",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a project with session references.

        Args:
            session_count: Number of sessions to add
            name: Project name
            owner_id: Owner user ID
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with project containing session references
        """
        sessions = [
            ProjectSessionRefFactory.create(
                session_id=f"sess-{i}",
                name=f"Session {i + 1}",
                message_count=i * 5,
            )
            for i in range(session_count)
        ]
        return ProjectFactory.create(
            name=name,
            owner_id=owner_id,
            sessions=sessions,
            **kwargs,
        )

    @staticmethod
    def create_with_team(
        member_count: int = 3,
        name: str = "Team Project",
        owner_id: str = "alice",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a project with multiple team members.

        Args:
            member_count: Number of members (including owner)
            name: Project name
            owner_id: Owner user ID
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with project containing team members
        """
        members = [ProjectMemberFactory.create_owner(owner_id)]

        roles = ["editor", "viewer", "executor"]
        for i in range(1, member_count):
            role = roles[(i - 1) % len(roles)]
            members.append(
                ProjectMemberFactory.create(
                    user_id=f"user-{i}",
                    role=role,
                )
            )

        return ProjectFactory.create(
            name=name,
            owner_id=owner_id,
            members=members,
            **kwargs,
        )

    @staticmethod
    def create_full(
        name: str = "Full Project",
        owner_id: str = "alice",
        workflow_count: int = 2,
        session_count: int = 3,
        connection_count: int = 1,
        member_count: int = 2,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a project with all child resources populated.

        Args:
            name: Project name
            owner_id: Owner user ID
            workflow_count: Number of workflows
            session_count: Number of sessions
            connection_count: Number of connections
            member_count: Number of members
            **kwargs: Additional fields passed to create()

        Returns:
            Dictionary with fully populated project
        """
        workflows = [
            ProjectWorkflowRefFactory.create(
                workflow_id=f"wf-{i}",
                name=f"Workflow {i + 1}",
            )
            for i in range(workflow_count)
        ]

        sessions = [
            ProjectSessionRefFactory.create(
                session_id=f"sess-{i}",
                name=f"Session {i + 1}",
                message_count=i * 5,
            )
            for i in range(session_count)
        ]

        connections = [
            ProjectConnectionFactory.create(
                connection_id=f"conn-{i}",
                name=f"Connection {i + 1}",
            )
            for i in range(connection_count)
        ]

        members = [ProjectMemberFactory.create_owner(owner_id)]
        for i in range(1, member_count):
            members.append(
                ProjectMemberFactory.create(
                    user_id=f"member-{i}",
                    role="editor" if i % 2 == 0 else "viewer",
                )
            )

        return ProjectFactory.create(
            name=name,
            owner_id=owner_id,
            workflows=workflows,
            sessions=sessions,
            connections=connections,
            members=members,
            **kwargs,
        )

    @staticmethod
    def create_summary(
        project_id: str | None = None,
        name: str = "Test Project",
        description: str = "A test project",
        owner_id: str = "alice",
        organization_id: str | None = None,
        status: str = "active",
        workflow_count: int = 0,
        session_count: int = 0,
        connection_count: int = 0,
        member_count: int = 1,
    ) -> dict[str, Any]:
        """
        Create a project summary dictionary.

        Returns:
            Dictionary matching ProjectSummary model
        """
        now = datetime.now(UTC)
        return {
            "id": project_id or f"proj-{uuid4().hex[:8]}",
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "organization_id": organization_id,
            "status": status,
            "workflow_count": workflow_count,
            "session_count": session_count,
            "connection_count": connection_count,
            "member_count": member_count,
            "created_at": now,
            "updated_at": now,
        }


class ProjectWorkflowRefFactory:
    """Factory for creating project workflow references."""

    @staticmethod
    def create(
        workflow_id: str | None = None,
        name: str = "Referenced Workflow",
        added_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a workflow reference for a project."""
        return {
            "id": workflow_id or f"wf-{uuid4().hex[:8]}",
            "name": name,
            "added_at": added_at or datetime.now(UTC),
        }


class ProjectSessionRefFactory:
    """Factory for creating project session references."""

    @staticmethod
    def create(
        session_id: str | None = None,
        name: str = "Referenced Session",
        message_count: int = 0,
        added_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a session reference for a project."""
        return {
            "id": session_id or f"sess-{uuid4().hex[:8]}",
            "name": name,
            "message_count": message_count,
            "added_at": added_at or datetime.now(UTC),
        }


class ProjectConnectionFactory:
    """Factory for creating project connection references."""

    @staticmethod
    def create(
        connection_id: str | None = None,
        name: str = "Project Connection",
        connection_type: str = "mcp_server",
        status: str = "active",
        config: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a connection reference for a project."""
        return {
            "id": connection_id or f"conn-{uuid4().hex[:8]}",
            "connection_type": connection_type,
            "name": name,
            "status": status,
            "config": config,
            "created_at": created_at or datetime.now(UTC),
        }

    @staticmethod
    def create_mcp_server(
        connection_id: str | None = None,
        name: str = "MCP Server Connection",
        url: str = "https://mcp.example.com",
    ) -> dict[str, Any]:
        """Create an MCP server connection reference."""
        return ProjectConnectionFactory.create(
            connection_id=connection_id,
            name=name,
            connection_type="mcp_server",
            config={"url": url},
        )

    @staticmethod
    def create_vector_store(
        connection_id: str | None = None,
        name: str = "Vector Store Connection",
        collection: str = "default",
    ) -> dict[str, Any]:
        """Create a vector store connection reference."""
        return ProjectConnectionFactory.create(
            connection_id=connection_id,
            name=name,
            connection_type="vector_store",
            config={"collection": collection},
        )


class ProjectMemberFactory:
    """Factory for creating project member objects."""

    @staticmethod
    def create(
        user_id: str = "user-001",
        role: str = "viewer",
        added_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a project member."""
        return {
            "user_id": user_id,
            "role": role,
            "added_at": added_at or datetime.now(UTC),
        }

    @staticmethod
    def create_owner(user_id: str = "alice") -> dict[str, Any]:
        """Create an owner member."""
        return ProjectMemberFactory.create(user_id=user_id, role="owner")

    @staticmethod
    def create_editor(user_id: str = "bob") -> dict[str, Any]:
        """Create an editor member."""
        return ProjectMemberFactory.create(user_id=user_id, role="editor")

    @staticmethod
    def create_viewer(user_id: str = "charlie") -> dict[str, Any]:
        """Create a viewer member."""
        return ProjectMemberFactory.create(user_id=user_id, role="viewer")

    @staticmethod
    def create_executor(user_id: str = "executor") -> dict[str, Any]:
        """Create an executor member (can run but not modify)."""
        return ProjectMemberFactory.create(user_id=user_id, role="executor")


# Convenience instances for common test scenarios
empty_project = ProjectFactory.create(
    name="Empty Project",
    description="A project with no resources",
)

team_project = ProjectFactory.create_with_team(
    name="Team Collaboration Project",
    member_count=4,
)

full_project = ProjectFactory.create_full(
    name="Complete Project",
    workflow_count=3,
    session_count=5,
    connection_count=2,
    member_count=3,
)
