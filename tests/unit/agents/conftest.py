"""
Pytest fixtures for agents tests.

Enables feature flags required for multi-agent orchestration testing.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

if TYPE_CHECKING:
    pass


@pytest.fixture(autouse=True)
def mock_feature_flags_for_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable multi-agent feature flags for all agent tests.

    This fixture patches feature_flags in the core module and all
    agent-related modules to enable multi-agent orchestration.
    """
    from mcp_server_langgraph.agents import orchestrator as orch_module
    from mcp_server_langgraph.agents import resilience as resilience_module

    # Get the actual module (not the exported singleton)
    ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]

    # Create mock with multi-agent features enabled
    mock_flags = MockFeatureFlags(
        enable_multi_agent_orchestration=True,
        enable_agentic_memory=True,
        enable_sdk_agent_definition=True,
        max_subagents=10,
        enable_cost_tracking=True,
        orchestration_cost_limit=0.50,
        session_cost_limit=5.00,
        cost_alert_thresholds=[0.5, 0.75, 0.9],
        enable_thinking_budget=True,
        default_thinking_level="medium",
        enable_dynamic_context_splitting=True,
        context_split_threshold=0.8,
        # Orchestrator resilience flags (Phase 10)
        enable_orchestrator_resilience=True,
        orchestrator_timeout_seconds=300,
        orchestrator_max_concurrent=5,
        orchestrator_circuit_breaker_threshold=3,
        # HITL (Human-in-the-Loop) flags
        enable_agent_hitl=True,
        agent_hitl_confidence_threshold=0.7,
        # Context Graph flags (ADR-0101)
        enable_context_graph=True,
        enable_precedent_search=True,
        context_graph_async_persistence=False,  # Sync for testing
        context_graph_sampling_rate=1.0,
    )

    # Patch at all module levels that use feature_flags
    monkeypatch.setattr(ff_module, "feature_flags", mock_flags)
    monkeypatch.setattr(orch_module, "feature_flags", mock_flags)
    monkeypatch.setattr(resilience_module, "feature_flags", mock_flags)

    # Reset the orchestrator semaphore to ensure fresh state
    resilience_module.reset_orchestrator_semaphore()

    # Patch cost_tracker if it's been imported
    if "mcp_server_langgraph.agents.cost_tracker" in sys.modules:
        cost_tracker_module = sys.modules["mcp_server_langgraph.agents.cost_tracker"]
        monkeypatch.setattr(cost_tracker_module, "feature_flags", mock_flags)
