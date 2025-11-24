import pytest
import os


@pytest.fixture
def disable_auth_skip(monkeypatch):
    """Disable MCP_SKIP_AUTH for tests requiring real authentication."""
    monkeypatch.setenv("MCP_SKIP_AUTH", "false")


@pytest.fixture
def isolated_environment(monkeypatch):
    """Provide isolated environment for pollution-sensitive tests."""
    return monkeypatch
