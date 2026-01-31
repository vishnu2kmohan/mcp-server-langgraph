"""
Plan Persistence Service.

Persists execution plans with immediate commit for streaming compatibility.

Features:
- Immediate commit for plan row existence before streaming begins
- Memory mode: Uses injected repo from app.state
- Postgres mode: Creates dedicated session with immediate commit

Phase 5: Persist Plan Generation (chat.py integration)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp_server_langgraph.core.config import settings

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
    from mcp_server_langgraph.repositories.execution_plan import ExecutionPlanRepository

logger = logging.getLogger(__name__)


class PlanPersistenceService:
    """Persists plans with immediate commit for streaming compatibility.

    CRITICAL: In memory mode, pass the repo explicitly to write to the singleton.

    Usage:
        # Memory mode: pass repo from app.state
        plan_repo = request.app.state.execution_plan_repo
        service = PlanPersistenceService(plan_repo=plan_repo)
        await service.persist_plan(execution_plan)

        # Postgres mode: repo is optional (creates own session)
        service = PlanPersistenceService()
        await service.persist_plan(execution_plan)
    """

    def __init__(self, plan_repo: ExecutionPlanRepository | None = None) -> None:
        """Initialize with optional repo for memory mode.

        Args:
            plan_repo: For memory mode, pass the singleton repo from app.state.
                      For postgres mode, this is ignored (new session created).
        """
        self._plan_repo = plan_repo

    async def persist_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Persist plan with immediate commit (streaming-safe).

        Memory mode: Uses injected repo (must be the app.state singleton)
        Postgres mode: Creates dedicated session with immediate commit

        Args:
            plan: The execution plan to persist.

        Returns:
            The persisted plan.

        Raises:
            RuntimeError: If called in memory mode without repo.
        """
        if settings.plan_storage_backend != "postgres":
            # Memory mode: use injected repo
            if self._plan_repo is None:
                raise RuntimeError(
                    "persist_plan called in memory mode without repo - "
                    "this would cause data loss. Pass plan_repo to constructor."
                )
            return await self._plan_repo.create(plan)

        # Postgres mode: create dedicated session for immediate commit
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(settings.database_url)
        async with session_maker() as session:
            try:
                # Create a factory wrapper for the repository
                class SingleSessionFactory:
                    def __init__(self, sess):
                        self._session = sess

                    def __call__(self):
                        return self

                    async def __aenter__(self):
                        return self._session

                    async def __aexit__(self, *args):
                        pass

                # Note: We use raw session here for immediate commit instead of repo
                # (PostgresExecutionPlanRepository uses deferred commit patterns)
                from mcp_server_langgraph.database.execution_plan_models import (
                    ExecutionPlanModel,
                )

                model = ExecutionPlanModel(
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
                session.add(model)
                await session.commit()  # IMMEDIATE COMMIT
                logger.debug(f"Persisted plan {plan.plan_id} to postgres")
                return plan
            except Exception:
                await session.rollback()
                raise
