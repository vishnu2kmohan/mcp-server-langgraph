"""
PostgreSQL Implementation of Plan Template Repository.

Uses SQLAlchemy AsyncSession for async database operations.
Supports pgvector for semantic similarity search.

Features:
- Full CRUD operations
- Tag-based filtering
- Orchestrator filtering
- Vector similarity search via pgvector
- Usage metrics tracking
- Full-text search with FTS

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Callable

from sqlalchemy import delete, func, select, text, update

from mcp_server_langgraph.core.models.plan_template import PlanTemplate
from mcp_server_langgraph.database.execution_plan_models import PlanTemplateModel
from mcp_server_langgraph.repositories.plan_template import PlanTemplateRepository

# Type alias for session factory
SessionFactory = Callable[[], Any]  # Returns context manager yielding AsyncSession

# CODEX REVIEW v2 FIX: Map sort fields to explicit model columns
SORT_FIELD_MAP = {
    "created_at": PlanTemplateModel.created_at,
    "updated_at": PlanTemplateModel.updated_at,
    "name": PlanTemplateModel.name,
    "use_count": PlanTemplateModel.use_count,
    "success_rate": PlanTemplateModel.success_rate,
}
ALLOWED_SORT_ORDERS = frozenset({"asc", "desc"})


class PostgresPlanTemplateRepository(PlanTemplateRepository):
    """PostgreSQL implementation of plan template repository.

    Uses async session factory for connection pooling.
    Leverages pgvector for semantic similarity search.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize with async session factory.

        Args:
            session_factory: Factory that returns async context manager for sessions.
        """
        self._session_factory = session_factory

    def _model_to_pydantic(self, model: PlanTemplateModel) -> PlanTemplate:
        """Convert SQLAlchemy model to Pydantic model."""
        return PlanTemplate(
            template_id=model.template_id,
            name=model.name,
            description=model.description,
            orchestrator=model.orchestrator,  # type: ignore[arg-type]
            thinking_budget=model.thinking_budget,  # type: ignore[arg-type]
            critique_rounds=model.critique_rounds,
            auto_approve=model.auto_approve,
            tags=model.tags or [],
            created_by=model.created_by,
            use_count=model.use_count,
            success_rate=model.success_rate,  # type: ignore[arg-type]
            last_used_at=model.last_used_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            embedding_status=model.embedding_status or "pending",  # type: ignore[arg-type]
            embedding_error=model.embedding_error,
            embedding_failed_at=model.embedding_failed_at,
        )

    def _pydantic_to_model(self, template: PlanTemplate) -> PlanTemplateModel:
        """Convert Pydantic model to SQLAlchemy model."""
        return PlanTemplateModel(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            orchestrator=template.orchestrator,
            thinking_budget=template.thinking_budget,
            critique_rounds=template.critique_rounds,
            auto_approve=template.auto_approve,
            tags=template.tags,
            created_by=template.created_by,
            use_count=template.use_count,
            success_rate=template.success_rate,
            last_used_at=template.last_used_at,
            created_at=template.created_at,
            updated_at=template.updated_at,
            embedding_status=getattr(template, "embedding_status", "pending"),
            embedding_error=getattr(template, "embedding_error", None),
            embedding_failed_at=getattr(template, "embedding_failed_at", None),
        )

    async def create(self, template: PlanTemplate) -> PlanTemplate:
        """Create a new plan template."""
        async with self._session_factory() as session:
            model = self._pydantic_to_model(template)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_pydantic(model)

    async def get(self, template_id: str) -> PlanTemplate | None:
        """Get a template by ID."""
        async with self._session_factory() as session:
            result = await session.execute(select(PlanTemplateModel).where(PlanTemplateModel.template_id == template_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def update(self, template: PlanTemplate) -> PlanTemplate:
        """Update an existing template."""
        async with self._session_factory() as session:
            values = {
                "name": template.name,
                "description": template.description,
                "orchestrator": template.orchestrator,
                "thinking_budget": template.thinking_budget,
                "critique_rounds": template.critique_rounds,
                "auto_approve": template.auto_approve,
                "tags": template.tags,
                "use_count": template.use_count,
                "success_rate": template.success_rate,
                "last_used_at": template.last_used_at,
                "updated_at": datetime.now(UTC),
                "embedding_status": getattr(template, "embedding_status", "pending"),
                "embedding_error": getattr(template, "embedding_error", None),
                "embedding_failed_at": getattr(template, "embedding_failed_at", None),
            }

            await session.execute(
                update(PlanTemplateModel).where(PlanTemplateModel.template_id == template.template_id).values(**values)
            )

            # Persist embedding via raw SQL (pgvector column not mapped in ORM)
            if template.description_embedding is not None:
                vector_str = "[" + ",".join(str(v) for v in template.description_embedding) + "]"
                await session.execute(
                    text(
                        "UPDATE plan_templates SET description_embedding = :embedding::vector WHERE template_id = :template_id"
                    ),
                    {"embedding": vector_str, "template_id": template.template_id},
                )

            await session.commit()

            result = await session.execute(
                select(PlanTemplateModel).where(PlanTemplateModel.template_id == template.template_id)
            )
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else template

    async def delete(self, template_id: str) -> bool:
        """Delete a template."""
        async with self._session_factory() as session:
            result = await session.execute(delete(PlanTemplateModel).where(PlanTemplateModel.template_id == template_id))
            await session.commit()
            return result.rowcount > 0  # type: ignore[no-any-return]

    async def list_all(self, limit: int = 100) -> list[PlanTemplate]:
        """List all templates."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PlanTemplateModel).order_by(PlanTemplateModel.created_at.desc()).limit(limit)
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def find_by_tags(self, tags: list[str]) -> list[PlanTemplate]:
        """Find templates by tags (any match)."""
        async with self._session_factory() as session:
            # Use PostgreSQL array overlap operator
            result = await session.execute(select(PlanTemplateModel).where(PlanTemplateModel.tags.overlap(tags)))
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def find_by_orchestrator(self, orchestrator: str) -> list[PlanTemplate]:
        """Find templates by orchestrator type."""
        async with self._session_factory() as session:
            result = await session.execute(select(PlanTemplateModel).where(PlanTemplateModel.orchestrator == orchestrator))
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def find_similar(
        self,
        query_embedding: list[float],
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> list[PlanTemplate]:
        """Find templates similar to the query embedding using pgvector.

        Uses cosine distance for similarity calculation.
        Requires description_embedding column to be populated.
        """
        async with self._session_factory() as session:
            # Convert min_similarity to max_distance (cosine distance = 1 - similarity)
            max_distance = 1 - min_similarity
            vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # Use pgvector cosine distance operator <=>
            result = await session.execute(
                text("""
                    SELECT template_id, name, description, orchestrator, thinking_budget,
                           critique_rounds, auto_approve, tags, created_by, use_count,
                           success_rate, last_used_at, created_at, updated_at,
                           embedding_status, embedding_error, embedding_failed_at,
                           (description_embedding <=> :embedding::vector) as distance
                    FROM plan_templates
                    WHERE description_embedding IS NOT NULL
                      AND (description_embedding <=> :embedding::vector) <= :max_distance
                    ORDER BY distance
                    LIMIT :limit
                """),
                {"embedding": vector_str, "max_distance": max_distance, "limit": limit},
            )
            rows = result.fetchall()

            # Convert rows to PlanTemplate objects
            templates = []
            for row in rows:
                templates.append(
                    PlanTemplate(
                        template_id=row.template_id,
                        name=row.name,
                        description=row.description,
                        orchestrator=row.orchestrator,
                        thinking_budget=row.thinking_budget,
                        critique_rounds=row.critique_rounds,
                        auto_approve=row.auto_approve,
                        tags=row.tags or [],
                        created_by=row.created_by,
                        use_count=row.use_count,
                        success_rate=row.success_rate,
                        last_used_at=row.last_used_at,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                        embedding_status=row.embedding_status or "pending",
                        embedding_error=row.embedding_error,
                        embedding_failed_at=row.embedding_failed_at,
                    )
                )
            return templates

    async def record_usage(self, template_id: str, success: bool) -> None:
        """Record a template usage and update metrics."""
        async with self._session_factory() as session:
            # Get current values
            result = await session.execute(select(PlanTemplateModel).where(PlanTemplateModel.template_id == template_id))
            model = result.scalar_one_or_none()
            if not model:
                return

            # Update metrics
            new_use_count = model.use_count + 1
            current_success_rate = model.success_rate or 0.0
            # Weighted average: (old_rate * old_count + new_success) / new_count
            new_success = 1.0 if success else 0.0
            new_success_rate = (current_success_rate * model.use_count + new_success) / new_use_count

            await session.execute(
                update(PlanTemplateModel)
                .where(PlanTemplateModel.template_id == template_id)
                .values(
                    use_count=new_use_count,
                    success_rate=new_success_rate,
                    last_used_at=datetime.now(UTC),
                )
            )
            await session.commit()

    async def search(
        self,
        filters: dict[str, Any],
        sort_field: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlanTemplate], int]:
        """Search templates with filtering, sorting, and pagination."""
        # CODEX REVIEW v2 FIX: Validate sort parameters
        if sort_field not in SORT_FIELD_MAP:
            raise ValueError(f"Invalid sort_field: {sort_field}. Allowed: {set(SORT_FIELD_MAP.keys())}")
        if sort_order.lower() not in ALLOWED_SORT_ORDERS:
            raise ValueError(f"Invalid sort_order: {sort_order}. Allowed: {ALLOWED_SORT_ORDERS}")

        sort_column = SORT_FIELD_MAP[sort_field]

        async with self._session_factory() as session:
            # Base query
            query = select(PlanTemplateModel)
            count_query = select(func.count()).select_from(PlanTemplateModel)

            # Apply filters
            if filters.get("query"):
                search_term = f"%{filters['query']}%"
                condition = PlanTemplateModel.name.ilike(search_term) | PlanTemplateModel.description.ilike(search_term)
                query = query.where(condition)
                count_query = count_query.where(condition)

            if filters.get("tags"):
                tag_condition = PlanTemplateModel.tags.overlap(filters["tags"])
                query = query.where(tag_condition)
                count_query = count_query.where(tag_condition)

            if filters.get("orchestrator"):
                orch_condition = PlanTemplateModel.orchestrator == filters["orchestrator"]
                query = query.where(orch_condition)
                count_query = count_query.where(orch_condition)

            # Get total count
            count_result = await session.execute(count_query)
            total_count = count_result.scalar() or 0

            # Apply sorting
            query = query.order_by(sort_column.desc()) if sort_order.lower() == "desc" else query.order_by(sort_column.asc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            models = result.scalars().all()

            return [self._model_to_pydantic(m) for m in models], total_count

    async def list_by_user(self, user_id: str) -> list[PlanTemplate]:
        """List all templates for a user (GDPR export)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PlanTemplateModel)
                .where(PlanTemplateModel.created_by == user_id)
                .order_by(PlanTemplateModel.created_at.desc())
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all templates for a user (GDPR deletion)."""
        async with self._session_factory() as session:
            result = await session.execute(delete(PlanTemplateModel).where(PlanTemplateModel.created_by == user_id))
            await session.commit()
            return result.rowcount  # type: ignore[no-any-return]

    async def list_pending_embeddings(self, limit: int = 100) -> list[PlanTemplate]:
        """List templates with pending embeddings for background processing."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PlanTemplateModel)
                .where(PlanTemplateModel.embedding_status == "pending")
                .order_by(PlanTemplateModel.created_at.asc())
                .limit(limit)
            )
            models = result.scalars().all()
            return [self._model_to_pydantic(m) for m in models]
