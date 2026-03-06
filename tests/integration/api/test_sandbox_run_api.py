"""
Integration smoke tests for /api/v1/sandbox/run.

These tests hit the sandbox runner endpoint to verify:
- bash commands execute inside the sandbox container
- web_fetch works with the sandbox image and unrestricted network mode
- screenshot capture succeeds with Playwright/Chromium in the sandbox image
"""

from __future__ import annotations

import gc
import json
from typing import Any

import pytest
from mcp_server_langgraph.api.v1 import sandbox as sandbox_api
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.config import settings

pytestmark = pytest.mark.integration


def _require_sandbox_env() -> None:
    """Skip tests if sandbox prerequisites aren't met."""
    if not settings.enable_code_execution:
        pytest.skip("Code execution is disabled; sandbox runner not available")
    if settings.code_execution_backend != "docker-engine":
        pytest.skip("Sandbox runner tests require docker-engine backend")
    if settings.code_execution_network_mode != "unrestricted":
        pytest.skip("Sandbox runner tests require CODE_EXECUTION_NETWORK_MODE=unrestricted for fetch/screenshot")

    try:
        import docker
    except Exception:
        pytest.skip("Docker package not available")

    # Ensure the configured sandbox image is present to avoid long pulls during tests
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.images.get(settings.code_execution_docker_image)
    except Exception as exc:
        pytest.skip(f"Docker sandbox image not available: {exc}")


@pytest.fixture
def sandbox_client() -> TestClient:
    """Create a TestClient with auth dependencies overridden."""
    _require_sandbox_env()

    from mcp_server_langgraph.auth import dependencies as auth_deps
    from mcp_server_langgraph.mcp.server_streamable import app

    mock_user = {
        "user_id": "test-user",
        "username": "test",
        "email": "test@example.com",
        "roles": ["admin", "user"],
    }

    # Bypass auth for tests
    app.dependency_overrides[auth_deps.get_current_user] = lambda: mock_user
    app.dependency_overrides[auth_deps.get_current_user_with_auth] = lambda: mock_user
    app.dependency_overrides[sandbox_api.get_current_user] = lambda: mock_user

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Cleanup overrides to avoid cross-test pollution
    app.dependency_overrides.clear()
    gc.collect()


def _post_sandbox(client: TestClient, payload: dict[str, Any]):
    response = client.post("/api/v1/sandbox/run", json=payload)
    assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text}"
    return response.json()


@pytest.mark.xdist_group(name="sandbox_api")
class TestSandboxAPI:
    """Smoke tests for sandbox runner endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_bash_echo_command_returns_stdout(self, sandbox_client: TestClient):
        result = _post_sandbox(
            sandbox_client,
            {"type": "bash", "command": "echo hello-sandbox"},
        )
        assert result["exit_code"] == 0
        assert "hello-sandbox" in (result.get("stdout") or "")

    def test_web_fetch_example_com(self, sandbox_client: TestClient):
        result = _post_sandbox(
            sandbox_client,
            {"type": "web_fetch", "url": "https://example.com"},
        )
        assert result["exit_code"] == 0
        assert result.get("stdout")
        # Basic sanity that we fetched HTML
        assert "example" in result.get("stdout", "").lower()

    def test_screenshot_capture_returns_png_image(self, sandbox_client: TestClient):
        result = _post_sandbox(
            sandbox_client,
            {"type": "screenshot", "url": "https://example.com"},
        )
        assert result["exit_code"] == 0
        assert result.get("stdout")
        # stdout should be JSON with image_data
        data = json.loads(result["stdout"])
        assert "image_data" in data
        assert data.get("mime_type") == "image/png"
