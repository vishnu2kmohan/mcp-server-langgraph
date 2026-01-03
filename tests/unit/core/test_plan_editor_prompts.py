"""
Unit tests for plan editor prompts.

Tests plan editor prompts for Phase 5b readiness:
- PLAN_VALIDATION_SYSTEM_PROMPT: Plan validation with constraints
- TEMPLATE_SUGGESTION_SYSTEM_PROMPT: Template suggestion (feature-flagged)

Feature flags tested:
- ff_enable_plan_search: Guards semantic template search
- ff_enable_plan_templates: Guards template suggestion features

TDD: These tests are written FIRST before implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_plan_editor_prompts")
class TestPlanEditorPromptsExist:
    """Test that plan editor prompts are defined and accessible."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_validation_prompt_exists(self) -> None:
        """Test PLAN_VALIDATION_SYSTEM_PROMPT is defined."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
        )

        assert PLAN_VALIDATION_SYSTEM_PROMPT is not None
        assert isinstance(PLAN_VALIDATION_SYSTEM_PROMPT, str)
        assert len(PLAN_VALIDATION_SYSTEM_PROMPT) > 0

    def test_template_suggestion_prompt_exists(self) -> None:
        """Test TEMPLATE_SUGGESTION_SYSTEM_PROMPT is defined."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        )

        assert TEMPLATE_SUGGESTION_SYSTEM_PROMPT is not None
        assert isinstance(TEMPLATE_SUGGESTION_SYSTEM_PROMPT, str)


@pytest.mark.xdist_group(name="test_plan_editor_prompts")
class TestPlanEditorPromptsContent:
    """Test plan editor prompts have required content structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompts_have_json_enforcement(self) -> None:
        """Test all prompts enforce JSON-only output."""
        from mcp_server_langgraph.core.prompts import plan_editor_prompts

        prompt_names = [
            "PLAN_VALIDATION_SYSTEM_PROMPT",
            "TEMPLATE_SUGGESTION_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(plan_editor_prompts, name)
            assert "json" in prompt.lower(), f"{name} should enforce JSON output"

    def test_plan_validation_has_orchestrator_allowlist(self) -> None:
        """Test PLAN_VALIDATION_SYSTEM_PROMPT mentions valid orchestrators."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
        )

        # Should mention valid orchestrators
        assert "standard" in PLAN_VALIDATION_SYSTEM_PROMPT.lower()
        assert "swarm" in PLAN_VALIDATION_SYSTEM_PROMPT.lower()

    def test_plan_validation_has_thinking_budget_enum(self) -> None:
        """Test PLAN_VALIDATION_SYSTEM_PROMPT mentions thinking budget levels."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
        )

        # Should mention thinking budget levels
        assert "none" in PLAN_VALIDATION_SYSTEM_PROMPT.lower()
        assert "deep" in PLAN_VALIDATION_SYSTEM_PROMPT.lower()

    def test_plan_validation_has_critique_rounds_constraint(self) -> None:
        """Test PLAN_VALIDATION_SYSTEM_PROMPT mentions critique_rounds constraint."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
        )

        # Should mention critique_rounds constraint (0-3)
        assert "critique" in PLAN_VALIDATION_SYSTEM_PROMPT.lower()


@pytest.mark.xdist_group(name="test_plan_editor_prompts")
class TestPlanEditorPromptsSecurityBlock:
    """Test plan editor prompts have security/injection protection blocks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_security_block(self) -> None:
        """Test all prompts have security block for injection protection."""
        from mcp_server_langgraph.core.prompts import plan_editor_prompts

        prompt_names = [
            "PLAN_VALIDATION_SYSTEM_PROMPT",
            "TEMPLATE_SUGGESTION_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(plan_editor_prompts, name)
            assert "<security>" in prompt, f"{name} should have security block"
            assert "</security>" in prompt, f"{name} should have security closing tag"


@pytest.mark.xdist_group(name="test_plan_editor_prompts")
class TestPlanEditorDynamicTemplate:
    """Test plan editor prompts as dynamic templates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_plan_validation_prompt_exists(self) -> None:
        """Test get_plan_validation_prompt function exists."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            get_plan_validation_prompt,
        )

        assert callable(get_plan_validation_prompt)

    def test_get_plan_validation_prompt_accepts_model_ids(self) -> None:
        """Test get_plan_validation_prompt accepts valid_model_ids parameter."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            get_plan_validation_prompt,
        )

        model_ids = ["gemini-3-flash", "claude-sonnet-4-5-20250929"]
        prompt = get_plan_validation_prompt(valid_model_ids=model_ids)

        # Model IDs should be mentioned in the prompt
        assert "gemini-3-flash" in prompt
        assert "claude-sonnet-4-5-20250929" in prompt

    def test_get_plan_validation_prompt_with_empty_models(self) -> None:
        """Test get_plan_validation_prompt handles empty model list."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            get_plan_validation_prompt,
        )

        prompt = get_plan_validation_prompt(valid_model_ids=[])
        # Should still be a valid prompt
        assert "<role>" in prompt
        assert "<security>" in prompt
