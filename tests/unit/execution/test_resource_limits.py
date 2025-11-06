"""
Unit tests for resource limits configuration

Tests timeout, memory, CPU quota validation and enforcement.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

# This import will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.execution.resource_limits import ResourceLimitError, ResourceLimits
except ImportError:
    pytest.skip("ResourceLimits not implemented yet", allow_module_level=True)


@pytest.mark.unit
class TestResourceLimits:
    """Test suite for ResourceLimits configuration"""

    def test_default_resource_limits(self):
        """Test default resource limit values"""
        limits = ResourceLimits()
        assert limits.timeout_seconds > 0
        assert limits.memory_limit_mb > 0
        assert limits.cpu_quota > 0

    def test_custom_resource_limits(self):
        """Test creating custom resource limits"""
        limits = ResourceLimits(
            timeout_seconds=60,
            memory_limit_mb=1024,
            cpu_quota=2.0,
        )
        assert limits.timeout_seconds == 60
        assert limits.memory_limit_mb == 1024
        assert limits.cpu_quota == 2.0

    def test_timeout_validation_positive(self):
        """Test that timeout must be positive"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(timeout_seconds=0)

        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(timeout_seconds=-10)

    def test_timeout_maximum_limit(self):
        """Test that timeout has a reasonable maximum"""
        # Should reject extremely large timeouts (e.g., > 10 minutes)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(timeout_seconds=36000)  # 10 hours

    def test_memory_limit_validation_positive(self):
        """Test that memory limit must be positive"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(memory_limit_mb=0)

        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(memory_limit_mb=-512)

    def test_memory_limit_minimum(self):
        """Test that memory limit has a reasonable minimum"""
        # Should reject too small memory limits (< 64MB)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(memory_limit_mb=32)

    def test_memory_limit_maximum(self):
        """Test that memory limit has a reasonable maximum"""
        # Should reject too large memory limits (> 16GB)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(memory_limit_mb=20480)  # 20GB

    def test_cpu_quota_validation_positive(self):
        """Test that CPU quota must be positive"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(cpu_quota=0)

        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(cpu_quota=-1.0)

    def test_cpu_quota_maximum(self):
        """Test that CPU quota has a reasonable maximum"""
        # Should reject too many CPUs (> 8 cores for sandbox)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(cpu_quota=16.0)

    def test_cpu_quota_fractional(self):
        """Test that CPU quota accepts fractional values"""
        limits = ResourceLimits(cpu_quota=0.5)
        assert limits.cpu_quota == 0.5

        limits = ResourceLimits(cpu_quota=1.5)
        assert limits.cpu_quota == 1.5

    def test_resource_limits_immutable(self):
        """Test that resource limits are immutable after creation"""
        limits = ResourceLimits(timeout_seconds=30)

        # Should not be able to modify after creation (if using frozen dataclass)
        with pytest.raises((AttributeError, TypeError)):
            limits.timeout_seconds = 60

    def test_resource_limits_repr(self):
        """Test string representation of resource limits"""
        limits = ResourceLimits(
            timeout_seconds=30,
            memory_limit_mb=512,
            cpu_quota=1.0,
        )
        repr_str = repr(limits)
        assert "30" in repr_str
        assert "512" in repr_str

    def test_resource_limits_dict_conversion(self):
        """Test converting resource limits to dictionary"""
        limits = ResourceLimits(
            timeout_seconds=30,
            memory_limit_mb=512,
            cpu_quota=1.0,
        )

        # Should be able to convert to dict for serialization
        limit_dict = limits.to_dict()
        assert limit_dict["timeout_seconds"] == 30
        assert limit_dict["memory_limit_mb"] == 512
        assert limit_dict["cpu_quota"] == 1.0

    def test_resource_limits_from_dict(self):
        """Test creating resource limits from dictionary"""
        limit_dict = {
            "timeout_seconds": 45,
            "memory_limit_mb": 768,
            "cpu_quota": 1.5,
        }
        limits = ResourceLimits.from_dict(limit_dict)
        assert limits.timeout_seconds == 45
        assert limits.memory_limit_mb == 768
        assert limits.cpu_quota == 1.5

    def test_network_access_control(self):
        """Test network access mode configuration"""
        # Test no network mode
        limits = ResourceLimits(network_mode="none")
        assert limits.network_mode == "none"

        # Test allowlist mode
        limits = ResourceLimits(
            network_mode="allowlist",
            allowed_domains=["api.example.com", "data.example.com"],
        )
        assert limits.network_mode == "allowlist"
        assert "api.example.com" in limits.allowed_domains

    def test_network_mode_validation(self):
        """Test that network mode must be valid"""
        valid_modes = ["none", "allowlist", "unrestricted"]

        for mode in valid_modes:
            limits = ResourceLimits(network_mode=mode)
            assert limits.network_mode == mode

        # Invalid mode should raise error
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(network_mode="invalid_mode")

    def test_network_allowlist_with_empty_domains(self):
        """Test that allowlist mode allows empty domains (blocks all network)"""
        # Empty allowlist is allowed (effectively blocks all network)
        # This allows configuring profile first, then adding domains later
        limits = ResourceLimits(network_mode="allowlist", allowed_domains=[])
        assert limits.network_mode == "allowlist"
        assert len(limits.allowed_domains) == 0

    def test_disk_quota_configuration(self):
        """Test disk quota configuration"""
        limits = ResourceLimits(disk_quota_mb=100)
        assert limits.disk_quota_mb == 100

    def test_disk_quota_validation(self):
        """Test disk quota validation"""
        # Should reject negative or zero
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(disk_quota_mb=0)

        # Should reject too large (> 10GB)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(disk_quota_mb=15360)  # 15GB

    def test_max_processes_configuration(self):
        """Test maximum process limit configuration"""
        limits = ResourceLimits(max_processes=10)
        assert limits.max_processes == 10

    def test_max_processes_validation(self):
        """Test maximum process validation"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(max_processes=0)

        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(max_processes=-5)

        # Should reject too many processes (> 100)
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(max_processes=500)


@pytest.mark.unit
@pytest.mark.property
class TestResourceLimitsProperties:
    """Property-based tests for resource limits"""

    @given(st.integers(min_value=1, max_value=600))
    def test_valid_timeout_range_accepted(self, timeout):
        """Property: all timeouts in valid range should be accepted"""
        limits = ResourceLimits(timeout_seconds=timeout)
        assert limits.timeout_seconds == timeout

    @given(st.integers(min_value=64, max_value=8192))
    def test_valid_memory_range_accepted(self, memory_mb):
        """Property: all memory limits in valid range should be accepted"""
        limits = ResourceLimits(memory_limit_mb=memory_mb)
        assert limits.memory_limit_mb == memory_mb

    @given(st.floats(min_value=0.1, max_value=8.0))
    def test_valid_cpu_quota_range_accepted(self, cpu_quota):
        """Property: all CPU quotas in valid range should be accepted"""
        limits = ResourceLimits(cpu_quota=cpu_quota)
        assert abs(limits.cpu_quota - cpu_quota) < 0.001

    @given(st.integers(max_value=0))
    def test_non_positive_timeout_rejected(self, timeout):
        """Property: all non-positive timeouts should be rejected"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(timeout_seconds=timeout)

    @given(st.integers(max_value=0))
    def test_non_positive_memory_rejected(self, memory_mb):
        """Property: all non-positive memory limits should be rejected"""
        with pytest.raises((ValueError, ResourceLimitError)):
            ResourceLimits(memory_limit_mb=memory_mb)


@pytest.mark.unit
class TestResourceLimitError:
    """Test ResourceLimitError exception"""

    def test_resource_limit_error_creation(self):
        """Test creating ResourceLimitError"""
        error = ResourceLimitError("Invalid timeout: must be positive")
        assert "timeout" in str(error).lower()

    def test_resource_limit_error_inheritance(self):
        """Test that ResourceLimitError inherits from Exception"""
        error = ResourceLimitError("Test error")
        assert isinstance(error, Exception)


@pytest.mark.unit
class TestPresetResourceProfiles:
    """Test preset resource profiles for common use cases"""

    def test_development_profile(self):
        """Test development profile (relaxed limits)"""
        limits = ResourceLimits.development()
        # Development should have generous limits
        assert limits.timeout_seconds >= 120  # At least 2 minutes
        assert limits.memory_limit_mb >= 1024  # At least 1GB

    def test_production_profile(self):
        """Test production profile (strict limits)"""
        limits = ResourceLimits.production()
        # Production should have conservative limits
        assert limits.timeout_seconds <= 60  # Max 1 minute
        assert limits.memory_limit_mb <= 512  # Max 512MB
        assert limits.network_mode == "allowlist" or limits.network_mode == "none"

    def test_testing_profile(self):
        """Test testing profile (minimal limits)"""
        limits = ResourceLimits.testing()
        # Testing should have tight limits for fast execution
        assert limits.timeout_seconds <= 30
        assert limits.memory_limit_mb <= 256

    def test_data_processing_profile(self):
        """Test data processing profile (high memory, more CPU)"""
        limits = ResourceLimits.data_processing()
        # Data processing needs more resources
        assert limits.memory_limit_mb >= 2048  # At least 2GB
        assert limits.cpu_quota >= 2.0  # At least 2 CPUs


@pytest.mark.unit
class TestResourceLimitsComparison:
    """Test resource limits comparison and validation"""

    def test_limits_equality(self):
        """Test that identical limits are equal"""
        limits1 = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        limits2 = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        assert limits1 == limits2

    def test_limits_inequality(self):
        """Test that different limits are not equal"""
        limits1 = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        limits2 = ResourceLimits(timeout_seconds=60, memory_limit_mb=512)
        assert limits1 != limits2

    def test_is_within_limits(self):
        """Test checking if one limit set is within another"""
        strict_limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=256)
        relaxed_limits = ResourceLimits(timeout_seconds=60, memory_limit_mb=512)

        # Strict should be within relaxed
        assert strict_limits.is_within(relaxed_limits) is True
        # Relaxed should not be within strict
        assert relaxed_limits.is_within(strict_limits) is False
