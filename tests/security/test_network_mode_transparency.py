"""
Security tests for network mode transparency (OpenAI Codex Finding #3)

SECURITY FINDING:
Production resource limits default to network_mode="allowlist" but _get_network_mode()
downgrades to "none" because allowlist is unimplemented. This creates misleading
configuration expectations.

This test suite validates that:
1. Production profile accurately reflects actual network behavior
2. Documentation clearly states allowlist is not yet implemented
3. Operators receive clear warnings when allowlist is requested
4. System fails closed (denies network) rather than allowing unrestricted access

References:
- src/mcp_server_langgraph/execution/resource_limits.py:170-183
- src/mcp_server_langgraph/execution/docker_sandbox.py:264-288
- CWE-670: Always-Incorrect Control Flow Implementation
"""

import gc
import logging
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.execution.resource_limits import ResourceLimits

# Docker is an optional dependency - mock if not available
try:
    from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    DockerSandbox = MagicMock


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="security_network_mode_transparency_tests")
class TestNetworkModeTransparency:
    """Test suite for network mode configuration transparency"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_production_profile_network_mode_is_none(self):
        """
        SECURITY TEST: Production profile should set network_mode="none" to match actual behavior

        The previous config set network_mode="allowlist" but that's not implemented,
        creating false expectations. Configuration should reflect reality.
        """
        limits = ResourceLimits.production()

        assert limits.network_mode == "none", (
            "SECURITY: Production profile must accurately reflect that network is disabled. "
            f"Got network_mode='{limits.network_mode}' but allowlist is not implemented. "
            "Use network_mode='none' for transparency."
        )

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_allowlist_mode_fails_closed_with_warning(self, caplog):
        """
        SECURITY TEST: When allowlist is requested (future feature), system must fail closed

        Until allowlist filtering is implemented, requesting it should:
        1. Return network_mode='none' (fail closed)
        2. Log clear warning explaining the limitation
        """
        limits = ResourceLimits(
            timeout_seconds=30, memory_limit_mb=512, network_mode="allowlist", allowed_domains=("pypi.org", "github.com")
        )

        sandbox = DockerSandbox(limits=limits)

        with caplog.at_level(logging.WARNING):
            network_mode = sandbox._get_network_mode()

        # Must fail closed
        assert network_mode == "none", f"SECURITY: Allowlist mode must fail closed to 'none', got '{network_mode}'"

        # Must log warning
        assert any(
            "allowlist" in record.message.lower() and "not implemented" in record.message.lower() for record in caplog.records
        ), "Expected warning about unimplemented allowlist not found in logs"

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_none_network_mode_works_correctly(self):
        """
        Test that network_mode='none' correctly disables networking

        This is the secure default and current production behavior.
        """
        limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512, network_mode="none")

        sandbox = DockerSandbox(limits=limits)
        network_mode = sandbox._get_network_mode()

        assert network_mode == "none"

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_unrestricted_network_mode_enables_network(self):
        """
        Test that network_mode='unrestricted' enables network access

        This is for cases where network access is explicitly required.
        """
        limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512, network_mode="unrestricted")

        sandbox = DockerSandbox(limits=limits)
        network_mode = sandbox._get_network_mode()

        assert network_mode == "bridge", f"Unrestricted mode should use 'bridge', got '{network_mode}'"

    def test_development_profile_network_mode_is_explicit(self):
        """
        Test that development profile explicitly sets network expectations
        """
        limits = ResourceLimits.development()

        # Development should have explicit network mode
        assert limits.network_mode in (
            "none",
            "unrestricted",
        ), f"Development profile has unclear network_mode: {limits.network_mode}"

    def test_testing_profile_network_mode_is_none(self):
        """
        Test that testing profile disables network (deterministic tests)
        """
        limits = ResourceLimits.testing()

        assert limits.network_mode == "none", "Testing profile should disable network for deterministic tests"


@pytest.mark.security
@pytest.mark.integration
@pytest.mark.xdist_group(name="security_network_mode_transparency_tests")
class TestNetworkModeDocumentation:
    """Test suite for network mode documentation"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_resource_limits_production_has_network_documentation(self):
        """
        Test that ResourceLimits.production() docstring documents network behavior
        """
        docstring = ResourceLimits.production.__doc__

        assert docstring is not None, "production() method must have docstring"
        assert "network" in docstring.lower(), "production() docstring must mention network mode"

    def test_network_mode_parameter_has_documentation(self):
        """
        Test that network_mode parameter is documented in ResourceLimits
        """
        # Check class docstring or __init__ docstring
        class_doc = ResourceLimits.__doc__ or ""
        init_doc = ResourceLimits.__init__.__doc__ or ""

        combined_docs = (class_doc + init_doc).lower()

        assert "network" in combined_docs, "ResourceLimits must document network_mode parameter"

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_docker_sandbox_documents_allowlist_limitation(self):
        """
        Test that DockerSandbox documents that allowlist is not implemented
        """
        # Check _get_network_mode has documentation about allowlist
        _ = DockerSandbox._get_network_mode.__doc__ or ""  # noqa: F841

        # At minimum, the code should have comments (checked via reading source)
        # This test ensures the limitation is documented somewhere
        import inspect

        source = inspect.getsource(DockerSandbox._get_network_mode)

        assert "allowlist" in source.lower(), "_get_network_mode must reference allowlist mode"
        assert (
            "not implemented" in source.lower() or "fail closed" in source.lower()
        ), "_get_network_mode must document that allowlist is not implemented"


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="security_network_mode_transparency_tests")
class TestNetworkModeSecurityDefaults:
    """Test suite for network mode security defaults"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_default_network_mode_is_none(self):
        """
        SECURITY TEST: Default network mode should be 'none' (fail-closed)

        If no network mode is specified, default to most restrictive (none).
        """
        limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)

        assert (
            limits.network_mode == "none"
        ), f"SECURITY: Default network_mode should be 'none' (fail-closed), got '{limits.network_mode}'"

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_allowed_domains_ignored_when_network_disabled(self):
        """
        Test that allowed_domains has no effect when network_mode='none'

        This prevents confusion about what allowed_domains does.
        """
        limits = ResourceLimits(
            timeout_seconds=30,
            memory_limit_mb=512,
            network_mode="none",
            allowed_domains=("pypi.org", "github.com"),  # These should have no effect
        )

        sandbox = DockerSandbox(limits=limits)
        network_mode = sandbox._get_network_mode()

        # Network should still be disabled regardless of allowed_domains
        assert network_mode == "none"

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_empty_allowed_domains_with_unrestricted_mode(self):
        """
        Test that unrestricted mode works even with empty allowed_domains

        This clarifies that allowed_domains only matters for allowlist mode.
        """
        limits = ResourceLimits(
            timeout_seconds=30,
            memory_limit_mb=512,
            network_mode="unrestricted",
            allowed_domains=(),  # Empty, but unrestricted should still work
        )

        sandbox = DockerSandbox(limits=limits)
        network_mode = sandbox._get_network_mode()

        assert network_mode == "bridge"


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.xdist_group(name="security_network_mode_transparency_tests")
class TestFutureAllowlistImplementation:
    """Test suite for future allowlist implementation requirements"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_allowlist_will_require_allowed_domains(self):
        """
        Document that future allowlist implementation will require allowed_domains

        This test serves as documentation for future implementers.
        """
        # When allowlist is implemented, it should validate allowed_domains
        limits = ResourceLimits(
            timeout_seconds=30,
            memory_limit_mb=512,
            network_mode="allowlist",
            allowed_domains=(),  # Empty - should this be valid?
        )

        # For now, this is allowed because allowlist isn't implemented
        # Future implementation should consider whether empty allowlist is valid
        assert limits.allowed_domains == ()

    @pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker package not available")
    def test_allowlist_mode_preserves_allowed_domains_config(self):
        """
        Test that allowed_domains configuration is preserved for future use

        Even though allowlist isn't implemented, the config should be stored.
        """
        domains = ("pypi.org", "github.com", "anthropic.com")
        limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512, network_mode="allowlist", allowed_domains=domains)

        # Configuration should be preserved
        assert limits.allowed_domains == domains

        # But actual behavior is still 'none'
        sandbox = DockerSandbox(limits=limits)
        assert sandbox._get_network_mode() == "none"
