"""
Workflow Suggestions Tests

Tests for AI-powered workflow suggestions using LangGraph.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_workflow_suggestions")
class TestWorkflowSuggestionAgent:
    """Tests for the workflow suggestion agent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_suggestion_agent_initializes(self) -> None:
        """GIVEN WorkflowSuggestionAgent class
        WHEN instantiated
        THEN should initialize with default configuration
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()
        assert agent is not None
        assert hasattr(agent, "suggest")

    def test_suggestion_agent_accepts_llm_config(self) -> None:
        """GIVEN WorkflowSuggestionAgent
        WHEN instantiated with LLM config
        THEN should use provided configuration
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent(
            model_name="gpt-4",
            temperature=0.5,
        )
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.5

    @pytest.mark.asyncio
    async def test_suggest_returns_suggestions_for_workflow(self) -> None:
        """GIVEN a workflow context
        WHEN calling suggest()
        THEN should return list of suggestions
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()

        with patch.object(agent, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "suggestions": [
                    {
                        "type": "add_node",
                        "description": "Add error handling node",
                        "confidence": 0.85,
                    }
                ]
            }

            result = await agent.suggest(
                workflow={
                    "nodes": [{"id": "start", "type": "input"}],
                    "edges": [],
                }
            )

            assert isinstance(result, list)
            assert len(result) >= 1
            assert result[0]["type"] == "add_node"

    @pytest.mark.asyncio
    async def test_suggest_respects_max_suggestions(self) -> None:
        """GIVEN max_suggestions parameter
        WHEN calling suggest()
        THEN should return at most max_suggestions items
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()

        with patch.object(agent, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "suggestions": [
                    {"type": "add_node", "description": "Add node 1", "confidence": 0.9},
                    {"type": "add_node", "description": "Add node 2", "confidence": 0.8},
                    {"type": "add_node", "description": "Add node 3", "confidence": 0.7},
                ]
            }

            result = await agent.suggest(
                workflow={"nodes": [], "edges": []},
                max_suggestions=2,
            )

            assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_suggest_filters_by_confidence_threshold(self) -> None:
        """GIVEN confidence_threshold parameter
        WHEN calling suggest()
        THEN should only return suggestions above threshold
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()

        with patch.object(agent, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "suggestions": [
                    {"type": "add_node", "description": "High", "confidence": 0.9},
                    {"type": "add_node", "description": "Low", "confidence": 0.3},
                ]
            }

            result = await agent.suggest(
                workflow={"nodes": [], "edges": []},
                confidence_threshold=0.5,
            )

            assert all(s["confidence"] >= 0.5 for s in result)

    @pytest.mark.asyncio
    async def test_suggest_handles_empty_workflow(self) -> None:
        """GIVEN empty workflow
        WHEN calling suggest()
        THEN should return starter suggestions
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()

        with patch.object(agent, "_invoke_llm") as mock_llm:
            mock_llm.return_value = {
                "suggestions": [
                    {
                        "type": "add_node",
                        "description": "Add an input node to start",
                        "confidence": 0.95,
                    }
                ]
            }

            result = await agent.suggest(workflow={"nodes": [], "edges": []})

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_suggest_tracks_metrics(self) -> None:
        """GIVEN workflow suggestion request
        WHEN calling suggest()
        THEN should track HEART metrics
        """
        from mcp_server_langgraph.studio.ai.suggestions import WorkflowSuggestionAgent

        agent = WorkflowSuggestionAgent()

        with (
            patch.object(agent, "_invoke_llm") as mock_llm,
            patch.object(agent, "_track_suggestion_event") as mock_track,
        ):
            mock_llm.return_value = {"suggestions": []}

            await agent.suggest(workflow={"nodes": [], "edges": []})

            mock_track.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_workflow_suggestions")
class TestSuggestionTypes:
    """Tests for different suggestion types."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_suggestion_has_required_fields(self) -> None:
        """GIVEN a Suggestion
        WHEN created
        THEN should have required fields
        """
        from mcp_server_langgraph.studio.ai.suggestions import Suggestion

        suggestion = Suggestion(
            type="add_node",
            description="Add a processing node",
            confidence=0.8,
        )

        assert suggestion.type == "add_node"
        assert suggestion.description == "Add a processing node"
        assert suggestion.confidence == 0.8

    def test_suggestion_supports_optional_metadata(self) -> None:
        """GIVEN a Suggestion
        WHEN created with metadata
        THEN should store metadata
        """
        from mcp_server_langgraph.studio.ai.suggestions import Suggestion

        suggestion = Suggestion(
            type="add_node",
            description="Add a processing node",
            confidence=0.8,
            metadata={"node_type": "llm", "position": {"x": 100, "y": 200}},
        )

        assert suggestion.metadata["node_type"] == "llm"
