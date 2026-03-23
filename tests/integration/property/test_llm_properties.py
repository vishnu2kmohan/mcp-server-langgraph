"""
Property-based tests for LLM Factory (async ainvoke API)

Tests invariants that should hold for all inputs using Hypothesis.

Migrated from sync invoke() to async ainvoke() after LLM Factory
was migrated to async-only. See: tests/unit/llm/test_factory_async_only.py
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.property,
]

# Hypothesis strategies
valid_providers = st.sampled_from(["anthropic", "openai", "google", "gemini", "azure", "bedrock", "ollama"])

valid_temperatures = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)

valid_max_tokens = st.integers(min_value=1, max_value=100000)

valid_timeouts = st.integers(min_value=1, max_value=600)

# Message content strategy - realistic user inputs
message_content = st.text(min_size=1, max_size=10000)

# List of messages strategy
message_lists = st.lists(
    st.one_of(
        st.builds(HumanMessage, content=message_content),
        st.builds(AIMessage, content=message_content),
        st.builds(SystemMessage, content=message_content),
    ),
    min_size=1,
    max_size=20,
)


@pytest.mark.unit
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryProperties:
    """Property-based tests for LLM Factory"""

    def teardown_method(self):
        """Force GC and reset circuit breakers to prevent state leakage in xdist workers"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        gc.collect()

    @given(provider=valid_providers, temperature=valid_temperatures, max_tokens=valid_max_tokens)
    @settings(max_examples=50, deadline=3000)
    def test_factory_creation_never_crashes(self, provider, temperature, max_tokens):
        """Property: Factory creation should never crash with valid inputs"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        try:
            factory = LLMFactory(
                provider=provider, model_name="test-model", temperature=temperature, max_tokens=max_tokens, timeout=60
            )
            assert factory is not None
            assert factory.provider == provider
            assert factory.temperature == temperature
            assert factory.max_tokens == max_tokens
        except Exception as e:
            # Should not raise for valid inputs
            pytest.fail(f"Factory creation failed with valid inputs: {e}")

    @given(messages=message_lists)
    @settings(max_examples=30, deadline=5000)
    async def test_ainvoke_preserves_message_content(self, messages):
        """Property: ainvoke should accept messages without crashing"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("test response")
            mock_acompletion.return_value = mock_response

            try:
                response = await factory.ainvoke(messages)

                # Property: Response is returned as AIMessage
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                # Should not crash with valid messages
                pytest.fail(f"ainvoke() failed with valid messages: {e}")

    @given(
        messages=message_lists,
        temperature1=valid_temperatures,
        temperature2=valid_temperatures,
        max_tokens1=valid_max_tokens,
        max_tokens2=valid_max_tokens,
    )
    @settings(max_examples=20, deadline=5000)
    async def test_parameter_override_consistency(self, messages, temperature1, temperature2, max_tokens1, max_tokens2):
        """Property: Parameter overrides should be consistent"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model", temperature=temperature1, max_tokens=max_tokens1)

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("test response")
            mock_acompletion.return_value = mock_response

            # Call with override
            await factory.ainvoke(messages, temperature=temperature2, max_tokens=max_tokens2)

            # Property: Overrides take precedence
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["temperature"] == temperature2
            assert call_kwargs["max_tokens"] == max_tokens2

    @given(messages=message_lists)
    @settings(max_examples=20, deadline=5000)
    async def test_fallback_always_tried_on_failure(self, messages):
        """Property: Fallback should always be attempted when primary fails"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()

        from mcp_server_langgraph.llm.factory import LLMFactory

        fallback_models = ["fallback-1", "fallback-2"]
        factory = LLMFactory(
            provider="anthropic",
            model_name="primary-model",
            enable_fallback=True,
            fallback_models=fallback_models,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            # Make primary fail, fallback succeed
            mock_acompletion.side_effect = [
                Exception("Primary failed"),  # First call fails
                self._create_mock_response("fallback response"),  # Fallback succeeds
            ]

            response = await factory.ainvoke(messages)

            # Property: Should have called at least twice (primary + fallback)
            assert mock_acompletion.call_count >= 2

            # Property: Response should come from fallback
            assert response.content == "fallback response"

    @given(messages=message_lists, provider=valid_providers)
    @settings(max_examples=20, deadline=5000)
    async def test_ainvoke_handles_different_message_types(self, messages, provider):
        """Property: ainvoke() should handle all message types for all providers"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider=provider, model_name="test-model")

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("response")
            mock_acompletion.return_value = mock_response

            try:
                response = await factory.ainvoke(messages)

                # Property: Response is always returned for valid messages
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"ainvoke() failed for provider {provider}: {e}")

    @staticmethod
    def _create_mock_response(content: str):
        """Helper to create mock LiteLLM response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage = None
        return mock_response


@pytest.mark.unit
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryEdgeCases:
    """Property tests for edge cases and invariants"""

    def teardown_method(self):
        """Force GC and reset circuit breakers to prevent state leakage in xdist workers"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        gc.collect()

    @staticmethod
    def _create_mock_response(content: str):
        """Helper to create mock LiteLLM response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage = None
        return mock_response

    @given(st.lists(st.text(min_size=0, max_size=0), min_size=1, max_size=5))
    @settings(max_examples=20, deadline=5000)
    async def test_ainvoke_handles_empty_message_content(self, empty_contents):
        """Property: ainvoke() should handle empty message content gracefully"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        messages = [HumanMessage(content=content) for content in empty_contents]

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("response")
            mock_acompletion.return_value = mock_response

            try:
                response = await factory.ainvoke(messages)
                assert response is not None
            except Exception as e:
                pytest.fail(f"ainvoke() crashed with empty messages: {e}")

    @given(
        temperature=st.one_of(
            st.floats(min_value=-10.0, max_value=-0.01),  # Negative
            st.floats(min_value=2.01, max_value=10.0),  # Too high
        )
    )
    @settings(max_examples=20, deadline=2000)
    def test_invalid_temperature_outside_range(self, temperature):
        """Property: Factory should handle out-of-range temperatures gracefully"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Should create factory (LiteLLM may clamp or reject later)
        factory = LLMFactory(provider="anthropic", model_name="test-model", temperature=temperature)

        # Property: Temperature is stored as-is (validation happens at LLM level)
        assert factory.temperature == temperature

    @given(provider=valid_providers)
    @settings(max_examples=10, deadline=5000)
    async def test_ainvoke_works_with_api_key_for_all_providers(self, provider):
        """Property: ainvoke() should work with API keys for all providers"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("test response")
            mock_acompletion.return_value = mock_response

            try:
                factory = LLMFactory(provider=provider, model_name="test-model", api_key="test-key-123")
                messages = [HumanMessage(content="test")]
                response = await factory.ainvoke(messages)

                # Property: Response is returned regardless of provider
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"ainvoke() failed for provider {provider}: {e}")

    @given(messages=st.lists(st.builds(HumanMessage, content=st.text(min_size=1, max_size=100)), min_size=1, max_size=10))
    @settings(max_examples=20, deadline=5000)
    async def test_ainvoke_processes_messages_successfully(self, messages):
        """Property: ainvoke() should process message lists of any length"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_response = self._create_mock_response("test response")
            mock_acompletion.return_value = mock_response

            try:
                response = await factory.ainvoke(messages)

                # Property: Response is returned for any valid message list
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"ainvoke() failed with {len(messages)} messages: {e}")


@pytest.mark.integration
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryFallbackProperties:
    """Property tests for fallback behavior"""

    def teardown_method(self):
        """Force GC and reset circuit breakers to prevent state leakage in xdist workers"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        gc.collect()

    @given(
        fallback_count=st.integers(min_value=1, max_value=5),
        success_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=15, deadline=5000)
    async def test_fallback_stops_on_first_success(self, fallback_count, success_index):
        """Property: Fallback should stop trying once one succeeds"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()

        from mcp_server_langgraph.llm.factory import LLMFactory

        # Ensure success_index is within fallback_count
        success_index = min(success_index, fallback_count - 1)

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            # Create side effects: fail until success_index, then succeed
            side_effects = []
            for i in range(success_index + 1):
                if i == success_index:
                    side_effects.append(TestLLMFactoryProperties._create_mock_response("success"))
                else:
                    side_effects.append(Exception(f"Failure {i}"))

            mock_acompletion.side_effect = side_effects

            messages = [HumanMessage(content="test")]
            response = await factory.ainvoke(messages)

            # Property: Should call exactly success_index + 1 times (including primary)
            assert mock_acompletion.call_count == success_index + 1
            assert response.content == "success"

    @given(fallback_count=st.integers(min_value=1, max_value=3))
    @settings(max_examples=10, deadline=5000)
    async def test_all_fallbacks_exhausted_raises(self, fallback_count):
        """Property: If all fallbacks fail, should raise exception"""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()

        from mcp_server_langgraph.llm.factory import LLMFactory

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            # All fail
            mock_acompletion.side_effect = Exception("All models failed")

            messages = [HumanMessage(content="test")]

            # Property: Should raise RuntimeError when all fail
            # ainvoke catches the primary error, tries fallback via _try_fallback_async,
            # which raises RuntimeError("All async models failed including fallbacks")
            with pytest.raises(RuntimeError, match="All.*models failed"):
                await factory.ainvoke(messages)

            # Property: Should have tried all models
            # +1 for primary, +fallback_count for fallbacks
            assert mock_acompletion.call_count >= fallback_count
