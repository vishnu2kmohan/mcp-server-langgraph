"""
Contract Tests: Hallucination Reporting Frontend-Backend Alignment.

These tests verify that frontend type definitions match backend API schema.
They prevent drift between frontend TypeScript types and backend Python enums.

Frontend Types: src/mcp_server_langgraph/studio/frontend/src/types/api.ts
Backend Types: src/mcp_server_langgraph/api/v1/feedback.py
Component: src/mcp_server_langgraph/studio/frontend/src/components/Chat/HallucinationIndicator.tsx

Contract Alignment (ADR-0091):
- Categories: factual_error, outdated_info, made_up_source, other
- Severity: low, medium, high
- Request fields: message_id, session_id, category, description, severity
"""

import pytest

from mcp_server_langgraph.api.v1.feedback import (
    HallucinationCategory,
    HallucinationReportRequest,
    Severity,
)

pytestmark = pytest.mark.contract


# =============================================================================
# Frontend Constants (Mirror of TypeScript types)
# =============================================================================
# These must match: src/mcp_server_langgraph/studio/frontend/src/types/api.ts
# See: HallucinationCategory, HallucinationSeverity, HallucinationReportRequest

FRONTEND_HALLUCINATION_CATEGORIES = frozenset(
    [
        "factual_error",
        "outdated_info",
        "made_up_source",
        "other",
    ]
)

FRONTEND_SEVERITY_LEVELS = frozenset(
    [
        "low",
        "medium",
        "high",
    ]
)

FRONTEND_REQUEST_FIELDS = frozenset(
    [
        "message_id",
        "session_id",
        "category",
        "description",
        "severity",
    ]
)

# Component categories (HallucinationIndicator.tsx)
# These must match the categoryOptions array in the component
COMPONENT_CATEGORY_IDS = frozenset(
    [
        "factual_error",
        "outdated_info",
        "made_up_source",
        "other",
    ]
)


# =============================================================================
# Contract Tests
# =============================================================================


class TestHallucinationCategoryContract:
    """Verify HallucinationCategory enum matches frontend type."""

    def test_backend_categories_match_frontend(self) -> None:
        """Backend HallucinationCategory values must match frontend type."""
        backend_categories = {member.value for member in HallucinationCategory}
        assert backend_categories == FRONTEND_HALLUCINATION_CATEGORIES, (
            f"Category mismatch! Backend: {backend_categories}, Frontend expects: {FRONTEND_HALLUCINATION_CATEGORIES}"
        )

    def test_backend_categories_match_component(self) -> None:
        """Backend HallucinationCategory values must match component options."""
        backend_categories = {member.value for member in HallucinationCategory}
        assert backend_categories == COMPONENT_CATEGORY_IDS, (
            f"Category mismatch! Backend: {backend_categories}, Component expects: {COMPONENT_CATEGORY_IDS}"
        )

    def test_category_count_matches(self) -> None:
        """Both frontend and backend must have exactly 4 categories."""
        backend_count = len(HallucinationCategory)
        frontend_count = len(FRONTEND_HALLUCINATION_CATEGORIES)
        assert backend_count == frontend_count == 4, (
            f"Category count mismatch! Backend: {backend_count}, Frontend: {frontend_count}, Expected: 4"
        )

    def test_specific_category_values(self) -> None:
        """Verify each specific category value exists in backend."""
        assert HallucinationCategory.FACTUAL_ERROR.value == "factual_error"
        assert HallucinationCategory.OUTDATED_INFO.value == "outdated_info"
        assert HallucinationCategory.MADE_UP_SOURCE.value == "made_up_source"
        assert HallucinationCategory.OTHER.value == "other"


class TestSeverityContract:
    """Verify Severity enum matches frontend type."""

    def test_backend_severity_matches_frontend(self) -> None:
        """Backend Severity values must match frontend HallucinationSeverity type."""
        backend_severity = {member.value for member in Severity}
        assert backend_severity == FRONTEND_SEVERITY_LEVELS, (
            f"Severity mismatch! Backend: {backend_severity}, Frontend expects: {FRONTEND_SEVERITY_LEVELS}"
        )

    def test_severity_count_matches(self) -> None:
        """Both frontend and backend must have exactly 3 severity levels."""
        backend_count = len(Severity)
        frontend_count = len(FRONTEND_SEVERITY_LEVELS)
        assert backend_count == frontend_count == 3, (
            f"Severity count mismatch! Backend: {backend_count}, Frontend: {frontend_count}, Expected: 3"
        )


class TestHallucinationReportRequestContract:
    """Verify HallucinationReportRequest fields match frontend interface."""

    def test_request_fields_match_frontend(self) -> None:
        """Backend request model fields must match frontend interface."""
        # Get all field names from the Pydantic model
        backend_fields = set(HallucinationReportRequest.model_fields.keys())
        assert backend_fields == FRONTEND_REQUEST_FIELDS, (
            f"Field mismatch! Backend: {backend_fields}, Frontend expects: {FRONTEND_REQUEST_FIELDS}"
        )

    def test_required_fields_have_no_defaults(self) -> None:
        """Verify required fields have no defaults (except severity)."""
        model_fields = HallucinationReportRequest.model_fields

        # These fields should be required (no default)
        required_fields = ["message_id", "session_id", "category", "description"]
        for field_name in required_fields:
            field_info = model_fields[field_name]
            assert field_info.is_required(), f"Field {field_name} should be required"

        # severity should have a default
        assert not model_fields["severity"].is_required(), "Field 'severity' should have a default value"

    def test_severity_default_is_medium(self) -> None:
        """Verify severity defaults to 'medium' matching frontend expectation."""
        # This matches the frontend ChatDocument.tsx:776
        # severity: "medium", // Default severity
        default_severity = HallucinationReportRequest.model_fields["severity"].default
        assert default_severity == Severity.MEDIUM, f"Default severity should be 'medium', got: {default_severity}"


class TestFieldNameConventions:
    """Verify field naming follows snake_case convention (ADR-0091)."""

    def test_all_request_fields_are_snake_case(self) -> None:
        """All request fields should use snake_case (API convention)."""
        for field_name in HallucinationReportRequest.model_fields.keys():
            # snake_case means lowercase with underscores, no camelCase
            assert field_name == field_name.lower(), f"Field {field_name} is not lowercase"
            assert " " not in field_name, f"Field {field_name} contains spaces"
            # Heuristic: camelCase would have uppercase after lowercase
            has_camel = any(c.isupper() and i > 0 and field_name[i - 1].islower() for i, c in enumerate(field_name))
            assert not has_camel, f"Field {field_name} appears to be camelCase"


class TestCategoryDescriptions:
    """Verify category descriptions are defined for UI display."""

    def test_all_categories_have_ui_labels(self) -> None:
        """
        Frontend HallucinationIndicator.tsx defines UI labels for each category.
        This test documents the expected mapping.
        """
        # These labels come from HallucinationIndicator.tsx categoryOptions
        expected_labels = {
            "factual_error": "Factual Error",
            "outdated_info": "Outdated Information",
            "made_up_source": "Made Up Source",
            "other": "Other Issue",
        }

        # Verify all backend categories have expected UI labels defined
        for category in HallucinationCategory:
            assert category.value in expected_labels, f"Missing UI label for category: {category.value}"
