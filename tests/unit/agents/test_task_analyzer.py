"""Tests for TaskAnalyzer heuristics.

TDD: These tests define the contract for the TaskAnalyzer that provides
heuristics for analyzing tasks to help determine execution mode.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestTaskAnalyzerBasic:
    """Tests for TaskAnalyzer basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_task_analyzer_exists(self) -> None:
        """Test TaskAnalyzer class exists."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        assert TaskAnalyzer is not None

    def test_task_analyzer_has_analyze_method(self) -> None:
        """Test TaskAnalyzer has analyze method."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        assert hasattr(analyzer, "analyze")

    def test_analyze_returns_task_analysis(self) -> None:
        """Test analyze returns TaskAnalysis dataclass."""
        from mcp_server_langgraph.agents.task_analyzer import (
            TaskAnalysis,
            TaskAnalyzer,
        )

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Write a function to calculate fibonacci")

        assert isinstance(result, TaskAnalysis)


@pytest.mark.unit
class TestTaskAnalyzerComplexity:
    """Tests for TaskAnalyzer complexity detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_simple_task_detection(self) -> None:
        """Test detection of simple tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("What is 2 + 2?")

        assert result.complexity == "simple"

    def test_complicated_task_detection(self) -> None:
        """Test detection of complicated tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Write a REST API endpoint that handles user authentication")

        assert result.complexity == "complicated"

    def test_complex_task_detection(self) -> None:
        """Test detection of complex tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze(
            "Design and implement a distributed caching system with sharding, replication, and automatic failover"
        )

        assert result.complexity == "complex"


@pytest.mark.unit
class TestTaskAnalyzerExploration:
    """Tests for TaskAnalyzer exploration detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exploration_required_for_search_tasks(self) -> None:
        """Test exploration is required for search/find tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Find all files that contain the word 'error'")

        assert result.requires_exploration is True

    def test_exploration_required_for_investigation(self) -> None:
        """Test exploration is required for investigation tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Investigate why the tests are failing")

        assert result.requires_exploration is True

    def test_no_exploration_for_direct_tasks(self) -> None:
        """Test no exploration for direct action tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Create a file named config.json")

        assert result.requires_exploration is False


@pytest.mark.unit
class TestTaskAnalyzerMultiStep:
    """Tests for TaskAnalyzer multi-step detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_multi_step_for_sequential_tasks(self) -> None:
        """Test multi-step detection for sequential tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("First, create a database. Then, add a table. Finally, insert data.")

        assert result.requires_multi_step is True

    def test_multi_step_for_numbered_steps(self) -> None:
        """Test multi-step detection for numbered steps."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("1. Read the file 2. Parse the JSON 3. Extract the values")

        assert result.requires_multi_step is True

    def test_single_step_for_simple_task(self) -> None:
        """Test single step detection for simple tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Print hello world")

        assert result.requires_multi_step is False


@pytest.mark.unit
class TestTaskAnalyzerBatch:
    """Tests for TaskAnalyzer batch processing detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_batch_for_bulk_operations(self) -> None:
        """Test batch detection for bulk operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Update all 500 records in the database")

        assert result.requires_batch_processing is True

    def test_batch_for_multiple_files(self) -> None:
        """Test batch detection for multiple file operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Rename all .txt files to .md files")

        assert result.requires_batch_processing is True

    def test_no_batch_for_single_operation(self) -> None:
        """Test no batch for single operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Create one new file")

        assert result.requires_batch_processing is False


@pytest.mark.unit
class TestTaskAnalyzerRisk:
    """Tests for TaskAnalyzer risk level detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_high_risk_for_delete_operations(self) -> None:
        """Test high risk detection for delete operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Delete all user data from the database")

        assert result.risk_level == "high"

    def test_high_risk_for_production(self) -> None:
        """Test high risk detection for production operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Deploy the application to production")

        assert result.risk_level == "high"

    def test_medium_risk_for_modify_operations(self) -> None:
        """Test medium risk detection for modify operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Update the configuration file")

        assert result.risk_level == "medium"

    def test_low_risk_for_read_operations(self) -> None:
        """Test low risk detection for read operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Read the contents of the log file")

        assert result.risk_level == "low"


@pytest.mark.unit
class TestTaskAnalyzerToolEstimation:
    """Tests for TaskAnalyzer tool count estimation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_estimates_tool_count_for_file_task(self) -> None:
        """Test tool count estimation for file operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Read a file and write the result to another file")

        assert result.estimated_tool_count >= 2

    def test_zero_tools_for_conversational(self) -> None:
        """Test zero tools for conversational tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Explain what a binary tree is")

        assert result.estimated_tool_count == 0

    def test_multiple_tools_for_complex_task(self) -> None:
        """Test multiple tool estimation for complex tasks."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Search for files, read them, parse the content, and save results")

        assert result.estimated_tool_count >= 3


@pytest.mark.unit
class TestTaskAnalyzerApproval:
    """Tests for TaskAnalyzer approval requirement detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_for_irreversible_actions(self) -> None:
        """Test approval required for irreversible actions."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Permanently delete the backup files")

        assert result.requires_approval is True

    def test_approval_for_external_systems(self) -> None:
        """Test approval required for external system changes."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Send an email to all customers")

        assert result.requires_approval is True

    def test_no_approval_for_local_read(self) -> None:
        """Test no approval for local read operations."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("List the files in the directory")

        assert result.requires_approval is False


@pytest.mark.unit
class TestTaskAnalysisDataclass:
    """Tests for TaskAnalysis dataclass structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_task_analysis_has_all_fields(self) -> None:
        """Test TaskAnalysis has all required fields."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalysis

        analysis = TaskAnalysis(
            complexity="complicated",
            risk_level="medium",
            requires_exploration=False,
            requires_multi_step=False,
            requires_batch_processing=False,
            requires_approval=False,
            estimated_tool_count=2,
            suggested_execution_mode="tool_calling",
        )

        assert analysis.complexity == "complicated"
        assert analysis.risk_level == "medium"
        assert analysis.requires_exploration is False
        assert analysis.requires_multi_step is False
        assert analysis.requires_batch_processing is False
        assert analysis.requires_approval is False
        assert analysis.estimated_tool_count == 2
        assert analysis.suggested_execution_mode == "tool_calling"

    def test_task_analysis_has_suggested_execution_mode(self) -> None:
        """Test TaskAnalysis includes suggested execution mode."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        result = analyzer.analyze("Search for files matching pattern")

        assert hasattr(result, "suggested_execution_mode")
        assert result.suggested_execution_mode in [
            "pure_llm",
            "tool_calling",
            "react",
            "programmatic",
            "orchestrator",
        ]
