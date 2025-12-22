"""
Multi-Agent Orchestration

Implements the orchestrator-worker pattern for parallel task execution
with clean context windows and artifact-based synthesis.

Architecture:
    Lead Agent (Orchestrator) [Complex Model]
        ├── Subagent 1 (parallel) [Simple Model] → Artifact Storage
        ├── Subagent 2 (parallel) [Simple Model] → Artifact Storage
        └── Subagent 3 (parallel) [Simple Model] → Artifact Storage
             ↓
        Synthesis (coordinator reads artifacts) [Complex Model]
             ↓
        Cross-Vendor Verification [Verifier Model]

Usage:
    from mcp_server_langgraph.agents import Orchestrator

    orchestrator = Orchestrator()
    decomposition = orchestrator.decompose_task("Research quantum computing")
    results = await orchestrator.execute(decomposition)
    final = await orchestrator.synthesize(decomposition, results)
"""

from mcp_server_langgraph.agents import base_orchestrator
from mcp_server_langgraph.agents.artifacts import Artifact, ArtifactStorage
from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
)
from mcp_server_langgraph.agents.coordinator import Coordinator
from mcp_server_langgraph.agents.definition import AgentDefinition, AgentRegistry
from mcp_server_langgraph.agents.metrics import (
    record_artifact_storage,
    record_cross_vendor_verification,
    record_model_selection,
    record_orchestrator_execution,
    record_subagent_execution,
    record_synthesis_operation,
)
from mcp_server_langgraph.agents.model_selector import (
    MODEL_TIERS,
    VENDOR_PRIORITY,
    ModelSelector,
)
from mcp_server_langgraph.agents.orchestrator import (
    Orchestrator,
    Subtask,
    TaskDecomposition,
)
from mcp_server_langgraph.agents.subagent import (
    Subagent,
    SubagentResult,
    SubagentStatus,
)
from mcp_server_langgraph.agents.ux_orchestrator import (
    UX_ANALYSIS_TYPES,
    UXAnalysisResult,
    UXAnalysisTask,
    UXOrchestrator,
)
from mcp_server_langgraph.agents import alert_orchestrator
from mcp_server_langgraph.agents.alert_orchestrator import (
    ALERT_ANALYSIS_TYPES,
    AlertAnalysisResult,
    AlertAnalysisTask,
    AlertOrchestrator,
)
from mcp_server_langgraph.agents import context_filter
from mcp_server_langgraph.agents.context_filter import (
    ChainedFilter,
    ContextFilter,
    KeepLastNFilter,
    RemoveToolCallsFilter,
    SummarizeHistoryFilter,
)
from mcp_server_langgraph.agents import handoff
from mcp_server_langgraph.agents.handoff import (
    Handoff,
    HandoffContext,
    HandoffResult,
    HandoffTool,
)
from mcp_server_langgraph.agents import loop_agent
from mcp_server_langgraph.agents.loop_agent import (
    LoopAgent,
    LoopConfig,
    LoopResult,
)

__all__ = [
    # Base Orchestrator (REFACTOR phase)
    "base_orchestrator",
    "BaseOrchestrator",
    "BaseTask",
    "BaseResult",
    # Agent Definition (SDK Pattern)
    "AgentDefinition",
    "AgentRegistry",
    # Orchestrator
    "Orchestrator",
    "TaskDecomposition",
    "Subtask",
    # Subagent
    "Subagent",
    "SubagentResult",
    "SubagentStatus",
    # Coordinator
    "Coordinator",
    # Artifacts
    "Artifact",
    "ArtifactStorage",
    # Model Selection
    "ModelSelector",
    "MODEL_TIERS",
    "VENDOR_PRIORITY",
    # Metrics
    "record_artifact_storage",
    "record_cross_vendor_verification",
    "record_model_selection",
    "record_orchestrator_execution",
    "record_subagent_execution",
    "record_synthesis_operation",
    # UX Orchestrator (Phase 11)
    "UXOrchestrator",
    "UXAnalysisTask",
    "UXAnalysisResult",
    "UX_ANALYSIS_TYPES",
    # Alert Orchestrator (Phase 12)
    "alert_orchestrator",
    "AlertOrchestrator",
    "AlertAnalysisTask",
    "AlertAnalysisResult",
    "ALERT_ANALYSIS_TYPES",
    # Context Filter (ADR-0081)
    "context_filter",
    "ContextFilter",
    "KeepLastNFilter",
    "RemoveToolCallsFilter",
    "SummarizeHistoryFilter",
    "ChainedFilter",
    # Handoff Pattern (ADR-0081)
    "handoff",
    "Handoff",
    "HandoffContext",
    "HandoffResult",
    "HandoffTool",
    # LoopAgent Pattern (ADR-0084 / Google ADK parity)
    "loop_agent",
    "LoopAgent",
    "LoopConfig",
    "LoopResult",
]
