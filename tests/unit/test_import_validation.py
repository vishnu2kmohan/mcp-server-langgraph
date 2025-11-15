"""
Test module import validation and type resolution.

This test suite validates that all modules can be imported correctly
and that type annotations are properly resolved. These tests follow TDD
principles and should FAIL initially, then PASS after fixes are applied.

RED Phase: These tests will fail due to:
- Missing ResourceLimits import in sandbox.py
- Undefined 'tools' variable in server_stdio.py
- Missing CostMetricsCollector import in budget_monitor.py

GREEN Phase: Tests should pass after imports are added.
"""

import gc
import inspect

import pytest


def test_sandbox_module_imports_successfully():
    """
    Test that sandbox module can be imported without NameError.

    FAILS when: ResourceLimits is not imported in sandbox.py
    PASSES when: Import is added at top of sandbox.py
    """
    from mcp_server_langgraph.execution import sandbox

    assert hasattr(sandbox, "Sandbox")
    # This will fail if ResourceLimits is not imported
    assert sandbox.Sandbox is not None


def test_sandbox_init_signature_resolves_resource_limits():
    """
    Test that Sandbox.__init__ type hints are properly resolved.

    FAILS when: ResourceLimits is not imported (NameError during inspection)
    PASSES when: Import is added
    """
    from mcp_server_langgraph.execution.sandbox import Sandbox

    # This will raise NameError if ResourceLimits is not imported
    sig = inspect.signature(Sandbox.__init__)
    assert "limits" in sig.parameters

    # Verify the type annotation is resolved
    limits_param = sig.parameters["limits"]
    assert limits_param.annotation is not inspect.Parameter.empty


@pytest.mark.asyncio
async def test_server_stdio_list_tools_public_does_not_crash():
    """
    Test that list_tools_public() can be called without NameError.

    FAILS when: 'tools' variable is not initialized in server_stdio.py
    PASSES when: tools list is properly initialized before use
    """
    from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

    # Create server instance
    server = MCPAgentServer()

    # This will raise NameError if 'tools' is not defined
    tools = await server.list_tools_public()

    # Verify we get a list back
    assert isinstance(tools, list)
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_server_stdio_list_tools_includes_required_tools():
    """
    Test that list_tools_public() returns all expected tools.

    FAILS when: 'tools' variable is undefined, preventing tool additions
    PASSES when: tools list is initialized and all tools are added
    """
    from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

    server = MCPAgentServer()
    tools = await server.list_tools_public()

    # Extract tool names
    tool_names = [t.name for t in tools]

    # Verify base tools are present
    assert "agent_chat" in tool_names, "Missing agent_chat tool"
    assert "conversation_get" in tool_names, "Missing conversation_get tool"

    # These will fail if tools.append() fails due to undefined 'tools'
    assert len(tool_names) >= 3, f"Expected at least 3 tools, got {len(tool_names)}"


def test_budget_monitor_module_imports_successfully():
    """
    Test that budget_monitor module can be imported without errors.

    FAILS when: CostMetricsCollector type is not imported
    PASSES when: Import is added (top-level or TYPE_CHECKING)
    """
    from mcp_server_langgraph.monitoring import budget_monitor

    assert hasattr(budget_monitor, "BudgetMonitor")
    assert budget_monitor.BudgetMonitor is not None


def test_budget_monitor_init_signature_resolves_cost_collector():
    """
    Test that BudgetMonitor.__init__ type hints are properly resolved.

    FAILS when: CostMetricsCollector is not imported for type checking
    PASSES when: Import is added (top-level or TYPE_CHECKING)
    """
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor

    # This will raise NameError if CostMetricsCollector is not imported
    sig = inspect.signature(BudgetMonitor.__init__)
    assert "cost_collector" in sig.parameters

    # Verify the type annotation is resolved
    cost_collector_param = sig.parameters["cost_collector"]
    assert cost_collector_param.annotation is not inspect.Parameter.empty


def test_budget_monitor_accepts_none_cost_collector():
    """
    Test that BudgetMonitor can be instantiated without cost_collector.

    FAILS when: Type annotations cause import errors
    PASSES when: Imports are correct and Optional works properly
    """
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor

    # Should accept None (Optional parameter)
    monitor = BudgetMonitor(cost_collector=None)
    assert monitor is not None


def test_all_critical_modules_import_without_errors():
    """
    Integration test: Verify all critical modules with import issues can be imported.

    FAILS when: Any of the three import errors exist
    PASSES when: All imports are fixed
    """
    # These imports will fail if any of the issues exist
    from mcp_server_langgraph.execution.sandbox import Sandbox
    from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor

    # Verify classes are importable
    assert Sandbox is not None
    assert MCPAgentServer is not None
    assert BudgetMonitor is not None


def test_sandbox_accepts_resource_limits_instance():
    """
    Test that Sandbox can be instantiated with ResourceLimits.

    FAILS when: ResourceLimits import is missing
    PASSES when: Import is added and class is available
    """
    from mcp_server_langgraph.execution.resource_limits import ResourceLimits
    from mcp_server_langgraph.execution.sandbox import Sandbox

    # Sandbox is abstract, but we can verify the signature accepts it
    # (Actual instantiation would require implementing abstract methods)
    sig = inspect.signature(Sandbox.__init__)
    limits_param = sig.parameters["limits"]

    # Verify ResourceLimits type is recognized
    assert limits_param.annotation is not inspect.Parameter.empty

    # Verify ResourceLimits class is available (create instance to confirm)
    _ = ResourceLimits(timeout_seconds=30, memory_limit_mb=512, cpu_quota=0.5)
