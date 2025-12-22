"""
Pytest fixtures for compliance tests.

Enables PII tokenization feature flag required for GDPR/HIPAA compliance testing.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

if TYPE_CHECKING:
    pass


@pytest.fixture(autouse=True)
def enable_pii_tokenization_for_compliance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable PII tokenization feature flag for all compliance tests.

    This fixture patches feature_flags in the core module and the privacy
    modules to enable PII detection and tokenization functionality.

    The PII tokenization feature is disabled by default to minimize overhead,
    but must be enabled for GDPR and HIPAA compliance testing.
    """
    # Get the feature flags module
    ff_module = sys.modules.get("mcp_server_langgraph.core.feature_flags")

    # Create mock with PII tokenization enabled
    mock_flags = MockFeatureFlags(
        enable_pii_tokenization=True,
        # Enable test mode to bypass other feature checks
        is_test_mode=True,
    )

    # Patch at the core module level if loaded
    if ff_module is not None:
        monkeypatch.setattr(ff_module, "feature_flags", mock_flags)

    # Patch the is_feature_enabled function in the detectors module
    # This is the function checked at runtime to gate PII detection
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


@pytest.fixture(autouse=True)
def ensure_privacy_modules_loaded() -> None:
    """Ensure privacy modules are imported before patching.

    This fixture forces the import of privacy modules so they're
    available for patching by the feature flag fixture.
    """
    # Import to ensure modules are loaded
    import mcp_server_langgraph.privacy.detectors  # noqa: F401
    import mcp_server_langgraph.privacy.lookup_table  # noqa: F401
    import mcp_server_langgraph.privacy.tokenizer  # noqa: F401
