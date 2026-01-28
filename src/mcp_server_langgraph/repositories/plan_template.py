"""
Plan Template Repository

Repository abstraction for storing and retrieving reusable plan templates.
Supports semantic search using vector embeddings for template matching.

Usage:
    from mcp_server_langgraph.repositories.plan_template import (
        InMemoryPlanTemplateRepository,
    )

    repo = InMemoryPlanTemplateRepository()
    template = await repo.create(plan_template)
    similar = await repo.find_similar(embedding, min_similarity=0.8)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.plan_template import PlanTemplate


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


class PlanTemplateRepository(ABC):
    """Abstract base class for plan template repositories.

    Defines the interface for storing and retrieving plan templates,
    including semantic search capabilities.
    """

    @abstractmethod
    async def create(self, template: PlanTemplate) -> PlanTemplate:
        """Create a new plan template.

        Args:
            template: The template to create

        Returns:
            The created template
        """
        ...

    @abstractmethod
    async def get(self, template_id: str) -> PlanTemplate | None:
        """Get a template by ID.

        Args:
            template_id: The template ID

        Returns:
            The template if found, None otherwise
        """
        ...

    @abstractmethod
    async def update(self, template: PlanTemplate) -> PlanTemplate:
        """Update an existing template.

        Args:
            template: The template with updated values

        Returns:
            The updated template
        """
        ...

    @abstractmethod
    async def delete(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: The template ID to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100) -> list[PlanTemplate]:
        """List all templates.

        Args:
            limit: Maximum number of templates to return

        Returns:
            List of templates
        """
        ...

    @abstractmethod
    async def find_by_tags(self, tags: list[str]) -> list[PlanTemplate]:
        """Find templates by tags.

        Args:
            tags: Tags to search for (any match)

        Returns:
            List of matching templates
        """
        ...

    @abstractmethod
    async def find_by_orchestrator(self, orchestrator: str) -> list[PlanTemplate]:
        """Find templates by orchestrator type.

        Args:
            orchestrator: Orchestrator type to filter by

        Returns:
            List of matching templates
        """
        ...

    @abstractmethod
    async def find_similar(
        self,
        query_embedding: list[float],
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> list[PlanTemplate]:
        """Find templates similar to the query embedding.

        Args:
            query_embedding: The embedding vector to search with
            min_similarity: Minimum cosine similarity threshold (0-1)
            limit: Maximum number of results

        Returns:
            List of similar templates sorted by similarity
        """
        ...

    @abstractmethod
    async def record_usage(self, template_id: str, success: bool) -> None:
        """Record a template usage and update metrics.

        Args:
            template_id: The template that was used
            success: Whether the usage was successful
        """
        ...

    @abstractmethod
    async def search(
        self,
        filters: dict[str, Any],
        sort_field: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlanTemplate], int]:
        """Search templates with filtering, sorting, and pagination.

        Args:
            filters: Dict with optional keys:
                - query: Text search in name/description (substring match)
                - tags: List of tags to filter by (any match)
                - orchestrator: Orchestrator type to filter by
            sort_field: Field to sort by (use_count, success_rate, created_at)
            sort_order: Sort direction (asc, desc)
            limit: Max results per page
            offset: Skip first N results

        Returns:
            Tuple of (matching templates, total count before pagination)
        """
        ...


class InMemoryPlanTemplateRepository(PlanTemplateRepository):
    """In-memory implementation of PlanTemplateRepository.

    Suitable for testing and development. Uses simple cosine similarity
    for semantic search without external vector database.
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        self._templates: dict[str, PlanTemplate] = {}

    async def create(self, template: PlanTemplate) -> PlanTemplate:
        """Create a new plan template."""
        self._templates[template.template_id] = template
        return template

    async def get(self, template_id: str) -> PlanTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    async def update(self, template: PlanTemplate) -> PlanTemplate:
        """Update an existing template."""
        self._templates[template.template_id] = template
        return template

    async def delete(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    async def list_all(self, limit: int = 100) -> list[PlanTemplate]:
        """List all templates."""
        templates = list(self._templates.values())
        return templates[:limit]

    async def find_by_tags(self, tags: list[str]) -> list[PlanTemplate]:
        """Find templates by tags."""
        tag_set = set(tags)
        return [t for t in self._templates.values() if tag_set.intersection(set(t.tags))]

    async def find_by_orchestrator(self, orchestrator: str) -> list[PlanTemplate]:
        """Find templates by orchestrator type."""
        return [t for t in self._templates.values() if t.orchestrator == orchestrator]

    async def find_similar(
        self,
        query_embedding: list[float],
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> list[PlanTemplate]:
        """Find templates similar to the query embedding."""
        results: list[tuple[float, PlanTemplate]] = []

        for template in self._templates.values():
            if template.description_embedding is None:
                continue

            similarity = _cosine_similarity(query_embedding, template.description_embedding)
            if similarity >= min_similarity:
                results.append((similarity, template))

        # Sort by similarity descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [t for _, t in results[:limit]]

    async def record_usage(self, template_id: str, success: bool) -> None:
        """Record a template usage and update metrics."""
        template = self._templates.get(template_id)
        if template is None:
            return

        updated = template.record_use(success)
        self._templates[template_id] = updated

    async def search(
        self,
        filters: dict[str, Any],
        sort_field: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlanTemplate], int]:
        """Search templates with filtering, sorting, and pagination."""
        results = list(self._templates.values())

        # Apply filters
        if "tags" in filters:
            tag_set = set(filters["tags"])
            results = [t for t in results if tag_set & set(t.tags)]

        if "orchestrator" in filters:
            results = [t for t in results if t.orchestrator == filters["orchestrator"]]

        if "query" in filters:
            query_lower = filters["query"].lower()
            results = [t for t in results if query_lower in t.name.lower() or query_lower in t.description.lower()]

        # Get total before pagination
        total = len(results)

        # Sort
        reverse = sort_order == "desc"
        if sort_field == "use_count":
            results.sort(key=lambda t: t.use_count, reverse=reverse)
        elif sort_field == "success_rate":
            results.sort(key=lambda t: t.success_rate, reverse=reverse)
        else:  # created_at (default)
            results.sort(key=lambda t: t.created_at, reverse=reverse)

        # Paginate
        results = results[offset : offset + limit]

        return results, total
