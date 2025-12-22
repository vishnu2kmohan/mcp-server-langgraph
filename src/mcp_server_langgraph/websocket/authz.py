"""
WebSocket Authorization Middleware.

Implements fine-grained authorization for WebSocket endpoints using OpenFGA.
Uses ReBAC (Relationship-Based Access Control) where permissions are derived
from user relationships to resources, not static roles.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.auth.openfga import OpenFGAClient

logger = logging.getLogger(__name__)


async def get_openfga_client() -> OpenFGAClient | None:
    """
    Get the OpenFGA client instance.

    Returns:
        OpenFGA client if configured, None otherwise.
    """
    try:
        from mcp_server_langgraph.auth.openfga import get_openfga_client as _get_client

        return await _get_client()
    except Exception as e:
        logger.debug(f"OpenFGA client not available: {e}")
        return None


class WebSocketAuthorizationMiddleware:
    """
    Fine-grained authorization for WebSocket endpoints using OpenFGA.

    Implements ReBAC (Relationship-Based Access Control) where permissions
    are derived from user relationships to resources, not static roles.

    Two-phase authorization:
    1. Connection phase: Check if user can connect to the endpoint at all
    2. Subscription phase: Check if user can subscribe to specific resources
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: str | None = None,
        required_relation: str = "viewer",
        fail_closed: bool = True,
    ) -> None:
        """
        Initialize authorization middleware.

        Args:
            resource_type: OpenFGA resource type (e.g., "dashboard", "workflow").
            resource_id: Specific resource ID, or None for wildcard check.
            required_relation: Required relation (e.g., "viewer", "editor", "admin").
            fail_closed: If True, deny access on errors. If False, allow on errors.
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.required_relation = required_relation
        self.fail_closed = fail_closed

    async def authorize_connection(self, user_id: str) -> bool:
        """
        Check if user can establish WebSocket connection.

        Called during WebSocket handshake after authentication.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            True if authorized, False otherwise.
        """
        openfga = await get_openfga_client()
        if openfga is None:
            logger.debug("OpenFGA not configured, using fail-closed policy")
            return not self.fail_closed

        resource = f"{self.resource_type}:{self.resource_id or '*'}"

        try:
            allowed = await openfga.check_permission(
                user=f"user:{user_id}",
                relation=self.required_relation,
                object=resource,
            )
            logger.debug(
                f"OpenFGA check: user={user_id}, relation={self.required_relation}, object={resource}, allowed={allowed}"
            )
            return bool(allowed)
        except Exception as e:
            logger.warning(f"OpenFGA authorization error: {e}")
            return not self.fail_closed

    async def authorize_subscription(
        self,
        user_id: str,
        resource_id: str,
    ) -> bool:
        """
        Check if user can subscribe to specific resource updates.

        Called when client sends a subscribe message for a specific resource.

        Args:
            user_id: The authenticated user's ID.
            resource_id: The specific resource to subscribe to.

        Returns:
            True if authorized, False otherwise.
        """
        openfga = await get_openfga_client()
        if openfga is None:
            return not self.fail_closed

        resource = f"{self.resource_type}:{resource_id}"

        try:
            allowed = await openfga.check_permission(
                user=f"user:{user_id}",
                relation=self.required_relation,
                object=resource,
            )
            logger.debug(
                f"OpenFGA subscription check: user={user_id}, "
                f"relation={self.required_relation}, object={resource}, allowed={allowed}"
            )
            return bool(allowed)
        except Exception as e:
            logger.warning(f"OpenFGA subscription authorization error: {e}")
            return not self.fail_closed

    async def authorize_action(
        self,
        user_id: str,
        resource_id: str,
        action_relation: str | None = None,
    ) -> bool:
        """
        Check if user can perform a specific action on a resource.

        Args:
            user_id: The authenticated user's ID.
            resource_id: The resource ID.
            action_relation: Optional different relation for this action.

        Returns:
            True if authorized, False otherwise.
        """
        relation = action_relation or self.required_relation
        openfga = await get_openfga_client()
        if openfga is None:
            return not self.fail_closed

        resource = f"{self.resource_type}:{resource_id}"

        try:
            allowed = await openfga.check_permission(
                user=f"user:{user_id}",
                relation=relation,
                object=resource,
            )
            return bool(allowed)
        except Exception as e:
            logger.warning(f"OpenFGA action authorization error: {e}")
            return not self.fail_closed
