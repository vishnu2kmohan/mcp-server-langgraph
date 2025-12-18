"""
LLM Provider Configuration Module.

Settings for multi-provider LLM support via LiteLLM.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class LLMSettings(DomainSettings):
    """
    LLM provider and model settings.

    Covers:
    - Primary LLM provider configuration (Google, Anthropic, OpenAI, etc.)
    - Model parameters (temperature, max_tokens, timeout)
    - Dedicated models for summarization and verification
    - Fallback model configuration for resilience
    - Embedding configuration for semantic search
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # LLM Provider (litellm integration)
    llm_provider: str = "google"  # google, anthropic, openai, ollama, azure, bedrock, vertex_ai

    # Anthropic (Direct API)
    anthropic_api_key: str | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_organization: str | None = None

    # Google (Gemini via Google AI Studio)
    google_api_key: str | None = None
    google_project_id: str | None = None
    google_location: str = Field(
        default="global",
        validation_alias=AliasChoices("GOOGLE_LOCATION", "GOOGLE_CLOUD_LOCATION"),
    )

    # Vertex AI (Google Cloud AI Platform)
    vertex_project: str | None = None
    vertex_location: str = Field(
        default="global",
        validation_alias=AliasChoices("VERTEX_LOCATION", "GOOGLE_CLOUD_LOCATION"),
    )

    # Azure OpenAI
    azure_api_key: str | None = None
    azure_api_base: str | None = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_name: str | None = None

    # AWS Bedrock
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Ollama (local/open-source models)
    ollama_base_url: str = "http://localhost:11434"

    # Primary Model Configuration
    model_name: str = "gemini-2.5-flash"
    model_temperature: float = 0.7
    model_max_tokens: int = 8192
    model_timeout: int = 60

    # Summarization Model (lighter/cheaper model for context compaction)
    use_dedicated_summarization_model: bool = True
    summarization_model_name: str | None = "gemini-2.5-flash"
    summarization_model_provider: str | None = None
    summarization_model_temperature: float = 0.3
    summarization_model_max_tokens: int = 2000

    # Verification Model (dedicated model for LLM-as-judge)
    use_dedicated_verification_model: bool = True
    verification_model_name: str | None = "gemini-2.5-flash"
    verification_model_provider: str | None = None
    verification_model_temperature: float = 0.0
    verification_model_max_tokens: int = 1000

    # Fallback Models (for resilience)
    enable_fallback: bool = True
    fallback_models: list[str] = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "gpt-5.1",
    ]

    # Embedding Configuration
    embedding_provider: str = "google_vertex"
    embedding_model_name: str = "text-embedding-005"
    embedding_dimensions: int = 768
    embedding_task_type: str = "RETRIEVAL_DOCUMENT"
    embedding_model: str = "all-MiniLM-L6-v2"  # Deprecated, use embedding_model_name


__all__ = ["LLMSettings"]
