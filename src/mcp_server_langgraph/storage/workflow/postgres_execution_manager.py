"""
PostgreSQL-backed Execution History Manager

Provides durable storage for workflow execution history using PostgreSQL.

Features:
- Full CRUD operations for executions
- Status filtering and pagination
- Efficient indexed queries
- Integration with ExecutionHistoryManagerInterface

TDD: Tests in tests/unit/storage/test_postgres_execution_manager.py
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Index, JSON, select, String, Text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.api.v1.workflow_executions import ExecutionHistoryManagerInterface
from mcp_server_langgraph.models.base import Base
from mcp_server_langgraph.observability.telemetry import logger, tracer


# ==============================================================================
# SQLAlchemy Models
# ==============================================================================


class WorkflowExecutionModel(Base):
    """
    SQLAlchemy model for workflow execution storage.

    Table: workflow_executions
    """

    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Composite indices for optimized queries
    __table_args__ = (
        # Index for filtering by workflow_id + status
        Index(
            "ix_workflow_executions_workflow_status",
            "workflow_id",
            "status",
        ),
        # Index for pagination by workflow_id + started_at
        Index(
            "ix_workflow_executions_workflow_started",
            "workflow_id",
            "started_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<WorkflowExecution(id={self.id!r}, workflow_id={self.workflow_id!r}, status={self.status!r})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
        }


# ==============================================================================
# PostgreSQL Execution History Manager
# ==============================================================================


class PostgresExecutionHistoryManager(ExecutionHistoryManagerInterface):
    """
    PostgreSQL-backed execution history manager.

    Provides durable storage for workflow execution history
    with support for filtering, pagination, and efficient queries.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """
        Initialize the PostgreSQL execution history manager.

        Args:
            engine: SQLAlchemy async engine instance.
        """
        self._engine = engine
        self._session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("PostgresExecutionHistoryManager initialized")

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get a workflow by ID.

        Args:
            workflow_id: The workflow ID.

        Returns:
            Workflow dict if found, None otherwise.
        """
        with tracer.start_as_current_span("postgres_execution.get_workflow") as span:
            span.set_attribute("workflow.id", workflow_id)

            # Import here to avoid circular imports
            from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

            async with self._session_maker() as session:
                stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
                result = await session.execute(stmt)
                workflow = result.scalar_one_or_none()

                if workflow is None:
                    return None

                return {
                    "id": workflow.id,
                    "name": workflow.name,
                }

    async def list_executions(
        self,
        workflow_id: str,
        status: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List executions for a workflow.

        Args:
            workflow_id: The workflow ID.
            status: Optional status filter.
            limit: Maximum number of results.
            cursor: Pagination cursor (offset).

        Returns:
            List of execution dictionaries.
        """
        with tracer.start_as_current_span("postgres_execution.list_executions") as span:
            span.set_attribute("workflow.id", workflow_id)
            if status:
                span.set_attribute("filter.status", status)

            async with self._session_maker() as session:
                stmt = (
                    select(WorkflowExecutionModel)
                    .where(WorkflowExecutionModel.workflow_id == workflow_id)
                    .order_by(WorkflowExecutionModel.started_at.desc())
                )

                if status:
                    stmt = stmt.where(WorkflowExecutionModel.status == status)

                # Apply pagination
                if cursor:
                    try:
                        offset = int(cursor)
                        stmt = stmt.offset(offset)
                    except ValueError:
                        pass

                stmt = stmt.limit(limit)

                result = await session.execute(stmt)
                executions = result.scalars().all()

                return [
                    {
                        "id": e.id,
                        "workflow_id": e.workflow_id,
                        "status": e.status,
                        "started_at": e.started_at.isoformat() if e.started_at else None,
                        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                        "input_data": e.input_data,
                        "output_data": e.output_data,
                        "error": e.error,
                    }
                    for e in executions
                ]

    async def get_execution(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a specific execution.

        Args:
            workflow_id: The workflow ID.
            execution_id: The execution ID.

        Returns:
            Execution dict if found, None otherwise.
        """
        with tracer.start_as_current_span("postgres_execution.get_execution") as span:
            span.set_attribute("workflow.id", workflow_id)
            span.set_attribute("execution.id", execution_id)

            async with self._session_maker() as session:
                stmt = select(WorkflowExecutionModel).where(
                    WorkflowExecutionModel.id == execution_id,
                    WorkflowExecutionModel.workflow_id == workflow_id,
                )
                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution is None:
                    return None

                return {
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "input_data": execution.input_data,
                    "output_data": execution.output_data,
                    "error": execution.error,
                }

    # ==============================================================================
    # Additional Methods (beyond interface)
    # ==============================================================================

    async def create_execution(
        self,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
        status: str = "pending",
    ) -> str:
        """
        Create a new execution.

        Args:
            workflow_id: The workflow ID.
            input_data: Optional input data.
            status: Initial status (default: pending).

        Returns:
            The execution ID.
        """
        with tracer.start_as_current_span("postgres_execution.create_execution") as span:
            span.set_attribute("workflow.id", workflow_id)

            execution_id = str(uuid4())
            execution = WorkflowExecutionModel(
                id=execution_id,
                workflow_id=workflow_id,
                status=status,
                started_at=datetime.now(UTC),
                input_data=input_data,
            )

            async with self._session_maker() as session:
                session.add(execution)
                await session.commit()

            span.set_attribute("execution.id", execution_id)
            logger.info(f"Created execution: {execution_id} for workflow: {workflow_id}")

            return execution_id

    async def update_execution(
        self,
        execution_id: str,
        status: str | None = None,
        output_data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Update an execution.

        Args:
            execution_id: The execution ID.
            status: New status (optional).
            output_data: Output data (optional).
            error: Error message (optional).
        """
        with tracer.start_as_current_span("postgres_execution.update_execution") as span:
            span.set_attribute("execution.id", execution_id)

            async with self._session_maker() as session:
                # Find the execution first
                stmt = select(WorkflowExecutionModel).where(WorkflowExecutionModel.id == execution_id)
                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution is None:
                    logger.warning(f"Execution not found for update: {execution_id}")
                    return

                # Update fields
                if status is not None:
                    execution.status = status
                    span.set_attribute("execution.status", status)
                if output_data is not None:
                    execution.output_data = output_data
                if error is not None:
                    execution.error = error

                # Set completion time for terminal states
                if status in ("completed", "failed"):
                    execution.completed_at = datetime.now(UTC)

                await session.commit()

            logger.info(f"Updated execution: {execution_id}")


# ==============================================================================
# Global Execution Manager Instance
# ==============================================================================

# Global execution manager instance (set by application)
_global_execution_manager: PostgresExecutionHistoryManager | None = None


def set_execution_manager(manager: PostgresExecutionHistoryManager) -> None:
    """
    Set global execution manager instance.

    This should be called during application startup.

    Args:
        manager: PostgresExecutionHistoryManager instance.
    """
    global _global_execution_manager
    _global_execution_manager = manager
    logger.info("Global execution manager set")


def get_execution_manager() -> PostgresExecutionHistoryManager | None:
    """
    Get global execution manager instance.

    This is used by WebSocket workflow execution service and other components
    that need access to the execution manager without DI.

    Returns:
        PostgresExecutionHistoryManager if configured, None otherwise.
    """
    return _global_execution_manager


def clear_execution_manager() -> None:
    """
    Clear global execution manager instance.

    Useful for testing to reset state between tests.
    """
    global _global_execution_manager
    _global_execution_manager = None


# ==============================================================================
# Exports
# ==============================================================================

__all__ = [
    "PostgresExecutionHistoryManager",
    "WorkflowExecutionModel",
    # Global getter pattern
    "set_execution_manager",
    "get_execution_manager",
    "clear_execution_manager",
]
