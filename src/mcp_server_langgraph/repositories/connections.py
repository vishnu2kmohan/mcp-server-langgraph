"""
PostgreSQL MCP Connection Repository Implementation

Implements the ConnectionRepository interface for persistent MCP server
connection storage using SQLAlchemy async with PostgreSQL.

Supports:
- OAuth 2.1 authentication (per MCP 2025-03-26 / 2025-06-18 spec)
- API Key authentication
- Secrets provider integration for credential storage
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.models.connection import (
    MCPConnectionModel,
    OAuth2StateModel,
)
from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionUpdate,
    OAuth2Config,
)


class SecretsProvider(Protocol):
    """Protocol for secrets provider integration."""

    async def set_secret(self, secret_id: str, value: str) -> None:
        """Store a secret value."""
        ...

    async def get_secret(self, secret_id: str) -> str | None:
        """Retrieve a secret value."""
        ...

    async def delete_secret(self, secret_id: str) -> None:
        """Delete a secret value."""
        ...


class ConnectionRepository(ABC):
    """Abstract base class for connection repository."""

    @abstractmethod
    async def create(
        self,
        data: MCPConnectionCreate,
        owner_id: str,
    ) -> MCPConnection:
        """Create a new MCP connection."""
        pass

    @abstractmethod
    async def get(self, connection_id: str) -> MCPConnection | None:
        """Get connection by ID."""
        pass

    @abstractmethod
    async def get_many(self, connection_ids: list[str]) -> list[MCPConnection]:
        """Get multiple connections by their IDs."""
        pass

    @abstractmethod
    async def update(
        self,
        connection_id: str,
        data: MCPConnectionUpdate,
    ) -> MCPConnection | None:
        """Update connection configuration."""
        pass

    @abstractmethod
    async def delete(self, connection_id: str) -> bool:
        """Delete connection and associated secrets."""
        pass

    @abstractmethod
    async def list(
        self,
        owner_id: str,
        cursor: str | None = None,
        limit: int = 20,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MCPConnectionSummary], str | None]:
        """List connections with filtering and pagination."""
        pass

    # Secret management
    @abstractmethod
    async def store_api_key(self, connection_id: str, api_key: str) -> None:
        """Store API key securely."""
        pass

    @abstractmethod
    async def get_api_key(self, connection_id: str) -> str | None:
        """Retrieve API key."""
        pass

    # OAuth2 state management
    @abstractmethod
    async def create_oauth2_state(
        self,
        connection_id: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> None:
        """Create OAuth2 state for PKCE flow."""
        pass

    @abstractmethod
    async def get_and_delete_oauth2_state(self, state: str) -> dict[str, Any] | None:
        """Get and delete OAuth2 state (one-time use)."""
        pass

    # OAuth2 token management
    @abstractmethod
    async def store_oauth2_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> None:
        """Store OAuth2 tokens securely."""
        pass

    @abstractmethod
    async def get_oauth2_access_token(self, connection_id: str) -> str | None:
        """Get current access token."""
        pass

    # Status management
    @abstractmethod
    async def update_status(
        self,
        connection_id: str,
        status: str,
        server_name: str | None = None,
        server_version: str | None = None,
        tool_count: int | None = None,
        resource_count: int | None = None,
        prompt_count: int | None = None,
        last_error: str | None = None,
    ) -> None:
        """Update connection status and server info."""
        pass


class PostgresConnectionRepository(ConnectionRepository):
    """PostgreSQL implementation of ConnectionRepository."""

    def __init__(
        self,
        session: AsyncSession,
        secrets_provider: SecretsProvider,
    ) -> None:
        """Initialize with async database session and secrets provider."""
        self._session = session
        self._secrets = secrets_provider

    def _model_to_entity(self, model: MCPConnectionModel) -> MCPConnection:
        """Convert SQLAlchemy model to Pydantic entity."""
        oauth2_config = None
        if model.auth_type == "oauth2":
            oauth2_config = OAuth2Config(
                client_id=model.oauth2_client_id,
                authorization_url=model.oauth2_authorization_url,
                token_url=model.oauth2_token_url,
                scopes=model.oauth2_scopes or [],
            )

        return MCPConnection(
            id=str(model.id),
            name=model.name,
            description=model.description,
            url=model.url,
            auth_type=model.auth_type,  # type: ignore[arg-type]
            oauth2_config=oauth2_config,
            status=model.status,  # type: ignore[arg-type]
            last_error=model.last_error,
            last_connected_at=model.last_connected_at,
            server_name=model.server_name,
            server_version=model.server_version,
            server_capabilities=model.server_capabilities,
            tool_count=model.tool_count,
            resource_count=model.resource_count,
            prompt_count=model.prompt_count,
            owner_id=model.owner_id,
            organization_id=str(model.organization_id) if model.organization_id else None,
            project_id=str(model.project_id) if model.project_id else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: MCPConnectionModel) -> MCPConnectionSummary:
        """Convert SQLAlchemy model to summary Pydantic model."""
        return MCPConnectionSummary(
            id=str(model.id),
            name=model.name,
            url=model.url,
            auth_type=model.auth_type,  # type: ignore[arg-type]
            status=model.status,  # type: ignore[arg-type]
            server_name=model.server_name,
            tool_count=model.tool_count,
            resource_count=model.resource_count,
            prompt_count=model.prompt_count,
            last_connected_at=model.last_connected_at,
            created_at=model.created_at,
        )

    async def create(
        self,
        data: MCPConnectionCreate,
        owner_id: str,
    ) -> MCPConnection:
        """Create a new MCP connection."""
        connection_id = str(uuid4())
        now = datetime.now(UTC)

        model = MCPConnectionModel(
            id=connection_id,
            name=data.name,
            description=data.description,
            url=data.url,
            auth_type=data.auth_type,
            oauth2_client_id=data.oauth2_client_id if data.auth_type == "oauth2" else None,
            oauth2_scopes=data.oauth2_scopes if data.auth_type == "oauth2" else None,
            status="disconnected",
            owner_id=owner_id,
            project_id=data.project_id,
            tool_count=0,
            resource_count=0,
            prompt_count=0,
            created_at=now,
            updated_at=now,
        )

        self._session.add(model)
        await self._session.flush()

        # Store secrets
        if data.auth_type == "api_key" and data.api_key:
            await self.store_api_key(connection_id, data.api_key)

        if data.auth_type == "oauth2" and data.oauth2_client_secret:
            await self._store_oauth2_client_secret(connection_id, data.oauth2_client_secret)

        return self._model_to_entity(model)

    async def get(self, connection_id: str) -> MCPConnection | None:
        """Get connection by ID."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def get_many(self, connection_ids: list[str]) -> list[MCPConnection]:
        """Get multiple connections by their IDs."""
        if not connection_ids:
            return []

        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id.in_(connection_ids))
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(m) for m in models]

    async def update(
        self,
        connection_id: str,
        data: MCPConnectionUpdate,
    ) -> MCPConnection | None:
        """Update connection configuration."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        # Update fields
        if data.name is not None:
            model.name = data.name
        if data.description is not None:
            model.description = data.description
        if data.url is not None:
            model.url = data.url

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return self._model_to_entity(model)

    async def delete(self, connection_id: str) -> bool:
        """Delete connection and associated secrets."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        # Delete associated secrets
        if model.api_key_secret_id:
            await self._secrets.delete_secret(model.api_key_secret_id)
        if model.oauth2_client_secret_id:
            await self._secrets.delete_secret(model.oauth2_client_secret_id)
        if model.oauth2_token_secret_id:
            await self._secrets.delete_secret(model.oauth2_token_secret_id)
        if model.oauth2_refresh_token_secret_id:
            await self._secrets.delete_secret(model.oauth2_refresh_token_secret_id)

        await self._session.delete(model)
        await self._session.flush()

        return True

    async def list(
        self,
        owner_id: str,
        cursor: str | None = None,
        limit: int = 20,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MCPConnectionSummary], str | None]:
        """List connections with filtering and pagination."""
        # Build base query
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.owner_id == owner_id)

        # Apply filters
        if status:
            stmt = stmt.where(MCPConnectionModel.status == status)
        if auth_type:
            stmt = stmt.where(MCPConnectionModel.auth_type == auth_type)
        if project_id:
            stmt = stmt.where(MCPConnectionModel.project_id == project_id)

        # Full-text search
        if search:
            search_term = search.replace(" ", " & ")
            stmt = stmt.where(MCPConnectionModel.search_vector.op("@@")(func.plainto_tsquery("english", search_term)))

        # Cursor pagination
        if cursor:
            # Decode cursor (created_at timestamp + id)
            try:
                cursor_time, cursor_id = cursor.split("_", 1)
                cursor_dt = datetime.fromisoformat(cursor_time)
                if sort_order == "desc":
                    stmt = stmt.where(
                        or_(
                            MCPConnectionModel.created_at < cursor_dt,
                            and_(
                                MCPConnectionModel.created_at == cursor_dt,
                                MCPConnectionModel.id < cursor_id,
                            ),
                        )
                    )
                else:
                    stmt = stmt.where(
                        or_(
                            MCPConnectionModel.created_at > cursor_dt,
                            and_(
                                MCPConnectionModel.created_at == cursor_dt,
                                MCPConnectionModel.id > cursor_id,
                            ),
                        )
                    )
            except ValueError:
                pass  # Invalid cursor, ignore

        # Sorting
        sort_column = getattr(MCPConnectionModel, sort_by, MCPConnectionModel.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc(), MCPConnectionModel.id.desc())
        else:
            stmt = stmt.order_by(sort_column.asc(), MCPConnectionModel.id.asc())

        # Limit + 1 to check for more pages
        stmt = stmt.limit(limit + 1)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        # Check for next page
        has_more = len(models) > limit
        if has_more:
            models = models[:limit]

        # Build next cursor
        next_cursor = None
        if has_more and models:
            last_model = models[-1]
            next_cursor = f"{last_model.created_at.isoformat()}_{last_model.id}"

        return [self._model_to_summary(m) for m in models], next_cursor

    async def store_api_key(self, connection_id: str, api_key: str) -> None:
        """Store API key in secrets provider."""
        secret_id = f"mcp_conn_{connection_id}_api_key"
        await self._secrets.set_secret(secret_id, api_key)

        # Update connection with secret reference
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.api_key_secret_id = secret_id
            await self._session.flush()

    async def get_api_key(self, connection_id: str) -> str | None:
        """Retrieve API key from secrets provider."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model and model.api_key_secret_id:
            return await self._secrets.get_secret(model.api_key_secret_id)

        return None

    async def _store_oauth2_client_secret(
        self,
        connection_id: str,
        client_secret: str,
    ) -> None:
        """Store OAuth2 client secret in secrets provider."""
        secret_id = f"mcp_conn_{connection_id}_client_secret"
        await self._secrets.set_secret(secret_id, client_secret)

        # Update connection with secret reference
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.oauth2_client_secret_id = secret_id
            await self._session.flush()

    async def create_oauth2_state(
        self,
        connection_id: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> None:
        """Create OAuth2 state for PKCE flow."""
        state_model = OAuth2StateModel(
            id=str(uuid4()),
            connection_id=connection_id,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        self._session.add(state_model)
        await self._session.flush()

    async def get_and_delete_oauth2_state(self, state: str) -> dict[str, Any] | None:
        """Get and delete OAuth2 state (one-time use)."""
        stmt = select(OAuth2StateModel).where(
            and_(
                OAuth2StateModel.state == state,
                OAuth2StateModel.expires_at > datetime.now(UTC),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        # Extract data before deletion
        data = {
            "connection_id": str(model.connection_id),
            "state": model.state,
            "code_verifier": model.code_verifier,
            "redirect_uri": model.redirect_uri,
        }

        # Delete (one-time use)
        await self._session.delete(model)
        await self._session.flush()

        return data

    async def store_oauth2_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> None:
        """Store OAuth2 tokens securely."""
        # Store access token
        access_token_secret_id = f"mcp_conn_{connection_id}_access_token"
        await self._secrets.set_secret(access_token_secret_id, access_token)

        # Store refresh token if provided
        refresh_token_secret_id = None
        if refresh_token:
            refresh_token_secret_id = f"mcp_conn_{connection_id}_refresh_token"
            await self._secrets.set_secret(refresh_token_secret_id, refresh_token)

        # Update connection with token references
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.oauth2_token_secret_id = access_token_secret_id
            model.oauth2_refresh_token_secret_id = refresh_token_secret_id
            model.oauth2_token_expires_at = expires_at
            model.status = "connected"
            model.updated_at = datetime.now(UTC)
            await self._session.flush()

    async def get_oauth2_access_token(self, connection_id: str) -> str | None:
        """Get current access token."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model and model.oauth2_token_secret_id:
            # Check if token is expired
            if model.oauth2_token_expires_at and model.oauth2_token_expires_at < datetime.now(UTC):
                return None  # Token expired, needs refresh
            return await self._secrets.get_secret(model.oauth2_token_secret_id)

        return None

    async def update_status(
        self,
        connection_id: str,
        status: str,
        server_name: str | None = None,
        server_version: str | None = None,
        tool_count: int | None = None,
        resource_count: int | None = None,
        prompt_count: int | None = None,
        last_error: str | None = None,
    ) -> None:
        """Update connection status and server info."""
        stmt = select(MCPConnectionModel).where(MCPConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.status = status
            if server_name is not None:
                model.server_name = server_name
            if server_version is not None:
                model.server_version = server_version
            if tool_count is not None:
                model.tool_count = tool_count
            if resource_count is not None:
                model.resource_count = resource_count
            if prompt_count is not None:
                model.prompt_count = prompt_count
            if last_error is not None:
                model.last_error = last_error
            if status == "connected":
                model.last_connected_at = datetime.now(UTC)
                model.last_error = None

            model.updated_at = datetime.now(UTC)
            await self._session.flush()
