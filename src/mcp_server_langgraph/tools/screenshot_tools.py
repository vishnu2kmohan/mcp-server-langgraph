"""
Screenshot Tool for Visual Verification

Captures webpage screenshots for visual verification in agent loops by
delegating to the sandbox runner (Docker/K8s). The sandbox image should
provide the required headless browser utilities.

Usage:
    from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

    result = await capture_screenshot.ainvoke({"url": "https://example.com"})
    # result contains sandbox runner output or an error message
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.execution.sandbox_runner import get_sandbox_runner, SandboxError

# =============================================================================
# Data Models
# =============================================================================


class ScreenshotResult(BaseModel):
    """Result from a screenshot capture operation.

    Contains base64-encoded image data suitable for MCP transmission
    and LLM vision analysis.
    """

    image_data: str = Field(description="Base64-encoded PNG image data")
    mime_type: str = Field(
        default="image/png",
        description="MIME type of the image",
    )
    url: str = Field(description="URL that was captured")
    title: str | None = Field(
        default=None,
        description="Page title if available",
    )
    width: int | None = Field(
        default=None,
        description="Viewport width used for capture",
    )
    height: int | None = Field(
        default=None,
        description="Viewport height used for capture",
    )


# =============================================================================
# SSRF Protection
# =============================================================================


# Private IP ranges that should be blocked
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

# Blocked hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "local",
}

SANDBOX_ENVIRONMENTS = {"test", "sandbox"}


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to access (SSRF protection).

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise

    Security:
        - Requires HTTPS
        - Blocks private IP ranges
        - Blocks localhost and internal hostnames
    """
    try:
        parsed = urlparse(url)

        # Require HTTPS
        if parsed.scheme != "https":
            return False

        # Check hostname
        hostname = parsed.hostname
        if not hostname:
            return False

        # Block known internal hostnames
        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False

        # Check if hostname is an IP address
        try:
            # Handle IPv6 addresses (remove brackets)
            if hostname.startswith("[") and hostname.endswith("]"):
                hostname = hostname[1:-1]

            ip = ipaddress.ip_address(hostname)

            # Check against private ranges
            for private_range in PRIVATE_IP_RANGES:
                if ip in private_range:
                    return False

        except ValueError:
            # Not an IP address - hostname is fine
            pass

        return True

    except Exception:
        return False


def _validate_url(url: str) -> str | None:
    """Validate URL and return error message if invalid.

    Args:
        url: URL to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not url:
        return "URL is required"

    # Check URL format
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IPv4
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        return "Invalid URL format"

    if not is_safe_url(url):
        if not url.startswith("https://"):
            return "URL must use HTTPS for security"
        return "URL blocked for security (private/internal address)"

    return None


def _check_screenshot_enabled() -> dict[str, Any] | None:
    """Ensure screenshot tools are only available in sandbox/code-execution environments."""
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return {"error": "Screenshot tools are restricted to sandbox environments with code execution enabled."}
    return None


def _run_sandbox_capture(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Delegate capture operations to the sandbox runner."""
    _safe_log("debug", "Delegating capture to sandbox", operation=operation, payload_keys=list(payload.keys()))
    try:
        runner = get_sandbox_runner()
        result = runner.run_screenshot({"operation": operation, **payload})
    except SandboxError as exc:
        return {"error": f"Sandbox error: {exc}"}

    if result.timed_out:
        return {
            "error": f"{operation} timed out in sandbox",
            "details": result.stderr or result.error_message,
        }

    if result.exit_code != 0 or result.error_message:
        return {
            "error": result.error_message or result.stderr or f"{operation} failed in sandbox",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    if not result.stdout:
        return {"error": "Empty response from sandbox", "stderr": result.stderr}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from sandbox", "raw": result.stdout, "stderr": result.stderr}

    if isinstance(data, dict) and data.get("error"):
        return data

    return data if isinstance(data, dict) else {"result": data}


# =============================================================================
# Screenshot Tool
# =============================================================================


def _safe_log(level: str, message: str, **kwargs: Any) -> None:
    """Safely log message, handling cases where observability isn't initialized."""
    try:
        from mcp_server_langgraph.observability.telemetry import logger

        getattr(logger, level)(message, **kwargs)
    except (ImportError, RuntimeError, TypeError):
        # Observability not available or logger doesn't accept kwargs - silently skip
        pass


def _resolve_field_default(value: Any, default: Any) -> Any:
    """Resolve FieldInfo to actual default value if needed.

    LangChain's @tool decorator can pass FieldInfo objects instead of
    actual values when parameters aren't provided. This helper extracts
    the actual default.
    """
    from pydantic.fields import FieldInfo

    if isinstance(value, FieldInfo):
        return default
    return value


@tool
async def capture_screenshot(
    url: str = Field(description="URL to capture (must be HTTPS)"),
    viewport_width: int = Field(
        default=1280,
        description="Viewport width in pixels (default: 1280)",
    ),
    viewport_height: int = Field(
        default=720,
        description="Viewport height in pixels (default: 720)",
    ),
    full_page: bool = Field(
        default=False,
        description="Capture full page (scrollable content)",
    ),
    timeout: int = Field(
        default=30000,
        description="Navigation timeout in milliseconds (default: 30000)",
    ),
) -> dict[str, Any]:
    """Capture a screenshot of a webpage for visual verification.

    Use this tool to visually verify web pages, check UI state,
    or capture evidence of page content for analysis.

    The screenshot is returned as base64-encoded PNG data that can be
    sent to vision-capable LLMs for analysis.

    Security:
        - Only HTTPS URLs are allowed
        - Private/internal IP addresses are blocked (SSRF protection)
        - Localhost access is blocked

    Args:
        url: URL to capture (must be HTTPS)
        viewport_width: Viewport width in pixels (default: 1280)
        viewport_height: Viewport height in pixels (default: 720)
        full_page: Capture full scrollable page content
        timeout: Navigation timeout in milliseconds

    Returns:
        Dictionary containing:
        - image_data: Base64-encoded PNG
        - mime_type: "image/png"
        - url: Captured URL
        - title: Page title (if available)
        - width/height: Actual dimensions used

        Or error dictionary if capture fails:
        - error: Error description
    """
    enabled_error = _check_screenshot_enabled()
    if enabled_error:
        return enabled_error

    resolved_viewport_width = _resolve_field_default(viewport_width, 1280)
    resolved_viewport_height = _resolve_field_default(viewport_height, 720)
    resolved_full_page = _resolve_field_default(full_page, False)
    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    result = _run_sandbox_capture(
        "capture_screenshot",
        {
            "url": url,
            "viewport_width": resolved_viewport_width,
            "viewport_height": resolved_viewport_height,
            "full_page": resolved_full_page,
            "timeout": resolved_timeout,
        },
    )
    result.setdefault("url", url)
    return result


# =============================================================================
# Element Screenshot Tool
# =============================================================================


class ElementScreenshotResult(BaseModel):
    """Result from an element screenshot capture operation.

    Contains base64-encoded image data for a specific DOM element.
    """

    image_data: str = Field(description="Base64-encoded PNG image data")
    mime_type: str = Field(
        default="image/png",
        description="MIME type of the image",
    )
    url: str = Field(description="URL that was captured")
    selector: str = Field(description="CSS selector used to find element")
    title: str | None = Field(
        default=None,
        description="Page title if available",
    )


@tool
async def capture_element_screenshot(
    url: str = Field(description="URL to capture (must be HTTPS)"),
    selector: str = Field(description="CSS selector for the element to capture"),
    timeout: int = Field(
        default=30000,
        description="Navigation timeout in milliseconds (default: 30000)",
    ),
) -> dict[str, Any]:
    """Capture a screenshot of a specific element on a webpage.

    Use this tool to capture only a specific element (like a chart, form,
    or component) instead of the full page. The element is identified
    by a CSS selector.

    Security:
        - Only HTTPS URLs are allowed
        - Private/internal IP addresses are blocked (SSRF protection)
        - Localhost access is blocked

    Args:
        url: URL to capture (must be HTTPS)
        selector: CSS selector to identify the element (e.g., "#main-content", ".chart")
        timeout: Navigation timeout in milliseconds

    Returns:
        Dictionary containing:
        - image_data: Base64-encoded PNG of the element
        - mime_type: "image/png"
        - url: Captured URL
        - selector: The selector used
        - title: Page title (if available)

        Or error dictionary if capture fails:
        - error: Error description
    """
    enabled_error = _check_screenshot_enabled()
    if enabled_error:
        return enabled_error

    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    result = _run_sandbox_capture(
        "capture_element_screenshot",
        {"url": url, "selector": selector, "timeout": resolved_timeout},
    )
    result.setdefault("url", url)
    result.setdefault("selector", selector)
    return result


# =============================================================================
# PDF Capture Tool
# =============================================================================


class PDFResult(BaseModel):
    """Result from a PDF capture operation.

    Contains base64-encoded PDF data suitable for download or analysis.
    """

    pdf_data: str = Field(description="Base64-encoded PDF data")
    mime_type: str = Field(
        default="application/pdf",
        description="MIME type of the document",
    )
    url: str = Field(description="URL that was captured")
    title: str | None = Field(
        default=None,
        description="Page title if available",
    )


@tool
async def capture_pdf(
    url: str = Field(description="URL to capture as PDF (must be HTTPS)"),
    timeout: int = Field(
        default=30000,
        description="Navigation timeout in milliseconds (default: 30000)",
    ),
    format: str = Field(
        default="A4",
        description="Page format: A4, Letter, Legal, etc. (default: A4)",
    ),
    print_background: bool = Field(
        default=True,
        description="Print background graphics (default: True)",
    ),
) -> dict[str, Any]:
    """Capture a webpage as a PDF document.

    Use this tool to generate a PDF version of a webpage, useful for
    archiving, printing, or document analysis.

    Security:
        - Only HTTPS URLs are allowed
        - Private/internal IP addresses are blocked (SSRF protection)
        - Localhost access is blocked

    Args:
        url: URL to capture as PDF (must be HTTPS)
        timeout: Navigation timeout in milliseconds
        format: Page format (A4, Letter, Legal, etc.)
        print_background: Whether to print background graphics

    Returns:
        Dictionary containing:
        - pdf_data: Base64-encoded PDF
        - mime_type: "application/pdf"
        - url: Captured URL
        - title: Page title (if available)

        Or error dictionary if capture fails:
        - error: Error description
    """
    enabled_error = _check_screenshot_enabled()
    if enabled_error:
        return enabled_error

    resolved_timeout = _resolve_field_default(timeout, 30000)
    resolved_format = _resolve_field_default(format, "A4")
    resolved_print_background = _resolve_field_default(print_background, True)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    result = _run_sandbox_capture(
        "capture_pdf",
        {
            "url": url,
            "timeout": resolved_timeout,
            "format": resolved_format,
            "print_background": resolved_print_background,
        },
    )
    result.setdefault("url", url)
    return result


# =============================================================================
# Wait and Capture Tool
# =============================================================================


@tool
async def wait_and_capture(
    url: str = Field(description="URL to capture (must be HTTPS)"),
    wait_for: str = Field(description="CSS selector to wait for before capturing"),
    viewport_width: int = Field(
        default=1280,
        description="Viewport width in pixels (default: 1280)",
    ),
    viewport_height: int = Field(
        default=720,
        description="Viewport height in pixels (default: 720)",
    ),
    timeout: int = Field(
        default=30000,
        description="Wait timeout in milliseconds (default: 30000)",
    ),
) -> dict[str, Any]:
    """Wait for a dynamic element to appear, then capture a screenshot.

    Use this tool for pages with dynamic content that loads after the
    initial page load. Specify a CSS selector to wait for before
    capturing the screenshot.

    Security:
        - Only HTTPS URLs are allowed
        - Private/internal IP addresses are blocked (SSRF protection)
        - Localhost access is blocked

    Args:
        url: URL to capture (must be HTTPS)
        wait_for: CSS selector to wait for (e.g., ".dynamic-content", "#loaded")
        viewport_width: Viewport width in pixels (default: 1280)
        viewport_height: Viewport height in pixels (default: 720)
        timeout: Wait timeout in milliseconds

    Returns:
        Dictionary containing:
        - image_data: Base64-encoded PNG
        - mime_type: "image/png"
        - url: Captured URL
        - title: Page title (if available)
        - waited_for: The selector that was waited for

        Or error dictionary if capture fails:
        - error: Error description
    """
    enabled_error = _check_screenshot_enabled()
    if enabled_error:
        return enabled_error

    resolved_viewport_width = _resolve_field_default(viewport_width, 1280)
    resolved_viewport_height = _resolve_field_default(viewport_height, 720)
    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    result = _run_sandbox_capture(
        "wait_and_capture",
        {
            "url": url,
            "wait_for": wait_for,
            "viewport_width": resolved_viewport_width,
            "viewport_height": resolved_viewport_height,
            "timeout": resolved_timeout,
        },
    )
    result.setdefault("url", url)
    result.setdefault("wait_for", wait_for)
    return result
