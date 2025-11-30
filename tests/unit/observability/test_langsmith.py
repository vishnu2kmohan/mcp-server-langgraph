"""
Unit tests for LangSmith configuration and integration.

Tests LangSmith tracing configuration, metadata, and run config generation.
"""

import gc
import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_langsmith")
class TestConfigureLangsmith:
    """Tests for configure_langsmith function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_configure_langsmith_returns_false_when_disabled(self) -> None:
        """Test that configure_langsmith returns False when tracing is disabled."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = False

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import configure_langsmith

            result = configure_langsmith()

            assert result is False

    def test_configure_langsmith_sets_environment_variables(self) -> None:
        """Test that configure_langsmith sets LangSmith environment variables."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test-api-key"
        mock_settings.langsmith_tracing_v2 = True
        mock_settings.langsmith_project = "test-project"
        mock_settings.langsmith_endpoint = "https://api.langsmith.com"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import configure_langsmith

            result = configure_langsmith()

            assert result is True
            assert os.environ.get("LANGSMITH_API_KEY") == "test-api-key"
            assert os.environ.get("LANGCHAIN_API_KEY") == "test-api-key"
            assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
            assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
            assert os.environ.get("LANGCHAIN_ENDPOINT") == "https://api.langsmith.com"

    def test_configure_langsmith_handles_no_api_key(self) -> None:
        """Test that configure_langsmith works without API key."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = None
        mock_settings.langsmith_tracing_v2 = True
        mock_settings.langsmith_project = "test-project"
        mock_settings.langsmith_endpoint = "https://api.langsmith.com"

        # Clear any existing env vars
        for key in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"]:
            os.environ.pop(key, None)

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import configure_langsmith

            result = configure_langsmith()

            assert result is True
            assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"


@pytest.mark.xdist_group(name="test_langsmith")
class TestGetRunMetadata:
    """Tests for get_run_metadata function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_run_metadata_returns_base_metadata(self) -> None:
        """Test that get_run_metadata returns environment metadata."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.service_name = "test-service"
        mock_settings.service_version = "1.0.0"
        mock_settings.model_name = "gpt-4"
        mock_settings.llm_provider = "openai"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_metadata

            result = get_run_metadata()

            assert result["environment"] == "test"
            assert result["service_name"] == "test-service"
            assert result["service_version"] == "1.0.0"
            assert result["model_name"] == "gpt-4"
            assert result["llm_provider"] == "openai"

    def test_get_run_metadata_includes_user_id(self) -> None:
        """Test that get_run_metadata includes user_id when provided."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.service_name = "test-service"
        mock_settings.service_version = "1.0.0"
        mock_settings.model_name = "gpt-4"
        mock_settings.llm_provider = "openai"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_metadata

            result = get_run_metadata(user_id="user-123")

            assert result["user_id"] == "user-123"

    def test_get_run_metadata_includes_request_id(self) -> None:
        """Test that get_run_metadata includes request_id when provided."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.service_name = "test-service"
        mock_settings.service_version = "1.0.0"
        mock_settings.model_name = "gpt-4"
        mock_settings.llm_provider = "openai"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_metadata

            result = get_run_metadata(request_id="req-456")

            assert result["request_id"] == "req-456"

    def test_get_run_metadata_merges_additional_metadata(self) -> None:
        """Test that get_run_metadata merges additional metadata."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.service_name = "test-service"
        mock_settings.service_version = "1.0.0"
        mock_settings.model_name = "gpt-4"
        mock_settings.llm_provider = "openai"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_metadata

            additional = {"custom_key": "custom_value", "another_key": 123}
            result = get_run_metadata(additional_metadata=additional)

            assert result["custom_key"] == "custom_value"
            assert result["another_key"] == 123


@pytest.mark.xdist_group(name="test_langsmith")
class TestGetRunTags:
    """Tests for get_run_tags function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_run_tags_returns_base_tags(self) -> None:
        """Test that get_run_tags returns environment-based tags."""
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.llm_provider = "anthropic"
        mock_settings.model_name = "claude-3-sonnet"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_tags

            result = get_run_tags()

            assert "production" in result
            assert "anthropic" in result
            assert "model:claude-3-sonnet" in result

    def test_get_run_tags_includes_user_tag(self) -> None:
        """Test that get_run_tags includes user tag when user_id provided."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.llm_provider = "openai"
        mock_settings.model_name = "gpt-4"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_tags

            result = get_run_tags(user_id="user-789")

            assert "user:user-789" in result

    def test_get_run_tags_extends_additional_tags(self) -> None:
        """Test that get_run_tags extends with additional tags."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.llm_provider = "openai"
        mock_settings.model_name = "gpt-4"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import get_run_tags

            result = get_run_tags(additional_tags=["custom-tag", "feature:chat"])

            assert "custom-tag" in result
            assert "feature:chat" in result


@pytest.mark.xdist_group(name="test_langsmith")
class TestLangSmithConfig:
    """Tests for LangSmithConfig class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_langsmith_config_is_enabled_returns_true_when_configured(self) -> None:
        """Test that is_enabled returns True when LangSmith is configured."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test-key"
        mock_settings.langsmith_tracing_v2 = True
        mock_settings.langsmith_project = "test-project"
        mock_settings.langsmith_endpoint = "https://api.langsmith.com"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import LangSmithConfig

            config = LangSmithConfig()

            assert config.is_enabled() is True

    def test_langsmith_config_is_enabled_returns_false_when_disabled(self) -> None:
        """Test that is_enabled returns False when LangSmith is disabled."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = False

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import LangSmithConfig

            config = LangSmithConfig()

            assert config.is_enabled() is False

    def test_langsmith_config_get_client_kwargs_returns_empty_when_disabled(self) -> None:
        """Test that get_client_kwargs returns empty dict when disabled."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = False

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import LangSmithConfig

            config = LangSmithConfig()
            result = config.get_client_kwargs()

            assert result == {}

    def test_langsmith_config_get_client_kwargs_returns_config_when_enabled(self) -> None:
        """Test that get_client_kwargs returns API config when enabled."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test-api-key"
        mock_settings.langsmith_tracing_v2 = True
        mock_settings.langsmith_project = "test-project"
        mock_settings.langsmith_endpoint = "https://api.langsmith.com"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import LangSmithConfig

            config = LangSmithConfig()
            result = config.get_client_kwargs()

            assert result["api_key"] == "test-api-key"
            assert result["api_url"] == "https://api.langsmith.com"

    def test_langsmith_config_create_run_config(self) -> None:
        """Test that create_run_config generates complete run configuration."""
        mock_settings = MagicMock()
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test-key"
        mock_settings.langsmith_tracing_v2 = True
        mock_settings.langsmith_project = "test-project"
        mock_settings.langsmith_endpoint = "https://api.langsmith.com"
        mock_settings.environment = "test"
        mock_settings.service_name = "test-service"
        mock_settings.service_version = "1.0.0"
        mock_settings.model_name = "gpt-4"
        mock_settings.llm_provider = "openai"

        with patch(
            "mcp_server_langgraph.observability.langsmith.settings",
            mock_settings,
        ):
            from mcp_server_langgraph.observability.langsmith import LangSmithConfig

            config = LangSmithConfig()
            result = config.create_run_config(
                run_name="test-run",
                user_id="user-123",
                request_id="req-456",
            )

            assert result["run_name"] == "test-run"
            assert result["project_name"] == "test-project"
            assert "user:user-123" in result["tags"]
            assert result["metadata"]["user_id"] == "user-123"
            assert result["metadata"]["request_id"] == "req-456"
