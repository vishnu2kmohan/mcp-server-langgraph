"""
Configuration management with Infisical secrets integration
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional
from secrets_manager import get_secrets_manager


class Settings(BaseSettings):
    """Application settings with Infisical secrets support"""

    # Service
    service_name: str = "mcp-server-langgraph"
    service_version: str = "1.0.0"
    environment: str = "development"

    # Authentication
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600

    # OpenTelemetry
    otlp_endpoint: str = "http://localhost:4317"
    enable_console_export: bool = True
    enable_tracing: bool = True
    enable_metrics: bool = True

    # LangSmith Observability
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "mcp-server-langgraph"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False  # Enable LangSmith tracing
    langsmith_tracing_v2: bool = True  # Use v2 tracing (recommended)

    # Observability Backend Selection
    observability_backend: str = "both"  # opentelemetry, langsmith, both

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # LLM Provider (litellm integration)
    llm_provider: str = "google"  # google, anthropic, openai, ollama, azure, bedrock

    # Anthropic
    anthropic_api_key: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None

    # Google (Gemini/VertexAI)
    google_api_key: Optional[str] = None
    google_project_id: Optional[str] = None
    google_location: str = "us-central1"

    # Azure OpenAI
    azure_api_key: Optional[str] = None
    azure_api_base: Optional[str] = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_name: Optional[str] = None

    # AWS Bedrock
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"

    # Ollama (for local/open-source models)
    ollama_base_url: str = "http://localhost:11434"

    # Model Configuration
    model_name: str = "gemini-2.5-flash-002"  # Latest Gemini 2.5 Flash
    model_temperature: float = 0.7
    model_max_tokens: int = 8192
    model_timeout: int = 60

    # Fallback Models (for resilience)
    enable_fallback: bool = True
    fallback_models: list[str] = [
        "gemini-2.5-pro",
        "claude-3-5-sonnet-20241022",
        "gpt-4o"
    ]

    # Agent
    max_iterations: int = 10
    enable_checkpointing: bool = True

    # OpenFGA
    openfga_api_url: str = "http://localhost:8080"
    openfga_store_id: Optional[str] = None
    openfga_model_id: Optional[str] = None

    # Infisical
    infisical_site_url: str = "https://app.infisical.com"
    infisical_client_id: Optional[str] = None
    infisical_client_secret: Optional[str] = None
    infisical_project_id: Optional[str] = None

    # LangGraph Platform
    langgraph_api_key: Optional[str] = None
    langgraph_deployment_url: Optional[str] = None
    langgraph_api_url: str = "https://api.langchain.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def load_secrets(self):
        """Load secrets from Infisical"""
        secrets_mgr = get_secrets_manager()

        # Load JWT secret
        if not self.jwt_secret_key:
            self.jwt_secret_key = secrets_mgr.get_secret(
                "JWT_SECRET_KEY",
                fallback="change-this-in-production"
            )
            # Warn if using default secret in production
            if self.jwt_secret_key == "change-this-in-production" and self.environment == "production":
                raise ValueError(
                    "CRITICAL: Default JWT secret detected in production environment! "
                    "Set JWT_SECRET_KEY environment variable or configure Infisical."
                )

        # Load LLM API keys based on provider
        if not self.anthropic_api_key:
            self.anthropic_api_key = secrets_mgr.get_secret(
                "ANTHROPIC_API_KEY",
                fallback=None
            )

        if not self.openai_api_key:
            self.openai_api_key = secrets_mgr.get_secret(
                "OPENAI_API_KEY",
                fallback=None
            )

        if not self.google_api_key:
            self.google_api_key = secrets_mgr.get_secret(
                "GOOGLE_API_KEY",
                fallback=None
            )

        if not self.azure_api_key:
            self.azure_api_key = secrets_mgr.get_secret(
                "AZURE_API_KEY",
                fallback=None
            )

        if not self.aws_access_key_id:
            self.aws_access_key_id = secrets_mgr.get_secret(
                "AWS_ACCESS_KEY_ID",
                fallback=None
            )

        if not self.aws_secret_access_key:
            self.aws_secret_access_key = secrets_mgr.get_secret(
                "AWS_SECRET_ACCESS_KEY",
                fallback=None
            )

        # Load OpenFGA configuration
        if not self.openfga_store_id:
            self.openfga_store_id = secrets_mgr.get_secret(
                "OPENFGA_STORE_ID",
                fallback=None
            )

        if not self.openfga_model_id:
            self.openfga_model_id = secrets_mgr.get_secret(
                "OPENFGA_MODEL_ID",
                fallback=None
            )

        # Load LangSmith configuration
        if not self.langsmith_api_key:
            self.langsmith_api_key = secrets_mgr.get_secret(
                "LANGSMITH_API_KEY",
                fallback=None
            )

        # Load LangGraph Platform configuration
        if not self.langgraph_api_key:
            self.langgraph_api_key = secrets_mgr.get_secret(
                "LANGGRAPH_API_KEY",
                fallback=None
            )

    def get_secret(self, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value from Infisical

        Args:
            key: Secret key
            fallback: Fallback value if not found

        Returns:
            Secret value
        """
        secrets_mgr = get_secrets_manager()
        return secrets_mgr.get_secret(key, fallback=fallback)


# Global settings instance
settings = Settings()

# Load secrets on initialization
try:
    settings.load_secrets()
except Exception as e:
    print(f"Warning: Failed to load secrets from Infisical: {e}")
    print("Using environment variables and defaults")
