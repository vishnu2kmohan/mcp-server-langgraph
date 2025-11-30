"""
Configuration management with Infisical secrets integration
"""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_server_langgraph.secrets.manager import get_secrets_manager

# Import version from package __init__.py (single source of truth)
try:
    from mcp_server_langgraph import __version__
except ImportError:
    __version__ = "2.7.0"  # Fallback


class Settings(BaseSettings):
    """Application settings with Infisical secrets support"""

    # Service
    service_name: str = "mcp-server-langgraph"
    service_version: str = __version__  # Read from package version
    environment: str = "development"

    # CORS Configuration
    # SECURITY: Empty list by default (no CORS) in production
    # Override with CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"
    cors_allowed_origins: list[str] = []  # Empty = no CORS/restrictive by default

    # Authentication
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600
    use_password_hashing: bool = True  # Enable bcrypt password hashing for InMemoryUserProvider (default: secure)

    # Authorization Fallback Control (OpenAI Codex Finding #1)
    # SECURITY: Controls whether authorization can fall back to role-based checks when OpenFGA is unavailable
    # Default: False (fail-closed, secure by default)
    # Set to True only in development/testing environments to allow degraded authorization
    allow_auth_fallback: bool = False

    # HIPAA Compliance (only required if processing PHI)
    hipaa_integrity_secret: str | None = None

    # OpenTelemetry
    otlp_endpoint: str = "http://localhost:4317"
    enable_console_export: bool = True
    enable_tracing: bool = True
    enable_metrics: bool = True

    # Prometheus (for SLA monitoring and compliance metrics)
    prometheus_url: str = "http://prometheus:9090"
    prometheus_timeout: int = 30  # Query timeout in seconds
    prometheus_retry_attempts: int = 3  # Number of retry attempts

    # Alerting Configuration (PagerDuty, Slack, OpsGenie, Email)
    pagerduty_integration_key: str | None = None  # PagerDuty Events API v2 integration key
    slack_webhook_url: str | None = None  # Slack incoming webhook URL
    opsgenie_api_key: str | None = None  # OpsGenie API key
    email_smtp_host: str | None = None  # SMTP server for email alerts
    email_smtp_port: int = 587  # SMTP port
    email_from_address: str | None = None  # From email address
    email_to_addresses: str | None = None  # Comma-separated list of email addresses

    # Web Search API Configuration (for search_tools.py)
    tavily_api_key: str | None = None  # Tavily API key (recommended for AI)
    serper_api_key: str | None = None  # Serper API key (Google search)
    brave_api_key: str | None = None  # Brave Search API key (privacy-focused)

    # LangSmith Observability
    langsmith_api_key: str | None = None
    langsmith_project: str = "mcp-server-langgraph"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False  # Enable LangSmith tracing
    langsmith_tracing_v2: bool = True  # Use v2 tracing (recommended)

    # Observability Backend Selection
    observability_backend: str = "both"  # opentelemetry, langsmith, both

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None
    log_format: str = "json"  # "json" or "text"
    log_json_indent: int | None = None  # None for compact, 2 for pretty-print
    enable_file_logging: bool = False  # Opt-in file-based log rotation (for persistent storage)

    # LLM Provider (litellm integration)
    llm_provider: str = "google"  # google, anthropic, openai, ollama, azure, bedrock, vertex_ai

    # Anthropic (Direct API)
    # Latest models: claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001, claude-opus-4-1-20250805
    anthropic_api_key: str | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_organization: str | None = None

    # Google (Gemini via Google AI Studio)
    # Latest models: gemini-3-pro-preview (Nov 2025), gemini-2.5-flash
    google_api_key: str | None = None
    google_project_id: str | None = None
    google_location: str = "us-central1"

    # Vertex AI (Google Cloud AI Platform)
    # Supports both Anthropic Claude and Google Gemini models via Vertex AI
    # Authentication:
    #   - On GKE: Use Workload Identity (automatic, no credentials needed)
    #   - Locally: Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
    # Anthropic via Vertex AI: vertex_ai/claude-sonnet-4-5@20250929
    # Google via Vertex AI: vertex_ai/gemini-3-pro-preview
    vertex_project: str | None = None  # GCP project ID for Vertex AI (falls back to google_project_id)
    vertex_location: str = "us-central1"  # Vertex AI location/region

    # Azure OpenAI
    azure_api_key: str | None = None
    azure_api_base: str | None = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_name: str | None = None

    # AWS Bedrock
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Ollama (for local/open-source models)
    ollama_base_url: str = "http://localhost:11434"

    # Model Configuration (Primary Chat Model)
    # Options:
    #   - gemini-3-pro-preview (Gemini 3.0 Pro - latest, Nov 2025, 1M context window)
    #   - gemini-2.5-flash (Gemini 2.5 Flash - fast, cost-effective)
    #   - claude-sonnet-4-5-20250929 (Claude Sonnet 4.5 via Anthropic API)
    #   - vertex_ai/claude-sonnet-4-5@20250929 (Claude Sonnet 4.5 via Vertex AI)
    #   - vertex_ai/gemini-3-pro-preview (Gemini 3.0 Pro via Vertex AI)
    model_name: str = "gemini-2.5-flash"  # Default: Gemini 2.5 Flash (balanced cost/performance)
    model_temperature: float = 0.7
    model_max_tokens: int = 8192
    model_timeout: int = 60

    # Dedicated Models for Cost/Performance Optimization
    # Summarization Model (lighter/cheaper model for context compaction)
    use_dedicated_summarization_model: bool = True
    summarization_model_name: str | None = "gemini-2.5-flash"  # Lighter/cheaper for summarization
    summarization_model_provider: str | None = None  # Defaults to llm_provider if None
    summarization_model_temperature: float = 0.3  # Lower temperature for factual summaries
    summarization_model_max_tokens: int = 2000  # Smaller output for summaries

    # Verification Model (dedicated model for LLM-as-judge)
    use_dedicated_verification_model: bool = True
    verification_model_name: str | None = "gemini-2.5-flash"  # Can use different model for verification
    verification_model_provider: str | None = None  # Defaults to llm_provider if None
    verification_model_temperature: float = 0.0  # Deterministic for consistent verification
    verification_model_max_tokens: int = 1000  # Smaller output for verification feedback

    # Fallback Models (for resilience)
    # Using latest production Claude 4.5 models as of October 2025
    # Verified against https://docs.claude.com/en/docs/about-claude/models
    enable_fallback: bool = True
    fallback_models: list[str] = [
        "claude-haiku-4-5-20251001",  # Claude Haiku 4.5 (fast, cost-effective)
        "claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (balanced performance)
        "gpt-5",  # OpenAI GPT-5 (cross-provider resilience)
    ]

    # Agent
    max_iterations: int = 10
    enable_checkpointing: bool = True

    # Agentic Loop Configuration (Anthropic Best Practices)
    # Context Management
    enable_context_compaction: bool = True  # Enable conversation compaction
    compaction_threshold: int = 8000  # Token count that triggers compaction
    target_after_compaction: int = 4000  # Target token count after compaction
    recent_message_count: int = 5  # Number of recent messages to keep uncompacted

    # Work Verification
    enable_verification: bool = True  # Enable LLM-as-judge verification
    verification_quality_threshold: float = 0.7  # Minimum score to pass (0.0-1.0)
    max_refinement_attempts: int = 3  # Maximum refinement iterations
    verification_mode: str = "standard"  # "standard", "strict", "lenient"

    # Dynamic Context Loading (Just-in-Time) - Anthropic Best Practice
    enable_dynamic_context_loading: bool = False  # Enable semantic search-based context loading
    qdrant_url: str = "localhost"  # Qdrant server URL
    qdrant_port: int = 6333  # Qdrant server port
    qdrant_collection_name: str = "mcp_context"  # Collection name for context storage
    dynamic_context_max_tokens: int = 2000  # Max tokens to load from dynamic context
    dynamic_context_top_k: int = 3  # Number of top results from semantic search

    # Embedding Configuration
    embedding_provider: str = "google"  # "google" (Gemini API) or "local" (sentence-transformers)
    embedding_model_name: str = "models/text-embedding-004"  # Google: text-embedding-004, Local: all-MiniLM-L6-v2
    embedding_dimensions: int = 768  # Google: 768 (128-3072 supported), Local: 384
    embedding_task_type: str = "RETRIEVAL_DOCUMENT"  # Google task type optimization
    embedding_model: str = (
        "all-MiniLM-L6-v2"  # Deprecated: use embedding_model_name instead (kept for backwards compatibility)
    )

    context_cache_size: int = 100  # LRU cache size for loaded contexts

    # Data Security & Compliance (for regulated workloads)
    enable_context_encryption: bool = False  # Enable encryption-at-rest for context data
    context_encryption_key: str | None = None  # Encryption key for context data (Fernet-compatible)
    context_retention_days: int = 90  # Retention period for context data (days)
    enable_auto_deletion: bool = True  # Automatically delete expired context data
    enable_multi_tenant_isolation: bool = False  # Use separate collections per tenant

    # Parallel Tool Execution - Anthropic Best Practice
    enable_parallel_execution: bool = False  # Enable parallel tool execution
    max_parallel_tools: int = 5  # Maximum concurrent tool executions

    # Enhanced Note-Taking - Anthropic Best Practice
    enable_llm_extraction: bool = False  # Use LLM for structured note extraction
    extraction_categories: list[str] = [
        "decisions",
        "requirements",
        "facts",
        "action_items",
        "issues",
        "preferences",
    ]  # Categories for information extraction

    # Code Execution Configuration (Anthropic Best Practice - Progressive Disclosure)
    # SECURITY: Disabled by default - must be explicitly enabled
    enable_code_execution: bool = False  # Enable sandboxed code execution
    code_execution_backend: str = "docker-engine"  # Backend: docker-engine, kubernetes, process
    code_execution_timeout: int = 30  # Execution timeout in seconds (1-600)
    code_execution_memory_limit_mb: int = 512  # Memory limit in MB (64-8192)
    code_execution_cpu_quota: float = 1.0  # CPU cores quota (0.1-8.0)
    code_execution_disk_quota_mb: int = 100  # Disk quota in MB (1-10240)
    code_execution_max_processes: int = 1  # Maximum processes (1-100)
    code_execution_network_mode: str = "none"  # Network mode: none, allowlist, unrestricted (SECURITY: defaults to 'none' for maximum isolation - users must explicitly opt-in to network access)
    code_execution_allowed_domains: list[str] = []  # Allowed domains for allowlist mode
    code_execution_allowed_imports: list[str] = [
        # Safe standard library modules
        "json",
        "math",
        "datetime",
        "statistics",
        "collections",
        "itertools",
        "functools",
        "typing",
        # Data processing libraries
        "pandas",
        "numpy",
    ]  # Allowed Python imports (whitelist)

    # Docker-specific settings
    code_execution_docker_image: str = "python:3.12-slim"  # Docker image for execution
    code_execution_docker_socket: str = "/var/run/docker.sock"  # Docker socket path

    # Kubernetes-specific settings
    code_execution_k8s_namespace: str = "default"  # Kubernetes namespace for jobs
    code_execution_k8s_job_ttl: int = 300  # Kubernetes job TTL in seconds (cleanup)

    # Conversation Checkpointing (for distributed state across replicas)
    checkpoint_backend: str = "memory"  # "memory", "redis"
    checkpoint_redis_url: str = Field(
        default="redis://localhost:6379/1",  # Use db 1 (sessions use db 0)
        validation_alias="redis_checkpoint_url",  # Accept both names
    )
    checkpoint_redis_ttl: int = 604800  # 7 days TTL for conversation checkpoints

    # OpenFGA
    openfga_api_url: str = "http://localhost:8080"
    openfga_store_id: str | None = None
    openfga_model_id: str | None = None

    # Infisical
    infisical_site_url: str = "https://app.infisical.com"
    infisical_client_id: str | None = None
    infisical_client_secret: str | None = None
    infisical_project_id: str | None = None

    # LangGraph Platform
    langgraph_api_key: str | None = None
    langgraph_deployment_url: str | None = None
    langgraph_api_url: str = "https://api.langchain.com"

    # Authentication Provider
    auth_provider: str = "inmemory"  # "inmemory", "keycloak"
    auth_mode: str = "token"  # "token" (JWT), "session"

    # Mock Data (Development)
    # SECURITY: Mock authorization disabled by default in production
    # Override with ENABLE_MOCK_AUTHORIZATION=true if needed for staging/testing
    enable_mock_authorization: bool | None = None  # None = auto-determine based on environment

    # Keycloak Settings
    keycloak_server_url: str = "http://localhost:8082"
    keycloak_realm: str = "langgraph-agent"
    keycloak_client_id: str = "langgraph-client"
    keycloak_client_secret: str | None = None
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str | None = None
    keycloak_verify_ssl: bool = True
    keycloak_timeout: int = 30  # HTTP timeout in seconds

    # Session Management
    session_backend: str = "memory"  # "memory", "redis"
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="redis_session_url",  # Accept both names
    )
    redis_host: str = "localhost"  # Redis host for rate limiting and cache
    redis_port: int = 6379  # Redis port for rate limiting and cache
    redis_password: str | None = None
    redis_ssl: bool = False
    session_ttl_seconds: int = 86400  # 24 hours
    session_sliding_window: bool = True
    session_max_concurrent: int = 5  # Max concurrent sessions per user

    # API Key Cache Configuration (ADR-0034: Redis-backed API key lookup)
    # Improves API key validation from O(users×keys) to O(1)
    # Redis DB allocation: 0=sessions, 1=checkpoints, 2=api-key-cache, 3=rate-limiting
    api_key_cache_enabled: bool = True  # Enable Redis cache for API key validation
    api_key_cache_db: int = 3  # Redis database number for API key cache (ISOLATED from L2 cache DB 2)
    api_key_cache_ttl: int = 3600  # Cache TTL in seconds (1 hour)

    # Storage Backend Configuration (for compliance data retention)
    # Conversation Storage (uses checkpoint backend by default)
    conversation_storage_backend: str = "checkpoint"  # "checkpoint" (uses checkpoint_backend), "database"

    # GDPR/HIPAA/SOC2 Compliance Storage (ADR-0041: Pure PostgreSQL)
    # Storage for user profiles, preferences, consents, conversations, and audit logs
    # CRITICAL: Must use "postgres" in production (in-memory is DEVELOPMENT ONLY)
    gdpr_storage_backend: str = "memory"  # "postgres" (production), "memory" (dev/test only)
    gdpr_postgres_url: str = "postgresql://postgres:postgres@localhost:5432/gdpr"

    # GDPR Storage Configuration
    # - User profiles: Until deletion request (GDPR Article 17)
    # - Preferences: Until deletion request
    # - Consents: 7 years (GDPR Article 7, legal requirement)
    # - Conversations: 90 days (GDPR Article 5(1)(e), configurable)
    # - Audit logs: 7 years (HIPAA §164.316(b)(2)(i), SOC2 CC6.6)

    # Audit Log Cold Storage (for long-term compliance archival)
    audit_log_cold_storage_backend: str | None = None  # None, "s3", "gcs", "azure", "local"
    audit_log_cold_storage_path: str | None = None  # Local path or bucket name

    # S3 Configuration (for audit log archival)
    aws_s3_bucket: str | None = None  # S3 bucket for audit log archival
    aws_s3_region: str | None = None  # S3 region (defaults to aws_region if not set)
    aws_s3_prefix: str = "audit-logs/"  # S3 key prefix for audit logs

    # GCS Configuration (for audit log archival)
    gcp_storage_bucket: str | None = None  # GCS bucket for audit log archival
    gcp_storage_prefix: str = "audit-logs/"  # GCS object prefix for audit logs
    gcp_credentials_path: str | None = None  # Path to GCP service account credentials JSON

    # Azure Blob Storage Configuration (for audit log archival)
    azure_storage_account: str | None = None  # Azure storage account name
    azure_storage_container: str | None = None  # Azure blob container for audit logs
    azure_storage_prefix: str = "audit-logs/"  # Blob prefix for audit logs
    azure_storage_connection_string: str | None = None  # Azure storage connection string

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    def model_post_init(self, __context: Any) -> None:
        """
        Pydantic v2 hook called after model initialization.

        Performs security validation to ensure production configuration is secure.
        """
        # Validate production security configuration
        self.validate_production_config()

        # Validate CORS configuration
        self.validate_cors_config()

    @field_validator("cors_allowed_origins", "code_execution_allowed_domains", "code_execution_allowed_imports", mode="before")
    @classmethod
    def parse_comma_separated_list(cls, v: Any) -> Any:
        """Parse comma-separated strings from environment variables into lists"""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    def validate_production_config(self) -> None:
        """
        Validate that production configuration is secure.

        SECURITY: Prevents CWE-1188 (Initialization with Insecure Default) by
        enforcing secure configuration in production environments.

        Raises:
            ValueError: If production configuration is insecure
        """
        # Only validate in production/staging environments
        if self.environment.lower() not in ("production", "staging", "prod", "stg"):
            return

        errors = []

        # Check 1: Auth provider must not be inmemory in production
        if self.auth_provider.lower() == "inmemory":
            errors.append(
                "AUTH_PROVIDER=inmemory is not allowed in production. "
                "Use AUTH_PROVIDER=keycloak or another production-grade provider."
            )

        # Check 2: Mock authorization must be explicitly disabled
        if self.get_mock_authorization_enabled():
            errors.append("Mock authorization must be disabled in production. Set ENABLE_MOCK_AUTHORIZATION=false")

        # Check 3: JWT secret key must be set
        if not self.jwt_secret_key or self.jwt_secret_key == "change-this-in-production":
            errors.append(
                "JWT_SECRET_KEY must be set to a secure value in production. "
                "Generate a strong secret key and set it via environment variable."
            )

        # Check 4: GDPR storage must use database in production
        if self.gdpr_storage_backend == "memory":
            errors.append(
                "GDPR_STORAGE_BACKEND=memory is not allowed in production. Use GDPR_STORAGE_BACKEND=postgres for compliance."
            )

        # Check 5: Code execution should be explicitly enabled if needed
        # (Already disabled by default, but log warning if enabled without proper config)
        if self.enable_code_execution and self.code_execution_backend not in ("kubernetes", "docker-engine"):
            errors.append(
                "Code execution is enabled but backend is not set to kubernetes or docker-engine. "
                f"Current: {self.code_execution_backend}"
            )

        if errors:
            error_msg = (
                "PRODUCTION CONFIGURATION SECURITY ERRORS:\n\n"
                + "\n\n".join(f"  {i + 1}. {err}" for i, err in enumerate(errors))
                + "\n\nProduction deployment blocked to prevent security vulnerabilities."
            )
            raise ValueError(error_msg)

    def get_mock_authorization_enabled(self) -> bool:
        """
        Get the effective value of enable_mock_authorization based on environment.

        SECURITY: Mock authorization is disabled by default in production.
        In development, it's enabled by default for better developer experience.

        Returns:
            bool: True if mock authorization should be enabled, False otherwise
        """
        if self.enable_mock_authorization is not None:
            # Explicit override from environment variable
            return self.enable_mock_authorization

        # Auto-determine based on environment
        # Enable in development, disable in production/staging
        return self.environment == "development"

    def get_cors_origins(self) -> list[str]:
        """
        Get the effective CORS allowed origins based on environment and configuration.

        SECURITY: Returns empty list (no CORS) by default in production for security.
        In development, defaults to localhost URLs if not explicitly configured.

        Returns:
            List[str]: List of allowed CORS origins
        """
        if self.cors_allowed_origins:
            # Explicit configuration from environment variable
            return self.cors_allowed_origins

        # Auto-determine based on environment
        if self.environment == "development":
            # Development: Allow common localhost URLs
            return ["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
        else:
            # Production/staging: No CORS by default (fail-closed)
            return []

    def validate_cors_config(self) -> None:
        """
        Validate CORS configuration for security issues.

        SECURITY: Prevents wildcard CORS with credentials in production.
        This configuration is rejected by browsers and is a security risk.

        Raises:
            ValueError: If insecure CORS configuration detected in production
        """
        origins = self.get_cors_origins()

        # Check for wildcard CORS in production
        if self.environment == "production" and "*" in origins:
            msg = (
                "CRITICAL: Wildcard CORS (allow_origins=['*']) is not allowed in production. "
                "This is a security risk and browsers will reject it when allow_credentials=True. "
                "Set CORS_ALLOWED_ORIGINS to specific domains or set ENVIRONMENT=development for local testing."
            )
            raise ValueError(msg)

        # Warn about wildcard in non-production environments
        if self.environment != "production" and "*" in origins:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "SECURITY WARNING: Wildcard CORS detected in %s environment. "
                "This should only be used for local development, never in production.",
                self.environment,
            )

    def _validate_fallback_credentials(self) -> None:
        """
        Validate that fallback models have corresponding API keys configured.

        Logs warnings for missing credentials but doesn't block startup.
        This helps users catch configuration errors early.
        """
        if not self.enable_fallback or not self.fallback_models:
            return

        # Map model patterns to required credentials
        provider_patterns = {
            "anthropic": (["claude", "anthropic"], "anthropic_api_key"),
            "openai": (["gpt-", "o1-", "davinci"], "openai_api_key"),
            "google": (["gemini", "palm", "bison"], "google_api_key"),
            "azure": (["azure/"], "azure_api_key"),
            "bedrock": (["bedrock/"], "aws_access_key_id"),
        }

        missing_creds = []

        for model in self.fallback_models:
            model_lower = model.lower()

            # Determine which provider this model belongs to
            for provider, (patterns, cred_attr) in provider_patterns.items():
                if any(pattern in model_lower for pattern in patterns):
                    # Check if the credential is configured
                    if not getattr(self, cred_attr, None):
                        missing_creds.append((model, provider, cred_attr))
                    break

        # Log warnings for missing credentials
        if missing_creds:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Fallback models configured without required credentials. "
                "These fallbacks will fail at runtime if the primary provider fails."
            )
            for model, provider, cred in missing_creds:
                logger.warning(f"  - Model '{model}' (provider: {provider}) requires '{cred.upper()}' environment variable")

    def load_secrets(self) -> None:  # noqa: C901
        """
        Load secrets from Infisical or environment variables.

        Implements fail-closed security pattern - critical secrets have no fallbacks.
        Secrets are now loaded conditionally based on feature flags to reduce noise.
        """
        secrets_mgr = get_secrets_manager()

        # Load JWT secret (no fallback - fail-closed pattern)
        if not self.jwt_secret_key:
            self.jwt_secret_key = secrets_mgr.get_secret("JWT_SECRET_KEY", fallback=None)

        # Load HIPAA integrity secret ONLY if HIPAA controls are being used
        # Check for enable_hipaa flag or hipaa_integrity_secret env var
        if not self.hipaa_integrity_secret and hasattr(self, "enable_hipaa") and self.enable_hipaa:
            self.hipaa_integrity_secret = secrets_mgr.get_secret("HIPAA_INTEGRITY_SECRET", fallback=None)

        # Load context encryption key ONLY if context encryption is enabled
        if not self.context_encryption_key and self.enable_context_encryption:
            self.context_encryption_key = secrets_mgr.get_secret("CONTEXT_ENCRYPTION_KEY", fallback=None)

        # Load LLM API keys based on ACTIVE provider and fallbacks
        # Primary provider
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            self.anthropic_api_key = secrets_mgr.get_secret("ANTHROPIC_API_KEY", fallback=None)
        elif self.llm_provider == "openai" and not self.openai_api_key:
            self.openai_api_key = secrets_mgr.get_secret("OPENAI_API_KEY", fallback=None)
        elif self.llm_provider == "google" and not self.google_api_key:
            self.google_api_key = secrets_mgr.get_secret("GOOGLE_API_KEY", fallback=None)
        elif self.llm_provider == "azure" and not self.azure_api_key:
            self.azure_api_key = secrets_mgr.get_secret("AZURE_API_KEY", fallback=None)
        elif self.llm_provider == "bedrock" and not self.aws_access_key_id:
            self.aws_access_key_id = secrets_mgr.get_secret("AWS_ACCESS_KEY_ID", fallback=None)
            self.aws_secret_access_key = secrets_mgr.get_secret("AWS_SECRET_ACCESS_KEY", fallback=None)

        # Load fallback providers if fallback enabled
        if self.enable_fallback and self.fallback_models:
            # Check which providers are needed for fallbacks
            fallback_providers = set()
            for model in self.fallback_models:
                model_lower = model.lower()
                if "claude" in model_lower or "anthropic" in model_lower:
                    fallback_providers.add("anthropic")
                elif "gpt-" in model_lower or "o1-" in model_lower:
                    fallback_providers.add("openai")
                elif "gemini" in model_lower or "palm" in model_lower:
                    fallback_providers.add("google")
                elif "azure/" in model_lower:
                    fallback_providers.add("azure")
                elif "bedrock/" in model_lower:
                    fallback_providers.add("bedrock")

            # Load secrets for fallback providers only
            if "anthropic" in fallback_providers and not self.anthropic_api_key:
                self.anthropic_api_key = secrets_mgr.get_secret("ANTHROPIC_API_KEY", fallback=None)
            if "openai" in fallback_providers and not self.openai_api_key:
                self.openai_api_key = secrets_mgr.get_secret("OPENAI_API_KEY", fallback=None)
            if "google" in fallback_providers and not self.google_api_key:
                self.google_api_key = secrets_mgr.get_secret("GOOGLE_API_KEY", fallback=None)
            if "azure" in fallback_providers and not self.azure_api_key:
                self.azure_api_key = secrets_mgr.get_secret("AZURE_API_KEY", fallback=None)
            if "bedrock" in fallback_providers:
                if not self.aws_access_key_id:
                    self.aws_access_key_id = secrets_mgr.get_secret("AWS_ACCESS_KEY_ID", fallback=None)
                if not self.aws_secret_access_key:
                    self.aws_secret_access_key = secrets_mgr.get_secret("AWS_SECRET_ACCESS_KEY", fallback=None)

        # Load OpenFGA configuration (if any OpenFGA settings are configured)
        if self.openfga_api_url and self.openfga_api_url != "http://localhost:8080":
            if not self.openfga_store_id:
                self.openfga_store_id = secrets_mgr.get_secret("OPENFGA_STORE_ID", fallback=None)
            if not self.openfga_model_id:
                self.openfga_model_id = secrets_mgr.get_secret("OPENFGA_MODEL_ID", fallback=None)

        # Load LangSmith configuration ONLY if enabled
        if self.langsmith_tracing and not self.langsmith_api_key:
            self.langsmith_api_key = secrets_mgr.get_secret("LANGSMITH_API_KEY", fallback=None)

        # Load LangGraph Platform configuration (if deployment URL configured)
        if self.langgraph_deployment_url and not self.langgraph_api_key:
            self.langgraph_api_key = secrets_mgr.get_secret("LANGGRAPH_API_KEY", fallback=None)

        # Load Keycloak configuration ONLY if using Keycloak auth provider
        if self.auth_provider == "keycloak":
            if not self.keycloak_client_secret:
                self.keycloak_client_secret = secrets_mgr.get_secret("KEYCLOAK_CLIENT_SECRET", fallback=None)
            if not self.keycloak_admin_password:
                self.keycloak_admin_password = secrets_mgr.get_secret("KEYCLOAK_ADMIN_PASSWORD", fallback=None)

        # Checkpoint configuration loaded on-demand (redis backend specific)

        # Load cloud storage credentials if cold storage is configured
        if self.audit_log_cold_storage_backend == "s3":
            # S3 credentials already loaded via AWS Bedrock configuration if set
            pass
        elif self.audit_log_cold_storage_backend == "azure":
            if not self.azure_storage_connection_string:
                self.azure_storage_connection_string = secrets_mgr.get_secret("AZURE_STORAGE_CONNECTION_STRING", fallback=None)
        elif self.audit_log_cold_storage_backend == "gcs" and not self.gcp_credentials_path:
            # GCP credentials are typically loaded from a file path
            # or via GOOGLE_APPLICATION_CREDENTIALS environment variable
            pass

    # ========================================================================
    # REDIS URL ALIASES (for test compatibility)
    # ========================================================================
    @property
    def redis_checkpoint_url(self) -> str:
        """Alias for checkpoint_redis_url (test compatibility)"""
        return self.checkpoint_redis_url

    @property
    def redis_session_url(self) -> str:
        """Alias for redis_url (test compatibility)"""
        return self.redis_url

    def get_secret(self, key: str, fallback: str | None = None) -> str | None:
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
# SECURITY: Do not log exception details - may contain credentials (CWE-532)
try:
    settings.load_secrets()
except Exception:
    # Note: We intentionally don't log the exception message as it may contain
    # Infisical credentials, connection strings, or other sensitive data.
    # The fallback to environment variables is silent and graceful.
    import logging

    _logger = logging.getLogger(__name__)
    _logger.warning("Failed to load secrets from Infisical, using environment fallback")

# Validate fallback model credentials
settings._validate_fallback_credentials()
