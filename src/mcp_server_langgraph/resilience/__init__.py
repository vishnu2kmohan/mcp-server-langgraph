"""
Resilience patterns for production-ready MCP server.

This module provides production-grade resilience patterns:
- Circuit Breaker: Prevent cascade failures
- Retry Logic: Exponential backoff with jitter
- Timeout Enforcement: Prevent hanging requests
- Bulkhead Isolation: Resource pool limits
- Fallback Strategies: Graceful degradation

See ADR-0026 for full rationale and design decisions.
"""

from mcp_server_langgraph.resilience.bulkhead import BulkheadConfig, get_bulkhead, with_bulkhead
from mcp_server_langgraph.resilience.circuit_breaker import (
    CircuitBreakerState,
    circuit_breaker,
    get_circuit_breaker,
    get_circuit_breaker_state,
    reset_circuit_breaker,
)
from mcp_server_langgraph.resilience.config import ResilienceConfig, get_resilience_config
from mcp_server_langgraph.resilience.fallback import (
    FallbackStrategy,
    fail_closed,
    fail_open,
    return_empty_on_error,
    with_fallback,
)
from mcp_server_langgraph.resilience.retry import RetryPolicy, RetryStrategy, retry_with_backoff
from mcp_server_langgraph.resilience.timeout import TimeoutConfig, with_timeout


__all__ = [
    # Circuit Breaker
    "circuit_breaker",
    "CircuitBreakerState",
    "get_circuit_breaker",
    "get_circuit_breaker_state",
    "reset_circuit_breaker",
    # Retry
    "retry_with_backoff",
    "RetryPolicy",
    "RetryStrategy",
    # Timeout
    "with_timeout",
    "TimeoutConfig",
    # Bulkhead
    "with_bulkhead",
    "BulkheadConfig",
    "get_bulkhead",
    # Fallback
    "with_fallback",
    "fail_open",
    "fail_closed",
    "return_empty_on_error",
    "FallbackStrategy",
    # Config
    "ResilienceConfig",
    "get_resilience_config",
]
