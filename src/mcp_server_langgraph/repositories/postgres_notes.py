"""
PostgreSQL Implementation of Notes Repository.

Uses SQLAlchemy AsyncSession for async database operations.
Full-text search via tsvector GIN index with plainto_tsquery.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from sqlalchemy import delete, func, select

from mcp_server_langgraph.memory.notes import Note
from mcp_server_langgraph.repositories.notes import NotesRepository
from mcp_server_langgraph.repositories.postgres_models.agentic import NoteModel

SessionFactory = Callable[[], Any]

MAX_QUERY_LENGTH = 500


class PostgresNotesRepository(NotesRepository):
    """PostgreSQL implementation of notes repository."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _model_to_pydantic(self, model: NoteModel) -> Note:
        return Note(
            id=model.id,
            content=model.content,
            category=model.category,
            tags=model.tags if isinstance(model.tags, list) else [],
            created_at=model.created_at,
            metadata=model.metadata_json if isinstance(model.metadata_json, dict) else {},
            session_id=model.session_id,
            user_id=model.user_id,
            title=model.title,
            slug=model.slug,
        )

    def _pydantic_to_model(self, note: Note) -> NoteModel:
        return NoteModel(
            id=note.id,
            content=note.content,
            category=note.category,
            tags=note.tags,
            created_at=note.created_at,
            metadata_json=note.metadata,
            session_id=note.session_id,
            user_id=note.user_id,
            title=note.title,
            slug=note.slug,
        )

    async def create(self, note: Note) -> Note:
        async with self._session_factory() as session:
            model = self._pydantic_to_model(note)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_pydantic(model)

    async def get(self, note_id: str) -> Note | None:
        async with self._session_factory() as session:
            result = await session.execute(select(NoteModel).where(NoteModel.id == note_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def delete(self, note_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(delete(NoteModel).where(NoteModel.id == note_id))
            await session.commit()
            return result.rowcount > 0

    async def list(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Note]:
        async with self._session_factory() as session:
            query = select(NoteModel)
            if category:
                query = query.where(NoteModel.category == category)
            if session_id:
                query = query.where(NoteModel.session_id == session_id)
            if user_id:
                query = query.where(NoteModel.user_id == user_id)
            query = query.order_by(NoteModel.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return [self._model_to_pydantic(m) for m in result.scalars().all()]

    async def count(
        self,
        *,
        category: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        async with self._session_factory() as session:
            query = select(func.count(NoteModel.id))
            if category:
                query = query.where(NoteModel.category == category)
            if session_id:
                query = query.where(NoteModel.session_id == session_id)
            if user_id:
                query = query.where(NoteModel.user_id == user_id)

            result = await session.execute(query)
            return result.scalar_one()

    async def search(self, query: str, *, limit: int = 100) -> list[Note]:
        if not query:
            return await self.list(limit=limit)

        # Truncate query for safety
        search_term = query[:MAX_QUERY_LENGTH].strip()

        async with self._session_factory() as session:
            if len(search_term) < 3:
                # Short queries: fall back to ILIKE with escaped wildcards
                escaped = re.sub(r"([%_\\])", r"\\\1", search_term)
                stmt = (
                    select(NoteModel)
                    .where(NoteModel.content.ilike(f"%{escaped}%"))
                    .order_by(NoteModel.created_at.desc())
                    .limit(limit)
                )
            else:
                # Use FTS with plainto_tsquery
                stmt = (
                    select(NoteModel)
                    .where(NoteModel.search_vector.op("@@")(func.plainto_tsquery("english", search_term)))
                    .order_by(NoteModel.created_at.desc())
                    .limit(limit)
                )

            result = await session.execute(stmt)
            return [self._model_to_pydantic(m) for m in result.scalars().all()]

    async def clear(self) -> None:
        async with self._session_factory() as session:
            await session.execute(delete(NoteModel))
            await session.commit()

    async def list_by_user(self, user_id: str) -> list[Note]:
        return await self.list(user_id=user_id, limit=10000)

    async def delete_by_user(self, user_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(delete(NoteModel).where(NoteModel.user_id == user_id))
            await session.commit()
            return result.rowcount
