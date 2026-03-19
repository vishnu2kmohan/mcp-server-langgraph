"""
PostgreSQL Implementation of Checkpoint Repository.

Uses SQLAlchemy AsyncSession for async database operations.
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import delete, select

from mcp_server_langgraph.memory.checkpoints import Checkpoint
from mcp_server_langgraph.repositories.checkpoint import CheckpointRepository
from mcp_server_langgraph.repositories.postgres_models.agentic import PhaseCheckpointModel

SessionFactory = Callable[[], Any]


class PostgresCheckpointRepository(CheckpointRepository):
    """PostgreSQL implementation of checkpoint repository."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _model_to_pydantic(self, model: PhaseCheckpointModel) -> Checkpoint:
        return Checkpoint(
            id=model.id,
            phase=model.phase,
            summary=model.summary,
            created_at=model.created_at,
            artifacts=model.artifacts if isinstance(model.artifacts, list) else [],
            metadata=model.metadata_json if isinstance(model.metadata_json, dict) else {},
            session_id=model.session_id,
            user_id=model.user_id,
        )

    def _pydantic_to_model(self, checkpoint: Checkpoint) -> PhaseCheckpointModel:
        return PhaseCheckpointModel(
            id=checkpoint.id,
            phase=checkpoint.phase,
            summary=checkpoint.summary,
            created_at=checkpoint.created_at,
            artifacts=checkpoint.artifacts,
            metadata_json=checkpoint.metadata,
            session_id=checkpoint.session_id,
            user_id=checkpoint.user_id,
        )

    async def create(self, checkpoint: Checkpoint) -> Checkpoint:
        async with self._session_factory() as session:
            model = self._pydantic_to_model(checkpoint)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_pydantic(model)

    async def get(self, checkpoint_id: str) -> Checkpoint | None:
        async with self._session_factory() as session:
            result = await session.execute(select(PhaseCheckpointModel).where(PhaseCheckpointModel.id == checkpoint_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def get_latest(self, *, user_id: str | None = None) -> Checkpoint | None:
        async with self._session_factory() as session:
            query = select(PhaseCheckpointModel)
            if user_id:
                query = query.where(PhaseCheckpointModel.user_id == user_id)
            query = query.order_by(PhaseCheckpointModel.created_at.desc()).limit(1)

            result = await session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def list(
        self,
        *,
        phase: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Checkpoint]:
        async with self._session_factory() as session:
            query = select(PhaseCheckpointModel)
            if phase:
                query = query.where(PhaseCheckpointModel.phase == phase)
            if user_id:
                query = query.where(PhaseCheckpointModel.user_id == user_id)
            query = query.order_by(PhaseCheckpointModel.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return [self._model_to_pydantic(m) for m in result.scalars().all()]

    async def delete(self, checkpoint_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(delete(PhaseCheckpointModel).where(PhaseCheckpointModel.id == checkpoint_id))
            await session.commit()
            return result.rowcount > 0

    async def clear(self) -> None:
        async with self._session_factory() as session:
            await session.execute(delete(PhaseCheckpointModel))
            await session.commit()

    async def summarize(self, *, user_id: str | None = None) -> str:
        checkpoints = await self.list(user_id=user_id, limit=1000)
        if not checkpoints:
            return "No checkpoints recorded."

        # Sort ascending for chronological summary
        checkpoints.sort(key=lambda c: c.created_at)

        lines = ["# Session Summary", ""]
        for checkpoint in checkpoints:
            lines.append(f"## {checkpoint.phase.title()}")
            lines.append(checkpoint.summary)
            lines.append("")

        return "\n".join(lines)

    async def list_by_user(self, user_id: str) -> list[Checkpoint]:
        return await self.list(user_id=user_id, limit=10000)

    async def delete_by_user(self, user_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(delete(PhaseCheckpointModel).where(PhaseCheckpointModel.user_id == user_id))
            await session.commit()
            return result.rowcount
