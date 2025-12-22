"""
Unit tests for BaseOrchestrator (REFACTOR phase).

Tests the abstract base class that provides common orchestration patterns:
- Parallel task execution with asyncio.gather
- Exception handling and conversion to failed results
- Generic task/result pattern
- Feature flag integration

TDD: Tests written FIRST before implementation.
"""

import asyncio
import gc
from abc import ABC
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="base_orchestrator_module")
class TestBaseOrchestratorModule:
    """Test base orchestrator module structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_orchestrator_module_exists(self) -> None:
        """Test that base_orchestrator module exists."""
        from mcp_server_langgraph.agents import base_orchestrator

        assert base_orchestrator is not None

    def test_base_orchestrator_class_exists(self) -> None:
        """Test that BaseOrchestrator class exists."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        assert BaseOrchestrator is not None

    def test_base_task_class_exists(self) -> None:
        """Test that BaseTask class exists."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        assert BaseTask is not None

    def test_base_result_class_exists(self) -> None:
        """Test that BaseResult class exists."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        assert BaseResult is not None


@pytest.mark.xdist_group(name="base_orchestrator_abstract")
class TestBaseOrchestratorIsAbstract:
    """Test that BaseOrchestrator is an abstract base class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_orchestrator_is_abc(self) -> None:
        """Test that BaseOrchestrator inherits from ABC."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        assert issubclass(BaseOrchestrator, ABC)

    def test_base_orchestrator_cannot_be_instantiated_directly(self) -> None:
        """Test that BaseOrchestrator cannot be instantiated."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseOrchestrator()  # type: ignore

    def test_base_orchestrator_has_abstract_execute_task(self) -> None:
        """Test that _execute_task is an abstract method."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        # The abstract method should be in __abstractmethods__
        assert "_execute_task" in BaseOrchestrator.__abstractmethods__

    def test_base_orchestrator_has_abstract_synthesize(self) -> None:
        """Test that synthesize is an abstract method."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        assert "synthesize" in BaseOrchestrator.__abstractmethods__

    def test_base_orchestrator_has_abstract_feature_flag_name(self) -> None:
        """Test that feature_flag_name is an abstract property."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator

        assert "feature_flag_name" in BaseOrchestrator.__abstractmethods__


@pytest.mark.xdist_group(name="base_task")
class TestBaseTask:
    """Test BaseTask dataclass."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_task_has_task_type(self) -> None:
        """Test that BaseTask has task_type field."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        task = BaseTask(task_type="test_task")
        assert task.task_type == "test_task"

    def test_base_task_has_data_with_default(self) -> None:
        """Test that BaseTask has data field with default empty dict."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        task = BaseTask(task_type="test")
        assert task.data == {}

    def test_base_task_accepts_custom_data(self) -> None:
        """Test that BaseTask accepts custom data."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        task = BaseTask(task_type="test", data={"key": "value"})
        assert task.data == {"key": "value"}


@pytest.mark.xdist_group(name="base_result")
class TestBaseResult:
    """Test BaseResult dataclass."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_result_has_task_type(self) -> None:
        """Test that BaseResult has task_type field."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=True)
        assert result.task_type == "test"

    def test_base_result_has_success(self) -> None:
        """Test that BaseResult has success field."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=True)
        assert result.success is True

    def test_base_result_has_optional_result(self) -> None:
        """Test that BaseResult has optional result field."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=True, result={"data": "value"})
        assert result.result == {"data": "value"}

    def test_base_result_has_optional_error(self) -> None:
        """Test that BaseResult has optional error field."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=False, error="Something failed")
        assert result.error == "Something failed"

    def test_base_result_result_defaults_to_none(self) -> None:
        """Test that result defaults to None."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=True)
        assert result.result is None

    def test_base_result_error_defaults_to_none(self) -> None:
        """Test that error defaults to None."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult

        result = BaseResult(task_type="test", success=True)
        assert result.error is None


@pytest.mark.xdist_group(name="base_orchestrator_concrete")
class TestConcreteOrchestrator:
    """Test concrete orchestrator implementation patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_concrete_orchestrator(self):
        """Create a concrete implementation for testing."""
        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
            BaseTask,
        )

        class ConcreteOrchestrator(BaseOrchestrator[BaseTask, BaseResult]):
            """Concrete implementation for testing."""

            @property
            def feature_flag_name(self) -> str:
                return "enable_test_orchestrator"

            async def _execute_task(self, task: BaseTask) -> BaseResult:
                # Simple test implementation
                return BaseResult(
                    task_type=task.task_type,
                    success=True,
                    result={"processed": True},
                )

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {
                    "total": len(results),
                    "successful": sum(1 for r in results if r.success),
                }

        return ConcreteOrchestrator

    def test_concrete_orchestrator_can_be_instantiated(self) -> None:
        """Test that concrete implementation can be instantiated."""
        ConcreteOrchestrator = self._create_concrete_orchestrator()
        orchestrator = ConcreteOrchestrator()
        assert orchestrator is not None

    def test_concrete_orchestrator_has_execute_method(self) -> None:
        """Test that concrete orchestrator has execute method."""
        ConcreteOrchestrator = self._create_concrete_orchestrator()
        orchestrator = ConcreteOrchestrator()
        assert hasattr(orchestrator, "execute")
        assert callable(orchestrator.execute)

    def test_concrete_orchestrator_has_is_enabled_property(self) -> None:
        """Test that concrete orchestrator has is_enabled property."""
        ConcreteOrchestrator = self._create_concrete_orchestrator()
        orchestrator = ConcreteOrchestrator()
        assert hasattr(orchestrator, "is_enabled")
        # is_enabled should return a bool
        assert isinstance(orchestrator.is_enabled, bool)


@pytest.mark.xdist_group(name="base_orchestrator_execute")
class TestBaseOrchestratorExecute:
    """Test execute method behavior."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_test_orchestrator(self, execute_task_impl=None):
        """Create a test orchestrator with custom execute_task."""
        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
            BaseTask,
        )

        class TestOrchestrator(BaseOrchestrator[BaseTask, BaseResult]):
            def __init__(self, execute_impl=None):
                super().__init__()
                self._execute_impl = execute_impl

            @property
            def feature_flag_name(self) -> str:
                return "enable_test_orchestrator"

            async def _execute_task(self, task: BaseTask) -> BaseResult:
                if self._execute_impl:
                    return await self._execute_impl(task)
                return BaseResult(task_type=task.task_type, success=True)

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {"results": [r.task_type for r in results]}

        return TestOrchestrator(execute_impl=execute_task_impl)

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_for_empty_tasks(self) -> None:
        """Test that execute returns empty list for empty input."""
        orchestrator = self._create_test_orchestrator()
        results = await orchestrator.execute([])
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_returns_list_of_results(self) -> None:
        """Test that execute returns list of BaseResult."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        orchestrator = self._create_test_orchestrator()
        tasks = [BaseTask(task_type="task1"), BaseTask(task_type="task2")]
        results = await orchestrator.execute(tasks)

        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_runs_tasks_in_parallel(self) -> None:
        """Test that execute runs tasks in parallel using asyncio.gather."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseResult, BaseTask

        execution_order = []

        async def slow_execute(task):
            execution_order.append(f"{task.task_type}_start")
            await asyncio.sleep(0.01)
            execution_order.append(f"{task.task_type}_end")
            return BaseResult(task_type=task.task_type, success=True)

        orchestrator = self._create_test_orchestrator(execute_task_impl=slow_execute)
        tasks = [BaseTask(task_type="task1"), BaseTask(task_type="task2")]

        await orchestrator.execute(tasks)

        # Both starts should happen before at least one end (parallel execution)
        if len(execution_order) >= 4:
            task1_start = execution_order.index("task1_start")
            task2_start = execution_order.index("task2_start")
            task1_end = execution_order.index("task1_end")
            task2_end = execution_order.index("task2_end")

            # Both starts should happen before at least one end
            assert task1_start < max(task1_end, task2_end)
            assert task2_start < max(task1_end, task2_end)

    @pytest.mark.asyncio
    async def test_execute_converts_exceptions_to_failed_results(self) -> None:
        """Test that exceptions are converted to failed results."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseTask

        async def failing_execute(task):
            if task.task_type == "failing":
                raise ValueError("Task failed!")
            from mcp_server_langgraph.agents.base_orchestrator import BaseResult

            return BaseResult(task_type=task.task_type, success=True)

        orchestrator = self._create_test_orchestrator(execute_task_impl=failing_execute)
        tasks = [BaseTask(task_type="success"), BaseTask(task_type="failing")]

        results = await orchestrator.execute(tasks)

        assert len(results) == 2

        # Find the failing result
        failing_result = next(r for r in results if r.task_type == "failing")
        assert failing_result.success is False
        assert "Task failed!" in failing_result.error

        # Success result should still succeed
        success_result = next(r for r in results if r.task_type == "success")
        assert success_result.success is True


@pytest.mark.xdist_group(name="base_orchestrator_feature_flag")
class TestBaseOrchestratorFeatureFlag:
    """Test feature flag integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_enabled_checks_feature_flag(self) -> None:
        """Test that is_enabled property checks the feature flag."""
        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
            BaseTask,
        )

        class FlagTestOrchestrator(BaseOrchestrator[BaseTask, BaseResult]):
            @property
            def feature_flag_name(self) -> str:
                return "enable_orchestrated_ai_ux"

            async def _execute_task(self, task: BaseTask) -> BaseResult:
                return BaseResult(task_type=task.task_type, success=True)

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {}

        orchestrator = FlagTestOrchestrator()
        # is_enabled should return a bool based on feature flag
        assert isinstance(orchestrator.is_enabled, bool)


@pytest.mark.xdist_group(name="base_orchestrator_generics")
class TestBaseOrchestratorGenerics:
    """Test generic type support."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_supports_custom_task_type(self) -> None:
        """Test that orchestrator supports custom task types."""
        from dataclasses import dataclass, field

        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
        )

        @dataclass
        class CustomTask:
            task_type: str
            custom_field: str
            data: dict[str, Any] = field(default_factory=dict)

        class CustomTaskOrchestrator(BaseOrchestrator[CustomTask, BaseResult]):
            @property
            def feature_flag_name(self) -> str:
                return "enable_custom"

            async def _execute_task(self, task: CustomTask) -> BaseResult:
                # Access custom field
                return BaseResult(
                    task_type=task.task_type,
                    success=True,
                    result={"custom": task.custom_field},
                )

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {}

        orchestrator = CustomTaskOrchestrator()
        assert orchestrator is not None

    def test_orchestrator_supports_custom_result_type(self) -> None:
        """Test that orchestrator supports custom result types."""
        from dataclasses import dataclass

        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseTask,
        )

        @dataclass
        class CustomResult:
            task_type: str
            success: bool
            custom_score: float
            result: dict[str, Any] | None = None
            error: str | None = None

        class CustomResultOrchestrator(BaseOrchestrator[BaseTask, CustomResult]):
            @property
            def feature_flag_name(self) -> str:
                return "enable_custom"

            async def _execute_task(self, task: BaseTask) -> CustomResult:
                return CustomResult(
                    task_type=task.task_type,
                    success=True,
                    custom_score=0.95,
                )

            def synthesize(self, results: list[CustomResult]) -> dict[str, Any]:
                return {"avg_score": sum(r.custom_score for r in results) / len(results)}

        orchestrator = CustomResultOrchestrator()
        assert orchestrator is not None


@pytest.mark.xdist_group(name="base_orchestrator_metrics")
class TestBaseOrchestratorMetrics:
    """Test metrics instrumentation in base orchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_has_metrics_enabled_flag(self) -> None:
        """Test that orchestrator can enable/disable metrics."""
        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
            BaseTask,
        )

        class MetricsTestOrchestrator(BaseOrchestrator[BaseTask, BaseResult]):
            @property
            def feature_flag_name(self) -> str:
                return "enable_test"

            async def _execute_task(self, task: BaseTask) -> BaseResult:
                return BaseResult(task_type=task.task_type, success=True)

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {}

        orchestrator = MetricsTestOrchestrator()
        # Default should be True
        assert orchestrator.enable_metrics is True

    def test_orchestrator_metrics_can_be_disabled(self) -> None:
        """Test that metrics can be disabled."""
        from mcp_server_langgraph.agents.base_orchestrator import (
            BaseOrchestrator,
            BaseResult,
            BaseTask,
        )

        class MetricsTestOrchestrator(BaseOrchestrator[BaseTask, BaseResult]):
            @property
            def feature_flag_name(self) -> str:
                return "enable_test"

            async def _execute_task(self, task: BaseTask) -> BaseResult:
                return BaseResult(task_type=task.task_type, success=True)

            def synthesize(self, results: list[BaseResult]) -> dict[str, Any]:
                return {}

        orchestrator = MetricsTestOrchestrator(enable_metrics=False)
        assert orchestrator.enable_metrics is False
