"""
PostgreSQL Implementation of Execution Plan Repository.

Uses SQLAlchemy AsyncSession for async database operations.

Features:
- Full CRUD operations
- Session-based queries
- Pending plan queries
- GDPR compliance (list_by_user, delete_by_user)

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import delete, select, update

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from mcp_server_langgraph.database.execution_plan_models import ExecutionPlanModel
from mcp_server_langgraph.repositories.execution_plan import ExecutionPlanRepository

# Type alias for session factory
SessionFactory = Callable[[], Any]  # Returns context manager yielding AsyncSession


class PostgresExecutionPlanRepository(ExecutionPlanRepository):
    """PostgreSQL implementation of execution plan repository.

    Uses async session factory for connection pooling.
    All methods use context managers for proper session lifecycle.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize with async session factory.

        Args:
            session_factory: Factory that returns async context manager for sessions.
        """
        self._session_factory = session_factory

    def _model_to_pydantic(self, model: ExecutionPlanModel) -> ExecutionPlan:
        """Convert SQLAlchemy model to Pydantic model."""
        return ExecutionPlan(
            plan_id=model.plan_id,
            session_id=model.session_id,
            status=model.status,
            complexity=model.complexity,
            risk_level=model.risk_level,
            task_type=model.task_type,
            executor_model=model.executor_model,
            critic_model=model.critic_model,
            estimated_cost=model.estimated_cost,
            actual_cost=model.actual_cost,
            message=model.message,
            tools_needed=model.tools_needed or [],
            force_approval=model.force_approval,
            confidence=model.confidence,
            suggested_orchestrator=model.suggested_orchestrator,
            critique_rounds=model.critique_rounds,
            thinking_budget=model.thinking_budget,
            created_at=model.created_at,
            expires_at=model.expires_at,
            executed_at=model.executed_at,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            rejected_by=model.rejected_by,
            rejected_at=model.rejected_at,
            rejection_reason=model.rejection_reason,
            user_id=model.user_id,
            created_by=model.created_by,
            embedding_status=model.embedding_status or "pending",
            embedding_error=model.embedding_error,
            embedding_failed_at=model.embedding_failed_at,
        )

    def _pydantic_to_model(self, plan: ExecutionPlan) -> ExecutionPlanModel:
        """Convert Pydantic model to SQLAlchemy model."""
        return ExecutionPlanModel(
            plan_id=plan.plan_id,
            session_id=plan.session_id,
            status=plan.status,
            complexity=plan.complexity,
            risk_level=plan.risk_level,
            task_type=plan.task_type,
            executor_model=plan.executor_model,
            critic_model=plan.critic_model,
            estimated_cost=plan.estimated_cost,
            actual_cost=plan.actual_cost,
            message=plan.message,
            tools_needed=plan.tools_needed,
            force_approval=plan.force_approval,
            confidence=plan.confidence,
            suggested_orchestrator=plan.suggested_orchestrator,
            critique_rounds=plan.critique_rounds,
            thinking_budget=plan.thinking_budget,
            created_at=plan.created_at,
            expires_at=plan.expires_at,
            executed_at=plan.executed_at,
            approved_by=plan.approved_by,
            approved_at=plan.approved_at,
            rejected_by=plan.rejected_by,
            rejected_at=plan.rejected_at,
            rejection_reason=plan.rejection_reason,
            user_id=plan.user_id,
            created_by=plan.created_by,
            embedding_status=plan.embedding_status,
            embedding_error=plan.embedding_error,
            embedding_failed_at=plan.embedding_failed_at,
        )

    async def create(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Create a new execution plan.

        Args:
            plan: The execution plan to store

        Returns:
            The stored execution plan
        """
        async with self._session_factory() as session:
            model = self._pydantic_to_model(plan)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_pydantic(model)

    async def get(self, plan_id: str) -> ExecutionPlan | None:
        """Get an execution plan by ID.

        Args:
            plan_id: The plan ID to retrieve

        Returns:
            The execution plan if found, None otherwise
        """
        async with self._session_factory() as session:
            result = await session.execute(select(ExecutionPlanModel).where(ExecutionPlanModel.plan_id == plan_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def update(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Update an existing execution plan.

        Args:
            plan: The execution plan to update

        Returns:
            The updated execution plan
        """
        async with self._session_factory() as session:
            # Build update values from plan
            values = {
                "status": plan.status,
                "actual_cost": plan.actual_cost,
                "executed_at": plan.executed_at,
                "approved_by": plan.approved_by,
                "approved_at": plan.approved_at,
                "rejected_by": plan.rejected_by,
                "rejected_at": plan.rejected_at,
                "rejection_reason": plan.rejection_reason,
                "embedding_status": plan.embedding_status,
                "embedding_error": plan.embedding_error,
                "embedding_failed_at": plan.embedding_failed_at,
                # Include all mutable fields
                "force_approval": plan.force_approval,
                "confidence": plan.confidence,
                "tools_needed": plan.tools_needed,
            }

            await session.execute(
                update(ExecutionPlanModel).where(ExecutionPlanModel.plan_id == plan.plan_id).values(**values)
            )
            await session.commit()

            # Fetch updated record
            result = await session.execute(select(ExecutionPlanModel).where(ExecutionPlanModel.plan_id == plan.plan_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else plan

    async def delete(self, plan_id: str) -> bool:
        """Delete an execution plan.

        Args:
            plan_id: The plan ID to delete

        Returns:
            True if deleted, False if not found
        """
        async with self._session_factory() as session:
            result = await session.execute(delete(ExecutionPlanModel).where(ExecutionPlanModel.plan_id == plan_id))
            await session.commit()
            return result.rowcount > 0

    async def list_by_session(self, session_id: str) -> list[ExecutionPlan]:
        """List all plans for a session.

        Args:
            session_id: The session ID to filter by

        Returns:
            List of execution plans for the session
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExecutionPlanModel)
                .where(ExecutionPlanModel.session_id == session_id)
                .order_by(ExecutionPlanModel.created_at.desc())
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def list_pending(self) -> list[ExecutionPlan]:
        """List all plans awaiting approval.

        Returns:
            List of execution plans with status 'awaiting_approval'
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExecutionPlanModel)
                .where(ExecutionPlanModel.status == "awaiting_approval")
                .order_by(ExecutionPlanModel.created_at.desc())
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def list_by_user(self, user_id: str) -> list[ExecutionPlan]:
        """List all plans for a user (GDPR export).

        Args:
            user_id: The user ID to filter by

        Returns:
            List of execution plans for the user
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExecutionPlanModel)
                .where(ExecutionPlanModel.user_id == user_id)
                .order_by(ExecutionPlanModel.created_at.desc())
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all plans for a user (GDPR deletion).

        Args:
            user_id: The user ID to delete plans for

        Returns:
            Count of deleted plans
        """
        async with self._session_factory() as session:
            result = await session.execute(delete(ExecutionPlanModel).where(ExecutionPlanModel.user_id == user_id))
            await session.commit()
            return result.rowcount

    async def list_pending_embeddings(self, limit: int = 100) -> list[ExecutionPlan]:
        """List plans with pending embeddings for background processing.

        Args:
            limit: Maximum number of plans to return

        Returns:
            List of plans needing embedding generation
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExecutionPlanModel)
                .where(ExecutionPlanModel.embedding_status == "pending")
                .order_by(ExecutionPlanModel.created_at.asc())
                .limit(limit)
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]
