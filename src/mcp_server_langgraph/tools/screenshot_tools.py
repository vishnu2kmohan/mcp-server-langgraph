"""
Screenshot Tool for Visual Verification

Captures webpage screenshots for visual verification in agent loops.
Uses Playwright for headless browser automation.

Requires the 'visual-verification' optional dependency:
    pip install mcp-server-langgraph[visual-verification]

Or directly:
    pip install playwright
    playwright install chromium

Usage:
    from mcp_server_langgraph.tools.screenshot_tools import capture_screenshot

    result = await capture_screenshot.ainvoke({"url": "https://example.com"})
    # result contains base64-encoded screenshot
"""

from __future__ import annotations

import base64
import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import BaseModel, Field


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
    # Resolve any FieldInfo objects to actual defaults (LangChain @tool workaround)
    resolved_viewport_width = _resolve_field_default(viewport_width, 1280)
    resolved_viewport_height = _resolve_field_default(viewport_height, 720)
    resolved_full_page = _resolve_field_default(full_page, False)
    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    _safe_log("debug", "Capturing screenshot", url=url)

    try:
        # Dynamic import to handle optional dependency
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium",
            "url": url,
        }

    browser = None
    try:
        async with async_playwright() as p:
            # Launch headless browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Set viewport size
            await page.set_viewport_size(
                {
                    "width": resolved_viewport_width,
                    "height": resolved_viewport_height,
                }
            )

            # Navigate to URL
            try:
                await page.goto(url, timeout=resolved_timeout)
                await page.wait_for_load_state("networkidle", timeout=resolved_timeout)
            except Exception as nav_error:
                error_msg = str(nav_error).lower()
                if "timeout" in error_msg:
                    return {"error": "Timeout: Page took too long to load", "url": url}
                raise

            # Get page title
            title = await page.title()

            # Capture screenshot
            screenshot_bytes = await page.screenshot(full_page=resolved_full_page)

            # Close resources
            await page.close()
            await context.close()
            await browser.close()

            # Encode as base64
            image_data = base64.b64encode(screenshot_bytes).decode("utf-8")

            result = ScreenshotResult(
                image_data=image_data,
                mime_type="image/png",
                url=url,
                title=title,
                width=resolved_viewport_width,
                height=resolved_viewport_height,
            )

            _safe_log(
                "debug",
                "Screenshot captured successfully",
                url=url,
                size_bytes=len(screenshot_bytes),
            )

            return result.model_dump()

    except TimeoutError:
        return {"error": "Timeout: Page took too long to load", "url": url}
    except Exception as e:
        error_type = type(e).__name__
        _safe_log("error", "Screenshot capture failed", url=url, error=str(e))
        return {"error": f"{error_type}: {e!s}", "url": url}
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass


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
    # Resolve any FieldInfo objects to actual defaults
    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    _safe_log("debug", "Capturing element screenshot", url=url, selector=selector)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium",
            "url": url,
        }

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.set_viewport_size({"width": 1280, "height": 720})

            try:
                await page.goto(url, timeout=resolved_timeout)
                await page.wait_for_load_state("networkidle", timeout=resolved_timeout)
            except Exception as nav_error:
                error_msg = str(nav_error).lower()
                if "timeout" in error_msg:
                    return {"error": "Timeout: Page took too long to load", "url": url}
                raise

            title = await page.title()

            # Locate and screenshot the element
            element = page.locator(selector)
            screenshot_bytes = await element.screenshot()

            await page.close()
            await context.close()
            await browser.close()

            image_data = base64.b64encode(screenshot_bytes).decode("utf-8")

            result = ElementScreenshotResult(
                image_data=image_data,
                mime_type="image/png",
                url=url,
                selector=selector,
                title=title,
            )

            _safe_log(
                "debug",
                "Element screenshot captured successfully",
                url=url,
                selector=selector,
                size_bytes=len(screenshot_bytes),
            )

            return result.model_dump()

    except TimeoutError:
        return {"error": "Timeout: Page took too long to load", "url": url}
    except Exception as e:
        error_type = type(e).__name__
        _safe_log(
            "error",
            "Element screenshot capture failed",
            url=url,
            selector=selector,
            error=str(e),
        )
        return {"error": f"{error_type}: {e!s}", "url": url}
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass


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
    # Resolve any FieldInfo objects to actual defaults
    resolved_timeout = _resolve_field_default(timeout, 30000)
    resolved_format = _resolve_field_default(format, "A4")
    resolved_print_background = _resolve_field_default(print_background, True)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    _safe_log("debug", "Capturing PDF", url=url)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium",
            "url": url,
        }

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, timeout=resolved_timeout)
                await page.wait_for_load_state("networkidle", timeout=resolved_timeout)
            except Exception as nav_error:
                error_msg = str(nav_error).lower()
                if "timeout" in error_msg:
                    return {"error": "Timeout: Page took too long to load", "url": url}
                raise

            title = await page.title()

            # Generate PDF
            pdf_bytes = await page.pdf(
                format=resolved_format,
                print_background=resolved_print_background,
            )

            await page.close()
            await context.close()
            await browser.close()

            pdf_data = base64.b64encode(pdf_bytes).decode("utf-8")

            result = PDFResult(
                pdf_data=pdf_data,
                mime_type="application/pdf",
                url=url,
                title=title,
            )

            _safe_log(
                "debug",
                "PDF captured successfully",
                url=url,
                size_bytes=len(pdf_bytes),
            )

            return result.model_dump()

    except TimeoutError:
        return {"error": "Timeout: Page took too long to load", "url": url}
    except Exception as e:
        error_type = type(e).__name__
        _safe_log("error", "PDF capture failed", url=url, error=str(e))
        return {"error": f"{error_type}: {e!s}", "url": url}
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass


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
    # Resolve any FieldInfo objects to actual defaults
    resolved_viewport_width = _resolve_field_default(viewport_width, 1280)
    resolved_viewport_height = _resolve_field_default(viewport_height, 720)
    resolved_timeout = _resolve_field_default(timeout, 30000)

    # Validate URL
    error = _validate_url(url)
    if error:
        return {"error": error, "url": url}

    _safe_log("debug", "Wait and capture screenshot", url=url, wait_for=wait_for)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium",
            "url": url,
        }

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.set_viewport_size(
                {
                    "width": resolved_viewport_width,
                    "height": resolved_viewport_height,
                }
            )

            try:
                await page.goto(url, timeout=resolved_timeout)
                await page.wait_for_load_state("networkidle", timeout=resolved_timeout)
            except Exception as nav_error:
                error_msg = str(nav_error).lower()
                if "timeout" in error_msg:
                    return {"error": "Timeout: Page took too long to load", "url": url}
                raise

            # Wait for the specified selector
            try:
                await page.wait_for_selector(wait_for, timeout=resolved_timeout)
            except TimeoutError:
                return {
                    "error": f"Timeout: Element '{wait_for}' did not appear",
                    "url": url,
                }

            title = await page.title()

            # Capture screenshot
            screenshot_bytes = await page.screenshot()

            await page.close()
            await context.close()
            await browser.close()

            image_data = base64.b64encode(screenshot_bytes).decode("utf-8")

            result = {
                "image_data": image_data,
                "mime_type": "image/png",
                "url": url,
                "title": title,
                "waited_for": wait_for,
                "width": resolved_viewport_width,
                "height": resolved_viewport_height,
            }

            _safe_log(
                "debug",
                "Wait and capture completed successfully",
                url=url,
                wait_for=wait_for,
                size_bytes=len(screenshot_bytes),
            )

            return result

    except TimeoutError:
        return {"error": "Timeout: Page took too long to load", "url": url}
    except Exception as e:
        error_type = type(e).__name__
        _safe_log(
            "error",
            "Wait and capture failed",
            url=url,
            wait_for=wait_for,
            error=str(e),
        )
        return {"error": f"{error_type}: {e!s}", "url": url}
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
