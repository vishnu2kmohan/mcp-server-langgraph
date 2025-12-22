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


@pytest.mark.xdist_group(name="proxy_protocol")
class TestProxyProtocolHandler:
    """Tests for HTTP CONNECT proxy protocol handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_connect_request_valid(self) -> None:
        """Test parsing valid CONNECT request."""
        from mcp_server_langgraph.execution.domain_proxy import parse_connect_request

        request = b"CONNECT api.example.com:443 HTTP/1.1\r\nHost: api.example.com:443\r\n\r\n"
        result = parse_connect_request(request)

        assert result is not None
        assert result["host"] == "api.example.com"
        assert result["port"] == 443

    def test_parse_connect_request_http_port(self) -> None:
        """Test parsing CONNECT request with HTTP port."""
        from mcp_server_langgraph.execution.domain_proxy import parse_connect_request

        request = b"CONNECT example.com:80 HTTP/1.1\r\nHost: example.com:80\r\n\r\n"
        result = parse_connect_request(request)

        assert result is not None
        assert result["host"] == "example.com"
        assert result["port"] == 80

    def test_parse_connect_request_invalid(self) -> None:
        """Test parsing invalid request returns None."""
        from mcp_server_langgraph.execution.domain_proxy import parse_connect_request

        request = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
        result = parse_connect_request(request)

        assert result is None

    def test_parse_http_request_valid(self) -> None:
        """Test parsing valid HTTP GET request."""
        from mcp_server_langgraph.execution.domain_proxy import parse_http_request

        request = b"GET http://api.example.com/path HTTP/1.1\r\nHost: api.example.com\r\n\r\n"
        result = parse_http_request(request)

        assert result is not None
        assert result["host"] == "api.example.com"
        assert result["method"] == "GET"
        assert result["path"] == "/path"

    def test_create_blocked_response(self) -> None:
        """Test creating blocked response."""
        from mcp_server_langgraph.execution.domain_proxy import create_blocked_response

        response = create_blocked_response("evil.com")

        assert b"403 Forbidden" in response
        assert b"evil.com" in response

    def test_create_connect_success_response(self) -> None:
        """Test creating CONNECT success response."""
        from mcp_server_langgraph.execution.domain_proxy import create_connect_success_response

        response = create_connect_success_response()

        assert b"200 Connection Established" in response


@pytest.mark.xdist_group(name="proxy_connection")
class TestProxyConnectionHandler:
    """Tests for proxy connection handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_connect_allowed_domain(self) -> None:
        """Test handling CONNECT for allowed domain."""
        from mcp_server_langgraph.execution.domain_proxy import (
            DomainProxyConfig,
            ProxyConnectionHandler,
        )

        config = DomainProxyConfig(allowed_domains=["*.example.com"])
        handler = ProxyConnectionHandler(config)

        # Mock reader/writer
        reader = AsyncMock()
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        request = b"CONNECT api.example.com:443 HTTP/1.1\r\nHost: api.example.com:443\r\n\r\n"
        reader.read = AsyncMock(return_value=request)

        # Should allow the connection
        result = await handler.check_request(request)
        assert result["allowed"] is True
        assert result["host"] == "api.example.com"

    @pytest.mark.asyncio
    async def test_handle_connect_blocked_domain(self) -> None:
        """Test handling CONNECT for blocked domain."""
        from mcp_server_langgraph.execution.domain_proxy import (
            DomainProxyConfig,
            ProxyConnectionHandler,
        )

        config = DomainProxyConfig(allowed_domains=["*.allowed.com"])
        handler = ProxyConnectionHandler(config)

        request = b"CONNECT evil.com:443 HTTP/1.1\r\nHost: evil.com:443\r\n\r\n"

        result = await handler.check_request(request)
        assert result["allowed"] is False
        assert result["host"] == "evil.com"

    @pytest.mark.asyncio
    async def test_handler_timeout_config(self) -> None:
        """Test connection handler respects timeout config."""
        from mcp_server_langgraph.execution.domain_proxy import (
            DomainProxyConfig,
            ProxyConnectionHandler,
        )

        config = DomainProxyConfig(
            allowed_domains=["*.example.com"],
            connection_timeout=30.0,
        )
        handler = ProxyConnectionHandler(config)

        assert handler.timeout == 30.0


@pytest.mark.xdist_group(name="proxy_prometheus")
class TestProxyPrometheusMetrics:
    """Tests for Prometheus metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_proxy_requests_counter_exists(self) -> None:
        """Test proxy requests counter metric exists."""
        from mcp_server_langgraph.execution.domain_proxy import get_proxy_metrics

        metrics = get_proxy_metrics()
        assert "proxy_requests_total" in metrics

    def test_proxy_blocked_counter_exists(self) -> None:
        """Test proxy blocked requests counter exists."""
        from mcp_server_langgraph.execution.domain_proxy import get_proxy_metrics

        metrics = get_proxy_metrics()
        assert "proxy_requests_blocked_total" in metrics

    def test_proxy_latency_histogram_exists(self) -> None:
        """Test proxy latency histogram exists."""
        from mcp_server_langgraph.execution.domain_proxy import get_proxy_metrics

        metrics = get_proxy_metrics()
        assert "proxy_request_duration_seconds" in metrics
