"""
Unit tests for GenUI prompts centralization.

Tests the 3 GenUI prompts migrated from agents/genui_orchestrator.py:
- GENUI_WIDGET_SYSTEM_PROMPT: Widget configuration generation
- GENUI_RENDER_SYSTEM_PROMPT: Data transformation to UI format
- GENUI_FORM_SYSTEM_PROMPT: Form submission processing

TDD: These tests are written FIRST before implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_genui_prompts")
class TestGenUIPromptsExist:
    """Test that all GenUI prompts are centralized and accessible."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_genui_widget_prompt_exists(self) -> None:
        """Test GENUI_WIDGET_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.genui_prompts import (
            GENUI_WIDGET_SYSTEM_PROMPT,
        )

        assert GENUI_WIDGET_SYSTEM_PROMPT is not None
        assert isinstance(GENUI_WIDGET_SYSTEM_PROMPT, str)
        assert len(GENUI_WIDGET_SYSTEM_PROMPT) > 0

    def test_genui_render_prompt_exists(self) -> None:
        """Test GENUI_RENDER_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.genui_prompts import (
            GENUI_RENDER_SYSTEM_PROMPT,
        )

        assert GENUI_RENDER_SYSTEM_PROMPT is not None
        assert isinstance(GENUI_RENDER_SYSTEM_PROMPT, str)

    def test_genui_form_prompt_exists(self) -> None:
        """Test GENUI_FORM_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.genui_prompts import (
            GENUI_FORM_SYSTEM_PROMPT,
        )

        assert GENUI_FORM_SYSTEM_PROMPT is not None
        assert isinstance(GENUI_FORM_SYSTEM_PROMPT, str)


@pytest.mark.xdist_group(name="test_genui_prompts")
class TestGenUIPromptsContent:
    """Test GenUI prompts have required content structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_json_enforcement(self) -> None:
        """Test all prompts enforce JSON-only output."""
        from mcp_server_langgraph.core.prompts import genui_prompts

        prompt_names = [
            "GENUI_WIDGET_SYSTEM_PROMPT",
            "GENUI_RENDER_SYSTEM_PROMPT",
            "GENUI_FORM_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(genui_prompts, name)
            # All prompts should mention JSON in output enforcement
            assert "json" in prompt.lower(), f"{name} should enforce JSON output"

    def test_widget_prompt_has_widget_types(self) -> None:
        """Test GENUI_WIDGET_SYSTEM_PROMPT mentions widget types."""
        from mcp_server_langgraph.core.prompts.genui_prompts import (
            GENUI_WIDGET_SYSTEM_PROMPT,
        )

        # Should mention widget types
        assert "chart" in GENUI_WIDGET_SYSTEM_PROMPT.lower()
        assert "table" in GENUI_WIDGET_SYSTEM_PROMPT.lower()
        assert "text" in GENUI_WIDGET_SYSTEM_PROMPT.lower()

    def test_form_prompt_has_actions(self) -> None:
        """Test GENUI_FORM_SYSTEM_PROMPT mentions form actions."""
        from mcp_server_langgraph.core.prompts.genui_prompts import (
            GENUI_FORM_SYSTEM_PROMPT,
        )

        # Should mention form actions
        assert "submit" in GENUI_FORM_SYSTEM_PROMPT.lower()
        assert "validate" in GENUI_FORM_SYSTEM_PROMPT.lower()


@pytest.mark.xdist_group(name="test_genui_prompts")
class TestGenUIPromptsSecurityBlock:
    """Test GenUI prompts have security/injection protection blocks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_security_block(self) -> None:
        """Test all prompts have security block for injection protection."""
        from mcp_server_langgraph.core.prompts import genui_prompts

        prompt_names = [
            "GENUI_WIDGET_SYSTEM_PROMPT",
            "GENUI_RENDER_SYSTEM_PROMPT",
            "GENUI_FORM_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(genui_prompts, name)
            # All prompts should have security block
            assert "<security>" in prompt, f"{name} should have security block"
            assert "</security>" in prompt, f"{name} should have security closing tag"
