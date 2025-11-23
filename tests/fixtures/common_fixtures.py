import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root():
    """Find project root directory in any environment (local, Docker, CI)."""
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml", "setup.py"]
    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent
    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.fixture
def settings_isolation(monkeypatch):
    """Fixture that provides automatic settings isolation and restoration."""
    return monkeypatch
