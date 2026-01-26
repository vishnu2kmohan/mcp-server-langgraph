"""
Orchestrator Registry

Provides metadata about all available orchestrators in the system.

Sprint 1 of Enhanced Agents Page Implementation Plan:
- ORCHESTRATOR_REGISTRY: Dictionary of all registered orchestrators
- OrchestratorInfo: Pydantic model for orchestrator metadata
- get_orchestrator_info: Get info for a specific orchestrator
- get_all_orchestrators: Get list of all orchestrator infos

Usage:
    from mcp_server_langgraph.agents.registry import (
        ORCHESTRATOR_REGISTRY,
        get_orchestrator_info,
        get_all_orchestrators,
    )

    # Get specific orchestrator info
    info = get_orchestrator_info("StudioOrchestrator")
    if info:
        print(f"Feature flag: {info.feature_flag}")

    # Get all orchestrators
    all_orchestrators = get_all_orchestrators()
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrchestratorInfo(BaseModel):
    """Metadata about an orchestrator.

    Used for displaying orchestrator information in the agents page
    and for understanding the orchestrator hierarchy.
    """

    name: str = Field(..., description="Orchestrator class name")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Description of orchestrator purpose")
    feature_flag: str = Field(..., description="Feature flag controlling this orchestrator")
    task_categories: list[str] = Field(
        default_factory=list,
        description="Task categories this orchestrator handles",
    )


# =============================================================================
# ORCHESTRATOR_REGISTRY
# =============================================================================
# Registry of all orchestrators in the system with their metadata.
# This is the single source of truth for orchestrator information.
# =============================================================================

ORCHESTRATOR_REGISTRY: dict[str, OrchestratorInfo] = {
    "Orchestrator": OrchestratorInfo(
        name="Orchestrator",
        display_name="Multi-Agent Orchestrator",
        description="Lead agent that decomposes complex tasks and delegates to subagents. "
        "Implements orchestrator-worker pattern with artifact-based synthesis.",
        feature_flag="enable_multi_agent_orchestration",
        task_categories=["decomposition", "delegation", "synthesis"],
    ),
    "SwarmOrchestrator": OrchestratorInfo(
        name="SwarmOrchestrator",
        display_name="Swarm Orchestrator",
        description="Parallel multi-agent orchestrator using race, cascade, or consensus strategies. "
        "Implements ADR-0105 AsyncIO-first swarm execution for speed-optimized parallel responses.",
        feature_flag="enable_swarm_orchestrator",
        task_categories=["parallel", "consensus", "race", "cascade"],
    ),
    "StudioOrchestrator": OrchestratorInfo(
        name="StudioOrchestrator",
        display_name="Studio AI Orchestrator",
        description="Unified Studio AI orchestration for StudioShell AI capabilities. "
        "Handles UX, session, conversation, canvas, diagram, trace, HITL, and command tasks.",
        feature_flag="enable_studio_ai",
        task_categories=[
            "UX",
            "SESSION",
            "CONVERSATION",
            "CANVAS",
            "DIAGRAM",
            "TRACE",
            "HITL",
            "COMMAND",
        ],
    ),
    "UXOrchestrator": OrchestratorInfo(
        name="UXOrchestrator",
        display_name="UX Orchestrator",
        description="Orchestrates AI-native UX analysis tasks including persona analysis, "
        "disclosure analysis, error recovery, and composite analysis.",
        feature_flag="enable_orchestrated_ai_ux",
        task_categories=["persona", "disclosure", "error_recovery", "composite"],
    ),
    "AlertOrchestrator": OrchestratorInfo(
        name="AlertOrchestrator",
        display_name="Alert Orchestrator",
        description="Orchestrates alert analysis tasks including correlation analysis, "
        "root cause analysis, and recommendation generation.",
        feature_flag="enable_orchestrated_alert_analysis",
        task_categories=["correlation", "root_cause", "recommendations"],
    ),
    "ExplanationOrchestrator": OrchestratorInfo(
        name="ExplanationOrchestrator",
        display_name="Explanation Orchestrator",
        description="Generates AI-powered explanations for HITL dialogs including "
        "uncertainty analysis, risk analysis, and alternatives analysis.",
        feature_flag="enable_ai_explanations",
        task_categories=["uncertainty", "risk", "alternatives", "evidence"],
    ),
    "LoopAgent": OrchestratorInfo(
        name="LoopAgent",
        display_name="Loop Agent",
        description="Iterative task execution agent with termination conditions. "
        "Implements Google ADK LoopAgent pattern for repeated task execution.",
        feature_flag="enable_loop_agent",
        task_categories=["iteration", "refinement"],
    ),
}


def get_orchestrator_info(name: str) -> OrchestratorInfo | None:
    """Get orchestrator info by name.

    Args:
        name: Orchestrator class name (e.g., "StudioOrchestrator")

    Returns:
        OrchestratorInfo if found, None otherwise
    """
    return ORCHESTRATOR_REGISTRY.get(name)


def get_all_orchestrators() -> list[OrchestratorInfo]:
    """Get list of all registered orchestrators.

    Returns:
        List of OrchestratorInfo for all registered orchestrators
    """
    return list(ORCHESTRATOR_REGISTRY.values())
