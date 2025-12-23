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
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage

if TYPE_CHECKING:
    from mcp_server_langgraph.core.cache import CacheService
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.constants import MESSAGE_PREVIEW_LENGTH
from mcp_server_langgraph.llm.factory import create_verification_model
from mcp_server_langgraph.llm.visual_verification_metrics import (
    record_screenshot_cache_hit,
    record_screenshot_cache_miss,
    record_visual_verification_duration,
    record_visual_verification_request,
    record_visual_verification_retry,
    record_visual_verification_score,
    record_visual_verification_urls,
)
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
import asyncio
import contextlib
import random
import time

import httpx


class VerificationCriterion(str, Enum):
    """Criteria for evaluating agent outputs."""

    ACCURACY = "accuracy"  # Is the information correct?
    COMPLETENESS = "completeness"  # Does it fully answer the question?
    CLARITY = "clarity"  # Is it clear and well-structured?
    RELEVANCE = "relevance"  # Is it relevant to the user's request?
    SAFETY = "safety"  # Is it safe and appropriate?
    SOURCES = "sources"  # Are sources cited when appropriate?


class VisualVerificationCriterion(str, Enum):
    """Criteria for evaluating visual state of web pages.

    Used with screenshot-based verification to assess UI state.
    """

    UI_LAYOUT = "ui_layout"  # Is the layout correct and responsive?
    CONTENT_VISIBLE = "content_visible"  # Is the expected content visible?
    ELEMENT_PRESENT = "element_present"  # Are expected elements present?
    ERROR_VISIBLE = "error_visible"  # Are there visible errors? (inverse - low is good)
    LOADING_COMPLETE = "loading_complete"  # Has the page finished loading?


class VerificationResult(BaseModel):
    """Result of output verification."""

    passed: bool = Field(description="Whether verification passed")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score (0-1)")
    criterion_scores: dict[str, float] = Field(default_factory=dict, description="Scores for individual criteria (0-1)")
    feedback: str = Field(description="Actionable feedback for improvement")
    requires_refinement: bool = Field(default=False, description="Whether output should be refined")
    critical_issues: list[str] = Field(default_factory=list, description="Critical issues that must be fixed")
    suggestions: list[str] = Field(default_factory=list, description="Optional suggestions for improvement")


class VisualVerificationResult(VerificationResult):
    """Result of visual verification using screenshot analysis.

    Extends VerificationResult with visual-specific fields.
    """

    url: str = Field(description="URL that was verified")
    screenshot_captured: bool = Field(default=False, description="Whether screenshot was successfully captured")
    visual_observations: list[str] = Field(default_factory=list, description="Observations from visual analysis")


# =============================================================================
# Retry Configuration for Visual Verification
# =============================================================================
# Aligned with codebase resilience patterns (see ADR-0026)

VISUAL_VERIFICATION_MAX_ATTEMPTS = 3
VISUAL_VERIFICATION_EXPONENTIAL_BASE = 2.0
VISUAL_VERIFICATION_EXPONENTIAL_MAX = 10.0

# Exceptions that trigger retry for screenshot capture
SCREENSHOT_RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
    ConnectionError,
    OSError,
)

# Exceptions that trigger retry for LLM invocation
LLM_RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
    ConnectionError,
)

# =============================================================================
# Screenshot Cache Configuration
# =============================================================================
# Caches screenshots by URL to avoid redundant captures for repeated verifications.
# Uses CacheService from core/cache.py with L1 (in-memory) + L2 (Redis) layers.

SCREENSHOT_CACHE_TTL = 300  # 5 minutes - pages may change, keep cache short
SCREENSHOT_CACHE_PREFIX = "screenshot"


def generate_screenshot_cache_key(url: str) -> str:
    """
    Generate cache key from URL with normalization.

    Normalizes URL to ensure consistent caching:
    - Removes trailing slashes
    - Lowercases scheme and host

    Args:
        url: URL to generate cache key for

    Returns:
        Cache key string
    """
    import hashlib
    from urllib.parse import urlparse, urlunparse

    # Parse and normalize URL
    parsed = urlparse(url)

    # Normalize: lowercase scheme and host, remove trailing slash from path
    normalized_path = parsed.path.rstrip("/") if parsed.path else ""

    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.params,
            parsed.query,
            "",  # Remove fragment
        )
    )

    # Generate hash for cache key (URL may be too long for key)
    url_hash = hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()

    return f"{SCREENSHOT_CACHE_PREFIX}:{url_hash}"


def get_screenshot_cache() -> "CacheService":
    """
    Get the screenshot cache service.

    Uses CacheService from core/cache.py with L1 (in-memory) fallback if Redis unavailable.

    Returns:
        CacheService instance
    """
    from mcp_server_langgraph.core.cache import get_cache

    return get_cache()


def _is_retryable_exception(exception: Exception) -> bool:
    """
    Check if an exception is retryable.

    Aligned with resilience/retry.py:should_retry_exception pattern.
    Non-retryable: ValidationError, AuthorizationError, AuthenticationError

    Args:
        exception: The exception to check

    Returns:
        True if retryable, False otherwise
    """
    # Import here to avoid circular dependency
    try:
        from mcp_server_langgraph.core.exceptions import (
            AuthenticationError,
            AuthorizationError,
            ValidationError,
        )

        # Never retry client/validation errors
        if isinstance(exception, (ValidationError, AuthorizationError, AuthenticationError)):
            return False
    except ImportError:
        pass

    # Check for common transient exceptions
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True

    # Check for connection/network errors
    if isinstance(exception, (ConnectionError, OSError)):
        return True

    # Check for LLM overload (529 status code)
    return hasattr(exception, "status_code") and exception.status_code == 529


def _calculate_backoff_delay(attempt: int) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Follows AWS best practices for exponential backoff with jitter.

    Args:
        attempt: Current attempt number (1-indexed)

    Returns:
        Delay in seconds
    """
    # Exponential backoff: 2^attempt
    base_delay = VISUAL_VERIFICATION_EXPONENTIAL_BASE**attempt

    # Cap at max
    capped_delay = min(base_delay, VISUAL_VERIFICATION_EXPONENTIAL_MAX)

    # Add jitter: +/- 20%
    jitter_factor = random.uniform(0.8, 1.2)

    return capped_delay * jitter_factor


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
        criteria: list[VerificationCriterion] | None = None,
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
        conversation_context: list[BaseMessage] | None = None,
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

                # Get content and ensure it's a string
                content = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
                judgment = str(content) if not isinstance(content, str) else content

                # Parse judgment into structured result
                result = self._parse_verification_judgment(judgment, threshold)

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
                    feedback=f"Verification system unavailable. Response accepted by default. Error: {e!s}",
                    requires_refinement=False,
                )

    def _build_verification_prompt(
        self, response: str, user_request: str, conversation_context: list[BaseMessage] | None = None
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
            context_text = "\n".join(
                [f"{self._get_role(msg)}: {msg.content[:MESSAGE_PREVIEW_LENGTH]}..." for msg in conversation_context[-3:]]
            )
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
                with contextlib.suppress(ValueError, IndexError):
                    overall_score = float(line.split(":")[1].strip())
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
            criterion_scores=criterion_scores,  # type: ignore[arg-type]
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

    async def verify_with_visual(
        self,
        url: str,
        expected_state: str,
        criteria: list[VisualVerificationCriterion] | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        full_page: bool = False,
        use_screenshot_cache: bool = True,
    ) -> VisualVerificationResult:
        """
        Verify visual state of a web page using screenshot capture.

        Implements Anthropic's "Visual Feedback" pattern from the Agent SDK guide.
        Captures a screenshot and uses LLM-as-judge to evaluate visual state.

        Args:
            url: URL to verify
            expected_state: Description of expected visual state
            criteria: Visual criteria to evaluate (default: all)
            viewport_width: Viewport width for screenshot
            viewport_height: Viewport height for screenshot
            full_page: Whether to capture full page
            use_screenshot_cache: Whether to use screenshot caching (default: True)

        Returns:
            VisualVerificationResult with visual analysis
        """
        start_time = time.perf_counter()

        # Record URL count (always 1 for single URL verification)
        record_visual_verification_urls(1)

        with tracer.start_as_current_span("verifier.verify_with_visual") as span:
            span.set_attribute("visual.url", url)
            span.set_attribute("visual.viewport_width", viewport_width)
            span.set_attribute("visual.viewport_height", viewport_height)
            span.set_attribute("visual.use_cache", use_screenshot_cache)

            effective_criteria = criteria or list(VisualVerificationCriterion)

            # Try to get screenshot from cache first
            screenshot_result = None
            cache_key = None

            if use_screenshot_cache:
                try:
                    cache_key = generate_screenshot_cache_key(url)
                    cache = get_screenshot_cache()
                    cached_screenshot = await cache.aget(cache_key)

                    if cached_screenshot is not None:
                        # Cache hit - use cached screenshot
                        screenshot_result = cached_screenshot
                        record_screenshot_cache_hit()
                        logger.debug(
                            "Screenshot cache hit",
                            extra={"url": url, "cache_key": cache_key},
                        )
                        span.set_attribute("visual.cache_hit", True)
                    else:
                        record_screenshot_cache_miss()
                        span.set_attribute("visual.cache_hit", False)
                except Exception as cache_error:
                    # Cache errors should not prevent verification
                    logger.debug(
                        "Screenshot cache lookup failed, proceeding with capture",
                        extra={"url": url, "error": str(cache_error)},
                    )
                    record_screenshot_cache_miss()
                    span.set_attribute("visual.cache_hit", False)

            # Capture screenshot with retry logic (if not cached)
            last_screenshot_error: Exception | None = None

            if screenshot_result is None:
                try:
                    from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

                    for attempt in range(1, VISUAL_VERIFICATION_MAX_ATTEMPTS + 1):
                        try:
                            screenshot_result = await capture_screenshot.ainvoke(
                                {
                                    "url": url,
                                    "viewport_width": viewport_width,
                                    "viewport_height": viewport_height,
                                    "full_page": full_page,
                                }
                            )
                            # Success - cache the result and break out of retry loop
                            if use_screenshot_cache and cache_key and screenshot_result:
                                try:
                                    cache = get_screenshot_cache()
                                    await cache.aset(cache_key, screenshot_result, ttl=SCREENSHOT_CACHE_TTL)
                                    logger.debug(
                                        "Screenshot cached",
                                        extra={"url": url, "cache_key": cache_key, "ttl": SCREENSHOT_CACHE_TTL},
                                    )
                                except Exception as cache_set_error:
                                    # Cache errors should not prevent verification
                                    logger.debug(
                                        "Failed to cache screenshot",
                                        extra={"url": url, "error": str(cache_set_error)},
                                    )
                            break

                        except Exception as screenshot_error:
                            last_screenshot_error = screenshot_error

                            # Check if retryable
                            if not _is_retryable_exception(screenshot_error):
                                # Non-retryable error - fail immediately (no retry)
                                logger.warning(
                                    "Screenshot capture failed with non-retryable error",
                                    extra={"url": url, "error": str(screenshot_error), "attempt": attempt},
                                )
                                # Break to fall through to error handling
                                break

                            # Retryable error - check if we have attempts left
                            if attempt >= VISUAL_VERIFICATION_MAX_ATTEMPTS:
                                logger.warning(
                                    "Screenshot capture exhausted retries",
                                    extra={
                                        "url": url,
                                        "error": str(screenshot_error),
                                        "max_attempts": VISUAL_VERIFICATION_MAX_ATTEMPTS,
                                    },
                                )
                                # Fall through to error handling
                                break

                            # Calculate backoff and retry
                            delay = _calculate_backoff_delay(attempt)
                            logger.info(
                                "Retrying screenshot capture after transient error",
                                extra={
                                    "url": url,
                                    "attempt": attempt,
                                    "delay_seconds": delay,
                                    "error": str(screenshot_error),
                                },
                            )
                            record_visual_verification_retry("screenshot")
                            await asyncio.sleep(delay)

                except ImportError as import_error:
                    logger.error(
                        "Screenshot tools not available",
                        extra={"error": str(import_error)},
                    )
                    last_screenshot_error = import_error

                # Handle case where all retries exhausted
                if screenshot_result is None and last_screenshot_error is not None:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    record_visual_verification_duration(duration_ms)
                    record_visual_verification_request("failed")

                    return VisualVerificationResult(
                        passed=False,
                        overall_score=0.0,
                        feedback=f"Screenshot capture failed after {VISUAL_VERIFICATION_MAX_ATTEMPTS} retry attempts: {last_screenshot_error!s}",
                        requires_refinement=True,
                        critical_issues=[f"Screenshot capture exhausted retries: {last_screenshot_error!s}"],
                        url=url,
                        screenshot_captured=False,
                        visual_observations=[],
                    )

            # Check for screenshot error in result
            if screenshot_result and "error" in screenshot_result:
                logger.warning(
                    "Screenshot capture failed",
                    extra={"url": url, "error": screenshot_result["error"]},
                )
                # Record metrics for screenshot error
                duration_ms = (time.perf_counter() - start_time) * 1000
                record_visual_verification_duration(duration_ms)
                record_visual_verification_request("screenshot_error")

                return VisualVerificationResult(
                    passed=False,
                    overall_score=0.0,
                    feedback=f"Screenshot capture failed: {screenshot_result['error']}",
                    requires_refinement=True,
                    critical_issues=[f"Could not capture screenshot: {screenshot_result['error']}"],
                    url=url,
                    screenshot_captured=False,
                    visual_observations=[],
                )

            # Guard against None screenshot_result (shouldn't happen due to earlier checks)
            if screenshot_result is None:
                return VisualVerificationResult(
                    passed=False,
                    overall_score=0.0,
                    feedback="Screenshot result was None unexpectedly",
                    requires_refinement=True,
                    critical_issues=["Screenshot result was None"],
                    url=url,
                    screenshot_captured=False,
                    visual_observations=[],
                )

            # Build visual verification prompt with image
            prompt_messages = self._build_visual_verification_prompt(
                expected_state=expected_state,
                url=url,
                criteria=effective_criteria,
                image_data=screenshot_result.get("image_data"),
                mime_type=screenshot_result.get("mime_type", "image/png"),
            )

            # Get LLM judgment with multimodal input - with retry logic
            llm_response = None
            last_llm_error: Exception | None = None

            for llm_attempt in range(1, VISUAL_VERIFICATION_MAX_ATTEMPTS + 1):
                try:
                    # Cast to expected type (HumanMessage is a subtype of BaseMessage)
                    messages: list[BaseMessage | dict[str, Any]] = list(prompt_messages)
                    llm_response = await self.llm.ainvoke(messages)
                    # Success - break out of retry loop
                    break

                except Exception as llm_error:
                    last_llm_error = llm_error

                    # Check if retryable
                    if not _is_retryable_exception(llm_error):
                        # Non-retryable error - fail immediately (no retry)
                        logger.warning(
                            "LLM invocation failed with non-retryable error",
                            extra={"url": url, "error": str(llm_error), "attempt": llm_attempt},
                        )
                        # Break to fall through to error handling at line 891+
                        break

                    # Retryable error - check if we have attempts left
                    if llm_attempt >= VISUAL_VERIFICATION_MAX_ATTEMPTS:
                        logger.warning(
                            "LLM invocation exhausted retries",
                            extra={
                                "url": url,
                                "error": str(llm_error),
                                "max_attempts": VISUAL_VERIFICATION_MAX_ATTEMPTS,
                            },
                        )
                        # Fall through to error handling
                        break

                    # Calculate backoff and retry
                    delay = _calculate_backoff_delay(llm_attempt)
                    logger.info(
                        "Retrying LLM invocation after transient error",
                        extra={
                            "url": url,
                            "attempt": llm_attempt,
                            "delay_seconds": delay,
                            "error": str(llm_error),
                        },
                    )
                    record_visual_verification_retry("llm")
                    await asyncio.sleep(delay)

            # Handle case where all LLM retries exhausted
            if llm_response is None and last_llm_error is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                record_visual_verification_duration(duration_ms)
                record_visual_verification_request("failed")

                return VisualVerificationResult(
                    passed=False,
                    overall_score=0.0,
                    feedback=f"LLM verification failed after {VISUAL_VERIFICATION_MAX_ATTEMPTS} retry attempts: {last_llm_error!s}",
                    requires_refinement=True,
                    critical_issues=[f"LLM verification exhausted retries: {last_llm_error!s}"],
                    url=url,
                    screenshot_captured=True,  # Screenshot was successful
                    visual_observations=[],
                )

            # At this point llm_response cannot be None (handled by return at line 900)
            assert llm_response is not None, "llm_response should not be None here"

            # Get content and ensure it's a string
            content = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
            judgment = str(content) if not isinstance(content, str) else content

            # Parse judgment into structured result
            result = self._parse_visual_verification_judgment(judgment, url=url, threshold=self.quality_threshold)

            span.set_attribute("visual.passed", result.passed)
            span.set_attribute("visual.overall_score", result.overall_score)

            # Record visual verification metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            record_visual_verification_duration(duration_ms)
            record_visual_verification_score(result.overall_score)
            record_visual_verification_request("success" if result.passed else "failed")

            metrics.successful_calls.add(1, {"operation": "verify_with_visual", "passed": str(result.passed).lower()})

            logger.info(
                "Visual verification completed",
                extra={
                    "url": url,
                    "passed": result.passed,
                    "overall_score": result.overall_score,
                    "observations_count": len(result.visual_observations),
                    "duration_ms": duration_ms,
                },
            )

            return result

    def _build_visual_verification_prompt(
        self,
        expected_state: str,
        url: str,
        criteria: list[VisualVerificationCriterion] | None = None,
        image_data: str | None = None,
        mime_type: str = "image/png",
    ) -> list[HumanMessage]:
        """
        Build visual verification prompt with multimodal content.

        Args:
            expected_state: Expected visual state description
            url: URL being verified
            criteria: Visual criteria to evaluate
            image_data: Base64-encoded image data
            mime_type: Image MIME type

        Returns:
            List of messages including image for multimodal LLM
        """
        effective_criteria = criteria or list(VisualVerificationCriterion)

        criteria_descriptions = {
            VisualVerificationCriterion.UI_LAYOUT: "Is the page layout correct and properly structured?",
            VisualVerificationCriterion.CONTENT_VISIBLE: "Is the expected content clearly visible?",
            VisualVerificationCriterion.ELEMENT_PRESENT: "Are all expected UI elements present?",
            VisualVerificationCriterion.ERROR_VISIBLE: "Are there any visible error messages or broken elements?",
            VisualVerificationCriterion.LOADING_COMPLETE: "Has the page fully loaded (no spinners or placeholders)?",
        }

        criteria_text = "\n".join(
            [f"- {criterion.value}: {criteria_descriptions[criterion]}" for criterion in effective_criteria]
        )

        prompt_text = f"""<task>
Evaluate the visual state of a web page screenshot.
</task>

<role>
You are a visual QA evaluator analyzing screenshots for correctness.
</role>

<url>{url}</url>

<expected_state>
{expected_state}
</expected_state>

<evaluation_criteria>
Evaluate the screenshot on these visual criteria (score each 0.0-1.0):
{criteria_text}

Note: For error_visible, 0.0 means no errors (good), 1.0 means many errors (bad).
</evaluation_criteria>

<instructions>
1. Analyze the screenshot carefully
2. Compare what you see to the expected state
3. Score each visual criterion from 0.0 to 1.0
4. List specific observations about what you see
5. Identify any critical visual issues
</instructions>

<output_format>
Provide your evaluation in this exact format:

VISUAL_SCORES:
- ui_layout: [0.0-1.0]
- content_visible: [0.0-1.0]
- element_present: [0.0-1.0]
- error_visible: [0.0-1.0]
- loading_complete: [0.0-1.0]

OVERALL: [0.0-1.0]

OBSERVATIONS:
- [Observation 1]
- [Observation 2]
- [etc.]

CRITICAL_ISSUES:
- [Issue 1, if any]
- [Issue 2, if any]

SUGGESTIONS:
- [Suggestion 1]
- [Suggestion 2]

REQUIRES_REFINEMENT: [yes/no]

FEEDBACK:
[Detailed feedback about the visual state]
</output_format>"""

        # Build multimodal message with image
        if image_data:
            return [
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                        },
                    ]
                )
            ]
        else:
            # No image - text-only fallback
            return [HumanMessage(content=prompt_text)]

    def _parse_visual_verification_judgment(
        self,
        judgment: str,
        url: str,
        threshold: float,
    ) -> VisualVerificationResult:
        """
        Parse visual verification LLM judgment into structured result.

        Args:
            judgment: Raw LLM judgment text
            url: URL that was verified
            threshold: Quality threshold for passing

        Returns:
            Structured VisualVerificationResult
        """
        criterion_scores: dict[str, float] = {}
        overall_score: float | None = None
        visual_observations: list[str] = []
        critical_issues: list[str] = []
        suggestions: list[str] = []
        requires_refinement = False
        feedback = ""

        lines = judgment.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("VISUAL_SCORES:"):
                current_section = "scores"
            elif line.startswith("OVERALL:"):
                current_section = "overall"
                with contextlib.suppress(ValueError, IndexError):
                    overall_score = float(line.split(":")[1].strip())
            elif line.startswith("OBSERVATIONS:"):
                current_section = "observations"
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
                with contextlib.suppress(ValueError, IndexError):
                    criterion, score_str = line.split(":", 1)
                    criterion = criterion.strip(" -")
                    score_value = float(score_str.strip())
                    criterion_scores[criterion] = score_value
            elif current_section == "observations" and line.startswith("-"):
                obs = line[1:].strip()
                if obs and obs.lower() not in ["none", "n/a", "na"]:
                    visual_observations.append(obs)
            elif current_section == "critical" and line.startswith("-"):
                issue = line[1:].strip()
                if issue and issue.lower() not in ["none", "n/a", "na"]:
                    critical_issues.append(issue)
            elif current_section == "suggestions" and line.startswith("-"):
                suggestion = line[1:].strip()
                if suggestion and suggestion.lower() not in ["none", "n/a", "na"]:
                    suggestions.append(suggestion)
            elif current_section == "feedback" and line:
                feedback += line + " "

        feedback = feedback.strip() or "No specific visual feedback provided."

        # Calculate overall score from visual criteria if not explicitly provided
        if overall_score is None:
            if criterion_scores:
                # Invert error_visible score for average (low error = good)
                adjusted_scores = []
                for k, v in criterion_scores.items():
                    if k == "error_visible":
                        adjusted_scores.append(1.0 - v)  # Invert
                    else:
                        adjusted_scores.append(v)
                overall_score = sum(adjusted_scores) / len(adjusted_scores)
                logger.info("Calculated visual overall score from criterion scores")
            else:
                overall_score = 0.5  # Default fallback
                logger.warning("Failed to parse visual scores, using default")

        passed = overall_score >= threshold and len(critical_issues) == 0

        return VisualVerificationResult(
            passed=passed,
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            feedback=feedback,
            requires_refinement=requires_refinement or not passed,
            critical_issues=critical_issues,
            suggestions=suggestions,
            url=url,
            screenshot_captured=True,
            visual_observations=visual_observations,
        )


# Convenience function for easy import
async def verify_output(
    response: str,
    user_request: str,
    conversation_context: list[BaseMessage] | None = None,
    verifier: OutputVerifier | None = None,
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
