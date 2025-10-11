"""
Property-based tests for LLM Factory

Tests invariants that should hold for all inputs using Hypothesis.
"""

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
class TestLLMFactoryProperties:
    """Property-based tests for LLM Factory"""

    @given(provider=valid_providers, temperature=valid_temperatures, max_tokens=valid_max_tokens)
    @settings(max_examples=50, deadline=3000)
    def test_factory_creation_never_crashes(self, provider, temperature, max_tokens):
        """Property: Factory creation should never crash with valid inputs"""
        from llm_factory import LLMFactory

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
    def test_message_format_preserves_content(self, messages):
        """Property: Message format conversion should preserve content"""
        from llm_factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        formatted = factory._format_messages(messages)

        # Property: Same number of messages
        assert len(formatted) == len(messages)

        # Property: Content is preserved
        for original, formatted_msg in zip(messages, formatted):
            assert formatted_msg["content"] == original.content

        # Property: All messages have required fields
        for msg in formatted:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["user", "assistant", "system"]

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
        from llm_factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model", temperature=temperature1, max_tokens=max_tokens1)

        # Mock the completion call
        with patch("llm_factory.completion") as mock_completion:
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
        from llm_factory import LLMFactory

        fallback_models = ["fallback-1", "fallback-2"]
        factory = LLMFactory(
            provider="anthropic",
            model_name="primary-model",
            enable_fallback=True,
            fallback_models=fallback_models,
        )

        with patch("llm_factory.completion") as mock_completion:
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
    def test_message_type_mapping_is_reversible(self, messages, provider):
        """Property: Message type mapping should be consistent across providers"""
        from llm_factory import LLMFactory

        factory = LLMFactory(provider=provider, model_name="test-model")

        formatted = factory._format_messages(messages)

        # Property: Role mapping is consistent
        role_mapping = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}

        for original, formatted_msg in zip(messages, formatted):
            original_type = type(original).__name__
            expected_role = {
                "HumanMessage": "user",
                "AIMessage": "assistant",
                "SystemMessage": "system",
            }.get(original_type, "user")

            assert formatted_msg["role"] == expected_role

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
class TestLLMFactoryEdgeCases:
    """Property tests for edge cases and invariants"""

    @given(st.lists(st.text(min_size=0, max_size=0), min_size=1, max_size=5))
    @settings(max_examples=20, deadline=2000)
    def test_empty_message_content_handled(self, empty_contents):
        """Property: Empty messages should not crash"""
        from llm_factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        messages = [HumanMessage(content=content) for content in empty_contents]

        # Should not crash
        formatted = factory._format_messages(messages)
        assert len(formatted) == len(messages)

    @given(
        temperature=st.one_of(
            st.floats(min_value=-10.0, max_value=-0.01),  # Negative
            st.floats(min_value=2.01, max_value=10.0),  # Too high
        )
    )
    @settings(max_examples=20, deadline=2000)
    def test_invalid_temperature_outside_range(self, temperature):
        """Property: Factory should handle out-of-range temperatures gracefully"""
        from llm_factory import LLMFactory

        # Should create factory (LiteLLM may clamp or reject later)
        factory = LLMFactory(provider="anthropic", model_name="test-model", temperature=temperature)

        # Property: Temperature is stored as-is (validation happens at LLM level)
        assert factory.temperature == temperature

    @given(provider=valid_providers)
    @settings(max_examples=10, deadline=2000)
    def test_environment_variables_set_consistently(self, provider):
        """Property: Environment variables should be set based on provider"""
        import os

        from llm_factory import LLMFactory

        # Clear any existing keys
        env_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "AZURE_API_KEY"]
        original_values = {k: os.environ.get(k) for k in env_vars}

        try:
            factory = LLMFactory(provider=provider, model_name="test-model", api_key="test-key-123")

            factory._setup_environment()

            # Property: Correct env var should be set for provider
            if provider == "anthropic":
                assert os.environ.get("ANTHROPIC_API_KEY") == "test-key-123"
            elif provider in ["openai", "ollama"]:
                # Ollama uses OpenAI format, so might not set env var
                pass  # Optional
            elif provider in ["google", "gemini"]:
                assert os.environ.get("GOOGLE_API_KEY") == "test-key-123"

        finally:
            # Restore original values
            for k, v in original_values.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    @given(messages=st.lists(st.builds(HumanMessage, content=st.text(min_size=1, max_size=100)), min_size=1, max_size=10))
    @settings(max_examples=20, deadline=3000)
    def test_message_order_preserved(self, messages):
        """Property: Message order must be preserved through formatting"""
        from llm_factory import LLMFactory

        factory = LLMFactory(provider="anthropic", model_name="test-model")

        formatted = factory._format_messages(messages)

        # Property: Order is preserved
        for i, (original, formatted_msg) in enumerate(zip(messages, formatted)):
            assert formatted_msg["content"] == original.content, f"Order broken at index {i}"


@pytest.mark.property
@pytest.mark.integration
class TestLLMFactoryFallbackProperties:
    """Property tests for fallback behavior"""

    @given(
        fallback_count=st.integers(min_value=1, max_value=5),
        success_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=15, deadline=5000)
    def test_fallback_stops_on_first_success(self, fallback_count, success_index):
        """Property: Fallback should stop trying once one succeeds"""
        from llm_factory import LLMFactory

        # Ensure success_index is within fallback_count
        success_index = min(success_index, fallback_count - 1)

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("llm_factory.completion") as mock_completion:
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
        from llm_factory import LLMFactory

        fallback_models = [f"fallback-{i}" for i in range(fallback_count)]

        factory = LLMFactory(provider="anthropic", model_name="primary", enable_fallback=True, fallback_models=fallback_models)

        with patch("llm_factory.completion") as mock_completion:
            # All fail
            mock_completion.side_effect = Exception("All models failed")

            messages = [HumanMessage(content="test")]

            # Property: Should raise RuntimeError when all fail
            with pytest.raises(RuntimeError, match="All models failed"):
                factory.invoke(messages)

            # Property: Should have tried all models
            # +1 for primary, +fallback_count for fallbacks
            assert mock_completion.call_count >= fallback_count
