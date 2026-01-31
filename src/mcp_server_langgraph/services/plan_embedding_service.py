"""
Plan Embedding Service.

Background task service for generating embeddings for execution plans
and plan templates.

Features:
- Async embedding generation
- Failure tracking with retry logic
- Support for both execution plans and templates
- Uses EmbeddingService for multi-provider support

Phase 7: Embedding Generation (Background Task)
Phase 7.25: Template Embedding Service (Self-Healing)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from mcp_server_langgraph.core.constants import assert_embedding_dimension

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
    from mcp_server_langgraph.core.models.plan_template import PlanTemplate
    from mcp_server_langgraph.repositories.execution_plan import ExecutionPlanRepository
    from mcp_server_langgraph.repositories.plan_template import PlanTemplateRepository

logger = logging.getLogger(__name__)


class PlanEmbeddingService:
    """Background service for generating plan embeddings.

    Generates embeddings for execution plans and templates asynchronously.
    Tracks failures for self-healing and retry logic.
    """

    def __init__(
        self,
        execution_plan_repo: ExecutionPlanRepository | None = None,
        plan_template_repo: PlanTemplateRepository | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> None:
        """Initialize embedding service.

        Args:
            execution_plan_repo: Repository for execution plans.
            plan_template_repo: Repository for plan templates.
            max_retries: Maximum retry attempts for failed embeddings.
            retry_delay: Delay between retries in seconds.
        """
        self._execution_plan_repo = execution_plan_repo
        self._plan_template_repo = plan_template_repo
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._running = False
        self._task: asyncio.Task | None = None

    async def _get_embedding_service(self):
        """Get the embedding service instance."""
        from mcp_server_langgraph.llm.embeddings import get_embedding_service

        service = await get_embedding_service()
        return service

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.

        Raises:
            ValueError: If embedding dimension doesn't match expected.
        """
        service = await self._get_embedding_service()
        embedding = await service.embed(text)

        # Validate embedding dimension
        assert_embedding_dimension(len(embedding), "PlanEmbeddingService.generate_embedding")

        return embedding

    async def embed_execution_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Generate embedding for an execution plan.

        Updates the plan's embedding status and persists to database.

        Args:
            plan: The execution plan to embed.

        Returns:
            Updated plan with embedding.
        """
        if self._execution_plan_repo is None:
            raise RuntimeError("Execution plan repository not configured")

        # Mark as processing
        plan = plan.model_copy(update={"embedding_status": "processing"})
        await self._execution_plan_repo.update(plan)

        try:
            # Generate embedding from message text
            embedding = await self.generate_embedding(plan.message)

            # Update plan with embedding
            plan = plan.model_copy(
                update={
                    "description_embedding": embedding,
                    "embedding_status": "completed",
                    "embedding_error": None,
                    "embedding_failed_at": None,
                }
            )
            await self._execution_plan_repo.update(plan)
            logger.debug(f"Generated embedding for plan {plan.plan_id}")
            return plan

        except Exception as e:
            # Mark as failed
            plan = plan.model_copy(
                update={
                    "embedding_status": "failed",
                    "embedding_error": str(e)[:255],
                    "embedding_failed_at": datetime.now(UTC),
                }
            )
            await self._execution_plan_repo.update(plan)
            logger.warning(f"Failed to generate embedding for plan {plan.plan_id}: {e}")
            raise

    async def embed_plan_template(self, template: PlanTemplate) -> PlanTemplate:
        """Generate embedding for a plan template.

        Updates the template's embedding status and persists to database.

        Args:
            template: The plan template to embed.

        Returns:
            Updated template with embedding.
        """
        if self._plan_template_repo is None:
            raise RuntimeError("Plan template repository not configured")

        # Mark as processing
        template = template.model_copy(update={"embedding_status": "processing"})
        await self._plan_template_repo.update(template)

        try:
            # Generate embedding from name + description
            text = f"{template.name}: {template.description}"
            embedding = await self.generate_embedding(text)

            # Update template with embedding
            template = template.model_copy(
                update={
                    "description_embedding": embedding,
                    "embedding_status": "completed",
                    "embedding_error": None,
                    "embedding_failed_at": None,
                }
            )
            await self._plan_template_repo.update(template)
            logger.debug(f"Generated embedding for template {template.template_id}")
            return template

        except Exception as e:
            # Mark as failed
            template = template.model_copy(
                update={
                    "embedding_status": "failed",
                    "embedding_error": str(e)[:255],
                    "embedding_failed_at": datetime.now(UTC),
                }
            )
            await self._plan_template_repo.update(template)
            logger.warning(f"Failed to generate embedding for template {template.template_id}: {e}")
            raise

    async def process_pending_embeddings(self, batch_size: int = 10) -> int:
        """Process pending embeddings for both plans and templates.

        Finds items with pending embedding status and generates embeddings.

        Args:
            batch_size: Maximum items to process per batch.

        Returns:
            Number of items processed.
        """
        processed = 0

        # Process pending execution plans
        if self._execution_plan_repo is not None:
            try:
                pending_plans = await self._execution_plan_repo.list_pending_embeddings(limit=batch_size)
                for plan in pending_plans:
                    try:
                        await self.embed_execution_plan(plan)
                        processed += 1
                    except Exception as e:
                        logger.warning(f"Embedding failed for plan {plan.plan_id}: {e}")
            except Exception:
                logger.exception("Failed to fetch pending execution plans")

        # Process pending templates
        if self._plan_template_repo is not None:
            try:
                pending_templates = await self._plan_template_repo.list_pending_embeddings(limit=batch_size)
                for template in pending_templates:
                    try:
                        await self.embed_plan_template(template)
                        processed += 1
                    except Exception as e:
                        logger.warning(f"Embedding failed for template {template.template_id}: {e}")
            except Exception:
                logger.exception("Failed to fetch pending plan templates")

        return processed

    async def start_background_processing(self, interval: float = 30.0) -> None:
        """Start background embedding processing loop.

        Periodically processes pending embeddings.

        Args:
            interval: Processing interval in seconds.
        """
        self._running = True
        logger.info(f"Starting embedding background processor (interval: {interval}s)")

        while self._running:
            try:
                processed = await self.process_pending_embeddings()
                if processed > 0:
                    logger.info(f"Processed {processed} pending embeddings")
            except Exception:
                logger.exception("Embedding background processor error")

            await asyncio.sleep(interval)

    def stop_background_processing(self) -> None:
        """Stop the background processing loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None
        logger.info("Stopping embedding background processor")


# Module-level singleton for background service
_embedding_service: PlanEmbeddingService | None = None


def get_embedding_service_instance() -> PlanEmbeddingService | None:
    """Get the module-level embedding service instance."""
    return _embedding_service


def set_embedding_service_instance(service: PlanEmbeddingService | None) -> None:
    """Set the module-level embedding service instance."""
    global _embedding_service
    _embedding_service = service


async def schedule_plan_embedding(plan: ExecutionPlan) -> None:
    """Schedule embedding generation for a plan.

    Non-blocking: spawns a background task.

    Args:
        plan: The plan to embed.
    """
    service = get_embedding_service_instance()
    if service is None:
        logger.debug("Embedding service not configured, skipping plan embedding")
        return

    # Spawn background task (fire-and-forget)
    asyncio.create_task(  # noqa: RUF006
        _embed_with_retry(service, "plan", plan),
        name=f"embed_plan_{plan.plan_id}",
    )


async def schedule_template_embedding(template: PlanTemplate) -> None:
    """Schedule embedding generation for a template.

    Non-blocking: spawns a background task.

    Args:
        template: The template to embed.
    """
    service = get_embedding_service_instance()
    if service is None:
        logger.debug("Embedding service not configured, skipping template embedding")
        return

    # Spawn background task (fire-and-forget)
    asyncio.create_task(  # noqa: RUF006
        _embed_with_retry(service, "template", template),
        name=f"embed_template_{template.template_id}",
    )


async def _embed_with_retry(
    service: PlanEmbeddingService,
    item_type: str,
    item: ExecutionPlan | PlanTemplate,
) -> None:
    """Embed an item with retry logic.

    Args:
        service: The embedding service.
        item_type: "plan" or "template".
        item: The item to embed.
    """
    for attempt in range(service._max_retries):
        try:
            if item_type == "plan":
                await service.embed_execution_plan(item)
            else:
                await service.embed_plan_template(item)
            return
        except Exception as e:
            if attempt < service._max_retries - 1:
                logger.warning(f"Embedding retry {attempt + 1}/{service._max_retries} for {item_type}: {e}")
                await asyncio.sleep(service._retry_delay * (attempt + 1))
            else:
                logger.exception(f"Embedding failed after {service._max_retries} attempts")
