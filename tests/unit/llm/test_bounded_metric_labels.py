"""
Tests for Bounded Metric Labels.

TDD tests to ensure metrics use bounded labels to prevent cardinality explosion:
- model → model_family (bounded)
- workflow_name (bounded, not workflow_id)
- operation (bounded enum)
- status (bounded enum)

Reference: Prometheus best practices for labels
"""

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="bounded_metric_labels"),
]


class TestModelFamilyBoundedLabels:
    """Test that model labels are bounded using model_family."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_model_family_openai_models(self) -> None:
        """
        GIVEN an OpenAI model name
        WHEN get_model_family is called
        THEN it should return a bounded model family name
        """
        from mcp_server_langgraph.llm.metrics import get_model_family

        # GPT-4 variants should all map to "gpt-4"
        assert get_model_family("gpt-4") == "gpt-4"
        assert get_model_family("gpt-4-turbo") == "gpt-4"
        assert get_model_family("gpt-4-turbo-preview") == "gpt-4"
        assert get_model_family("gpt-4o") == "gpt-4o"
        assert get_model_family("gpt-4o-mini") == "gpt-4o"
        assert get_model_family("gpt-4-0613") == "gpt-4"

        # GPT-3.5 variants
        assert get_model_family("gpt-3.5-turbo") == "gpt-3.5"
        assert get_model_family("gpt-3.5-turbo-16k") == "gpt-3.5"

        # GPT-5.x variants
        assert get_model_family("gpt-5.1") == "gpt-5"
        assert get_model_family("gpt-5.1-preview") == "gpt-5"

    def test_get_model_family_anthropic_models(self) -> None:
        """
        GIVEN an Anthropic model name
        WHEN get_model_family is called
        THEN it should return a bounded model family name
        """
        from mcp_server_langgraph.llm.metrics import get_model_family

        # Claude 3 variants
        assert get_model_family("claude-3-opus") == "claude-3-opus"
        assert get_model_family("claude-3-opus-20240229") == "claude-3-opus"
        assert get_model_family("claude-3-sonnet") == "claude-3-sonnet"
        assert get_model_family("claude-3-sonnet-20240229") == "claude-3-sonnet"
        assert get_model_family("claude-3-haiku") == "claude-3-haiku"
        assert get_model_family("claude-3-haiku-20240307") == "claude-3-haiku"

        # Claude 3.5 variants
        assert get_model_family("claude-3-5-sonnet") == "claude-3.5-sonnet"
        assert get_model_family("claude-3-5-sonnet-20241022") == "claude-3.5-sonnet"
        assert get_model_family("claude-3-5-haiku") == "claude-3.5-haiku"

        # Claude 4 variants
        assert get_model_family("claude-sonnet-4-5-20250929") == "claude-4-sonnet"
        assert get_model_family("claude-haiku-4-5-20251001") == "claude-4-haiku"
        assert get_model_family("claude-opus-4-5-20251101") == "claude-4-opus"

    def test_get_model_family_google_models(self) -> None:
        """
        GIVEN a Google model name
        WHEN get_model_family is called
        THEN it should return a bounded model family name
        """
        from mcp_server_langgraph.llm.metrics import get_model_family

        # Gemini variants
        assert get_model_family("gemini-pro") == "gemini-pro"
        assert get_model_family("gemini-1.5-pro") == "gemini-1.5-pro"
        assert get_model_family("gemini-1.5-pro-001") == "gemini-1.5-pro"
        assert get_model_family("gemini-1.5-flash") == "gemini-1.5-flash"
        assert get_model_family("gemini-2.0-flash-exp") == "gemini-2.0-flash"

    def test_get_model_family_unknown_model(self) -> None:
        """
        GIVEN an unknown model name
        WHEN get_model_family is called
        THEN it should return 'other' to maintain bounded cardinality
        """
        from mcp_server_langgraph.llm.metrics import get_model_family

        assert get_model_family("some-random-model") == "other"
        assert get_model_family("custom-fine-tuned-model-v1.2.3") == "other"

    def test_get_model_family_empty_input(self) -> None:
        """
        GIVEN empty or None model name
        WHEN get_model_family is called
        THEN it should return 'unknown'
        """
        from mcp_server_langgraph.llm.metrics import get_model_family

        assert get_model_family("") == "unknown"
        assert get_model_family(None) == "unknown"  # type: ignore[arg-type]


class TestBoundedOperationLabels:
    """Test that operation labels are bounded to known values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bounded_operation_values(self) -> None:
        """
        GIVEN the BOUNDED_OPERATIONS constant
        THEN it should contain only known operation types
        """
        from mcp_server_langgraph.llm.metrics import BOUNDED_OPERATIONS

        # Should be a frozenset for immutability
        assert isinstance(BOUNDED_OPERATIONS, frozenset)

        # Should contain expected operations
        expected = {
            "chat",
            "completion",
            "embedding",
            "streaming",
            "tool_call",
            "function_call",
            "other",
        }
        assert expected == BOUNDED_OPERATIONS

    def test_normalize_operation_known_value(self) -> None:
        """
        GIVEN a known operation name
        WHEN normalize_operation is called
        THEN it should return the same value
        """
        from mcp_server_langgraph.llm.metrics import normalize_operation

        assert normalize_operation("chat") == "chat"
        assert normalize_operation("completion") == "completion"
        assert normalize_operation("embedding") == "embedding"
        assert normalize_operation("streaming") == "streaming"

    def test_normalize_operation_unknown_value(self) -> None:
        """
        GIVEN an unknown operation name
        WHEN normalize_operation is called
        THEN it should return 'other' to maintain bounded cardinality
        """
        from mcp_server_langgraph.llm.metrics import normalize_operation

        assert normalize_operation("custom_operation") == "other"
        assert normalize_operation("foo_bar_baz") == "other"


class TestBoundedStatusLabels:
    """Test that status labels are bounded to known values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bounded_status_values(self) -> None:
        """
        GIVEN the BOUNDED_STATUSES constant
        THEN it should contain only known status types
        """
        from mcp_server_langgraph.llm.metrics import BOUNDED_STATUSES

        # Should be a frozenset for immutability
        assert isinstance(BOUNDED_STATUSES, frozenset)

        # Should contain expected statuses
        expected = {
            "success",
            "error",
            "timeout",
            "rate_limited",
            "cancelled",
            "fallback",
            "other",
        }
        assert expected == BOUNDED_STATUSES

    def test_normalize_status_known_value(self) -> None:
        """
        GIVEN a known status name
        WHEN normalize_status is called
        THEN it should return the same value
        """
        from mcp_server_langgraph.llm.metrics import normalize_status

        assert normalize_status("success") == "success"
        assert normalize_status("error") == "error"
        assert normalize_status("timeout") == "timeout"
        assert normalize_status("rate_limited") == "rate_limited"

    def test_normalize_status_unknown_value(self) -> None:
        """
        GIVEN an unknown status name
        WHEN normalize_status is called
        THEN it should return 'other' to maintain bounded cardinality
        """
        from mcp_server_langgraph.llm.metrics import normalize_status

        assert normalize_status("custom_status") == "other"
        assert normalize_status("foo_bar_baz") == "other"
