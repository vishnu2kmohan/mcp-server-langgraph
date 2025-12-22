"""
Pytest fixtures for execution tests.

Enables feature flags required for programmatic tools testing.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

if TYPE_CHECKING:
    pass


@pytest.fixture(autouse=True)
def mock_feature_flags_for_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable programmatic tools feature flags for all execution tests.

    This fixture patches feature_flags in the core module.
    The @feature_gated decorator imports from core.feature_flags,
    so we only need to patch there.
    """
    # Get the actual module (not the exported singleton)
    ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]

    # Create mock with programmatic tools enabled
    mock_flags = MockFeatureFlags(
        enable_programmatic_tools=True,
    )

    # Patch at core module level (decorator imports from here)
    monkeypatch.setattr(ff_module, "feature_flags", mock_flags)
