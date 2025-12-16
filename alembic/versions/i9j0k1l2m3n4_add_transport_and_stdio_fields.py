"""Add transport protocol and stdio configuration fields to MCP connections

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2025-12-16

Adds per MCP 2025-11-25 specification:
- transport: Transport protocol (streamable_http or stdio)
- command: Command to execute for stdio transport
- args: Command arguments for stdio transport
- env: Environment variables for stdio transport

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: str | Sequence[str] | None = "h8i9j0k1l2m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add transport protocol and stdio configuration fields to mcp_connections.

    MCP 2025-11-25 Transport Support:
    - streamable_http: HTTP endpoint with SSE streaming (default)
    - stdio: Standard I/O for local subprocess-based servers

    For stdio transport, we need:
    - command: The executable to run (e.g., "python", "npx")
    - args: Command line arguments (e.g., ["-m", "mcp_server"])
    - env: Environment variables to pass to the process
    """
    # Add transport column with default 'streamable_http' for existing rows
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS transport VARCHAR(50) NOT NULL DEFAULT 'streamable_http';
        """
    )

    # Add stdio configuration columns
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS command TEXT;
        """
    )

    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS args TEXT[];
        """
    )

    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS env JSONB;
        """
    )

    # Add constraint for valid transport values
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT mcp_connections_transport_valid
        CHECK (transport IN ('streamable_http', 'stdio'));
        """
    )

    # Add index on transport for filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mcp_connections_transport
        ON mcp_connections (transport);
        """
    )

    # Add comment for documentation
    op.execute(
        """
        COMMENT ON COLUMN mcp_connections.transport IS
        'Transport protocol: streamable_http (default) or stdio per MCP 2025-11-25';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN mcp_connections.command IS
        'Command to execute for stdio transport (e.g., python, npx)';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN mcp_connections.args IS
        'Command arguments array for stdio transport (e.g., [-m, mcp_server])';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN mcp_connections.env IS
        'Environment variables JSONB for stdio transport';
        """
    )


def downgrade() -> None:
    """Remove transport and stdio configuration fields."""
    # Drop constraint first
    op.execute(
        """
        ALTER TABLE mcp_connections
        DROP CONSTRAINT IF EXISTS mcp_connections_transport_valid;
        """
    )

    # Drop index
    op.execute(
        """
        DROP INDEX IF EXISTS ix_mcp_connections_transport;
        """
    )

    # Drop columns
    op.execute(
        """
        ALTER TABLE mcp_connections
        DROP COLUMN IF EXISTS transport,
        DROP COLUMN IF EXISTS command,
        DROP COLUMN IF EXISTS args,
        DROP COLUMN IF EXISTS env;
        """
    )
