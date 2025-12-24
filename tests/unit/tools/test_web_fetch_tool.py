"""
Tests for web_fetch tool backed by the sandbox runner.
"""

import gc
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="web_fetch_tool")
class TestWebFetchTool:
    """Test suite for web_fetch tool (sandbox-backed)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_web_fetch_returns_content(self):
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        payload = {"text": "<html>Hello World</html>", "content_type": "text/html", "truncated": False, "status": 200}
        run_result = SimpleNamespace(stdout=json.dumps(payload), stderr="", exit_code=0, timed_out=False, error_message=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_web_fetch.return_value = run_result
            result = await web_fetch.ainvoke({"url": "https://example.com"})

        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_web_fetch_converts_html_to_markdown(self):
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        html_content = "<html><body><h1>Title</h1><p>Paragraph text.</p></body></html>"
        payload = {"text": html_content, "content_type": "text/html", "truncated": False, "status": 200}
        run_result = SimpleNamespace(stdout=json.dumps(payload), stderr="", exit_code=0, timed_out=False, error_message=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_web_fetch.return_value = run_result
            result = await web_fetch.ainvoke({"url": "https://example.com", "convert_html": True})

        assert "Title" in result
        assert "Paragraph" in result
        assert "<html>" not in result

    @pytest.mark.asyncio
    async def test_web_fetch_with_prompt_includes_prompt(self):
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        html_content = "<html><body><h1>Product Page</h1><p>Price: $99.99</p></body></html>"
        payload = {"text": html_content, "content_type": "text/html", "truncated": False, "status": 200}
        run_result = SimpleNamespace(stdout=json.dumps(payload), stderr="", exit_code=0, timed_out=False, error_message=None)

        with patch("mcp_server_langgraph.tools.web_fetch_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_web_fetch.return_value = run_result
            result = await web_fetch.ainvoke({"url": "https://example.com/product", "prompt": "What is the price?"})

        assert "price" in result.lower()
        assert "$99.99" in result

    @pytest.mark.asyncio
    async def test_web_fetch_rejects_bad_scheme(self):
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        result = await web_fetch.ainvoke({"url": "file:///etc/passwd"})
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_web_fetch_timeout_error(self):
        from mcp_server_langgraph.tools.web_fetch_tools import web_fetch

        run_result = SimpleNamespace(
            stdout="",
            stderr="timeout",
            exit_code=1,
            timed_out=True,
            error_message=None,
        )

        with patch("mcp_server_langgraph.tools.web_fetch_tools.get_sandbox_runner") as mock_runner_fn:
            mock_runner_fn.return_value.run_web_fetch.return_value = run_result
            result = await web_fetch.ainvoke({"url": "https://example.com"})

        assert "timeout" in result.lower()
