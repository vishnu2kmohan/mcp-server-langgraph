"""
Pytest fixtures for integration tests.

Enables test mode to bypass feature flag checks for all experimental features.
This allows integration tests to test feature interactions without complex mocking.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest

from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

if TYPE_CHECKING:
    pass


@pytest.fixture(scope="session", autouse=True)
def enable_test_mode_for_integration() -> None:
    """Enable test mode for all integration tests.

    Sets FF_TEST_MODE=true which bypasses all feature flag checks in
    require_feature(). This allows integration tests to test experimental
    features (multi-agent orchestration, agentic memory, skills system, etc.)
    without needing to individually mock each feature flag.

    Note: This is set at session scope to avoid repeated environment
    modifications and ensure consistent behavior across all integration tests.
    """
    os.environ["FF_TEST_MODE"] = "true"
    # Also enable PII tokenization feature flag
    os.environ["FF_ENABLE_PII_TOKENIZATION"] = "true"


@pytest.fixture(autouse=True)
def enable_pii_for_integration_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable PII tokenization for integration tests that use the privacy module.

    This patches the is_feature_enabled function in the detectors module
    to return True for pii_tokenization checks.
    """
    # Get the feature flags module
    ff_module = sys.modules.get("mcp_server_langgraph.core.feature_flags")

    # Create mock with PII tokenization enabled
    mock_flags = MockFeatureFlags(
        enable_pii_tokenization=True,
        is_test_mode=True,
    )

    # Patch at the core module level if loaded
    if ff_module is not None:
        monkeypatch.setattr(ff_module, "feature_flags", mock_flags)

    # Patch the is_feature_enabled function in the detectors module
    privacy_detectors = sys.modules.get("mcp_server_langgraph.privacy.detectors")
    if privacy_detectors is not None:

        def mock_is_feature_enabled(flag_name: str) -> bool:
            """Mock is_feature_enabled to enable pii_tokenization."""
            if flag_name == "pii_tokenization":
                return True
            return mock_flags.is_feature_enabled(flag_name)

        monkeypatch.setattr(privacy_detectors, "is_feature_enabled", mock_is_feature_enabled)

    # Also ensure the core is_feature_enabled is patched
    if ff_module is not None and hasattr(ff_module, "is_feature_enabled"):

        def core_mock_is_feature_enabled(flag_name: str) -> bool:
            """Mock core is_feature_enabled."""
            if flag_name == "pii_tokenization":
                return True
            return mock_flags.is_feature_enabled(flag_name)

        monkeypatch.setattr(ff_module, "is_feature_enabled", core_mock_is_feature_enabled)
