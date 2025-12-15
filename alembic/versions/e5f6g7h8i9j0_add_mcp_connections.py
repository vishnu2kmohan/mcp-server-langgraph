"""Add MCP connections with OAuth2 and API Key authentication

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-14

Creates:
- mcp_connections: MCP server connection configuration with auth
- mcp_oauth2_states: OAuth2 PKCE flow state storage

Implements:
- OAuth 2.1 with PKCE (MCP 2025-03-26 / 2025-06-18 spec)
- API Key authentication
- Secrets provider references (not raw credentials)
- Server metadata caching (tools, resources, prompts counts)
- Full-text search support
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | Sequence[str] | None = "d4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create MCP connections schema with OAuth2 and API Key support.

    Security notes:
    - Credentials stored via secrets provider references, not raw values
    - OAuth2 states are single-use and expire after 10 minutes
    - PKCE required for all OAuth2 flows (per MCP spec)
    """
    # 1. MCP_CONNECTIONS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_connections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            url VARCHAR(2048) NOT NULL,

            -- Authentication configuration
            auth_type VARCHAR(50) NOT NULL DEFAULT 'none',

            -- API Key auth (secret_id references secrets provider)
            api_key_secret_id VARCHAR(255),

            -- OAuth2 configuration
            oauth2_client_id VARCHAR(255),
            oauth2_client_secret_id VARCHAR(255),
            oauth2_authorization_url VARCHAR(2048),
            oauth2_token_url VARCHAR(2048),
            oauth2_scopes TEXT[],
            oauth2_token_secret_id VARCHAR(255),
            oauth2_refresh_token_secret_id VARCHAR(255),
            oauth2_token_expires_at TIMESTAMPTZ,

            -- Connection state
            status VARCHAR(50) NOT NULL DEFAULT 'disconnected',
            last_error TEXT,
            last_connected_at TIMESTAMPTZ,

            -- Server info (populated after successful connection)
            server_name VARCHAR(255),
            server_version VARCHAR(50),
            server_capabilities JSONB,

            -- Tool/resource counts (cached)
            tool_count INTEGER NOT NULL DEFAULT 0,
            resource_count INTEGER NOT NULL DEFAULT 0,
            prompt_count INTEGER NOT NULL DEFAULT 0,

            -- Ownership and multi-tenancy
            owner_id VARCHAR(255) NOT NULL,
            organization_id UUID,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Constraints
            CONSTRAINT mcp_connections_auth_type_valid
                CHECK (auth_type IN ('none', 'api_key', 'oauth2')),
            CONSTRAINT mcp_connections_status_valid
                CHECK (status IN (
                    'disconnected', 'connecting', 'connected', 'error', 'auth_required'
                )),
            CONSTRAINT mcp_connections_name_not_empty
                CHECK (LENGTH(name) > 0),
            CONSTRAINT mcp_connections_url_not_empty
                CHECK (LENGTH(url) > 0),
            CONSTRAINT mcp_connections_counts_positive
                CHECK (tool_count >= 0 AND resource_count >= 0 AND prompt_count >= 0)
        )
        """
    )

    # 2. INDEXES FOR MCP_CONNECTIONS
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_owner ON mcp_connections(owner_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mcp_connections_org "
        "ON mcp_connections(organization_id) WHERE organization_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mcp_connections_project ON mcp_connections(project_id) WHERE project_id IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_status ON mcp_connections(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_url ON mcp_connections(url)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_owner_created ON mcp_connections(owner_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_auth_type ON mcp_connections(auth_type)")

    # 3. FULL-TEXT SEARCH VECTOR
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(server_name, '')), 'C')
        ) STORED
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_connections_search ON mcp_connections USING GIN(search_vector)")

    # 4. UPDATED_AT TRIGGER
    op.execute("DROP TRIGGER IF EXISTS update_mcp_connections_updated_at ON mcp_connections")
    op.execute(
        """
        CREATE TRIGGER update_mcp_connections_updated_at
            BEFORE UPDATE ON mcp_connections
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )

    # 5. COMMENTS
    op.execute("COMMENT ON TABLE mcp_connections IS 'MCP server connections with OAuth2 and API Key authentication'")
    op.execute(
        "COMMENT ON COLUMN mcp_connections.api_key_secret_id IS 'Reference to API key in secrets provider (not raw value)'"
    )
    op.execute(
        "COMMENT ON COLUMN mcp_connections.oauth2_client_secret_id IS 'Reference to OAuth2 client secret in secrets provider'"
    )
    op.execute(
        "COMMENT ON COLUMN mcp_connections.oauth2_token_secret_id IS 'Reference to current access token in secrets provider'"
    )

    # 6. MCP_OAUTH2_STATES TABLE (for PKCE flow)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_oauth2_states (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            connection_id UUID NOT NULL
                REFERENCES mcp_connections(id) ON DELETE CASCADE,
            state VARCHAR(255) NOT NULL UNIQUE,
            code_verifier VARCHAR(255) NOT NULL,
            redirect_uri VARCHAR(2048) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes'),

            -- Constraints
            CONSTRAINT mcp_oauth2_states_state_not_empty
                CHECK (LENGTH(state) > 0),
            CONSTRAINT mcp_oauth2_states_verifier_not_empty
                CHECK (LENGTH(code_verifier) >= 43)
        )
        """
    )

    # 7. INDEXES FOR OAUTH2_STATES
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_oauth2_states_state ON mcp_oauth2_states(state)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_oauth2_states_expires ON mcp_oauth2_states(expires_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcp_oauth2_states_connection ON mcp_oauth2_states(connection_id)")

    # 8. COMMENTS FOR OAUTH2_STATES
    op.execute("COMMENT ON TABLE mcp_oauth2_states IS 'OAuth2 PKCE flow state storage (single-use, expires in 10 minutes)'")
    op.execute("COMMENT ON COLUMN mcp_oauth2_states.code_verifier IS 'PKCE code verifier (min 43 chars per RFC 7636)'")

    # 9. CLEANUP FUNCTION FOR EXPIRED STATES
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_oauth2_states()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM mcp_oauth2_states
            WHERE expires_at < NOW();

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        "COMMENT ON FUNCTION cleanup_expired_oauth2_states IS "
        "'Removes expired OAuth2 states - call periodically or via pg_cron'"
    )


def downgrade() -> None:
    """
    Drop MCP connections tables.

    WARNING: This will delete all MCP connection data permanently.
    """
    # Drop function first
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_oauth2_states()")

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_mcp_connections_updated_at ON mcp_connections")

    # Drop tables in reverse order (respecting foreign keys)
    op.execute("DROP TABLE IF EXISTS mcp_oauth2_states CASCADE")
    op.execute("DROP TABLE IF EXISTS mcp_connections CASCADE")
