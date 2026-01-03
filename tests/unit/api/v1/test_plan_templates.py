"""
Tests for Plan Templates API Endpoints

TDD: These tests define the contract for plan template CRUD and search endpoints.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="plan_templates_api")
class TestPlanTemplatesAPIRouter:
    """Tests for plan templates API router."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_templates_router_exists(self) -> None:
        """Test that plan_templates_router exists."""
        from mcp_server_langgraph.api.v1.plan_templates import plan_templates_router

        assert plan_templates_router is not None

    def test_router_has_correct_tags(self) -> None:
        """Test router has correct OpenAPI tags."""
        from mcp_server_langgraph.api.v1.plan_templates import plan_templates_router

        assert "plan-templates" in plan_templates_router.tags


@pytest.mark.xdist_group(name="plan_templates_list")
class TestListTemplatesEndpoint:
    """Tests for list templates endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_templates_returns_list(self) -> None:
        """Test list templates returns a list."""
        from mcp_server_langgraph.api.v1.plan_templates import list_templates

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = []

        result = await list_templates(
            limit=10,
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_templates_respects_limit(self) -> None:
        """Test list templates respects limit parameter."""
        from mcp_server_langgraph.api.v1.plan_templates import list_templates

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = []

        await list_templates(
            limit=5,
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        mock_repo.list_all.assert_called_once_with(limit=5)


@pytest.mark.xdist_group(name="plan_templates_get")
class TestGetTemplateEndpoint:
    """Tests for get template endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_template_returns_template(self) -> None:
        """Test get template returns template data."""
        from mcp_server_langgraph.api.v1.plan_templates import get_template
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        mock_template = PlanTemplate(
            template_id="tmpl-123",
            name="Test Template",
            description="Test description",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user@example.com",
        )
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_template

        result = await get_template(
            template_id="tmpl-123",
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert result["template_id"] == "tmpl-123"
        assert result["name"] == "Test Template"

    @pytest.mark.asyncio
    async def test_get_template_not_found_raises_404(self) -> None:
        """Test get template raises 404 when not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.plan_templates import get_template

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_template(
                template_id="nonexistent",
                template_repo=mock_repo,
                current_user=MagicMock(email="test@example.com"),
            )

        assert exc_info.value.status_code == 404


@pytest.mark.xdist_group(name="plan_templates_create")
class TestCreateTemplateEndpoint:
    """Tests for create template endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        """Test creating a new template."""
        from mcp_server_langgraph.api.v1.plan_templates import (
            CreateTemplateRequest,
            create_template,
        )
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        mock_repo = AsyncMock()
        mock_repo.create.return_value = PlanTemplate(
            template_id="tmpl-new",
            name="New Template",
            description="New description",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user@example.com",
        )

        request = CreateTemplateRequest(
            name="New Template",
            description="New description",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            tags=["test"],
        )

        result = await create_template(
            request=request,
            template_repo=mock_repo,
            current_user=MagicMock(email="user@example.com"),
        )

        assert result["name"] == "New Template"
        mock_repo.create.assert_called_once()


@pytest.mark.xdist_group(name="plan_templates_delete")
class TestDeleteTemplateEndpoint:
    """Tests for delete template endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        """Test deleting a template."""
        from mcp_server_langgraph.api.v1.plan_templates import delete_template

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = True

        result = await delete_template(
            template_id="tmpl-123",
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found_raises_404(self) -> None:
        """Test delete raises 404 when template not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.plan_templates import delete_template

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_template(
                template_id="nonexistent",
                template_repo=mock_repo,
                current_user=MagicMock(email="test@example.com"),
            )

        assert exc_info.value.status_code == 404


@pytest.mark.xdist_group(name="plan_templates_search")
class TestSearchTemplatesEndpoint:
    """Tests for search templates endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_by_tags(self) -> None:
        """Test searching templates by tags."""
        from mcp_server_langgraph.api.v1.plan_templates import search_templates
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        mock_template = PlanTemplate(
            template_id="tmpl-123",
            name="Code Review",
            description="Review code",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user@example.com",
            tags=["code", "review"],
        )
        mock_repo = AsyncMock()
        mock_repo.find_by_tags.return_value = [mock_template]

        result = await search_templates(
            tags="code,review",
            orchestrator=None,
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert len(result) == 1
        assert result[0]["template_id"] == "tmpl-123"

    @pytest.mark.asyncio
    async def test_search_by_orchestrator(self) -> None:
        """Test searching templates by orchestrator type."""
        from mcp_server_langgraph.api.v1.plan_templates import search_templates
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        mock_template = PlanTemplate(
            template_id="tmpl-123",
            name="Swarm Template",
            description="Uses swarm",
            orchestrator="swarm",
            thinking_budget="deep",
            critique_rounds=2,
            auto_approve=False,
            created_by="user@example.com",
        )
        mock_repo = AsyncMock()
        mock_repo.find_by_orchestrator.return_value = [mock_template]

        result = await search_templates(
            tags=None,
            orchestrator="swarm",
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert len(result) == 1
        assert result[0]["orchestrator"] == "swarm"


@pytest.mark.xdist_group(name="plan_templates_record_usage")
class TestRecordUsageEndpoint:
    """Tests for record usage endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_successful_usage(self) -> None:
        """Test recording successful template usage."""
        from mcp_server_langgraph.api.v1.plan_templates import (
            RecordUsageRequest,
            record_usage,
        )

        mock_repo = AsyncMock()

        result = await record_usage(
            template_id="tmpl-123",
            request=RecordUsageRequest(success=True),
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        assert result["recorded"] is True
        mock_repo.record_usage.assert_called_once_with("tmpl-123", success=True)

    @pytest.mark.asyncio
    async def test_record_failed_usage(self) -> None:
        """Test recording failed template usage."""
        from mcp_server_langgraph.api.v1.plan_templates import (
            RecordUsageRequest,
            record_usage,
        )

        mock_repo = AsyncMock()

        await record_usage(
            template_id="tmpl-123",
            request=RecordUsageRequest(success=False),
            template_repo=mock_repo,
            current_user=MagicMock(email="test@example.com"),
        )

        mock_repo.record_usage.assert_called_once_with("tmpl-123", success=False)
