"""
Unit tests for Docker sandbox with mocked Docker client.

Tests focus on security-critical logic without requiring Docker.
Following TDD - targets low-coverage methods from Codex audit.

Coverage targets:
- _get_network_mode() - Network isolation security logic (~2% coverage)
- Security configurations and error handling
"""

import gc
from unittest.mock import MagicMock, patch

import pytest


# Docker is an optional dependency - skip tests if not available
try:
    from docker.errors import ImageNotFound, NotFound

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    ImageNotFound = Exception  # type: ignore[misc, assignment]
    NotFound = Exception  # type: ignore[misc, assignment]

from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import SandboxError


pytestmark = pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not installed")


@pytest.mark.unit
@pytest.mark.xdist_group(name="docker_sandbox_unit")
class TestDockerSandboxNetworkMode:
    """Test network mode security logic (security-critical)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_network_mode_none_is_secure_default(self):
        """
        Test that network mode 'none' returns 'none' (maximum isolation)

        SECURITY: Validates default secure configuration
        """
        limits = ResourceLimits(network_mode="none")

        with patch("docker.DockerClient") as mock_docker_client:
            mock_client = MagicMock()
            mock_docker_client.return_value = mock_client
            sandbox = DockerSandbox(limits=limits)
            result = sandbox._get_network_mode()

        assert result == "none", "Network mode 'none' must return 'none' for security"

    def test_get_network_mode_unrestricted_returns_bridge(self):
        """
        Test that network mode 'unrestricted' returns 'bridge'

        SECURITY: Explicit opt-in to network access required
        """
        limits = ResourceLimits(network_mode="unrestricted")

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            sandbox = DockerSandbox(limits=limits)
            result = sandbox._get_network_mode()

        assert result == "bridge", "Unrestricted mode should return 'bridge' (Docker default)"

    def test_get_network_mode_allowlist_fails_closed_to_none(self):
        """
        Test that unimplemented 'allowlist' mode fails closed to 'none'

        SECURITY CRITICAL: CWE-1188 mitigation - unimplemented features fail safely
        """
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=("httpbin.org", "example.com"),
        )

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            sandbox = DockerSandbox(limits=limits)

            # Should log warning about unimplemented feature
            with patch("mcp_server_langgraph.execution.docker_sandbox.logger") as mock_logger:
                result = sandbox._get_network_mode()

                # Verify warning was logged
                assert mock_logger.warning.called
                warning_msg = str(mock_logger.warning.call_args)
                assert "not implemented" in warning_msg.lower()

        assert result == "none", (
            "SECURITY: Unimplemented allowlist mode MUST fail closed to 'none'. "
            "This prevents false sense of security (CWE-1188)."
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="docker_sandbox_unit")
class TestDockerSandboxInitialization:
    """Test sandbox initialization and Docker client connection"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_init_connects_to_docker_successfully(self):
        """Test that initialization connects to Docker daemon"""
        limits = ResourceLimits.testing()

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client

            sandbox = DockerSandbox(limits=limits)

        assert mock_docker.called
        assert sandbox.client is not None

    def test_init_handles_docker_unavailable_gracefully(self):
        """
        Test graceful failure when Docker is not available

        Error handling: Should provide clear error message
        """
        limits = ResourceLimits.testing()

        with patch("docker.DockerClient") as mock_docker:
            mock_docker.side_effect = Exception("Cannot connect to Docker daemon")

            with pytest.raises(SandboxError) as exc_info:
                DockerSandbox(limits=limits)

            error_msg = str(exc_info.value).lower()
            assert "docker" in error_msg

    def test_init_uses_custom_image_when_specified(self):
        """Test that custom Docker image can be specified"""
        limits = ResourceLimits.testing()
        custom_image = "python:3.11-alpine"

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            sandbox = DockerSandbox(limits=limits, image=custom_image)

        assert sandbox.image == custom_image


@pytest.mark.unit
@pytest.mark.xdist_group(name="docker_sandbox_unit")
class TestDockerSandboxErrorHandling:
    """Test error handling for Docker operations"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_handles_image_not_found_with_clear_error(self):
        """
        Test graceful handling when Docker image is not available

        Error handling: Should provide actionable error message during image pull
        """
        limits = ResourceLimits.testing()

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            # Mock the images.get to raise ImageNotFound during _ensure_image
            mock_client.images.get.side_effect = ImageNotFound("Image not found")
            mock_client.images.pull.side_effect = ImageNotFound("Pull failed")
            mock_docker.return_value = mock_client

            with pytest.raises(SandboxError) as exc_info:
                DockerSandbox(limits=limits)

            error_msg = str(exc_info.value).lower()
            assert "image" in error_msg or "not found" in error_msg or "pull" in error_msg

    def test_cleanup_handles_already_removed_container(self):
        """
        Test cleanup handles containers that are already removed

        Idempotency: Cleanup should be safe to call multiple times
        """
        limits = ResourceLimits.testing()

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_container = MagicMock()
            mock_container.stop.side_effect = NotFound("Container not found")

            sandbox = DockerSandbox(limits=limits)

            # Should not raise - cleanup should be idempotent
            sandbox._cleanup_container(mock_container)

    def test_cleanup_resilient_to_stop_errors(self):
        """
        Test cleanup handles errors when stopping container

        Error handling: Should still attempt to remove even if stop fails
        """
        limits = ResourceLimits.testing()

        with patch("docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_container = MagicMock()
            mock_container.stop.side_effect = Exception("Stop failed")

            sandbox = DockerSandbox(limits=limits)

            # Should not raise - cleanup should be resilient
            sandbox._cleanup_container(mock_container)

            # Should still attempt to remove
            assert mock_container.remove.called
