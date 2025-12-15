"""Add projects tables for Unified Workspace Paradigm

Revision ID: a1b2c3d4e5f6
Revises: 8348487e5796
Create Date: 2025-12-13

Creates:
- projects: Core project entity (unified workspace container)
- project_workflows: Junction table for project-workflow associations
- project_sessions: Junction table for project-session associations
- project_connections: Connections (MCP, vectors, API keys) per project
- project_members: Project membership with roles
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "8348487e5796"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create projects schema for Unified Workspace Paradigm.

    Implements:
    - One Project = Session + Workflow + Connections
    - OpenFGA integration ready (owner, editor, viewer, executor roles)
    - Cascade delete for child resources
    """
    # 1. PROJECTS TABLE (core entity)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            organization_id VARCHAR(36),
            owner_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Constraints
            CONSTRAINT projects_name_not_empty CHECK (LENGTH(name) > 0),
            CONSTRAINT projects_status_valid CHECK (status IN ('active', 'archived', 'deleted'))
        )
        """
    )

    # Indexes for projects
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_owner ON projects(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_org ON projects(organization_id) WHERE organization_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_owner_created ON projects(owner_id, created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_org_status "
        "ON projects(organization_id, status) WHERE organization_id IS NOT NULL"
    )

    # Comments for projects
    op.execute("COMMENT ON TABLE projects IS 'Unified workspace container - implements Unified Workspace Paradigm'")

    # 2. PROJECT_WORKFLOWS TABLE (junction)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_workflows (
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            workflow_id UUID NOT NULL,
            workflow_name VARCHAR(255) NOT NULL,
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            PRIMARY KEY (project_id, workflow_id)
        )
        """
    )

    # Indexes for project_workflows
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_workflows_workflow ON project_workflows(workflow_id)")

    # Comments for project_workflows
    op.execute("COMMENT ON TABLE project_workflows IS 'Associates workflows with projects (many-to-many)'")

    # 3. PROJECT_SESSIONS TABLE (junction)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_sessions (
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            session_id UUID NOT NULL,
            session_name VARCHAR(255) NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            PRIMARY KEY (project_id, session_id),

            -- Constraints
            CONSTRAINT project_sessions_message_count_positive
                CHECK (message_count >= 0)
        )
        """
    )

    # Indexes for project_sessions
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_sessions_session ON project_sessions(session_id)")

    # Comments for project_sessions
    op.execute("COMMENT ON TABLE project_sessions IS 'Associates sessions with projects (many-to-many)'")

    # 4. PROJECT_CONNECTIONS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_connections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            connection_type VARCHAR(50) NOT NULL,
            connection_name VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            config JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Constraints
            CONSTRAINT project_connections_type_valid
                CHECK (connection_type IN ('mcp_server', 'vector_store', 'api_key')),
            CONSTRAINT project_connections_status_valid
                CHECK (status IN ('active', 'inactive', 'error'))
        )
        """
    )

    # Indexes for project_connections
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_connections_project ON project_connections(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_connections_type ON project_connections(project_id, connection_type)")

    # Comments for project_connections
    op.execute(
        "COMMENT ON TABLE project_connections IS 'Connections (MCP servers, vector stores, API keys) associated with projects'"
    )

    # 5. PROJECT_MEMBERS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_members (
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            PRIMARY KEY (project_id, user_id),

            -- Constraints
            CONSTRAINT project_members_role_valid
                CHECK (role IN ('owner', 'editor', 'viewer', 'executor'))
        )
        """
    )

    # Indexes for project_members
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_user ON project_members(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_role ON project_members(project_id, role)")

    # Comments for project_members
    op.execute("COMMENT ON TABLE project_members IS 'Project membership with roles (owner, editor, viewer, executor)'")

    # 6. UPDATED_AT TRIGGER FUNCTION (if not exists)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """
    )

    # 7. TRIGGER FOR PROJECTS UPDATED_AT
    # Note: asyncpg doesn't support multiple statements in one execute
    op.execute("DROP TRIGGER IF EXISTS update_projects_updated_at ON projects")
    op.execute(
        """
        CREATE TRIGGER update_projects_updated_at
            BEFORE UPDATE ON projects
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )


def downgrade() -> None:
    """
    Drop all project-related tables.

    WARNING: This will delete all project data permanently.
    """
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS update_projects_updated_at ON projects")

    # Drop tables in reverse order (respecting foreign keys)
    op.execute("DROP TABLE IF EXISTS project_members CASCADE")
    op.execute("DROP TABLE IF EXISTS project_connections CASCADE")
    op.execute("DROP TABLE IF EXISTS project_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS project_workflows CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")

    # Note: We don't drop the update_updated_at_column function
    # as it may be used by other tables
