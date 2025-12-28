"""
Budget Storage Service

Provides persistence layer for budget configurations.

Supports:
- In-memory storage for development/testing
- PostgreSQL storage for production (via BudgetRecord model)

Usage:
    >>> from mcp_server_langgraph.monitoring.budget_storage import get_budget_storage
    >>> storage = get_budget_storage()
    >>> budget = await storage.get_budget("organization", "organization:acme")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, Protocol, runtime_checkable

from mcp_server_langgraph.monitoring.cost_budget import Budget

logger = logging.getLogger(__name__)


# ==============================================================================
# Protocol Definition
# ==============================================================================


@runtime_checkable
class BudgetStorageProtocol(Protocol):
    """
    Protocol for budget storage backends.

    Defines the interface for loading and saving budget configurations.
    Implementations include:
    - MemoryBudgetStorage: In-memory storage for testing
    - PostgresBudgetStorage: Database storage for production
    """

    async def get_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> Budget | None:
        """
        Get a budget by entity type and ID.

        Args:
            entity_type: Type of entity (organization, project, team, user)
            entity_id: Unique identifier for the entity

        Returns:
            Budget if found, None otherwise
        """
        ...

    async def save_budget(self, budget: Budget) -> None:
        """
        Save or update a budget.

        If a budget for the entity already exists, it will be updated.

        Args:
            budget: Budget to save
        """
        ...

    async def list_budgets(
        self,
        entity_type: Literal["organization", "project", "team", "user"] | None = None,
    ) -> list[Budget]:
        """
        List all budgets, optionally filtered by entity type.

        Args:
            entity_type: Optional filter by entity type

        Returns:
            List of budgets
        """
        ...

    async def delete_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> bool:
        """
        Delete a budget.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier

        Returns:
            True if budget was deleted, False if not found
        """
        ...


# ==============================================================================
# In-Memory Implementation
# ==============================================================================


class MemoryBudgetStorage:
    """
    In-memory budget storage for development and testing.

    Thread-safe using asyncio.Lock.
    """

    def __init__(self) -> None:
        """Initialize empty storage."""
        self._budgets: dict[str, Budget] = {}
        self._lock = asyncio.Lock()

    def _make_key(
        self,
        entity_type: str,
        entity_id: str,
    ) -> str:
        """Create a unique key for budget lookup."""
        return f"{entity_type}:{entity_id}"

    async def get_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> Budget | None:
        """Get a budget by entity type and ID."""
        async with self._lock:
            key = self._make_key(entity_type, entity_id)
            return self._budgets.get(key)

    async def save_budget(self, budget: Budget) -> None:
        """Save or update a budget."""
        async with self._lock:
            key = self._make_key(budget.entity_type, budget.entity_id)
            self._budgets[key] = budget
            logger.debug(
                f"Saved budget for {budget.entity_type}:{budget.entity_id}",
                extra={"entity_type": budget.entity_type, "entity_id": budget.entity_id},
            )

    async def list_budgets(
        self,
        entity_type: Literal["organization", "project", "team", "user"] | None = None,
    ) -> list[Budget]:
        """List all budgets, optionally filtered by entity type."""
        async with self._lock:
            if entity_type is None:
                return list(self._budgets.values())
            return [b for b in self._budgets.values() if b.entity_type == entity_type]

    async def delete_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> bool:
        """Delete a budget."""
        async with self._lock:
            key = self._make_key(entity_type, entity_id)
            if key in self._budgets:
                del self._budgets[key]
                logger.debug(
                    f"Deleted budget for {entity_type}:{entity_id}",
                    extra={"entity_type": entity_type, "entity_id": entity_id},
                )
                return True
            return False


# ==============================================================================
# PostgreSQL Implementation
# ==============================================================================


class PostgresBudgetStorage:
    """
    PostgreSQL budget storage for production use.

    Uses the BudgetRecord SQLAlchemy model for persistence.
    """

    def __init__(self, session_maker: Any) -> None:
        """
        Initialize with a session maker.

        Args:
            session_maker: SQLAlchemy async session maker
        """
        self._session_maker = session_maker

    async def get_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> Budget | None:
        """Get a budget by entity type and ID."""
        from sqlalchemy import select

        from mcp_server_langgraph.database.models import BudgetRecord

        async with self._session_maker() as session:
            stmt = select(BudgetRecord).where(
                BudgetRecord.entity_type == entity_type,
                BudgetRecord.entity_id == entity_id,
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record is None:
                return None

            return self._record_to_budget(record)

    async def save_budget(self, budget: Budget) -> None:
        """Save or update a budget."""
        from mcp_server_langgraph.database.models import BudgetRecord

        async with self._session_maker() as session:
            # Create or update record using merge
            record = BudgetRecord(
                entity_type=budget.entity_type,
                entity_id=budget.entity_id,
                monthly_limit_usd=budget.monthly_limit_usd,
                warning_threshold=budget.warning_threshold,
                critical_threshold=budget.critical_threshold,
                name=budget.name,
                description=budget.description,
                enabled=budget.enabled if hasattr(budget, "enabled") else True,
            )
            await session.merge(record)
            await session.commit()
            logger.debug(
                f"Saved budget for {budget.entity_type}:{budget.entity_id} to PostgreSQL",
                extra={"entity_type": budget.entity_type, "entity_id": budget.entity_id},
            )

    async def list_budgets(
        self,
        entity_type: Literal["organization", "project", "team", "user"] | None = None,
    ) -> list[Budget]:
        """List all budgets, optionally filtered by entity type."""
        from sqlalchemy import select

        from mcp_server_langgraph.database.models import BudgetRecord

        async with self._session_maker() as session:
            stmt = select(BudgetRecord)
            if entity_type is not None:
                stmt = stmt.where(BudgetRecord.entity_type == entity_type)

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [self._record_to_budget(r) for r in records]

    async def delete_budget(
        self,
        entity_type: Literal["organization", "project", "team", "user"],
        entity_id: str,
    ) -> bool:
        """Delete a budget."""
        from sqlalchemy import select

        from mcp_server_langgraph.database.models import BudgetRecord

        async with self._session_maker() as session:
            stmt = select(BudgetRecord).where(
                BudgetRecord.entity_type == entity_type,
                BudgetRecord.entity_id == entity_id,
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record is None:
                return False

            await session.delete(record)
            await session.commit()
            logger.debug(
                f"Deleted budget for {entity_type}:{entity_id} from PostgreSQL",
                extra={"entity_type": entity_type, "entity_id": entity_id},
            )
            return True

    @staticmethod
    def _record_to_budget(record: Any) -> Budget:
        """Convert a BudgetRecord to a Budget."""
        return Budget(
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            monthly_limit_usd=record.monthly_limit_usd,
            warning_threshold=float(record.warning_threshold),
            critical_threshold=float(record.critical_threshold),
            name=record.name,
            description=record.description,
        )


# ==============================================================================
# Singleton and Factory
# ==============================================================================

_storage_instance: BudgetStorageProtocol | None = None


def get_budget_storage() -> BudgetStorageProtocol:
    """
    Get the budget storage singleton.

    Returns an in-memory storage by default.
    In production, this should be configured to use PostgresBudgetStorage.

    Returns:
        BudgetStorage instance
    """
    global _storage_instance
    if _storage_instance is None:
        # Default to in-memory storage
        # Production/staging uses PostgresBudgetStorage via app_factory.py
        _storage_instance = MemoryBudgetStorage()
        logger.info("Initialized MemoryBudgetStorage")
    return _storage_instance


def set_budget_storage(storage: BudgetStorageProtocol | None) -> None:
    """
    Set the budget storage singleton.

    Used for dependency injection in app_factory.py.

    Args:
        storage: BudgetStorage instance, or None to reset
    """
    global _storage_instance
    _storage_instance = storage
    if storage is not None:
        logger.info(f"Budget storage set to {type(storage).__name__}")


def _reset_budget_storage() -> None:
    """
    Reset the budget storage singleton.

    For testing purposes only - NOT for production use.
    """
    global _storage_instance
    _storage_instance = None
