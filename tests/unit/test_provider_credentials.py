"""TDD tests for multi-credential provider setup (Azure, Bedrock).

Tests verify that providers requiring multiple environment variables
(Azure: API_KEY + BASE + VERSION + DEPLOYMENT, Bedrock: ACCESS_KEY + SECRET + REGION)
are properly configured.
"""

import gc
import os
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.llm.factory import LLMFactory


@pytest.mark.xdist_group(name="unit_provider_credentials_tests")
class TestProviderCredentialSetup:
    """Test multi-credential provider configuration (TDD RED → GREEN)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_azure_provider_sets_all_required_env_vars(self):
        """
        Test that Azure provider sets API_KEY, BASE, VERSION, and DEPLOYMENT_NAME.

        GREEN: Should pass with multi-credential provider_config_map
        """
        # GIVEN: Settings with Azure configuration
        mock_settings = MagicMock()
        mock_settings.llm_provider = "azure"
        mock_settings.llm_model = "azure/gpt-4"
        mock_settings.llm_api_key = "test-azure-key"
        mock_settings.azure_api_key = "test-azure-key"
        mock_settings.azure_api_base = "https://test.openai.azure.com"
        mock_settings.azure_api_version = "2024-02-15-preview"
        mock_settings.azure_deployment_name = "gpt-4-deployment"
        mock_settings.llm_fallback_models = []
        mock_settings.llm_temperature = 0.7
        mock_settings.llm_max_tokens = 4096

        # Clear environment
        for var in ["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION", "AZURE_DEPLOYMENT_NAME"]:
            os.environ.pop(var, None)

        # WHEN: Creating LLMFactory and setting up environment
        factory = LLMFactory(
            provider="azure",
            model_name="azure/gpt-4",
            api_key="test-azure-key",
        )
        factory._setup_environment(mock_settings)

        # THEN: All Azure environment variables should be set
        assert os.environ.get("AZURE_API_KEY") == "test-azure-key"
        assert os.environ.get("AZURE_API_BASE") == "https://test.openai.azure.com"
        assert os.environ.get("AZURE_API_VERSION") == "2024-02-15-preview"
        assert os.environ.get("AZURE_DEPLOYMENT_NAME") == "gpt-4-deployment"

    def test_bedrock_provider_sets_all_aws_credentials(self):
        """
        Test that Bedrock provider sets ACCESS_KEY_ID, SECRET_ACCESS_KEY, and REGION.

        GREEN: Should pass with multi-credential provider_config_map
        """
        # GIVEN: Settings with Bedrock configuration
        mock_settings = MagicMock()
        mock_settings.llm_provider = "bedrock"
        mock_settings.llm_model = "bedrock/anthropic.claude-v2"
        mock_settings.aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
        mock_settings.aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        mock_settings.aws_region = "us-west-2"
        mock_settings.llm_fallback_models = []
        mock_settings.llm_temperature = 0.7
        mock_settings.llm_max_tokens = 4096

        # Clear environment
        for var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]:
            os.environ.pop(var, None)

        # WHEN: Creating LLMFactory and setting up environment
        factory = LLMFactory(
            provider="bedrock",
            model_name="bedrock/anthropic.claude-v2",
            api_key="AKIAIOSFODNN7EXAMPLE",
        )
        factory._setup_environment(mock_settings)

        # THEN: All AWS environment variables should be set
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "AKIAIOSFODNN7EXAMPLE"
        assert os.environ.get("AWS_SECRET_ACCESS_KEY") == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert os.environ.get("AWS_REGION") == "us-west-2"

    def test_azure_fallback_provider_configures_all_credentials(self):
        """
        Test that Azure as a fallback provider gets all required credentials.

        GREEN: Should pass with multi-credential mapping
        """
        # GIVEN: Primary provider is Anthropic, Azure is fallback
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_model = "claude-3-5-sonnet-20241022"
        mock_settings.llm_api_key = "test-anthropic-key"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.llm_fallback_models = ["azure/gpt-4"]
        mock_settings.azure_api_key = "fallback-azure-key"
        mock_settings.azure_api_base = "https://fallback.openai.azure.com"
        mock_settings.azure_api_version = "2024-02-15-preview"
        mock_settings.azure_deployment_name = "gpt-4-fallback"
        mock_settings.llm_temperature = 0.7
        mock_settings.llm_max_tokens = 4096

        # Clear environment
        for var in ["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION", "AZURE_DEPLOYMENT_NAME", "ANTHROPIC_API_KEY"]:
            os.environ.pop(var, None)

        # WHEN: Creating LLMFactory and setting up environment
        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            api_key="test-anthropic-key",
            fallback_models=["azure/gpt-4"],
        )
        factory._setup_environment(mock_settings)

        # THEN: Both Anthropic and Azure credentials should be configured
        assert os.environ.get("ANTHROPIC_API_KEY") == "test-anthropic-key"
        assert os.environ.get("AZURE_API_KEY") == "fallback-azure-key"
        assert os.environ.get("AZURE_API_BASE") == "https://fallback.openai.azure.com"
        assert os.environ.get("AZURE_API_VERSION") == "2024-02-15-preview"
        assert os.environ.get("AZURE_DEPLOYMENT_NAME") == "gpt-4-fallback"

    def test_single_credential_providers_still_work(self):
        """
        Test backward compatibility: single-credential providers (OpenAI, Anthropic, Google).

        GREEN: Should pass (no regression)
        """
        # GIVEN: Settings with OpenAI (single credential provider)
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = "gpt-4"
        mock_settings.llm_api_key = "test-openai-key"
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.llm_fallback_models = []
        mock_settings.llm_temperature = 0.7
        mock_settings.llm_max_tokens = 4096

        # Clear environment
        os.environ.pop("OPENAI_API_KEY", None)

        # WHEN: Creating LLMFactory and setting up environment
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            api_key="test-openai-key",
        )
        factory._setup_environment(mock_settings)

        # THEN: OpenAI API key should be set
        assert os.environ.get("OPENAI_API_KEY") == "test-openai-key"

    def test_missing_azure_endpoint_does_not_crash(self):
        """
        Test that missing Azure endpoint doesn't crash, just logs warning.

        GREEN: Should handle None values gracefully
        """
        # GIVEN: Azure settings with missing endpoint
        mock_settings = MagicMock()
        mock_settings.llm_provider = "azure"
        mock_settings.llm_model = "azure/gpt-4"
        mock_settings.azure_api_key = "test-key"
        mock_settings.azure_api_base = None  # Missing endpoint
        mock_settings.azure_api_version = "2024-02-15-preview"
        mock_settings.azure_deployment_name = None  # Missing deployment
        mock_settings.llm_fallback_models = []
        mock_settings.llm_temperature = 0.7
        mock_settings.llm_max_tokens = 4096

        # Clear environment
        for var in ["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION", "AZURE_DEPLOYMENT_NAME"]:
            os.environ.pop(var, None)

        # WHEN: Creating LLMFactory (should not crash)
        factory = LLMFactory(
            provider="azure",
            model_name="azure/gpt-4",
            api_key="test-key",
        )
        factory._setup_environment(mock_settings)

        # THEN: Should set available credentials, skip None values
        assert os.environ.get("AZURE_API_KEY") == "test-key"
        assert os.environ.get("AZURE_API_VERSION") == "2024-02-15-preview"
        # None values should not be set as string "None"
        assert os.environ.get("AZURE_API_BASE") != "None"
        assert os.environ.get("AZURE_DEPLOYMENT_NAME") != "None"
