"""
Vector Search Settings Integration Tests

TDD RED PHASE: Tests for vector_search_provider Settings integration.

These tests verify:
1. Settings has vector_search_provider field
2. get_vector_provider factory respects Settings
3. EmbeddingService factory is wired correctly
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.storage,
]


@pytest.mark.xdist_group(name="vector_settings_integration")
class TestVectorSearchProviderSettings:
    """Tests for vector_search_provider Settings field."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_vector_search_provider_field(self) -> None:
        """
        GIVEN the Settings class
        WHEN accessing vector_search_provider
        THEN the field should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "vector_search_provider")

    def test_settings_vector_search_provider_default_is_inmemory(self) -> None:
        """
        GIVEN the Settings class with no override
        WHEN accessing vector_search_provider
        THEN default should be "inmemory" for safe testing
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.vector_search_provider == "inmemory"

    def test_settings_vector_search_provider_accepts_pgvector(self) -> None:
        """
        GIVEN the Settings class
        WHEN setting vector_search_provider to "pgvector"
        THEN the value should be accepted
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(vector_search_provider="pgvector")
        assert settings.vector_search_provider == "pgvector"

    def test_settings_vector_search_provider_accepts_qdrant(self) -> None:
        """
        GIVEN the Settings class
        WHEN setting vector_search_provider to "qdrant"
        THEN the value should be accepted
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(vector_search_provider="qdrant")
        assert settings.vector_search_provider == "qdrant"


@pytest.mark.xdist_group(name="vector_factory_settings")
class TestVectorProviderFactorySettings:
    """Tests for get_vector_provider factory Settings integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_vector_provider_from_settings_inmemory(self) -> None:
        """
        GIVEN Settings with vector_search_provider="inmemory"
        WHEN calling get_vector_provider_from_settings()
        THEN returns InMemoryVectorProvider
        """
        from mcp_server_langgraph.storage.vectors import InMemoryVectorProvider
        from mcp_server_langgraph.storage.vectors.factory import (
            get_vector_provider_from_settings,
        )

        provider = get_vector_provider_from_settings()
        assert isinstance(provider, InMemoryVectorProvider)

    def test_get_vector_provider_from_settings_pgvector(self) -> None:
        """
        GIVEN Settings with vector_search_provider="pgvector"
        WHEN calling get_vector_provider_from_settings()
        THEN returns PgVectorProvider
        """
        from mcp_server_langgraph.storage.vectors.factory import (
            get_vector_provider_from_settings,
        )
        from mcp_server_langgraph.storage.vectors.pgvector_provider import (
            PgVectorProvider,
        )

        # Mock the database pool and settings
        mock_pool = MagicMock()
        mock_settings = MagicMock()
        mock_settings.vector_search_provider = "pgvector"

        with patch(
            "mcp_server_langgraph.core.config.settings", mock_settings
        ):
            with patch(
                "mcp_server_langgraph.storage.vectors.factory.get_database_pool",
                return_value=mock_pool,
            ):
                provider = get_vector_provider_from_settings()
                assert isinstance(provider, PgVectorProvider)

    def test_get_vector_provider_from_settings_qdrant(self) -> None:
        """
        GIVEN Settings with vector_search_provider="qdrant"
        WHEN calling get_vector_provider_from_settings()
        THEN returns QdrantVectorProvider
        """
        from mcp_server_langgraph.storage.vectors.factory import (
            get_vector_provider_from_settings,
        )
        from mcp_server_langgraph.storage.vectors.qdrant_provider import (
            QdrantVectorProvider,
        )

        # Mock the Qdrant client and settings
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.vector_search_provider = "qdrant"
        mock_settings.embedding_dimensions = 768

        with patch(
            "mcp_server_langgraph.core.config.settings", mock_settings
        ):
            with patch(
                "mcp_server_langgraph.storage.vectors.factory.get_qdrant_client",
                return_value=mock_client,
            ):
                provider = get_vector_provider_from_settings()
                assert isinstance(provider, QdrantVectorProvider)


@pytest.mark.xdist_group(name="embedding_factory_settings")
class TestEmbeddingServiceSettings:
    """Tests for get_embedding_service Settings integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_embedding_provider_field(self) -> None:
        """
        GIVEN the Settings class
        WHEN accessing embedding_provider
        THEN the field should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "embedding_provider")

    def test_get_embedding_service_from_settings_uses_provider(self) -> None:
        """
        GIVEN Settings with embedding_provider configured
        WHEN calling get_embedding_service_from_settings()
        THEN uses the configured provider
        """
        from mcp_server_langgraph.llm.embeddings import (
            InMemoryEmbeddingService,
            get_embedding_service,
        )

        # Without API keys, should return InMemory
        with patch.dict("os.environ", {}, clear=False):
            with patch(
                "mcp_server_langgraph.llm.embeddings._has_litellm_embedding_config",
                return_value=False,
            ):
                service = get_embedding_service()
                assert isinstance(service, InMemoryEmbeddingService)
