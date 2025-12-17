"""
OpenFGA Workflow Sharing Integration

Syncs workflow sharing permissions to OpenFGA authorization tuples.

Mapping:
- view → viewer relation
- edit → editor relation
- execute → executor relation

This module provides a service that:
1. Writes tuples when shares are created
2. Deletes tuples when shares are removed
3. Sets workflow ownership
4. Checks permissions via OpenFGA
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.auth.openfga import OpenFGAClient


# Permission to OpenFGA relation mapping
PERMISSION_TO_RELATION: dict[str, str] = {
    "view": "viewer",
    "edit": "editor",
    "execute": "executor",
}

# All possible share relations (for removal)
ALL_SHARE_RELATIONS = ["viewer", "editor", "executor"]


class OpenFGAWorkflowSharingService:
    """
    Service for syncing workflow shares to OpenFGA.

    Provides a bridge between the workflow sharing API layer and
    the OpenFGA authorization system.

    Usage:
        service = OpenFGAWorkflowSharingService(openfga_client)

        # When a share is created
        await service.sync_share(workflow_id, user_id, permission="view")

        # When a share is removed
        await service.remove_share(workflow_id, user_id)

        # When checking permission
        has_access = await service.check_permission(workflow_id, user_id, "view")
    """

    def __init__(self, openfga_client: OpenFGAClient) -> None:
        """
        Initialize the service.

        Args:
            openfga_client: OpenFGA client instance for writing tuples.
        """
        self._client = openfga_client

    async def sync_share(
        self,
        workflow_id: str,
        user_id: str,
        permission: str,
    ) -> None:
        """
        Sync a workflow share to OpenFGA.

        Writes a tuple establishing the user's permission on the workflow.

        Args:
            workflow_id: The workflow ID.
            user_id: The user ID being granted access.
            permission: Permission level (view, edit, execute).

        Raises:
            ValueError: If permission is not recognized.
            OpenFGAError: If tuple write fails.
        """
        relation = PERMISSION_TO_RELATION.get(permission)
        if relation is None:
            raise ValueError(f"Unknown permission: {permission}. Valid: {list(PERMISSION_TO_RELATION.keys())}")

        tuple_data = {
            "user": f"user:{user_id}",
            "relation": relation,
            "object": f"workflow:{workflow_id}",
        }

        logger.info(
            "Syncing workflow share to OpenFGA",
            extra={
                "workflow_id": workflow_id,
                "user_id": user_id,
                "permission": permission,
                "relation": relation,
            },
        )

        await self._client.write_tuples([tuple_data])

    async def remove_share(
        self,
        workflow_id: str,
        user_id: str,
    ) -> None:
        """
        Remove a workflow share from OpenFGA.

        Deletes all permission tuples for the user on the workflow.
        This is idempotent - succeeds even if no tuples exist.

        Args:
            workflow_id: The workflow ID.
            user_id: The user ID whose access is being revoked.

        Raises:
            OpenFGAError: If tuple deletion fails.
        """
        # Delete all possible share relations for this user/workflow
        tuples_to_delete = [
            {
                "user": f"user:{user_id}",
                "relation": relation,
                "object": f"workflow:{workflow_id}",
            }
            for relation in ALL_SHARE_RELATIONS
        ]

        logger.info(
            "Removing workflow share from OpenFGA",
            extra={
                "workflow_id": workflow_id,
                "user_id": user_id,
                "relations": ALL_SHARE_RELATIONS,
            },
        )

        await self._client.delete_tuples(tuples_to_delete)

    async def set_workflow_owner(
        self,
        workflow_id: str,
        user_id: str,
    ) -> None:
        """
        Set the owner of a workflow in OpenFGA.

        Establishes the owner relationship which grants all permissions
        through the OpenFGA model's computed usersets.

        Args:
            workflow_id: The workflow ID.
            user_id: The owner's user ID.

        Raises:
            OpenFGAError: If tuple write fails.
        """
        tuple_data = {
            "user": f"user:{user_id}",
            "relation": "owner",
            "object": f"workflow:{workflow_id}",
        }

        logger.info(
            "Setting workflow owner in OpenFGA",
            extra={
                "workflow_id": workflow_id,
                "owner_id": user_id,
            },
        )

        await self._client.write_tuples([tuple_data])

    async def check_permission(
        self,
        workflow_id: str,
        user_id: str,
        permission: str,
    ) -> bool:
        """
        Check if a user has permission on a workflow.

        Delegates to OpenFGA to check the permission, which evaluates
        all possible paths (direct grants, ownership, organization membership, etc).

        Args:
            workflow_id: The workflow ID.
            user_id: The user ID to check.
            permission: Permission level (view, edit, execute).

        Returns:
            True if user has the permission, False otherwise.

        Raises:
            ValueError: If permission is not recognized.
            OpenFGAError: If permission check fails.
        """
        relation = PERMISSION_TO_RELATION.get(permission)
        if relation is None:
            raise ValueError(f"Unknown permission: {permission}. Valid: {list(PERMISSION_TO_RELATION.keys())}")

        return await self._client.check_permission(
            user=f"user:{user_id}",
            relation=relation,
            object=f"workflow:{workflow_id}",
        )

    async def delete_workflow_tuples(self, workflow_id: str) -> None:
        """
        Delete all OpenFGA tuples for a workflow.

        Called when a workflow is deleted to clean up authorization data.
        Delegates to the OpenFGA client's delete_tuples_for_object method.

        Args:
            workflow_id: The workflow ID being deleted.

        Raises:
            OpenFGAError: If tuple deletion fails.
        """
        logger.info(
            "Deleting all OpenFGA tuples for workflow",
            extra={"workflow_id": workflow_id},
        )

        await self._client.delete_tuples_for_object(f"workflow:{workflow_id}")


async def get_workflow_sharing_service() -> OpenFGAWorkflowSharingService | None:
    """
    Factory function to get the workflow sharing service.

    Returns None if OpenFGA is not configured.

    Returns:
        OpenFGAWorkflowSharingService instance or None.
    """
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Check if OpenFGA is configured
    if not getattr(settings, "openfga_enabled", False):
        logger.debug("OpenFGA not enabled, workflow sharing service not available")
        return None

    config = OpenFGAConfig(
        api_url=getattr(settings, "openfga_api_url", "http://localhost:8080"),
        store_name=getattr(settings, "openfga_store_name", None),
        preshared_key=getattr(settings, "openfga_preshared_key", None),
    )

    client = OpenFGAClient(config=config)
    return OpenFGAWorkflowSharingService(openfga_client=client)
