"""
TDD: Unit tests for Background Agents API endpoints.

Tests that background agent management endpoints work correctly
for submitting, querying, and canceling background tasks.

Phase 3.2: canvas_agents feature flag
- POST /api/v1/agents/background - Submit background task
- GET /api/v1/agents/background - List background tasks
- GET /api/v1/agents/background/{id} - Get task status
- DELETE /api/v1/agents/background/{id} - Cancel task

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.background_agents]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags with canvas_agents enabled."""
    mock_flags = MagicMock()
    mock_flags.canvas_agents = True
    return mock_flags


@pytest.fixture
def sample_task_request():
    """Sample background task request."""
    return {
        "name": "Code Analysis Agent",
        "task": "Analyze code quality in src/ directory",
        "agent_type": "code_analysis",
        "data": {"directory": "src/", "depth": 3},
    }


# =============================================================================
# Submit Background Task Tests
# =============================================================================


class TestSubmitBackgroundTask:
    """Test POST /api/v1/agents/background endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_submit_task_request_model_validation(self, sample_task_request: dict) -> None:
        """GIVEN valid request data WHEN create model THEN succeeds."""
        from mcp_server_langgraph.api.v1.background_agents import BackgroundTaskRequest

        request = BackgroundTaskRequest(**sample_task_request)

        assert request.name == "Code Analysis Agent"
        assert request.task == "Analyze code quality in src/ directory"
        assert request.agent_type == "code_analysis"

    def test_submit_task_response_model_structure(self) -> None:
        """GIVEN response data WHEN create model THEN has required fields."""
        from mcp_server_langgraph.api.v1.background_agents import BackgroundTaskResponse

        response = BackgroundTaskResponse(
            id="task-123",
            name="Code Analysis Agent",
            task="Analyze code",
            status="queued",
            progress=0,
            started_at=1704067200000,
        )

        assert response.id == "task-123"
        assert response.status == "queued"
        assert response.progress == 0

    @pytest.mark.asyncio
    async def test_submit_task_creates_agent(self, mock_feature_flags: MagicMock, sample_task_request: dict) -> None:
        """GIVEN valid request WHEN POST submit THEN creates agent task."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            submit_background_task,
            BackgroundTaskRequest,
        )

        request = BackgroundTaskRequest(**sample_task_request)

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            result = await submit_background_task(request, current_user={"sub": "user-123"})

        assert result.id is not None
        assert result.status in ("queued", "running")
        assert result.name == "Code Analysis Agent"

    @pytest.mark.asyncio
    async def test_submit_task_returns_task_id(self, mock_feature_flags: MagicMock, sample_task_request: dict) -> None:
        """GIVEN valid request WHEN POST submit THEN returns unique task ID."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            submit_background_task,
            BackgroundTaskRequest,
        )

        request = BackgroundTaskRequest(**sample_task_request)

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            result1 = await submit_background_task(request, current_user={"sub": "user-123"})
            result2 = await submit_background_task(request, current_user={"sub": "user-123"})

        assert result1.id != result2.id


# =============================================================================
# List Background Tasks Tests
# =============================================================================


class TestListBackgroundTasks:
    """Test GET /api/v1/agents/background endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_tasks_returns_array(self, mock_feature_flags: MagicMock) -> None:
        """GIVEN tasks exist WHEN GET list THEN returns task array."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import list_background_tasks

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            result = await list_background_tasks(current_user={"sub": "user-123"})

        assert isinstance(result.tasks, list)

    @pytest.mark.asyncio
    async def test_list_tasks_includes_status(self, mock_feature_flags: MagicMock) -> None:
        """GIVEN tasks exist WHEN GET list THEN each has status field."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            list_background_tasks,
            submit_background_task,
            BackgroundTaskRequest,
        )

        request = BackgroundTaskRequest(
            name="Test Agent",
            task="Test task",
            agent_type="test",
        )

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            await submit_background_task(request, current_user={"sub": "user-123"})
            result = await list_background_tasks(current_user={"sub": "user-123"})

        # At least one task should have a status
        if result.tasks:
            assert result.tasks[0].status in (
                "queued",
                "running",
                "completed",
                "failed",
                "awaiting_approval",
                "awaiting_clarification",
            )


# =============================================================================
# Get Task Status Tests
# =============================================================================


class TestGetTaskStatus:
    """Test GET /api/v1/agents/background/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, mock_feature_flags: MagicMock, sample_task_request: dict) -> None:
        """GIVEN task exists WHEN GET by ID THEN returns task."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            get_background_task,
            submit_background_task,
            BackgroundTaskRequest,
        )

        request = BackgroundTaskRequest(**sample_task_request)

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            created = await submit_background_task(request, current_user={"sub": "user-123"})
            result = await get_background_task(created.id, current_user={"sub": "user-123"})

        assert result.id == created.id
        assert result.name == "Code Analysis Agent"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_returns_none(self, mock_feature_flags: MagicMock) -> None:
        """GIVEN task doesn't exist WHEN GET by ID THEN returns None."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import get_background_task

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            result = await get_background_task("nonexistent-id", current_user={"sub": "user-123"})

        assert result is None


# =============================================================================
# Cancel Task Tests
# =============================================================================


class TestCancelTask:
    """Test DELETE /api/v1/agents/background/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cancel_queued_task(self, mock_feature_flags: MagicMock, sample_task_request: dict) -> None:
        """GIVEN queued task WHEN DELETE THEN cancels task."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            cancel_background_task,
            submit_background_task,
            BackgroundTaskRequest,
        )

        request = BackgroundTaskRequest(**sample_task_request)

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            created = await submit_background_task(request, current_user={"sub": "user-123"})
            result = await cancel_background_task(created.id, current_user={"sub": "user-123"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task_fails(self, mock_feature_flags: MagicMock) -> None:
        """GIVEN task doesn't exist WHEN DELETE THEN returns failure."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import cancel_background_task

        with patch.object(bg_agents_module, "feature_flags", mock_feature_flags):
            result = await cancel_background_task("nonexistent-id", current_user={"sub": "user-123"})

        assert result.success is False


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestBackgroundAgentsFeatureFlag:
    """Test feature flag gating for background agents endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_submit_respects_feature_flag(self, sample_task_request: dict) -> None:
        """GIVEN feature flag disabled WHEN POST submit THEN returns fallback."""
        from mcp_server_langgraph.api.v1 import background_agents as bg_agents_module
        from mcp_server_langgraph.api.v1.background_agents import (
            submit_background_task,
            BackgroundTaskRequest,
        )

        mock_flags = MagicMock()
        mock_flags.canvas_agents = False

        request = BackgroundTaskRequest(**sample_task_request)

        with patch.object(bg_agents_module, "feature_flags", mock_flags):
            result = await submit_background_task(request, current_user={"sub": "user-123"})

        # Should still return valid response (graceful degradation)
        assert result is not None
        assert result.status == "disabled"
