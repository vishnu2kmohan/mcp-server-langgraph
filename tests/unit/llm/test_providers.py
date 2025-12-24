"""
Tests for SUPPORTED_PROVIDERS (Sprint 1)

TDD tests for the LLM provider registry that provides metadata about
all supported LLM providers in the system.

Test Coverage:
- ProviderInfo model validation
- SUPPORTED_PROVIDERS constant contains all providers
- get_provider_info returns correct info for known providers
- get_all_providers returns list of all provider infos
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_llm_providers")
class TestProviderInfoModel:
    """Tests for ProviderInfo model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_provider_info_valid(self) -> None:
        """ProviderInfo should accept valid data."""
        from mcp_server_langgraph.llm.providers import ProviderInfo

        info = ProviderInfo(
            name="anthropic",
            display_name="Anthropic Claude",
            description="Anthropic's Claude AI models",
            supported_model_types=["primary", "summarization", "verification"],
            requires_api_key=True,
            api_key_env_var="ANTHROPIC_API_KEY",
        )

        assert info.name == "anthropic"
        assert info.display_name == "Anthropic Claude"
        assert "primary" in info.supported_model_types
        assert info.requires_api_key is True
        assert info.api_key_env_var == "ANTHROPIC_API_KEY"

    def test_provider_info_no_api_key(self) -> None:
        """ProviderInfo should accept providers without API keys."""
        from mcp_server_langgraph.llm.providers import ProviderInfo

        info = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            description="Local LLM via Ollama",
            supported_model_types=["primary"],
            requires_api_key=False,
            api_key_env_var=None,
        )

        assert info.name == "ollama"
        assert info.requires_api_key is False
        assert info.api_key_env_var is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_llm_providers")
class TestSupportedProviders:
    """Tests for SUPPORTED_PROVIDERS constant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_contains_google(self) -> None:
        """SUPPORTED_PROVIDERS should contain Google."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "google" in SUPPORTED_PROVIDERS
        assert SUPPORTED_PROVIDERS["google"].display_name == "Google Gemini"

    def test_registry_contains_anthropic(self) -> None:
        """SUPPORTED_PROVIDERS should contain Anthropic."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "anthropic" in SUPPORTED_PROVIDERS
        assert SUPPORTED_PROVIDERS["anthropic"].api_key_env_var == "ANTHROPIC_API_KEY"

    def test_registry_contains_openai(self) -> None:
        """SUPPORTED_PROVIDERS should contain OpenAI."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "openai" in SUPPORTED_PROVIDERS
        assert SUPPORTED_PROVIDERS["openai"].api_key_env_var == "OPENAI_API_KEY"

    def test_registry_contains_azure(self) -> None:
        """SUPPORTED_PROVIDERS should contain Azure OpenAI."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "azure" in SUPPORTED_PROVIDERS

    def test_registry_contains_bedrock(self) -> None:
        """SUPPORTED_PROVIDERS should contain AWS Bedrock."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "bedrock" in SUPPORTED_PROVIDERS

    def test_registry_contains_vertex_ai(self) -> None:
        """SUPPORTED_PROVIDERS should contain Vertex AI."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "vertex_ai" in SUPPORTED_PROVIDERS

    def test_registry_contains_ollama(self) -> None:
        """SUPPORTED_PROVIDERS should contain Ollama."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert "ollama" in SUPPORTED_PROVIDERS
        assert SUPPORTED_PROVIDERS["ollama"].requires_api_key is False

    def test_registry_has_at_least_seven_providers(self) -> None:
        """SUPPORTED_PROVIDERS should have at least 7 providers."""
        from mcp_server_langgraph.llm.providers import SUPPORTED_PROVIDERS

        assert len(SUPPORTED_PROVIDERS) >= 7


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_llm_providers")
class TestGetProviderInfo:
    """Tests for get_provider_info helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_provider_info_known(self) -> None:
        """get_provider_info should return info for known provider."""
        from mcp_server_langgraph.llm.providers import get_provider_info

        info = get_provider_info("anthropic")

        assert info is not None
        assert info.name == "anthropic"
        assert info.requires_api_key is True

    def test_get_provider_info_unknown(self) -> None:
        """get_provider_info should return None for unknown provider."""
        from mcp_server_langgraph.llm.providers import get_provider_info

        info = get_provider_info("nonexistent_provider")

        assert info is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_llm_providers")
class TestGetAllProviders:
    """Tests for get_all_providers helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_all_providers_returns_list(self) -> None:
        """get_all_providers should return list of ProviderInfo."""
        from mcp_server_langgraph.llm.providers import ProviderInfo, get_all_providers

        providers = get_all_providers()

        assert isinstance(providers, list)
        assert len(providers) >= 7
        assert all(isinstance(p, ProviderInfo) for p in providers)

    def test_get_all_providers_contains_all_registered(self) -> None:
        """get_all_providers should contain all registered providers."""
        from mcp_server_langgraph.llm.providers import (
            SUPPORTED_PROVIDERS,
            get_all_providers,
        )

        providers = get_all_providers()
        names = {p.name for p in providers}

        for name in SUPPORTED_PROVIDERS:
            assert name in names
