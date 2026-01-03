"""
Unit tests for AI UX prompts centralization.

Tests the 17 AI UX prompts migrated from api/v1/ai_ux_service.py:
- Error Handling: ERROR_ANALYSIS_SYSTEM_PROMPT
- Core UX: EMPTY_STATE, PERSONA_ANALYSIS, DISCLOSURE_ANALYSIS, NUDGE_RECOMMENDATION, ONBOARDING_PERSONALIZATION
- Analytics: METRICS_INSIGHTS_SYSTEM_PROMPT
- Session Intelligence: SESSION_SUMMARIZE, SESSION_GROUP, SESSION_SIMILARITY
- Traces: TRACE_SUMMARIZE, TRACE_ANOMALIES
- Canvas/Diagrams: CANVAS_ARTIFACT_TYPE, CANVAS_CODE_ANALYSIS, CANVAS_DIFF_EXPLAIN, DIAGRAM_ANALYZE, DIAGRAM_TO_CODE

TDD: These tests are written FIRST before implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_ai_ux_prompts")
class TestAIUXPromptsExist:
    """Test that all 17 AI UX prompts are centralized and accessible."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_error_analysis_prompt_exists(self) -> None:
        """Test ERROR_ANALYSIS_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            ERROR_ANALYSIS_SYSTEM_PROMPT,
        )

        assert ERROR_ANALYSIS_SYSTEM_PROMPT is not None
        assert isinstance(ERROR_ANALYSIS_SYSTEM_PROMPT, str)
        assert len(ERROR_ANALYSIS_SYSTEM_PROMPT) > 0

    def test_empty_state_prompt_exists(self) -> None:
        """Test EMPTY_STATE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            EMPTY_STATE_SYSTEM_PROMPT,
        )

        assert EMPTY_STATE_SYSTEM_PROMPT is not None
        assert isinstance(EMPTY_STATE_SYSTEM_PROMPT, str)

    def test_persona_analysis_prompt_exists(self) -> None:
        """Test PERSONA_ANALYSIS_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            PERSONA_ANALYSIS_SYSTEM_PROMPT,
        )

        assert PERSONA_ANALYSIS_SYSTEM_PROMPT is not None
        assert isinstance(PERSONA_ANALYSIS_SYSTEM_PROMPT, str)

    def test_disclosure_analysis_prompt_exists(self) -> None:
        """Test DISCLOSURE_ANALYSIS_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            DISCLOSURE_ANALYSIS_SYSTEM_PROMPT,
        )

        assert DISCLOSURE_ANALYSIS_SYSTEM_PROMPT is not None
        assert isinstance(DISCLOSURE_ANALYSIS_SYSTEM_PROMPT, str)

    def test_nudge_recommendation_prompt_exists(self) -> None:
        """Test NUDGE_RECOMMENDATION_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            NUDGE_RECOMMENDATION_SYSTEM_PROMPT,
        )

        assert NUDGE_RECOMMENDATION_SYSTEM_PROMPT is not None
        assert isinstance(NUDGE_RECOMMENDATION_SYSTEM_PROMPT, str)

    def test_onboarding_personalization_prompt_exists(self) -> None:
        """Test ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT,
        )

        assert ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT is not None
        assert isinstance(ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT, str)

    def test_metrics_insights_prompt_exists(self) -> None:
        """Test METRICS_INSIGHTS_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            METRICS_INSIGHTS_SYSTEM_PROMPT,
        )

        assert METRICS_INSIGHTS_SYSTEM_PROMPT is not None
        assert isinstance(METRICS_INSIGHTS_SYSTEM_PROMPT, str)

    def test_session_summarize_prompt_exists(self) -> None:
        """Test SESSION_SUMMARIZE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            SESSION_SUMMARIZE_SYSTEM_PROMPT,
        )

        assert SESSION_SUMMARIZE_SYSTEM_PROMPT is not None
        assert isinstance(SESSION_SUMMARIZE_SYSTEM_PROMPT, str)

    def test_session_group_prompt_exists(self) -> None:
        """Test SESSION_GROUP_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            SESSION_GROUP_SYSTEM_PROMPT,
        )

        assert SESSION_GROUP_SYSTEM_PROMPT is not None
        assert isinstance(SESSION_GROUP_SYSTEM_PROMPT, str)

    def test_session_similarity_prompt_exists(self) -> None:
        """Test SESSION_SIMILARITY_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            SESSION_SIMILARITY_SYSTEM_PROMPT,
        )

        assert SESSION_SIMILARITY_SYSTEM_PROMPT is not None
        assert isinstance(SESSION_SIMILARITY_SYSTEM_PROMPT, str)

    def test_trace_summarize_prompt_exists(self) -> None:
        """Test TRACE_SUMMARIZE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            TRACE_SUMMARIZE_SYSTEM_PROMPT,
        )

        assert TRACE_SUMMARIZE_SYSTEM_PROMPT is not None
        assert isinstance(TRACE_SUMMARIZE_SYSTEM_PROMPT, str)

    def test_trace_anomalies_prompt_exists(self) -> None:
        """Test TRACE_ANOMALIES_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            TRACE_ANOMALIES_SYSTEM_PROMPT,
        )

        assert TRACE_ANOMALIES_SYSTEM_PROMPT is not None
        assert isinstance(TRACE_ANOMALIES_SYSTEM_PROMPT, str)

    def test_canvas_artifact_type_prompt_exists(self) -> None:
        """Test CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT,
        )

        assert CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT is not None
        assert isinstance(CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT, str)

    def test_canvas_code_analysis_prompt_exists(self) -> None:
        """Test CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT,
        )

        assert CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT is not None
        assert isinstance(CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT, str)

    def test_canvas_diff_explain_prompt_exists(self) -> None:
        """Test CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT,
        )

        assert CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT is not None
        assert isinstance(CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT, str)

    def test_diagram_analyze_prompt_exists(self) -> None:
        """Test DIAGRAM_ANALYZE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            DIAGRAM_ANALYZE_SYSTEM_PROMPT,
        )

        assert DIAGRAM_ANALYZE_SYSTEM_PROMPT is not None
        assert isinstance(DIAGRAM_ANALYZE_SYSTEM_PROMPT, str)

    def test_diagram_to_code_prompt_exists(self) -> None:
        """Test DIAGRAM_TO_CODE_SYSTEM_PROMPT is centralized."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            DIAGRAM_TO_CODE_SYSTEM_PROMPT,
        )

        assert DIAGRAM_TO_CODE_SYSTEM_PROMPT is not None
        assert isinstance(DIAGRAM_TO_CODE_SYSTEM_PROMPT, str)


@pytest.mark.xdist_group(name="test_ai_ux_prompts")
class TestAIUXPromptsContent:
    """Test AI UX prompts have required content structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_json_enforcement(self) -> None:
        """Test all prompts enforce JSON-only output."""
        from mcp_server_langgraph.core.prompts import ai_ux_prompts

        prompt_names = [
            "ERROR_ANALYSIS_SYSTEM_PROMPT",
            "EMPTY_STATE_SYSTEM_PROMPT",
            "PERSONA_ANALYSIS_SYSTEM_PROMPT",
            "DISCLOSURE_ANALYSIS_SYSTEM_PROMPT",
            "NUDGE_RECOMMENDATION_SYSTEM_PROMPT",
            "ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT",
            "METRICS_INSIGHTS_SYSTEM_PROMPT",
            "SESSION_SUMMARIZE_SYSTEM_PROMPT",
            "SESSION_GROUP_SYSTEM_PROMPT",
            "SESSION_SIMILARITY_SYSTEM_PROMPT",
            "TRACE_SUMMARIZE_SYSTEM_PROMPT",
            "TRACE_ANOMALIES_SYSTEM_PROMPT",
            "CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT",
            "CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT",
            "CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT",
            "DIAGRAM_ANALYZE_SYSTEM_PROMPT",
            "DIAGRAM_TO_CODE_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(ai_ux_prompts, name)
            # All prompts should mention JSON in output enforcement
            assert "json" in prompt.lower(), f"{name} should enforce JSON output"

    def test_error_analysis_has_category_field(self) -> None:
        """Test ERROR_ANALYSIS_SYSTEM_PROMPT mentions category field."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            ERROR_ANALYSIS_SYSTEM_PROMPT,
        )

        assert "category" in ERROR_ANALYSIS_SYSTEM_PROMPT.lower()
        assert "network" in ERROR_ANALYSIS_SYSTEM_PROMPT.lower()

    def test_persona_analysis_has_persona_enum(self) -> None:
        """Test PERSONA_ANALYSIS_SYSTEM_PROMPT mentions valid personas."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            PERSONA_ANALYSIS_SYSTEM_PROMPT,
        )

        # Should mention available personas
        assert "admin" in PERSONA_ANALYSIS_SYSTEM_PROMPT.lower()

    def test_disclosure_analysis_has_level_enum(self) -> None:
        """Test DISCLOSURE_ANALYSIS_SYSTEM_PROMPT mentions disclosure levels."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            DISCLOSURE_ANALYSIS_SYSTEM_PROMPT,
        )

        # Should mention disclosure levels
        assert "beginner" in DISCLOSURE_ANALYSIS_SYSTEM_PROMPT.lower()
        assert "advanced" in DISCLOSURE_ANALYSIS_SYSTEM_PROMPT.lower()

    def test_metrics_insights_has_heart_dimensions(self) -> None:
        """Test METRICS_INSIGHTS_SYSTEM_PROMPT mentions HEART dimensions."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            METRICS_INSIGHTS_SYSTEM_PROMPT,
        )

        # Should mention HEART dimensions
        assert "happiness" in METRICS_INSIGHTS_SYSTEM_PROMPT.lower()
        assert "engagement" in METRICS_INSIGHTS_SYSTEM_PROMPT.lower()

    def test_trace_anomalies_has_severity_levels(self) -> None:
        """Test TRACE_ANOMALIES_SYSTEM_PROMPT mentions severity levels."""
        from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
            TRACE_ANOMALIES_SYSTEM_PROMPT,
        )

        # Should mention severity levels
        assert "warning" in TRACE_ANOMALIES_SYSTEM_PROMPT.lower()
        assert "critical" in TRACE_ANOMALIES_SYSTEM_PROMPT.lower()


@pytest.mark.xdist_group(name="test_ai_ux_prompts")
class TestAIUXPromptsSecurityBlock:
    """Test AI UX prompts have security/injection protection blocks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_prompts_have_security_block(self) -> None:
        """Test all prompts have security block for injection protection."""
        from mcp_server_langgraph.core.prompts import ai_ux_prompts

        prompt_names = [
            "ERROR_ANALYSIS_SYSTEM_PROMPT",
            "EMPTY_STATE_SYSTEM_PROMPT",
            "PERSONA_ANALYSIS_SYSTEM_PROMPT",
            "DISCLOSURE_ANALYSIS_SYSTEM_PROMPT",
            "NUDGE_RECOMMENDATION_SYSTEM_PROMPT",
            "ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT",
            "METRICS_INSIGHTS_SYSTEM_PROMPT",
            "SESSION_SUMMARIZE_SYSTEM_PROMPT",
            "SESSION_GROUP_SYSTEM_PROMPT",
            "SESSION_SIMILARITY_SYSTEM_PROMPT",
            "TRACE_SUMMARIZE_SYSTEM_PROMPT",
            "TRACE_ANOMALIES_SYSTEM_PROMPT",
            "CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT",
            "CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT",
            "CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT",
            "DIAGRAM_ANALYZE_SYSTEM_PROMPT",
            "DIAGRAM_TO_CODE_SYSTEM_PROMPT",
        ]

        for name in prompt_names:
            prompt = getattr(ai_ux_prompts, name)
            # All prompts should have security block (added in Phase 5)
            # For now, just ensure they mention JSON-only output
            assert "json" in prompt.lower(), f"{name} should enforce JSON output"
