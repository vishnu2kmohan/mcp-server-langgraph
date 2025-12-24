"""
Agent Configuration Module.

Settings for LangGraph agent behavior, feature flags, and graph configuration.
"""

from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class AgentSettings(DomainSettings):
    """
    Agent behavior and feature flag settings.

    Covers:
    - Agentic loop configuration (context management, verification)
    - Dynamic context loading
    - Parallel tool execution
    - LLM extraction
    - Code execution sandbox
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # Agent Core
    max_iterations: int = 10
    enable_checkpointing: bool = True

    # Context Management (Anthropic Best Practices)
    enable_context_compaction: bool = True
    compaction_threshold: int = 8000
    target_after_compaction: int = 4000
    recent_message_count: int = 5

    # Work Verification (LLM-as-judge)
    enable_verification: bool = True
    verification_quality_threshold: float = 0.7
    max_refinement_attempts: int = 3
    verification_mode: str = "standard"  # "standard", "strict", "lenient"

    # Dynamic Context Loading (Just-in-Time)
    enable_dynamic_context_loading: bool = False

    # Parallel Tool Execution
    enable_parallel_execution: bool = False
    max_parallel_tools: int = 5

    # Enhanced Note-Taking
    enable_llm_extraction: bool = False
    extraction_categories: list[str] = [
        "decisions",
        "requirements",
        "facts",
        "action_items",
        "issues",
        "preferences",
    ]

    # Code Execution Configuration
    # SECURITY: Disabled by default - must be explicitly enabled
    enable_code_execution: bool = False
    code_execution_backend: str = "docker-engine"  # docker-engine, kubernetes, process
    code_execution_timeout: int = 30
    code_execution_memory_limit_mb: int = 512
    code_execution_cpu_quota: float = 1.0
    code_execution_disk_quota_mb: int = 100
    code_execution_max_processes: int = 1
    code_execution_network_mode: str = "none"  # none, allowlist, unrestricted
    code_execution_allowed_domains: list[str] = []
    code_execution_allowed_imports: list[str] = [
        "json",
        "math",
        "datetime",
        "statistics",
        "collections",
        "itertools",
        "functools",
        "typing",
        "pandas",
        "numpy",
    ]

    # Docker-specific settings
    code_execution_docker_image: str = "mcr.microsoft.com/playwright/python:v1.42.0-jammy"
    code_execution_docker_socket: str = "/var/run/docker.sock"

    # Kubernetes-specific settings
    code_execution_k8s_namespace: str = "default"
    code_execution_k8s_job_ttl: int = 300


__all__ = ["AgentSettings"]
