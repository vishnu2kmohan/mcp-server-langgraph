"""Tests for ExecutionMode enum.

TDD: These tests define the contract for the 5 execution modes
that determine how agents process tasks.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from enum import StrEnum

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_mode")
class TestExecutionModeEnum:
    """Tests for ExecutionMode enum existence and structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_mode_exists(self) -> None:
        """Test that ExecutionMode class exists."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert ExecutionMode is not None

    def test_execution_mode_is_str_enum(self) -> None:
        """Test ExecutionMode is a StrEnum for easy serialization."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert issubclass(ExecutionMode, StrEnum)

    def test_execution_mode_has_five_modes(self) -> None:
        """Test ExecutionMode has exactly 5 modes.

        The 5 execution modes:
        - PURE_LLM: No tools, direct response
        - TOOL_CALLING: Native function calling (single step)
        - REACT: Reasoning + Acting loop (multi-step exploration)
        - PROGRAMMATIC: Code-orchestrated batch processing
        - ORCHESTRATOR: Supervisor + workers (hierarchical)
        """
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        mode_values = list(ExecutionMode)
        assert len(mode_values) == 5

    def test_execution_mode_pure_llm(self) -> None:
        """Test PURE_LLM mode for direct LLM responses without tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert hasattr(ExecutionMode, "PURE_LLM")
        assert ExecutionMode.PURE_LLM.value == "pure_llm"

    def test_execution_mode_tool_calling(self) -> None:
        """Test TOOL_CALLING mode for native function calling."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert hasattr(ExecutionMode, "TOOL_CALLING")
        assert ExecutionMode.TOOL_CALLING.value == "tool_calling"

    def test_execution_mode_react(self) -> None:
        """Test REACT mode for multi-step reasoning + acting."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert hasattr(ExecutionMode, "REACT")
        assert ExecutionMode.REACT.value == "react"

    def test_execution_mode_programmatic(self) -> None:
        """Test PROGRAMMATIC mode for code-orchestrated batch processing."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert hasattr(ExecutionMode, "PROGRAMMATIC")
        assert ExecutionMode.PROGRAMMATIC.value == "programmatic"

    def test_execution_mode_orchestrator(self) -> None:
        """Test ORCHESTRATOR mode for supervisor + workers pattern."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert hasattr(ExecutionMode, "ORCHESTRATOR")
        assert ExecutionMode.ORCHESTRATOR.value == "orchestrator"


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_mode_default")
class TestExecutionModeDefault:
    """Tests for default execution mode behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_execution_mode_constant_exists(self) -> None:
        """Test DEFAULT_EXECUTION_MODE constant exists."""
        from mcp_server_langgraph.core.execution_modes import DEFAULT_EXECUTION_MODE

        assert DEFAULT_EXECUTION_MODE is not None

    def test_default_execution_mode_is_tool_calling(self) -> None:
        """Test default mode is TOOL_CALLING for backward compatibility."""
        from mcp_server_langgraph.core.execution_modes import (
            DEFAULT_EXECUTION_MODE,
            ExecutionMode,
        )

        assert DEFAULT_EXECUTION_MODE == ExecutionMode.TOOL_CALLING


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_mode_traits")
class TestExecutionModeTraits:
    """Tests for execution mode characteristics and traits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_requires_tools_function_exists(self) -> None:
        """Test requires_tools helper function exists."""
        from mcp_server_langgraph.core.execution_modes import requires_tools

        assert callable(requires_tools)

    def test_pure_llm_does_not_require_tools(self) -> None:
        """Test PURE_LLM mode does not require tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, requires_tools

        assert requires_tools(ExecutionMode.PURE_LLM) is False

    def test_tool_calling_requires_tools(self) -> None:
        """Test TOOL_CALLING mode requires tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, requires_tools

        assert requires_tools(ExecutionMode.TOOL_CALLING) is True

    def test_react_requires_tools(self) -> None:
        """Test REACT mode requires tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, requires_tools

        assert requires_tools(ExecutionMode.REACT) is True

    def test_programmatic_requires_tools(self) -> None:
        """Test PROGRAMMATIC mode requires tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, requires_tools

        assert requires_tools(ExecutionMode.PROGRAMMATIC) is True

    def test_orchestrator_requires_tools(self) -> None:
        """Test ORCHESTRATOR mode requires tools."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, requires_tools

        assert requires_tools(ExecutionMode.ORCHESTRATOR) is True

    def test_is_multi_step_function_exists(self) -> None:
        """Test is_multi_step helper function exists."""
        from mcp_server_langgraph.core.execution_modes import is_multi_step

        assert callable(is_multi_step)

    def test_pure_llm_is_not_multi_step(self) -> None:
        """Test PURE_LLM is a single-step mode."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, is_multi_step

        assert is_multi_step(ExecutionMode.PURE_LLM) is False

    def test_tool_calling_is_not_multi_step(self) -> None:
        """Test TOOL_CALLING is typically single-step."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, is_multi_step

        assert is_multi_step(ExecutionMode.TOOL_CALLING) is False

    def test_react_is_multi_step(self) -> None:
        """Test REACT is a multi-step mode (reasoning loop)."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, is_multi_step

        assert is_multi_step(ExecutionMode.REACT) is True

    def test_programmatic_is_multi_step(self) -> None:
        """Test PROGRAMMATIC is multi-step (batch processing)."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, is_multi_step

        assert is_multi_step(ExecutionMode.PROGRAMMATIC) is True

    def test_orchestrator_is_multi_step(self) -> None:
        """Test ORCHESTRATOR is multi-step (supervisor pattern)."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode, is_multi_step

        assert is_multi_step(ExecutionMode.ORCHESTRATOR) is True


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_mode_serialization")
class TestExecutionModeSerialization:
    """Tests for ExecutionMode serialization behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mode_from_string(self) -> None:
        """Test creating ExecutionMode from string value."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        # StrEnum allows direct comparison with strings
        assert ExecutionMode("tool_calling") == ExecutionMode.TOOL_CALLING
        assert ExecutionMode("react") == ExecutionMode.REACT

    def test_mode_string_value(self) -> None:
        """Test ExecutionMode string value for serialization."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        # StrEnum values should be usable as strings
        mode = ExecutionMode.REACT
        assert str(mode) == "react"
        assert mode == "react"

    def test_mode_in_json_dict(self) -> None:
        """Test ExecutionMode works in JSON-serializable dicts."""
        import json

        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        data = {"mode": ExecutionMode.TOOL_CALLING}
        # StrEnum should serialize naturally
        json_str = json.dumps(data)
        assert "tool_calling" in json_str
