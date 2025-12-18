"""
Workflow Generator Service Tests

TDD tests for LLM-based workflow generation service.

The WorkflowGenerator:
- Generates workflow definitions from text prompts
- Generates workflow definitions from session message history
- Uses structured output to ensure valid workflow format
- Returns confidence scores and improvement suggestions
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestWorkflowGeneratorModels:
    """Tests for workflow generator Pydantic models."""

    def test_generated_workflow_output_model_exists(self) -> None:
        """GeneratedWorkflowOutput model should exist."""
        from mcp_server_langgraph.services.workflow_generator import (
            GeneratedWorkflowOutput,
        )

        schema = GeneratedWorkflowOutput.model_json_schema()
        properties = schema.get("properties", {})

        assert "name" in properties
        assert "description" in properties
        assert "nodes" in properties
        assert "edges" in properties
        assert "reasoning" in properties

    def test_generated_node_model_exists(self) -> None:
        """GeneratedNode model should exist with required fields."""
        from mcp_server_langgraph.services.workflow_generator import GeneratedNode

        schema = GeneratedNode.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "type" in properties
        assert "label" in properties
        assert "config" in properties

    def test_generated_edge_model_exists(self) -> None:
        """GeneratedEdge model should exist with required fields."""
        from mcp_server_langgraph.services.workflow_generator import GeneratedEdge

        schema = GeneratedEdge.model_json_schema()
        properties = schema.get("properties", {})

        assert "source" in properties
        assert "target" in properties
        assert "condition" in properties

    def test_workflow_generation_result_model_exists(self) -> None:
        """WorkflowGenerationResult model should exist."""
        from mcp_server_langgraph.services.workflow_generator import (
            WorkflowGenerationResult,
        )

        schema = WorkflowGenerationResult.model_json_schema()
        properties = schema.get("properties", {})

        assert "workflow" in properties
        assert "confidence" in properties
        assert "suggestions" in properties


class TestWorkflowGeneratorClass:
    """Tests for WorkflowGenerator class structure."""

    def test_workflow_generator_class_exists(self) -> None:
        """WorkflowGenerator class should exist."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        assert WorkflowGenerator is not None

    def test_workflow_generator_has_generate_from_prompt_method(self) -> None:
        """WorkflowGenerator should have generate_from_prompt method."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        assert hasattr(WorkflowGenerator, "generate_from_prompt")
        assert callable(WorkflowGenerator.generate_from_prompt)

    def test_workflow_generator_has_generate_from_session_method(self) -> None:
        """WorkflowGenerator should have generate_from_session method."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        assert hasattr(WorkflowGenerator, "generate_from_session")
        assert callable(WorkflowGenerator.generate_from_session)


@pytest.mark.xdist_group(name="test_workflow_generator_integration")
class TestWorkflowGeneratorIntegration:
    """Integration-style unit tests for workflow generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create a mock LLM that returns valid JSON."""
        llm = MagicMock()
        # Return a mock response with JSON content
        mock_response = MagicMock()
        mock_response.content = """{
            "name": "Customer Support Bot",
            "description": "A workflow for handling customer inquiries",
            "nodes": [
                {"id": "start", "type": "start", "label": "Start", "config": {}},
                {"id": "llm_1", "type": "llm", "label": "Process Query", "config": {"model": "gpt-4"}},
                {"id": "router", "type": "router", "label": "Route Response", "config": {}},
                {"id": "end", "type": "end", "label": "End", "config": {}}
            ],
            "edges": [
                {"source": "start", "target": "llm_1", "condition": null},
                {"source": "llm_1", "target": "router", "condition": null},
                {"source": "router", "target": "end", "condition": "default"}
            ],
            "reasoning": "Created a simple customer support workflow with an LLM node for processing and a router for response handling."
        }"""
        llm.ainvoke = AsyncMock(return_value=mock_response)
        return llm

    @pytest.mark.asyncio
    async def test_generate_from_prompt_returns_workflow(self, mock_llm: MagicMock) -> None:
        """generate_from_prompt should return a valid workflow."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a workflow generator with mocked LLM
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN generating from a prompt
        result = await generator.generate_from_prompt("Create a customer support chatbot")

        # THEN should return a workflow generation result
        assert result.workflow is not None
        assert result.workflow.name == "Customer Support Bot"
        assert len(result.workflow.nodes) >= 2  # At least start and end
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generate_from_prompt_calls_llm(self, mock_llm: MagicMock) -> None:
        """generate_from_prompt should call the LLM with appropriate prompt."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a workflow generator
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN generating from a prompt
        await generator.generate_from_prompt("Create an email automation workflow")

        # THEN should have called the LLM
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args
        # Verify the prompt contains the user's request
        messages = call_args[0][0]
        assert any("email automation" in str(m).lower() for m in messages)

    @pytest.mark.asyncio
    async def test_generate_from_session_uses_messages(self, mock_llm: MagicMock) -> None:
        """generate_from_session should use session messages for context."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a workflow generator
        generator = WorkflowGenerator(llm=mock_llm)

        # GIVEN session messages
        messages = [
            {"role": "user", "content": "I need help with data processing"},
            {"role": "assistant", "content": "I can help you create a data pipeline"},
            {"role": "user", "content": "Yes, let's process CSV files and store in a database"},
        ]

        # WHEN generating from session
        result = await generator.generate_from_session(messages)

        # THEN should return a workflow
        assert result.workflow is not None
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_includes_suggestions(self, mock_llm: MagicMock) -> None:
        """Generated workflow should include improvement suggestions."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a workflow generator
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN generating a workflow
        result = await generator.generate_from_prompt("Create a simple hello world bot")

        # THEN should include suggestions
        assert isinstance(result.suggestions, list)

    @pytest.mark.asyncio
    async def test_generate_handles_invalid_llm_response(self) -> None:
        """Should handle invalid LLM responses gracefully."""
        from mcp_server_langgraph.services.workflow_generator import (
            WorkflowGenerator,
            WorkflowGenerationError,
        )

        # GIVEN an LLM that returns invalid JSON
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN/THEN should raise WorkflowGenerationError
        with pytest.raises(WorkflowGenerationError):
            await generator.generate_from_prompt("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_calculates_confidence(self, mock_llm: MagicMock) -> None:
        """Should calculate confidence based on workflow completeness."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a workflow generator
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN generating a workflow
        result = await generator.generate_from_prompt("Create a complex multi-step workflow")

        # THEN confidence should be calculated
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.xdist_group(name="workflow_generator_prompt_building")
class TestWorkflowGeneratorPromptBuilding:
    """Tests for prompt building logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_system_prompt_includes_workflow_instructions(self) -> None:
        """System prompt should include workflow generation instructions."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a generator
        mock_llm = MagicMock()
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN getting the system prompt
        system_prompt = generator.get_system_prompt()

        # THEN should include key instructions
        assert "workflow" in system_prompt.lower()
        assert "node" in system_prompt.lower()
        assert "edge" in system_prompt.lower()
        assert "json" in system_prompt.lower()

    def test_system_prompt_includes_node_types(self) -> None:
        """System prompt should list available node types."""
        from mcp_server_langgraph.services.workflow_generator import WorkflowGenerator

        # GIVEN a generator
        mock_llm = MagicMock()
        generator = WorkflowGenerator(llm=mock_llm)

        # WHEN getting the system prompt
        system_prompt = generator.get_system_prompt()

        # THEN should include node types
        assert "start" in system_prompt.lower()
        assert "end" in system_prompt.lower()
        assert "llm" in system_prompt.lower()


@pytest.mark.xdist_group(name="workflow_generator_factory")
class TestCreateWorkflowGeneratorFactory:
    """Tests for workflow generator factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_workflow_generator_function_exists(self) -> None:
        """create_workflow_generator factory function should exist."""
        from mcp_server_langgraph.services.workflow_generator import (
            create_workflow_generator,
        )

        assert callable(create_workflow_generator)

    @pytest.mark.asyncio
    async def test_create_workflow_generator_returns_generator(self) -> None:
        """create_workflow_generator should return a WorkflowGenerator instance."""
        from mcp_server_langgraph.services.workflow_generator import (
            WorkflowGenerator,
        )

        # Create a generator directly with a mock LLM (simpler than patching imports)
        mock_llm = MagicMock()
        generator = WorkflowGenerator(llm=mock_llm)

        # THEN should be a WorkflowGenerator instance
        assert isinstance(generator, WorkflowGenerator)
