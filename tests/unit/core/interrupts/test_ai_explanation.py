"""
Tests for AI Explanation Models.

Part of AI-Native Enhancements for HITL Dialogs (Phase 1).

TDD: Write tests FIRST, then implementation.

Tests:
1. AIExplanation model imports and validates correctly
2. ConfidenceFactor model validates correctly
3. AlternativeSuggestion model validates correctly
4. ExplanationType enum has all expected values
5. Model serialization/deserialization works
6. Default values are applied correctly
"""

from __future__ import annotations

import gc
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="ai_explanation_imports")
class TestAIExplanationImports:
    """Test AI explanation models can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_explanation_importable(self) -> None:
        """AIExplanation should be importable."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        assert AIExplanation is not None

    def test_confidence_factor_importable(self) -> None:
        """ConfidenceFactor should be importable."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ConfidenceFactor

        assert ConfidenceFactor is not None

    def test_alternative_suggestion_importable(self) -> None:
        """AlternativeSuggestion should be importable."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AlternativeSuggestion,
        )

        assert AlternativeSuggestion is not None

    def test_explanation_type_importable(self) -> None:
        """ExplanationType enum should be importable."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ExplanationType

        assert ExplanationType is not None


@pytest.mark.xdist_group(name="ai_explanation_enum")
class TestExplanationType:
    """Test ExplanationType enum values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_type_has_uncertainty_value(self) -> None:
        """ExplanationType should have UNCERTAINTY value."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ExplanationType

        assert hasattr(ExplanationType, "UNCERTAINTY")
        assert ExplanationType.UNCERTAINTY.value == "uncertainty"

    def test_explanation_type_has_risk_analysis_value(self) -> None:
        """ExplanationType should have RISK_ANALYSIS value."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ExplanationType

        assert hasattr(ExplanationType, "RISK_ANALYSIS")
        assert ExplanationType.RISK_ANALYSIS.value == "risk_analysis"

    def test_explanation_type_has_alternatives_value(self) -> None:
        """ExplanationType should have ALTERNATIVES value."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ExplanationType

        assert hasattr(ExplanationType, "ALTERNATIVES")
        assert ExplanationType.ALTERNATIVES.value == "alternatives"

    def test_explanation_type_has_evidence_value(self) -> None:
        """ExplanationType should have EVIDENCE value."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ExplanationType

        assert hasattr(ExplanationType, "EVIDENCE")
        assert ExplanationType.EVIDENCE.value == "evidence"


@pytest.mark.xdist_group(name="confidence_factor_model")
class TestConfidenceFactorModel:
    """Test ConfidenceFactor model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_confidence_factor_creation(self) -> None:
        """ConfidenceFactor should be creatable with required fields."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ConfidenceFactor

        factor = ConfidenceFactor(
            factor="ambiguous_input",
            weight=-0.2,
            evidence="User query contains ambiguous terms",
        )

        assert factor.factor == "ambiguous_input"
        assert factor.weight == -0.2
        assert factor.evidence == "User query contains ambiguous terms"

    def test_confidence_factor_weight_range(self) -> None:
        """ConfidenceFactor weight should accept -1.0 to 1.0."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ConfidenceFactor

        # Negative weight (reduces confidence)
        factor_neg = ConfidenceFactor(
            factor="uncertainty",
            weight=-1.0,
            evidence="Maximum uncertainty",
        )
        assert factor_neg.weight == -1.0

        # Positive weight (increases confidence)
        factor_pos = ConfidenceFactor(
            factor="strong_match",
            weight=1.0,
            evidence="Strong pattern match",
        )
        assert factor_pos.weight == 1.0

    def test_confidence_factor_serialization(self) -> None:
        """ConfidenceFactor should serialize to dict."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import ConfidenceFactor

        factor = ConfidenceFactor(
            factor="multiple_interpretations",
            weight=-0.15,
            evidence="Query could mean X or Y",
        )

        data = factor.model_dump()
        assert data["factor"] == "multiple_interpretations"
        assert data["weight"] == -0.15
        assert data["evidence"] == "Query could mean X or Y"


@pytest.mark.xdist_group(name="alternative_suggestion_model")
class TestAlternativeSuggestionModel:
    """Test AlternativeSuggestion model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alternative_suggestion_creation(self) -> None:
        """AlternativeSuggestion should be creatable with required fields."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AlternativeSuggestion,
        )

        alt = AlternativeSuggestion(
            action="Use read-only mode instead",
            confidence=0.92,
            trade_off="Cannot make changes, only view data",
        )

        assert alt.action == "Use read-only mode instead"
        assert alt.confidence == 0.92
        assert alt.trade_off == "Cannot make changes, only view data"

    def test_alternative_suggestion_confidence_range(self) -> None:
        """AlternativeSuggestion confidence should be 0.0 to 1.0."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AlternativeSuggestion,
        )

        alt_low = AlternativeSuggestion(
            action="Risky alternative",
            confidence=0.0,
            trade_off="Completely uncertain",
        )
        assert alt_low.confidence == 0.0

        alt_high = AlternativeSuggestion(
            action="Safe alternative",
            confidence=1.0,
            trade_off="Full guarantee",
        )
        assert alt_high.confidence == 1.0

    def test_alternative_suggestion_serialization(self) -> None:
        """AlternativeSuggestion should serialize to dict."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AlternativeSuggestion,
        )

        alt = AlternativeSuggestion(
            action="Request clarification first",
            confidence=0.95,
            trade_off="Adds one extra interaction step",
        )

        data = alt.model_dump()
        assert data["action"] == "Request clarification first"
        assert data["confidence"] == 0.95
        assert data["trade_off"] == "Adds one extra interaction step"


@pytest.mark.xdist_group(name="ai_explanation_model")
class TestAIExplanationModel:
    """Test AIExplanation model validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_explanation_creation_minimal(self) -> None:
        """AIExplanation should be creatable with minimal fields."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="The input is ambiguous.",
            what_could_go_wrong="May perform wrong action.",
        )

        assert explanation.why_uncertain == "The input is ambiguous."
        assert explanation.what_could_go_wrong == "May perform wrong action."

    def test_ai_explanation_has_default_empty_lists(self) -> None:
        """AIExplanation should have empty lists as defaults."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        assert explanation.safer_alternatives == []
        assert explanation.confidence_factors == []
        assert explanation.reasoning_trace == []

    def test_ai_explanation_default_explanation_type(self) -> None:
        """AIExplanation should default to UNCERTAINTY type."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            ExplanationType,
        )

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        assert explanation.explanation_type == ExplanationType.UNCERTAINTY

    def test_ai_explanation_default_model(self) -> None:
        """AIExplanation should default to gpt-4o-mini model."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        assert explanation.model_used == "gpt-4o-mini"

    def test_ai_explanation_default_cached_false(self) -> None:
        """AIExplanation should default cached to False."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        assert explanation.cached is False

    def test_ai_explanation_default_latency_zero(self) -> None:
        """AIExplanation should default generation_latency_ms to 0.0."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )

        assert explanation.generation_latency_ms == 0.0

    def test_ai_explanation_generated_at_auto_set(self) -> None:
        """AIExplanation should auto-set generated_at to current time."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        before = datetime.now(timezone.utc)
        explanation = AIExplanation(
            why_uncertain="Test",
            what_could_go_wrong="Test",
        )
        after = datetime.now(timezone.utc)

        assert before <= explanation.generated_at <= after

    def test_ai_explanation_with_alternatives(self) -> None:
        """AIExplanation should accept list of AlternativeSuggestion."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
        )

        alternatives = [
            AlternativeSuggestion(
                action="Read-only mode",
                confidence=0.92,
                trade_off="Cannot modify data",
            ),
            AlternativeSuggestion(
                action="Ask for confirmation",
                confidence=0.88,
                trade_off="Extra step required",
            ),
        ]

        explanation = AIExplanation(
            why_uncertain="Multiple valid actions possible",
            what_could_go_wrong="May choose wrong action",
            safer_alternatives=alternatives,
        )

        assert len(explanation.safer_alternatives) == 2
        assert explanation.safer_alternatives[0].action == "Read-only mode"

    def test_ai_explanation_with_confidence_factors(self) -> None:
        """AIExplanation should accept list of ConfidenceFactor."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            ConfidenceFactor,
        )

        factors = [
            ConfidenceFactor(
                factor="ambiguous_input",
                weight=-0.2,
                evidence="Query lacks specificity",
            ),
            ConfidenceFactor(
                factor="multiple_interpretations",
                weight=-0.15,
                evidence="Could mean A or B",
            ),
        ]

        explanation = AIExplanation(
            why_uncertain="Input interpretation unclear",
            what_could_go_wrong="Wrong interpretation chosen",
            confidence_factors=factors,
        )

        assert len(explanation.confidence_factors) == 2
        assert explanation.confidence_factors[0].factor == "ambiguous_input"

    def test_ai_explanation_with_reasoning_trace(self) -> None:
        """AIExplanation should accept reasoning trace list."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        trace = [
            "Step 1: Parsed user query",
            "Step 2: Found ambiguous terms",
            "Step 3: Multiple actions match query",
        ]

        explanation = AIExplanation(
            why_uncertain="Reasoning led to uncertainty",
            what_could_go_wrong="May choose incorrectly",
            reasoning_trace=trace,
        )

        assert len(explanation.reasoning_trace) == 3
        assert "ambiguous" in explanation.reasoning_trace[1]


@pytest.mark.xdist_group(name="ai_explanation_serialization")
class TestAIExplanationSerialization:
    """Test AIExplanation model serialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_explanation_to_dict(self) -> None:
        """AIExplanation should serialize to dict."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            AlternativeSuggestion,
            ConfidenceFactor,
        )

        explanation = AIExplanation(
            why_uncertain="Test uncertainty",
            what_could_go_wrong="Test risk",
            safer_alternatives=[
                AlternativeSuggestion(
                    action="Safe action",
                    confidence=0.9,
                    trade_off="Minor limitation",
                ),
            ],
            confidence_factors=[
                ConfidenceFactor(
                    factor="test_factor",
                    weight=-0.1,
                    evidence="Test evidence",
                ),
            ],
            reasoning_trace=["Step 1", "Step 2"],
        )

        data = explanation.model_dump()

        assert data["why_uncertain"] == "Test uncertainty"
        assert data["what_could_go_wrong"] == "Test risk"
        assert len(data["safer_alternatives"]) == 1
        assert len(data["confidence_factors"]) == 1
        assert len(data["reasoning_trace"]) == 2

    def test_ai_explanation_from_dict(self) -> None:
        """AIExplanation should deserialize from dict."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import (
            AIExplanation,
            ExplanationType,
        )

        data = {
            "why_uncertain": "Deserialized uncertainty",
            "what_could_go_wrong": "Deserialized risk",
            "safer_alternatives": [
                {
                    "action": "Alt action",
                    "confidence": 0.85,
                    "trade_off": "Some trade-off",
                }
            ],
            "confidence_factors": [],
            "reasoning_trace": [],
            "explanation_type": "risk_analysis",
            "model_used": "gpt-4o",
            "generation_latency_ms": 150.5,
            "cached": True,
        }

        explanation = AIExplanation(**data)

        assert explanation.why_uncertain == "Deserialized uncertainty"
        assert explanation.explanation_type == ExplanationType.RISK_ANALYSIS
        assert explanation.model_used == "gpt-4o"
        assert explanation.generation_latency_ms == 150.5
        assert explanation.cached is True
        assert len(explanation.safer_alternatives) == 1

    def test_ai_explanation_json_round_trip(self) -> None:
        """AIExplanation should round-trip through JSON."""
        import json

        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        original = AIExplanation(
            why_uncertain="JSON round trip test",
            what_could_go_wrong="Should preserve all fields",
            reasoning_trace=["Step 1"],
        )

        json_str = original.model_dump_json()
        data = json.loads(json_str)
        restored = AIExplanation(**data)

        assert restored.why_uncertain == original.why_uncertain
        assert restored.what_could_go_wrong == original.what_could_go_wrong
        assert restored.reasoning_trace == original.reasoning_trace
