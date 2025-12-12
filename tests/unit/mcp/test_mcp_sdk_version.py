"""
Tests for MCP SDK version compatibility with 2025-11-25 specification.

TDD: RED phase - This test defines expected behavior for MCP spec upgrade.
"""

import gc

import pytest
from packaging import version

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_sdk_version")
class TestMCPSDKVersion:
    """Test MCP SDK version supports 2025-11-25 specification."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.timeout(60)  # Reduced timeout for faster feedback
    def test_mcp_sdk_version_supports_2025_11_25_spec(self) -> None:
        """MCP SDK version must be >= 1.23.0 for 2025-11-25 spec support.

        The MCP Python SDK 1.23.0 was the first version to support
        the MCP specification 2025-11-25. Key features include:
        - SEP-1577: Sampling with Tools
        - SEP-1686: Tasks feature
        - SEP-1330: Enhanced Elicitation enum schemas
        - SEP-973: Icons metadata
        - SEP-1036: URL mode elicitation
        - SEP-1303: Tool validation errors as Tool Errors
        """
        from importlib.metadata import version as pkg_version

        mcp_version_str = pkg_version("mcp")
        sdk_version = version.parse(mcp_version_str)
        min_required = version.parse("1.23.0")

        assert sdk_version >= min_required, (
            f"MCP SDK version {mcp_version_str} is too old. Version >= 1.23.0 required for MCP spec 2025-11-25 support."
        )

    @pytest.mark.timeout(60)  # Reduced timeout for faster feedback
    def test_mcp_sdk_has_latest_protocol_version_constant(self) -> None:
        """MCP SDK should have LATEST_PROTOCOL_VERSION for 2025-11-25."""
        try:
            from mcp import LATEST_PROTOCOL_VERSION

            # SDK 1.23.1+ sets this to 2025-11-25
            assert LATEST_PROTOCOL_VERSION == "2025-11-25", (
                f"Expected LATEST_PROTOCOL_VERSION='2025-11-25', got '{LATEST_PROTOCOL_VERSION}'"
            )
        except ImportError:
            # Older SDKs may not export this constant
            pytest.skip("LATEST_PROTOCOL_VERSION not available in this SDK version")
