"""
Tests for computer use tools delegating to the sandbox runner.
"""

from __future__ import annotations

import gc
import json
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.tools]


class StubResult(SimpleNamespace):
    pass


def make_run_result(payload: dict) -> StubResult:
    return StubResult(stdout=json.dumps(payload), stderr="", exit_code=0, timed_out=False, error_message=None)


@pytest.fixture
def sandbox_enabled_settings() -> Iterator[MagicMock]:
    """Mock settings to enable sandbox computer use operations.

    The computer use tools require:
    - enable_code_execution = True
    - environment in SANDBOX_ENVIRONMENTS or enable_sandbox_tools = True
    """
    mock_settings = MagicMock()
    mock_settings.enable_code_execution = True
    mock_settings.environment = "test"
    mock_settings.enable_sandbox_tools = True
    mock_settings.code_execution_timeout = 30

    with patch("mcp_server_langgraph.tools.computer_use_tools.settings", mock_settings):
        yield mock_settings


class TestComputerUseFeatureFlag:
    def teardown_method(self) -> None:
        gc.collect()

    def test_computer_use_feature_flag_exists(self) -> None:
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_computer_use")
        assert flags.enable_computer_use is False


class TestMouseInteractionTools:
    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_mouse_click_at_coordinates(self, sandbox_enabled_settings: MagicMock) -> None:
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        run_result = make_run_result({"success": True, "action": "mouse_click", "coordinates": {"x": 100, "y": 200}})
        with (
            patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.tools.computer_use_tools.get_sandbox_runner") as mock_runner_fn,
        ):
            mock_flags.enable_computer_use = True
            mock_runner_fn.return_value.run_computer_use.return_value = run_result
            result = await mouse_click.ainvoke({"x": 100, "y": 200, "button": "left"})

        assert result["success"] is True
        assert result.get("coordinates") == {"x": 100, "y": 200}

    @pytest.mark.asyncio
    async def test_mouse_click_on_selector(self, sandbox_enabled_settings: MagicMock) -> None:
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        run_result = make_run_result({"success": True, "selector": "#submit-button"})
        with (
            patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.tools.computer_use_tools.get_sandbox_runner") as mock_runner_fn,
        ):
            mock_flags.enable_computer_use = True
            mock_runner_fn.return_value.run_computer_use.return_value = run_result
            result = await mouse_click.ainvoke({"selector": "#submit-button"})

        assert result["success"] is True
        assert result.get("selector") == "#submit-button"


class TestKeyboardTools:
    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_keyboard_type(self, sandbox_enabled_settings: MagicMock) -> None:
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_type

        run_result = make_run_result({"success": True, "text_typed": "hello"})
        with (
            patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.tools.computer_use_tools.get_sandbox_runner") as mock_runner_fn,
        ):
            mock_flags.enable_computer_use = True
            mock_runner_fn.return_value.run_computer_use.return_value = run_result
            result = await keyboard_type.ainvoke({"text": "hello"})

        assert result["success"] is True
        assert "hello" in json.dumps(result)


class TestNavigationTools:
    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_navigate(self, sandbox_enabled_settings: MagicMock) -> None:
        from mcp_server_langgraph.tools.computer_use_tools import navigate

        run_result = make_run_result({"success": True, "url": "https://example.com"})
        with (
            patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.tools.computer_use_tools.get_sandbox_runner") as mock_runner_fn,
        ):
            mock_flags.enable_computer_use = True
            mock_runner_fn.return_value.run_computer_use.return_value = run_result
            result = await navigate.ainvoke({"url": "https://example.com"})

        assert result["success"] is True
        assert result.get("url") == "https://example.com"
