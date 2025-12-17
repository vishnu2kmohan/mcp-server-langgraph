"""
Workflow Share Repository Implementations.

Provides storage implementations for workflow sharing:
- InMemoryWorkflowShareRepository: For testing and development
- PostgresWorkflowShareRepository: For production use (future)

These repositories implement the WorkflowShareRepositoryProtocol.
"""

import secrets
from typing import Any, Protocol, runtime_checkable

from mcp_server_langgraph.storage.workflow.models import WorkflowShare


@runtime_checkable
class WorkflowShareRepositoryProtocol(Protocol):
    """
    Protocol for workflow share repository implementations.

    Defines the interface for storing and retrieving workflow shares.
    """

    async def create_share(self, share: WorkflowShare) -> None:
        """
        Create or update a share.

        If a share already exists for the same workflow_id + user_id,
        the permission is updated.

        Args:
            share: The share to create or update.
        """
        ...

    async def get_shares(self, workflow_id: str) -> list[WorkflowShare]:
        """
        Get all shares for a workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            List of shares for the workflow.
        """
        ...

    async def get_share(self, workflow_id: str, user_id: str) -> WorkflowShare | None:
        """
        Get a specific share by workflow_id and user_id.

        Args:
            workflow_id: The workflow ID.
            user_id: The user ID.

        Returns:
            The share if found, None otherwise.
        """
        ...

    async def delete_share(self, workflow_id: str, user_id: str) -> bool:
        """
        Delete a share.

        Args:
            workflow_id: The workflow ID.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def list_shared_with_user(self, user_id: str) -> list[str]:
        """
        List workflow IDs shared with a user.

        Args:
            user_id: The user ID.

        Returns:
            List of workflow IDs shared with the user.
        """
        ...

    async def update_workflow_public(self, workflow_id: str, is_public: bool) -> dict[str, Any] | None:
        """
        Update public visibility of a workflow.

        When made public, generates a share_link. When made private,
        clears the share_link.

        Args:
            workflow_id: The workflow ID.
            is_public: Whether to make the workflow public.

        Returns:
            Dict with is_public and share_link, or None if workflow not found.
        """
        ...

    async def get_by_share_link(self, share_link: str) -> str | None:
        """
        Get workflow ID by share link.

        Args:
            share_link: The public share link.

        Returns:
            The workflow ID if found, None otherwise.
        """
        ...


class InMemoryWorkflowShareRepository:
    """
    In-memory implementation of workflow share repository.

    Stores shares in memory for testing and development.
    NOT suitable for production use.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        # shares indexed by (workflow_id, user_id)
        self._shares: dict[tuple[str, str], WorkflowShare] = {}
        # workflow public state: workflow_id -> {"is_public": bool, "share_link": str|None}
        self._workflows: dict[str, dict[str, Any]] = {}
        # share_link -> workflow_id mapping
        self._share_links: dict[str, str] = {}

    async def create_share(self, share: WorkflowShare) -> None:
        """
        Create or update a share.

        If a share already exists for the same workflow_id + user_id,
        the permission is updated.
        """
        key = (share.workflow_id, share.user_id)
        self._shares[key] = share

    async def get_shares(self, workflow_id: str) -> list[WorkflowShare]:
        """Get all shares for a workflow."""
        return [share for (wf_id, _), share in self._shares.items() if wf_id == workflow_id]

    async def get_share(self, workflow_id: str, user_id: str) -> WorkflowShare | None:
        """Get a specific share by workflow_id and user_id."""
        return self._shares.get((workflow_id, user_id))

    async def delete_share(self, workflow_id: str, user_id: str) -> bool:
        """Delete a share. Returns True if deleted, False if not found."""
        key = (workflow_id, user_id)
        if key in self._shares:
            del self._shares[key]
            return True
        return False

    async def list_shared_with_user(self, user_id: str) -> list[str]:
        """List workflow IDs shared with a user."""
        return [wf_id for (wf_id, uid), _ in self._shares.items() if uid == user_id]

    async def update_workflow_public(self, workflow_id: str, is_public: bool) -> dict[str, Any] | None:
        """
        Update public visibility of a workflow.

        When made public, generates a share_link. When made private,
        clears the share_link.
        """
        if workflow_id not in self._workflows:
            return None

        # Clear old share_link if exists
        old_state = self._workflows[workflow_id]
        old_link = old_state.get("share_link")
        if old_link and old_link in self._share_links:
            del self._share_links[old_link]

        # Generate new share_link if public
        share_link: str | None = None
        if is_public:
            share_link = secrets.token_urlsafe(16)
            self._share_links[share_link] = workflow_id

        # Update state
        self._workflows[workflow_id] = {
            "is_public": is_public,
            "share_link": share_link,
        }

        return self._workflows[workflow_id]

    async def get_by_share_link(self, share_link: str) -> str | None:
        """Get workflow ID by share link."""
        return self._share_links.get(share_link)
