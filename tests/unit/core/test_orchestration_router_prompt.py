"""
Unit tests for orchestration router prompt.

Tests the orchestration router prompt for:
- XML structure following Anthropic best practices
- Security block (injection protection)
- Dynamic template with available_tools context variable
- Output schema validation
- Code-level JSON fallback handling

TDD: These tests are written FIRST before implementation.
"""

import gc
import json

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.agents.router_agent import (
    DEFAULT_ROUTER_OUTPUT,
    RouterOutput,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_orchestration_router")
class TestOrchestrationRouterPromptStructure:
    """Test orchestration router prompt structure and content."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestration_router_prompt_exists(self) -> None:
        """Test that orchestration_router prompt is registered."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_orchestration_router_prompt_versioned(self) -> None:
        """Test that orchestration_router has versioning support."""
        from mcp_server_langgraph.core.prompts import (
            get_prompt_version,
            list_prompt_versions,
        )

        version = get_prompt_version("orchestration_router")
        assert version == "v1"

        versions = list_prompt_versions("orchestration_router")
        assert "v1" in versions
        assert "latest" in versions

    def test_orchestration_router_prompt_has_role_section(self) -> None:
        """Test that prompt contains <role> XML section."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        assert "<role>" in prompt
        assert "</role>" in prompt
        # Should describe classifier role
        assert "classifier" in prompt.lower() or "routing" in prompt.lower()

    def test_orchestration_router_prompt_has_security_block(self) -> None:
        """Test that prompt contains security/injection protection block."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        assert "<security>" in prompt
        assert "</security>" in prompt
        # Should contain untrusted/data-only instructions
        assert "untrusted" in prompt.lower() or "do not execute" in prompt.lower()

    def test_orchestration_router_prompt_has_output_schema(self) -> None:
        """Test that prompt contains output schema definition."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        # Should have output schema or output format section
        assert "<output_schema>" in prompt or "<output_format>" in prompt
        # Should mention required fields
        assert "complexity" in prompt
        assert "risk" in prompt
        assert "suggested_orchestrator" in prompt
        assert "critique_rounds" in prompt
        assert "thinking_budget" in prompt
        assert "confidence" in prompt

    def test_orchestration_router_prompt_has_defaults_section(self) -> None:
        """Test that prompt contains defaults on uncertainty section."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        # Should have defaults section
        assert "<defaults" in prompt.lower() or "default" in prompt.lower()
        # Should mention safe defaults
        assert "complicated" in prompt  # default complexity
        assert "medium" in prompt  # default risk

    def test_orchestration_router_prompt_enforces_json_only(self) -> None:
        """Test that prompt requires JSON-only output."""
        from mcp_server_langgraph.core.prompts import get_prompt

        prompt = get_prompt("orchestration_router")
        # Should enforce JSON-only output
        assert "json" in prompt.lower()
        assert ("only" in prompt.lower() and "json" in prompt.lower()) or "no markdown" in prompt.lower()


@pytest.mark.xdist_group(name="test_orchestration_router")
class TestOrchestrationRouterDynamicTemplate:
    """Test orchestration router prompt as a dynamic template."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestration_router_template_exists(self) -> None:
        """Test that template function exists."""
        from mcp_server_langgraph.core.prompts.orchestration_router_prompt import (
            get_orchestration_router_prompt,
        )

        assert callable(get_orchestration_router_prompt)

    def test_orchestration_router_template_accepts_available_tools(self) -> None:
        """Test that template accepts available_tools parameter."""
        from mcp_server_langgraph.core.prompts.orchestration_router_prompt import (
            get_orchestration_router_prompt,
        )

        tools = ["file_read", "file_write", "bash", "code_search"]
        prompt = get_orchestration_router_prompt(available_tools=tools)

        # Tools should be mentioned in the prompt
        assert "file_read" in prompt
        assert "file_write" in prompt
        assert "bash" in prompt
        assert "code_search" in prompt

    def test_orchestration_router_template_with_empty_tools(self) -> None:
        """Test that template handles empty tools list."""
        from mcp_server_langgraph.core.prompts.orchestration_router_prompt import (
            get_orchestration_router_prompt,
        )

        prompt = get_orchestration_router_prompt(available_tools=[])
        # Should still be a valid prompt
        assert "<role>" in prompt
        assert "<security>" in prompt

    def test_orchestration_router_template_with_no_tools_param(self) -> None:
        """Test that template works without tools parameter (uses default)."""
        from mcp_server_langgraph.core.prompts.orchestration_router_prompt import (
            get_orchestration_router_prompt,
        )

        # Should not raise, should use default empty list
        prompt = get_orchestration_router_prompt()
        assert "<role>" in prompt
        assert "<security>" in prompt


@pytest.mark.xdist_group(name="test_orchestration_router")
class TestRouterOutputSchemaValidation:
    """Test RouterOutput Pydantic model schema validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_valid_simple_low(self) -> None:
        """Test valid RouterOutput with simple/low settings."""
        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )
        assert output.complexity == "simple"
        assert output.risk == "low"
        assert output.critique_rounds == 0
        assert output.confidence == 0.95

    def test_router_output_valid_complex_high(self) -> None:
        """Test valid RouterOutput with complex/high settings."""
        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="code",
            tools_needed=["file_read", "file_write", "bash"],
            suggested_orchestrator="swarm",
            critique_rounds=3,
            thinking_budget="deep",
            confidence=0.85,
        )
        assert output.complexity == "complex"
        assert output.risk == "high"
        assert output.critique_rounds == 3
        assert output.thinking_budget == "deep"

    def test_router_output_critique_rounds_clamped_max(self) -> None:
        """Test that critique_rounds > 3 raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="complex",
                risk="high",
                task_type="code",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=4,  # Invalid: max is 3
                thinking_budget="deep",
                confidence=0.85,
            )

    def test_router_output_critique_rounds_clamped_min(self) -> None:
        """Test that critique_rounds < 0 raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="complex",
                risk="high",
                task_type="code",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=-1,  # Invalid: min is 0
                thinking_budget="deep",
                confidence=0.85,
            )

    def test_router_output_confidence_clamped_max(self) -> None:
        """Test that confidence > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=1.5,  # Invalid: max is 1.0
            )

    def test_router_output_confidence_clamped_min(self) -> None:
        """Test that confidence < 0.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=-0.1,  # Invalid: min is 0.0
            )

    def test_router_output_invalid_complexity(self) -> None:
        """Test that invalid complexity value raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="invalid",  # Not in Literal["simple", "complicated", "complex"]
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.5,
            )

    def test_router_output_invalid_orchestrator(self) -> None:
        """Test that invalid orchestrator value raises ValidationError."""
        with pytest.raises(ValidationError):
            RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="invalid",  # Not in allowlist
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.5,
            )


@pytest.mark.xdist_group(name="test_orchestration_router")
class TestRouterOutputJSONParsing:
    """Test RouterOutput JSON parsing with code-level fallbacks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_parses_valid_json(self) -> None:
        """Test that valid JSON parses to RouterOutput."""
        json_str = json.dumps(
            {
                "complexity": "complicated",
                "risk": "medium",
                "task_type": "analysis",
                "tools_needed": ["file_read"],
                "suggested_orchestrator": "standard",
                "critique_rounds": 1,
                "thinking_budget": "light",
                "confidence": 0.75,
            }
        )
        data = json.loads(json_str)
        output = RouterOutput(**data)
        assert output.complexity == "complicated"
        assert output.risk == "medium"
        assert output.confidence == 0.75

    def test_router_output_fallback_on_invalid_json(self) -> None:
        """Test that code-level fallback is used on invalid JSON."""
        invalid_json = "not valid json {"

        try:
            data = json.loads(invalid_json)
            output = RouterOutput(**data)
        except (json.JSONDecodeError, ValueError):
            # Fallback to default - this is the expected code pattern
            output = DEFAULT_ROUTER_OUTPUT

        # Should get default values
        assert output.complexity == "complicated"
        assert output.risk == "medium"
        assert output.suggested_orchestrator == "standard"
        assert output.critique_rounds == 1
        assert output.thinking_budget == "light"
        assert output.confidence == 0.5

    def test_router_output_fallback_on_missing_fields(self) -> None:
        """Test fallback when JSON is missing required fields."""
        partial_json = json.dumps(
            {
                "complexity": "simple",
                # Missing all other required fields
            }
        )

        try:
            data = json.loads(partial_json)
            output = RouterOutput(**data)
        except (json.JSONDecodeError, ValidationError):
            # Fallback to default - this is the expected code pattern
            output = DEFAULT_ROUTER_OUTPUT

        # Should get default values
        assert output.complexity == "complicated"
        assert output.confidence == 0.5

    def test_default_router_output_values(self) -> None:
        """Test that DEFAULT_ROUTER_OUTPUT has expected safe defaults."""
        assert DEFAULT_ROUTER_OUTPUT.complexity == "complicated"
        assert DEFAULT_ROUTER_OUTPUT.risk == "medium"
        assert DEFAULT_ROUTER_OUTPUT.task_type == "other"
        assert DEFAULT_ROUTER_OUTPUT.tools_needed == []
        assert DEFAULT_ROUTER_OUTPUT.suggested_orchestrator == "standard"
        assert DEFAULT_ROUTER_OUTPUT.critique_rounds == 1
        assert DEFAULT_ROUTER_OUTPUT.thinking_budget == "light"
        assert DEFAULT_ROUTER_OUTPUT.confidence == 0.5
