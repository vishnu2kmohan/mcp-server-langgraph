"""Tool Executor with Fallback Chain and Circuit Breaker (v7).

Provides unified tool execution with:
- Automatic fallback from native to builtin tools
- Circuit breaker pattern for native tool resilience
- Metrics recording for observability

Usage:
    from mcp_server_langgraph.core.tool_executor import (
        execute_tool_with_fallback,
        get_circuit_breaker,
    )

    result, source = await execute_tool_with_fallback(
        tool_name="web_search",
        tool_args={"query": "AI news"},
        tool_preference="auto",
        model_name="claude-sonnet-4-20250514",
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.tools import get_tool_by_name
from mcp_server_langgraph.tools.native_handler import (
    NATIVE_TO_BUILTIN_MAP,
    NativeToolHandler,
    get_fallback_chain,
)
from mcp_server_langgraph.tools.native_metrics import (
    record_builtin_tool_execution,
)


# =============================================================================
# Circuit Breaker
# =============================================================================


@dataclass
class ProviderCircuitState:
    """State for a single provider's circuit breaker."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False


class NativeToolCircuitBreaker:
    """Circuit breaker for native tool providers.

    Prevents cascading failures by temporarily disabling native tools
    when a provider experiences consecutive failures.

    States:
    - CLOSED: Normal operation, native tools enabled
    - OPEN: Native tools disabled, using builtins directly
    - HALF-OPEN: Allowing single retry after timeout

    Attributes:
        failure_threshold: Number of failures before opening circuit
        reset_timeout_seconds: Time to wait before allowing retry
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 60.0,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            reset_timeout_seconds: Seconds before half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self._lock = Lock()
        self._states: dict[str, ProviderCircuitState] = {}

    def _get_state(self, provider: str) -> ProviderCircuitState:
        """Get or create state for a provider."""
        if provider not in self._states:
            self._states[provider] = ProviderCircuitState()
        return self._states[provider]

    def is_open(self, provider: str) -> bool:
        """Check if circuit is open for a provider.

        Returns False if:
        - Circuit is closed (normal operation)
        - Circuit is half-open (timeout expired, allow retry)

        Returns True if:
        - Circuit is open and timeout hasn't expired

        Args:
            provider: Provider name (e.g., "anthropic", "google")

        Returns:
            True if circuit is open (native tools disabled)
        """
        with self._lock:
            state = self._get_state(provider)

            if not state.is_open:
                return False

            # Check if timeout has expired (half-open)
            if time.time() - state.last_failure_time > self.reset_timeout_seconds:
                # Allow retry (half-open state)
                return False

            return True

    def record_failure(self, provider: str) -> None:
        """Record a failure for a provider.

        Opens circuit if failure threshold is reached.

        Args:
            provider: Provider name
        """
        from mcp_server_langgraph.tools.native_metrics import (
            record_circuit_breaker_state,
            record_circuit_breaker_state_change,
        )

        with self._lock:
            state = self._get_state(provider)
            was_open = state.is_open
            state.failure_count += 1
            state.last_failure_time = time.time()

            if state.failure_count >= self.failure_threshold:
                state.is_open = True
                logger.warning(
                    f"Circuit breaker OPEN for provider '{provider}' after {state.failure_count} failures",
                    extra={
                        "provider": provider,
                        "failure_count": state.failure_count,
                    },
                )
                # Record state change metrics
                if not was_open:
                    record_circuit_breaker_state_change(provider, "closed", "open")
                record_circuit_breaker_state(provider, "open")

    def record_success(self, provider: str) -> None:
        """Record a success for a provider.

        Resets failure count and closes circuit.

        Args:
            provider: Provider name
        """
        from mcp_server_langgraph.tools.native_metrics import (
            record_circuit_breaker_state,
            record_circuit_breaker_state_change,
        )

        with self._lock:
            state = self._get_state(provider)
            was_open = state.is_open
            if state.is_open:
                logger.info(
                    f"Circuit breaker CLOSED for provider '{provider}' after success",
                    extra={"provider": provider},
                )
            state.failure_count = 0
            state.is_open = False

            # Record state change metrics
            if was_open:
                record_circuit_breaker_state_change(provider, "open", "closed")
            record_circuit_breaker_state(provider, "closed")

    def reset(self, provider: str | None = None) -> None:
        """Reset circuit breaker state.

        Args:
            provider: Provider to reset, or None to reset all
        """
        with self._lock:
            if provider is None:
                self._states.clear()
            elif provider in self._states:
                del self._states[provider]


# Global circuit breaker instance
_circuit_breaker: NativeToolCircuitBreaker | None = None


def get_circuit_breaker() -> NativeToolCircuitBreaker:
    """Get the global circuit breaker instance with configurable settings.

    Uses Settings for (operational configuration, not feature toggles):
    - native_tool_circuit_breaker_threshold: Failures before opening
    - native_tool_circuit_breaker_reset_seconds: Timeout before retry
    """
    global _circuit_breaker
    if _circuit_breaker is None:
        from mcp_server_langgraph.core.config import settings

        _circuit_breaker = NativeToolCircuitBreaker(
            failure_threshold=settings.native_tool_circuit_breaker_threshold,
            reset_timeout_seconds=float(settings.native_tool_circuit_breaker_reset_seconds),
        )
    return _circuit_breaker


def reset_circuit_breaker() -> None:
    """Reset the global circuit breaker (for testing)."""
    global _circuit_breaker
    _circuit_breaker = None


def get_native_tool_rate_limit(provider: str) -> int:
    """Get rate limit for a native tool provider.

    Args:
        provider: Provider name ("anthropic", "google", "openai")

    Returns:
        Rate limit in requests per minute
    """
    from mcp_server_langgraph.core.config import settings

    provider_lower = provider.lower()
    if provider_lower == "anthropic":
        return settings.native_tool_rate_limit_anthropic
    elif provider_lower == "google":
        return settings.native_tool_rate_limit_google
    elif provider_lower == "openai":
        return settings.native_tool_rate_limit_openai
    else:
        # Default to 60 rpm for unknown providers
        return 60


def get_native_tool_timeout() -> int:
    """Get timeout for native tool execution.

    Returns:
        Timeout in seconds
    """
    from mcp_server_langgraph.core.config import settings

    return settings.native_tool_timeout_seconds


# =============================================================================
# Tool Execution with Fallback
# =============================================================================


def _should_use_native(
    tool_name: str,
    tool_preference: str,
    model_name: str,
) -> bool:
    """Check if native tool should be used.

    Considers:
    - User preference
    - Model capabilities
    - Feature flags
    - Circuit breaker state

    Args:
        tool_name: Name of the tool
        tool_preference: User preference (auto/native/builtin/mcp)
        model_name: Model being used

    Returns:
        True if native tool should be attempted
    """
    # "builtin" or "mcp" preference forces non-native
    if tool_preference in ("builtin", "mcp"):
        return False

    # Check model capability
    handler = NativeToolHandler(model_name)
    if not handler.should_use_native(tool_name, tool_preference):
        return False

    # Check circuit breaker
    provider = handler.caps.native_provider
    if provider and get_circuit_breaker().is_open(provider):
        logger.warning(
            f"Circuit open for '{provider}', skipping native tool '{tool_name}'",
            extra={"tool_name": tool_name, "provider": provider},
        )
        return False

    return True


def _get_native_executor(
    tool_name: str,
    model_name: str,
) -> Callable[..., Any] | None:
    """Get native tool executor for a tool.

    NOTE: This is a placeholder. In actual implementation, this would
    return the provider-specific executor from the model's bound tools.

    Args:
        tool_name: Name of the tool
        model_name: Model being used

    Returns:
        Async callable for native execution, or None
    """
    # In real implementation, this would get the native executor
    # from the bound model. For now, return None to use builtin.
    return None


async def execute_tool_with_fallback(
    tool_name: str,
    tool_args: dict[str, Any],
    tool_preference: str,
    model_name: str,
) -> tuple[str, str]:
    """Execute a tool with automatic fallback support.

    Attempts native execution first (if applicable), falling back
    to builtin on failure. Records metrics and respects circuit breaker.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments to pass to the tool
        tool_preference: User preference (auto/native/builtin/mcp)
        model_name: Model being used

    Returns:
        Tuple of (result_content, execution_source)
        execution_source is "native", "builtin", or "error"
    """
    # Get builtin tool
    builtin_tool = get_tool_by_name(tool_name)

    # Also check for mapped builtin name
    if builtin_tool is None:
        mapped_name = NATIVE_TO_BUILTIN_MAP.get(tool_name)
        if mapped_name and mapped_name != tool_name:
            builtin_tool = get_tool_by_name(mapped_name)

    if builtin_tool is None:
        logger.error(f"Tool '{tool_name}' not found")
        return f"Error: Tool '{tool_name}' not found", "error"

    # Check if we should use native
    if _should_use_native(tool_name, tool_preference, model_name):
        native_executor = _get_native_executor(tool_name, model_name)

        if native_executor is not None:
            # Use fallback chain for native execution
            handler = NativeToolHandler(model_name)
            provider = handler.caps.native_provider or "unknown"
            fallback_chain = get_fallback_chain()

            async def builtin_executor(args: dict[str, Any]) -> Any:
                if hasattr(builtin_tool, "ainvoke"):
                    return await builtin_tool.ainvoke(args)
                return builtin_tool.invoke(args)

            try:
                result, source = await fallback_chain.execute_with_fallback(
                    tool_name=tool_name,
                    args=tool_args,
                    native_executor=native_executor,
                    builtin_executor=builtin_executor,
                    provider=provider,
                )

                # Update circuit breaker based on result
                if source == "native":
                    get_circuit_breaker().record_success(provider)
                elif source == "builtin":
                    # Fallback happened, failure already recorded in chain
                    get_circuit_breaker().record_failure(provider)

                return result, source

            except Exception as e:
                logger.error(
                    f"Tool execution failed completely: {tool_name}",
                    exc_info=True,
                )
                return f"Error executing tool '{tool_name}': {e!s}", "error"

    # Execute builtin directly
    try:
        start_time = time.perf_counter()
        if hasattr(builtin_tool, "ainvoke"):
            result = await builtin_tool.ainvoke(tool_args)
        else:
            result = builtin_tool.invoke(tool_args)
        duration_ms = (time.perf_counter() - start_time) * 1000

        record_builtin_tool_execution(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=True,
        )

        logger.info(
            f"Builtin tool '{tool_name}' executed successfully",
            extra={
                "tool_name": tool_name,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return str(result), "builtin"

    except Exception as e:
        record_builtin_tool_execution(
            tool_name=tool_name,
            duration_ms=0.0,
            success=False,
        )
        logger.error(f"Builtin tool '{tool_name}' failed: {e}", exc_info=True)
        return f"Error executing tool '{tool_name}': {e!s}", "error"
