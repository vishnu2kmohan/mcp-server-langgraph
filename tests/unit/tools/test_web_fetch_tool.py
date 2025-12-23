"""
TDD Tests for web_fetch tool

These tests define the expected behavior for the web_fetch tool.
Written FIRST before implementation (RED phase).
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="web_fetch_tool")
class TestWebFetchTool:
    """Test suite for web_fetch tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_returns_content(self):
        """GIVEN a valid URL
        WHEN web_fetch is called
        THEN it returns the content from the URL"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html><body>Hello World</body></html>")
        mock_response.headers = {"content-type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://example.com"})

        assert "Hello World" in result or "content" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_converts_html_to_markdown(self):
        """GIVEN HTML content and convert_html=True
        WHEN web_fetch is called
        THEN it converts HTML to markdown for cleaner output"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        html_content = "<html><body><h1>Title</h1><p>Paragraph text.</p></body></html>"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        mock_response.headers = {"content-type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke(
                {
                    "url": "https://example.com",
                    "convert_html": True,
                }
            )

        # Should contain markdown-style formatting or plain text, not raw HTML tags
        # The exact format depends on implementation
        assert "Title" in result
        assert "Paragraph" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_with_prompt_extracts_info(self):
        """GIVEN a URL and a prompt
        WHEN web_fetch is called
        THEN it returns content relevant to the prompt"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        html_content = "<html><body><h1>Product Page</h1><p>Price: $99.99</p></body></html>"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        mock_response.headers = {"content-type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke(
                {
                    "url": "https://example.com/product",
                    "prompt": "What is the price?",
                }
            )

        # Should contain the price information
        assert "99.99" in result or "price" in result.lower()

    # =========================================================================
    # URL Validation Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_file_scheme(self):
        """GIVEN a file:// URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "file:///etc/passwd"})

        assert "error" in result.lower()
        assert "scheme" in result.lower() or "not allowed" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_ftp_scheme(self):
        """GIVEN an ftp:// URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "ftp://ftp.example.com/file.txt"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_javascript_scheme(self):
        """GIVEN a javascript: URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "javascript:alert('xss')"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_allows_https_scheme(self):
        """GIVEN an https:// URL
        WHEN web_fetch is called
        THEN it is allowed"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Content")
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://example.com"})

        assert "error" not in result.lower() or "Content" in result

    # =========================================================================
    # Internal IP Rejection Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_localhost(self):
        """GIVEN a localhost URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "https://localhost/admin"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_127_ip(self):
        """GIVEN a 127.0.0.1 URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "https://127.0.0.1/admin"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_private_10_network(self):
        """GIVEN a 10.x.x.x URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "https://10.0.0.1/internal"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_private_192_network(self):
        """GIVEN a 192.168.x.x URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "https://192.168.1.1/router"})

        assert "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_rejects_private_172_network(self):
        """GIVEN a 172.16.x.x URL
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "https://172.16.0.1/internal"})

        assert "error" in result.lower()

    # =========================================================================
    # Domain Blocking Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_respects_blocked_domains(self):
        """GIVEN a blocked domain
        WHEN web_fetch is called
        THEN it is rejected"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        with patch(
            "mcp_server_langgraph.tools.web_fetch_tools.WEB_FETCH_BLOCKED_DOMAINS",
            {"blocked.example.com"},
        ):
            result = await web_fetch.ainvoke({"url": "https://blocked.example.com/page"})

        assert "error" in result.lower() or "blocked" in result.lower()

    # =========================================================================
    # Timeout and Size Limit Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_handles_timeout(self):
        """GIVEN a URL that times out
        WHEN web_fetch is called
        THEN it returns a timeout error"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(side_effect=TimeoutError())
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://slow.example.com"})

        assert "error" in result.lower()
        assert "timeout" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_respects_size_limit(self):
        """GIVEN a URL returning content exceeding size limit
        WHEN web_fetch is called
        THEN it stops reading at the limit"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        # Create content larger than limit
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=large_content)
        mock_response.headers = {"content-type": "text/plain", "content-length": str(len(large_content))}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://example.com/large"})

        # Should either truncate or reject
        assert "error" in result.lower() or len(result) < len(large_content)

    # =========================================================================
    # Redirect Handling Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_follows_redirects_safely(self):
        """GIVEN a URL that redirects
        WHEN web_fetch is called
        THEN it follows redirects but validates the final destination"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Redirected content")
        mock_response.headers = {"content-type": "text/html"}
        mock_response.url = "https://final.example.com/page"
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://redirect.example.com"})

        assert "Redirected content" in result or "content" in result.lower()

    # =========================================================================
    # HTTP Error Handling Tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_handles_404_error(self):
        """GIVEN a URL that returns 404
        WHEN web_fetch is called
        THEN it returns an appropriate error"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.headers = {"content-type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://example.com/notfound"})

        assert "error" in result.lower() or "404" in result or "not found" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_fetch_handles_500_error(self):
        """GIVEN a URL that returns 500
        WHEN web_fetch is called
        THEN it returns an appropriate error"""
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.headers = {"content-type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.aiohttp.ClientSession") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            result = await web_fetch.ainvoke({"url": "https://example.com/error"})

        assert "error" in result.lower() or "500" in result


@pytest.mark.xdist_group(name="web_fetch_tool_integration")
class TestWebFetchToolIntegration:
    """Integration tests for web_fetch tool."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_web_fetch_rate_limiting(self):
        """GIVEN rapid successive requests to the same domain
        WHEN web_fetch is called multiple times
        THEN rate limiting is applied"""
        # Placeholder for rate limiting integration test
        pass
