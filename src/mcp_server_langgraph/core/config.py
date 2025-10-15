"""
Configuration management with Infisical secrets integration
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_server_langgraph.secrets.manager import get_secrets_manager


class Settings(BaseSettings):
    """Application settings with Infisical secrets support"""

    # Service
    service_name: str = "mcp-server-langgraph"
    service_version: str = "2.6.0"
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
    log_format: str = "json"  # "json" or "text"
    log_json_indent: Optional[int] = None  # None for compact, 2 for pretty-print

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
    fallback_models: list[str] = ["gemini-2.5-pro", "claude-3-5-sonnet-20241022", "gpt-4o"]

    # Agent
    max_iterations: int = 10
    enable_checkpointing: bool = True

    # Conversation Checkpointing (for distributed state across replicas)
    checkpoint_backend: str = "memory"  # "memory", "redis"
    checkpoint_redis_url: str = "redis://localhost:6379/1"  # Use db 1 (sessions use db 0)
    checkpoint_redis_ttl: int = 604800  # 7 days TTL for conversation checkpoints

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

    # Authentication Provider
    auth_provider: str = "inmemory"  # "inmemory", "keycloak"
    auth_mode: str = "token"  # "token" (JWT), "session"

    # Keycloak Settings
    keycloak_server_url: str = "http://localhost:8180"
    keycloak_realm: str = "langgraph-agent"
    keycloak_client_id: str = "langgraph-client"
    keycloak_client_secret: Optional[str] = None
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: Optional[str] = None
    keycloak_verify_ssl: bool = True
    keycloak_timeout: int = 30  # HTTP timeout in seconds

    # Session Management
    session_backend: str = "memory"  # "memory", "redis"
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    session_ttl_seconds: int = 86400  # 24 hours
    session_sliding_window: bool = True
    session_max_concurrent: int = 5  # Max concurrent sessions per user

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    def load_secrets(self):
        """Load secrets from Infisical"""
        secrets_mgr = get_secrets_manager()

        # Load JWT secret
        if not self.jwt_secret_key:
            default_fallback = "INSECURE-DEV-ONLY-KEY-CHANGE-IN-PRODUCTION"
            self.jwt_secret_key = secrets_mgr.get_secret("JWT_SECRET_KEY", fallback=default_fallback)
            # Warn if using default secret in production
            if self.jwt_secret_key == default_fallback and self.environment == "production":
                raise ValueError(
                    "CRITICAL: Default JWT secret detected in production environment! "
                    "Set JWT_SECRET_KEY environment variable or configure Infisical."
                )

        # Load LLM API keys based on provider
        if not self.anthropic_api_key:
            self.anthropic_api_key = secrets_mgr.get_secret("ANTHROPIC_API_KEY", fallback=None)

        if not self.openai_api_key:
            self.openai_api_key = secrets_mgr.get_secret("OPENAI_API_KEY", fallback=None)

        if not self.google_api_key:
            self.google_api_key = secrets_mgr.get_secret("GOOGLE_API_KEY", fallback=None)

        if not self.azure_api_key:
            self.azure_api_key = secrets_mgr.get_secret("AZURE_API_KEY", fallback=None)

        if not self.aws_access_key_id:
            self.aws_access_key_id = secrets_mgr.get_secret("AWS_ACCESS_KEY_ID", fallback=None)

        if not self.aws_secret_access_key:
            self.aws_secret_access_key = secrets_mgr.get_secret("AWS_SECRET_ACCESS_KEY", fallback=None)

        # Load OpenFGA configuration
        if not self.openfga_store_id:
            self.openfga_store_id = secrets_mgr.get_secret("OPENFGA_STORE_ID", fallback=None)

        if not self.openfga_model_id:
            self.openfga_model_id = secrets_mgr.get_secret("OPENFGA_MODEL_ID", fallback=None)

        # Load LangSmith configuration
        if not self.langsmith_api_key:
            self.langsmith_api_key = secrets_mgr.get_secret("LANGSMITH_API_KEY", fallback=None)

        # Load LangGraph Platform configuration
        if not self.langgraph_api_key:
            self.langgraph_api_key = secrets_mgr.get_secret("LANGGRAPH_API_KEY", fallback=None)

        # Load Keycloak configuration
        if not self.keycloak_client_secret:
            self.keycloak_client_secret = secrets_mgr.get_secret("KEYCLOAK_CLIENT_SECRET", fallback=None)

        if not self.keycloak_admin_password:
            self.keycloak_admin_password = secrets_mgr.get_secret("KEYCLOAK_ADMIN_PASSWORD", fallback=None)

        # Load checkpoint configuration
        # Note: checkpoint_redis_url defaults to redis://localhost:6379/1
        # Can be overridden via environment variable or Infisical

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
