"""
Unit tests for network mode logic in DockerSandbox

Tests the _get_network_mode method to ensure it fails closed when allowlist is not implemented.
These tests don't require Docker to be installed.
"""

from unittest.mock import MagicMock, patch


def test_allowlist_mode_fails_closed_with_domains():
    """
    🟢 GREEN: Test that allowlist mode returns "none" when domains are specified.

    SECURITY: Unimplemented allowlist must fail closed, not fall back to bridge (unrestricted).
    """
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


def test_allowlist_mode_with_no_domains_returns_none():
    """
    Test that allowlist mode with no domains returns "none".
    """
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


def test_network_mode_none_returns_none():
    """Test that network_mode="none" returns "none"."""
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


def test_network_mode_unrestricted_returns_bridge():
    """Test that network_mode="unrestricted" returns "bridge"."""
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
