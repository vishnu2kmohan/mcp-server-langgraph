"""
TDD tests for Visual Verification helper functions.

Tests the extracted helper function for visual verification logic:
- URL extraction and prioritization
- Multi-URL verification execution
- Score aggregation and result combination
"""

import gc
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.xdist_group(name="visual_verification_helper")
class TestVisualVerificationHelper:
    """Test visual verification helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_visual_verification_helper_module_exists(self) -> None:
        """GIVEN visual verification helper module
        WHEN importing
        THEN module should be importable
        """
        from mcp_server_langgraph.core import visual_verification_helper

        assert visual_verification_helper is not None

    def test_extract_urls_function_exists(self) -> None:
        """GIVEN visual verification helper module
        WHEN accessing extract_urls_from_text
        THEN function should exist
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            extract_urls_from_text,
        )

        assert callable(extract_urls_from_text)

    def test_prioritize_urls_function_exists(self) -> None:
        """GIVEN visual verification helper module
        WHEN accessing prioritize_urls
        THEN function should exist
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            prioritize_urls,
        )

        assert callable(prioritize_urls)

    def test_perform_visual_verification_function_exists(self) -> None:
        """GIVEN visual verification helper module
        WHEN accessing perform_visual_verification
        THEN function should exist
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            perform_visual_verification,
        )

        assert callable(perform_visual_verification)

    def test_combine_verification_results_function_exists(self) -> None:
        """GIVEN visual verification helper module
        WHEN accessing combine_verification_results
        THEN function should exist
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            combine_verification_results,
        )

        assert callable(combine_verification_results)


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.xdist_group(name="visual_verification_extract_urls")
class TestExtractURLs:
    """Test URL extraction from text."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_urls_finds_http_urls(self) -> None:
        """GIVEN text containing HTTP URLs
        WHEN extracting URLs
        THEN all HTTP URLs should be found
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            extract_urls_from_text,
        )

        text = "Check http://example.com for info"
        urls = extract_urls_from_text(text)

        assert len(urls) == 1
        assert urls[0] == "http://example.com"

    def test_extract_urls_finds_https_urls(self) -> None:
        """GIVEN text containing HTTPS URLs
        WHEN extracting URLs
        THEN all HTTPS URLs should be found
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            extract_urls_from_text,
        )

        text = "Visit https://secure.example.com/page"
        urls = extract_urls_from_text(text)

        assert len(urls) == 1
        assert urls[0] == "https://secure.example.com/page"

    def test_extract_urls_finds_multiple_urls(self) -> None:
        """GIVEN text containing multiple URLs
        WHEN extracting URLs
        THEN all URLs should be found in order
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            extract_urls_from_text,
        )

        text = "Check https://a.com then https://b.com and https://c.com"
        urls = extract_urls_from_text(text)

        assert len(urls) == 3
        assert urls[0] == "https://a.com"
        assert urls[1] == "https://b.com"
        assert urls[2] == "https://c.com"

    def test_extract_urls_returns_empty_for_no_urls(self) -> None:
        """GIVEN text without URLs
        WHEN extracting URLs
        THEN empty list should be returned
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            extract_urls_from_text,
        )

        text = "This text has no URLs at all."
        urls = extract_urls_from_text(text)

        assert urls == []


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.xdist_group(name="visual_verification_prioritize_urls")
class TestPrioritizeURLs:
    """Test URL prioritization logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prioritize_urls_last_reverses_order(self) -> None:
        """GIVEN URLs and priority='last'
        WHEN prioritizing
        THEN URLs should be in reversed order
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            prioritize_urls,
        )

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        result = prioritize_urls(urls, priority="last")

        assert result[0] == "https://c.com"
        assert result[1] == "https://b.com"
        assert result[2] == "https://a.com"

    def test_prioritize_urls_first_keeps_order(self) -> None:
        """GIVEN URLs and priority='first'
        WHEN prioritizing
        THEN URLs should be in original order
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            prioritize_urls,
        )

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        result = prioritize_urls(urls, priority="first")

        assert result[0] == "https://a.com"
        assert result[1] == "https://b.com"
        assert result[2] == "https://c.com"

    def test_prioritize_urls_all_keeps_order(self) -> None:
        """GIVEN URLs and priority='all'
        WHEN prioritizing
        THEN URLs should be in original order
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            prioritize_urls,
        )

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        result = prioritize_urls(urls, priority="all")

        assert result == urls

    def test_prioritize_urls_with_max_limit(self) -> None:
        """GIVEN URLs and max_urls limit
        WHEN prioritizing
        THEN result should be limited to max_urls
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            prioritize_urls,
        )

        urls = ["https://a.com", "https://b.com", "https://c.com", "https://d.com"]
        result = prioritize_urls(urls, priority="first", max_urls=2)

        assert len(result) == 2
        assert result == ["https://a.com", "https://b.com"]


@pytest.mark.unit
@pytest.mark.visual_verification
@pytest.mark.xdist_group(name="visual_verification_combine_results")
class TestCombineVerificationResults:
    """Test result combination logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_combine_results_with_no_visual(self) -> None:
        """GIVEN text verification only (no visual)
        WHEN combining results
        THEN text result should be used directly
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            combine_verification_results,
        )

        text_result = MagicMock()
        text_result.passed = True
        text_result.overall_score = 0.9
        text_result.feedback = "Good text"

        result = combine_verification_results(
            text_result=text_result,
            visual_results=[],
            text_weight=0.6,
            visual_weight=0.4,
        )

        assert result["passed"] is True
        assert result["score"] == 0.9
        assert result["feedback"] == "Good text"

    def test_combine_results_with_visual(self) -> None:
        """GIVEN text and visual results
        WHEN combining results with weights
        THEN weighted average score should be calculated
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            combine_verification_results,
        )

        text_result = MagicMock()
        text_result.passed = True
        text_result.overall_score = 0.9
        text_result.feedback = "Good text"

        visual_result = MagicMock()
        visual_result.passed = True
        visual_result.overall_score = 0.8
        visual_result.url = "https://example.com"
        visual_result.feedback = "Good visual"

        result = combine_verification_results(
            text_result=text_result,
            visual_results=[visual_result],
            text_weight=0.6,
            visual_weight=0.4,
        )

        expected_score = 0.9 * 0.6 + 0.8 * 0.4  # 0.54 + 0.32 = 0.86
        assert result["passed"] is True
        assert result["score"] == pytest.approx(expected_score, abs=0.001)

    def test_combine_results_aggregates_multiple_visual(self) -> None:
        """GIVEN text and multiple visual results
        WHEN combining results
        THEN visual scores should be averaged before weighting
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            combine_verification_results,
        )

        text_result = MagicMock()
        text_result.passed = True
        text_result.overall_score = 0.9
        text_result.feedback = "Good text"

        visual1 = MagicMock()
        visual1.passed = True
        visual1.overall_score = 0.8
        visual1.url = "https://a.com"
        visual1.feedback = "Good A"

        visual2 = MagicMock()
        visual2.passed = True
        visual2.overall_score = 0.6
        visual2.url = "https://b.com"
        visual2.feedback = "Good B"

        result = combine_verification_results(
            text_result=text_result,
            visual_results=[visual1, visual2],
            text_weight=0.6,
            visual_weight=0.4,
        )

        # Visual avg = (0.8 + 0.6) / 2 = 0.7
        # Combined = 0.9 * 0.6 + 0.7 * 0.4 = 0.54 + 0.28 = 0.82
        expected_score = 0.9 * 0.6 + 0.7 * 0.4
        assert result["score"] == pytest.approx(expected_score, abs=0.001)

    def test_combine_results_fails_if_visual_fails(self) -> None:
        """GIVEN text passes but visual fails
        WHEN combining results
        THEN combined result should fail
        """
        from mcp_server_langgraph.core.visual_verification_helper import (
            combine_verification_results,
        )

        text_result = MagicMock()
        text_result.passed = True
        text_result.overall_score = 0.9
        text_result.feedback = "Good text"

        visual_result = MagicMock()
        visual_result.passed = False
        visual_result.overall_score = 0.4
        visual_result.url = "https://example.com"
        visual_result.feedback = "Visual failed"

        result = combine_verification_results(
            text_result=text_result,
            visual_results=[visual_result],
            text_weight=0.6,
            visual_weight=0.4,
        )

        assert result["passed"] is False
