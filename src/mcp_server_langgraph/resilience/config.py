"""
Resilience configuration with environment variable support.

Centralized configuration for all resilience patterns:
- Circuit breaker thresholds and timeouts
- Retry policies and backoff strategies
- Timeout values per operation type
- Bulkhead concurrency limits
- Provider-aware concurrency limits

Provider rate limit references:
- Anthropic: https://docs.anthropic.com/en/api/rate-limits (Tier 1: 50 RPM → ~8 concurrent)
- OpenAI: https://platform.openai.com/docs/guides/rate-limits (~500 RPM → ~15 concurrent)
- Google Vertex AI: https://cloud.google.com/vertex-ai/generative-ai/docs/quotas (DSQ, ~5000 RPM)
- AWS Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html (Claude Opus: 50 RPM)
"""

import os
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Provider-Specific Concurrency Limits
# =============================================================================
# These limits are based on typical rate limits and assume ~5-10s average LLM latency.
# Formula: concurrent_limit ≈ (requests_per_minute / 60) * avg_latency_seconds
#
# Example: Anthropic Tier 1 = 50 RPM, 10s latency → (50/60) * 10 ≈ 8 concurrent

PROVIDER_CONCURRENCY_LIMITS: dict[str, int] = {
    # Anthropic Claude (direct API): Conservative Tier 1 (50 RPM)
    # Higher tiers (Tier 4: 4000 RPM) can override via env var
    "anthropic": 8,
    # OpenAI GPT-4: Moderate tier (~500 RPM typical)
    "openai": 15,
    # Google Gemini via AI Studio or direct API
    # Gemini 2.5 Flash: 5000 RPM per region (very generous)
    "google": 15,
    # Google Vertex AI (Gemini models): Higher limits for vishnu-sandbox-20250310
    # Gemini 2.5 Flash/Pro: 3.4M TPM → ~1400 RPM (2500 tokens/req)
    # Conservative: 15 concurrent (assumes 1s avg latency)
    "vertex_ai": 15,
    # Anthropic Claude via Vertex AI (MaaS) - vishnu-sandbox-20250310:
    # Claude Opus 4.5: 12M TPM, Sonnet 4.5: 3M TPM, Haiku 4.5: 10M TPM
    # Lowest is Sonnet 4.5: 3M TPM → ~1200 RPM (2500 tokens/req)
    # With ~3s avg latency: 20 req/sec * 3s = 60 concurrent possible
    # Conservative: 15 concurrent (balanced across all 4.5 models)
    "vertex_ai_anthropic": 15,
    # AWS Bedrock: Claude Opus is most restrictive (50 RPM)
    # Sonnet has higher limits (500 RPM) but we use conservative default
    "bedrock": 8,
    # Ollama: Local model, no upstream rate limits
    # Limited only by local hardware resources
    "ollama": 50,
    # Azure OpenAI: Similar to OpenAI, but deployment-specific
    "azure": 15,
}

# Default limit for unknown providers
DEFAULT_PROVIDER_LIMIT = 10


def get_provider_limit(provider: str) -> int:
    """
    Get the concurrency limit for a specific provider.

    Checks environment variables first (e.g., BULKHEAD_ANTHROPIC_LIMIT=5),
    then falls back to the default for that provider.

    Args:
        provider: Provider name (e.g., "anthropic", "openai", "vertex_ai")

    Returns:
        Concurrency limit for the provider
    """
    # Check for environment variable override
    env_var = f"BULKHEAD_{provider.upper()}_LIMIT"
    env_value = os.getenv(env_var)

    if env_value is not None:
        try:
            return int(env_value)
        except ValueError:
            # Invalid value, log and use default
            import logging

            logging.warning(
                f"Invalid {env_var}={env_value}, using default for {provider}",
                extra={"env_var": env_var, "invalid_value": env_value},
            )

    # Use provider-specific limit or default
    return PROVIDER_CONCURRENCY_LIMITS.get(provider, DEFAULT_PROVIDER_LIMIT)


class JitterStrategy(str, Enum):
    """Jitter strategies for retry backoff.

    See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """

    SIMPLE = "simple"  # +/- 20% of base delay (current implicit behavior)
    FULL = "full"  # random(0, delay) - high variance, good for many clients
    DECORRELATED = "decorrelated"  # min(max, random(base, prev*3)) - best for overload


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for a service"""

    name: str = Field(description="Service name")
    fail_max: int = Field(default=5, description="Max failures before opening")
    timeout_duration: int = Field(default=60, description="Seconds to stay open")
    expected_exception: type = Field(default=Exception, description="Exception type to track")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OverloadRetryConfig(BaseModel):
    """Configuration specific to overload/529 error handling.

    These settings provide more aggressive retry behavior for overload errors,
    which typically require longer wait times and more attempts to recover.
    """

    max_attempts: int = Field(default=6, description="Max attempts for overload errors")
    exponential_base: float = Field(default=2.0, description="Backoff base for overload")
    exponential_max: float = Field(default=60.0, description="Max backoff for overload (seconds)")
    initial_delay: float = Field(default=5.0, description="Initial delay for overload (seconds)")
    jitter_strategy: JitterStrategy = Field(
        default=JitterStrategy.DECORRELATED,
        description="Jitter strategy for overload retries",
    )
    honor_retry_after: bool = Field(default=True, description="Honor Retry-After header")
    retry_after_max: float = Field(default=120.0, description="Max Retry-After to honor (seconds)")


class RetryConfig(BaseModel):
    """Retry configuration"""

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    exponential_base: float = Field(default=2.0, description="Exponential backoff base")
    exponential_max: float = Field(default=10.0, description="Maximum backoff in seconds")
    jitter: bool = Field(default=True, description="Add random jitter to backoff")
    jitter_strategy: JitterStrategy = Field(
        default=JitterStrategy.SIMPLE,
        description="Jitter strategy for standard retries",
    )
    overload: OverloadRetryConfig = Field(
        default_factory=OverloadRetryConfig,
        description="Configuration for overload (529) error handling",
    )


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
    circuit_breakers: dict[str, CircuitBreakerConfig] = Field(
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
        # Parse jitter strategy from env
        jitter_strategy_str = os.getenv("RETRY_JITTER_STRATEGY", "simple").lower()
        jitter_strategy = (
            JitterStrategy(jitter_strategy_str)
            if jitter_strategy_str in [s.value for s in JitterStrategy]
            else JitterStrategy.SIMPLE
        )

        # Parse overload jitter strategy from env
        overload_jitter_str = os.getenv("RETRY_OVERLOAD_JITTER_STRATEGY", "decorrelated").lower()
        overload_jitter_strategy = (
            JitterStrategy(overload_jitter_str)
            if overload_jitter_str in [s.value for s in JitterStrategy]
            else JitterStrategy.DECORRELATED
        )

        return cls(
            enabled=os.getenv("RESILIENCE_ENABLED", "true").lower() == "true",
            retry=RetryConfig(
                max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
                exponential_base=float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0")),
                exponential_max=float(os.getenv("RETRY_EXPONENTIAL_MAX", "10.0")),
                jitter=os.getenv("RETRY_JITTER", "true").lower() == "true",
                jitter_strategy=jitter_strategy,
                overload=OverloadRetryConfig(
                    max_attempts=int(os.getenv("RETRY_OVERLOAD_MAX_ATTEMPTS", "6")),
                    exponential_base=float(os.getenv("RETRY_OVERLOAD_EXPONENTIAL_BASE", "2.0")),
                    exponential_max=float(os.getenv("RETRY_OVERLOAD_EXPONENTIAL_MAX", "60.0")),
                    initial_delay=float(os.getenv("RETRY_OVERLOAD_INITIAL_DELAY", "5.0")),
                    jitter_strategy=overload_jitter_strategy,
                    honor_retry_after=os.getenv("RETRY_OVERLOAD_HONOR_RETRY_AFTER", "true").lower() == "true",
                    retry_after_max=float(os.getenv("RETRY_OVERLOAD_RETRY_AFTER_MAX", "120.0")),
                ),
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
_resilience_config: ResilienceConfig | None = None


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
