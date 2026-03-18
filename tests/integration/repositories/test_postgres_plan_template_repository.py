"""
Integration Tests for PostgresPlanTemplateRepository.

Tests the PostgreSQL implementation of the plan template repository
with real database connections and pgvector semantic search.

TDD Approach:
- RED: Tests fail without PostgresPlanTemplateRepository implementation
- GREEN: Tests pass after implementing repository
- REFACTOR: Optimize queries and indexing

Phase 10: Integration Tests for PostgreSQL Persistence
"""

import gc
import socket
import uuid
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from mcp_server_langgraph.core.models.plan_template import PlanTemplate
from tests.constants import (
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

pytestmark = [pytest.mark.integration, pytest.mark.repository]


def create_test_template(
    created_by: str | None = None,
    name: str | None = None,
) -> PlanTemplate:
    """Create a test plan template with minimal required fields."""
    return PlanTemplate(
        template_id=f"tmpl_{uuid.uuid4().hex[:8]}",
        name=name or f"Test Template {uuid.uuid4().hex[:6]}",
        description="Test template description for testing purposes",
        orchestrator="standard",
        thinking_budget="none",
        critique_rounds=0,
        auto_approve=False,
        created_by=created_by or f"user:{uuid.uuid4().hex[:8]}",
        tags=["test", "integration"],
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpostgresplantemplaterepository")
@pytest.mark.skip_isolation_check  # Uses worker-scoped Postgres schemas for isolation
class TestPostgresPlanTemplateRepository:
    """
    Test PostgresPlanTemplateRepository with real PostgreSQL.

    TDD: RED phase - These tests will fail without the repository implementation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    async def async_engine(self) -> AsyncGenerator[AsyncEngine, None]:
        """Create SQLAlchemy async engine for compliance_test database."""
        try:
            with socket.create_connection((TEST_POSTGRES_HOST, TEST_POSTGRES_PORT), timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError):
            pytest.skip(f"PostgreSQL not available at {TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}")

        # Import models to register them with Base.metadata
        import mcp_server_langgraph.database.execution_plan_models  # noqa: F401
        import mcp_server_langgraph.storage.session.postgres_models  # noqa: F401

        compliance_db = "compliance_test"
        database_url = (
            f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
            f"@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{compliance_db}"
        )
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def repo(self, async_engine: AsyncEngine):
        """Create repository with SQLAlchemy async session factory, cleaning plan_templates first."""
        from sqlalchemy import text

        from mcp_server_langgraph.repositories.postgres_plan_template import (
            PostgresPlanTemplateRepository,
        )

        # Clean up leftover data from previous test runs
        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM plan_templates"))

        session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        return PostgresPlanTemplateRepository(session_factory)

    async def test_create_and_get_template(self, repo):
        """Test creating and retrieving a plan template."""
        template = create_test_template()

        # Create
        created = await repo.create(template)
        assert created.template_id == template.template_id

        # Get
        retrieved = await repo.get(template.template_id)
        assert retrieved is not None
        assert retrieved.template_id == template.template_id
        assert retrieved.name == template.name
        assert retrieved.created_by == template.created_by

    async def test_update_template(self, repo):
        """Test updating a plan template."""
        template = create_test_template()
        await repo.create(template)

        # Update
        template = template.model_copy(
            update={
                "name": "Updated Name",
                "description": "Updated description",
            }
        )
        updated = await repo.update(template)

        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    async def test_delete_template(self, repo):
        """Test deleting a plan template."""
        template = create_test_template()
        await repo.create(template)

        # Delete
        result = await repo.delete(template.template_id)
        assert result is True

        # Verify deletion
        retrieved = await repo.get(template.template_id)
        assert retrieved is None

    async def test_list_all(self, repo):
        """Test listing all templates."""
        templates = [create_test_template() for _ in range(3)]
        for template in templates:
            await repo.create(template)

        # List all
        all_templates = await repo.list_all()
        assert len(all_templates) >= 3

    async def test_find_by_tags(self, repo):
        """Test finding templates by tags."""
        # Create templates with specific tags
        template1 = create_test_template()
        template1 = template1.model_copy(update={"tags": ["python", "backend"]})
        await repo.create(template1)

        template2 = create_test_template()
        template2 = template2.model_copy(update={"tags": ["javascript", "frontend"]})
        await repo.create(template2)

        # Find by tags
        python_templates = await repo.find_by_tags(["python"])
        assert len(python_templates) >= 1
        assert any(t.template_id == template1.template_id for t in python_templates)

    async def test_find_by_orchestrator(self, repo):
        """Test finding templates by orchestrator."""
        template = create_test_template()
        template = template.model_copy(update={"orchestrator": "swarm"})
        await repo.create(template)

        # Find by orchestrator
        swarm_templates = await repo.find_by_orchestrator("swarm")
        assert len(swarm_templates) >= 1
        assert any(t.template_id == template.template_id for t in swarm_templates)

    async def test_record_usage(self, repo):
        """Test recording template usage."""
        template = create_test_template()
        await repo.create(template)

        # Record successful usage
        await repo.record_usage(template.template_id, success=True)

        # Verify metrics updated
        updated = await repo.get(template.template_id)
        assert updated.use_count == 1
        assert updated.success_rate == 1.0

        # Record failed usage
        await repo.record_usage(template.template_id, success=False)
        updated = await repo.get(template.template_id)
        assert updated.use_count == 2
        assert updated.success_rate == 0.5

    async def test_list_by_user(self, repo):
        """Test listing templates by user (GDPR export)."""
        user_id = f"user:{uuid.uuid4().hex[:8]}"

        # Create templates for user
        templates = [create_test_template(created_by=user_id) for _ in range(3)]
        for template in templates:
            await repo.create(template)

        # Create template for different user
        other_template = create_test_template()
        await repo.create(other_template)

        # List by user
        user_templates = await repo.list_by_user(user_id)
        assert len(user_templates) == 3
        assert all(t.created_by == user_id for t in user_templates)

    async def test_delete_by_user(self, repo):
        """Test deleting all templates for a user (GDPR deletion)."""
        user_id = f"user:{uuid.uuid4().hex[:8]}"

        # Create templates for user
        templates = [create_test_template(created_by=user_id) for _ in range(3)]
        for template in templates:
            await repo.create(template)

        # Create template for different user
        other_template = create_test_template()
        await repo.create(other_template)

        # Delete by user
        deleted_count = await repo.delete_by_user(user_id)
        assert deleted_count == 3

        # Verify deletion
        user_templates = await repo.list_by_user(user_id)
        assert len(user_templates) == 0

        # Verify other user's template still exists
        retrieved = await repo.get(other_template.template_id)
        assert retrieved is not None

    async def test_search_with_filters(self, repo):
        """Test search with filtering, sorting, and pagination."""
        # Create templates with specific names
        for i in range(5):
            template = create_test_template(name=f"Search Test Template {i}")
            await repo.create(template)

        # Search with query
        results, total = await repo.search(
            filters={"query": "Search Test"},
            sort_field="name",
            sort_order="asc",
            limit=3,
            offset=0,
        )
        assert len(results) <= 3
        assert total >= 5


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testembeddingpipeline")
@pytest.mark.skip_isolation_check
class TestEmbeddingPipeline:
    """
    Test the embedding generation pipeline.

    Verifies that embeddings are generated correctly for plans and templates.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_embedding_dimension_constant(self):
        """Test that EMBEDDING_DIM constant is defined and valid."""
        from mcp_server_langgraph.core.constants import EMBEDDING_DIM

        assert EMBEDDING_DIM == 768

    async def test_assert_embedding_dimension(self):
        """Test embedding dimension assertion helper."""
        from mcp_server_langgraph.core.constants import assert_embedding_dimension

        # Should not raise for correct dimension
        assert_embedding_dimension(768, "test")

        # Should raise for incorrect dimension
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            assert_embedding_dimension(512, "test")
