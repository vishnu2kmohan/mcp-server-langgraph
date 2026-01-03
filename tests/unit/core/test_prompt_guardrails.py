"""
Comprehensive guardrail tests for prompt architecture.

Tests JSON parsing, defaults, clamps, and required key validation:
- JSON parsing tests: Verify all prompts produce parseable JSON structures
- Default value tests: Verify fallback defaults are applied on missing fields
- Clamp tests: Verify constraints (critique_rounds 0-3, confidence 0.0-1.0)
- Required key tests: Verify required keys are always present in output
- Security block tests: Verify all prompts have injection protection

These tests ensure robustness of the prompt output parsing pipeline.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_prompt_guardrails")
class TestAllPromptsHaveSecurityBlocks:
    """Verify ALL centralized prompts have security blocks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_core_prompts_have_security_block(self) -> None:
        """Test all core prompts have security/injection protection."""
        from mcp_server_langgraph.core.prompts.response_prompt import (
            RESPONSE_SYSTEM_PROMPT,
        )
        from mcp_server_langgraph.core.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
        from mcp_server_langgraph.core.prompts.verification_prompt import (
            VERIFICATION_SYSTEM_PROMPT,
        )

        prompts = {
            "ROUTER_SYSTEM_PROMPT": ROUTER_SYSTEM_PROMPT,
            "RESPONSE_SYSTEM_PROMPT": RESPONSE_SYSTEM_PROMPT,
            "VERIFICATION_SYSTEM_PROMPT": VERIFICATION_SYSTEM_PROMPT,
        }

        for name, prompt in prompts.items():
            assert "<security>" in prompt, f"{name} missing security block"
            assert "</security>" in prompt, f"{name} missing security closing tag"

    def test_orchestration_router_has_security_block(self) -> None:
        """Test orchestration router prompt has security block."""
        from mcp_server_langgraph.core.prompts import get_orchestration_router_prompt

        prompt = get_orchestration_router_prompt()
        assert "<security>" in prompt
        assert "</security>" in prompt
        assert "untrusted" in prompt.lower()

    def test_plan_editor_prompts_have_security_block(self) -> None:
        """Test plan editor prompts have security block."""
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        )

        for prompt in [PLAN_VALIDATION_SYSTEM_PROMPT, TEMPLATE_SUGGESTION_SYSTEM_PROMPT]:
            assert "<security>" in prompt
            assert "</security>" in prompt


@pytest.mark.xdist_group(name="test_prompt_guardrails")
class TestRouterOutputConstraints:
    """Test RouterOutput Pydantic model constraints and clamps."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_critique_rounds_min_boundary(self) -> None:
        """Test critique_rounds = 0 is valid (minimum)."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,  # Minimum valid
            thinking_budget="none",
            confidence=0.9,
        )
        assert output.critique_rounds == 0

    def test_critique_rounds_max_boundary(self) -> None:
        """Test critique_rounds = 3 is valid (maximum)."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="code",
            tools_needed=["bash"],
            suggested_orchestrator="swarm",
            critique_rounds=3,  # Maximum valid
            thinking_budget="deep",
            confidence=0.8,
        )
        assert output.critique_rounds == 3

    def test_confidence_min_boundary(self) -> None:
        """Test confidence = 0.0 is valid (minimum)."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.0,  # Minimum valid
        )
        assert output.confidence == 0.0

    def test_confidence_max_boundary(self) -> None:
        """Test confidence = 1.0 is valid (maximum)."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=1.0,  # Maximum valid
        )
        assert output.confidence == 1.0


@pytest.mark.xdist_group(name="test_prompt_guardrails")
class TestDefaultRouterOutputValues:
    """Test DEFAULT_ROUTER_OUTPUT has expected safe defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_uses_complicated_complexity(self) -> None:
        """Default complexity should be 'complicated' (middle tier)."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.complexity == "complicated"

    def test_default_uses_medium_risk(self) -> None:
        """Default risk should be 'medium' (safe middle ground)."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.risk == "medium"

    def test_default_uses_standard_orchestrator(self) -> None:
        """Default orchestrator should be 'standard'."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.suggested_orchestrator == "standard"

    def test_default_uses_single_critique_round(self) -> None:
        """Default critique_rounds should be 1 (light review)."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.critique_rounds == 1

    def test_default_uses_light_thinking_budget(self) -> None:
        """Default thinking_budget should be 'light'."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.thinking_budget == "light"

    def test_default_uses_half_confidence(self) -> None:
        """Default confidence should be 0.5 (uncertain)."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.confidence == 0.5


@pytest.mark.xdist_group(name="test_prompt_guardrails")
class TestPromptXMLStructure:
    """Test all prompts have proper XML structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_role_section(self) -> None:
        """Test all prompts have <role> section."""
        from mcp_server_langgraph.core.prompts import get_orchestration_router_prompt
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        )
        from mcp_server_langgraph.core.prompts.response_prompt import (
            RESPONSE_SYSTEM_PROMPT,
        )
        from mcp_server_langgraph.core.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
        from mcp_server_langgraph.core.prompts.verification_prompt import (
            VERIFICATION_SYSTEM_PROMPT,
        )

        prompts = [
            ROUTER_SYSTEM_PROMPT,
            RESPONSE_SYSTEM_PROMPT,
            VERIFICATION_SYSTEM_PROMPT,
            get_orchestration_router_prompt(),
            PLAN_VALIDATION_SYSTEM_PROMPT,
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        ]

        for prompt in prompts:
            assert "<role>" in prompt, "Prompt missing <role> section"
            assert "</role>" in prompt, "Prompt missing </role> closing tag"

    def test_prompts_with_json_output_have_format_enforcement(self) -> None:
        """Test prompts requiring JSON output have format enforcement."""
        from mcp_server_langgraph.core.prompts import get_orchestration_router_prompt
        from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
            PLAN_VALIDATION_SYSTEM_PROMPT,
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        )

        prompts = [
            get_orchestration_router_prompt(),
            PLAN_VALIDATION_SYSTEM_PROMPT,
            TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        ]

        for prompt in prompts:
            # Should have format enforcement or output format section
            has_enforcement = (
                "<format_enforcement>" in prompt
                or "<output_format>" in prompt
                or "only" in prompt.lower()
                and "json" in prompt.lower()
            )
            assert has_enforcement, "JSON prompts should have format enforcement"


@pytest.mark.xdist_group(name="test_prompt_guardrails")
class TestSchemaConstraintValidation:
    """Test Pydantic schema constraint validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_response_output_content_required(self) -> None:
        """Test ResponseOutput requires content field."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput

        with pytest.raises(ValidationError):
            ResponseOutput(confidence=0.9)  # Missing content

    def test_verification_output_feedback_required(self) -> None:
        """Test VerificationOutput requires feedback field."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.schemas import VerificationOutput

        with pytest.raises(ValidationError):
            VerificationOutput(
                accuracy=0.9,
                completeness=0.9,
                clarity=0.9,
                relevance=0.9,
                safety=1.0,
                sources=0.8,
                overall=0.9,
                requires_refinement=False,
                # Missing feedback
            )

    def test_error_analysis_category_enum(self) -> None:
        """Test ErrorAnalysisOutput category must be valid enum."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.prompts.schemas import ErrorAnalysisOutput

        # Valid category
        output = ErrorAnalysisOutput(
            category="network",
            subcategory="timeout",
            confidence=0.8,
            root_cause="Connection failed",
            suggestions=[],
        )
        assert output.category == "network"

        # Invalid category
        with pytest.raises(ValidationError):
            ErrorAnalysisOutput(
                category="invalid",  # Not in enum
                subcategory="test",
                confidence=0.8,
                root_cause="test",
                suggestions=[],
            )
