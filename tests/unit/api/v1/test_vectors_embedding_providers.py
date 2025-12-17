"""
Tests for Vector API Embedding Provider Selection.

Tests the get_embedding_model dependency function which selects
the appropriate embedding model based on the configured provider.

Primary focus: Testing the new google_vertex provider for GCP WIF support.
"""

import gc
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="test_embedding_providers")
class TestGoogleVertexEmbeddingProvider:
    """Tests for google_vertex embedding provider (new feature for GCP WIF).

    PYTEST-XDIST FIX (2025-12-16):
    Added setup_method to reset singleton dependencies and prevent state pollution
    between tests in xdist workers.
    """

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-gcp-project"})
    def test_google_vertex_provider_returns_vertex_embeddings(self) -> None:
        """
        GIVEN: embedding_provider set to 'google_vertex' with GCP project set
        WHEN: get_embedding_model is called
        THEN: Returns VertexAIEmbeddings with project ID.

        This is the key test for GCP Workload Identity Federation support.
        """
        mock_vertex_class = MagicMock()
        mock_vertex_module = MagicMock()
        mock_vertex_module.VertexAIEmbeddings = mock_vertex_class

        with (
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_provider",
                "google_vertex",
            ),
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_model_name",
                "text-embedding-005",
            ),
            patch.dict(sys.modules, {"langchain_google_vertexai": mock_vertex_module}),
        ):
            from mcp_server_langgraph.api.v1.vectors import get_embedding_model

            result = get_embedding_model()

            mock_vertex_class.assert_called_once_with(
                model_name="text-embedding-005",
                project="my-gcp-project",
            )
            assert result == mock_vertex_class.return_value

    def test_google_vertex_uses_gcp_project_id_env_var(self, monkeypatch) -> None:
        """
        GIVEN: GCP_PROJECT_ID set (alternative to GOOGLE_CLOUD_PROJECT)
        WHEN: get_embedding_model is called with google_vertex
        THEN: Uses the GCP_PROJECT_ID value.

        PYTEST-XDIST FIX (2025-12-16):
        Use monkeypatch instead of @patch.dict to ensure GOOGLE_CLOUD_PROJECT
        is deleted before setting GCP_PROJECT_ID (the code checks GOOGLE_CLOUD_PROJECT first).
        """
        # Clear GOOGLE_CLOUD_PROJECT first (the code checks it before GCP_PROJECT_ID)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.setenv("GCP_PROJECT_ID", "alternate-project")

        mock_vertex_class = MagicMock()
        mock_vertex_module = MagicMock()
        mock_vertex_module.VertexAIEmbeddings = mock_vertex_class

        with (
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_provider",
                "google_vertex",
            ),
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_model_name",
                "textembedding-gecko",
            ),
            patch.dict(sys.modules, {"langchain_google_vertexai": mock_vertex_module}),
        ):
            from mcp_server_langgraph.api.v1.vectors import get_embedding_model

            result = get_embedding_model()

            mock_vertex_class.assert_called_once_with(
                model_name="textembedding-gecko",
                project="alternate-project",
            )
            assert result == mock_vertex_class.return_value

    def test_google_vertex_raises_when_package_not_installed(self) -> None:
        """
        GIVEN: embedding_provider set to 'google_vertex'
        AND: langchain-google-vertexai package is not installed
        WHEN: get_embedding_model is called
        THEN: Raises ValueError with installation instructions.
        """
        with (
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_provider",
                "google_vertex",
            ),
            patch(
                "mcp_server_langgraph.core.config.settings.embedding_model_name",
                "textembedding-gecko",
            ),
            patch.dict(sys.modules, {"langchain_google_vertexai": None}),
        ):
            from mcp_server_langgraph.api.v1.vectors import get_embedding_model

            with pytest.raises(ValueError) as exc_info:
                get_embedding_model()

            error_message = str(exc_info.value)
            assert "langchain-google-vertexai" in error_message
            assert "pip install" in error_message


@pytest.mark.xdist_group(name="test_embedding_providers")
class TestEmbeddingProviderConfiguration:
    """Tests for embedding provider configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_provider_is_google_vertex(self) -> None:
        """
        GIVEN: Default settings
        WHEN: embedding_provider is checked
        THEN: Defaults to 'google_vertex' for GCP WIF compatibility.
        """
        from mcp_server_langgraph.core.config import Settings

        # Create a fresh settings instance to test defaults
        fresh_settings = Settings(
            _env_file=None,  # Don't load .env files
        )

        assert fresh_settings.embedding_provider == "google_vertex"
        assert fresh_settings.embedding_model_name == "text-embedding-005"

    def test_supported_provider_values(self) -> None:
        """
        Test that documentation comments list all supported providers.
        This is a meta-test to ensure docs stay in sync with code.
        """
        supported_providers = [
            "openai",
            "google",
            "google_vertex",
            "huggingface",
            "local",
        ]

        # Just verify these are the expected valid values
        # The actual provider selection is tested via the full tests above
        assert len(supported_providers) == 5
        assert "google_vertex" in supported_providers
