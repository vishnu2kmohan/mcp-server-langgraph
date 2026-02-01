"""
Execution Plan Repository Implementation

Provides storage and retrieval of execution plans for approval workflows.

Supports:
- Create/Read/Update/Delete operations
- Query by session ID
- Query pending approvals

Uses ExecutionPlan model from core.models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan


class ExecutionPlanRepository(ABC):
    """Abstract base class for execution plan repository."""

    @abstractmethod
    async def create(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Create a new execution plan.

        Args:
            plan: The execution plan to store

        Returns:
            The stored execution plan
        """
        pass

    @abstractmethod
    async def get(self, plan_id: str) -> ExecutionPlan | None:
        """Get an execution plan by ID.

        Args:
            plan_id: The plan ID to retrieve

        Returns:
            The execution plan if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Update an existing execution plan.

        Args:
            plan: The execution plan to update

        Returns:
            The updated execution plan
        """
        pass

    @abstractmethod
    async def delete(self, plan_id: str) -> bool:
        """Delete an execution plan.

        Args:
            plan_id: The plan ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_by_session(self, session_id: str) -> list[ExecutionPlan]:
        """List all plans for a session.

        Args:
            session_id: The session ID to filter by

        Returns:
            List of execution plans for the session
        """
        pass

    @abstractmethod
    async def list_pending(self) -> list[ExecutionPlan]:
        """List all plans awaiting approval.

        Returns:
            List of execution plans with status 'awaiting_approval'
        """
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[ExecutionPlan]:
        """List all plans for a user (GDPR export).

        Args:
            user_id: The user ID to filter by

        Returns:
            List of execution plans for the user
        """
        pass

    @abstractmethod
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all plans for a user (GDPR deletion).

        Args:
            user_id: The user ID to delete plans for

        Returns:
            Count of deleted plans
        """
        pass

    @abstractmethod
    async def list_pending_embeddings(self, limit: int = 100) -> list[ExecutionPlan]:
        """List plans with pending embeddings for background processing.

        Args:
            limit: Maximum number of plans to return

        Returns:
            List of plans needing embedding generation
        """
        pass

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ExecutionPlan]:
        """List all execution plans with pagination.

        Args:
            limit: Maximum number of plans to return (capped at 1000)
            offset: Number of plans to skip (capped at 100000)

        Returns:
            List of execution plans sorted by created_at DESC
        """
        pass


class InMemoryExecutionPlanRepository(ExecutionPlanRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        """Initialize empty plan storage."""

        self._plans: dict[str, ExecutionPlan] = {}

    async def create(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Create a new execution plan."""
        self._plans[plan.plan_id] = plan
        return plan

    async def get(self, plan_id: str) -> ExecutionPlan | None:
        """Get an execution plan by ID."""
        return self._plans.get(plan_id)

    async def update(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Update an existing execution plan."""
        self._plans[plan.plan_id] = plan
        return plan

    async def delete(self, plan_id: str) -> bool:
        """Delete an execution plan."""
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False

    async def list_by_session(self, session_id: str) -> list[ExecutionPlan]:
        """List all plans for a session."""
        return [plan for plan in self._plans.values() if plan.session_id == session_id]

    async def list_pending(self) -> list[ExecutionPlan]:
        """List all plans awaiting approval."""
        return [plan for plan in self._plans.values() if plan.status == "awaiting_approval"]

    async def list_by_user(self, user_id: str) -> list[ExecutionPlan]:
        """List all plans for a user (GDPR export)."""
        return [plan for plan in self._plans.values() if plan.user_id == user_id]

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all plans for a user (GDPR deletion)."""
        to_delete = [plan_id for plan_id, plan in self._plans.items() if plan.user_id == user_id]
        for plan_id in to_delete:
            del self._plans[plan_id]
        return len(to_delete)

    async def list_pending_embeddings(self, limit: int = 100) -> list[ExecutionPlan]:
        """List plans with pending embeddings for background processing."""
        pending = [plan for plan in self._plans.values() if getattr(plan, "embedding_status", "pending") == "pending"]
        return sorted(pending, key=lambda p: p.created_at)[:limit]

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ExecutionPlan]:
        """List all execution plans with pagination.

        v35.0: Sorted by created_at DESC with hard caps on limit/offset.
        """
        # Apply hard caps (v35.0)
        capped_limit = min(limit, 1000)
        capped_offset = min(offset, 100000)

        # Sort by created_at DESC (newest first)
        sorted_plans = sorted(
            self._plans.values(),
            key=lambda p: p.created_at,
            reverse=True,
        )

        # Apply pagination
        return sorted_plans[capped_offset : capped_offset + capped_limit]


# Singleton pattern for shared InMemory repository (v35.0)
_plan_repository: InMemoryExecutionPlanRepository | None = None


def get_plan_repository() -> InMemoryExecutionPlanRepository:
    """Get the shared InMemory execution plan repository singleton.

    Returns:
        The shared InMemoryExecutionPlanRepository instance
    """
    global _plan_repository
    if _plan_repository is None:
        _plan_repository = InMemoryExecutionPlanRepository()
    return _plan_repository


def reset_plan_repository() -> None:
    """Reset the shared InMemory repository (for testing).

    Creates a fresh repository instance, clearing all stored plans.
    """
    global _plan_repository
    _plan_repository = None
