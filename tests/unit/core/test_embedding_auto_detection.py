"""Tests for embedding provider auto-detection.

TDD: These tests define the expected behavior for auto-detecting
the embedding provider based on available API keys.

The auto_detect_embedding_provider function should:
- Return "google" if GOOGLE_API_KEY is set
- Return "openai" if OPENAI_API_KEY is set (and no Google key)
- Return "huggingface" if HF_TOKEN is set (and no higher-priority keys)
- Return "local" as fallback when no API keys are set
"""

from __future__ import annotations

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestEmbeddingAutoDetection:
    """Tests for embedding provider auto-detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_auto_detect_function_exists(self) -> None:
        """Test auto_detect_embedding_provider function exists."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        assert auto_detect_embedding_provider is not None
        assert callable(auto_detect_embedding_provider)

    def test_returns_google_when_google_api_key_set(self) -> None:
        """Test returns 'google' when GOOGLE_API_KEY is available."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=True):
            result = auto_detect_embedding_provider()
            assert result == "google"

    def test_returns_openai_when_openai_api_key_set(self) -> None:
        """Test returns 'openai' when only OPENAI_API_KEY is available."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            result = auto_detect_embedding_provider()
            assert result == "openai"

    def test_returns_huggingface_when_hf_token_set(self) -> None:
        """Test returns 'huggingface' when only HF_TOKEN is available."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=True):
            result = auto_detect_embedding_provider()
            assert result == "huggingface"

    def test_returns_local_when_no_keys_set(self) -> None:
        """Test returns 'local' when no API keys are available."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(os.environ, {}, clear=True):
            # Ensure none of the keys are set
            for key in ["GOOGLE_API_KEY", "OPENAI_API_KEY", "HF_TOKEN", "HUGGINGFACE_TOKEN"]:
                if key in os.environ:
                    del os.environ[key]
            result = auto_detect_embedding_provider()
            assert result == "local"

    def test_google_has_priority_over_openai(self) -> None:
        """Test Google has priority when both Google and OpenAI keys are set."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(
            os.environ,
            {"GOOGLE_API_KEY": "google-key", "OPENAI_API_KEY": "openai-key"},
            clear=True,
        ):
            result = auto_detect_embedding_provider()
            assert result == "google"

    def test_openai_has_priority_over_huggingface(self) -> None:
        """Test OpenAI has priority when both OpenAI and HF keys are set."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "openai-key", "HF_TOKEN": "hf-token"},
            clear=True,
        ):
            result = auto_detect_embedding_provider()
            assert result == "openai"

    def test_huggingface_token_alternative_env_var(self) -> None:
        """Test HUGGINGFACE_TOKEN is also recognized."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            auto_detect_embedding_provider,
        )

        with patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "hf-token"}, clear=True):
            result = auto_detect_embedding_provider()
            assert result == "huggingface"

    def test_returns_default_model_for_provider(self) -> None:
        """Test get_default_embedding_model returns correct defaults."""
        from mcp_server_langgraph.core.dynamic_context_loader import (
            get_default_embedding_model,
        )

        assert get_default_embedding_model("google") == "models/text-embedding-004"
        assert get_default_embedding_model("openai") == "text-embedding-3-small"
        assert get_default_embedding_model("huggingface") == "sentence-transformers/all-MiniLM-L6-v2"
        assert get_default_embedding_model("local") == "all-MiniLM-L6-v2"
        assert get_default_embedding_model("google_vertex") == "textembedding-gecko@latest"
