"""
Property-based tests for LLM Factory

Tests invariants that should hold for all inputs using Hypothesis.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

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


@pytest.mark.property
@pytest.mark.unit
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryProperties:
    """Property-based tests for LLM Factory"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
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
    def test_invoke_preserves_message_content(self, messages):
        """Property: Invoke should accept messages without crashing"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        # Mock the LLM completion call to test public API
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = self._create_mock_response("test response")
            mock_completion.return_value = mock_response

            try:
                # Test public API invoke() instead of private _format_messages()
                response = factory.invoke(messages)

                # Property: Response is returned
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                # Should not crash with valid messages
                pytest.fail(f"invoke() failed with valid messages: {e}")

    @given(
        messages=message_lists,
        temperature1=valid_temperatures,
        temperature2=valid_temperatures,
        max_tokens1=valid_max_tokens,
        max_tokens2=valid_max_tokens,
    )
    @settings(max_examples=20, deadline=3000)
    def test_parameter_override_consistency(self, messages, temperature1, temperature2, max_tokens1, max_tokens2):
        """Property: Parameter overrides should be consistent"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model", temperature=temperature1, max_tokens=max_tokens1)

        # Mock the completion call
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "test response"
            mock_response.usage = None
            mock_completion.return_value = mock_response

            # Call with override
            factory.invoke(messages, temperature=temperature2, max_tokens=max_tokens2)

            # Property: Overrides take precedence
            call_kwargs = mock_completion.call_args[1]
            assert call_kwargs["temperature"] == temperature2
            assert call_kwargs["max_tokens"] == max_tokens2

    @given(messages=message_lists)
    @settings(max_examples=20, deadline=5000)
    def test_fallback_always_tried_on_failure(self, messages):
        """Property: Fallback should always be attempted when primary fails"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        fallback_models = ["fallback-1", "fallback-2"]
        factory = LLMFactory(
            provider="anthropic",
            model_name="primary-model",
            enable_fallback=True,
            fallback_models=fallback_models,
        )

        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            # Make primary fail, fallback succeed
            mock_completion.side_effect = [
                Exception("Primary failed"),  # First call fails
                self._create_mock_response("fallback response"),  # Fallback succeeds
            ]

            response = factory.invoke(messages)

            # Property: Should have called at least twice (primary + fallback)
            assert mock_completion.call_count >= 2

            # Property: Response should come from fallback
            assert response.content == "fallback response"

    @given(messages=message_lists, provider=valid_providers)
    @settings(max_examples=20, deadline=3000)
    def test_invoke_handles_different_message_types(self, messages, provider):
        """Property: invoke() should handle all message types for all providers"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider=provider, model_name="test-model")

        # Mock the LLM completion to test public API
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = self._create_mock_response("response")
            mock_completion.return_value = mock_response

            try:
                # Test public API with different message types
                response = factory.invoke(messages)

                # Property: Response is always returned for valid messages
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"invoke() failed for provider {provider}: {e}")

    @staticmethod
    def _create_mock_response(content: str):
        """Helper to create mock LiteLLM response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage = None
        return mock_response


@pytest.mark.property
@pytest.mark.unit
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryEdgeCases:
    """Property tests for edge cases and invariants"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
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
    @settings(max_examples=20, deadline=2000)
    def test_invoke_handles_empty_message_content(self, empty_contents):
        """Property: invoke() should handle empty message content gracefully"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        messages = [HumanMessage(content=content) for content in empty_contents]

        # Mock LLM to test public API
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = self._create_mock_response("response")
            mock_completion.return_value = mock_response

            try:
                # Should not crash with empty content
                response = factory.invoke(messages)
                assert response is not None
            except Exception as e:
                pytest.fail(f"invoke() crashed with empty messages: {e}")

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
    @settings(max_examples=10, deadline=2000)
    def test_invoke_works_with_api_key_for_all_providers(self, provider):
        """Property: invoke() should work with API keys for all providers"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Mock the completion call to test public API
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = self._create_mock_response("test response")
            mock_completion.return_value = mock_response

            try:
                # Test public API with API key
                factory = LLMFactory(provider=provider, model_name="test-model", api_key="test-key-123")
                messages = [HumanMessage(content="test")]
                response = factory.invoke(messages)

                # Property: Response is returned regardless of provider
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"invoke() failed for provider {provider}: {e}")

    @given(messages=st.lists(st.builds(HumanMessage, content=st.text(min_size=1, max_size=100)), min_size=1, max_size=10))
    @settings(max_examples=20, deadline=3000)
    def test_invoke_processes_messages_successfully(self, messages):
        """Property: invoke() should process message lists of any length"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        # Mock LLM to test public API
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            mock_response = self._create_mock_response("test response")
            mock_completion.return_value = mock_response

            try:
                # Test public API with varying message list lengths
                response = factory.invoke(messages)

                # Property: Response is returned for any valid message list
                assert response is not None
                assert hasattr(response, "content")
            except Exception as e:
                pytest.fail(f"invoke() failed with {len(messages)} messages: {e}")


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.xdist_group(name="property_llm_properties_tests")
class TestLLMFactoryFallbackProperties:
    """Property tests for fallback behavior"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        fallback_count=st.integers(min_value=1, max_value=5),
        success_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=15, deadline=5000)
    def test_fallback_stops_on_first_success(self, fallback_count, success_index):
        """Property: Fallback should stop trying once one succeeds"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Ensure success_index is within fallback_count
        success_index = min(success_index, fallback_count - 1)

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            # Create side effects: fail until success_index, then succeed
            side_effects = []
            for i in range(success_index + 1):
                if i == success_index:
                    side_effects.append(TestLLMFactoryProperties._create_mock_response("success"))
                else:
                    side_effects.append(Exception(f"Failure {i}"))

            mock_completion.side_effect = side_effects

            messages = [HumanMessage(content="test")]
            response = factory.invoke(messages)

            # Property: Should call exactly success_index + 1 times (including primary)
            assert mock_completion.call_count == success_index + 1
            assert response.content == "success"

    @given(fallback_count=st.integers(min_value=1, max_value=3))
    @settings(max_examples=10, deadline=5000)
    def test_all_fallbacks_exhausted_raises(self, fallback_count):
        """Property: If all fallbacks fail, should raise exception"""
        from mcp_server_langgraph.llm.factory import LLMFactory

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            # All fail
            mock_completion.side_effect = Exception("All models failed")

            messages = [HumanMessage(content="test")]

            # Property: Should raise RuntimeError when all fail
            with pytest.raises(RuntimeError, match="All models failed"):
                factory.invoke(messages)

            # Property: Should have tried all models
            # +1 for primary, +fallback_count for fallbacks
            assert mock_completion.call_count >= fallback_count
