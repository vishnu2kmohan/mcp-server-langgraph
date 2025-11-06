"""
Resource limits configuration for code execution

Defines CPU, memory, timeout, and network constraints for sandboxed execution.
Immutable configuration with validation and preset profiles.
"""

from dataclasses import dataclass, field
from typing import Literal


class ResourceLimitError(Exception):
    """Raised when resource limit validation fails"""

    pass


NetworkMode = Literal["none", "allowlist", "unrestricted"]


@dataclass(frozen=True)
class ResourceLimits:
    """
    Resource limits for sandboxed code execution.

    Immutable configuration ensuring consistent resource constraints.
    All limits are validated on creation to prevent invalid configurations.

    Example:
        >>> limits = ResourceLimits(timeout_seconds=30, memory_limit_mb=512)
        >>> assert limits.timeout_seconds == 30

    Attributes:
        timeout_seconds: Maximum execution time (1-600 seconds, default: 30)
        memory_limit_mb: Maximum memory usage in MB (64-8192 MB, default: 512)
        cpu_quota: CPU cores quota (0.1-8.0, default: 1.0)
        disk_quota_mb: Maximum disk usage in MB (1-10240 MB, default: 100)
        max_processes: Maximum number of processes (1-100, default: 1)
        network_mode: Network access mode (none/allowlist/unrestricted, default: none)
        allowed_domains: Domains allowed in 'allowlist' mode (default: empty)
    """

    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_quota: float = 1.0
    disk_quota_mb: int = 100
    max_processes: int = 1
    network_mode: NetworkMode = "none"
    allowed_domains: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate resource limits after initialization"""
        self._validate_timeout()
        self._validate_memory()
        self._validate_cpu()
        self._validate_disk()
        self._validate_processes()
        self._validate_network()

    def _validate_timeout(self) -> None:
        """Validate timeout constraints"""
        if self.timeout_seconds <= 0:
            raise ResourceLimitError(f"Timeout must be positive, got {self.timeout_seconds}")

        if self.timeout_seconds > 600:  # 10 minutes max
            raise ResourceLimitError(f"Timeout cannot exceed 600 seconds, got {self.timeout_seconds}")

    def _validate_memory(self) -> None:
        """Validate memory constraints"""
        if self.memory_limit_mb <= 0:
            raise ResourceLimitError(f"Memory limit must be positive, got {self.memory_limit_mb}")

        if self.memory_limit_mb < 64:
            raise ResourceLimitError(f"Memory limit cannot be less than 64MB, got {self.memory_limit_mb}")

        if self.memory_limit_mb > 16384:  # 16GB max
            raise ResourceLimitError(f"Memory limit cannot exceed 16GB (16384MB), got {self.memory_limit_mb}")

    def _validate_cpu(self) -> None:
        """Validate CPU quota constraints"""
        if self.cpu_quota <= 0:
            raise ResourceLimitError(f"CPU quota must be positive, got {self.cpu_quota}")

        if self.cpu_quota > 8.0:
            raise ResourceLimitError(f"CPU quota cannot exceed 8.0 cores, got {self.cpu_quota}")

    def _validate_disk(self) -> None:
        """Validate disk quota constraints"""
        if self.disk_quota_mb <= 0:
            raise ResourceLimitError(f"Disk quota must be positive, got {self.disk_quota_mb}")

        if self.disk_quota_mb > 10240:  # 10GB max
            raise ResourceLimitError(f"Disk quota cannot exceed 10GB (10240MB), got {self.disk_quota_mb}")

    def _validate_processes(self) -> None:
        """Validate max processes constraints"""
        if self.max_processes <= 0:
            raise ResourceLimitError(f"Max processes must be positive, got {self.max_processes}")

        if self.max_processes > 100:
            raise ResourceLimitError(f"Max processes cannot exceed 100, got {self.max_processes}")

    def _validate_network(self) -> None:
        """Validate network configuration"""
        valid_modes: tuple[NetworkMode, ...] = ("none", "allowlist", "unrestricted")
        if self.network_mode not in valid_modes:
            raise ResourceLimitError(f"Network mode must be one of {valid_modes}, got '{self.network_mode}'")

        # Note: allowlist with empty domains is allowed (effectively blocks all network)
        # This allows configuring the profile first, then adding domains later

    def to_dict(self) -> dict:
        """Convert resource limits to dictionary"""
        return {
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_quota": self.cpu_quota,
            "disk_quota_mb": self.disk_quota_mb,
            "max_processes": self.max_processes,
            "network_mode": self.network_mode,
            "allowed_domains": list(self.allowed_domains),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceLimits":
        """Create resource limits from dictionary"""
        # Convert allowed_domains list to tuple for immutability
        if "allowed_domains" in data and isinstance(data["allowed_domains"], list):
            data = {**data, "allowed_domains": tuple(data["allowed_domains"])}

        return cls(**data)

    def is_within(self, other: "ResourceLimits") -> bool:
        """
        Check if these limits are within (stricter than or equal to) another set of limits.

        Args:
            other: Resource limits to compare against

        Returns:
            True if all limits are within the other limits
        """
        return (
            self.timeout_seconds <= other.timeout_seconds
            and self.memory_limit_mb <= other.memory_limit_mb
            and self.cpu_quota <= other.cpu_quota
            and self.disk_quota_mb <= other.disk_quota_mb
            and self.max_processes <= other.max_processes
        )

    @classmethod
    def development(cls) -> "ResourceLimits":
        """
        Development profile with relaxed limits for local testing.

        Returns:
            ResourceLimits configured for development
        """
        return cls(
            timeout_seconds=300,  # 5 minutes
            memory_limit_mb=2048,  # 2GB
            cpu_quota=2.0,  # 2 CPUs
            disk_quota_mb=1024,  # 1GB
            max_processes=10,
            network_mode="unrestricted",  # Full network for development
            allowed_domains=tuple(),
        )

    @classmethod
    def production(cls) -> "ResourceLimits":
        """
        Production profile with conservative limits for security.

        Returns:
            ResourceLimits configured for production
        """
        return cls(
            timeout_seconds=30,  # 30 seconds
            memory_limit_mb=512,  # 512MB
            cpu_quota=1.0,  # 1 CPU
            disk_quota_mb=100,  # 100MB
            max_processes=1,
            network_mode="allowlist",
            allowed_domains=tuple(),  # Must be configured per deployment
        )

    @classmethod
    def testing(cls) -> "ResourceLimits":
        """
        Testing profile with minimal limits for fast execution.

        Returns:
            ResourceLimits configured for testing
        """
        return cls(
            timeout_seconds=10,  # 10 seconds
            memory_limit_mb=256,  # 256MB
            cpu_quota=0.5,  # 0.5 CPU
            disk_quota_mb=50,  # 50MB
            max_processes=1,
            network_mode="none",  # No network for tests
            allowed_domains=tuple(),
        )

    @classmethod
    def data_processing(cls) -> "ResourceLimits":
        """
        Data processing profile with higher memory and CPU for analytics.

        Returns:
            ResourceLimits configured for data processing
        """
        return cls(
            timeout_seconds=300,  # 5 minutes
            memory_limit_mb=4096,  # 4GB
            cpu_quota=4.0,  # 4 CPUs
            disk_quota_mb=512,  # 512MB
            max_processes=4,
            network_mode="allowlist",
            allowed_domains=tuple(),  # Configure per use case
        )
