"""
Semantic Prompt Search

Provides semantic search over registered prompts using embeddings.
Enables finding relevant prompts based on natural language queries.

Features:
- Semantic similarity search using embeddings
- Category-based filtering
- Keyword fallback when embeddings unavailable
- Feature flag integration (ff_enable_plan_search)

Usage:
    from mcp_server_langgraph.core.prompts.search import PromptIndex, search_prompts

    index = PromptIndex(embedding_service=get_embedding_service())
    await index.build()

    results = await search_prompts("error handling", index=index, top_k=5)

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 6: Plan Editor Prompts
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PromptSearchResult:
    """Result from semantic prompt search.

    Attributes:
        prompt_name: Internal name of the prompt (e.g., "error_analysis")
        similarity: Cosine similarity score (0.0 to 1.0)
        category: Category of the prompt (e.g., "ai_ux", "core", "genui")
        version: Version of the prompt (e.g., "v1", "latest")
        content_preview: Optional preview of prompt content (first N chars)
    """

    prompt_name: str
    similarity: float
    category: str | None = None
    version: str = "v1"
    content_preview: str | None = None


@dataclass
class _PromptEntry:
    """Internal representation of an indexed prompt."""

    name: str
    category: str
    content: str
    embedding: list[float] = field(default_factory=list)


# =============================================================================
# PROMPT METADATA
# =============================================================================

# Map prompt names to categories
PROMPT_CATEGORIES: dict[str, str] = {
    # Core prompts
    "router": "core",
    "response": "core",
    "verification": "core",
    "orchestration_router": "core",
    "studio": "core",
    # GenUI prompts
    "genui_widget": "genui",
    "genui_render": "genui",
    "genui_form": "genui",
    # Workflow prompts
    "workflow_generator": "workflow",
    # Plan editor prompts
    "plan_validation": "plan",
    "template_suggestion": "plan",
    # AI UX prompts
    "error_analysis": "ai_ux",
    "empty_state": "ai_ux",
    "persona_analysis": "ai_ux",
    "disclosure_analysis": "ai_ux",
    "nudge_recommendation": "ai_ux",
    "onboarding_personalization": "ai_ux",
    "metrics_insights": "ai_ux",
    "session_summarize": "ai_ux",
    "session_group": "ai_ux",
    "session_similarity": "ai_ux",
    "trace_summarize": "ai_ux",
    "trace_anomalies": "ai_ux",
    "canvas_artifact_type": "ai_ux",
    "canvas_code_analysis": "ai_ux",
    "canvas_diff_explain": "ai_ux",
    "diagram_analyze": "ai_ux",
    "diagram_to_code": "ai_ux",
}


# =============================================================================
# PROMPT INDEX
# =============================================================================


class PromptIndex:
    """Index for semantic prompt search.

    Builds and maintains an embedding index over registered prompts.
    Supports semantic similarity search and keyword fallback.

    Attributes:
        embedding_service: Service for generating embeddings
        is_built: Whether the index has been built
        prompt_count: Number of prompts in the index
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        """Initialize prompt index.

        Args:
            embedding_service: Service for generating text embeddings
        """
        self._embedding_service = embedding_service
        self._entries: list[_PromptEntry] = []
        self._is_built = False

    @property
    def is_built(self) -> bool:
        """Whether the index has been built."""
        return self._is_built

    @property
    def prompt_count(self) -> int:
        """Number of prompts in the index."""
        return len(self._entries)

    async def build(self) -> None:
        """Build the prompt index by embedding all registered prompts.

        Fetches all prompts from the registry, generates embeddings,
        and stores them for later similarity search.
        """
        from mcp_server_langgraph.core.prompts import (
            _PROMPT_VERSIONS,
            get_prompt,
        )

        self._entries = []

        # Collect prompts to embed
        prompts_to_embed: list[tuple[str, str, str]] = []  # (name, category, content)

        for prompt_name in _PROMPT_VERSIONS:
            try:
                content = get_prompt(prompt_name)
                category = PROMPT_CATEGORIES.get(prompt_name, "other")
                prompts_to_embed.append((prompt_name, category, content))
            except ValueError:
                logger.warning(f"Failed to get prompt: {prompt_name}")
                continue

        if not prompts_to_embed:
            self._is_built = True
            return

        # Generate embeddings in batch
        try:
            contents = [p[2] for p in prompts_to_embed]
            # Truncate long prompts for embedding (most embedding models have limits)
            truncated_contents = [c[:8000] for c in contents]
            embeddings = await self._embedding_service.embed_batch(truncated_contents)

            # Create entries
            for (name, category, content), embedding in zip(prompts_to_embed, embeddings, strict=False):
                self._entries.append(
                    _PromptEntry(
                        name=name,
                        category=category,
                        content=content,
                        embedding=embedding,
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to generate embeddings during build: {e}")
            # Create entries without embeddings (for keyword fallback)
            for name, category, content in prompts_to_embed:
                self._entries.append(
                    _PromptEntry(
                        name=name,
                        category=category,
                        content=content,
                        embedding=[],
                    )
                )

        self._is_built = True
        logger.info(f"Prompt index built with {len(self._entries)} prompts")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[PromptSearchResult]:
        """Search for prompts similar to the query.

        Args:
            query: Natural language search query
            top_k: Maximum number of results to return
            category: Optional category filter

        Returns:
            List of PromptSearchResult ordered by similarity (descending)
        """
        if not self._is_built:
            await self.build()

        # Generate query embedding
        try:
            query_embedding = await self._embedding_service.embed(query)
        except Exception as e:
            logger.warning(f"Failed to embed query, falling back to keyword: {e}")
            return self._keyword_search(query, top_k, category)

        # Filter by category if specified
        entries = self._entries
        if category:
            entries = [e for e in entries if e.category == category]

        # Calculate similarities
        results: list[tuple[float, _PromptEntry]] = []

        for entry in entries:
            if not entry.embedding:
                # No embedding available, skip
                continue

            similarity = self._cosine_similarity(query_embedding, entry.embedding)
            results.append((similarity, entry))

        # Sort by similarity (descending) and take top_k
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:top_k]

        return [
            PromptSearchResult(
                prompt_name=entry.name,
                similarity=sim,
                category=entry.category,
                version="v1",
                content_preview=entry.content[:200] if entry.content else None,
            )
            for sim, entry in results
        ]

    def _keyword_search(
        self,
        query: str,
        top_k: int,
        category: str | None,
    ) -> list[PromptSearchResult]:
        """Fallback keyword-based search.

        Args:
            query: Search query
            top_k: Maximum results
            category: Optional category filter

        Returns:
            Results based on keyword matching
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        entries = self._entries
        if category:
            entries = [e for e in entries if e.category == category]

        results: list[tuple[float, _PromptEntry]] = []

        for entry in entries:
            # Simple keyword matching score
            name_lower = entry.name.lower().replace("_", " ")
            content_lower = entry.content.lower()[:1000] if entry.content else ""

            # Score based on word matches
            score = 0.0
            for word in query_words:
                if word in name_lower:
                    score += 0.5  # Name match is weighted higher
                if word in content_lower:
                    score += 0.2

            if score > 0:
                # Normalize score to 0-1 range
                normalized_score = min(score / len(query_words), 1.0)
                results.append((normalized_score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:top_k]

        return [
            PromptSearchResult(
                prompt_name=entry.name,
                similarity=sim,
                category=entry.category,
                version="v1",
                content_preview=entry.content[:200] if entry.content else None,
            )
            for sim, entry in results
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        if len(a) != len(b) or not a:
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        similarity = dot_product / (magnitude_a * magnitude_b)
        # Clamp to 0-1 range (may exceed due to floating point)
        return max(0.0, min(1.0, similarity))


# =============================================================================
# PUBLIC API
# =============================================================================


async def search_prompts(
    query: str,
    *,
    index: PromptIndex,
    top_k: int = 5,
    category: str | None = None,
    respect_feature_flags: bool = False,
    allow_fallback: bool = True,
) -> list[PromptSearchResult]:
    """Search for prompts by semantic similarity.

    Args:
        query: Natural language search query
        index: PromptIndex instance to search
        top_k: Maximum number of results (default: 5)
        category: Optional category filter (e.g., "ai_ux", "core")
        respect_feature_flags: If True, returns empty when ff_enable_plan_search is False
        allow_fallback: If True, falls back to keyword search on embedding errors

    Returns:
        List of PromptSearchResult ordered by similarity (descending)

    Examples:
        >>> index = PromptIndex(embedding_service=get_embedding_service())
        >>> await index.build()
        >>> results = await search_prompts("error handling", index=index)
        >>> for r in results:
        ...     print(f"{r.prompt_name}: {r.similarity:.2f}")
    """
    # Check feature flag
    if respect_feature_flags:
        from mcp_server_langgraph.core.feature_flags import feature_flags

        if not feature_flags.enable_plan_search:
            return []

    # Ensure index is built
    if not index.is_built:
        await index.build()

    try:
        return await index.search(query, top_k=top_k, category=category)
    except Exception as e:
        logger.warning(f"Semantic search failed: {e}")
        if allow_fallback:
            return index._keyword_search(query, top_k, category)
        return []


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PromptIndex",
    "PromptSearchResult",
    "search_prompts",
]
