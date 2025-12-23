"""
Context Ranking and Semantic Deduplication.

Phase 3.3-3.4 of the Multi-Agent Orchestrator Enhancement Plan.

Provides multi-factor context ranking and semantic deduplication to:
- Prioritize relevant context based on semantic similarity, recency, and usage
- Remove semantically duplicate contexts to reduce redundancy
- Optimize context window usage

Usage:
    from mcp_server_langgraph.core.context_ranker import ContextRanker, is_semantically_duplicate

    ranker = ContextRanker()
    ranked_contexts = ranker.rank_contexts(contexts, query="user question")

    # Check for duplicates
    if is_semantically_duplicate(embedding, seen_embeddings, threshold=0.92):
        skip_this_context()
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import TYPE_CHECKING


from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    from mcp_server_langgraph.core.dynamic_context_loader import ContextReference


# Time constants for recency scoring
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
RECENCY_DECAY_DAYS = 7  # Half-life for recency decay


@dataclass
class RankedContext:
    """Context reference with multi-factor ranking scores."""

    reference: ContextReference
    semantic_score: float
    recency_score: float
    frequency_score: float
    composite_score: float


class ContextRanker:
    """
    Multi-factor context ranking for optimal context window usage.

    Ranks contexts based on:
    - Semantic similarity (from relevance_score)
    - Recency (how recently the context was created/used)
    - Usage frequency (how often the context has been accessed)

    Default weights (from Anthropic best practices):
    - Semantic: 0.5 (primary factor for relevance)
    - Recency: 0.3 (recent context often more relevant)
    - Frequency: 0.2 (frequently used context tends to be important)
    """

    def __init__(
        self,
        semantic_weight: float = 0.5,
        recency_weight: float = 0.3,
        frequency_weight: float = 0.2,
    ) -> None:
        """
        Initialize context ranker with configurable weights.

        Args:
            semantic_weight: Weight for semantic similarity score (default 0.5)
            recency_weight: Weight for recency score (default 0.3)
            frequency_weight: Weight for usage frequency score (default 0.2)
        """
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight

    def rank_contexts(
        self,
        contexts: list[ContextReference],
        query: str = "",
    ) -> list[RankedContext]:
        """
        Rank contexts by composite score combining multiple factors.

        When feature flag is disabled, returns contexts wrapped in RankedContext
        with only semantic scores (original order preserved based on relevance_score).

        Args:
            contexts: List of context references to rank
            query: Optional query for semantic matching (not used directly,
                   relies on relevance_score from semantic search)

        Returns:
            List of RankedContext sorted by composite_score descending
        """
        if not feature_flags.enable_context_ranking:
            # Disabled: wrap and return in original order
            return [
                RankedContext(
                    reference=ctx,
                    semantic_score=ctx.relevance_score or 0.0,
                    recency_score=0.0,
                    frequency_score=0.0,
                    composite_score=ctx.relevance_score or 0.0,
                )
                for ctx in contexts
            ]

        ranked = []
        for ctx in contexts:
            semantic = ctx.relevance_score or 0.0
            recency = self._calculate_recency_score(ctx)
            frequency = self._calculate_frequency_score(ctx)

            composite = self.semantic_weight * semantic + self.recency_weight * recency + self.frequency_weight * frequency

            ranked.append(
                RankedContext(
                    reference=ctx,
                    semantic_score=semantic,
                    recency_score=recency,
                    frequency_score=frequency,
                    composite_score=composite,
                )
            )

        # Sort by composite score descending
        ranked.sort(key=lambda r: r.composite_score, reverse=True)
        return ranked

    def _calculate_recency_score(self, ctx: ContextReference) -> float:
        """
        Calculate recency score based on context age.

        Uses exponential decay with half-life of RECENCY_DECAY_DAYS.
        Score ranges from 0.0 (very old) to 1.0 (just created).

        Args:
            ctx: Context reference with created_at in metadata

        Returns:
            Recency score between 0.0 and 1.0
        """
        created_at = ctx.metadata.get("created_at")
        if created_at is None:
            return 0.5  # Default for contexts without timestamp

        now = datetime.now(UTC).timestamp()
        age_seconds = max(0, now - created_at)
        age_days = age_seconds / SECONDS_PER_DAY

        # Exponential decay: score = 0.5^(age/half_life)
        # At age=0: score=1.0, at age=half_life: score=0.5
        score = math.pow(0.5, age_days / RECENCY_DECAY_DAYS)
        return min(1.0, max(0.0, score))

    def _calculate_frequency_score(self, ctx: ContextReference) -> float:
        """
        Calculate frequency score based on usage count.

        Uses logarithmic scaling to handle widely varying counts.
        Score ranges from 0.0 (unused) to 1.0 (heavily used).

        Args:
            ctx: Context reference with usage_count in metadata

        Returns:
            Frequency score between 0.0 and 1.0
        """
        usage_count = ctx.metadata.get("usage_count", 0)
        if usage_count <= 0:
            return 0.0

        # Logarithmic scaling: log10(count+1) / log10(101)
        # At count=0: score=0, at count=100: score~=1.0
        max_log = math.log10(101)  # Normalize to ~1.0 at 100 uses
        score = math.log10(usage_count + 1) / max_log
        return min(1.0, max(0.0, score))


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity between -1.0 and 1.0
    """
    if len(vec1) != len(vec2):
        msg = f"Vector lengths must match: {len(vec1)} != {len(vec2)}"
        raise ValueError(msg)

    # Dot product
    dot = sum(a * b for a, b in zip(vec1, vec2))

    # Magnitudes
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def is_semantically_duplicate(
    embedding: list[float],
    seen_embeddings: list[list[float]],
    threshold: float = 0.92,
) -> bool:
    """
    Check if an embedding is semantically duplicate of any seen embedding.

    Uses cosine similarity to compare embeddings against a threshold.

    Args:
        embedding: The embedding to check
        seen_embeddings: List of previously seen embeddings
        threshold: Similarity threshold (default 0.92 from feature flags)

    Returns:
        True if embedding is a duplicate (similarity >= threshold), False otherwise
    """
    if not feature_flags.enable_semantic_deduplication:
        return False

    if not seen_embeddings:
        return False

    for seen in seen_embeddings:
        similarity = cosine_similarity(embedding, seen)
        if similarity >= threshold:
            return True

    return False
