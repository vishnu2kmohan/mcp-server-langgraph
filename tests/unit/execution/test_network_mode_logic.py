"""
Unit tests for network mode logic in DockerSandbox

Tests the _get_network_mode method to ensure it fails closed when allowlist is not implemented.
These tests don't require Docker to be installed.

NOTE: The project has a docker/ directory (for Docker configs) that can shadow
the docker Python package during import. We handle this by clearing module
cache before each test.
"""

import gc
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def _clear_docker_module_cache():
    """Clear docker module from cache to prevent shadowing by docker/ directory."""
    # Remove any cached docker modules to allow fresh mocking
    modules_to_clear = [key for key in sys.modules.keys() if key == "docker" or key.startswith("docker.")]
    for mod in modules_to_clear:
        del sys.modules[mod]
    # Also clear our module that imports docker
    if "mcp_server_langgraph.execution.docker_sandbox" in sys.modules:
        del sys.modules["mcp_server_langgraph.execution.docker_sandbox"]


@pytest.mark.xdist_group(name="network_mode_logic")
class TestNetworkModeLogic:
    """Test network mode logic in DockerSandbox."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_allowlist_mode_fails_closed_with_domains(self):
        """
        🟢 GREEN: Test that allowlist mode returns "none" when domains are specified.

        SECURITY: Unimplemented allowlist must fail closed, not fall back to bridge (unrestricted).
        """
        # Clear module cache to prevent docker/ directory shadowing
        _clear_docker_module_cache()

        # Mock the docker imports to avoid import errors
        with patch.dict(
            "sys.modules",
            {
                "docker": MagicMock(),
                "docker.models": MagicMock(),
                "docker.models.containers": MagicMock(),
                "docker.errors": MagicMock(),
                "docker.types": MagicMock(),
            },
        ):
            from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
            from mcp_server_langgraph.execution.resource_limits import ResourceLimits

            # Create limits with allowlist mode and domains
            limits = ResourceLimits(
                network_mode="allowlist",
                allowed_domains=("httpbin.org", "example.com"),
            )

            # Create sandbox (mock docker client)
            with patch("mcp_server_langgraph.execution.docker_sandbox.docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client

                sandbox = DockerSandbox(limits=limits)

                # Call _get_network_mode
                network_mode = sandbox._get_network_mode()

                # Should fail closed to "none", NOT "bridge"
                assert network_mode == "none", f"Allowlist mode with domains must fail closed to 'none'. Got: {network_mode}"

    def test_allowlist_mode_with_no_domains_returns_none(self):
        """
        Test that allowlist mode with no domains returns "none".
        """
        # Clear module cache to prevent docker/ directory shadowing
        _clear_docker_module_cache()

        with patch.dict(
            "sys.modules",
            {
                "docker": MagicMock(),
                "docker.models": MagicMock(),
                "docker.models.containers": MagicMock(),
                "docker.errors": MagicMock(),
                "docker.types": MagicMock(),
            },
        ):
            from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
            from mcp_server_langgraph.execution.resource_limits import ResourceLimits

            limits = ResourceLimits(
                network_mode="allowlist",
                allowed_domains=(),  # Empty tuple
            )

            with patch("mcp_server_langgraph.execution.docker_sandbox.docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client

                sandbox = DockerSandbox(limits=limits)
                network_mode = sandbox._get_network_mode()

                assert network_mode == "none"

    def test_network_mode_none_returns_none(self):
        """Test that network_mode="none" returns "none"."""
        # Clear module cache to prevent docker/ directory shadowing
        _clear_docker_module_cache()

        with patch.dict(
            "sys.modules",
            {
                "docker": MagicMock(),
                "docker.models": MagicMock(),
                "docker.models.containers": MagicMock(),
                "docker.errors": MagicMock(),
                "docker.types": MagicMock(),
            },
        ):
            from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
            from mcp_server_langgraph.execution.resource_limits import ResourceLimits

            limits = ResourceLimits(network_mode="none")

            with patch("mcp_server_langgraph.execution.docker_sandbox.docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client

                sandbox = DockerSandbox(limits=limits)
                network_mode = sandbox._get_network_mode()

                assert network_mode == "none"

    def test_network_mode_unrestricted_returns_bridge(self):
        """Test that network_mode="unrestricted" returns "bridge"."""
        # Clear module cache to prevent docker/ directory shadowing
        _clear_docker_module_cache()

        with patch.dict(
            "sys.modules",
            {
                "docker": MagicMock(),
                "docker.models": MagicMock(),
                "docker.models.containers": MagicMock(),
                "docker.errors": MagicMock(),
                "docker.types": MagicMock(),
            },
        ):
            from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
            from mcp_server_langgraph.execution.resource_limits import ResourceLimits

            limits = ResourceLimits(network_mode="unrestricted")

            with patch("mcp_server_langgraph.execution.docker_sandbox.docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client

                sandbox = DockerSandbox(limits=limits)
                network_mode = sandbox._get_network_mode()

                assert network_mode == "bridge"
