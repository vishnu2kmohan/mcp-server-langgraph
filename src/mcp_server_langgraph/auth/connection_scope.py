"""
Connection Scope Authorization

Implements scope-aware access control for MCP connections.

Scope semantics:
- user: Personal connection - only owner can use
- project: Shared connection - project members can use (checked via OpenFGA)
- session: Ephemeral connection - only within the same session

Reference: Phase 6 - Connections Page Redesign Plan (Scope Model)
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.observability.telemetry import logger

__all__ = ["ConnectionScope", "ConnectionLike"]


class ConnectionScope(str, Enum):
    """
    Connection access scope for authorization.

    Determines who can access and use the connection.

    Note: Defined here in auth module (not models) to avoid SQLAlchemy
    dependency in lightweight deployments.
    """

    USER = "user"  # Personal - only owner can use
    PROJECT = "project"  # Shared - project members can use
    SESSION = "session"  # Ephemeral - session-only, not persisted


if TYPE_CHECKING:
    from mcp_server_langgraph.auth.openfga import OpenFGAClient


class ConnectionLike(Protocol):
    """Protocol for connection objects supporting scope checks."""

    id: str
    owner_id: str
    scope: str
    project_id: str | None
    session_id: str | None


async def can_use_connection(
    connection: Any,
    user_id: str,
    project_id: str | None = None,
    session_id: str | None = None,
    openfga_client: "OpenFGAClient | None" = None,
) -> bool:
    """
    Check if a user can use a connection based on its scope.

    Implements scope-based access control:
    1. Owner can always use their own connections (any scope)
    2. Project-scoped: project members can use (verified via OpenFGA)
    3. Session-scoped: only within the same session

    Args:
        connection: Connection entity with scope, owner_id, project_id, session_id
        user_id: User ID attempting to use the connection (e.g., "user:alice")
        project_id: Current project context (required for project-scoped access)
        session_id: Current session context (required for session-scoped access)
        openfga_client: OpenFGA client for project membership checks

    Returns:
        True if user can use the connection, False otherwise

    Example:
        >>> conn = MCPConnection(scope="project", owner_id="user:alice", project_id="proj-1")
        >>> allowed = await can_use_connection(conn, "user:bob", project_id="proj-1", openfga_client=fga)
    """
    # 1. Owner can always use their own connections
    if connection.owner_id == user_id:
        logger.debug(
            "Connection access granted - owner",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "scope": connection.scope,
            },
        )
        return True

    # 2. Check scope-based access for non-owners
    scope = connection.scope

    if scope == ConnectionScope.USER.value:
        # User-scoped: only owner (already checked above)
        logger.debug(
            "Connection access denied - user scope, not owner",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "owner_id": connection.owner_id,
            },
        )
        return False

    if scope == ConnectionScope.PROJECT.value:
        # Project-scoped: require project context match and membership
        return await _check_project_scope_access(
            connection=connection,
            user_id=user_id,
            project_id=project_id,
            openfga_client=openfga_client,
        )

    if scope == ConnectionScope.SESSION.value:
        # Session-scoped: require session match
        return _check_session_scope_access(
            connection=connection,
            user_id=user_id,
            session_id=session_id,
        )

    # Unknown scope - deny access
    logger.warning(
        "Connection access denied - unknown scope",
        extra={
            "connection_id": connection.id,
            "user_id": user_id,
            "scope": scope,
        },
    )
    return False


async def _check_project_scope_access(
    connection: Any,
    user_id: str,
    project_id: str | None,
    openfga_client: "OpenFGAClient | None",
) -> bool:
    """
    Check project-scoped connection access.

    Requires:
    1. Connection has a project_id
    2. User is in the same project context
    3. User is a member of the project (verified via OpenFGA)

    Args:
        connection: Connection entity
        user_id: User ID attempting access
        project_id: Current project context
        openfga_client: OpenFGA client for membership verification

    Returns:
        True if user is a project member, False otherwise
    """
    # Require project context
    if not project_id:
        logger.debug(
            "Connection access denied - no project context for project-scoped connection",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
            },
        )
        return False

    # Require connection to be in a project
    if not connection.project_id:
        logger.debug(
            "Connection access denied - project-scoped connection has no project_id",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
            },
        )
        return False

    # Require same project
    if connection.project_id != project_id:
        logger.debug(
            "Connection access denied - project mismatch",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "connection_project_id": connection.project_id,
                "request_project_id": project_id,
            },
        )
        return False

    # Check project membership via OpenFGA
    if not openfga_client:
        logger.warning(
            "Connection access denied - no OpenFGA client for project membership check",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "project_id": project_id,
            },
        )
        return False

    try:
        is_member = await openfga_client.check_permission(
            user=user_id,
            relation="member",
            object=f"project:{project_id}",
        )

        if is_member:
            logger.debug(
                "Connection access granted - project member",
                extra={
                    "connection_id": connection.id,
                    "user_id": user_id,
                    "project_id": project_id,
                },
            )
        else:
            logger.debug(
                "Connection access denied - not a project member",
                extra={
                    "connection_id": connection.id,
                    "user_id": user_id,
                    "project_id": project_id,
                },
            )

        return is_member

    except Exception as e:
        logger.error(
            f"Connection access denied - OpenFGA check failed: {e}",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "project_id": project_id,
            },
            exc_info=True,
        )
        # Fail closed on error
        return False


def _check_session_scope_access(
    connection: Any,
    user_id: str,
    session_id: str | None,
) -> bool:
    """
    Check session-scoped connection access.

    Session-scoped connections are ephemeral and only accessible within
    the same session. This is useful for temporary connections created
    during a chat session that shouldn't persist.

    Args:
        connection: Connection entity with session_id
        user_id: User ID attempting access
        session_id: Current session context

    Returns:
        True if session matches, False otherwise
    """
    # Require session context
    if not session_id:
        logger.debug(
            "Connection access denied - no session context for session-scoped connection",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
            },
        )
        return False

    # Get connection's session ID
    connection_session_id = getattr(connection, "session_id", None)

    if not connection_session_id:
        logger.debug(
            "Connection access denied - session-scoped connection has no session_id",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
            },
        )
        return False

    # Check session match
    if connection_session_id == session_id:
        logger.debug(
            "Connection access granted - same session",
            extra={
                "connection_id": connection.id,
                "user_id": user_id,
                "session_id": session_id,
            },
        )
        return True

    logger.debug(
        "Connection access denied - session mismatch",
        extra={
            "connection_id": connection.id,
            "user_id": user_id,
            "connection_session_id": connection_session_id,
            "request_session_id": session_id,
        },
    )
    return False


async def filter_accessible_connections(
    connections: list[Any],
    user_id: str,
    project_id: str | None = None,
    session_id: str | None = None,
    openfga_client: "OpenFGAClient | None" = None,
) -> list[Any]:
    """
    Filter a list of connections to only those the user can access.

    Useful for listing connections where some may be project-scoped
    and only visible to project members.

    Args:
        connections: List of connection entities to filter
        user_id: User ID attempting access
        project_id: Current project context
        session_id: Current session context
        openfga_client: OpenFGA client for membership checks

    Returns:
        List of connections the user can access
    """
    accessible = []
    for connection in connections:
        if await can_use_connection(
            connection=connection,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            openfga_client=openfga_client,
        ):
            accessible.append(connection)
    return accessible
