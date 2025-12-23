"""
Unit tests for Screenshot Tool for Visual Verification

Tests the screenshot tool that captures webpage screenshots for
visual verification in agent loops.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.screenshot_tool]


@pytest.fixture
def mock_playwright_module():
    """Create mock playwright module structure for tests.

    This fixture allows patching playwright.async_api.async_playwright
    even when playwright is not installed (optional dependency).
    """
    # Create mock module structure
    mock_playwright = MagicMock()
    mock_async_api = MagicMock()
    mock_playwright.async_api = mock_async_api

    # Save original modules (if they exist)
    orig_playwright = sys.modules.get("playwright")
    orig_async_api = sys.modules.get("playwright.async_api")

    # Inject mock modules
    sys.modules["playwright"] = mock_playwright
    sys.modules["playwright.async_api"] = mock_async_api

    yield mock_async_api

    # Restore original state
    if orig_playwright is not None:
        sys.modules["playwright"] = orig_playwright
    else:
        sys.modules.pop("playwright", None)

    if orig_async_api is not None:
        sys.modules["playwright.async_api"] = orig_async_api
    else:
        sys.modules.pop("playwright.async_api", None)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_tool_basic")
class TestScreenshotToolBasic:
    """Test suite for basic screenshot tool functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capture_screenshot_tool_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing capture_screenshot
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        assert isinstance(capture_screenshot, BaseTool)

    def test_capture_screenshot_has_correct_name(self):
        """GIVEN the capture_screenshot tool
        WHEN checking its name
        THEN it should be 'capture_screenshot'
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        assert capture_screenshot.name == "capture_screenshot"

    def test_capture_screenshot_has_description(self):
        """GIVEN the capture_screenshot tool
        WHEN checking its description
        THEN it should describe screenshot capture functionality
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        description = capture_screenshot.description.lower()
        assert "screenshot" in description or "capture" in description

    def test_capture_screenshot_schema_has_url_field(self):
        """GIVEN the capture_screenshot tool schema
        WHEN examining input fields
        THEN it should have a 'url' field
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        schema = capture_screenshot.args_schema
        assert schema is not None

        fields = schema.model_fields
        assert "url" in fields


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_tool_output")
class TestScreenshotToolOutput:
    """Test suite for screenshot tool output behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_capture_screenshot_returns_base64_image(self, mock_playwright_module):
        """GIVEN a valid URL
        WHEN capturing a screenshot
        THEN it should return base64-encoded image data
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        # Mock the browser to avoid real network calls
        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_data")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_screenshot.ainvoke({"url": "https://example.com"})

            assert isinstance(result, dict)
            assert "image_data" in result
            assert "mime_type" in result
            assert result["mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_capture_screenshot_includes_metadata(self, mock_playwright_module):
        """GIVEN a valid URL
        WHEN capturing a screenshot
        THEN it should include metadata about the capture
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_data")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.title = AsyncMock(return_value="Example Domain")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_screenshot.ainvoke({"url": "https://example.com"})

            assert "url" in result
            assert result["url"] == "https://example.com"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_tool_validation")
class TestScreenshotToolValidation:
    """Test suite for screenshot tool input validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_capture_screenshot_requires_https(self):
        """GIVEN an HTTP (non-HTTPS) URL
        WHEN capturing a screenshot
        THEN it should reject the URL for security
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        result = await capture_screenshot.ainvoke({"url": "http://insecure.com"})

        assert isinstance(result, dict)
        assert "error" in result
        assert "https" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_capture_screenshot_validates_url_format(self):
        """GIVEN an invalid URL
        WHEN capturing a screenshot
        THEN it should return an error
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        result = await capture_screenshot.ainvoke({"url": "not-a-url"})

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_capture_screenshot_blocks_private_ips(self):
        """GIVEN a private IP address URL
        WHEN capturing a screenshot
        THEN it should block SSRF attempts
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        # Test localhost
        result = await capture_screenshot.ainvoke({"url": "https://127.0.0.1"})

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_capture_screenshot_blocks_internal_hosts(self):
        """GIVEN an internal network URL
        WHEN capturing a screenshot
        THEN it should block for security
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        # Test internal host patterns
        result = await capture_screenshot.ainvoke({"url": "https://192.168.1.1"})

        assert isinstance(result, dict)
        assert "error" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_tool_options")
class TestScreenshotToolOptions:
    """Test suite for screenshot tool optional parameters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_schema_has_optional_viewport_width(self):
        """GIVEN the capture_screenshot tool schema
        WHEN examining input fields
        THEN it should have optional 'viewport_width' field
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        schema = capture_screenshot.args_schema
        fields = schema.model_fields

        assert "viewport_width" in fields
        # Should have a default value (optional)
        assert fields["viewport_width"].default is not None or not fields["viewport_width"].is_required()

    def test_schema_has_optional_viewport_height(self):
        """GIVEN the capture_screenshot tool schema
        WHEN examining input fields
        THEN it should have optional 'viewport_height' field
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        schema = capture_screenshot.args_schema
        fields = schema.model_fields

        assert "viewport_height" in fields
        assert fields["viewport_height"].default is not None or not fields["viewport_height"].is_required()

    def test_schema_has_optional_full_page(self):
        """GIVEN the capture_screenshot tool schema
        WHEN examining input fields
        THEN it should have optional 'full_page' field
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        schema = capture_screenshot.args_schema
        fields = schema.model_fields

        assert "full_page" in fields

    @pytest.mark.asyncio
    async def test_capture_screenshot_respects_viewport_size(self, mock_playwright_module):
        """GIVEN custom viewport dimensions
        WHEN capturing a screenshot
        THEN it should use the specified dimensions
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_data")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            await capture_screenshot.ainvoke(
                {
                    "url": "https://example.com",
                    "viewport_width": 1920,
                    "viewport_height": 1080,
                }
            )

            # Verify viewport was set
            mock_page.set_viewport_size.assert_called_once()
            call_args = mock_page.set_viewport_size.call_args
            assert call_args[0][0]["width"] == 1920
            assert call_args[0][0]["height"] == 1080


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_tool_error_handling")
class TestScreenshotToolErrorHandling:
    """Test suite for screenshot tool error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_capture_screenshot_handles_timeout(self, mock_playwright_module):
        """GIVEN a URL that times out
        WHEN capturing a screenshot
        THEN it should return a timeout error gracefully
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        mock_page = MagicMock()
        mock_page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_screenshot.ainvoke({"url": "https://slow-site.com"})

            assert isinstance(result, dict)
            assert "error" in result
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_capture_screenshot_handles_browser_error(self, mock_playwright_module):
        """GIVEN a browser launch failure
        WHEN capturing a screenshot
        THEN it should return an error gracefully
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(side_effect=RuntimeError("Browser not available"))

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_screenshot.ainvoke({"url": "https://example.com"})

            assert isinstance(result, dict)
            assert "error" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screenshot_models")
class TestScreenshotModels:
    """Test suite for screenshot data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_screenshot_result_model_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing ScreenshotResult
        THEN it should be a valid Pydantic model
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.tools.screenshot_tools import ScreenshotResult

        assert issubclass(ScreenshotResult, BaseModel)

    def test_screenshot_result_has_required_fields(self):
        """GIVEN ScreenshotResult model
        WHEN examining its fields
        THEN it should have image_data, mime_type, url
        """
        from mcp_server_langgraph.tools.screenshot_tools import ScreenshotResult

        fields = ScreenshotResult.model_fields
        assert "image_data" in fields
        assert "mime_type" in fields
        assert "url" in fields

    def test_screenshot_result_serializes_to_dict(self):
        """GIVEN a ScreenshotResult
        WHEN serializing to dict
        THEN it should produce valid dict for MCP transmission
        """
        from mcp_server_langgraph.tools.screenshot_tools import ScreenshotResult

        result = ScreenshotResult(
            image_data="base64_data_here",
            mime_type="image/png",
            url="https://example.com",
        )

        data = result.model_dump()
        assert data["image_data"] == "base64_data_here"
        assert data["mime_type"] == "image/png"
        assert data["url"] == "https://example.com"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_ssrf_protection")
class TestSSRFProtection:
    """Test suite for SSRF protection in screenshot tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_safe_url_function_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing is_safe_url
        THEN it should be a callable function
        """
        from mcp_server_langgraph.tools.screenshot_tools import is_safe_url

        assert callable(is_safe_url)

    def test_is_safe_url_blocks_localhost(self):
        """GIVEN a localhost URL
        WHEN checking if safe
        THEN it should return False
        """
        from mcp_server_langgraph.tools.screenshot_tools import is_safe_url

        assert not is_safe_url("https://localhost")
        assert not is_safe_url("https://127.0.0.1")
        assert not is_safe_url("https://[::1]")

    def test_is_safe_url_blocks_private_ranges(self):
        """GIVEN private IP range URLs
        WHEN checking if safe
        THEN it should return False
        """
        from mcp_server_langgraph.tools.screenshot_tools import is_safe_url

        # 10.x.x.x
        assert not is_safe_url("https://10.0.0.1")
        # 172.16.x.x - 172.31.x.x
        assert not is_safe_url("https://172.16.0.1")
        # 192.168.x.x
        assert not is_safe_url("https://192.168.1.1")

    def test_is_safe_url_allows_public_urls(self):
        """GIVEN public URL
        WHEN checking if safe
        THEN it should return True
        """
        from mcp_server_langgraph.tools.screenshot_tools import is_safe_url

        assert is_safe_url("https://example.com")
        assert is_safe_url("https://google.com")
        assert is_safe_url("https://8.8.8.8")

    def test_is_safe_url_requires_https(self):
        """GIVEN an HTTP URL
        WHEN checking if safe
        THEN it should return False
        """
        from mcp_server_langgraph.tools.screenshot_tools import is_safe_url

        assert not is_safe_url("http://example.com")


# =============================================================================
# Computer Use Expansion Tests (TDD: RED phase)
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_element_screenshot")
class TestElementScreenshot:
    """Test suite for element-specific screenshot capture."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capture_element_screenshot_tool_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing capture_element_screenshot
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.screenshot_tools import capture_element_screenshot

        assert isinstance(capture_element_screenshot, BaseTool)

    def test_capture_element_schema_has_selector_field(self):
        """GIVEN the capture_element_screenshot tool schema
        WHEN examining input fields
        THEN it should have a 'selector' field for CSS selector
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_element_screenshot

        schema = capture_element_screenshot.args_schema
        fields = schema.model_fields

        assert "selector" in fields

    @pytest.mark.asyncio
    async def test_capture_element_returns_cropped_image(self, mock_playwright_module):
        """GIVEN a valid URL and selector
        WHEN capturing an element screenshot
        THEN it should return base64 image of that element only
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_element_screenshot

        mock_element = MagicMock()
        mock_element.screenshot = AsyncMock(return_value=b"element_png_data")

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_element)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_element_screenshot.ainvoke(
                {
                    "url": "https://example.com",
                    "selector": "#main-content",
                }
            )

            assert isinstance(result, dict)
            assert "image_data" in result
            mock_page.locator.assert_called_with("#main-content")

    @pytest.mark.asyncio
    async def test_capture_element_handles_missing_element(self, mock_playwright_module):
        """GIVEN a selector that doesn't match any element
        WHEN capturing an element screenshot
        THEN it should return an error
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_element_screenshot

        mock_element = MagicMock()
        mock_element.screenshot = AsyncMock(side_effect=Exception("Element not found"))

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_element)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_element_screenshot.ainvoke(
                {
                    "url": "https://example.com",
                    "selector": "#nonexistent",
                }
            )

            assert isinstance(result, dict)
            assert "error" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pdf_capture")
class TestPDFCapture:
    """Test suite for PDF capture capability."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capture_pdf_tool_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing capture_pdf
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.screenshot_tools import capture_pdf

        assert isinstance(capture_pdf, BaseTool)

    def test_capture_pdf_schema_has_url_field(self):
        """GIVEN the capture_pdf tool schema
        WHEN examining input fields
        THEN it should have a 'url' field
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_pdf

        schema = capture_pdf.args_schema
        fields = schema.model_fields

        assert "url" in fields

    @pytest.mark.asyncio
    async def test_capture_pdf_returns_base64_pdf(self, mock_playwright_module):
        """GIVEN a valid URL
        WHEN capturing as PDF
        THEN it should return base64-encoded PDF data
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_pdf

        mock_page = MagicMock()
        mock_page.pdf = AsyncMock(return_value=b"fake_pdf_data")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await capture_pdf.ainvoke({"url": "https://example.com"})

            assert isinstance(result, dict)
            assert "pdf_data" in result
            assert "mime_type" in result
            assert result["mime_type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_capture_pdf_respects_ssrf_protection(self):
        """GIVEN a private IP URL
        WHEN capturing as PDF
        THEN it should block for security
        """
        from mcp_server_langgraph.tools.screenshot_tools import capture_pdf

        result = await capture_pdf.ainvoke({"url": "https://192.168.1.1"})

        assert isinstance(result, dict)
        assert "error" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_wait_for_selector")
class TestWaitForSelector:
    """Test suite for wait_for_selector tool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_wait_and_screenshot_tool_exists(self):
        """GIVEN the screenshot_tools module
        WHEN importing wait_and_capture
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.screenshot_tools import wait_and_capture

        assert isinstance(wait_and_capture, BaseTool)

    def test_wait_and_capture_schema_has_wait_selector(self):
        """GIVEN the wait_and_capture tool schema
        WHEN examining input fields
        THEN it should have 'wait_for' selector field
        """
        from mcp_server_langgraph.tools.screenshot_tools import wait_and_capture

        schema = wait_and_capture.args_schema
        fields = schema.model_fields

        assert "wait_for" in fields

    @pytest.mark.asyncio
    async def test_wait_and_capture_waits_for_element(self, mock_playwright_module):
        """GIVEN a URL and wait_for selector
        WHEN capturing screenshot
        THEN it should wait for element before capturing
        """
        from mcp_server_langgraph.tools.screenshot_tools import wait_and_capture

        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_data")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await wait_and_capture.ainvoke(
                {
                    "url": "https://example.com",
                    "wait_for": ".dynamic-content",
                }
            )

            assert isinstance(result, dict)
            mock_page.wait_for_selector.assert_called()

    @pytest.mark.asyncio
    async def test_wait_and_capture_handles_timeout(self, mock_playwright_module):
        """GIVEN a selector that never appears
        WHEN waiting for element
        THEN it should return timeout error
        """
        from mcp_server_langgraph.tools.screenshot_tools import wait_and_capture

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=TimeoutError("Waiting for selector timed out"))
        mock_page.close = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "playwright.async_api.async_playwright",
            return_value=mock_async_playwright,
        ):
            result = await wait_and_capture.ainvoke(
                {
                    "url": "https://example.com",
                    "wait_for": ".never-appears",
                }
            )

            assert isinstance(result, dict)
            assert "error" in result
