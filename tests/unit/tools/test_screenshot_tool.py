"""
Tests for screenshot tools delegating to the sandbox runner.
"""

import gc
import json
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.screenshot_tool]


class StubResult(SimpleNamespace):
    pass


@pytest.fixture
def sandbox_enabled_settings() -> Iterator[MagicMock]:
    """Mock settings to enable sandbox screenshot operations.

    The screenshot tools require:
    - enable_code_execution = True
    - environment in SANDBOX_ENVIRONMENTS or enable_sandbox_tools = True
    """
    mock_settings = MagicMock()
    mock_settings.enable_code_execution = True
    mock_settings.environment = "test"
    mock_settings.enable_sandbox_tools = True
    mock_settings.code_execution_timeout = 30

    with patch("mcp_server_langgraph.tools.screenshot_tools.settings", mock_settings):
        yield mock_settings


@pytest.mark.xdist_group(name="test_screenshot_tool_basic")
class TestScreenshotToolBasic:
    def teardown_method(self) -> None:
        gc.collect()

    def test_capture_screenshot_tool_exists(self):
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        assert isinstance(capture_screenshot, BaseTool)

    @pytest.mark.asyncio
    async def test_capture_screenshot_returns_json_from_runner(self, sandbox_enabled_settings: MagicMock):
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        payload = {
            "image_data": "ZmFrZQ==",
            "mime_type": "image/png",
            "url": "https://example.com",
            "title": "Test",
            "width": 1280,
            "height": 720,
        }
        run_result = StubResult(
            stdout=json.dumps(payload),
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        with patch("mcp_server_langgraph.tools.screenshot_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_screenshot.return_value = run_result
            result = await capture_screenshot.ainvoke({"url": "https://example.com"})

        assert result["image_data"] == payload["image_data"]
        assert result["mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_capture_screenshot_validates_url(self):
        from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

        result = await capture_screenshot.ainvoke({"url": "http://example.com"})
        assert "error" in result


@pytest.mark.xdist_group(name="test_element_screenshot")
class TestElementScreenshot:
    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_capture_element_screenshot_passes_selector(self, sandbox_enabled_settings: MagicMock):
        from mcp_server_langgraph.tools.screenshot_tools import capture_element_screenshot

        payload = {
            "image_data": "ZmFrZQ==",
            "mime_type": "image/png",
            "url": "https://example.com",
            "selector": "#main",
            "title": "Test",
        }
        run_result = StubResult(
            stdout=json.dumps(payload),
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        with patch("mcp_server_langgraph.tools.screenshot_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_screenshot.return_value = run_result
            result = await capture_element_screenshot.ainvoke({"url": "https://example.com", "selector": "#main"})

        assert result["selector"] == "#main"
        assert "image_data" in result
