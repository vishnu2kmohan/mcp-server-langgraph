"""
Tests for Visual Verification Integration (TDD RED Phase)

Tests for integrating screenshot capture into the agent verification workflow.
Implements Anthropic's "Visual Feedback" pattern from the Agent SDK guide.

References:
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests as visual_verification
pytestmark = [pytest.mark.unit, pytest.mark.visual_verification]


# =============================================================================
# Tool Registry Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationToolRegistration:
    """Tests for registering screenshot tool in tool registry."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_capture_screenshot_importable_from_registry(self):
        """Test that capture_screenshot can be imported from tools registry."""
        from mcp_server_langgraph.tools import capture_screenshot

        assert capture_screenshot is not None
        # Should be a LangChain tool
        assert hasattr(capture_screenshot, "name")
        assert capture_screenshot.name == "capture_screenshot"

    def test_visual_verification_tools_group_exists(self):
        """Test VISUAL_VERIFICATION_TOOLS group exists in registry."""
        from mcp_server_langgraph.tools import VISUAL_VERIFICATION_TOOLS

        assert isinstance(VISUAL_VERIFICATION_TOOLS, list)
        assert len(VISUAL_VERIFICATION_TOOLS) >= 1

    def test_visual_verification_tools_contain_screenshot(self):
        """Test that capture_screenshot is in VISUAL_VERIFICATION_TOOLS."""
        from mcp_server_langgraph.tools import VISUAL_VERIFICATION_TOOLS

        tool_names = [t.name for t in VISUAL_VERIFICATION_TOOLS]
        assert "capture_screenshot" in tool_names

    def test_get_tools_supports_visual_verification_category(self):
        """Test that get_tools() supports 'visual_verification' category."""
        from mcp_server_langgraph.tools import get_tools

        tools = get_tools(categories=["visual_verification"])
        tool_names = [t.name for t in tools]
        assert "capture_screenshot" in tool_names

    def test_get_all_tools_excludes_visual_verification_by_default(self):
        """Test that visual verification tools are excluded by default (opt-in)."""
        from mcp_server_langgraph.tools import get_all_tools

        tools = get_all_tools()
        tool_names = [t.name for t in tools]
        # Screenshot tool should NOT be in default tool list (requires opt-in)
        assert "capture_screenshot" not in tool_names

    def test_get_all_tools_includes_visual_verification_when_enabled(self):
        """Test that visual verification tools are included when setting enabled."""
        from mcp_server_langgraph.tools import get_all_tools

        # Create mock settings with visual verification enabled
        mock_settings = MagicMock()
        mock_settings.enable_visual_verification = True
        mock_settings.enable_code_execution = False

        tools = get_all_tools(settings_override=mock_settings)
        tool_names = [t.name for t in tools]
        assert "capture_screenshot" in tool_names

    def test_get_tool_by_name_finds_capture_screenshot(self):
        """Test that get_tool_by_name can find capture_screenshot."""
        from mcp_server_langgraph.tools import get_tool_by_name

        # Create mock settings with visual verification enabled
        mock_settings = MagicMock()
        mock_settings.enable_visual_verification = True
        mock_settings.enable_code_execution = False

        tool = get_tool_by_name("capture_screenshot", settings_override=mock_settings)
        assert tool is not None
        assert tool.name == "capture_screenshot"


# =============================================================================
# Settings Configuration Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationSettings:
    """Tests for visual verification settings configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_visual_verification_setting_exists(self):
        """Test that enable_visual_verification setting exists."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "enable_visual_verification")

    def test_enable_visual_verification_default_false(self):
        """Test that enable_visual_verification defaults to False."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.enable_visual_verification is False

    def test_enable_visual_verification_can_be_set_true(self):
        """Test that enable_visual_verification can be enabled."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(enable_visual_verification=True)
        assert settings.enable_visual_verification is True

    def test_visual_verification_env_var(self, monkeypatch):
        """Test that visual verification can be configured via env var."""
        from mcp_server_langgraph.core.config import Settings

        monkeypatch.setenv("ENABLE_VISUAL_VERIFICATION", "true")
        settings = Settings()
        assert settings.enable_visual_verification is True


# =============================================================================
# Visual Verification Criteria Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationCriteria:
    """Tests for visual verification criteria enum."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_visual_criteria_enum_exists(self):
        """Test that VisualVerificationCriterion enum exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert VisualVerificationCriterion is not None

    def test_visual_criteria_has_ui_layout(self):
        """Test UI_LAYOUT criterion exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert hasattr(VisualVerificationCriterion, "UI_LAYOUT")
        assert VisualVerificationCriterion.UI_LAYOUT.value == "ui_layout"

    def test_visual_criteria_has_content_visible(self):
        """Test CONTENT_VISIBLE criterion exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert hasattr(VisualVerificationCriterion, "CONTENT_VISIBLE")
        assert VisualVerificationCriterion.CONTENT_VISIBLE.value == "content_visible"

    def test_visual_criteria_has_element_present(self):
        """Test ELEMENT_PRESENT criterion exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert hasattr(VisualVerificationCriterion, "ELEMENT_PRESENT")
        assert VisualVerificationCriterion.ELEMENT_PRESENT.value == "element_present"

    def test_visual_criteria_has_error_visible(self):
        """Test ERROR_VISIBLE criterion exists (negative - should be absent)."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert hasattr(VisualVerificationCriterion, "ERROR_VISIBLE")
        assert VisualVerificationCriterion.ERROR_VISIBLE.value == "error_visible"

    def test_visual_criteria_has_loading_complete(self):
        """Test LOADING_COMPLETE criterion exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        assert hasattr(VisualVerificationCriterion, "LOADING_COMPLETE")
        assert VisualVerificationCriterion.LOADING_COMPLETE.value == "loading_complete"


# =============================================================================
# Visual Verification Result Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationResult:
    """Tests for VisualVerificationResult model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_visual_result_model_exists(self):
        """Test that VisualVerificationResult model exists."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        assert VisualVerificationResult is not None

    def test_visual_result_has_screenshot_url(self):
        """Test VisualVerificationResult has url field."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        result = VisualVerificationResult(
            passed=True,
            overall_score=0.9,
            feedback="Page looks correct",
            url="https://example.com",
        )
        assert result.url == "https://example.com"

    def test_visual_result_has_visual_observations(self):
        """Test VisualVerificationResult has visual_observations field."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        result = VisualVerificationResult(
            passed=True,
            overall_score=0.9,
            feedback="Page looks correct",
            url="https://example.com",
            visual_observations=["Login button visible", "Header loads correctly"],
        )
        assert len(result.visual_observations) == 2

    def test_visual_result_has_screenshot_captured(self):
        """Test VisualVerificationResult has screenshot_captured field."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        result = VisualVerificationResult(
            passed=True,
            overall_score=0.9,
            feedback="Page looks correct",
            url="https://example.com",
            screenshot_captured=True,
        )
        assert result.screenshot_captured is True

    def test_visual_result_inherits_base_fields(self):
        """Test VisualVerificationResult has all base VerificationResult fields."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        result = VisualVerificationResult(
            passed=True,
            overall_score=0.85,
            criterion_scores={"ui_layout": 0.9},
            feedback="Good visual state",
            requires_refinement=False,
            critical_issues=[],
            suggestions=["Consider higher contrast"],
            url="https://example.com",
        )
        # Should have all base fields
        assert result.passed is True
        assert result.overall_score == 0.85
        assert result.criterion_scores == {"ui_layout": 0.9}
        assert result.feedback == "Good visual state"
        assert result.requires_refinement is False
        assert result.critical_issues == []
        assert len(result.suggestions) == 1


# =============================================================================
# OutputVerifier Visual Verification Method Tests
# =============================================================================


@pytest.fixture
def visual_verifier():
    """Create OutputVerifier instance with visual verification enabled."""
    from mcp_server_langgraph.llm.verifier import OutputVerifier

    mock_settings = MagicMock()
    mock_settings.model_name = "test-model"
    mock_settings.llm_provider = "test-provider"
    mock_settings.enable_visual_verification = True

    verifier = OutputVerifier(settings=mock_settings)
    # Mock the LLM
    verifier.llm = AsyncMock()

    return verifier


@pytest.fixture
def mock_screenshot_result():
    """Mock successful screenshot capture result."""
    return {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "mime_type": "image/png",
        "url": "https://example.com",
        "title": "Example Page",
        "width": 1280,
        "height": 720,
    }


@pytest.fixture
def good_visual_judgment():
    """Mock LLM judgment for a good visual verification."""
    return """VISUAL_SCORES:
- ui_layout: 0.95
- content_visible: 0.90
- element_present: 1.00
- error_visible: 0.00
- loading_complete: 1.00

OVERALL: 0.92

OBSERVATIONS:
- Login form is centered and properly styled
- Header logo is visible
- No error messages displayed
- Page fully loaded

CRITICAL_ISSUES:
- None

SUGGESTIONS:
- Consider increasing button contrast

REQUIRES_REFINEMENT: no

FEEDBACK:
Page displays correctly with all expected elements visible and properly laid out."""


@pytest.fixture
def poor_visual_judgment():
    """Mock LLM judgment for a failed visual verification."""
    return """VISUAL_SCORES:
- ui_layout: 0.30
- content_visible: 0.20
- element_present: 0.50
- error_visible: 1.00
- loading_complete: 0.40

OVERALL: 0.35

OBSERVATIONS:
- Error modal displayed blocking content
- Login form not visible
- Loading spinner still present
- Layout broken on mobile viewport

CRITICAL_ISSUES:
- 500 error displayed on page
- Critical content blocked by error modal

SUGGESTIONS:
- Refresh page and retry
- Check server logs

REQUIRES_REFINEMENT: yes

FEEDBACK:
Page shows critical errors and content is not properly visible. Requires immediate attention."""


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationMethod:
    """Tests for verify_with_visual() method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_verify_with_visual_method_exists(self, visual_verifier):
        """Test that verify_with_visual method exists."""
        assert hasattr(visual_verifier, "verify_with_visual")
        assert callable(visual_verifier.verify_with_visual)

    @pytest.mark.asyncio
    async def test_verify_with_visual_captures_screenshot(self, visual_verifier, mock_screenshot_result, good_visual_judgment):
        """Test that verify_with_visual captures a screenshot."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form visible",
            )

            # Screenshot should have been captured
            mock_capture.ainvoke.assert_called_once()
            call_args = mock_capture.ainvoke.call_args[0][0]
            assert call_args["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_verify_with_visual_returns_visual_result(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """Test that verify_with_visual returns VisualVerificationResult."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationResult

        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            result = await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form visible",
            )

            assert isinstance(result, VisualVerificationResult)
            assert result.passed is True
            assert result.url == "https://example.com"
            assert result.screenshot_captured is True

    @pytest.mark.asyncio
    async def test_verify_with_visual_sends_image_to_llm(self, visual_verifier, mock_screenshot_result, good_visual_judgment):
        """Test that screenshot image is sent to LLM for analysis."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form visible",
            )

            # LLM should have been called with image content
            visual_verifier.llm.ainvoke.assert_called_once()
            call_args = visual_verifier.llm.ainvoke.call_args[0][0]
            # Should contain multimodal message with image
            assert len(call_args) > 0

    @pytest.mark.asyncio
    async def test_verify_with_visual_includes_expected_state(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """Test that expected_state is included in verification prompt."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form should be centered and visible",
            )

            # Check that expected_state is in the prompt
            call_args = visual_verifier.llm.ainvoke.call_args[0][0]
            # The prompt should mention the expected state
            message_content = str(call_args)
            assert "Login form" in message_content or "expected" in message_content.lower()

    @pytest.mark.asyncio
    async def test_verify_with_visual_fails_on_poor_visual(
        self, visual_verifier, mock_screenshot_result, poor_visual_judgment
    ):
        """Test that verification fails when visual state is poor."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=poor_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            result = await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form visible",
            )

            assert result.passed is False
            assert result.overall_score < 0.5
            assert len(result.critical_issues) > 0
            assert result.requires_refinement is True

    @pytest.mark.asyncio
    async def test_verify_with_visual_handles_screenshot_error(self, visual_verifier, good_visual_judgment):
        """Test graceful handling when screenshot capture fails."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            # Screenshot capture fails
            mock_capture.ainvoke = AsyncMock(return_value={"error": "Timeout: Page took too long to load"})

            result = await visual_verifier.verify_with_visual(
                url="https://slow-example.com",
                expected_state="Page loads",
            )

            # Should fail-open with informative message
            assert result.passed is False
            assert result.screenshot_captured is False
            assert "screenshot" in result.feedback.lower() or "error" in result.feedback.lower()

    @pytest.mark.asyncio
    async def test_verify_with_visual_respects_viewport_settings(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """Test that viewport settings are passed to screenshot capture."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Mobile layout",
                viewport_width=375,
                viewport_height=812,
            )

            call_args = mock_capture.ainvoke.call_args[0][0]
            assert call_args["viewport_width"] == 375
            assert call_args["viewport_height"] == 812

    @pytest.mark.asyncio
    async def test_verify_with_visual_supports_full_page(self, visual_verifier, mock_screenshot_result, good_visual_judgment):
        """Test that full_page option is passed to screenshot capture."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Full page content",
                full_page=True,
            )

            call_args = mock_capture.ainvoke.call_args[0][0]
            assert call_args["full_page"] is True

    @pytest.mark.asyncio
    async def test_verify_with_visual_has_visual_observations(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """Test that result includes visual observations."""
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            result = await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Login form visible",
            )

            # Should have observations from visual analysis
            assert hasattr(result, "visual_observations")
            assert len(result.visual_observations) > 0

    @pytest.mark.asyncio
    async def test_verify_with_visual_specific_criteria(self, visual_verifier, mock_screenshot_result, good_visual_judgment):
        """Test verification with specific visual criteria."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            result = await visual_verifier.verify_with_visual(
                url="https://example.com",
                expected_state="Form visible",
                criteria=[
                    VisualVerificationCriterion.UI_LAYOUT,
                    VisualVerificationCriterion.ELEMENT_PRESENT,
                ],
            )

            # Criterion scores should include the specified criteria
            assert "ui_layout" in result.criterion_scores or "element_present" in result.criterion_scores


# =============================================================================
# Visual Verification Prompt Building Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestVisualVerificationPrompt:
    """Tests for visual verification prompt building."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_build_visual_prompt_method_exists(self, visual_verifier):
        """Test that _build_visual_verification_prompt method exists."""
        assert hasattr(visual_verifier, "_build_visual_verification_prompt")
        assert callable(visual_verifier._build_visual_verification_prompt)

    def test_build_visual_prompt_includes_expected_state(self, visual_verifier):
        """Test that prompt includes expected state description."""
        messages = visual_verifier._build_visual_verification_prompt(
            expected_state="Login button should be visible and enabled",
            url="https://example.com",
        )

        # Extract text content from messages (list of HumanMessage)
        prompt_content = str(messages[0].content) if messages else ""
        assert "Login button" in prompt_content or "expected" in prompt_content.lower()

    def test_build_visual_prompt_has_evaluation_criteria(self, visual_verifier):
        """Test that prompt includes visual evaluation criteria."""
        from mcp_server_langgraph.llm.verifier import VisualVerificationCriterion

        messages = visual_verifier._build_visual_verification_prompt(
            expected_state="Page loaded",
            url="https://example.com",
            criteria=[
                VisualVerificationCriterion.UI_LAYOUT,
                VisualVerificationCriterion.CONTENT_VISIBLE,
            ],
        )

        # Extract text content from messages
        prompt_content = str(messages[0].content) if messages else ""
        assert "layout" in prompt_content.lower() or "content" in prompt_content.lower()

    def test_build_visual_prompt_has_output_format(self, visual_verifier):
        """Test that prompt specifies output format."""
        messages = visual_verifier._build_visual_verification_prompt(
            expected_state="Page loaded",
            url="https://example.com",
        )

        # Extract text content from messages
        prompt_content = str(messages[0].content) if messages else ""
        # Should have structured output format
        assert "VISUAL_SCORES" in prompt_content or "SCORES" in prompt_content
        assert "OBSERVATIONS" in prompt_content


# =============================================================================
# Parsing Visual Judgment Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_tests")
class TestParseVisualJudgment:
    """Tests for parsing visual verification LLM judgments."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_parse_visual_judgment_method_exists(self, visual_verifier):
        """Test that _parse_visual_verification_judgment method exists."""
        assert hasattr(visual_verifier, "_parse_visual_verification_judgment")
        assert callable(visual_verifier._parse_visual_verification_judgment)

    def test_parse_visual_judgment_extracts_scores(self, visual_verifier, good_visual_judgment):
        """Test that visual scores are correctly extracted."""
        result = visual_verifier._parse_visual_verification_judgment(
            good_visual_judgment,
            url="https://example.com",
            threshold=0.7,
        )

        assert "ui_layout" in result.criterion_scores
        assert result.criterion_scores["ui_layout"] == 0.95

    def test_parse_visual_judgment_extracts_observations(self, visual_verifier, good_visual_judgment):
        """Test that visual observations are extracted."""
        result = visual_verifier._parse_visual_verification_judgment(
            good_visual_judgment,
            url="https://example.com",
            threshold=0.7,
        )

        assert len(result.visual_observations) > 0
        # Should contain actual observations from the mock judgment
        assert any("login" in obs.lower() or "header" in obs.lower() for obs in result.visual_observations)

    def test_parse_visual_judgment_handles_malformed(self, visual_verifier):
        """Test graceful handling of malformed visual judgment."""
        malformed = "This is not a valid visual judgment format."

        result = visual_verifier._parse_visual_verification_judgment(
            malformed,
            url="https://example.com",
            threshold=0.7,
        )

        # Should not crash, should return some result
        assert result is not None
        assert len(result.feedback) > 0


# =============================================================================
# Visual Verification Metrics Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="visual_verification_metrics_integration")
class TestVisualVerificationMetricsIntegration:
    """Tests for metrics recording during visual verification.

    Verifies that verify_with_visual() properly instruments:
    - Request counts by status
    - Duration tracking
    - Score distribution
    - URL counts
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_success_metric(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """GIVEN successful visual verification
        WHEN verify_with_visual completes
        THEN success metric should be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_request"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record success status
                mock_record.assert_called()
                call_args = mock_record.call_args[0]
                assert call_args[0] == "success"

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_failed_metric(
        self, visual_verifier, mock_screenshot_result, poor_visual_judgment
    ):
        """GIVEN failed visual verification (low score)
        WHEN verify_with_visual completes
        THEN failed metric should be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=poor_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_request"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record failed status
                mock_record.assert_called()
                call_args = mock_record.call_args[0]
                assert call_args[0] == "failed"

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_screenshot_error_metric(self, visual_verifier):
        """GIVEN screenshot capture failure
        WHEN verify_with_visual completes
        THEN screenshot_error metric should be recorded
        """
        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(return_value={"error": "Timeout"})

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_request"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record screenshot_error status
                mock_record.assert_called()
                call_args = mock_record.call_args[0]
                assert call_args[0] == "screenshot_error"

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_duration_metric(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """GIVEN visual verification execution
        WHEN verify_with_visual completes
        THEN duration metric should be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_duration"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record duration
                mock_record.assert_called()
                duration_ms = mock_record.call_args[0][0]
                assert duration_ms >= 0  # Duration must be non-negative

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_score_metric(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """GIVEN successful visual verification
        WHEN verify_with_visual completes
        THEN score metric should be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_score"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record score
                mock_record.assert_called()
                score = mock_record.call_args[0][0]
                assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_url_count_metric(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """GIVEN visual verification for single URL
        WHEN verify_with_visual completes
        THEN URL count metric should be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_urls"
            ) as mock_record:
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record URL count (1 for single URL verification)
                mock_record.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_verify_with_visual_records_metrics_on_llm_exception(
        self, visual_verifier, mock_screenshot_result
    ):
        """GIVEN LLM throws exception during verification
        WHEN verify_with_visual catches exception
        THEN error metric should still be recorded
        """
        visual_verifier.llm.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        with (
            patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture,
            patch("mcp_server_langgraph.llm.verifier.get_screenshot_cache") as mock_get_cache,
        ):
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            # Mock cache to return None (cache miss) - forces screenshot capture
            mock_cache = MagicMock()
            mock_cache.aget = AsyncMock(return_value=None)
            mock_cache.aset = AsyncMock()
            mock_get_cache.return_value = mock_cache

            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_request"
            ) as mock_record:
                # Should not raise, should handle gracefully
                await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                # Should record error status
                mock_record.assert_called()

    @pytest.mark.asyncio
    async def test_verify_with_visual_skips_metrics_when_disabled(
        self, visual_verifier, mock_screenshot_result, good_visual_judgment
    ):
        """GIVEN prometheus_client not available
        WHEN verify_with_visual completes
        THEN metrics recording should be skipped gracefully
        """
        visual_verifier.llm.ainvoke = AsyncMock(return_value=MagicMock(content=good_visual_judgment))

        with patch("mcp_server_langgraph.tools.screenshot_tools.capture_screenshot") as mock_capture:
            mock_capture.ainvoke = AsyncMock(return_value=mock_screenshot_result)

            # Simulate metrics functions being no-ops when prometheus unavailable
            with patch(
                "mcp_server_langgraph.llm.verifier.record_visual_verification_request",
                side_effect=None,
            ):
                # Should complete without error even if metrics fail
                result = await visual_verifier.verify_with_visual(
                    url="https://example.com",
                    expected_state="Login form visible",
                )

                assert result is not None
                assert result.passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
