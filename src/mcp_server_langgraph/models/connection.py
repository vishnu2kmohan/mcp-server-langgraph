"""
MCP Connection SQLAlchemy Models

Implements MCP server connection management with:
- OAuth 2.1 authentication (per MCP 2025-03-26 / 2025-06-18 spec)
- API Key authentication
- No authentication (local/development servers)
- Secrets provider integration (credentials stored via references)

Uses modern SQLAlchemy 2.0+ async patterns with type annotations.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ConnectionBase(DeclarativeBase):
    """Base class for connection-related models."""

    pass


class MCPConnectionModel(ConnectionBase):
    """
    MCP server connection with OAuth2 and API Key authentication.

    Implements:
    - OAuth 2.1 with PKCE (per MCP specification)
    - API Key authentication
    - Secrets provider references (not raw credentials)
    - Server metadata caching
    - Full-text search support
    """

    __tablename__ = "mcp_connections"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        nullable=False,
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Authentication type: 'none' | 'api_key' | 'oauth2'
    auth_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="none",
    )

    # API Key auth (secret_id references secrets provider)
    api_key_secret_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # OAuth2 configuration
    oauth2_client_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    oauth2_client_secret_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    oauth2_authorization_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    oauth2_token_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    oauth2_scopes: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    oauth2_token_secret_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    oauth2_refresh_token_secret_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    oauth2_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Connection state
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="disconnected",
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Server info (populated after successful connection)
    server_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    server_capabilities: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Tool/resource counts (cached)
    tool_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Ownership and multi-tenancy
    owner_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Full-text search vector (PostgreSQL generated stored column)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(name, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(description, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(server_name, '')), 'C')",
            persisted=True,
        ),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    oauth2_states: Mapped[list["OAuth2StateModel"]] = relationship(
        "OAuth2StateModel",
        back_populates="connection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_mcp_connections_owner_created", "owner_id", "created_at"),
        Index("ix_mcp_connections_auth_type", "auth_type"),
        Index("ix_mcp_connections_status", "status"),
        Index("ix_mcp_connections_url", "url"),
        Index(
            "ix_mcp_connections_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )


class OAuth2StateModel(ConnectionBase):
    """
    OAuth2 PKCE flow state storage.

    Single-use, expires after 10 minutes.
    Used to validate OAuth2 callbacks and prevent CSRF attacks.
    """

    __tablename__ = "mcp_oauth2_states"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        nullable=False,
    )
    connection_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mcp_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    code_verifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    redirect_uri: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    connection: Mapped["MCPConnectionModel"] = relationship(
        "MCPConnectionModel",
        back_populates="oauth2_states",
    )

    __table_args__ = (
        Index("ix_mcp_oauth2_states_expires", "expires_at"),
        Index("ix_mcp_oauth2_states_connection", "connection_id"),
    )
