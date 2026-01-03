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


class InMemoryExecutionPlanRepository(ExecutionPlanRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        """Initialize empty plan storage."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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
        return [
            plan for plan in self._plans.values() if plan.session_id == session_id
        ]

    async def list_pending(self) -> list[ExecutionPlan]:
        """List all plans awaiting approval."""
        return [
            plan
            for plan in self._plans.values()
            if plan.status == "awaiting_approval"
        ]
