"""
Unit tests for Computer Use Tools (ADR-0086 / Multi-Framework parity)

TDD: RED phase - Tests for computer use functionality.

Computer Use tools provide:
- Screen capture (existing: capture_screenshot, capture_element_screenshot)
- Mouse interactions (click, move, drag)
- Keyboard input (type, key press)
- Page scrolling
- Browser automation (navigate, fill forms)
- Screen information retrieval

Reference: Anthropic Computer Use, Google ADK Computer Use, OpenAI ComputerTool
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.tools]


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_computer_use_flag")
class TestComputerUseFeatureFlag:
    """Test computer use feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_computer_use_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN accessing enable_computer_use
        THEN it should exist as a boolean field with default=False
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_computer_use")
        assert isinstance(flags.enable_computer_use, bool)
        # Default should be False (high-risk feature)
        assert flags.enable_computer_use is False


# =============================================================================
# Mouse Interaction Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_mouse_tools")
class TestMouseInteractionTools:
    """Test mouse interaction tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mouse_click_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing mouse_click
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        assert isinstance(mouse_click, BaseTool)

    @pytest.mark.asyncio
    async def test_mouse_click_at_coordinates(self) -> None:
        """GIVEN mouse_click tool
        WHEN clicking at specific coordinates
        THEN it should execute the click action
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await mouse_click.ainvoke(
                {
                    "x": 100,
                    "y": 200,
                    "button": "left",
                }
            )

            assert result["success"] is True
            assert result["action"] == "click"
            assert result["coordinates"] == {"x": 100, "y": 200}

    @pytest.mark.asyncio
    async def test_mouse_click_on_selector(self) -> None:
        """GIVEN mouse_click tool
        WHEN clicking on a CSS selector
        THEN it should find the element and click it
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await mouse_click.ainvoke(
                {
                    "selector": "#submit-button",
                    "button": "left",
                }
            )

            assert result["success"] is True
            assert result["selector"] == "#submit-button"

    @pytest.mark.asyncio
    async def test_mouse_double_click(self) -> None:
        """GIVEN mouse_click tool
        WHEN double clicking
        THEN it should execute a double click action
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await mouse_click.ainvoke(
                {
                    "x": 100,
                    "y": 200,
                    "button": "left",
                    "click_count": 2,
                }
            )

            assert result["success"] is True
            assert result["click_count"] == 2

    def test_mouse_move_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing mouse_move
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import mouse_move

        assert isinstance(mouse_move, BaseTool)

    @pytest.mark.asyncio
    async def test_mouse_move_to_coordinates(self) -> None:
        """GIVEN mouse_move tool
        WHEN moving to coordinates
        THEN it should move the mouse cursor
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_move

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await mouse_move.ainvoke(
                {
                    "x": 500,
                    "y": 300,
                }
            )

            assert result["success"] is True
            assert result["action"] == "move"

    def test_mouse_drag_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing mouse_drag
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import mouse_drag

        assert isinstance(mouse_drag, BaseTool)

    @pytest.mark.asyncio
    async def test_mouse_drag_from_to(self) -> None:
        """GIVEN mouse_drag tool
        WHEN dragging from one point to another
        THEN it should execute the drag action
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_drag

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await mouse_drag.ainvoke(
                {
                    "start_x": 100,
                    "start_y": 100,
                    "end_x": 300,
                    "end_y": 300,
                }
            )

            assert result["success"] is True
            assert result["action"] == "drag"


# =============================================================================
# Keyboard Interaction Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_keyboard_tools")
class TestKeyboardInteractionTools:
    """Test keyboard interaction tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keyboard_type_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing keyboard_type
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import keyboard_type

        assert isinstance(keyboard_type, BaseTool)

    @pytest.mark.asyncio
    async def test_keyboard_type_text(self) -> None:
        """GIVEN keyboard_type tool
        WHEN typing text
        THEN it should type the text
        """
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_type

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await keyboard_type.ainvoke(
                {
                    "text": "Hello, World!",
                }
            )

            assert result["success"] is True
            assert result["text_typed"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_keyboard_type_in_selector(self) -> None:
        """GIVEN keyboard_type tool
        WHEN typing into a specific element
        THEN it should focus and type into that element
        """
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_type

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await keyboard_type.ainvoke(
                {
                    "text": "user@example.com",
                    "selector": "#email-input",
                }
            )

            assert result["success"] is True
            assert result["selector"] == "#email-input"

    def test_keyboard_press_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing keyboard_press
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import keyboard_press

        assert isinstance(keyboard_press, BaseTool)

    @pytest.mark.asyncio
    async def test_keyboard_press_key(self) -> None:
        """GIVEN keyboard_press tool
        WHEN pressing a key
        THEN it should press the key
        """
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_press

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await keyboard_press.ainvoke(
                {
                    "key": "Enter",
                }
            )

            assert result["success"] is True
            assert result["key_pressed"] == "Enter"

    @pytest.mark.asyncio
    async def test_keyboard_press_with_modifier(self) -> None:
        """GIVEN keyboard_press tool
        WHEN pressing a key with modifier
        THEN it should press the key combination
        """
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_press

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await keyboard_press.ainvoke(
                {
                    "key": "c",
                    "modifiers": ["Control"],
                }
            )

            assert result["success"] is True
            assert result["key_pressed"] == "c"
            assert result["modifiers"] == ["Control"]


# =============================================================================
# Scroll Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_scroll_tools")
class TestScrollTools:
    """Test scroll tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scroll_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing scroll
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import scroll

        assert isinstance(scroll, BaseTool)

    @pytest.mark.asyncio
    async def test_scroll_down(self) -> None:
        """GIVEN scroll tool
        WHEN scrolling down
        THEN it should scroll the page down
        """
        from mcp_server_langgraph.tools.computer_use_tools import scroll

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await scroll.ainvoke(
                {
                    "direction": "down",
                    "amount": 500,
                }
            )

            assert result["success"] is True
            assert result["direction"] == "down"

    @pytest.mark.asyncio
    async def test_scroll_to_element(self) -> None:
        """GIVEN scroll tool
        WHEN scrolling to an element
        THEN it should scroll the element into view
        """
        from mcp_server_langgraph.tools.computer_use_tools import scroll

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await scroll.ainvoke(
                {
                    "selector": "#footer",
                    "scroll_into_view": True,
                }
            )

            assert result["success"] is True
            assert result["scrolled_to_selector"] == "#footer"


# =============================================================================
# Screen Information Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_screen_info_tools")
class TestScreenInfoTools:
    """Test screen information tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_screen_info_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing get_screen_info
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import get_screen_info

        assert isinstance(get_screen_info, BaseTool)

    @pytest.mark.asyncio
    async def test_get_screen_info_returns_dimensions(self) -> None:
        """GIVEN get_screen_info tool
        WHEN called
        THEN it should return screen dimensions
        """
        from mcp_server_langgraph.tools.computer_use_tools import get_screen_info

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await get_screen_info.ainvoke({})

            assert "width" in result
            assert "height" in result
            assert isinstance(result["width"], int)
            assert isinstance(result["height"], int)

    def test_get_element_info_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing get_element_info
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import get_element_info

        assert isinstance(get_element_info, BaseTool)

    @pytest.mark.asyncio
    async def test_get_element_info_returns_bounds(self) -> None:
        """GIVEN get_element_info tool
        WHEN called with a selector
        THEN it should return element bounds and properties
        """
        from mcp_server_langgraph.tools.computer_use_tools import get_element_info

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await get_element_info.ainvoke(
                {
                    "selector": "#main-content",
                }
            )

            assert "bounds" in result
            assert "x" in result["bounds"]
            assert "y" in result["bounds"]
            assert "width" in result["bounds"]
            assert "height" in result["bounds"]


# =============================================================================
# Browser Navigation Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_browser_nav_tools")
class TestBrowserNavigationTools:
    """Test browser navigation tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_navigate_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing navigate
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import navigate

        assert isinstance(navigate, BaseTool)

    @pytest.mark.asyncio
    async def test_navigate_to_url(self) -> None:
        """GIVEN navigate tool
        WHEN navigating to a URL
        THEN it should navigate and return result
        """
        from mcp_server_langgraph.tools.computer_use_tools import navigate

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await navigate.ainvoke(
                {
                    "url": "https://example.com",
                }
            )

            assert result["success"] is True
            assert result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_navigate_rejects_unsafe_url(self) -> None:
        """GIVEN navigate tool
        WHEN navigating to an unsafe URL
        THEN it should reject the navigation
        """
        from mcp_server_langgraph.tools.computer_use_tools import navigate

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await navigate.ainvoke(
                {
                    "url": "http://localhost:8080",
                }
            )

            assert "error" in result

    def test_go_back_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing go_back
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import go_back

        assert isinstance(go_back, BaseTool)

    def test_go_forward_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing go_forward
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import go_forward

        assert isinstance(go_forward, BaseTool)


# =============================================================================
# Form Interaction Tools Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_form_tools")
class TestFormInteractionTools:
    """Test form interaction tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fill_form_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing fill_form
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import fill_form

        assert isinstance(fill_form, BaseTool)

    @pytest.mark.asyncio
    async def test_fill_form_with_fields(self) -> None:
        """GIVEN fill_form tool
        WHEN filling multiple form fields
        THEN it should fill all fields
        """
        from mcp_server_langgraph.tools.computer_use_tools import fill_form

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await fill_form.ainvoke(
                {
                    "fields": {
                        "#username": "testuser",
                        "#email": "test@example.com",
                        "#password": "securepass123",
                    },
                }
            )

            assert result["success"] is True
            assert result["fields_filled"] == 3

    def test_select_option_tool_exists(self) -> None:
        """GIVEN the computer use tools module
        WHEN importing select_option
        THEN it should be a LangChain tool
        """
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.computer_use_tools import select_option

        assert isinstance(select_option, BaseTool)

    @pytest.mark.asyncio
    async def test_select_option_by_value(self) -> None:
        """GIVEN select_option tool
        WHEN selecting an option by value
        THEN it should select the option
        """
        from mcp_server_langgraph.tools.computer_use_tools import select_option

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            result = await select_option.ainvoke(
                {
                    "selector": "#country-select",
                    "value": "US",
                }
            )

            assert result["success"] is True
            assert result["selected_value"] == "US"


# =============================================================================
# Security Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_computer_use_security")
class TestComputerUseSecurity:
    """Test computer use security measures."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tool_disabled_when_flag_off(self) -> None:
        """GIVEN feature flag is off
        WHEN calling any computer use tool
        THEN it should return an error
        """
        from mcp_server_langgraph.tools.computer_use_tools import mouse_click

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = False

            result = await mouse_click.ainvoke({"x": 100, "y": 100})

            assert "error" in result
            assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_keyboard_type_sanitizes_dangerous_input(self) -> None:
        """GIVEN keyboard_type tool
        WHEN typing potentially dangerous input
        THEN it should sanitize or warn
        """
        from mcp_server_langgraph.tools.computer_use_tools import keyboard_type

        with patch("mcp_server_langgraph.tools.computer_use_tools.feature_flags") as mock_flags:
            mock_flags.enable_computer_use = True

            # Try to type a command that could be dangerous
            result = await keyboard_type.ainvoke(
                {
                    "text": "rm -rf /",  # Dangerous command
                }
            )

            # Should either sanitize or warn, but not blindly execute
            assert result.get("warning") or result.get("sanitized")


# =============================================================================
# Module Exports Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_computer_use_exports")
class TestComputerUseExports:
    """Test module exports for computer use tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exports_all_tools(self) -> None:
        """GIVEN the tools module
        WHEN checking computer use exports
        THEN all tools should be exported
        """
        from mcp_server_langgraph.tools import (
            mouse_click,
            mouse_move,
            mouse_drag,
            keyboard_type,
            keyboard_press,
            scroll,
            get_screen_info,
            get_element_info,
            navigate,
            go_back,
            go_forward,
            fill_form,
            select_option,
        )

        assert mouse_click is not None
        assert mouse_move is not None
        assert mouse_drag is not None
        assert keyboard_type is not None
        assert keyboard_press is not None
        assert scroll is not None
        assert get_screen_info is not None
        assert get_element_info is not None
        assert navigate is not None
        assert go_back is not None
        assert go_forward is not None
        assert fill_form is not None
        assert select_option is not None
