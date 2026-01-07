"""
Tests for PlanTemplateRepository

TDD: These tests define the contract for plan template storage with semantic search.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.plan_template import PlanTemplate


@pytest.mark.xdist_group(name="plan_template_repository")
class TestPlanTemplateRepositoryContract:
    """Tests for PlanTemplateRepository abstract contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_template_repository_exists(self) -> None:
        """Test that PlanTemplateRepository class exists."""
        from mcp_server_langgraph.repositories.plan_template import (
            PlanTemplateRepository,
        )

        assert PlanTemplateRepository is not None

    def test_plan_template_repository_is_abstract(self) -> None:
        """Test PlanTemplateRepository cannot be instantiated directly."""
        from mcp_server_langgraph.repositories.plan_template import (
            PlanTemplateRepository,
        )

        with pytest.raises(TypeError):
            PlanTemplateRepository()  # type: ignore[abstract]


@pytest.mark.xdist_group(name="inmemory_plan_template_repository")
class TestInMemoryPlanTemplateRepository:
    """Tests for InMemoryPlanTemplateRepository implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_sample_template(
        self,
        template_id: str = "tmpl-123",
        name: str = "Code Review Template",
    ) -> "PlanTemplate":
        """Create a sample template for testing."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        return PlanTemplate(
            template_id=template_id,
            name=name,
            description="Template for code review tasks",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user-456",
            tags=["code", "review"],
        )

    def test_inmemory_repository_exists(self) -> None:
        """Test that InMemoryPlanTemplateRepository class exists."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        assert InMemoryPlanTemplateRepository is not None

    @pytest.mark.asyncio
    async def test_create_template(self) -> None:
        """Test creating a template."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()

        result = await repo.create(template)

        assert result.template_id == "tmpl-123"
        assert result.name == "Code Review Template"

    @pytest.mark.asyncio
    async def test_get_template(self) -> None:
        """Test retrieving a template by ID."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()
        await repo.create(template)

        result = await repo.get("tmpl-123")

        assert result is not None
        assert result.template_id == "tmpl-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self) -> None:
        """Test retrieving a non-existent template returns None."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        result = await repo.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_template(self) -> None:
        """Test updating a template."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()
        await repo.create(template)

        updated = template.model_copy(update={"name": "Updated Template"})
        result = await repo.update(updated)

        assert result.name == "Updated Template"

        # Verify persistence
        fetched = await repo.get("tmpl-123")
        assert fetched is not None
        assert fetched.name == "Updated Template"

    @pytest.mark.asyncio
    async def test_delete_template(self) -> None:
        """Test deleting a template."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()
        await repo.create(template)

        result = await repo.delete("tmpl-123")

        assert result is True
        assert await repo.get("tmpl-123") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_template(self) -> None:
        """Test deleting a non-existent template returns False."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        result = await repo.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_templates(self) -> None:
        """Test listing all templates."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        await repo.create(self._create_sample_template("tmpl-1", "Template 1"))
        await repo.create(self._create_sample_template("tmpl-2", "Template 2"))
        await repo.create(self._create_sample_template("tmpl-3", "Template 3"))

        result = await repo.list_all()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_templates_with_limit(self) -> None:
        """Test listing templates with limit."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        await repo.create(self._create_sample_template("tmpl-1", "Template 1"))
        await repo.create(self._create_sample_template("tmpl-2", "Template 2"))
        await repo.create(self._create_sample_template("tmpl-3", "Template 3"))

        result = await repo.list_all(limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_by_tags(self) -> None:
        """Test finding templates by tags."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Create templates with different tags
        template1 = PlanTemplate(
            template_id="tmpl-1",
            name="Code Review",
            description="Review code",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user",
            tags=["code", "review"],
        )
        template2 = PlanTemplate(
            template_id="tmpl-2",
            name="Data Analysis",
            description="Analyze data",
            orchestrator="swarm",
            thinking_budget="deep",
            critique_rounds=2,
            auto_approve=False,
            created_by="user",
            tags=["data", "analysis"],
        )
        await repo.create(template1)
        await repo.create(template2)

        result = await repo.find_by_tags(["code"])

        assert len(result) == 1
        assert result[0].template_id == "tmpl-1"

    @pytest.mark.asyncio
    async def test_find_by_orchestrator(self) -> None:
        """Test finding templates by orchestrator type."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Create templates with different orchestrators
        template1 = PlanTemplate(
            template_id="tmpl-1",
            name="Standard Template",
            description="Standard",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user",
        )
        template2 = PlanTemplate(
            template_id="tmpl-2",
            name="Swarm Template",
            description="Swarm",
            orchestrator="swarm",
            thinking_budget="deep",
            critique_rounds=2,
            auto_approve=False,
            created_by="user",
        )
        await repo.create(template1)
        await repo.create(template2)

        result = await repo.find_by_orchestrator("swarm")

        assert len(result) == 1
        assert result[0].template_id == "tmpl-2"

    @pytest.mark.asyncio
    async def test_increment_use_count(self) -> None:
        """Test incrementing template use count."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()
        await repo.create(template)

        await repo.record_usage("tmpl-123", success=True)

        fetched = await repo.get("tmpl-123")
        assert fetched is not None
        assert fetched.use_count == 1
        assert fetched.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_record_failed_usage(self) -> None:
        """Test recording failed template usage."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()
        template = self._create_sample_template()
        await repo.create(template)

        await repo.record_usage("tmpl-123", success=True)
        await repo.record_usage("tmpl-123", success=False)

        fetched = await repo.get("tmpl-123")
        assert fetched is not None
        assert fetched.use_count == 2
        assert fetched.success_rate == 0.5


@pytest.mark.xdist_group(name="plan_template_semantic_search")
class TestPlanTemplateSemanticSearch:
    """Tests for semantic search functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_find_similar_requires_embedding(self) -> None:
        """Test finding similar templates requires embeddings."""
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Query with embedding
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = await repo.find_similar(query_embedding, min_similarity=0.5)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_find_similar_returns_matching_templates(self) -> None:
        """Test finding similar templates based on embedding similarity."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Create template with embedding
        template = PlanTemplate(
            template_id="tmpl-1",
            name="Code Review",
            description="Review code changes",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user",
            description_embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        )
        await repo.create(template)

        # Query with similar embedding
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = await repo.find_similar(query_embedding, min_similarity=0.9)

        assert len(result) == 1
        assert result[0].template_id == "tmpl-1"

    @pytest.mark.asyncio
    async def test_find_similar_respects_min_similarity(self) -> None:
        """Test that find_similar respects minimum similarity threshold."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Create template with embedding
        template = PlanTemplate(
            template_id="tmpl-1",
            name="Code Review",
            description="Review code changes",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user",
            description_embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        )
        await repo.create(template)

        # Query with different embedding (low similarity)
        query_embedding = [-0.5, -0.4, -0.3, -0.2, -0.1]
        result = await repo.find_similar(query_embedding, min_similarity=0.9)

        # Should not match due to low similarity
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_similar_respects_limit(self) -> None:
        """Test that find_similar respects result limit."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        repo = InMemoryPlanTemplateRepository()

        # Create multiple templates with similar embeddings
        for i in range(5):
            template = PlanTemplate(
                template_id=f"tmpl-{i}",
                name=f"Template {i}",
                description="Similar template",
                orchestrator="standard",
                thinking_budget="medium",
                critique_rounds=1,
                auto_approve=False,
                created_by="user",
                description_embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            )
            await repo.create(template)

        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = await repo.find_similar(query_embedding, min_similarity=0.9, limit=3)

        assert len(result) == 3
