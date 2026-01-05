"""Execution Mode enum for ADR-0092.

Defines the 5 execution modes that determine how agents process tasks.
Each mode represents a different execution strategy with specific
characteristics for tool usage and multi-step processing.

Usage:
    from mcp_server_langgraph.core.execution_modes import (
        ExecutionMode,
        DEFAULT_EXECUTION_MODE,
        requires_tools,
        is_multi_step,
    )

    # Check if mode needs tools
    if requires_tools(ExecutionMode.REACT):
        # Bind tools to agent
        ...

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from enum import StrEnum


class ExecutionMode(StrEnum):
    """5 execution modes for agent task processing.

    Modes from simplest to most complex:
    - PURE_LLM: No tools, direct LLM response (fastest, simplest)
    - TOOL_CALLING: Native function calling (single-step tool use)
    - REACT: Reasoning + Acting loop (multi-step exploration)
    - PROGRAMMATIC: Code-orchestrated batch processing
    - ORCHESTRATOR: Supervisor + workers (hierarchical delegation)

    The execution mode determines how the agent processes tasks:
    - Whether tools are bound to the LLM
    - Whether multi-step iteration is used
    - The overall execution pattern (single-shot vs loop vs delegation)
    """

    PURE_LLM = "pure_llm"
    TOOL_CALLING = "tool_calling"
    REACT = "react"
    PROGRAMMATIC = "programmatic"
    ORCHESTRATOR = "orchestrator"


# Default execution mode for backward compatibility
# TOOL_CALLING is the default because it matches current behavior
DEFAULT_EXECUTION_MODE: ExecutionMode = ExecutionMode.TOOL_CALLING


# Mode traits lookup tables
_REQUIRES_TOOLS: dict[ExecutionMode, bool] = {
    ExecutionMode.PURE_LLM: False,  # No tools needed
    ExecutionMode.TOOL_CALLING: True,  # Native function calling
    ExecutionMode.REACT: True,  # Tools for acting step
    ExecutionMode.PROGRAMMATIC: True,  # Code execution tools
    ExecutionMode.ORCHESTRATOR: True,  # Worker delegation tools
}

_IS_MULTI_STEP: dict[ExecutionMode, bool] = {
    ExecutionMode.PURE_LLM: False,  # Single LLM call
    ExecutionMode.TOOL_CALLING: False,  # Single tool invocation
    ExecutionMode.REACT: True,  # Reasoning loop
    ExecutionMode.PROGRAMMATIC: True,  # Batch iteration
    ExecutionMode.ORCHESTRATOR: True,  # Worker coordination
}


def requires_tools(mode: ExecutionMode) -> bool:
    """Check if an execution mode requires tools to be bound.

    Args:
        mode: The ExecutionMode to check

    Returns:
        True if the mode requires tools, False otherwise.

    Example:
        >>> requires_tools(ExecutionMode.PURE_LLM)
        False
        >>> requires_tools(ExecutionMode.TOOL_CALLING)
        True
    """
    return _REQUIRES_TOOLS[mode]


def is_multi_step(mode: ExecutionMode) -> bool:
    """Check if an execution mode uses multi-step processing.

    Multi-step modes iterate through reasoning/acting cycles or
    coordinate multiple workers, rather than single-shot execution.

    Args:
        mode: The ExecutionMode to check

    Returns:
        True if the mode is multi-step, False otherwise.

    Example:
        >>> is_multi_step(ExecutionMode.TOOL_CALLING)
        False
        >>> is_multi_step(ExecutionMode.REACT)
        True
    """
    return _IS_MULTI_STEP[mode]
