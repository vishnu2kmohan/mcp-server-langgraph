"""
E2E tests for complete skill lifecycle.

Tests the full flow: install → index → search → uninstall → verify de-indexed

TDD Cycle: RED -> GREEN -> REFACTOR

Test Categories:
----------------
1. Install: Skill is installed and indexed for semantic search
2. Search: Installed skill is discoverable via semantic search
3. Uninstall: Skill is removed and de-indexed
4. Verification: De-indexed skill is no longer searchable

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.skills: Skills system tests
- @pytest.mark.e2e: End-to-end lifecycle tests

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
               adr/adr-0099-semantic-tool-selection.md
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import SkillSearchTool

# Module-level markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skills,
    pytest.mark.xdist_group(name="skill_lifecycle_e2e"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


class MockVectorProvider:
    """Mock vector provider for E2E tests without real Qdrant.

    Provides in-memory vector storage for testing the full lifecycle
    without requiring infrastructure dependencies.
    """

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, dict]] = {}  # collection -> id -> data

    async def upsert(
        self,
        *,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict | None = None,
    ) -> None:
        """Store a vector in memory."""
        if collection not in self._storage:
            self._storage[collection] = {}
        self._storage[collection][id] = {
            "id": id,
            "vector": vector,
            "metadata": metadata or {},
        }

    async def search(
        self,
        *,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search vectors with simple cosine-like scoring."""
        if collection not in self._storage:
            return []

        results = []
        for doc_id, data in self._storage[collection].items():
            # Simple dot product score (normalized vectors assumed)
            score = sum(a * b for a, b in zip(query_vector[:10], data["vector"][:10], strict=False))
            if score >= min_score:
                results.append(
                    {
                        "id": doc_id,
                        "score": score,
                        "metadata": data["metadata"],
                    }
                )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def delete(
        self,
        *,
        collection: str,
        id: str,
    ) -> bool:
        """Delete a vector from memory."""
        if collection in self._storage and id in self._storage[collection]:
            del self._storage[collection][id]
            return True
        return False

    def count(self, collection: str) -> int:
        """Count vectors in collection."""
        return len(self._storage.get(collection, {}))


class MockEmbeddingService:
    """Mock embedding service for E2E tests.

    Produces deterministic vectors based on text content.
    """

    def __init__(self, vector_size: int = 768) -> None:
        self.vector_size = vector_size

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding from text."""
        # Create sparse vector with non-zero values for word overlap
        vector = [0.0] * self.vector_size
        for i, word in enumerate(text.lower().split()[:10]):
            word_hash = hash(word)
            idx = word_hash % self.vector_size
            vector[idx] = 0.1 * (i + 1)
        return vector


@pytest.fixture
def temp_install_path(tmp_path: Path) -> Path:
    """Create temporary skill installation directory."""
    install_path = tmp_path / "skills"
    install_path.mkdir(parents=True)
    return install_path
    # Cleanup handled by tmp_path fixture


@pytest.fixture
def mock_vector_provider() -> MockVectorProvider:
    """Create mock vector provider."""
    return MockVectorProvider()


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """Create mock embedding service."""
    return MockEmbeddingService()


@pytest.fixture
def skill_search_tool(
    mock_vector_provider: MockVectorProvider,
    mock_embedding_service: MockEmbeddingService,
) -> SkillSearchTool:
    """Create SkillSearchTool with mock providers."""
    from mcp_server_langgraph.skills.search import SkillSearchTool

    return SkillSearchTool(
        vector_provider=mock_vector_provider,
        embedding_service=mock_embedding_service,
    )


class TestSkillLifecycleE2E:
    """E2E tests for complete skill lifecycle."""

    @pytest.mark.asyncio
    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    async def test_install_indexes_skill_for_search(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
        mock_vector_provider: MockVectorProvider,
    ) -> None:
        """
        GIVEN: SkillInstaller with skill_search_tool configured
        WHEN: Installing a skill
        THEN: Skill should be indexed and searchable

        Tests Phase 1 of lifecycle: Install → Index
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        # Create installer with search tool
        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # Mock marketplace fetch
        mock_skill_data = {
            "content": "# Code Review\n\nReview code for quality and best practices.",
            "description": "Review code for quality, bugs, and best practices",
            "tags": ["code", "review", "quality"],
            "dependencies": [],
        }

        with MagicMock():
            installer._fetch_skill_from_marketplace = AsyncMock(return_value=mock_skill_data)

            # Install the skill
            result = await installer.install("code-review", source="test-marketplace")

            # Verify installation succeeded
            assert result.success is True
            assert result.skill_name == "code-review"

            # Verify skill was indexed
            assert mock_vector_provider.count("skills") == 1

    @pytest.mark.asyncio
    async def test_installed_skill_is_searchable(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
    ) -> None:
        """
        GIVEN: A skill has been installed and indexed
        WHEN: Searching with related query
        THEN: Skill should be found in search results

        Tests Phase 2 of lifecycle: Search
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        # Create installer with search tool
        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # Mock marketplace fetch for installation
        mock_skill_data = {
            "content": "# Test Generator\n\nGenerate unit tests for Python code.",
            "description": "Generate unit tests for Python code",
            "tags": ["testing", "python", "automation"],
            "dependencies": [],
        }

        installer._fetch_skill_from_marketplace = AsyncMock(return_value=mock_skill_data)

        # Install the skill
        await installer.install("test-generator", source="test-marketplace")

        # Search for the skill using related query
        results = await skill_search_tool.search("unit tests python", limit=5)

        # Verify skill is found
        assert len(results) >= 1
        skill_ids = [r.skill_id for r in results]
        assert "test-generator" in skill_ids

    @pytest.mark.asyncio
    async def test_uninstall_removes_skill_from_search_index(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
        mock_vector_provider: MockVectorProvider,
    ) -> None:
        """
        GIVEN: A skill has been installed and indexed
        WHEN: Uninstalling the skill
        THEN: Skill should be removed from search index

        Tests Phase 3 of lifecycle: Uninstall → De-index
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        # Create installer with search tool
        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # Mock marketplace fetch
        mock_skill_data = {
            "content": "# API Documentation\n\nGenerate API documentation.",
            "description": "Generate API documentation automatically",
            "tags": ["docs", "api", "automation"],
            "dependencies": [],
        }

        installer._fetch_skill_from_marketplace = AsyncMock(return_value=mock_skill_data)

        # Install the skill
        await installer.install("api-docs", source="test-marketplace")

        # Verify skill was indexed
        assert mock_vector_provider.count("skills") == 1

        # Uninstall the skill
        result = await installer.uninstall("api-docs")

        # Verify uninstall succeeded
        assert result is True

        # Verify skill was de-indexed
        assert mock_vector_provider.count("skills") == 0

    @pytest.mark.asyncio
    async def test_uninstalled_skill_not_searchable(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
    ) -> None:
        """
        GIVEN: A skill was installed then uninstalled
        WHEN: Searching for the skill
        THEN: Skill should not appear in search results

        Tests Phase 4 of lifecycle: Verify de-indexed
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        # Create installer with search tool
        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # Mock marketplace fetch
        mock_skill_data = {
            "content": "# Security Scanner\n\nScan code for security vulnerabilities.",
            "description": "Scan code for security vulnerabilities and issues",
            "tags": ["security", "scanning", "vulnerabilities"],
            "dependencies": [],
        }

        installer._fetch_skill_from_marketplace = AsyncMock(return_value=mock_skill_data)

        # Install the skill
        await installer.install("security-scanner", source="test-marketplace")

        # Verify searchable after install
        results_before = await skill_search_tool.search("security scan vulnerabilities", limit=5)
        assert any(r.skill_id == "security-scanner" for r in results_before)

        # Uninstall the skill
        await installer.uninstall("security-scanner")

        # Verify NOT searchable after uninstall
        results_after = await skill_search_tool.search("security scan vulnerabilities", limit=5)
        assert not any(r.skill_id == "security-scanner" for r in results_after)

    @pytest.mark.asyncio
    async def test_full_lifecycle_install_search_uninstall(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
        mock_vector_provider: MockVectorProvider,
    ) -> None:
        """
        GIVEN: Fresh installation environment
        WHEN: Full lifecycle: install → search → uninstall
        THEN: All phases should work correctly

        Tests complete E2E lifecycle in single test.
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # === PHASE 1: INSTALL ===
        mock_skill_data = {
            "content": "# Database Migration\n\nManage database schema migrations.",
            "description": "Manage and run database schema migrations safely",
            "tags": ["database", "migration", "schema"],
            "dependencies": [],
        }

        installer._fetch_skill_from_marketplace = AsyncMock(return_value=mock_skill_data)

        install_result = await installer.install("db-migrate", source="test-marketplace")
        assert install_result.success is True
        assert mock_vector_provider.count("skills") == 1

        # === PHASE 2: SEARCH ===
        search_results = await skill_search_tool.search("database migration schema", limit=10)
        assert len(search_results) >= 1
        assert any(r.skill_id == "db-migrate" for r in search_results)

        # === PHASE 3: UNINSTALL ===
        uninstall_result = await installer.uninstall("db-migrate")
        assert uninstall_result is True
        assert mock_vector_provider.count("skills") == 0

        # === PHASE 4: VERIFY DE-INDEXED ===
        post_uninstall_results = await skill_search_tool.search("database migration", limit=10)
        assert not any(r.skill_id == "db-migrate" for r in post_uninstall_results)

    @pytest.mark.asyncio
    async def test_multiple_skills_lifecycle(
        self,
        temp_install_path: Path,
        skill_search_tool: SkillSearchTool,
        mock_vector_provider: MockVectorProvider,
    ) -> None:
        """
        GIVEN: Multiple skills to be installed
        WHEN: Installing multiple skills and searching
        THEN: All skills should be indexed and searchable independently

        Tests multi-skill management.
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller(
            install_path=temp_install_path,
            skill_search_tool=skill_search_tool,
        )

        # Define multiple skills
        skills_data = [
            {
                "name": "web-scraper",
                "data": {
                    "content": "# Web Scraper\n\nScrape web pages for data.",
                    "description": "Extract data from web pages and websites",
                    "tags": ["web", "scraping", "data"],
                    "dependencies": [],
                },
            },
            {
                "name": "email-sender",
                "data": {
                    "content": "# Email Sender\n\nSend emails programmatically.",
                    "description": "Send emails with templates and attachments",
                    "tags": ["email", "notification", "communication"],
                    "dependencies": [],
                },
            },
            {
                "name": "pdf-generator",
                "data": {
                    "content": "# PDF Generator\n\nGenerate PDF documents.",
                    "description": "Create PDF documents from templates",
                    "tags": ["pdf", "documents", "generation"],
                    "dependencies": [],
                },
            },
        ]

        # Install all skills
        for skill_info in skills_data:
            installer._fetch_skill_from_marketplace = AsyncMock(return_value=skill_info["data"])
            result = await installer.install(skill_info["name"], source="test-marketplace")
            assert result.success is True

        # Verify all indexed
        assert mock_vector_provider.count("skills") == 3

        # Search should find relevant skills
        web_results = await skill_search_tool.search("web data extraction", limit=5)
        assert any(r.skill_id == "web-scraper" for r in web_results)

        email_results = await skill_search_tool.search("email notification", limit=5)
        assert any(r.skill_id == "email-sender" for r in email_results)

        # Uninstall one skill
        await installer.uninstall("email-sender")
        assert mock_vector_provider.count("skills") == 2

        # Verify uninstalled skill not searchable
        post_uninstall = await skill_search_tool.search("email notification", limit=5)
        assert not any(r.skill_id == "email-sender" for r in post_uninstall)

        # Other skills still searchable
        web_results_post = await skill_search_tool.search("web data extraction", limit=5)
        assert any(r.skill_id == "web-scraper" for r in web_results_post)
