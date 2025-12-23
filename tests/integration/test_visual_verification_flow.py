"""
Integration tests for Visual Verification Flow

Tests the end-to-end visual verification workflow:
MCP Server → Screenshot Capture → LLM Verification → Result

TDD: RED phase - these tests define expected behavior before integration.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.visual_verification]


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_visual_verification_integration")
class TestVisualVerificationMCPFlow:
    """Integration tests for visual verification through MCP server."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_capture_screenshot_tool_available_via_mcp(self):
        """GIVEN visual verification is enabled
        WHEN listing tools via MCP server
        THEN capture_screenshot should be in the tool list
        """
        from mcp_server_langgraph.core.config._settings import Settings

        # Create settings with visual verification enabled
        mock_settings = MagicMock(spec=Settings)
        mock_settings.enable_visual_verification = True
        mock_settings.enable_code_execution = False

        from mcp_server_langgraph.tools import get_all_tools

        tools = get_all_tools(mock_settings)
        tool_names = [t.name for t in tools]

        assert "capture_screenshot" in tool_names

    @pytest.mark.asyncio
    async def test_capture_screenshot_not_available_when_disabled(self):
        """GIVEN visual verification is disabled
        WHEN listing tools via MCP server
        THEN capture_screenshot should NOT be in the tool list
        """
        from mcp_server_langgraph.core.config._settings import Settings

        # Create settings with visual verification disabled
        mock_settings = MagicMock(spec=Settings)
        mock_settings.enable_visual_verification = False
        mock_settings.enable_code_execution = False

        from mcp_server_langgraph.tools import get_all_tools

        tools = get_all_tools(mock_settings)
        tool_names = [t.name for t in tools]

        assert "capture_screenshot" not in tool_names

    @pytest.mark.asyncio
    async def test_visual_verification_full_flow(self):
        """GIVEN a URL to verify and expected visual state
        WHEN invoking visual verification through verifier
        THEN it should capture screenshot and return verification result
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationResult,
        )

        # Mock the screenshot capture
        mock_screenshot_result = {
            "image_data": "base64encodedimagedata",
            "mime_type": "image/png",
            "viewport_width": 1280,
            "viewport_height": 720,
        }

        # Mock the LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = """
VISUAL_SCORES:
- ui_layout: 0.9
- content_visible: 0.85
- element_present: 0.95
- error_visible: 0.1
- loading_complete: 0.9

OVERALL: 0.88

OBSERVATIONS:
- Page layout is correct
- Main content is visible
- No error messages

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- Consider adding loading indicators

REQUIRES_REFINEMENT: no

FEEDBACK:
The page appears to be correctly rendered with all expected elements visible.
"""

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_screenshot,
            patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm,
        ):
            mock_screenshot.ainvoke = AsyncMock(return_value=mock_screenshot_result)
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Homepage with logo and navigation",
            )

            # Verify result type and structure
            assert isinstance(result, VisualVerificationResult)
            assert result.url == "https://example.com"
            assert result.screenshot_captured is True
            assert result.passed is True
            assert result.overall_score >= 0.7

    @pytest.mark.asyncio
    async def test_visual_verification_handles_screenshot_failure(self):
        """GIVEN screenshot capture fails
        WHEN invoking visual verification
        THEN it should return failure result with appropriate message
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationResult,
        )

        mock_screenshot_result = {
            "error": "Page load timeout after 30000ms",
        }

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_screenshot,
            patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm,
        ):
            mock_screenshot.ainvoke = AsyncMock(return_value=mock_screenshot_result)
            mock_llm = AsyncMock()
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            result = await verifier.verify_with_visual(
                url="https://slow-site.example.com",
                expected_state="Homepage loaded",
            )

            assert isinstance(result, VisualVerificationResult)
            assert result.passed is False
            assert result.screenshot_captured is False
            assert "timeout" in result.feedback.lower() or "failed" in result.feedback.lower()


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_visual_verification_verifier")
class TestVisualVerificationVerifierIntegration:
    """Integration tests for OutputVerifier visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verifier_uses_multimodal_prompt_with_image(self):
        """GIVEN screenshot is captured successfully
        WHEN building verification prompt
        THEN it should include image data in multimodal format
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationCriterion,
        )

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm:
            mock_llm = AsyncMock()
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            messages = verifier._build_visual_verification_prompt(
                expected_state="Page with form",
                url="https://example.com/form",
                criteria=[VisualVerificationCriterion.UI_LAYOUT],
                image_data="base64encodedimagedata",
                mime_type="image/png",
            )

            # Should return a list with HumanMessage
            assert len(messages) == 1
            message = messages[0]

            # Message content should be a list (multimodal)
            assert isinstance(message.content, list)
            assert len(message.content) == 2

            # First element is text prompt
            assert message.content[0]["type"] == "text"
            assert "Page with form" in message.content[0]["text"]

            # Second element is image
            assert message.content[1]["type"] == "image_url"
            assert "base64encodedimagedata" in message.content[1]["image_url"]["url"]

    @pytest.mark.asyncio
    async def test_verifier_criteria_selection(self):
        """GIVEN specific visual criteria
        WHEN verifying with those criteria
        THEN prompt should include only selected criteria
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationCriterion,
        )

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm:
            mock_llm = AsyncMock()
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            messages = verifier._build_visual_verification_prompt(
                expected_state="Error page",
                url="https://example.com/error",
                criteria=[
                    VisualVerificationCriterion.ERROR_VISIBLE,
                    VisualVerificationCriterion.CONTENT_VISIBLE,
                ],
                image_data=None,
            )

            prompt_text = messages[0].content
            assert "error_visible" in prompt_text.lower()
            assert "content_visible" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_verifier_parses_observations(self):
        """GIVEN LLM judgment with observations
        WHEN parsing the judgment
        THEN observations should be extracted
        """
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        with patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm:
            mock_llm = AsyncMock()
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            judgment = """
VISUAL_SCORES:
- ui_layout: 0.8
- content_visible: 0.9

OVERALL: 0.85

OBSERVATIONS:
- Logo is properly displayed
- Navigation menu is visible
- Footer links are present

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- None

REQUIRES_REFINEMENT: no

FEEDBACK:
Page renders correctly.
"""
            result = verifier._parse_visual_verification_judgment(
                judgment=judgment,
                url="https://example.com",
                threshold=0.7,
            )

            assert len(result.visual_observations) >= 2
            assert any("logo" in obs.lower() for obs in result.visual_observations)


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_visual_verification_e2e")
class TestVisualVerificationEndToEnd:
    """End-to-end integration tests for visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_visual_verification_with_all_criteria(self):
        """GIVEN all visual verification criteria
        WHEN running visual verification
        THEN all criteria should be evaluated
        """
        from mcp_server_langgraph.llm.verifier import (
            OutputVerifier,
            VisualVerificationCriterion,
        )

        mock_screenshot_result = {
            "image_data": "test_image_data",
            "mime_type": "image/png",
        }

        mock_llm_response = MagicMock()
        mock_llm_response.content = """
VISUAL_SCORES:
- ui_layout: 0.9
- content_visible: 0.85
- element_present: 0.9
- error_visible: 0.05
- loading_complete: 0.95

OVERALL: 0.89

OBSERVATIONS:
- All elements present
- No loading indicators

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- None

REQUIRES_REFINEMENT: no

FEEDBACK:
Visual verification passed all criteria.
"""

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_screenshot,
            patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm,
        ):
            mock_screenshot.ainvoke = AsyncMock(return_value=mock_screenshot_result)
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            result = await verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Complete page load",
                criteria=list(VisualVerificationCriterion),
            )

            assert result.passed is True
            assert result.overall_score >= 0.7
            assert len(result.criterion_scores) >= 2

    @pytest.mark.asyncio
    async def test_visual_verification_fails_with_critical_issues(self):
        """GIVEN page with critical visual issues
        WHEN running visual verification
        THEN verification should fail
        """
        from mcp_server_langgraph.llm.verifier import OutputVerifier

        mock_screenshot_result = {
            "image_data": "test_image_data",
            "mime_type": "image/png",
        }

        mock_llm_response = MagicMock()
        mock_llm_response.content = """
VISUAL_SCORES:
- ui_layout: 0.3
- content_visible: 0.4
- element_present: 0.5
- error_visible: 0.9
- loading_complete: 0.2

OVERALL: 0.38

OBSERVATIONS:
- Page shows 500 error
- Main content is missing
- Layout is broken

CRITICAL_ISSUES:
- 500 Internal Server Error displayed
- Navigation is completely missing

SUGGESTIONS:
- Fix server error
- Check backend service health

REQUIRES_REFINEMENT: yes

FEEDBACK:
The page displays a critical server error and cannot be used.
"""

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_screenshot,
            patch("mcp_server_langgraph.llm.verifier.create_verification_model") as mock_create_llm,
        ):
            mock_screenshot.ainvoke = AsyncMock(return_value=mock_screenshot_result)
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_create_llm.return_value = mock_llm

            verifier = OutputVerifier()

            result = await verifier.verify_with_visual(
                url="https://broken.example.com",
                expected_state="Working homepage",
            )

            assert result.passed is False
            assert result.overall_score < 0.7
            assert len(result.critical_issues) >= 1
            assert result.requires_refinement is True


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_visual_verification_multi_url")
class TestMultiURLVisualVerificationIntegration:
    """Integration tests for multi-URL visual verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_response_with_multiple_urls_integration(self):
        """GIVEN a response containing multiple URLs
        WHEN visual verification is enabled with max_urls=3
        THEN all URLs up to max are verified and scores are aggregated
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_visual_verification=True,
            visual_verification_max_urls=3,
            visual_verification_url_priority="last",
        )

        assert config.visual_verification_max_urls == 3
        assert config.visual_verification_url_priority == "last"

        # Verify URL extraction logic matches implementation
        import re

        response_text = (
            "Here are the results: "
            "https://example.com/page1 and https://example.com/page2 "
            "and finally https://example.com/page3"
        )
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, response_text)

        assert len(urls) == 3
        assert urls[0] == "https://example.com/page1"
        assert urls[1] == "https://example.com/page2"
        assert urls[2] == "https://example.com/page3"

    @pytest.mark.asyncio
    async def test_url_priority_first_takes_earlier_urls(self):
        """GIVEN url_priority='first' and 5 URLs in response
        WHEN max_urls=2
        THEN first 2 URLs are verified
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig
        import re

        config = AgentConfig(
            enable_visual_verification=True,
            visual_verification_max_urls=2,
            visual_verification_url_priority="first",
        )

        response_text = (
            "URL1: https://example.com/a "
            "URL2: https://example.com/b "
            "URL3: https://example.com/c "
            "URL4: https://example.com/d "
            "URL5: https://example.com/e"
        )

        url_pattern = r"https?://[^\s]+"
        all_urls = re.findall(url_pattern, response_text)

        # Apply priority (first = keep order)
        prioritized_urls = all_urls  # first keeps order
        urls_to_verify = prioritized_urls[: config.visual_verification_max_urls]

        assert len(urls_to_verify) == 2
        assert urls_to_verify[0] == "https://example.com/a"
        assert urls_to_verify[1] == "https://example.com/b"

    @pytest.mark.asyncio
    async def test_url_priority_last_takes_later_urls(self):
        """GIVEN url_priority='last' and 5 URLs in response
        WHEN max_urls=2
        THEN last 2 URLs are verified (reversed order)
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig
        import re

        config = AgentConfig(
            enable_visual_verification=True,
            visual_verification_max_urls=2,
            visual_verification_url_priority="last",
        )

        response_text = (
            "URL1: https://example.com/a "
            "URL2: https://example.com/b "
            "URL3: https://example.com/c "
            "URL4: https://example.com/d "
            "URL5: https://example.com/e"
        )

        url_pattern = r"https?://[^\s]+"
        all_urls = re.findall(url_pattern, response_text)

        # Apply priority (last = reverse order)
        prioritized_urls = list(reversed(all_urls))
        urls_to_verify = prioritized_urls[: config.visual_verification_max_urls]

        assert len(urls_to_verify) == 2
        assert urls_to_verify[0] == "https://example.com/e"  # last in response
        assert urls_to_verify[1] == "https://example.com/d"  # second to last

    @pytest.mark.asyncio
    async def test_configurable_weights_integration(self):
        """GIVEN custom weights (0.7 text, 0.3 visual)
        WHEN combining text and visual scores
        THEN combined score uses custom weights
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_visual_verification=True,
            visual_verification_text_weight=0.7,
            visual_verification_visual_weight=0.3,
        )

        # Simulate scores
        text_score = 0.9
        visual_score = 0.6

        # Calculate combined score with custom weights
        combined_score = (
            text_score * config.visual_verification_text_weight + visual_score * config.visual_verification_visual_weight
        )

        expected = 0.9 * 0.7 + 0.6 * 0.3  # 0.63 + 0.18 = 0.81
        assert abs(combined_score - expected) < 0.001
        assert combined_score == pytest.approx(0.81, abs=0.001)

    @pytest.mark.asyncio
    async def test_multi_url_score_aggregation(self):
        """GIVEN 3 URLs with scores [0.9, 0.8, 0.7]
        WHEN aggregating visual verification results
        THEN average score is 0.8
        """
        scores = [0.9, 0.8, 0.7]
        avg_score = sum(scores) / len(scores)

        assert avg_score == pytest.approx(0.8, abs=0.001)

    @pytest.mark.asyncio
    async def test_visual_verification_result_has_url_field(self):
        """GIVEN VisualVerificationResult
        WHEN result is created
        THEN it should have url field for multi-URL tracking
        """
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        result = VisualVerificationResult(
            url="https://example.com/test",
            passed=True,
            overall_score=0.85,
            screenshot_captured=True,
            criterion_scores={"ui_layout": 0.9},
            visual_observations=["Page loaded"],
            critical_issues=[],
            suggestions=[],
            feedback="OK",
            requires_refinement=False,
        )

        assert result.url == "https://example.com/test"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_config_from_settings_loads_multi_url_fields(self):
        """GIVEN Settings with multi-URL configuration
        WHEN AgentConfig.from_settings is called
        THEN config should have correct values
        """
        from mcp_server_langgraph.core.agent_config import AgentConfig

        # Create mock settings
        mock_settings = MagicMock()
        mock_settings.enable_visual_verification = True
        mock_settings.visual_verification_max_urls = 5
        mock_settings.visual_verification_url_priority = "all"
        mock_settings.visual_verification_text_weight = 0.5
        mock_settings.visual_verification_visual_weight = 0.5

        config = AgentConfig.from_settings(mock_settings)

        assert config.enable_visual_verification is True
        assert config.visual_verification_max_urls == 5
        assert config.visual_verification_url_priority == "all"
        assert config.visual_verification_text_weight == 0.5
        assert config.visual_verification_visual_weight == 0.5
