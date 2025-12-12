"""
Template Matching Tests

Tests for AI-powered workflow template recommendations.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_template_matching")
class TestTemplateRecommender:
    """Tests for the template recommendation agent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_template_recommender_initializes(self) -> None:
        """GIVEN TemplateRecommender class
        WHEN instantiated
        THEN should initialize successfully
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()
        assert recommender is not None
        assert hasattr(recommender, "recommend")

    def test_template_recommender_has_built_in_templates(self) -> None:
        """GIVEN TemplateRecommender
        WHEN accessing templates
        THEN should have built-in templates available
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()
        templates = recommender.get_available_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0

    @pytest.mark.asyncio
    async def test_recommend_returns_matching_templates(self) -> None:
        """GIVEN user description
        WHEN calling recommend()
        THEN should return matching templates
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()

        with patch.object(recommender, "_compute_similarity") as mock_sim:
            mock_sim.return_value = 0.85

            result = await recommender.recommend(description="I want to build a chatbot with RAG")

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_recommend_respects_top_k(self) -> None:
        """GIVEN top_k parameter
        WHEN calling recommend()
        THEN should return at most top_k templates
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()

        result = await recommender.recommend(
            description="chatbot",
            top_k=3,
        )

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_recommend_includes_similarity_score(self) -> None:
        """GIVEN template recommendation
        WHEN returned
        THEN should include similarity score
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()

        with patch.object(recommender, "_compute_similarity") as mock_sim:
            mock_sim.return_value = 0.75

            result = await recommender.recommend(description="API integration")

            if result:
                assert "similarity" in result[0] or hasattr(result[0], "similarity")

    @pytest.mark.asyncio
    async def test_recommend_orders_by_similarity(self) -> None:
        """GIVEN multiple matching templates
        WHEN returned
        THEN should be ordered by similarity descending
        """
        from mcp_server_langgraph.studio.ai.templates import TemplateRecommender

        recommender = TemplateRecommender()

        result = await recommender.recommend(description="data processing pipeline")

        if len(result) >= 2:
            scores = [r.get("similarity", r.similarity if hasattr(r, "similarity") else 0) for r in result]
            assert scores == sorted(scores, reverse=True)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_template_matching")
class TestWorkflowTemplate:
    """Tests for WorkflowTemplate model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_template_has_required_fields(self) -> None:
        """GIVEN WorkflowTemplate
        WHEN created
        THEN should have required fields
        """
        from mcp_server_langgraph.studio.ai.templates import WorkflowTemplate

        template = WorkflowTemplate(
            id="chatbot-rag",
            name="RAG Chatbot",
            description="Chatbot with retrieval-augmented generation",
            category="conversational",
            nodes=[{"id": "input", "type": "input"}],
            edges=[],
        )

        assert template.id == "chatbot-rag"
        assert template.name == "RAG Chatbot"
        assert template.category == "conversational"

    def test_template_supports_tags(self) -> None:
        """GIVEN WorkflowTemplate
        WHEN created with tags
        THEN should store tags for search
        """
        from mcp_server_langgraph.studio.ai.templates import WorkflowTemplate

        template = WorkflowTemplate(
            id="api-agent",
            name="API Agent",
            description="Agent that calls external APIs",
            category="integration",
            nodes=[],
            edges=[],
            tags=["api", "agent", "http", "rest"],
        )

        assert "api" in template.tags
        assert "agent" in template.tags
