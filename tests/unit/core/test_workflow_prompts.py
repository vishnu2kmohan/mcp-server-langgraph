"""
Unit tests for workflow prompts centralization.

Tests the workflow generator prompt migrated from services/workflow_generator.py:
- WORKFLOW_GENERATOR_SYSTEM_PROMPT: Workflow design/generation

TDD: These tests are written FIRST before implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_workflow_prompts")
class TestWorkflowPromptsExist:
    """Test that workflow prompts are centralized and accessible."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_generator_prompt_exists(self) -> None:
        """Test WORKFLOW_GENERATOR_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.workflow_prompts import (
            WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        )

        assert WORKFLOW_GENERATOR_SYSTEM_PROMPT is not None
        assert isinstance(WORKFLOW_GENERATOR_SYSTEM_PROMPT, str)
        assert len(WORKFLOW_GENERATOR_SYSTEM_PROMPT) > 0


@pytest.mark.xdist_group(name="test_workflow_prompts")
class TestWorkflowPromptsContent:
    """Test workflow prompts have required content structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_has_json_enforcement(self) -> None:
        """Test prompt enforces JSON-only output."""
        from mcp_server_langgraph.core.prompts.workflow_prompts import (
            WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        )

        # Should mention JSON in output enforcement
        assert "json" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()

    def test_prompt_has_node_types(self) -> None:
        """Test WORKFLOW_GENERATOR_SYSTEM_PROMPT mentions node types."""
        from mcp_server_langgraph.core.prompts.workflow_prompts import (
            WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        )

        # Should mention node types
        assert "start" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()
        assert "end" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()
        assert "llm" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()
        assert "tool" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()
        assert "router" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()

    def test_prompt_has_output_format(self) -> None:
        """Test prompt defines output format structure."""
        from mcp_server_langgraph.core.prompts.workflow_prompts import (
            WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        )

        # Should define output format
        assert "nodes" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()
        assert "edges" in WORKFLOW_GENERATOR_SYSTEM_PROMPT.lower()


@pytest.mark.xdist_group(name="test_workflow_prompts")
class TestWorkflowPromptsSecurityBlock:
    """Test workflow prompts have security/injection protection blocks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_has_security_block(self) -> None:
        """Test prompt has security block for injection protection."""
        from mcp_server_langgraph.core.prompts.workflow_prompts import (
            WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        )

        # Should have security block
        assert "<security>" in WORKFLOW_GENERATOR_SYSTEM_PROMPT
        assert "</security>" in WORKFLOW_GENERATOR_SYSTEM_PROMPT
