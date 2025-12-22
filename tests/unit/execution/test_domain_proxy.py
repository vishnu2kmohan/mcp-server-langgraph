"""
Tests for Domain Proxy Allowlist.

TDD tests for proxy-based network domain filtering in sandbox execution.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="domain_proxy")
class TestDomainProxyConfig:
    """Tests for domain proxy configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_domain_proxy_config_exists(self) -> None:
        """Test that DomainProxyConfig class exists."""
        from mcp_server_langgraph.execution.domain_proxy import DomainProxyConfig

        assert DomainProxyConfig is not None

    def test_domain_proxy_config_has_required_fields(self) -> None:
        """Test DomainProxyConfig has required fields."""
        from mcp_server_langgraph.execution.domain_proxy import DomainProxyConfig

        config = DomainProxyConfig(
            allowed_domains=["*.google.com", "api.openai.com"],
            proxy_port=8080,
            dns_port=5353,
        )

        assert config.allowed_domains == ["*.google.com", "api.openai.com"]
        assert config.proxy_port == 8080
        assert config.dns_port == 5353

    def test_domain_proxy_config_defaults(self) -> None:
        """Test DomainProxyConfig has sensible defaults."""
        from mcp_server_langgraph.execution.domain_proxy import DomainProxyConfig

        config = DomainProxyConfig(allowed_domains=[])
        assert config.proxy_port == 8080
        assert config.dns_port == 5353


@pytest.mark.xdist_group(name="domain_matcher")
class TestDomainMatcher:
    """Tests for domain matching logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_domain_matcher_exists(self) -> None:
        """Test that DomainMatcher class exists."""
        from mcp_server_langgraph.execution.domain_proxy import DomainMatcher

        assert DomainMatcher is not None

    def test_exact_domain_match(self) -> None:
        """Test exact domain matching."""
        from mcp_server_langgraph.execution.domain_proxy import DomainMatcher

        matcher = DomainMatcher(["api.openai.com"])
        assert matcher.is_allowed("api.openai.com") is True
        assert matcher.is_allowed("other.openai.com") is False

    def test_wildcard_domain_match(self) -> None:
        """Test wildcard domain matching."""
        from mcp_server_langgraph.execution.domain_proxy import DomainMatcher

        matcher = DomainMatcher(["*.google.com"])
        assert matcher.is_allowed("www.google.com") is True
        assert matcher.is_allowed("api.google.com") is True
        assert matcher.is_allowed("google.com") is False  # Wildcard doesn't match bare domain
        assert matcher.is_allowed("evil.com") is False

    def test_wildcard_matches_nested_subdomains(self) -> None:
        """Test wildcard matches nested subdomains."""
        from mcp_server_langgraph.execution.domain_proxy import DomainMatcher

        matcher = DomainMatcher(["*.example.com"])
        assert matcher.is_allowed("sub.domain.example.com") is True
        assert matcher.is_allowed("a.b.c.example.com") is True

    def test_empty_allowlist_blocks_all(self) -> None:
        """Test empty allowlist blocks all domains."""
        from mcp_server_langgraph.execution.domain_proxy import DomainMatcher

        matcher = DomainMatcher([])
        assert matcher.is_allowed("anything.com") is False


@pytest.mark.xdist_group(name="domain_proxy_server")
class TestDomainProxyServer:
    """Tests for domain proxy server."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_domain_proxy_server_exists(self) -> None:
        """Test that DomainProxyServer class exists."""
        from mcp_server_langgraph.execution.domain_proxy import DomainProxyServer

        assert DomainProxyServer is not None

    @pytest.mark.asyncio
    async def test_proxy_server_start_stop(self) -> None:
        """Test proxy server can be started and stopped."""
        from mcp_server_langgraph.execution.domain_proxy import (
            DomainProxyConfig,
            DomainProxyServer,
        )

        config = DomainProxyConfig(
            allowed_domains=["*.example.com"],
            proxy_port=0,  # Use ephemeral port
            dns_port=0,
        )
        server = DomainProxyServer(config)

        # Mock the actual server to avoid binding
        with patch.object(server, "_start_proxy", new_callable=AsyncMock):
            await server.start()
            assert server.is_running is True

            await server.stop()
            assert server.is_running is False

    @pytest.mark.asyncio
    async def test_proxy_blocks_disallowed_domain(self) -> None:
        """Test proxy blocks requests to disallowed domains."""
        from mcp_server_langgraph.execution.domain_proxy import (
            DomainProxyConfig,
            DomainProxyServer,
        )

        config = DomainProxyConfig(
            allowed_domains=["*.allowed.com"],
            proxy_port=0,
            dns_port=0,
        )
        server = DomainProxyServer(config)

        # Test domain check
        assert server.should_allow("www.allowed.com") is True
        assert server.should_allow("evil.com") is False


@pytest.mark.xdist_group(name="sandbox_proxy_integration")
class TestSandboxProxyIntegration:
    """Tests for sandbox proxy integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sandbox_config_accepts_proxy_config(self) -> None:
        """Test SandboxConfig accepts proxy configuration."""
        from mcp_server_langgraph.execution.domain_proxy import DomainProxyConfig
        from mcp_server_langgraph.execution.resource_limits import ResourceLimits

        proxy_config = DomainProxyConfig(
            allowed_domains=["*.api.com"],
            proxy_port=8080,
        )
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=["*.api.com"],
            proxy_config=proxy_config,
        )

        assert limits.proxy_config is not None
        assert limits.proxy_config.allowed_domains == ["*.api.com"]


@pytest.mark.xdist_group(name="proxy_metrics")
class TestProxyMetrics:
    """Tests for proxy metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_allowed_request_metric(self) -> None:
        """Test recording allowed request metric."""
        from mcp_server_langgraph.execution.domain_proxy import record_proxy_request

        # Should not raise
        record_proxy_request(domain="api.openai.com", allowed=True)

    def test_record_blocked_request_metric(self) -> None:
        """Test recording blocked request metric."""
        from mcp_server_langgraph.execution.domain_proxy import record_proxy_request

        # Should not raise
        record_proxy_request(domain="evil.com", allowed=False)
