"""
LiteLLM Atexit Handler Prevention (OpenAI Codex Finding 2025-11-17)

CRITICAL: This module must be imported/loaded BEFORE any litellm imports.
It monkey-patches litellm's atexit registration to prevent RuntimeWarnings.
"""

import atexit
import warnings

# Store original atexit.register
_original_atexit_register = atexit.register
_litellm_handlers = []


def _filtered_atexit_register(func, *args, **kwargs):
    """
    Intercept atexit.register calls and block litellm's cleanup_wrapper.

    This prevents litellm from registering an atexit handler that causes
    RuntimeWarning: coroutine 'close_litellm_async_clients' was never awaited
    """
    # Check if this is litellm's cleanup_wrapper
    if hasattr(func, "__name__") and func.__name__ == "cleanup_wrapper":
        # Check if it's from litellm module
        if hasattr(func, "__module__") and func.__module__ and "litellm" in func.__module__:
            # Store reference but don't register it
            _litellm_handlers.append((func, args, kwargs))
            return func  # Return func to maintain compatibility
        # Also check via closure variables (litellm uses nested functions)
        if hasattr(func, "__code__"):
            code_consts = str(func.__code__.co_consts)
            if "close_litellm_async_clients" in code_consts or "litellm" in code_consts:
                _litellm_handlers.append((func, args, kwargs))
                return func
    # For all other functions, use original atexit.register
    return _original_atexit_register(func, *args, **kwargs)


# Replace atexit.register before any litellm imports
atexit.register = _filtered_atexit_register

# Suppress litellm async cleanup warning (OpenAI Codex Finding 2025-11-15)
# Root cause: litellm's atexit handler calls loop.create_task() without awaiting
# Our pytest_sessionfinish hook already handles cleanup properly
# This must be set at import time to catch warnings during atexit phase
warnings.filterwarnings("ignore", category=RuntimeWarning, module="litellm.llms.custom_httpx.async_client_cleanup")
