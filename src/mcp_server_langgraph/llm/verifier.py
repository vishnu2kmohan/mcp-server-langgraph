"""
Work Verification Component for Agentic Workflows

Implements Anthropic's "Verify Work" step in the agent loop:
- LLM-as-judge: Use another LLM to evaluate outputs
- Rules-based validation: Check against explicit criteria
- Iterative refinement: Provide feedback for improvement

References:
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
"""

from enum import Enum
from typing import Any, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from mcp_server_langgraph.llm.factory import create_verification_model
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class VerificationCriterion(str, Enum):
    """Criteria for evaluating agent outputs."""

    ACCURACY = "accuracy"  # Is the information correct?
    COMPLETENESS = "completeness"  # Does it fully answer the question?
    CLARITY = "clarity"  # Is it clear and well-structured?
    RELEVANCE = "relevance"  # Is it relevant to the user's request?
    SAFETY = "safety"  # Is it safe and appropriate?
    SOURCES = "sources"  # Are sources cited when appropriate?


class VerificationResult(BaseModel):
    """Result of output verification."""

    passed: bool = Field(description="Whether verification passed")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score (0-1)")
    criterion_scores: dict[str, float] = Field(default_factory=dict, description="Scores for individual criteria (0-1)")
    feedback: str = Field(description="Actionable feedback for improvement")
    requires_refinement: bool = Field(default=False, description="Whether output should be refined")
    critical_issues: list[str] = Field(default_factory=list, description="Critical issues that must be fixed")
    suggestions: list[str] = Field(default_factory=list, description="Optional suggestions for improvement")


class OutputVerifier:
    """
    Verifies agent outputs using LLM-as-judge pattern.

    Implements "Work Verification" from Anthropic's Agent SDK guide:
    - Evaluates outputs against quality criteria
    - Provides actionable feedback
    - Supports iterative refinement
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        criteria: Optional[list[VerificationCriterion]] = None,
        quality_threshold: float = 0.7,
        settings=None,
    ):
        """
        Initialize output verifier.

        Args:
            criteria: Criteria to verify (default: all)
            quality_threshold: Minimum score to pass (default: 0.7)
            settings: Application settings (if None, uses global settings)
        """
        self.criteria = criteria or list(VerificationCriterion)
        self.quality_threshold = quality_threshold

        # Initialize dedicated LLM for verification (LLM-as-judge)
        if settings is None:
            from mcp_server_langgraph.core.config import settings as global_settings

            settings = global_settings

        self.llm = create_verification_model(settings)

        logger.info(
            "OutputVerifier initialized",
            extra={
                "criteria": [c.value for c in self.criteria],
                "quality_threshold": quality_threshold,
            },
        )

    async def verify_response(
        self,
        response: str,
        user_request: str,
        conversation_context: Optional[list[BaseMessage]] = None,
        verification_mode: Literal["standard", "strict", "lenient"] = "standard",
    ) -> VerificationResult:
        """
        Verify agent response quality using LLM-as-judge.

        Args:
            response: Agent's response to verify
            user_request: Original user request
            conversation_context: Conversation history for context
            verification_mode: Strictness level (default: standard)

        Returns:
            VerificationResult with scores and feedback
        """
        with tracer.start_as_current_span("verifier.verify_response") as span:
            span.set_attribute("response.length", len(response))
            span.set_attribute("verification.mode", verification_mode)

            # Adjust threshold based on mode
            threshold = self._get_threshold_for_mode(verification_mode)

            # Build verification prompt using XML structure
            verification_prompt = self._build_verification_prompt(response, user_request, conversation_context)

            try:
                # Get LLM judgment
                # BUGFIX: Wrap prompt in HumanMessage to avoid string-to-character-list iteration
                llm_response = await self.llm.ainvoke([HumanMessage(content=verification_prompt)])
                judgment = llm_response.content if hasattr(llm_response, "content") else str(llm_response)

                # Parse judgment into structured result
                result = self._parse_verification_judgment(judgment, threshold)  # type: ignore[ list]

                span.set_attribute("verification.passed", result.passed)
                span.set_attribute("verification.overall_score", result.overall_score)

                metrics.successful_calls.add(1, {"operation": "verify_response", "passed": str(result.passed).lower()})

                logger.info(
                    "Response verified",
                    extra={
                        "passed": result.passed,
                        "overall_score": result.overall_score,
                        "requires_refinement": result.requires_refinement,
                        "critical_issues_count": len(result.critical_issues),
                    },
                )

                return result

            except Exception as e:
                logger.error(f"Verification failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "verify_response"})
                span.record_exception(e)

                # Fallback: Return permissive result
                return VerificationResult(
                    passed=True,  # Fail-open on verification errors
                    overall_score=0.5,
                    feedback=f"Verification system unavailable. Response accepted by default. Error: {str(e)}",
                    requires_refinement=False,
                )

    def _build_verification_prompt(
        self, response: str, user_request: str, conversation_context: Optional[list[BaseMessage]] = None
    ) -> str:
        """
        Build verification prompt using XML structure (Anthropic best practice).

        Args:
            response: Response to verify
            user_request: Original request
            conversation_context: Conversation history

        Returns:
            Structured verification prompt
        """
        # Format conversation context if provided
        context_section = ""
        if conversation_context:
            context_text = "\n".join([f"{self._get_role(msg)}: {msg.content[:200]}..." for msg in conversation_context[-3:]])
            context_section = f"""<conversation_context>
{context_text}
</conversation_context>

"""

        # Build criteria section
        criteria_descriptions = {
            VerificationCriterion.ACCURACY: "Is the information factually correct?",
            VerificationCriterion.COMPLETENESS: "Does it fully address all aspects of the user's request?",
            VerificationCriterion.CLARITY: "Is it clear, well-organized, and easy to understand?",
            VerificationCriterion.RELEVANCE: "Is it directly relevant to what the user asked?",
            VerificationCriterion.SAFETY: "Is it safe, appropriate, and free from harmful content?",
            VerificationCriterion.SOURCES: "Are sources cited when making factual claims?",
        }

        criteria_text = "\n".join([f"- {criterion.value}: {criteria_descriptions[criterion]}" for criterion in self.criteria])

        prompt = f"""<task>
Evaluate the quality of an AI assistant's response to a user request.
</task>

<role>
You are a quality evaluator for AI assistant responses.
Your job is to provide objective, constructive feedback.
</role>

{context_section}<user_request>
{user_request}
</user_request>

<assistant_response>
{response}
</assistant_response>

<evaluation_criteria>
Evaluate the response on these criteria (score each 0.0-1.0):
{criteria_text}
</evaluation_criteria>

<instructions>
1. Evaluate each criterion independently with a score from 0.0 to 1.0
2. Calculate an overall score (average of all criteria)
3. Identify any critical issues that must be fixed
4. Provide actionable feedback for improvement
5. Suggest whether the response requires refinement
</instructions>

<output_format>
Provide your evaluation in this exact format:

SCORES:
- accuracy: [0.0-1.0]
- completeness: [0.0-1.0]
- clarity: [0.0-1.0]
- relevance: [0.0-1.0]
- safety: [0.0-1.0]
- sources: [0.0-1.0]

OVERALL: [0.0-1.0]

CRITICAL_ISSUES:
- [Issue 1, if any]
- [Issue 2, if any]

SUGGESTIONS:
- [Suggestion 1]
- [Suggestion 2]

REQUIRES_REFINEMENT: [yes/no]

FEEDBACK:
[Detailed, actionable feedback in 2-3 sentences]
</output_format>"""

        return prompt

    def _parse_verification_judgment(self, judgment: str, threshold: float) -> VerificationResult:  # noqa: C901
        """
        Parse LLM judgment into structured VerificationResult.

        Args:
            judgment: Raw LLM judgment text
            threshold: Quality threshold for passing

        Returns:
            Structured VerificationResult
        """
        # Extract scores using simple parsing (can be enhanced with regex)
        criterion_scores = {}
        overall_score = None  # Will be set from OVERALL or calculated
        critical_issues = []
        suggestions = []
        requires_refinement = False
        feedback = ""

        lines = judgment.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("SCORES:"):
                current_section = "scores"
            elif line.startswith("OVERALL:"):
                current_section = "overall"
                try:
                    overall_score = float(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.startswith("CRITICAL_ISSUES:"):
                current_section = "critical"
            elif line.startswith("SUGGESTIONS:"):
                current_section = "suggestions"
            elif line.startswith("REQUIRES_REFINEMENT:"):
                current_section = "refinement"
                requires_refinement = "yes" in line.lower()
            elif line.startswith("FEEDBACK:"):
                current_section = "feedback"
            elif current_section == "scores" and ":" in line:
                try:
                    criterion, score = line.split(":", 1)
                    criterion = criterion.strip(" -")
                    score = float(score.strip())  # type: ignore[assignment]
                    criterion_scores[criterion] = score
                except (ValueError, IndexError):
                    pass
            elif current_section == "critical" and line.startswith("-"):
                issue = line[1:].strip()
                # Filter out "None" or empty issues
                if issue and issue.lower() not in ["none", "n/a", "na"]:
                    critical_issues.append(issue)
            elif current_section == "suggestions" and line.startswith("-"):
                suggestion = line[1:].strip()
                if suggestion and suggestion.lower() not in ["none", "n/a", "na"]:
                    suggestions.append(suggestion)
            elif current_section == "feedback" and line:
                feedback += line + " "

        feedback = feedback.strip() or "No specific feedback provided."

        # Calculate overall score from criteria if not explicitly provided in OVERALL
        if overall_score is None:
            if criterion_scores:
                overall_score = sum(criterion_scores.values()) / len(criterion_scores)  # type: ignore[arg-type]
                logger.info("Calculated overall score from criterion scores")
            else:
                overall_score = 0.5  # Default fallback
                logger.warning("Failed to parse both overall score and criterion scores, using default")

        passed = overall_score >= threshold and len(critical_issues) == 0

        return VerificationResult(
            passed=passed,
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            feedback=feedback,
            requires_refinement=requires_refinement or not passed,
            critical_issues=critical_issues,
            suggestions=suggestions,
        )

    def _get_threshold_for_mode(self, mode: Literal["standard", "strict", "lenient"]) -> float:
        """Get quality threshold based on verification mode."""
        thresholds = {
            "strict": self.quality_threshold + 0.1,
            "standard": self.quality_threshold,
            "lenient": self.quality_threshold - 0.1,
        }
        # Round to avoid floating point precision issues in tests
        threshold = thresholds.get(mode, self.quality_threshold)
        return round(max(0.0, min(1.0, threshold)), 2)

    def _get_role(self, message: BaseMessage) -> str:
        """Get role label for message."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        if isinstance(message, HumanMessage):
            return "User"
        elif isinstance(message, AIMessage):
            return "Assistant"
        elif isinstance(message, SystemMessage):
            return "System"
        else:
            return "Message"

    async def verify_with_rules(self, response: str, rules: dict[str, Any]) -> VerificationResult:
        """
        Verify response against explicit rules (rules-based validation).

        Alternative to LLM-as-judge for deterministic checks.

        Args:
            response: Response to verify
            rules: Dictionary of rules to check

        Returns:
            VerificationResult based on rule compliance

        Example rules:
            {
                "min_length": 50,
                "max_length": 2000,
                "required_keywords": ["example", "explanation"],
                "forbidden_keywords": ["sorry", "I don't know"],
                "must_include_code": True
            }
        """
        issues = []
        suggestions = []
        criterion_scores = {}

        # Check length constraints
        if "min_length" in rules and len(response) < rules["min_length"]:
            issues.append(f"Response too short (minimum: {rules['min_length']} characters)")
            criterion_scores["completeness"] = 0.3

        if "max_length" in rules and len(response) > rules["max_length"]:
            suggestions.append(f"Response could be more concise (maximum: {rules['max_length']} characters)")
            criterion_scores["clarity"] = 0.7

        # Check required keywords
        if "required_keywords" in rules:
            missing = [kw for kw in rules["required_keywords"] if kw.lower() not in response.lower()]
            if missing:
                issues.append(f"Missing required keywords: {', '.join(missing)}")
                criterion_scores["completeness"] = 0.5

        # Check forbidden keywords
        if "forbidden_keywords" in rules:
            found = [kw for kw in rules["forbidden_keywords"] if kw.lower() in response.lower()]
            if found:
                issues.append(f"Contains forbidden keywords: {', '.join(found)}")
                criterion_scores["quality"] = 0.4

        # Check code inclusion
        if rules.get("must_include_code") and "```" not in response:
            issues.append("Response must include code examples")
            criterion_scores["completeness"] = 0.6

        # Calculate overall score
        overall_score = (
            1.0 if not issues else (sum(criterion_scores.values()) / len(criterion_scores) if criterion_scores else 0.5)
        )
        passed = len(issues) == 0

        feedback = "All rule checks passed." if passed else f"Failed {len(issues)} rule check(s). " + "; ".join(issues)

        logger.info(
            "Rules-based verification completed",
            extra={
                "passed": passed,
                "issues_count": len(issues),
                "rules_checked": len(rules),
            },
        )

        return VerificationResult(
            passed=passed,
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            feedback=feedback,
            requires_refinement=not passed,
            critical_issues=issues,
            suggestions=suggestions,
        )


# Convenience function for easy import
async def verify_output(
    response: str,
    user_request: str,
    conversation_context: Optional[list[BaseMessage]] = None,
    verifier: Optional[OutputVerifier] = None,
) -> VerificationResult:
    """
    Verify agent output (convenience function).

    Args:
        response: Response to verify
        user_request: Original user request
        conversation_context: Conversation history
        verifier: OutputVerifier instance (creates new if None)

    Returns:
        VerificationResult
    """
    if verifier is None:
        verifier = OutputVerifier()

    return await verifier.verify_response(response, user_request, conversation_context)
