"""
Visual Verification Helper Functions.

Extracted helper functions for visual verification logic:
- URL extraction and prioritization
- Multi-URL verification execution
- Score aggregation and result combination

These functions are used by the verify_response node in agent_graph_builder.py
to perform visual verification of LLM responses containing URLs.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# URL regex pattern for extraction
URL_PATTERN = re.compile(r"https?://[^\s]+")


def extract_urls_from_text(text: str) -> list[str]:
    """
    Extract all HTTP/HTTPS URLs from text.

    Args:
        text: Text to extract URLs from

    Returns:
        List of URLs in order of appearance
    """
    if not text:
        return []
    return URL_PATTERN.findall(text)


def prioritize_urls(
    urls: list[str],
    priority: str = "last",
    max_urls: int | None = None,
) -> list[str]:
    """
    Prioritize URLs based on priority strategy.

    Args:
        urls: List of URLs to prioritize
        priority: Priority strategy ("first", "last", or "all")
        max_urls: Maximum number of URLs to return (None for all)

    Returns:
        Prioritized and limited list of URLs
    """
    if not urls:
        return []

    # Apply priority
    if priority == "last":
        # Prefer URLs at end of response (likely result URLs)
        prioritized = list(reversed(urls))
    elif priority == "first":
        # Prefer URLs at start of response
        prioritized = urls.copy()
    else:  # "all"
        prioritized = urls.copy()

    # Apply max limit
    if max_urls is not None and max_urls > 0:
        return prioritized[:max_urls]

    return prioritized


async def perform_visual_verification(
    urls: list[str],
    expected_state: str,
    output_verifier: Any,
) -> list[Any]:
    """
    Perform visual verification on multiple URLs.

    Args:
        urls: List of URLs to verify
        expected_state: Expected visual state description
        output_verifier: OutputVerifier instance with verify_with_visual method

    Returns:
        List of VisualVerificationResult objects (may be empty if all failed)
    """
    results: list[Any] = []

    for url in urls:
        try:
            result = await output_verifier.verify_with_visual(
                url=url,
                expected_state=expected_state,
            )
            results.append(result)
            logger.info(f"Visual verification for {url}: score={result.overall_score}")
        except Exception as visual_error:
            logger.warning(f"Visual verification failed for {url}: {visual_error}")
            # Continue with remaining URLs

    return results


def combine_verification_results(
    text_result: Any,
    visual_results: list[Any],
    text_weight: float = 0.6,
    visual_weight: float = 0.4,
) -> dict[str, Any]:
    """
    Combine text and visual verification results with configurable weights.

    Args:
        text_result: Text verification result (VerificationResult)
        visual_results: List of visual verification results (VisualVerificationResult)
        text_weight: Weight for text verification score (default: 0.6)
        visual_weight: Weight for visual verification score (default: 0.4)

    Returns:
        Combined result dict with keys: passed, score, feedback
    """
    if not visual_results:
        # No visual verification - use text result directly
        return {
            "passed": text_result.passed,
            "score": text_result.overall_score,
            "feedback": text_result.feedback,
        }

    # Aggregate visual verification results
    avg_visual_score = sum(r.overall_score for r in visual_results) / len(visual_results)
    all_visual_passed = all(r.passed for r in visual_results)
    visual_feedback = " | ".join(f"{r.url}: {r.feedback}" for r in visual_results)

    # Calculate combined score using configurable weights
    combined_score = (text_result.overall_score * text_weight) + (avg_visual_score * visual_weight)
    combined_passed = text_result.passed and all_visual_passed
    combined_feedback = f"Text: {text_result.feedback} | Visual ({len(visual_results)} URLs): {visual_feedback}"

    return {
        "passed": combined_passed,
        "score": combined_score,
        "feedback": combined_feedback,
    }


__all__ = [
    "extract_urls_from_text",
    "prioritize_urls",
    "perform_visual_verification",
    "combine_verification_results",
]
