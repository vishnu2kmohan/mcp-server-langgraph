"""
Unit tests for execution plan repository dependency injection.

Tests the v35.0 RLM execution plan repository DI functions.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.core.dependencies import (
    get_execution_plan_repository,
    reset_singleton_dependencies,
    set_execution_plan_repository,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="execution_plan_dependency")
class TestExecutionPlanRepositoryDI:
    """Tests for execution plan repository dependency injection."""

    def setup_method(self) -> None:
        """Reset singletons before each test."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Reset singletons and force GC after each test."""
        reset_singleton_dependencies()
        gc.collect()

    def test_set_execution_plan_repository_sets_singleton(self) -> None:
        """Test set_execution_plan_repository sets the singleton."""
        mock_repo = MagicMock()

        set_execution_plan_repository(mock_repo)

        result = get_execution_plan_repository()
        assert result is mock_repo

    def test_get_execution_plan_repository_returns_cached(self) -> None:
        """Test get_execution_plan_repository returns cached instance."""
        mock_repo = MagicMock()
        set_execution_plan_repository(mock_repo)

        # Call twice
        result1 = get_execution_plan_repository()
        result2 = get_execution_plan_repository()

        assert result1 is result2
        assert result1 is mock_repo

    def test_reset_singleton_dependencies_clears_execution_plan_repository(
        self,
    ) -> None:
        """Test reset_singleton_dependencies clears the execution plan repository."""
        mock_repo = MagicMock()
        set_execution_plan_repository(mock_repo)

        # Verify it's set
        assert get_execution_plan_repository() is mock_repo

        # Reset
        reset_singleton_dependencies()

        # Now it should create a new instance
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.plan_storage_backend = "memory"
            with patch("mcp_server_langgraph.repositories.execution_plan.get_plan_repository") as mock_get_repo:
                new_repo = MagicMock()
                mock_get_repo.return_value = new_repo

                result = get_execution_plan_repository()
                assert result is new_repo
                assert result is not mock_repo

    def test_get_execution_plan_repository_memory_backend(self) -> None:
        """Test get_execution_plan_repository returns InMemory for memory backend."""
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.plan_storage_backend = "memory"

            with patch("mcp_server_langgraph.repositories.execution_plan.get_plan_repository") as mock_get_repo:
                mock_repo = MagicMock()
                mock_get_repo.return_value = mock_repo

                result = get_execution_plan_repository()

                mock_get_repo.assert_called_once()
                assert result is mock_repo

    def test_get_execution_plan_repository_postgres_backend(self) -> None:
        """Test get_execution_plan_repository returns Postgres for postgres backend."""
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.plan_storage_backend = "postgres"
            mock_settings.database_url = "postgresql+asyncpg://test"

            with patch("mcp_server_langgraph.database.session.get_session_maker") as mock_session_maker:
                mock_factory = MagicMock()
                mock_session_maker.return_value = mock_factory

                with patch(
                    "mcp_server_langgraph.repositories.postgres_execution_plan.PostgresExecutionPlanRepository"
                ) as mock_repo_class:
                    mock_repo = MagicMock()
                    mock_repo_class.return_value = mock_repo

                    result = get_execution_plan_repository()

                    mock_session_maker.assert_called_once_with("postgresql+asyncpg://test")
                    mock_repo_class.assert_called_once_with(mock_factory)
                    assert result is mock_repo

    def test_get_execution_plan_repository_postgres_no_database_url(self) -> None:
        """Test get_execution_plan_repository raises error for postgres without DATABASE_URL."""
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.plan_storage_backend = "postgres"
            mock_settings.database_url = None

            with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
                get_execution_plan_repository()

    def test_get_execution_plan_repository_default_backend(self) -> None:
        """Test get_execution_plan_repository defaults to memory for unknown backend."""
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            # Any value other than "postgres" should use memory backend
            mock_settings.plan_storage_backend = "unknown"

            with patch("mcp_server_langgraph.repositories.execution_plan.get_plan_repository") as mock_get_repo:
                mock_repo = MagicMock()
                mock_get_repo.return_value = mock_repo

                result = get_execution_plan_repository()

                mock_get_repo.assert_called_once()
                assert result is mock_repo
