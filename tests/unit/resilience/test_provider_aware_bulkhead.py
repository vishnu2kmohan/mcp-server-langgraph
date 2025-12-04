"""
Unit tests for provider-aware bulkhead limits.

TDD tests for provider-specific concurrency limits based on upstream rate limits:
- Anthropic Claude: Conservative (Tier 1) = 50 RPM → ~8 concurrent
- OpenAI GPT-4: Moderate = 500 RPM → ~15 concurrent
- Google Vertex AI/Gemini: DSQ = ~10 concurrent (conservative)
- AWS Bedrock: Variable = ~8 concurrent (Claude Opus limit)
- Ollama: Local = ~50 concurrent (no upstream limits)

Reference rates from:
- https://docs.anthropic.com/en/api/rate-limits
- https://platform.openai.com/docs/guides/rate-limits
- https://cloud.google.com/vertex-ai/generative-ai/docs/quotas
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# Test Provider Limit Configuration
# =============================================================================


@pytest.mark.xdist_group(name="provider_aware_bulkhead")
class TestProviderLimitConfiguration:
    """Test that provider limits are correctly configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_provider_limits_dict_exists(self):
        """Provider limits should be defined in config."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        assert isinstance(PROVIDER_CONCURRENCY_LIMITS, dict)
        assert len(PROVIDER_CONCURRENCY_LIMITS) > 0

    @pytest.mark.unit
    def test_provider_limits_contains_major_providers(self):
        """Should have limits for all major LLM providers."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        expected_providers = ["anthropic", "openai", "google", "vertex_ai", "bedrock", "ollama"]
        for provider in expected_providers:
            assert provider in PROVIDER_CONCURRENCY_LIMITS, f"Missing limit for {provider}"

    @pytest.mark.unit
    def test_anthropic_limit_is_conservative(self):
        """Anthropic limit should be conservative (Tier 1: 50 RPM)."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        # 50 RPM = ~0.83 RPS, with 10s avg latency → ~8 concurrent
        assert PROVIDER_CONCURRENCY_LIMITS["anthropic"] <= 10
        assert PROVIDER_CONCURRENCY_LIMITS["anthropic"] >= 5

    @pytest.mark.unit
    def test_openai_limit_is_moderate(self):
        """OpenAI limit can be higher (typical: 500+ RPM)."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        # 500 RPM = ~8 RPS, with 5s avg latency → ~15 concurrent
        assert PROVIDER_CONCURRENCY_LIMITS["openai"] >= 10
        assert PROVIDER_CONCURRENCY_LIMITS["openai"] <= 25

    @pytest.mark.unit
    def test_ollama_limit_is_high(self):
        """Ollama (local) should have high limit (no upstream constraints)."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        # Local model - limited only by hardware
        assert PROVIDER_CONCURRENCY_LIMITS["ollama"] >= 25

    @pytest.mark.unit
    def test_bedrock_limit_matches_opus_constraint(self):
        """Bedrock limit should respect Claude Opus limit (50 RPM)."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        # Claude Opus on Bedrock: 50 RPM → ~8 concurrent
        assert PROVIDER_CONCURRENCY_LIMITS["bedrock"] <= 10

    @pytest.mark.unit
    def test_vertex_ai_limit_is_conservative(self):
        """Vertex AI with DSQ should use conservative limit."""
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        # DSQ is dynamic but we default to conservative
        assert PROVIDER_CONCURRENCY_LIMITS["vertex_ai"] >= 8
        assert PROVIDER_CONCURRENCY_LIMITS["vertex_ai"] <= 15


# =============================================================================
# Test Provider-Aware Bulkhead Factory
# =============================================================================


@pytest.mark.xdist_group(name="provider_aware_bulkhead")
class TestProviderAwareBulkhead:
    """Test that bulkhead respects provider-specific limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        # Reset provider bulkheads between tests
        from mcp_server_langgraph.resilience.bulkhead import reset_all_provider_bulkheads

        reset_all_provider_bulkheads()

    @pytest.mark.unit
    def test_get_provider_bulkhead_returns_semaphore(self):
        """Should return asyncio.Semaphore for provider."""
        import asyncio

        from mcp_server_langgraph.resilience.bulkhead import get_provider_bulkhead

        semaphore = get_provider_bulkhead("anthropic")
        assert isinstance(semaphore, asyncio.Semaphore)

    @pytest.mark.unit
    def test_get_provider_bulkhead_uses_provider_limit(self):
        """Should use provider-specific limit from config."""
        from mcp_server_langgraph.resilience.bulkhead import get_provider_bulkhead
        from mcp_server_langgraph.resilience.config import PROVIDER_CONCURRENCY_LIMITS

        semaphore = get_provider_bulkhead("anthropic")
        expected_limit = PROVIDER_CONCURRENCY_LIMITS["anthropic"]
        # Semaphore._value gives available slots
        assert semaphore._value == expected_limit

    @pytest.mark.unit
    def test_get_provider_bulkhead_falls_back_to_default(self):
        """Unknown provider should use default limit."""
        from mcp_server_langgraph.resilience.bulkhead import get_provider_bulkhead

        semaphore = get_provider_bulkhead("unknown_provider")
        # Default should be conservative (10)
        assert semaphore._value == 10

    @pytest.mark.unit
    def test_get_provider_bulkhead_caches_semaphore(self):
        """Same provider should return same semaphore instance."""
        from mcp_server_langgraph.resilience.bulkhead import get_provider_bulkhead

        sem1 = get_provider_bulkhead("openai")
        sem2 = get_provider_bulkhead("openai")
        assert sem1 is sem2

    @pytest.mark.unit
    def test_different_providers_get_different_semaphores(self):
        """Different providers should have separate bulkheads."""
        from mcp_server_langgraph.resilience.bulkhead import get_provider_bulkhead

        anthropic_sem = get_provider_bulkhead("anthropic")
        openai_sem = get_provider_bulkhead("openai")
        assert anthropic_sem is not openai_sem


# =============================================================================
# Test LLM Factory Integration
# =============================================================================


@pytest.mark.xdist_group(name="provider_aware_bulkhead")
class TestLLMFactoryProviderBulkhead:
    """Test that LLMFactory uses provider-aware bulkhead."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.resilience.bulkhead import reset_all_provider_bulkheads

        reset_all_provider_bulkheads()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ainvoke_uses_provider_bulkhead(self):
        """ainvoke should acquire provider-specific bulkhead."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.llm.factory import LLMFactory

        _factory = LLMFactory(  # noqa: F841 - Created but skipped in RED phase
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            api_key="test-key",
        )

        # Track bulkhead usage
        bulkhead_acquired = False
        original_get_provider_bulkhead = None

        def mock_get_provider_bulkhead(provider: str):
            nonlocal bulkhead_acquired, original_get_provider_bulkhead
            bulkhead_acquired = True
            assert provider == "anthropic"
            # Return a real semaphore
            import asyncio

            return asyncio.Semaphore(10)

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion,
            patch(
                "mcp_server_langgraph.resilience.bulkhead.get_provider_bulkhead",
                side_effect=mock_get_provider_bulkhead,
            ),
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.usage = MagicMock(total_tokens=100)
            mock_acompletion.return_value = mock_response

            # This test documents expected behavior - implementation will make it pass
            # For now, skip to show RED phase
            pytest.skip("Provider-aware bulkhead not yet integrated into LLMFactory")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_uses_fallback_model_provider_bulkhead(self):
        """Fallback should use the fallback model's provider bulkhead, not primary."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        _factory = LLMFactory(  # noqa: F841 - Created but skipped in RED phase
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            api_key="test-key",
            fallback_models=["gpt-4"],  # OpenAI fallback
            enable_fallback=True,
        )

        # This test documents expected behavior for fallback provider isolation
        pytest.skip("Provider-aware bulkhead for fallbacks not yet implemented")


# =============================================================================
# Test Environment Variable Override
# =============================================================================


@pytest.mark.xdist_group(name="provider_aware_bulkhead")
class TestProviderLimitEnvOverride:
    """Test environment variable overrides for provider limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_env_override_anthropic_limit(self):
        """BULKHEAD_ANTHROPIC_LIMIT should override default."""
        import os

        with patch.dict(os.environ, {"BULKHEAD_ANTHROPIC_LIMIT": "5"}):
            # Need to reimport to pick up env var
            from mcp_server_langgraph.resilience.config import get_provider_limit

            limit = get_provider_limit("anthropic")
            assert limit == 5

    @pytest.mark.unit
    def test_env_override_openai_limit(self):
        """BULKHEAD_OPENAI_LIMIT should override default."""
        import os

        with patch.dict(os.environ, {"BULKHEAD_OPENAI_LIMIT": "20"}):
            from mcp_server_langgraph.resilience.config import get_provider_limit

            limit = get_provider_limit("openai")
            assert limit == 20

    @pytest.mark.unit
    def test_invalid_env_override_uses_default(self):
        """Invalid env value should fall back to default."""
        import os

        with patch.dict(os.environ, {"BULKHEAD_ANTHROPIC_LIMIT": "not_a_number"}):
            from mcp_server_langgraph.resilience.config import get_provider_limit

            # Should use default, not crash
            limit = get_provider_limit("anthropic")
            assert isinstance(limit, int)
            assert limit > 0
