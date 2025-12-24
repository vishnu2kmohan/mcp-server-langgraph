"""
Computer Use Tools (ADR-0086 / Multi-Framework parity)

Provides tools for computer automation including:
- Screen capture (existing: capture_screenshot, capture_element_screenshot)
- Mouse interactions (click, move, drag)
- Keyboard input (type, key press)
- Page scrolling
- Browser automation (navigate, fill forms)
- Screen information retrieval

These tools are designed to work with browser automation backends
like Playwright but return simulated results when no browser is available.

Reference: Anthropic Computer Use, Google ADK Computer Use, OpenAI ComputerTool
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.execution.sandbox_runner import get_sandbox_runner, SandboxError

# Patterns for dangerous input detection
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"sudo\s+",
    r"chmod\s+777",
    r"format\s+",
    r"del\s+/",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
]

SANDBOX_ENVIRONMENTS = {"test", "sandbox"}


def _check_feature_enabled() -> dict[str, Any] | None:
    """Check if computer use feature is enabled.

    Returns:
        Error dict if feature is disabled, None if enabled.
    """
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return {
            "success": False,
            "error": "Computer Use tools are restricted to sandbox environments with code execution enabled.",
        }

    if not feature_flags.enable_computer_use:
        return {
            "success": False,
            "error": "Computer Use feature is disabled. Enable with FF_ENABLE_COMPUTER_USE=true",
        }
    return None


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to navigate to.

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise
    """
    try:
        parsed = urlparse(url)
        # Block localhost, internal IPs, file:// protocol
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        if parsed.hostname and parsed.hostname.startswith("192.168."):
            return False
        return not (parsed.hostname and parsed.hostname.startswith("10."))
    except Exception:
        return False


def _check_dangerous_input(text: str) -> dict[str, Any] | None:
    """Check if text contains potentially dangerous patterns.

    Args:
        text: Text to check

    Returns:
        Warning dict if dangerous patterns found, None otherwise
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "warning": f"Potentially dangerous input detected matching pattern: {pattern}",
                "sanitized": True,
            }
    return None


def _run_computer_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Delegate computer-use actions to the sandbox runner."""
    error = _check_feature_enabled()
    if error:
        return error

    try:
        runner = get_sandbox_runner()
        result = runner.run_computer_use(action, payload)
    except SandboxError as exc:
        return {"success": False, "error": f"Sandbox error: {exc}"}

    if result.timed_out:
        return {
            "success": False,
            "error": f"Sandbox action '{action}' timed out",
            "stderr": result.stderr,
        }

    if result.exit_code != 0 or result.error_message:
        return {
            "success": False,
            "error": result.error_message or result.stderr or f"{action} failed in sandbox",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    if result.stdout:
        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return {
        "success": True,
        "action": action,
        "output": result.stdout,
        "stderr": result.stderr or "",
    }


# =============================================================================
# Mouse Interaction Tools
# =============================================================================


@tool
async def mouse_click(
    x: Annotated[int | None, Field(description="X coordinate for click (optional if selector provided)")] = None,
    y: Annotated[int | None, Field(description="Y coordinate for click (optional if selector provided)")] = None,
    selector: Annotated[str | None, Field(description="CSS selector to click (optional if coordinates provided)")] = None,
    button: Annotated[str, Field(description="Mouse button: 'left', 'right', or 'middle'")] = "left",
    click_count: Annotated[int, Field(description="Number of clicks (1 for single, 2 for double)")] = 1,
) -> dict[str, Any]:
    """
    Click at coordinates or on an element.

    Performs a mouse click at the specified coordinates or on an element
    matching the CSS selector.

    Example:
        # Click at coordinates
        mouse_click(x=100, y=200, button="left")

        # Click on element
        mouse_click(selector="#submit-button")

        # Double-click
        mouse_click(x=100, y=200, click_count=2)
    """
    if selector is None and (x is None or y is None):
        return {
            "success": False,
            "error": "Must provide either coordinates (x, y) or selector",
        }

    payload: dict[str, Any] = {
        "x": x,
        "y": y,
        "selector": selector,
        "button": button,
        "click_count": click_count,
    }
    return _run_computer_action("mouse_click", payload)


@tool
async def mouse_move(
    x: Annotated[int, Field(description="X coordinate to move to")],
    y: Annotated[int, Field(description="Y coordinate to move to")],
) -> dict[str, Any]:
    """
    Move the mouse cursor to coordinates.

    Moves the mouse cursor to the specified screen coordinates without clicking.

    Example:
        mouse_move(x=500, y=300)
    """
    return _run_computer_action(
        "mouse_move",
        {
            "x": x,
            "y": y,
        },
    )


@tool
async def mouse_drag(
    start_x: Annotated[int, Field(description="Starting X coordinate")],
    start_y: Annotated[int, Field(description="Starting Y coordinate")],
    end_x: Annotated[int, Field(description="Ending X coordinate")],
    end_y: Annotated[int, Field(description="Ending Y coordinate")],
) -> dict[str, Any]:
    """
    Drag from one point to another.

    Performs a mouse drag operation from the start coordinates to the end coordinates.

    Example:
        mouse_drag(start_x=100, start_y=100, end_x=300, end_y=300)
    """
    return _run_computer_action(
        "mouse_drag",
        {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
        },
    )


# =============================================================================
# Keyboard Interaction Tools
# =============================================================================


@tool
async def keyboard_type(
    text: Annotated[str, Field(description="Text to type")],
    selector: Annotated[str | None, Field(description="CSS selector of element to type into (optional)")] = None,
) -> dict[str, Any]:
    """
    Type text, optionally into a specific element.

    Types the specified text. If a selector is provided, focuses that element first.

    Example:
        # Type into focused element
        keyboard_type(text="Hello, World!")

        # Type into specific element
        keyboard_type(text="user@example.com", selector="#email-input")
    """
    warning = _check_dangerous_input(text)
    result = _run_computer_action(
        "keyboard_type",
        {
            "text": text,
            "selector": selector,
        },
    )
    if warning:
        result.update(warning)
    return result


@tool
async def keyboard_press(
    key: Annotated[str, Field(description="Key to press (e.g., 'Enter', 'Tab', 'Escape', 'a')")],
    modifiers: Annotated[list[str] | None, Field(description="Modifier keys: 'Control', 'Alt', 'Shift', 'Meta'")] = None,
) -> dict[str, Any]:
    """
    Press a key with optional modifiers.

    Presses a keyboard key, optionally with modifier keys held down.

    Example:
        # Press Enter
        keyboard_press(key="Enter")

        # Press Ctrl+C
        keyboard_press(key="c", modifiers=["Control"])

        # Press Ctrl+Shift+S
        keyboard_press(key="s", modifiers=["Control", "Shift"])
    """
    return _run_computer_action(
        "keyboard_press",
        {
            "key": key,
            "modifiers": modifiers,
        },
    )


# =============================================================================
# Scroll Tools
# =============================================================================


@tool
async def scroll(
    direction: Annotated[str | None, Field(description="Scroll direction: 'up', 'down', 'left', 'right'")] = None,
    amount: Annotated[int, Field(description="Scroll amount in pixels")] = 100,
    selector: Annotated[str | None, Field(description="CSS selector to scroll into view")] = None,
    scroll_into_view: Annotated[bool, Field(description="If true, scroll element into view")] = False,
) -> dict[str, Any]:
    """
    Scroll the page or scroll an element into view.

    Either scrolls the page by a specified amount in a direction,
    or scrolls to bring a specific element into view.

    Example:
        # Scroll down
        scroll(direction="down", amount=500)

        # Scroll element into view
        scroll(selector="#footer", scroll_into_view=True)
    """
    if scroll_into_view and selector:
        payload = {
            "selector": selector,
            "scroll_into_view": True,
        }
    elif direction:
        payload = {
            "direction": direction,
            "amount": amount,
        }
    else:
        return {
            "success": False,
            "error": "Must provide either direction or selector with scroll_into_view=True",
        }

    return _run_computer_action("scroll", payload)


# =============================================================================
# Screen Information Tools
# =============================================================================


@tool
async def get_screen_info() -> dict[str, Any]:
    """
    Get screen dimensions and information.

    Returns information about the current screen including width, height,
    and other properties.

    Example:
        info = get_screen_info()
        print(f"Screen: {info['width']}x{info['height']}")
    """
    return _run_computer_action(
        "get_screen_info",
        {},
    )


@tool
async def get_element_info(
    selector: Annotated[str, Field(description="CSS selector of the element")],
) -> dict[str, Any]:
    """
    Get information about an element.

    Returns the bounding box and properties of an element matching the selector.

    Example:
        info = get_element_info(selector="#main-content")
        print(f"Element at ({info['bounds']['x']}, {info['bounds']['y']})")
    """
    return _run_computer_action(
        "get_element_info",
        {"selector": selector},
    )


# =============================================================================
# Browser Navigation Tools
# =============================================================================


@tool
async def navigate(
    url: Annotated[str, Field(description="URL to navigate to")],
) -> dict[str, Any]:
    """
    Navigate to a URL.

    Navigates the browser to the specified URL. Only allows safe URLs
    (https:// and http:// to non-localhost addresses).

    Example:
        navigate(url="https://example.com")
    """
    if not _is_safe_url(url):
        return {
            "success": False,
            "error": f"URL '{url}' is not allowed (must be https:// or http:// to external host)",
        }

    return _run_computer_action(
        "navigate",
        {"url": url},
    )


@tool
async def go_back() -> dict[str, Any]:
    """
    Navigate back in browser history.

    Equivalent to clicking the browser's back button.

    Example:
        go_back()
    """
    return _run_computer_action("go_back", {})


@tool
async def go_forward() -> dict[str, Any]:
    """
    Navigate forward in browser history.

    Equivalent to clicking the browser's forward button.

    Example:
        go_forward()
    """
    return _run_computer_action("go_forward", {})


# =============================================================================
# Form Interaction Tools
# =============================================================================


@tool
async def fill_form(
    fields: Annotated[dict[str, str], Field(description="Dictionary mapping selectors to values")],
) -> dict[str, Any]:
    """
    Fill multiple form fields.

    Fills multiple form fields specified as a dictionary mapping CSS selectors
    to values.

    Example:
        fill_form(fields={
            "#username": "testuser",
            "#email": "test@example.com",
            "#password": "securepass123",
        })
    """
    return _run_computer_action(
        "fill_form",
        {"fields": fields},
    )


@tool
async def select_option(
    selector: Annotated[str, Field(description="CSS selector of the select element")],
    value: Annotated[str | None, Field(description="Value to select")] = None,
    label: Annotated[str | None, Field(description="Label text to select")] = None,
    index: Annotated[int | None, Field(description="Index to select (0-based)")] = None,
) -> dict[str, Any]:
    """
    Select an option from a dropdown.

    Selects an option from a <select> element by value, label, or index.

    Example:
        # Select by value
        select_option(selector="#country-select", value="US")

        # Select by label
        select_option(selector="#country-select", label="United States")

        # Select by index
        select_option(selector="#country-select", index=0)
    """
    if value is None and label is None and index is None:
        return {
            "success": False,
            "error": "Must provide value, label, or index to select",
        }

    payload: dict[str, Any] = {
        "selector": selector,
        "value": value,
        "label": label,
        "index": index,
    }
    return _run_computer_action("select_option", payload)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Mouse tools
    "mouse_click",
    "mouse_move",
    "mouse_drag",
    # Keyboard tools
    "keyboard_type",
    "keyboard_press",
    # Scroll tools
    "scroll",
    # Screen info tools
    "get_screen_info",
    "get_element_info",
    # Browser navigation
    "navigate",
    "go_back",
    "go_forward",
    # Form tools
    "fill_form",
    "select_option",
]
