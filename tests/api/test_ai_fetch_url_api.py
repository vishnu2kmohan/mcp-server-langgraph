"""
Tests for AI URL Content Fetch API

TDD: Tests for the POST /api/v1/ai/fetch-url endpoint.
Covers SSRF protection, content extraction, and error handling.

Follows memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def app():
    """Create a test FastAPI app with the AI router."""
    from mcp_server_langgraph.api.v1.ai import ai_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(ai_router, prefix="/api/v1/ai")

    # Mock authenticated user
    mock_user = {
        "sub": "user-123",
        "preferred_username": "testuser",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.mark.xdist_group(name="ai_fetch_url")
class TestFetchUrlSSRFProtection:
    """Tests for SSRF protection in the fetch-url endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_blocks_private_ip_address(self, client):
        """Should block requests to private IP addresses (192.168.x.x)."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http://192.168.1.1/admin"},
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower() or "internal" in response.json()["detail"].lower()

    def test_blocks_loopback_address(self, client):
        """Should block requests to localhost/127.0.0.1."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http://127.0.0.1/secret"},
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower() or "internal" in response.json()["detail"].lower()

    def test_blocks_localhost_hostname(self, client):
        """Should block requests to localhost hostname."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http://localhost/admin"},
        )
        assert response.status_code == 400
        # Either DNS resolution fails or it resolves to 127.0.0.1 which is blocked
        detail = response.json()["detail"].lower()
        assert "private" in detail or "internal" in detail or "resolve" in detail

    def test_blocks_file_scheme(self, client):
        """Should block file:// URLs."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "file:///etc/passwd"},
        )
        assert response.status_code == 400
        assert "scheme" in response.json()["detail"].lower()

    def test_blocks_ftp_scheme(self, client):
        """Should block ftp:// URLs."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "ftp://example.com/file"},
        )
        assert response.status_code == 400
        assert "scheme" in response.json()["detail"].lower()

    def test_blocks_empty_hostname(self, client):
        """Should block URLs with missing hostname."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http:///path"},
        )
        assert response.status_code == 400
        assert "hostname" in response.json()["detail"].lower()

    def test_blocks_link_local_address(self, client):
        """Should block link-local addresses (169.254.x.x)."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http://169.254.169.254/latest/meta-data"},
        )
        assert response.status_code == 400
        # AWS metadata endpoint - should be blocked
        detail = response.json()["detail"].lower()
        assert "private" in detail or "internal" in detail or "link-local" in detail.replace("-", "")


@pytest.mark.xdist_group(name="ai_fetch_url")
class TestFetchUrlContentExtraction:
    """Tests for content extraction from fetched URLs."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_extracts_html_title_and_content(self, mock_fetch, mock_safe, client):
        """Should extract title and content from HTML pages."""
        mock_safe.return_value = (True, None)
        mock_fetch.return_value = {
            "url": "https://example.com",
            "title": "Example Domain",
            "content": "This domain is for use in illustrative examples.",
            "content_type": "text/html",
            "content_length": 50,
            "truncated": False,
        }

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Example Domain"
        assert "illustrative" in data["content"]
        assert data["content_type"] == "text/html"
        assert data["truncated"] is False

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_handles_json_content(self, mock_fetch, mock_safe, client):
        """Should properly handle JSON response content."""
        mock_safe.return_value = (True, None)
        mock_fetch.return_value = {
            "url": "https://api.example.com/data",
            "title": None,
            "content": '{\n  "key": "value"\n}',
            "content_type": "application/json",
            "content_length": 22,
            "truncated": False,
        }

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://api.example.com/data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] is None
        assert '"key": "value"' in data["content"]
        assert data["content_type"] == "application/json"

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_truncates_large_content(self, mock_fetch, mock_safe, client):
        """Should truncate content that exceeds the size limit."""
        mock_safe.return_value = (True, None)
        mock_fetch.return_value = {
            "url": "https://example.com/large",
            "title": "Large Page",
            "content": "A" * 1000 + "... [truncated]",
            "content_type": "text/html",
            "content_length": 1014,
            "truncated": True,
        }

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://example.com/large"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is True
        assert "[truncated]" in data["content"]

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_returns_final_url_after_redirects(self, mock_fetch, mock_safe, client):
        """Should return the final URL after following redirects."""
        mock_safe.return_value = (True, None)
        mock_fetch.return_value = {
            "url": "https://www.example.com/final",
            "title": "Final Page",
            "content": "Redirected content",
            "content_type": "text/html",
            "content_length": 18,
            "truncated": False,
        }

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://example.com/redirect"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://www.example.com/final"


@pytest.mark.xdist_group(name="ai_fetch_url")
class TestFetchUrlErrorHandling:
    """Tests for error handling in the fetch-url endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_returns_502_on_network_error(self, mock_fetch, mock_safe, client):
        """Should return 502 Bad Gateway when URL fetch fails."""
        mock_safe.return_value = (True, None)
        mock_fetch.side_effect = Exception("Connection refused")

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://down.example.com"},
        )

        assert response.status_code == 502
        assert "Connection refused" in response.json()["detail"]

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_returns_502_on_http_error(self, mock_fetch, mock_safe, client):
        """Should return 502 on upstream HTTP errors (404, 500, etc.)."""
        import httpx

        mock_safe.return_value = (True, None)
        mock_fetch.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://example.com/not-found"},
        )

        assert response.status_code == 502
        assert "Not Found" in response.json()["detail"]

    @patch("mcp_server_langgraph.api.v1.ai._is_safe_url")
    @patch("mcp_server_langgraph.api.v1.ai._fetch_and_extract_content")
    def test_returns_502_on_timeout(self, mock_fetch, mock_safe, client):
        """Should return 502 when request times out."""
        import httpx

        mock_safe.return_value = (True, None)
        mock_fetch.side_effect = httpx.TimeoutException("Request timed out")

        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://slow.example.com"},
        )

        assert response.status_code == 502
        assert "timed out" in response.json()["detail"].lower()

    def test_validates_url_format(self, client):
        """Should validate URL format."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "not-a-url"},
        )

        # Should fail SSRF validation due to invalid URL
        assert response.status_code == 400


@pytest.mark.xdist_group(name="ai_fetch_url")
class TestFetchUrlRequestValidation:
    """Tests for request validation in the fetch-url endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_requires_url_field(self, client):
        """Should require the url field in the request body."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={},
        )

        assert response.status_code == 422  # Validation error

    def test_accepts_https_urls(self, client):
        """Should accept HTTPS URLs (after SSRF check)."""
        # This will fail SSRF check if it resolves to internal IP,
        # but proves the URL scheme is accepted
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "https://10.0.0.1/secret"},
        )

        # Should fail on private IP, not on scheme
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "private" in detail or "internal" in detail

    def test_accepts_http_urls(self, client):
        """Should accept HTTP URLs (after SSRF check)."""
        response = client.post(
            "/api/v1/ai/fetch-url",
            json={"url": "http://10.0.0.1/secret"},
        )

        # Should fail on private IP, not on scheme
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "private" in detail or "internal" in detail
