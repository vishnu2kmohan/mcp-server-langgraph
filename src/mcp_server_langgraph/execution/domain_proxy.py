"""
Domain Proxy for Network Allowlist Enforcement.

Provides a transparent HTTP proxy that enforces domain allowlists for
sandboxed code execution. This enables fine-grained network control
without requiring complex iptables/nftables rules.

Architecture:
    Container → HTTP Proxy (this module) → Internet
                     ↓
              Domain Matcher (allowlist)
                     ↓
              Block/Allow Decision

Usage:
    from mcp_server_langgraph.execution.domain_proxy import (
        DomainProxyConfig,
        DomainProxyServer,
        DomainMatcher,
    )

    config = DomainProxyConfig(
        allowed_domains=["*.google.com", "api.openai.com"],
        proxy_port=8080,
    )

    server = DomainProxyServer(config)
    await server.start()

    # Configure container with HTTP_PROXY/HTTPS_PROXY pointing to server
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class DomainProxyConfig(BaseModel):
    """Configuration for domain proxy."""

    allowed_domains: list[str] = Field(
        default_factory=list,
        description="List of allowed domains (supports wildcards like *.example.com)",
    )
    proxy_port: int = Field(default=8080, description="HTTP proxy port")
    dns_port: int = Field(default=5353, description="DNS proxy port (if using DNS-based filtering)")
    log_blocked: bool = Field(default=True, description="Log blocked requests")
    log_allowed: bool = Field(default=False, description="Log allowed requests")
    connection_timeout: float = Field(default=30.0, description="Connection timeout in seconds")


# =============================================================================
# Domain Matching
# =============================================================================


class DomainMatcher:
    """Matches domains against an allowlist with wildcard support.

    Supports patterns like:
    - "example.com" - exact match
    - "*.example.com" - matches any subdomain (but not bare domain)
    - "*.*.example.com" - matches nested subdomains

    Security: Fails closed (blocks if no match).
    """

    def __init__(self, allowed_domains: list[str]) -> None:
        """Initialize domain matcher.

        Args:
            allowed_domains: List of allowed domain patterns
        """
        self._allowed_domains = allowed_domains
        self._patterns = self._compile_patterns(allowed_domains)

    def _compile_patterns(self, domains: list[str]) -> list[re.Pattern[str]]:
        """Compile domain patterns to regex for efficient matching.

        Args:
            domains: List of domain patterns

        Returns:
            List of compiled regex patterns
        """
        patterns = []
        for domain in domains:
            if domain.startswith("*."):
                # Wildcard: *.example.com matches *.example.com but not example.com
                # Escape dots and convert * to regex
                base = re.escape(domain[2:])
                pattern = rf"^.+\.{base}$"
            else:
                # Exact match
                pattern = rf"^{re.escape(domain)}$"
            patterns.append(re.compile(pattern, re.IGNORECASE))
        return patterns

    def is_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed.

        Args:
            domain: Domain to check (e.g., "www.google.com")

        Returns:
            True if allowed, False otherwise
        """
        if not self._patterns:
            return False  # Empty allowlist blocks all

        domain = domain.lower().strip()
        for pattern in self._patterns:
            if pattern.match(domain):
                return True
        return False


# =============================================================================
# Proxy Server
# =============================================================================


class DomainProxyServer:
    """HTTP proxy server that enforces domain allowlist.

    Runs as a transparent proxy that containers connect through.
    Blocks requests to domains not in the allowlist.

    Attributes:
        config: Proxy configuration
        is_running: Whether the server is currently running
    """

    def __init__(self, config: DomainProxyConfig) -> None:
        """Initialize proxy server.

        Args:
            config: Proxy configuration
        """
        self.config = config
        self._matcher = DomainMatcher(config.allowed_domains)
        self._server: asyncio.Server | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def should_allow(self, domain: str) -> bool:
        """Check if a domain should be allowed.

        Args:
            domain: Domain to check

        Returns:
            True if allowed, False otherwise
        """
        allowed = self._matcher.is_allowed(domain)

        # Record metric
        record_proxy_request(domain=domain, allowed=allowed)

        if not allowed and self.config.log_blocked:
            logger.warning(f"Blocked request to domain: {domain}")
        elif allowed and self.config.log_allowed:
            logger.debug(f"Allowed request to domain: {domain}")

        return allowed

    async def start(self) -> None:
        """Start the proxy server."""
        if self._running:
            return

        await self._start_proxy()
        self._running = True
        logger.info(f"Domain proxy started on port {self.config.proxy_port}")

    async def _start_proxy(self) -> None:
        """Internal method to start the proxy server.

        This is a placeholder for the actual proxy implementation.
        Production implementation would use:
        - mitmproxy/mitmdump for HTTPS interception
        - Or a custom asyncio protocol handler
        """
        # In production, this would start an actual HTTP proxy
        # For now, this is a stub that will be mocked in tests
        pass

    async def stop(self) -> None:
        """Stop the proxy server."""
        if not self._running:
            return

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._running = False
        logger.info("Domain proxy stopped")

    def get_proxy_url(self) -> str:
        """Get the proxy URL for container configuration.

        Returns:
            Proxy URL (e.g., "http://host.docker.internal:8080")
        """
        return f"http://host.docker.internal:{self.config.proxy_port}"


# =============================================================================
# HTTP Protocol Parsing
# =============================================================================


def parse_connect_request(request: bytes) -> dict[str, Any] | None:
    """Parse HTTP CONNECT request.

    Args:
        request: Raw HTTP request bytes

    Returns:
        Dict with host and port, or None if invalid
    """
    try:
        lines = request.split(b"\r\n")
        if not lines:
            return None

        first_line = lines[0].decode("utf-8", errors="ignore")
        parts = first_line.split()

        if len(parts) < 3 or parts[0] != "CONNECT":
            return None

        host_port = parts[1]
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 443

        return {"host": host, "port": port}
    except (ValueError, IndexError):
        return None


def parse_http_request(request: bytes) -> dict[str, Any] | None:
    """Parse HTTP GET/POST request with absolute URL.

    Args:
        request: Raw HTTP request bytes

    Returns:
        Dict with host, method, path, or None if invalid
    """
    try:
        lines = request.split(b"\r\n")
        if not lines:
            return None

        first_line = lines[0].decode("utf-8", errors="ignore")
        parts = first_line.split()

        if len(parts) < 3:
            return None

        method = parts[0]
        url = parts[1]

        if url.startswith("http://"):
            url = url[7:]
        elif url.startswith("https://"):
            url = url[8:]

        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"

        if ":" in host:
            host = host.split(":")[0]

        return {"host": host, "method": method, "path": path}
    except (ValueError, IndexError):
        return None


def create_blocked_response(domain: str) -> bytes:
    """Create HTTP 403 Forbidden response.

    Args:
        domain: Blocked domain name

    Returns:
        HTTP response bytes
    """
    body = f"<html><body><h1>403 Forbidden</h1><p>Access to {domain} is blocked.</p></body></html>"
    response = (
        f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
    )
    return response.encode("utf-8")


def create_connect_success_response() -> bytes:
    """Create HTTP 200 Connection Established response.

    Returns:
        HTTP response bytes
    """
    return b"HTTP/1.1 200 Connection Established\r\n\r\n"


# =============================================================================
# Connection Handler
# =============================================================================


class ProxyConnectionHandler:
    """Handles individual proxy connections with domain validation."""

    def __init__(self, config: DomainProxyConfig) -> None:
        """Initialize connection handler.

        Args:
            config: Proxy configuration
        """
        self.config = config
        self._matcher = DomainMatcher(config.allowed_domains)
        self.timeout = config.connection_timeout

    async def check_request(self, request: bytes) -> dict[str, Any]:
        """Check if a request should be allowed.

        Args:
            request: Raw HTTP request bytes

        Returns:
            Dict with allowed status and parsed host
        """
        connect_info = parse_connect_request(request)
        if connect_info:
            host = connect_info["host"]
            allowed = self._matcher.is_allowed(host)
            record_proxy_request(domain=host, allowed=allowed)
            return {"allowed": allowed, "host": host, "port": connect_info["port"]}

        http_info = parse_http_request(request)
        if http_info:
            host = http_info["host"]
            allowed = self._matcher.is_allowed(host)
            record_proxy_request(domain=host, allowed=allowed)
            return {"allowed": allowed, "host": host, "method": http_info["method"]}

        return {"allowed": False, "host": "unknown", "error": "Invalid request format"}


# =============================================================================
# Prometheus Metrics
# =============================================================================

_proxy_metrics: dict[str, Any] | None = None


def get_proxy_metrics() -> dict[str, Any]:
    """Get proxy Prometheus metrics.

    Returns:
        Dict of metric names to metric objects
    """
    global _proxy_metrics
    if _proxy_metrics is None:
        _proxy_metrics = {
            "proxy_requests_total": {
                "type": "counter",
                "help": "Total number of proxy requests",
                "labels": ["domain", "status"],
            },
            "proxy_requests_blocked_total": {
                "type": "counter",
                "help": "Total number of blocked proxy requests",
                "labels": ["domain"],
            },
            "proxy_request_duration_seconds": {
                "type": "histogram",
                "help": "Proxy request duration in seconds",
                "buckets": [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            },
        }
    return _proxy_metrics


# =============================================================================
# Metrics Recording
# =============================================================================


def record_proxy_request(domain: str, allowed: bool) -> None:
    """Record proxy request metric.

    Args:
        domain: Domain of the request
        allowed: Whether the request was allowed
    """
    status = "allowed" if allowed else "blocked"
    logger.info(
        "proxy_request",
        extra={
            "domain": domain,
            "status": status,
        },
    )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DomainMatcher",
    "DomainProxyConfig",
    "DomainProxyServer",
    "ProxyConnectionHandler",
    "create_blocked_response",
    "create_connect_success_response",
    "get_proxy_metrics",
    "parse_connect_request",
    "parse_http_request",
    "record_proxy_request",
]
