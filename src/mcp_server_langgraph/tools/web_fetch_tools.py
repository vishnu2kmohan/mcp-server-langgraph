"""
Web fetch tools for URL content retrieval.

Provides secure URL fetching for the agent with comprehensive security controls.
"""

import ipaddress
import json
import os
import re
from typing import Annotated
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics
from mcp_server_langgraph.execution.sandbox_runner import get_sandbox_runner, SandboxError

# Configuration constants
WEB_FETCH_TIMEOUT_SECONDS = int(os.getenv("WEB_FETCH_TIMEOUT_SECONDS", "30"))
WEB_FETCH_MAX_SIZE_BYTES = int(os.getenv("WEB_FETCH_MAX_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10MB

# Domain filtering
_blocked_domains_str = os.getenv("WEB_FETCH_BLOCKED_DOMAINS", "")
WEB_FETCH_BLOCKED_DOMAINS: set[str] = {d.strip() for d in _blocked_domains_str.split(",") if d.strip()}

_allowed_domains_str = os.getenv("WEB_FETCH_ALLOWED_DOMAINS", "")
WEB_FETCH_ALLOWED_DOMAINS: set[str] = {d.strip() for d in _allowed_domains_str.split(",") if d.strip()}

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Internal IP ranges to block (SSRF protection)
BLOCKED_IP_PREFIXES = [
    "127.",  # Localhost
    "10.",  # Private Class A
    "192.168.",  # Private Class C
    "169.254.",  # Link-local
    "0.",  # Invalid
]

# Private Class B ranges (172.16.0.0 - 172.31.255.255)
PRIVATE_172_START = ipaddress.IPv4Address("172.16.0.0")
PRIVATE_172_END = ipaddress.IPv4Address("172.31.255.255")


def _is_private_ip(host: str) -> bool:
    """
    Check if a host is a private/internal IP address.

    Args:
        host: Hostname or IP address

    Returns:
        True if the host is a private IP, False otherwise
    """
    # Check for localhost hostnames
    if host.lower() in ("localhost", "localhost.localdomain", "ip6-localhost"):
        return True

    # Check for common internal hostnames
    if host.lower().endswith(".local") or host.lower().endswith(".internal"):
        return True

    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(host)

        # Check for loopback
        if ip.is_loopback:
            return True

        # Check for private networks
        if ip.is_private:
            return True

        # Check for reserved
        if ip.is_reserved:
            return True

        # Check for link-local
        return bool(ip.is_link_local)

    except ValueError:
        # Not an IP address, check prefixes for dotted-quad looking hosts
        return any(host.startswith(prefix) for prefix in BLOCKED_IP_PREFIXES)


def _validate_url(url: str) -> tuple[bool, str]:
    """
    Validate a URL for security.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if not parsed.scheme:
            return False, "Error: URL must include a scheme (https:// or http://)"

        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False, f"Error: URL scheme '{parsed.scheme}' not allowed. Use https:// or http://"

        # Check hostname exists
        if not parsed.hostname:
            return False, "Error: URL must include a hostname"

        hostname = parsed.hostname.lower()

        # Check for internal IPs (SSRF protection)
        if _is_private_ip(hostname):
            return False, f"Error: Access to internal/private IP addresses is not allowed: {hostname}"

        # Check blocked domains
        if WEB_FETCH_BLOCKED_DOMAINS:
            for blocked in WEB_FETCH_BLOCKED_DOMAINS:
                if hostname == blocked or hostname.endswith(f".{blocked}"):
                    return False, f"Error: Domain '{hostname}' is blocked"

        # Check allowed domains (if set, only these are allowed)
        if WEB_FETCH_ALLOWED_DOMAINS:
            allowed = False
            for domain in WEB_FETCH_ALLOWED_DOMAINS:
                if hostname == domain or hostname.endswith(f".{domain}"):
                    allowed = True
                    break
            if not allowed:
                return False, f"Error: Domain '{hostname}' not in allowed list"

        return True, ""

    except Exception as e:
        return False, f"Error: Invalid URL: {e}"


def _html_to_markdown(html: str) -> str:
    """
    Convert HTML to simplified markdown/text.

    This is a basic implementation. For production, consider using
    a library like html2text or markdownify.

    Args:
        html: HTML content

    Returns:
        Simplified text/markdown content
    """
    import html as html_module

    # Remove script and style elements
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements
    html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Unescape HTML entities
    html = html_module.unescape(html)

    # Clean up whitespace
    html = re.sub(r"\n\s*\n+", "\n\n", html)
    html = re.sub(r" +", " ", html)

    return html.strip()


@tool
async def web_fetch(
    url: Annotated[str, Field(description="URL to fetch (HTTP/HTTPS only)")],
    prompt: Annotated[str | None, Field(description="Optional prompt describing what to extract")] = None,
    convert_html: Annotated[bool, Field(description="Convert HTML to markdown for cleaner output")] = True,
) -> str:
    """
    Fetch content from a URL and optionally process it.

    Security controls:
    - Only HTTP/HTTPS URLs are allowed
    - Internal/private IP addresses are blocked (SSRF protection)
    - Domain allowlist/blocklist can be configured
    - Content size is limited to 10MB
    - Timeout after 30 seconds

    Use this to:
    - Retrieve web page content
    - Fetch API data
    - Access documentation

    SECURITY: Blocks internal IPs, dangerous schemes, and blocked domains.
    """
    if not settings.enable_code_execution or not (
        settings.environment.lower() in SANDBOX_ENVIRONMENTS or settings.enable_sandbox_tools
    ):
        return "Error: web_fetch is restricted to sandbox environments with code execution enabled."

    try:
        logger.info("Web fetch tool invoked", extra={"url": url})
        metrics.tool_calls.add(1, {"tool": "web_fetch"})

        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            logger.warning("URL validation failed", extra={"url": url, "error": error_msg})
            return error_msg

        runner = get_sandbox_runner()
        result = runner.run_web_fetch(url, timeout_override=WEB_FETCH_TIMEOUT_SECONDS, max_bytes=WEB_FETCH_MAX_SIZE_BYTES)

        if result.timed_out:
            error_msg = f"Error: Timeout fetching URL (>{WEB_FETCH_TIMEOUT_SECONDS}s): {url}"
            logger.warning(error_msg)
            return error_msg

        if result.exit_code != 0 or result.error_message:
            error_msg = result.error_message or result.stderr or "Unknown sandbox error"
            return f"Error fetching URL '{url}': {error_msg}"

        if not result.stdout:
            return f"Error fetching URL '{url}': Empty response from sandbox fetch"

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {
                "text": result.stdout,
                "content_type": "",
                "status": None,
                "truncated": False,
            }

        content = payload.get("text", "")
        content_type_header = payload.get("content_type") or ""
        content_type_lower = content_type_header.lower()
        truncated = bool(payload.get("truncated"))
        status = payload.get("status")

        if convert_html and "text/html" in content_type_lower:
            content = _html_to_markdown(content)

        result_text = f"URL: {url}\nContent-Type: {content_type_header}\n"
        if status:
            result_text += f"Status: {status}\n"
        result_text += "-" * 40 + "\n"

        if prompt:
            result_text += f"Extraction prompt: {prompt}\n"
            result_text += "-" * 40 + "\n"

        result_text += content

        if truncated:
            result_text += "\n\n[... content truncated at size limit ...]"

        if result.stderr:
            result_text += f"\n\n[stderr]\n{result.stderr}"

        logger.info("URL fetched successfully", extra={"url": url, "content_length": len(content)})
        return result_text

    except SandboxError as exc:
        error_msg = f"Sandbox error: {exc}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Error fetching URL '{url}': {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {e}"


SANDBOX_ENVIRONMENTS = {"test", "sandbox"}
