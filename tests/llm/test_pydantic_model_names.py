"""
Test pydantic-ai model name formatting with provider prefixes.

PYDANTIC-AI DEPRECATION: Model names must include provider prefix.

Background:
-----------
Pydantic AI v0.0.14+ requires model names to include provider prefixes:
- Google Gemini: 'google-gla:gemini-2.5-flash' (not 'gemini-2.5-flash')
- Anthropic Claude: 'anthropic:claude-sonnet-4-5-20250929'
- OpenAI: 'openai:gpt-4'

Without prefixes, deprecation warnings are emitted:
"Specifying a model name without a provider prefix is deprecated.
Instead of 'gemini-2.5-flash', use 'google-gla:gemini-2.5-flash'."

This test ensures the PydanticAIAgentWrapper correctly adds provider
prefixes to model names before passing them to pydantic-ai.

References:
-----------
- pydantic-ai docs: https://ai.pydantic.dev/models/
- Related issue: https://github.com/pydantic/pydantic-ai/issues/XXX
"""

from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper


@pytest.fixture
def mock_pydantic_agent_class():
    """Mock Pydantic AI Agent class to avoid API key requirements."""
    with patch("mcp_server_langgraph.llm.pydantic_agent.Agent") as mock_agent_class:
        yield mock_agent_class


@pytest.mark.unit
class TestPydanticModelNameFormatting:
    """Test proper model name formatting for pydantic-ai"""

    def test_google_gemini_model_has_google_gla_prefix(self, mock_pydantic_agent_class):
        """Gemini models must have 'google-gla:' prefix for pydantic-ai"""
        wrapper = PydanticAIAgentWrapper(model_name="gemini-2.5-flash", provider="google")

        pydantic_model_name = wrapper.pydantic_model_name

        assert pydantic_model_name == "google-gla:gemini-2.5-flash", (
            "Google Gemini models must use 'google-gla:' prefix for pydantic-ai. " f"Got: {pydantic_model_name}"
        )

    def test_gemini_provider_alias_has_google_gla_prefix(self, mock_pydantic_agent_class):
        """Provider 'gemini' should be treated same as 'google'"""
        wrapper = PydanticAIAgentWrapper(model_name="gemini-2.5-flash", provider="gemini")

        pydantic_model_name = wrapper.pydantic_model_name

        assert pydantic_model_name == "google-gla:gemini-2.5-flash", (
            "Provider 'gemini' should map to 'google-gla:' prefix. " f"Got: {pydantic_model_name}"
        )

    def test_anthropic_claude_model_has_anthropic_prefix(self, mock_pydantic_agent_class):
        """Claude models must have 'anthropic:' prefix"""
        wrapper = PydanticAIAgentWrapper(model_name="claude-sonnet-4-5-20250929", provider="anthropic")

        pydantic_model_name = wrapper.pydantic_model_name

        assert pydantic_model_name == "anthropic:claude-sonnet-4-5-20250929", (
            "Anthropic Claude models must use 'anthropic:' prefix. " f"Got: {pydantic_model_name}"
        )

    def test_openai_model_has_openai_prefix(self, mock_pydantic_agent_class):
        """OpenAI models must have 'openai:' prefix"""
        wrapper = PydanticAIAgentWrapper(model_name="gpt-4", provider="openai")

        pydantic_model_name = wrapper.pydantic_model_name

        assert pydantic_model_name == "openai:gpt-4", "OpenAI models must use 'openai:' prefix. " f"Got: {pydantic_model_name}"

    def test_unknown_provider_still_adds_prefix(self, mock_pydantic_agent_class):
        """Unknown providers should still get a prefix (provider:model format)"""
        wrapper = PydanticAIAgentWrapper(model_name="custom-model", provider="custom-provider")

        pydantic_model_name = wrapper.pydantic_model_name

        assert pydantic_model_name == "custom-provider:custom-model", (
            "Unknown providers should use 'provider:model' format. " f"Got: {pydantic_model_name}"
        )

    def test_settings_default_model_works_with_pydantic_ai(self, mock_pydantic_agent_class):
        """Default model from settings should work with pydantic-ai wrapper"""
        settings = Settings()

        # Ensure settings has a valid model configuration
        # Default is gemini-2.5-flash with google provider
        wrapper = PydanticAIAgentWrapper(model_name=settings.model_name, provider=settings.llm_provider)

        pydantic_model_name = wrapper.pydantic_model_name

        # Should have a provider prefix (contains colon)
        assert ":" in pydantic_model_name, (
            f"Default model '{settings.model_name}' from settings should have "
            f"provider prefix when used with pydantic-ai. Got: {pydantic_model_name}"
        )

    def test_model_name_without_prefix_gets_prefixed(self, mock_pydantic_agent_class):
        """
        Unprefixed model names should get provider prefix added.

        This is the core fix for the deprecation warning:
        "Specifying a model name without a provider prefix is deprecated"
        """
        test_cases = [
            ("gemini-2.5-flash", "google", "google-gla:gemini-2.5-flash"),
            ("gemini-2.5-pro", "google", "google-gla:gemini-2.5-pro"),
            ("claude-opus-4-1-20250805", "anthropic", "anthropic:claude-opus-4-1-20250805"),
            ("gpt-5", "openai", "openai:gpt-5"),
        ]

        for model_name, provider, expected_output in test_cases:
            wrapper = PydanticAIAgentWrapper(model_name=model_name, provider=provider)

            pydantic_model_name = wrapper.pydantic_model_name

            assert pydantic_model_name == expected_output, (
                f"Model '{model_name}' with provider '{provider}' should become '{expected_output}'. "
                f"Got: {pydantic_model_name}"
            )

    def test_already_prefixed_model_not_double_prefixed(self, mock_pydantic_agent_class):
        """If model name already has prefix, don't add another one"""
        # This is an edge case - config should have unprefixed names,
        # but if someone manually provides a prefixed name, don't break it
        wrapper = PydanticAIAgentWrapper(model_name="google-gla:gemini-2.5-flash", provider="google")

        pydantic_model_name = wrapper.pydantic_model_name

        # Should NOT become "google-gla:google-gla:gemini-2.5-flash"
        # Implementation checks for existing prefix and returns it as-is
        assert pydantic_model_name == "google-gla:gemini-2.5-flash", f"Should not double-prefix: {pydantic_model_name}"


@pytest.mark.unit
class TestPydanticWrapperIntegration:
    """Integration tests for PydanticAIAgentWrapper with real-world scenarios"""

    def test_wrapper_initialization_with_gemini_model(self, mock_pydantic_agent_class):
        """Wrapper should initialize correctly with Gemini model"""
        wrapper = PydanticAIAgentWrapper(model_name="gemini-2.5-flash", provider="google")

        assert wrapper.model_name == "gemini-2.5-flash"
        assert wrapper.provider in ["google", "gemini"]  # Either should work
        assert wrapper.pydantic_model_name == "google-gla:gemini-2.5-flash"

    def test_wrapper_initialization_with_settings(self, mock_pydantic_agent_class):
        """Wrapper should work with models from Settings"""
        settings = Settings()

        # Test with main model
        wrapper = PydanticAIAgentWrapper(model_name=settings.model_name, provider=settings.llm_provider)

        pydantic_model_name = wrapper.pydantic_model_name
        assert ":" in pydantic_model_name, "Should have provider prefix"

        # Test with summarization model (if configured)
        if settings.summarization_model_name:
            wrapper2 = PydanticAIAgentWrapper(model_name=settings.summarization_model_name, provider=settings.llm_provider)

            pydantic_model_name2 = wrapper2.pydantic_model_name
            assert ":" in pydantic_model_name2, "Summarization model should have provider prefix"
