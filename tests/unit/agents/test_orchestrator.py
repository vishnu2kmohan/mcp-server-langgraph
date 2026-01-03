"""
Unit tests for Multi-Agent Orchestrator

Tests the orchestrator-worker pattern for parallel task execution
with clean context windows and artifact-based synthesis.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.multi_agent]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_basic")
class TestOrchestratorBasic:
    """Test suite for basic orchestrator functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_import_and_instantiate_succeeds(self):
        """GIVEN the agents module
        WHEN importing Orchestrator
        THEN it should be available
        """
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        assert orchestrator is not None

    def test_orchestrator_has_model_selector(self):
        """GIVEN an Orchestrator
        WHEN checking configuration
        THEN it should have a model selector
        """
        from mcp_server_langgraph.agents.model_selector import ModelSelector
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        assert hasattr(orchestrator, "model_selector")
        assert isinstance(orchestrator.model_selector, ModelSelector)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_decomposition")
class TestOrchestratorDecomposition:
    """Test suite for task decomposition"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_decompose_task_creates_subtasks(self):
        """GIVEN a complex task
        WHEN decomposing the task
        THEN subtasks should be created
        """
        from mcp_server_langgraph.agents.orchestrator import (
            Orchestrator,
            TaskDecomposition,
        )

        orchestrator = Orchestrator()

        result = orchestrator.decompose_task(
            task="Research quantum computing and summarize key developments",
            num_subtasks=3,
        )

        assert isinstance(result, TaskDecomposition)
        assert len(result.subtasks) == 3

    def test_decomposition_has_delegation_instructions(self):
        """GIVEN a task decomposition
        WHEN checking subtasks
        THEN each should have detailed instructions
        """
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        result = orchestrator.decompose_task(
            task="Analyze codebase security",
            num_subtasks=2,
        )

        for subtask in result.subtasks:
            assert subtask.instructions is not None
            assert len(subtask.instructions) > 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_subagent")
class TestSubagent:
    """Test suite for subagent functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_subagent_import_and_instantiate_succeeds(self):
        """GIVEN the agents module
        WHEN importing Subagent
        THEN it should be available
        """
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(task_id="task-1", instructions="Do something")
        assert subagent is not None

    def test_subagent_has_clean_context(self):
        """GIVEN a Subagent
        WHEN checking configuration
        THEN it should have isolated context
        """
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(task_id="task-1", instructions="Test task")

        assert subagent.context_window is not None
        assert len(subagent.context_window) == 0  # Starts empty


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_subagent_llm")
class TestSubagentLLMIntegration:
    """Test suite for subagent LLM factory integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_subagent_accepts_llm_factory(self):
        """GIVEN a Subagent
        WHEN providing an LLM factory
        THEN it should be stored for execution
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.agents.subagent import Subagent

        mock_llm = MagicMock()
        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
            llm_factory=mock_llm,
        )

        assert subagent.llm_factory is mock_llm

    @pytest.mark.asyncio
    async def test_execute_calls_llm_with_context(self):
        """GIVEN a Subagent with LLM factory
        WHEN executing the task
        THEN LLM ainvoke should be called with context messages
        """
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.subagent import Subagent

        # Create mock LLM that returns an AIMessage
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="This is the LLM response"))

        subagent = Subagent(
            task_id="task-1",
            instructions="Analyze the data",
            llm_factory=mock_llm,
        )

        _result = await subagent.execute()  # noqa: F841 (verifying execution completes)

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify context was passed
        call_args = mock_llm.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg is messages list
        assert len(messages) > 0

    @pytest.mark.asyncio
    async def test_execute_returns_llm_response_as_output(self):
        """GIVEN a Subagent with LLM factory
        WHEN executing the task
        THEN the LLM response content should be the output
        """
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.subagent import Subagent

        expected_response = "The analysis shows positive results"
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=expected_response))

        subagent = Subagent(
            task_id="task-1",
            instructions="Analyze the data",
            llm_factory=mock_llm,
        )

        result = await subagent.execute()

        assert result.success is True
        assert result.output == expected_response

    @pytest.mark.asyncio
    async def test_execute_handles_llm_error(self):
        """GIVEN a Subagent with failing LLM
        WHEN executing the task
        THEN error should be captured and returned
        """
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.agents.subagent import Subagent, SubagentStatus

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM service unavailable"))

        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
            llm_factory=mock_llm,
        )

        result = await subagent.execute()

        assert result.success is False
        assert "LLM service unavailable" in result.error
        assert subagent.status == SubagentStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_without_llm_uses_placeholder(self):
        """GIVEN a Subagent without LLM factory
        WHEN executing the task
        THEN it should return placeholder result
        """
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
        )

        result = await subagent.execute()

        # Without LLM, should still succeed with placeholder
        assert result.success is True
        assert "task-1" in result.output

    @pytest.mark.asyncio
    async def test_execute_adds_system_prompt_to_context(self):
        """GIVEN a Subagent with system prompt
        WHEN executing the task
        THEN system prompt should be in context
        """
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.subagent import Subagent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))

        system_prompt = "You are a helpful assistant."
        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
            llm_factory=mock_llm,
            system_prompt=system_prompt,
        )

        await subagent.execute()

        # Check that context includes system message
        assert any(msg.get("role") == "system" and system_prompt in msg.get("content", "") for msg in subagent.context_window)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_coordinator")
class TestCoordinator:
    """Test suite for task coordinator"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_coordinator_import_and_instantiate_succeeds(self):
        """GIVEN the agents module
        WHEN importing Coordinator
        THEN it should be available
        """
        from mcp_server_langgraph.agents.coordinator import Coordinator

        coordinator = Coordinator()
        assert coordinator is not None

    def test_coordinator_tracks_subagents(self):
        """GIVEN a Coordinator
        WHEN spawning subagents
        THEN they should be tracked
        """
        from mcp_server_langgraph.agents.coordinator import Coordinator
        from mcp_server_langgraph.agents.subagent import Subagent

        coordinator = Coordinator()
        subagent = Subagent(task_id="task-1", instructions="Test")

        coordinator.register_subagent(subagent)

        assert coordinator.get_subagent("task-1") is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_artifacts")
class TestArtifacts:
    """Test suite for artifact storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_artifact_storage_exists(self):
        """GIVEN the agents module
        WHEN importing ArtifactStorage
        THEN it should be available
        """
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage

        storage = ArtifactStorage()
        assert storage is not None

    def test_store_and_retrieve_artifact(self):
        """GIVEN an ArtifactStorage
        WHEN storing and retrieving an artifact
        THEN the artifact should be returned
        """
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage

        storage = ArtifactStorage()

        storage.store("task-1", "result", {"data": "test result"})
        artifact = storage.retrieve("task-1", "result")

        assert artifact is not None
        assert artifact["data"] == "test result"

    def test_list_artifacts_for_task(self):
        """GIVEN an ArtifactStorage with artifacts
        WHEN listing artifacts for a task
        THEN all artifacts should be returned
        """
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage

        storage = ArtifactStorage()
        storage.store("task-1", "result-a", {"a": 1})
        storage.store("task-1", "result-b", {"b": 2})

        artifacts = storage.list_for_task("task-1")

        assert len(artifacts) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_model_selector")
class TestModelSelector:
    """Test suite for three-tier model selection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_model_selector_exists(self):
        """GIVEN the agents module
        WHEN importing ModelSelector
        THEN it should be available
        """
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()
        assert selector is not None

    def test_select_model_for_complexity(self):
        """GIVEN a ModelSelector
        WHEN selecting model for complexity
        THEN appropriate tier should be returned
        """
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()

        # Simple tasks
        simple = selector.select_model("simple")
        assert "flash" in simple.lower() or "nano" in simple.lower() or "haiku" in simple.lower()

        # Complex tasks
        complex_model = selector.select_model("complex")
        assert "pro" in complex_model.lower() or "opus" in complex_model.lower() or "o3" in complex_model.lower()

    def test_select_verifier_model(self):
        """GIVEN a ModelSelector
        WHEN selecting verifier model
        THEN cross-vendor model should be preferred
        """
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector()

        # With cross-vendor verification
        verifier = selector.select_verifier("auto")

        # Should return a valid model name
        assert verifier is not None
        assert len(verifier.model) > 0

    def test_graceful_fallback_returns_available_tier(self):
        """GIVEN a ModelSelector with limited tiers
        WHEN requesting unavailable tier
        THEN fallback should be used
        """
        from mcp_server_langgraph.agents.model_selector import ModelSelector

        # Only simple tier available
        selector = ModelSelector(available_tiers=["simple"])

        # Request complex, should fallback to simple
        model = selector.select_model("complex")

        assert model is not None  # Should return something


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_orchestrator_metrics_integration")
class TestOrchestratorMetricsIntegration:
    """Test suite for verifying metrics are recorded during orchestration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_orchestrator_execute_records_metrics(self):
        """GIVEN an orchestrator with decomposed task
        WHEN execute is called
        THEN orchestrator execution metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        decomposition = orchestrator.decompose_task("Test task", num_subtasks=2)

        with patch("mcp_server_langgraph.agents.orchestrator.record_orchestrator_execution") as mock_record:
            await orchestrator.execute(decomposition)

            # Verify metrics were recorded
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert "task_count" in call_kwargs
            assert "successful_count" in call_kwargs
            assert "duration_ms" in call_kwargs
            assert "success" in call_kwargs
            assert call_kwargs["task_count"] == 2

    @pytest.mark.asyncio
    async def test_orchestrator_execute_records_artifact_metrics(self):
        """GIVEN an orchestrator execution
        WHEN results are stored as artifacts
        THEN artifact storage metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        decomposition = orchestrator.decompose_task("Test task", num_subtasks=2)

        with patch("mcp_server_langgraph.agents.orchestrator.record_artifact_storage") as mock_record:
            await orchestrator.execute(decomposition)

            # Each successful result should record artifact storage
            assert mock_record.call_count >= 1

    @pytest.mark.asyncio
    async def test_orchestrator_synthesize_records_metrics(self):
        """GIVEN orchestrator results
        WHEN synthesize is called
        THEN synthesis metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.agents.subagent import SubagentResult

        orchestrator = Orchestrator()
        decomposition = orchestrator.decompose_task("Test task", num_subtasks=2)
        results = [
            SubagentResult(task_id="subtask-1", success=True, output="Result 1"),
            SubagentResult(task_id="subtask-2", success=True, output="Result 2"),
        ]

        with patch("mcp_server_langgraph.agents.orchestrator.record_synthesis_operation") as mock_record:
            await orchestrator.synthesize(decomposition, results)

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert "input_count" in call_kwargs
            assert "successful_inputs" in call_kwargs
            assert "duration_ms" in call_kwargs
            assert "success" in call_kwargs


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_subagent_metrics_integration")
class TestSubagentMetricsIntegration:
    """Test suite for verifying metrics are recorded during subagent execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subagent_execute_records_metrics(self):
        """GIVEN a subagent
        WHEN execute is called
        THEN subagent execution metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
            model="gemini-2.5-flash",
        )

        with patch("mcp_server_langgraph.agents.subagent.record_subagent_execution") as mock_record:
            await subagent.execute()

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["task_id"] == "task-1"
            assert call_kwargs["model"] == "gemini-2.5-flash"
            assert "duration_ms" in call_kwargs
            assert "success" in call_kwargs

    @pytest.mark.asyncio
    async def test_subagent_execute_records_error_type_on_failure(self):
        """GIVEN a subagent with failing LLM
        WHEN execute fails
        THEN error type should be recorded in metrics.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.agents.subagent import Subagent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Request timed out"))

        subagent = Subagent(
            task_id="task-1",
            instructions="Test task",
            model="gemini-2.5-flash",
            llm_factory=mock_llm,
        )

        with patch("mcp_server_langgraph.agents.subagent.record_subagent_execution") as mock_record:
            await subagent.execute()

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["success"] is False
            assert call_kwargs["error_type"] == "TimeoutError"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_model_selector_metrics_integration")
class TestModelSelectorMetricsIntegration:
    """Test suite for verifying metrics are recorded during model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_model_records_metrics(self):
        """GIVEN a model selector
        WHEN select_model is called
        THEN model selection metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        with patch("mcp_server_langgraph.agents.model_selector.record_model_selection") as mock_record:
            model = selector.select_model("complicated")

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["tier"] == "complicated"
            assert call_kwargs["vendor"] == "google"
            assert call_kwargs["model"] == model

    def test_select_model_records_fallback(self):
        """GIVEN a model selector with limited tiers
        WHEN fallback occurs
        THEN is_fallback should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_tiers=["simple"])

        with patch("mcp_server_langgraph.agents.model_selector.record_model_selection") as mock_record:
            selector.select_model("complex")  # Will fallback

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["is_fallback"] is True

    def test_select_verifier_records_cross_vendor_metrics(self):
        """GIVEN a model selector with multiple vendors
        WHEN select_verifier is called
        THEN cross-vendor verification metrics should be recorded.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google", "anthropic"])

        with patch("mcp_server_langgraph.agents.model_selector.record_cross_vendor_verification") as mock_record:
            selector.select_verifier("auto")

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["primary_vendor"] == "google"
            assert call_kwargs["verifier_vendor"] == "anthropic"
            assert call_kwargs["same_vendor_fallback"] is False

    def test_select_verifier_records_same_vendor_fallback(self):
        """GIVEN a model selector with single vendor
        WHEN select_verifier falls back to same vendor
        THEN same_vendor_fallback should be True.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.agents.model_selector import ModelSelector

        selector = ModelSelector(available_vendors=["google"])

        with patch("mcp_server_langgraph.agents.model_selector.record_cross_vendor_verification") as mock_record:
            selector.select_verifier("auto")

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["same_vendor_fallback"] is True
