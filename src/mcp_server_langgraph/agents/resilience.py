"""
Orchestrator Resilience Patterns

Phase 10 of the Multi-Agent Orchestrator Enhancement Plan.

Provides resilience wrappers for orchestrator and subagent execution:
- Circuit breaker for orchestrator failures
- Timeout enforcement on parallel execution
- Bulkhead for concurrent orchestrations
- Retry for transient subagent failures

Usage:
    from mcp_server_langgraph.agents.resilience import (
        resilient_orchestrate,
        resilient_subagent_execute,
    )

    results = await resilient_orchestrate(orchestrator, decomposition)
    result = await resilient_subagent_execute(subagent)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING, TypeVar

T = TypeVar("T")

import pybreaker

from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.resilience import (
    circuit_breaker,
    get_circuit_breaker,
    reset_circuit_breaker,
    retry_with_backoff,
    with_timeout,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
    from mcp_server_langgraph.agents.subagent import Subagent, SubagentResult


# Semaphore for bulkhead pattern (limits concurrent orchestrations)
_orchestrator_semaphore: asyncio.Semaphore | None = None


def get_orchestrator_semaphore() -> asyncio.Semaphore:
    """Get or create the orchestrator bulkhead semaphore.

    Returns:
        Semaphore limited to max concurrent orchestrations
    """
    global _orchestrator_semaphore
    if _orchestrator_semaphore is None:
        limit = feature_flags.orchestrator_max_concurrent
        _orchestrator_semaphore = asyncio.Semaphore(limit)
    return _orchestrator_semaphore


def reset_orchestrator_semaphore() -> None:
    """Reset the orchestrator semaphore (for testing)."""
    global _orchestrator_semaphore
    _orchestrator_semaphore = None


# Orchestrator circuit breaker name
ORCHESTRATOR_CIRCUIT_BREAKER_NAME = "orchestrator"


def get_orchestrator_circuit_breaker() -> pybreaker.CircuitBreaker:
    """Get or create the orchestrator circuit breaker.

    Uses the feature flag `orchestrator_circuit_breaker_threshold` for fail_max.

    Returns:
        CircuitBreaker instance for orchestrator
    """
    cb = get_circuit_breaker(ORCHESTRATOR_CIRCUIT_BREAKER_NAME)
    # Override fail_max from feature flag if different
    threshold = feature_flags.orchestrator_circuit_breaker_threshold
    if cb.fail_max != threshold:
        cb._fail_max = threshold
    return cb


def reset_orchestrator_circuit_breaker() -> None:
    """Reset the orchestrator circuit breaker to closed state (for testing)."""
    reset_circuit_breaker(ORCHESTRATOR_CIRCUIT_BREAKER_NAME)


async def resilient_orchestrate(
    orchestrator: Orchestrator,
    decomposition: TaskDecomposition,
) -> list[SubagentResult]:
    """Execute orchestration with full resilience protection.

    Applies the following resilience patterns when enabled:
    - Bulkhead: Limits concurrent orchestrations
    - Timeout: Enforces maximum execution time
    - Circuit Breaker: Fails fast on repeated failures

    Args:
        orchestrator: The Orchestrator instance
        decomposition: Task decomposition to execute

    Returns:
        List of SubagentResult from all subtasks

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
        CircuitBreakerOpenError: If circuit breaker is open
        Exception: If execution fails
    """
    from mcp_server_langgraph.agents.subagent import SubagentResult
    from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError

    if not feature_flags.enable_orchestrator_resilience:
        # Resilience disabled, execute directly
        return await orchestrator.execute(decomposition)

    timeout = feature_flags.orchestrator_timeout_seconds
    semaphore = get_orchestrator_semaphore()
    cb = get_orchestrator_circuit_breaker()

    # Check circuit breaker state before execution
    if cb.current_state == pybreaker.STATE_OPEN:
        raise CircuitBreakerOpenError(
            message="Orchestrator circuit breaker is open",
            metadata={"service": ORCHESTRATOR_CIRCUIT_BREAKER_NAME},
        )

    async def _execute_with_timeout() -> list[SubagentResult]:
        """Execute with timeout enforcement."""
        return await asyncio.wait_for(
            orchestrator.execute(decomposition),
            timeout=timeout,
        )

    # Apply bulkhead (concurrency limit) and circuit breaker
    async with semaphore:
        try:
            result = await _execute_with_timeout()
            # Success - reset failure counter by calling success handler
            with cb._lock:
                cb._state_storage.increment_counter()
                cb.state.on_success()
            return result
        except Exception as e:
            # Failure - increment failure counter
            with cb._lock:
                cb._inc_counter()
                try:
                    cb.state.on_failure(e)
                except pybreaker.CircuitBreakerError:
                    # Circuit just opened - re-raise the original exception
                    # The next call will see the circuit is open
                    pass
            raise


async def resilient_subagent_execute(
    subagent: Subagent,
    max_retries: int = 2,
) -> SubagentResult:
    """Execute subagent with retry protection.

    Applies retry logic for transient failures with exponential backoff.

    Args:
        subagent: The Subagent to execute
        max_retries: Maximum retry attempts (default 2)

    Returns:
        SubagentResult from execution

    Raises:
        Exception: If all retry attempts fail
    """
    from mcp_server_langgraph.agents.subagent import SubagentResult

    if not feature_flags.enable_orchestrator_resilience:
        # Resilience disabled, execute directly
        return await subagent.execute()

    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await subagent.execute()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # Exponential backoff: 1s, 2s
                delay = 2 ** attempt
                await asyncio.sleep(delay)
            else:
                # All retries exhausted
                break

    # Return failed result on all retries exhausted
    if last_exception is not None:
        return SubagentResult(
            task_id=subagent.task_id,
            success=False,
            error=f"All {max_retries + 1} attempts failed: {last_exception}",
        )

    # Should not reach here, but handle edge case
    return SubagentResult(
        task_id=subagent.task_id,
        success=False,
        error="Unknown error during resilient execution",
    )


async def execute_with_timeout(
    coro: Awaitable[T],
    timeout_seconds: int | None = None,
) -> T:
    """Execute a coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds (uses feature flag default if None)

    Returns:
        Result of the coroutine

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
    """
    if timeout_seconds is None:
        timeout_seconds = feature_flags.orchestrator_timeout_seconds

    return await asyncio.wait_for(coro, timeout=timeout_seconds)
