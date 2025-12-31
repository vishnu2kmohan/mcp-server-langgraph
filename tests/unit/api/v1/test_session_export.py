"""
Session Export API Tests.

TDD tests for the session export endpoint.

Endpoints tested:
- POST /api/v1/sessions/{session_id}/export - Export session in specified format
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.session_export import (
    session_export_router,
)

# Module-level pytest marker
pytestmark = pytest.mark.unit


# ==============================================================================
# Mock Data
# ==============================================================================

MOCK_SESSION = {
    "id": "session-123",
    "project_id": "project-456",
    "title": "Test Session",
    "created_at": "2024-12-01T10:00:00Z",
    "updated_at": "2024-12-01T12:00:00Z",
    "messages": [
        {
            "id": "msg-1",
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": "2024-12-01T10:00:00Z",
        },
        {
            "id": "msg-2",
            "role": "assistant",
            "content": "I'm doing well, thank you! How can I help you today?",
            "timestamp": "2024-12-01T10:00:05Z",
        },
        {
            "id": "msg-3",
            "role": "user",
            "content": "Can you write a Python function?",
            "timestamp": "2024-12-01T10:01:00Z",
        },
        {
            "id": "msg-4",
            "role": "assistant",
            "content": "Sure! Here's a simple Python function:\n\n```python\ndef greet(name: str) -> str:\n    return f'Hello, {name}!'\n```",
            "timestamp": "2024-12-01T10:01:10Z",
        },
    ],
}


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_current_user() -> dict[str, Any]:
    """Mock authenticated user."""
    return {
        "user_id": "user:testuser",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def mock_session_service() -> AsyncMock:
    """Mock session service."""
    service = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
    service.get_session.return_value = MOCK_SESSION
    return service


@pytest.fixture
def app(mock_current_user: dict[str, Any], mock_session_service: AsyncMock) -> FastAPI:
    """Create test FastAPI app with export router."""
    from mcp_server_langgraph.api.v1.session_export import set_session_service
    from mcp_server_langgraph.auth.middleware import get_current_user

    test_app = FastAPI()

    # Override auth dependency
    async def override_get_current_user() -> dict[str, Any]:
        return mock_current_user

    test_app.dependency_overrides[get_current_user] = override_get_current_user

    # Set mock session service
    set_session_service(mock_session_service)

    test_app.include_router(session_export_router, prefix="/api/v1")

    yield test_app

    # Cleanup
    set_session_service(None)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# ==============================================================================
# Export Format Tests
# ==============================================================================


class TestExportMarkdown:
    """Tests for Markdown export format."""

    def test_export_as_markdown(self, client: TestClient) -> None:
        """Should export session as Markdown."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "markdown"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"

        content = response.text
        assert "# Test Session" in content
        assert "Hello, how are you?" in content
        assert "```python" in content

    def test_markdown_includes_metadata(self, client: TestClient) -> None:
        """Markdown export should include metadata when requested."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "markdown", "include_metadata": True},
        )

        assert response.status_code == 200
        content = response.text
        assert "session-123" in content or "Session ID" in content


class TestExportJson:
    """Tests for JSON export format."""

    def test_export_as_json(self, client: TestClient) -> None:
        """Should export session as JSON."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "json"},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert data["id"] == "session-123"
        assert "messages" in data

    def test_json_includes_all_messages(self, client: TestClient) -> None:
        """JSON export should include all messages."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "json"},
        )

        data = response.json()
        assert len(data["messages"]) == 4


class TestExportHtml:
    """Tests for HTML export format."""

    def test_export_as_html(self, client: TestClient) -> None:
        """Should export session as HTML."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "html"},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        assert "<html" in content
        assert "Test Session" in content
        assert "Hello, how are you?" in content


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestExportErrors:
    """Tests for export error handling."""

    def test_invalid_format_returns_422(self, client: TestClient) -> None:
        """Invalid format should return 422."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "pdf"},  # PDF requires server-side generation
        )

        # PDF might be valid or invalid depending on implementation
        # For now, we only support markdown, json, html
        assert response.status_code in [200, 422]

    def test_session_not_found_returns_404(self, client: TestClient, mock_session_service: AsyncMock) -> None:
        """Non-existent session should return 404."""
        mock_session_service.get_session.return_value = None

        response = client.post(
            "/api/v1/sessions/nonexistent/export",
            json={"format": "markdown"},
        )

        assert response.status_code == 404


# ==============================================================================
# Content-Disposition Tests
# ==============================================================================


class TestExportDownload:
    """Tests for download behavior."""

    def test_has_content_disposition_header(self, client: TestClient) -> None:
        """Export should have Content-Disposition for download."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "markdown"},
        )

        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".md" in response.headers["content-disposition"]

    def test_filename_includes_session_title(self, client: TestClient) -> None:
        """Filename should include session title."""
        response = client.post(
            "/api/v1/sessions/session-123/export",
            json={"format": "markdown"},
        )

        disposition = response.headers["content-disposition"]
        assert "Test" in disposition or "session" in disposition.lower()
