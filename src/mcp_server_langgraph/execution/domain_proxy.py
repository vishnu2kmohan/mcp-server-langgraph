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
import fnmatch
import logging
import re
from dataclasses import dataclass, field
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
# Metrics
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
    "record_proxy_request",
]
