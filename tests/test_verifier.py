"""
Tests for Output Verifier (LLM-as-Judge Pattern)

Tests both LLM-based and rules-based verification.
Uses mocking to avoid actual LLM calls for fast execution.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from mcp_server_langgraph.llm.verifier import OutputVerifier, VerificationCriterion, VerificationResult, verify_output


@pytest.fixture
def output_verifier():
    """Create OutputVerifier instance for testing."""
    # Mock the settings
    mock_settings = MagicMock()
    mock_settings.model_name = "test-model"
    mock_settings.llm_provider = "test-provider"

    verifier = OutputVerifier(
        criteria=[
            VerificationCriterion.ACCURACY,
            VerificationCriterion.COMPLETENESS,
            VerificationCriterion.CLARITY,
        ],
        quality_threshold=0.7,
        settings=mock_settings,
    )

    # Mock the LLM
    verifier.llm = AsyncMock()

    return verifier


@pytest.fixture
def good_llm_judgment():
    """Mock LLM judgment for a good response."""
    return """SCORES:
- accuracy: 0.95
- completeness: 0.90
- clarity: 0.92

OVERALL: 0.92

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- Could add more examples
- Consider adding references

REQUIRES_REFINEMENT: no

FEEDBACK:
Excellent response with accurate information, comprehensive coverage, and clear structure. Minor improvements suggested but not required."""  # noqa: E501


@pytest.fixture
def poor_llm_judgment():
    """Mock LLM judgment for a poor response."""
    return """SCORES:
- accuracy: 0.60
- completeness: 0.50
- clarity: 0.70

OVERALL: 0.60

CRITICAL_ISSUES:
- Contains factual errors about quantum mechanics
- Missing explanation of key concepts

SUGGESTIONS:
- Verify facts before stating them
- Add more detail to explanation

REQUIRES_REFINEMENT: yes

FEEDBACK:
Response has accuracy issues and incomplete coverage. Needs to verify facts and provide more comprehensive explanation."""


@pytest.mark.xdist_group(name="verifier_tests")
class TestOutputVerifier:
    """Unit tests for OutputVerifier."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_initialization(self, output_verifier):
        """Test OutputVerifier initializes with correct config."""
        assert len(output_verifier.criteria) == 3
        assert output_verifier.quality_threshold == 0.7

    @pytest.mark.asyncio
    async def test_verify_response_good_quality(self, output_verifier, good_llm_judgment):
        """Test verification of high-quality response."""
        output_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_llm_judgment))

        result = await output_verifier.verify_response(
            response="Python is a high-level programming language created by Guido van Rossum.",
            user_request="What is Python?",
        )

        assert isinstance(result, VerificationResult)
        assert result.passed is True
        assert result.overall_score >= 0.7
        assert len(result.critical_issues) == 0
        assert result.requires_refinement is False

    @pytest.mark.asyncio
    async def test_verify_response_poor_quality(self, output_verifier, poor_llm_judgment):
        """Test verification of low-quality response."""
        output_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=poor_llm_judgment))

        result = await output_verifier.verify_response(
            response="Python is a type of snake.",
            user_request="What is Python programming language?",
        )

        assert isinstance(result, VerificationResult)
        assert result.passed is False
        assert result.overall_score < 0.7
        assert len(result.critical_issues) > 0
        assert result.requires_refinement is True

    @pytest.mark.asyncio
    async def test_verify_response_with_context(self, output_verifier, good_llm_judgment):
        """Test verification with conversation context."""
        output_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_llm_judgment))

        context = [
            HumanMessage(content="I'm learning programming"),
            AIMessage(content="Great! Which language are you interested in?"),
        ]

        result = await output_verifier.verify_response(
            response="Python is excellent for beginners.",
            user_request="Which language should I start with?",
            conversation_context=context,
        )

        assert result.passed is True

        # Verify LLM was called
        output_verifier.llm.ainvoke.assert_called_once()

        # Check that context was included in prompt
        # BUGFIX: After string-to-message fix, ainvoke receives a list of messages
        call_args = output_verifier.llm.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg is the messages list
        assert isinstance(messages, list), "Should receive list of messages"
        assert len(messages) > 0, "Should have at least one message"

        # Extract prompt content from HumanMessage
        prompt_content = messages[0].content
        assert "conversation_context" in prompt_content or "context" in prompt_content.lower()

    @pytest.mark.asyncio
    async def test_verify_response_strict_mode(self, output_verifier, good_llm_judgment):
        """Test verification in strict mode (higher threshold)."""
        # Judgment that passes standard but might fail strict
        judgment = good_llm_judgment.replace("OVERALL: 0.92", "OVERALL: 0.75")
        output_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=judgment))

        result = await output_verifier.verify_response(
            response="Test response",
            user_request="Test request",
            verification_mode="strict",
        )

        # In strict mode, threshold is higher (0.7 + 0.1 = 0.8)
        # 0.75 should fail
        assert result.overall_score == 0.75

    @pytest.mark.asyncio
    async def test_verify_response_lenient_mode(self, output_verifier):
        """Test verification in lenient mode (lower threshold)."""
        # Judgment with lower score
        judgment = """SCORES:
- accuracy: 0.65
- completeness: 0.65
- clarity: 0.65

OVERALL: 0.65

CRITICAL_ISSUES:
- None

REQUIRES_REFINEMENT: no

FEEDBACK: Acceptable response with room for improvement."""

        output_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=judgment))

        result = await output_verifier.verify_response(
            response="Test response",
            user_request="Test request",
            verification_mode="lenient",
        )

        # In lenient mode, threshold is lower (0.7 - 0.1 = 0.6)
        # 0.65 should pass
        assert result.overall_score == 0.65

    @pytest.mark.asyncio
    async def test_verify_response_error_handling(self, output_verifier):
        """Test that verification fails gracefully on errors."""
        # Make LLM raise an exception
        output_verifier.llm.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))

        result = await output_verifier.verify_response(
            response="Test response",
            user_request="Test request",
        )

        # Should fail-open (accept response on error)
        assert result.passed is True
        assert "unavailable" in result.feedback.lower() or "error" in result.feedback.lower()

    @pytest.mark.asyncio
    async def test_verify_with_rules_all_pass(self, output_verifier):
        """Test rules-based verification when all rules pass."""
        response = "This is a well-formed response with sufficient length and proper structure."

        rules = {
            "min_length": 10,
            "max_length": 1000,
        }

        result = await output_verifier.verify_with_rules(response, rules)

        assert result.passed is True
        assert result.overall_score == 1.0
        assert len(result.critical_issues) == 0

    @pytest.mark.asyncio
    async def test_verify_with_rules_min_length_fail(self, output_verifier):
        """Test rules-based verification fails on min length."""
        response = "Short"

        rules = {
            "min_length": 50,
        }

        result = await output_verifier.verify_with_rules(response, rules)

        assert result.passed is False
        assert len(result.critical_issues) > 0
        assert any("too short" in issue.lower() for issue in result.critical_issues)

    @pytest.mark.asyncio
    async def test_verify_with_rules_required_keywords(self, output_verifier):
        """Test rules-based verification with required keywords."""
        response = "This response explains Python and programming concepts."

        rules = {
            "required_keywords": ["python", "programming"],
        }

        result = await output_verifier.verify_with_rules(response, rules)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_verify_with_rules_missing_keywords(self, output_verifier):
        """Test rules-based verification fails on missing keywords."""
        response = "This response talks about Java and development."

        rules = {
            "required_keywords": ["python", "programming"],
        }

        result = await output_verifier.verify_with_rules(response, rules)

        assert result.passed is False
        assert any("missing" in issue.lower() and "keywords" in issue.lower() for issue in result.critical_issues)

    @pytest.mark.asyncio
    async def test_verify_with_rules_forbidden_keywords(self, output_verifier):
        """Test rules-based verification detects forbidden keywords."""
        response = "I'm sorry, but I don't know the answer to that question."

        rules = {
            "forbidden_keywords": ["sorry", "don't know"],
        }

        result = await output_verifier.verify_with_rules(response, rules)

        assert result.passed is False
        assert any("forbidden" in issue.lower() for issue in result.critical_issues)

    @pytest.mark.asyncio
    async def test_verify_with_rules_code_requirement(self, output_verifier):
        """Test rules-based verification for code inclusion."""
        response_with_code = "Here's an example:\n```python\nprint('hello')\n```"
        response_without_code = "You can use the print function."

        rules = {
            "must_include_code": True,
        }

        result_with = await output_verifier.verify_with_rules(response_with_code, rules)
        result_without = await output_verifier.verify_with_rules(response_without_code, rules)

        assert result_with.passed is True
        assert result_without.passed is False

    def test_parse_verification_judgment_well_formed(self, output_verifier, good_llm_judgment):
        """Test parsing of well-formed LLM judgment."""
        result = output_verifier._parse_verification_judgment(good_llm_judgment, threshold=0.7)

        assert isinstance(result, VerificationResult)
        assert result.overall_score > 0.8
        assert result.passed is True
        assert "accuracy" in result.criterion_scores

    def test_parse_verification_judgment_malformed(self, output_verifier):
        """Test parsing handles malformed judgments."""
        malformed = "This is not a properly formatted judgment."

        # Should not crash, should return some result
        result = output_verifier._parse_verification_judgment(malformed, threshold=0.7)

        assert isinstance(result, VerificationResult)
        # May or may not pass, but should have feedback
        assert len(result.feedback) > 0

    def test_get_threshold_for_mode(self, output_verifier):
        """Test threshold calculation for different modes."""
        strict = output_verifier._get_threshold_for_mode("strict")
        standard = output_verifier._get_threshold_for_mode("standard")
        lenient = output_verifier._get_threshold_for_mode("lenient")

        assert strict > standard > lenient
        assert strict == 0.8  # 0.7 + 0.1
        assert standard == 0.7
        assert lenient == 0.6  # 0.7 - 0.1

    def test_build_verification_prompt(self, output_verifier):
        """Test verification prompt building."""
        prompt = output_verifier._build_verification_prompt(
            response="Test response",
            user_request="Test request",
            conversation_context=None,
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Should contain XML tags (Anthropic best practice)
        assert "<task>" in prompt
        assert "<role>" in prompt
        assert "<evaluation_criteria>" in prompt
        assert "<output_format>" in prompt

        # Should contain the response and request
        assert "Test response" in prompt
        assert "Test request" in prompt


@pytest.mark.xdist_group(name="verifier_tests")
class TestVerificationCriterion:
    """Test VerificationCriterion enum."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_criteria_defined(self):
        """Test that all criteria are properly defined."""
        criteria = list(VerificationCriterion)

        assert VerificationCriterion.ACCURACY in criteria
        assert VerificationCriterion.COMPLETENESS in criteria
        assert VerificationCriterion.CLARITY in criteria
        assert VerificationCriterion.RELEVANCE in criteria
        assert VerificationCriterion.SAFETY in criteria
        assert VerificationCriterion.SOURCES in criteria

    def test_criterion_values(self):
        """Test criterion enum values."""
        assert VerificationCriterion.ACCURACY.value == "accuracy"
        assert VerificationCriterion.COMPLETENESS.value == "completeness"
        assert VerificationCriterion.CLARITY.value == "clarity"


@pytest.mark.xdist_group(name="verifier_tests")
class TestVerificationResult:
    """Test VerificationResult model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_verification_result_creation(self):
        """Test creating VerificationResult."""
        result = VerificationResult(
            passed=True,
            overall_score=0.85,
            criterion_scores={"accuracy": 0.9, "completeness": 0.8},
            feedback="Good response",
            requires_refinement=False,
            critical_issues=[],
            suggestions=["Add more examples"],
        )

        assert result.passed is True
        assert result.overall_score == 0.85
        assert len(result.criterion_scores) == 2
        assert len(result.suggestions) == 1

    def test_verification_result_validation(self):
        """Test VerificationResult validation."""
        # Score should be between 0 and 1
        with pytest.raises(Exception):  # Pydantic validation error
            VerificationResult(
                passed=True,
                overall_score=1.5,  # Invalid: > 1.0
                feedback="Test",
            )


@pytest.mark.xdist_group(name="verifier_tests")
class TestConvenienceFunctions:
    """Test convenience functions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_output_convenience(self, good_llm_judgment):
        """Test verify_output convenience function."""
        from unittest.mock import patch

        with patch("mcp_server_langgraph.llm.verifier.OutputVerifier") as MockVerifier:
            mock_verifier = MagicMock()
            mock_result = VerificationResult(
                passed=True,
                overall_score=0.9,
                feedback="Good",
            )
            mock_verifier.verify_response = AsyncMock(return_value=mock_result)
            MockVerifier.return_value = mock_verifier

            result = await verify_output(
                response="Test response",
                user_request="Test request",
            )

            assert result.passed is True
            mock_verifier.verify_response.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
