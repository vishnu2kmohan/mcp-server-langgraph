"""
Tests for ORCHESTRATOR_REGISTRY (Sprint 1)

TDD tests for the orchestrator registry that provides metadata about
all available orchestrators in the system.

Test Coverage:
- OrchestratorInfo model validation
- ORCHESTRATOR_REGISTRY constant contains all orchestrators
- get_orchestrator_info returns correct info for known orchestrators
- get_all_orchestrators returns list of all orchestrator infos
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_registry")
class TestOrchestratorInfoModel:
    """Tests for OrchestratorInfo model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_info_valid(self) -> None:
        """OrchestratorInfo should accept valid data."""
        from mcp_server_langgraph.agents.registry import OrchestratorInfo

        info = OrchestratorInfo(
            name="StudioOrchestrator",
            display_name="Studio AI Orchestrator",
            description="Unified Studio AI orchestration for StudioShell capabilities",
            feature_flag="enable_studio_ai",
            task_categories=["UX", "SESSION", "CONVERSATION", "CANVAS"],
        )

        assert info.name == "StudioOrchestrator"
        assert info.display_name == "Studio AI Orchestrator"
        assert info.feature_flag == "enable_studio_ai"
        assert len(info.task_categories) == 4

    def test_orchestrator_info_empty_categories(self) -> None:
        """OrchestratorInfo should accept empty task categories."""
        from mcp_server_langgraph.agents.registry import OrchestratorInfo

        info = OrchestratorInfo(
            name="LoopAgent",
            display_name="Loop Agent",
            description="Iterative task execution agent",
            feature_flag="enable_loop_agent",
            task_categories=[],
        )

        assert info.name == "LoopAgent"
        assert info.task_categories == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_registry")
class TestOrchestratorRegistry:
    """Tests for ORCHESTRATOR_REGISTRY constant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registry_contains_orchestrator(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain Orchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "Orchestrator" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["Orchestrator"].feature_flag == "enable_multi_agent_orchestration"

    def test_registry_contains_studio_orchestrator(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain StudioOrchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "StudioOrchestrator" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["StudioOrchestrator"].feature_flag == "enable_studio_ai"

    def test_registry_contains_ux_orchestrator(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain UXOrchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "UXOrchestrator" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["UXOrchestrator"].feature_flag == "enable_orchestrated_ai_ux"

    def test_registry_contains_alert_orchestrator(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain AlertOrchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "AlertOrchestrator" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["AlertOrchestrator"].feature_flag == "enable_orchestrated_alert_analysis"

    def test_registry_contains_explanation_orchestrator(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain ExplanationOrchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "ExplanationOrchestrator" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["ExplanationOrchestrator"].feature_flag == "enable_ai_explanations"

    def test_registry_contains_loop_agent(self) -> None:
        """ORCHESTRATOR_REGISTRY should contain LoopAgent."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "LoopAgent" in ORCHESTRATOR_REGISTRY
        assert ORCHESTRATOR_REGISTRY["LoopAgent"].feature_flag == "enable_loop_agent"

    def test_registry_has_at_least_six_orchestrators(self) -> None:
        """ORCHESTRATOR_REGISTRY should have at least 6 orchestrators."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert len(ORCHESTRATOR_REGISTRY) >= 6


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_registry")
class TestGetOrchestratorInfo:
    """Tests for get_orchestrator_info helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_orchestrator_info_known(self) -> None:
        """get_orchestrator_info should return info for known orchestrator."""
        from mcp_server_langgraph.agents.registry import get_orchestrator_info

        info = get_orchestrator_info("StudioOrchestrator")

        assert info is not None
        assert info.name == "StudioOrchestrator"
        assert info.feature_flag == "enable_studio_ai"

    def test_get_orchestrator_info_unknown(self) -> None:
        """get_orchestrator_info should return None for unknown orchestrator."""
        from mcp_server_langgraph.agents.registry import get_orchestrator_info

        info = get_orchestrator_info("NonExistentOrchestrator")

        assert info is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_registry")
class TestGetAllOrchestrators:
    """Tests for get_all_orchestrators helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_all_orchestrators_returns_list(self) -> None:
        """get_all_orchestrators should return list of OrchestratorInfo."""
        from mcp_server_langgraph.agents.registry import (
            OrchestratorInfo,
            get_all_orchestrators,
        )

        orchestrators = get_all_orchestrators()

        assert isinstance(orchestrators, list)
        assert len(orchestrators) >= 6
        assert all(isinstance(o, OrchestratorInfo) for o in orchestrators)

    def test_get_all_orchestrators_contains_all_registered(self) -> None:
        """get_all_orchestrators should contain all registered orchestrators."""
        from mcp_server_langgraph.agents.registry import (
            ORCHESTRATOR_REGISTRY,
            get_all_orchestrators,
        )

        orchestrators = get_all_orchestrators()
        names = {o.name for o in orchestrators}

        for name in ORCHESTRATOR_REGISTRY:
            assert name in names
