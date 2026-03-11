"""
Contract test to ensure FeedbackSummaryResponse types align between frontend and backend.

This test prevents drift between:
- Backend: api/v1/feedback.py FeedbackSummaryResponse
- Frontend: types/api.ts FeedbackSummaryResponse

The frontend uses camelCase (via RTK Query transformation) while
backend uses snake_case. This test verifies field alignment.
"""

import pytest

from mcp_server_langgraph.api.v1.feedback import (
    FeedbackSummaryResponse,
    HallucinationCategoryCounts,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

# Frontend expected fields (from types/api.ts)
# Note: Frontend uses snake_case in types, transformed to camelCase at runtime
FRONTEND_FEEDBACK_SUMMARY_FIELDS = {
    "timeframe",
    "total_feedback",
    "positive_count",
    "negative_count",
    "positive_rate",
    "hallucination_reports",
    "hallucination_categories",
}

FRONTEND_HALLUCINATION_CATEGORY_FIELDS = {
    "factual_error",
    "outdated_info",
    "made_up_source",
    "other",
}


@pytest.mark.xdist_group("test_feedback_summary_frontend_contract")
@pytest.mark.contract
class TestFeedbackSummaryFrontendContract:
    """Contract tests for FeedbackSummaryResponse alignment."""

    def test_feedback_summary_response_has_all_frontend_fields(self) -> None:
        """
        Verify backend FeedbackSummaryResponse has all fields expected by frontend.

        Frontend types/api.ts defines FeedbackSummaryResponse interface.
        This test ensures the backend model includes all those fields.
        """
        backend_fields = set(FeedbackSummaryResponse.model_fields.keys())

        missing = FRONTEND_FEEDBACK_SUMMARY_FIELDS - backend_fields
        assert not missing, (
            f"Frontend expects these fields but backend FeedbackSummaryResponse is missing them:\n"
            f"  {sorted(missing)}\n\n"
            f"Backend has: {sorted(backend_fields)}\n"
            f"Frontend expects: {sorted(FRONTEND_FEEDBACK_SUMMARY_FIELDS)}\n\n"
            f"Fix: Add missing fields to FeedbackSummaryResponse in api/v1/feedback.py"
        )

    def test_hallucination_category_counts_has_all_frontend_fields(self) -> None:
        """
        Verify HallucinationCategoryCounts has all category fields expected by frontend.

        The frontend AIQualityMetricsCard component expects these categories:
        - factual_error (displayed as "Factual Error")
        - outdated_info (displayed as "Outdated Info")
        - made_up_source (displayed as "Made Up Source")
        - other (displayed as "Other")
        """
        backend_fields = set(HallucinationCategoryCounts.model_fields.keys())

        missing = FRONTEND_HALLUCINATION_CATEGORY_FIELDS - backend_fields
        assert not missing, (
            f"Frontend expects these category fields but backend is missing them:\n"
            f"  {sorted(missing)}\n\n"
            f"Backend has: {sorted(backend_fields)}\n"
            f"Frontend expects: {sorted(FRONTEND_HALLUCINATION_CATEGORY_FIELDS)}\n\n"
            f"Fix: Add missing fields to HallucinationCategoryCounts in api/v1/feedback.py"
        )

    def test_no_extra_backend_fields_not_in_frontend(self) -> None:
        """
        Warn if backend has fields that frontend doesn't expect.

        Extra fields aren't breaking (they're just ignored), but indicate
        potential missed opportunities for frontend features.
        """
        backend_fields = set(FeedbackSummaryResponse.model_fields.keys())
        extra = backend_fields - FRONTEND_FEEDBACK_SUMMARY_FIELDS

        # Not a failure, just informational - extra fields are fine
        if extra:
            pytest.skip(
                f"Backend has extra fields not used by frontend: {sorted(extra)}. "
                f"Consider adding these to frontend types if useful."
            )

    def test_field_types_are_serializable(self) -> None:
        """
        Verify all fields can be JSON serialized for API response.

        RTK Query expects JSON-serializable responses.
        """
        # Create a sample response with all fields populated
        response = FeedbackSummaryResponse(
            timeframe="7d",
            total_feedback=100,
            positive_count=80,
            negative_count=20,
            positive_rate=0.8,
            hallucination_reports=5,
            hallucination_categories=HallucinationCategoryCounts(
                factual_error=2,
                outdated_info=1,
                made_up_source=1,
                other=1,
            ),
        )

        # Should not raise - model_dump_json handles serialization
        json_str = response.model_dump_json()
        assert json_str is not None
        assert "timeframe" in json_str
        assert "hallucination_categories" in json_str

    def test_hallucination_categories_default_to_zero(self) -> None:
        """
        Verify category counts default to 0 when not provided.

        Frontend AIQualityMetricsCard expects valid numbers for all categories.
        """
        categories = HallucinationCategoryCounts()

        assert categories.factual_error == 0
        assert categories.outdated_info == 0
        assert categories.made_up_source == 0
        assert categories.other == 0

    def test_positive_rate_is_float_between_0_and_1(self) -> None:
        """
        Verify positive_rate is a float that frontend can use directly.

        Frontend displays this as percentage: Math.round(positiveRate * 100)
        """
        response = FeedbackSummaryResponse(
            timeframe="7d",
            positive_rate=0.85,
        )

        assert isinstance(response.positive_rate, float)
        assert 0.0 <= response.positive_rate <= 1.0

    def test_snake_case_field_naming_convention(self) -> None:
        """
        Verify backend uses snake_case (frontend transforms to camelCase).

        Convention: Backend uses snake_case, frontend types/api.ts mirrors this,
        RTK Query transformSnakeToCamel converts at runtime.
        """
        backend_fields = set(FeedbackSummaryResponse.model_fields.keys())

        # All field names should be snake_case (contain underscore or be single word)
        camel_case_fields = [
            f
            for f in backend_fields
            if any(c.isupper() for c in f)  # Contains uppercase = camelCase
        ]

        assert not camel_case_fields, (
            f"Backend fields should be snake_case, found camelCase: {camel_case_fields}\n"
            f"RTK Query transforms snake_case to camelCase at runtime."
        )

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
