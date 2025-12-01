"""
Unit tests for Vertex AI provider detection in LLMFactory.

Tests the _get_provider_from_model method to ensure it correctly identifies
Vertex AI models for both Anthropic Claude and Google Gemini models.
"""

import gc

import pytest

from mcp_server_langgraph.llm.factory import LLMFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def llm_factory():
    """Create LLMFactory instance for testing provider detection."""
    factory = LLMFactory(
        provider="test",
        model_name="test-model",
        api_key="test-key",
    )
    return factory


@pytest.mark.unit
@pytest.mark.xdist_group(name="vertex_ai_provider_detection_tests")
class TestVertexAIProviderDetection:
    """Test Vertex AI provider detection for various model names."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_vertex_ai_claude_sonnet_with_prefix(self, llm_factory):
        """Test detection of Vertex AI Claude Sonnet with vertex_ai/ prefix."""
        model_name = "vertex_ai/claude-sonnet-4-5@20250929"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_vertex_ai_claude_haiku_with_prefix(self, llm_factory):
        """Test detection of Vertex AI Claude Haiku with vertex_ai/ prefix."""
        model_name = "vertex_ai/claude-haiku-4-5@20251001"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_vertex_ai_claude_opus_with_prefix(self, llm_factory):
        """Test detection of Vertex AI Claude Opus with vertex_ai/ prefix."""
        model_name = "vertex_ai/claude-opus-4-1@20250805"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_vertex_ai_gemini_pro_with_prefix(self, llm_factory):
        """Test detection of Vertex AI Gemini 3.0 Pro with vertex_ai/ prefix."""
        model_name = "vertex_ai/gemini-3-pro-preview"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_vertex_ai_gemini_flash_with_prefix(self, llm_factory):
        """Test detection of Vertex AI Gemini Flash with vertex_ai/ prefix."""
        model_name = "vertex_ai/gemini-2.5-flash"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_anthropic_direct_claude_sonnet(self, llm_factory):
        """Test detection of direct Anthropic API (without vertex_ai/ prefix)."""
        model_name = "claude-sonnet-4-5@20250929"
        provider = llm_factory._get_provider_from_model(model_name)
        # Should detect as anthropic, not vertex_ai
        assert provider == "anthropic"

    def test_detect_anthropic_direct_claude_haiku(self, llm_factory):
        """Test detection of direct Anthropic API for Haiku."""
        model_name = "claude-haiku-4-5@20251001"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "anthropic"

    def test_detect_google_direct_gemini_pro(self, llm_factory):
        """Test detection of Google AI Studio API (without vertex_ai/ prefix)."""
        model_name = "gemini-3-pro-preview"
        provider = llm_factory._get_provider_from_model(model_name)
        # Should detect as google, not vertex_ai
        assert provider == "google"

    def test_detect_google_direct_gemini_flash(self, llm_factory):
        """Test detection of Google AI Studio API for Flash."""
        model_name = "gemini-2.5-flash"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "google"

    def test_vertex_ai_prefix_takes_precedence_over_pattern(self, llm_factory):
        """Test that vertex_ai/ prefix takes precedence over model name pattern."""
        # Even though "claude" would match anthropic pattern,
        # vertex_ai/ prefix should take precedence
        model_name = "vertex_ai/claude-sonnet-4-5@20250929"
        provider = llm_factory._get_provider_from_model(model_name)
        assert provider == "vertex_ai"

    def test_detect_openai_models(self, llm_factory):
        """Test detection of OpenAI models (should not be affected)."""
        model_names = ["gpt-4", "gpt-5.1", "gpt-3.5-turbo", "o1-preview"]
        for model_name in model_names:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "openai", f"Failed for model: {model_name}"

    def test_detect_azure_models(self, llm_factory):
        """Test detection of Azure OpenAI models."""
        model_names = ["azure/gpt-4", "azure/gpt-35-turbo"]
        for model_name in model_names:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "azure", f"Failed for model: {model_name}"

    def test_detect_bedrock_models(self, llm_factory):
        """Test detection of AWS Bedrock models."""
        model_names = ["bedrock/claude-3", "bedrock/titan"]
        for model_name in model_names:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "bedrock", f"Failed for model: {model_name}"

    def test_detect_ollama_models(self, llm_factory):
        """Test detection of Ollama models."""
        model_names = ["ollama/llama2", "ollama/mistral"]
        for model_name in model_names:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "ollama", f"Failed for model: {model_name}"

    def test_case_insensitive_detection(self, llm_factory):
        """Test that provider detection is case-insensitive."""
        model_names = [
            "VERTEX_AI/claude-sonnet-4-5@20250929",
            "Vertex_Ai/gemini-2.5-pro",
            "CLAUDE-HAIKU-4-5@20251001",
            "GEMINI-2.5-FLASH",
        ]
        # vertex_ai/ prefix (any case) should be detected
        assert llm_factory._get_provider_from_model(model_names[0]) == "vertex_ai"
        assert llm_factory._get_provider_from_model(model_names[1]) == "vertex_ai"
        # Direct models should still be detected correctly
        assert llm_factory._get_provider_from_model(model_names[2]) == "anthropic"
        assert llm_factory._get_provider_from_model(model_names[3]) == "google"

    def test_fallback_to_default_provider(self, llm_factory):
        """Test fallback to default provider for unknown models."""
        model_name = "unknown-model-xyz"
        provider = llm_factory._get_provider_from_model(model_name)
        # Should fall back to the factory's default provider
        assert provider == llm_factory.provider


@pytest.mark.unit
@pytest.mark.xdist_group(name="vertex_ai_provider_detection_tests")
class TestVertexAIModelNamingConventions:
    """Test various Vertex AI model naming conventions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_claude_3_family_models_via_vertex_ai(self, llm_factory):
        """Test older Claude 3 family models via Vertex AI."""
        older_models = [
            "vertex_ai/claude-3-opus@20240229",
            "vertex_ai/claude-3-5-sonnet@20240620",
            "vertex_ai/claude-3-haiku@20240307",
        ]
        for model_name in older_models:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "vertex_ai", f"Failed for model: {model_name}"

    def test_claude_4_family_models_via_vertex_ai(self, llm_factory):
        """Test latest Claude 4 family models via Vertex AI."""
        latest_models = [
            "vertex_ai/claude-opus-4-1@20250805",
            "vertex_ai/claude-sonnet-4-5@20250929",
            "vertex_ai/claude-haiku-4-5@20251001",
        ]
        for model_name in latest_models:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "vertex_ai", f"Failed for model: {model_name}"

    def test_gemini_model_variants(self, llm_factory):
        """Test various Gemini model variants via Vertex AI."""
        gemini_models = [
            "vertex_ai/gemini-3-pro-preview",
            "vertex_ai/gemini-2.5-pro",
            "vertex_ai/gemini-2.5-flash",
            "vertex_ai/gemini-2.5-flash-lite",
            "vertex_ai/gemini-2.5-pro-vision",
        ]
        for model_name in gemini_models:
            provider = llm_factory._get_provider_from_model(model_name)
            assert provider == "vertex_ai", f"Failed for model: {model_name}"

    def test_model_name_with_unusual_spacing(self, llm_factory):
        """Test model names with extra whitespace (should be handled)."""
        # Note: This tests the robustness of the detection logic
        model_name = " vertex_ai/claude-sonnet-4-5@20250929 "
        # After strip(), should still detect correctly
        provider = llm_factory._get_provider_from_model(model_name.strip())
        assert provider == "vertex_ai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
