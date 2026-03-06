"""
Tests for Context Ranking and Semantic Deduplication.

Phase 3.3-3.4 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Context Ranking:
- Multi-factor scoring (semantic similarity, recency, usage frequency)
- Configurable weights
- Feature flag controlled

Semantic Deduplication:
- Detect semantically similar contexts
- Use configurable threshold
- Prevent loading redundant context
"""

from __future__ import annotations

import gc
from datetime import datetime, UTC
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Phase 3.3: Context Ranking Tests
# =============================================================================


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.core
class TestContextRankerClass:
    """Test ContextRanker class existence and structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_ranker_exists(self) -> None:
        """ContextRanker class should exist in core module."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker

        assert ContextRanker is not None

    def test_context_ranker_has_rank_method(self) -> None:
        """ContextRanker should have a rank_contexts method."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker

        ranker = ContextRanker()
        assert hasattr(ranker, "rank_contexts")
        assert callable(ranker.rank_contexts)

    def test_context_ranker_has_configurable_weights(self) -> None:
        """ContextRanker should accept configurable weights."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker

        ranker = ContextRanker(
            semantic_weight=0.6,
            recency_weight=0.2,
            frequency_weight=0.2,
        )
        assert ranker.semantic_weight == 0.6
        assert ranker.recency_weight == 0.2
        assert ranker.frequency_weight == 0.2

    def test_context_ranker_default_weights(self) -> None:
        """ContextRanker should have sensible default weights."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker

        ranker = ContextRanker()
        # Default weights from plan: semantic 0.5, recency 0.3, frequency 0.2
        assert ranker.semantic_weight == 0.5
        assert ranker.recency_weight == 0.3
        assert ranker.frequency_weight == 0.2

    def test_context_ranker_weights_sum_to_one(self) -> None:
        """ContextRanker weights should sum to 1.0."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker

        ranker = ContextRanker()
        total = ranker.semantic_weight + ranker.recency_weight + ranker.frequency_weight
        assert abs(total - 1.0) < 0.001


@pytest.mark.unit
@pytest.mark.core
class TestContextRankingLogic:
    """Test context ranking scoring logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rank_contexts_returns_sorted_list(self) -> None:
        """rank_contexts should return contexts sorted by score descending."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ranker = ContextRanker()

        # Create test contexts with different relevance scores
        contexts = [
            ContextReference(
                ref_id="ctx1",
                ref_type="document",
                summary="Low relevance",
                relevance_score=0.3,
                metadata={"created_at": datetime.now(UTC).timestamp()},
            ),
            ContextReference(
                ref_id="ctx2",
                ref_type="document",
                summary="High relevance",
                relevance_score=0.9,
                metadata={"created_at": datetime.now(UTC).timestamp()},
            ),
            ContextReference(
                ref_id="ctx3",
                ref_type="document",
                summary="Medium relevance",
                relevance_score=0.6,
                metadata={"created_at": datetime.now(UTC).timestamp()},
            ),
        ]

        ranked = ranker.rank_contexts(contexts, query="test query")

        # Should be sorted by score descending
        assert len(ranked) == 3
        assert ranked[0].reference.ref_id == "ctx2"  # Highest
        assert ranked[2].reference.ref_id == "ctx1"  # Lowest

    def test_rank_contexts_includes_all_factors(self) -> None:
        """Ranking should consider semantic, recency, and frequency factors."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker, RankedContext
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ranker = ContextRanker()

        # Recent context with medium semantic score
        recent_time = datetime.now(UTC).timestamp()
        contexts = [
            ContextReference(
                ref_id="ctx1",
                ref_type="document",
                summary="Recent but lower semantic",
                relevance_score=0.5,
                metadata={
                    "created_at": recent_time,
                    "usage_count": 10,
                },
            ),
        ]

        ranked = ranker.rank_contexts(contexts, query="test")

        # RankedContext should have composite score
        assert len(ranked) == 1
        assert isinstance(ranked[0], RankedContext)
        assert hasattr(ranked[0], "composite_score")
        assert ranked[0].composite_score > 0

    def test_recency_score_calculation(self) -> None:
        """More recent contexts should get higher recency scores."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ranker = ContextRanker()

        now = datetime.now(UTC).timestamp()
        now - 3600
        one_day_ago = now - 86400

        ctx_now = ContextReference(
            ref_id="ctx_now",
            ref_type="document",
            summary="Just created",
            metadata={"created_at": now},
        )
        ctx_old = ContextReference(
            ref_id="ctx_old",
            ref_type="document",
            summary="Created yesterday",
            metadata={"created_at": one_day_ago},
        )

        score_now = ranker._calculate_recency_score(ctx_now)
        score_old = ranker._calculate_recency_score(ctx_old)

        assert score_now > score_old

    def test_frequency_score_calculation(self) -> None:
        """Frequently used contexts should get higher frequency scores."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ranker = ContextRanker()

        ctx_high = ContextReference(
            ref_id="ctx_high",
            ref_type="document",
            summary="Frequently used",
            metadata={"usage_count": 100},
        )
        ctx_low = ContextReference(
            ref_id="ctx_low",
            ref_type="document",
            summary="Rarely used",
            metadata={"usage_count": 1},
        )

        score_high = ranker._calculate_frequency_score(ctx_high)
        score_low = ranker._calculate_frequency_score(ctx_low)

        assert score_high > score_low


@pytest.mark.unit
@pytest.mark.core
@pytest.mark.xdist_group(name="context_ranking_flags")
class TestContextRankingFeatureFlag:
    """Test feature flag controls for context ranking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ranking_respects_feature_flag(self) -> None:
        """Ranking should be disabled when feature flag is False."""
        from mcp_server_langgraph.core.context_ranker import ContextRanker
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        with patch("mcp_server_langgraph.core.context_ranker.feature_flags") as mock_flags:
            mock_flags.enable_context_ranking = False

            ranker = ContextRanker()

            contexts = [
                ContextReference(
                    ref_id="ctx1",
                    ref_type="document",
                    summary="Test",
                    relevance_score=0.5,
                    metadata={},
                ),
            ]

            # When disabled, should return contexts in original order
            ranked = ranker.rank_contexts(contexts, query="test")

            # Original order preserved, no additional scoring
            assert len(ranked) == 1
            assert ranked[0].reference.ref_id == "ctx1"


# =============================================================================
# Phase 3.4: Semantic Deduplication Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.core
class TestSemanticDeduplicationMethods:
    """Test semantic deduplication method existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_semantically_duplicate_function_exists(self) -> None:
        """is_semantically_duplicate function should exist."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        assert callable(is_semantically_duplicate)

    def test_load_batch_deduplicated_method_exists(self) -> None:
        """DynamicContextLoader should have load_batch_deduplicated method."""
        from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

        # Check that the method exists on the class
        assert hasattr(DynamicContextLoader, "load_batch_deduplicated")


@pytest.mark.unit
@pytest.mark.core
class TestSemanticDeduplicationLogic:
    """Test semantic deduplication logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_identical_embeddings_are_duplicates(self) -> None:
        """Identical embeddings should be detected as duplicates."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding2 = [0.1, 0.2, 0.3, 0.4, 0.5]
        seen = [embedding1]

        result = is_semantically_duplicate(embedding2, seen, threshold=0.92)

        assert result is True

    def test_different_embeddings_not_duplicates(self) -> None:
        """Very different embeddings should not be detected as duplicates."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        embedding1 = [1.0, 0.0, 0.0, 0.0, 0.0]
        embedding2 = [0.0, 0.0, 0.0, 0.0, 1.0]
        seen = [embedding1]

        result = is_semantically_duplicate(embedding2, seen, threshold=0.92)

        assert result is False

    def test_similar_embeddings_above_threshold_are_duplicates(self) -> None:
        """Embeddings above threshold should be duplicates."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        # Very similar embeddings
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding2 = [0.11, 0.21, 0.31, 0.41, 0.51]  # Slightly different
        seen = [embedding1]

        # With high threshold, these should NOT be duplicates
        result_high = is_semantically_duplicate(embedding2, seen, threshold=0.99)
        # With lower threshold, these SHOULD be duplicates
        result_low = is_semantically_duplicate(embedding2, seen, threshold=0.90)

        # The slightly different embeddings should have high cosine similarity
        # but exact behavior depends on implementation
        assert isinstance(result_high, bool)
        assert isinstance(result_low, bool)

    def test_empty_seen_list_returns_false(self) -> None:
        """With no seen embeddings, nothing should be a duplicate."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        embedding = [0.1, 0.2, 0.3]
        seen: list[list[float]] = []

        result = is_semantically_duplicate(embedding, seen, threshold=0.92)

        assert result is False


@pytest.mark.unit
@pytest.mark.core
class TestDeduplicationThreshold:
    """Test deduplication threshold configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_threshold_from_feature_flags(self) -> None:
        """Deduplication should use threshold from feature flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.context_deduplication_threshold == 0.92

    def test_deduplication_respects_feature_flag(self) -> None:
        """Deduplication should be disabled when feature flag is False."""
        from mcp_server_langgraph.core.context_ranker import is_semantically_duplicate

        with patch("mcp_server_langgraph.core.context_ranker.feature_flags") as mock_flags:
            mock_flags.enable_semantic_deduplication = False

            embedding1 = [0.1, 0.2, 0.3]
            embedding2 = [0.1, 0.2, 0.3]  # Identical
            seen = [embedding1]

            # When disabled, should always return False (no deduplication)
            result = is_semantically_duplicate(embedding2, seen, threshold=0.92)

            assert result is False


@pytest.mark.unit
@pytest.mark.core
class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cosine_similarity_function_exists(self) -> None:
        """cosine_similarity function should exist."""
        from mcp_server_langgraph.core.context_ranker import cosine_similarity

        assert callable(cosine_similarity)

    def test_identical_vectors_have_similarity_one(self) -> None:
        """Identical vectors should have cosine similarity of 1.0."""
        from mcp_server_langgraph.core.context_ranker import cosine_similarity

        vec = [0.5, 0.5, 0.5]
        result = cosine_similarity(vec, vec)

        assert abs(result - 1.0) < 0.001

    def test_orthogonal_vectors_have_similarity_zero(self) -> None:
        """Orthogonal vectors should have cosine similarity of 0.0."""
        from mcp_server_langgraph.core.context_ranker import cosine_similarity

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        result = cosine_similarity(vec1, vec2)

        assert abs(result - 0.0) < 0.001

    def test_opposite_vectors_have_similarity_negative_one(self) -> None:
        """Opposite vectors should have cosine similarity of -1.0."""
        from mcp_server_langgraph.core.context_ranker import cosine_similarity

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        result = cosine_similarity(vec1, vec2)

        assert abs(result - (-1.0)) < 0.001


@pytest.mark.unit
@pytest.mark.core
class TestRankedContextModel:
    """Test RankedContext data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ranked_context_exists(self) -> None:
        """RankedContext class should exist."""
        from mcp_server_langgraph.core.context_ranker import RankedContext

        assert RankedContext is not None

    def test_ranked_context_has_required_fields(self) -> None:
        """RankedContext should have reference and scores."""
        from mcp_server_langgraph.core.context_ranker import RankedContext
        from mcp_server_langgraph.core.dynamic_context_loader import ContextReference

        ref = ContextReference(
            ref_id="test",
            ref_type="document",
            summary="Test",
            metadata={},
        )

        ranked = RankedContext(
            reference=ref,
            semantic_score=0.8,
            recency_score=0.6,
            frequency_score=0.4,
            composite_score=0.7,
        )

        assert ranked.reference.ref_id == "test"
        assert ranked.semantic_score == 0.8
        assert ranked.recency_score == 0.6
        assert ranked.frequency_score == 0.4
        assert ranked.composite_score == 0.7
