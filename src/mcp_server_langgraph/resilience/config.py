"""
Resilience configuration with environment variable support.

Centralized configuration for all resilience patterns:
- Circuit breaker thresholds and timeouts
- Retry policies and backoff strategies
- Timeout values per operation type
- Bulkhead concurrency limits
"""

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for a service"""

    name: str = Field(description="Service name")
    fail_max: int = Field(default=5, description="Max failures before opening")
    timeout_duration: int = Field(default=60, description="Seconds to stay open")
    expected_exception: type = Field(default=Exception, description="Exception type to track")

    class Config:
        arbitrary_types_allowed = True


class RetryConfig(BaseModel):
    """Retry configuration"""

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    exponential_base: float = Field(default=2.0, description="Exponential backoff base")
    exponential_max: float = Field(default=10.0, description="Maximum backoff in seconds")
    jitter: bool = Field(default=True, description="Add random jitter to backoff")


class TimeoutConfig(BaseModel):
    """Timeout configuration per operation type"""

    default: int = Field(default=30, description="Default timeout in seconds")
    llm: int = Field(default=60, description="LLM operation timeout")
    auth: int = Field(default=5, description="Auth operation timeout")
    db: int = Field(default=10, description="Database operation timeout")
    http: int = Field(default=15, description="HTTP request timeout")


class BulkheadConfig(BaseModel):
    """Bulkhead configuration per resource type"""

    llm_limit: int = Field(default=10, description="Max concurrent LLM calls")
    openfga_limit: int = Field(default=50, description="Max concurrent OpenFGA checks")
    redis_limit: int = Field(default=100, description="Max concurrent Redis operations")
    db_limit: int = Field(default=20, description="Max concurrent DB queries")


class ResilienceConfig(BaseModel):
    """Master resilience configuration"""

    enabled: bool = Field(default=True, description="Enable resilience patterns")

    # Circuit breaker configs per service
    circuit_breakers: Dict[str, CircuitBreakerConfig] = Field(
        default_factory=lambda: {
            "llm": CircuitBreakerConfig(name="llm", fail_max=5, timeout_duration=60),
            "openfga": CircuitBreakerConfig(name="openfga", fail_max=10, timeout_duration=30),
            "redis": CircuitBreakerConfig(name="redis", fail_max=5, timeout_duration=30),
            "keycloak": CircuitBreakerConfig(name="keycloak", fail_max=5, timeout_duration=60),
            "prometheus": CircuitBreakerConfig(name="prometheus", fail_max=3, timeout_duration=30),
        }
    )

    # Retry configuration
    retry: RetryConfig = Field(default_factory=RetryConfig)

    # Timeout configuration
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)

    # Bulkhead configuration
    bulkhead: BulkheadConfig = Field(default_factory=BulkheadConfig)

    @classmethod
    def from_env(cls) -> "ResilienceConfig":
        """Load configuration from environment variables"""
        return cls(
            enabled=os.getenv("RESILIENCE_ENABLED", "true").lower() == "true",
            retry=RetryConfig(
                max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
                exponential_base=float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0")),
                exponential_max=float(os.getenv("RETRY_EXPONENTIAL_MAX", "10.0")),
                jitter=os.getenv("RETRY_JITTER", "true").lower() == "true",
            ),
            timeout=TimeoutConfig(
                default=int(os.getenv("TIMEOUT_DEFAULT", "30")),
                llm=int(os.getenv("TIMEOUT_LLM", "60")),
                auth=int(os.getenv("TIMEOUT_AUTH", "5")),
                db=int(os.getenv("TIMEOUT_DB", "10")),
                http=int(os.getenv("TIMEOUT_HTTP", "15")),
            ),
            bulkhead=BulkheadConfig(
                llm_limit=int(os.getenv("BULKHEAD_LLM_LIMIT", "10")),
                openfga_limit=int(os.getenv("BULKHEAD_OPENFGA_LIMIT", "50")),
                redis_limit=int(os.getenv("BULKHEAD_REDIS_LIMIT", "100")),
                db_limit=int(os.getenv("BULKHEAD_DB_LIMIT", "20")),
            ),
        )


# Global config instance
_resilience_config: Optional[ResilienceConfig] = None


def get_resilience_config() -> ResilienceConfig:
    """Get global resilience configuration (singleton)"""
    global _resilience_config
    if _resilience_config is None:
        _resilience_config = ResilienceConfig.from_env()
    return _resilience_config


def set_resilience_config(config: ResilienceConfig) -> None:
    """Set global resilience configuration (for testing)"""
    global _resilience_config
    _resilience_config = config
