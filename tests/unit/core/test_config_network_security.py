"""
🔴 RED PHASE - Test for network security configuration defaults

SECURITY FINDING #3: Default network mode must be secure.

This test validates that the default network mode for code execution is "none" (maximum isolation)
rather than "allowlist" or "unrestricted". Users must explicitly opt-in to network access.

Expected to FAIL until core/config.py:216 is fixed to default to "none".
"""

import os


def test_default_network_mode_is_secure_none():
    """
    🔴 RED: Test that Settings defaults code_execution_network_mode to "none".

    SECURITY CRITICAL: Code execution should default to maximum network isolation.

    This test will FAIL because core/config.py:216 currently defaults to "allowlist".
    Expected to PASS after fixing the default to "none".
    """
    # Set environment to test to avoid production validation errors
    os.environ["ENVIRONMENT"] = "test"

    # Import after setting environment
    from mcp_server_langgraph.core.config import Settings

    settings = Settings()

    assert settings.code_execution_network_mode == "none", (
        "SECURITY VULNERABILITY: Default network mode must be 'none' for maximum isolation. "
        f"Got: {settings.code_execution_network_mode}. "
        "Users must explicitly enable network access (allowlist or unrestricted). "
        "This prevents accidental network exposure in sandboxed code execution."
    )


def test_network_mode_can_be_explicitly_set_to_allowlist():
    """
    Verify that network mode CAN be explicitly set to allowlist if desired.

    This ensures the fix doesn't prevent legitimate use cases.
    """
    os.environ["ENVIRONMENT"] = "test"
    os.environ["CODE_EXECUTION_NETWORK_MODE"] = "allowlist"

    from mcp_server_langgraph.core.config import Settings

    settings = Settings()

    assert settings.code_execution_network_mode == "allowlist"

    # Clean up
    del os.environ["CODE_EXECUTION_NETWORK_MODE"]


def test_network_mode_can_be_explicitly_set_to_unrestricted():
    """
    Verify that network mode CAN be explicitly set to unrestricted if desired.

    This ensures the fix doesn't prevent legitimate use cases.
    """
    os.environ["ENVIRONMENT"] = "test"
    os.environ["CODE_EXECUTION_NETWORK_MODE"] = "unrestricted"

    from mcp_server_langgraph.core.config import Settings

    settings = Settings()

    assert settings.code_execution_network_mode == "unrestricted"

    # Clean up
    del os.environ["CODE_EXECUTION_NETWORK_MODE"]
